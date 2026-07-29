from __future__ import annotations

import json
import sqlite3
import statistics
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from src.db.retrieval import get_all_episodes_with_embeddings
from src.embeddings.provider import cosine_similarity
from src.memory.context_matched_stm import (
    extract_arm_l_payload,
    pack_stm_payload,
)


CALIBRATION_TURNS = tuple(range(92, 112))
N_CAPS = tuple(range(12, 41, 2))
K_THRESHOLDS = (0.48, 0.45, 0.40, 0.35)
PAYLOAD_BUDGET = 60_595
MATCH_GATE_MEDIAN_APE = 0.05


def arm_l_target_vector(
    prompt_root: Path,
    turns: Iterable[int] = CALIBRATION_TURNS,
) -> list[int]:
    return [
        len(
            extract_arm_l_payload(
                (prompt_root / f"turn_{turn:03d}.txt").read_text(
                    encoding="utf-8"
                )
            )
        )
        for turn in turns
    ]


def calibrate_context_match(
    *,
    arm_l_prompt_root: Path,
    arm_s_database: Path,
    script_path: Path,
    embedder: Callable[[str], np.ndarray],
) -> dict:
    target_vector = arm_l_target_vector(arm_l_prompt_root)
    if int(statistics.median(target_vector)) != PAYLOAD_BUDGET:
        raise AssertionError("Arm L calibration median changed")

    script = json.loads(script_path.read_text(encoding="utf-8"))
    script_turns = {
        int(item["turn"]): str(item["user"])
        for item in script["turns"]
        if int(item["turn"]) <= CALIBRATION_TURNS[-1]
    }
    expected_turns = set(range(1, CALIBRATION_TURNS[-1] + 1))
    if set(script_turns) != expected_turns:
        raise AssertionError("Calibration script turns are incomplete")

    episodes = _load_calibration_episodes(arm_s_database)
    ordered_turns = sorted(script_turns)
    query_texts = [script_turns[turn] for turn in ordered_turns]
    if hasattr(embedder, "embed_many"):
        query_vectors = embedder.embed_many(query_texts)
    else:
        query_vectors = [embedder(text) for text in query_texts]
    query_embeddings = {
        turn: np.asarray(vector, dtype=np.float32)
        for turn, vector in zip(
            ordered_turns,
            query_vectors,
            strict=True,
        )
    }
    similarities = {
        turn: {
            str(episode["id"]): cosine_similarity(
                query_embeddings[turn],
                episode["embedding"],
            )
            for episode in episodes
            if int(episode["turn_number"]) < turn
        }
        for turn in sorted(script_turns)
    }

    candidate_rows = [
        _calibrate_cell(
            episodes=episodes,
            similarities=similarities,
            target_vector=target_vector,
            n_cap=n_cap,
            k_threshold=k_threshold,
        )
        for n_cap in N_CAPS
        for k_threshold in K_THRESHOLDS
    ]
    candidate_rows.sort(
        key=lambda row: (
            row["mean_absolute_error"],
            row["maximum_absolute_error"],
            row["n_cap"],
            -row["k_threshold"],
        )
    )
    selected = candidate_rows[0]
    selected["match_gate_status"] = (
        "PASS"
        if selected["median_absolute_percentage_error"]
        <= MATCH_GATE_MEDIAN_APE
        else "FAIL"
    )
    return {
        "status": "LOCKED_BEFORE_T6_INFERENCE",
        "calibration_turns": list(CALIBRATION_TURNS),
        "payload_budget": PAYLOAD_BUDGET,
        "match_gate_median_absolute_percentage_error": (
            MATCH_GATE_MEDIAN_APE
        ),
        "arm_l_target_vector": target_vector,
        "arm_l_target_median": int(statistics.median(target_vector)),
        "arm_l_target_minimum": min(target_vector),
        "arm_l_target_maximum": max(target_vector),
        "grid": {
            "n_caps": list(N_CAPS),
            "k_thresholds": list(K_THRESHOLDS),
            "cell_count": len(candidate_rows),
        },
        "candidate_rows": candidate_rows,
        "selected": selected,
    }


def _calibrate_cell(
    *,
    episodes: list[dict],
    similarities: dict[int, dict[str, float]],
    target_vector: list[int],
    n_cap: int,
    k_threshold: float,
) -> dict:
    last_generation: dict[str, int] = {}
    delivered_vector: list[int] = []
    delivered_n_counts: list[int] = []
    delivered_k_only_counts: list[int] = []

    for turn in range(1, CALIBRATION_TURNS[-1] + 1):
        eligible = [
            episode
            for episode in episodes
            if int(episode["turn_number"]) < turn
        ]
        n_ranked = sorted(
            eligible,
            key=lambda episode: _calibration_n_key(
                episode,
                last_generation,
            ),
        )[:n_cap]
        n_ids = {str(episode["id"]) for episode in n_ranked}
        k_ranked = [
            {
                **_clean_calibration_episode(episode),
                "similarity": similarities[turn][str(episode["id"])],
                "provenance": "stm",
            }
            for episode in eligible
            if similarities[turn][str(episode["id"])] >= k_threshold
            and str(episode["id"]) not in n_ids
        ]
        packed = pack_stm_payload(
            [_clean_calibration_episode(episode) for episode in n_ranked],
            k_ranked,
            PAYLOAD_BUDGET,
        )
        for episode_id in packed.selected_ids:
            last_generation[episode_id] = turn
        if turn in CALIBRATION_TURNS:
            delivered_vector.append(packed.serialized_chars)
            delivered_n_counts.append(len(packed.recent_episodes))
            delivered_k_only_counts.append(len(packed.stm_episodes))

    absolute_errors = [
        abs(delivered - target)
        for delivered, target in zip(
            delivered_vector,
            target_vector,
            strict=True,
        )
    ]
    absolute_percentage_errors = [
        error / target
        for error, target in zip(
            absolute_errors,
            target_vector,
            strict=True,
        )
    ]
    return {
        "n_cap": n_cap,
        "k_threshold": k_threshold,
        "delivered_vector": delivered_vector,
        "delivered_median": int(statistics.median(delivered_vector)),
        "delivered_minimum": min(delivered_vector),
        "delivered_maximum": max(delivered_vector),
        "delivered_n_counts": delivered_n_counts,
        "delivered_k_only_counts": delivered_k_only_counts,
        "absolute_errors": absolute_errors,
        "mean_absolute_error": statistics.fmean(absolute_errors),
        "maximum_absolute_error": max(absolute_errors),
        "median_absolute_percentage_error": statistics.median(
            absolute_percentage_errors
        ),
    }


def _calibration_n_key(
    episode: dict,
    last_generation: dict[str, int],
) -> tuple:
    episode_id = str(episode["id"])
    generation = last_generation.get(episode_id)
    return (
        generation is not None,
        generation if generation is not None else -1,
        int(episode["turn_number"]),
        episode_id,
    )


def _clean_calibration_episode(episode: dict) -> dict:
    return {
        "id": str(episode["id"]),
        "topic_id": episode.get("topic_id"),
        "topic_label": (
            episode.get("topic_label")
            or episode.get("topic_id")
            or ""
        ),
        "user_message": episode["user_message"],
        "assistant_message": episode["assistant_message"],
        "turn_number": int(episode["turn_number"]),
    }


def _load_calibration_episodes(database: Path) -> list[dict]:
    with sqlite3.connect(database) as conn:
        rows = get_all_episodes_with_embeddings(conn)
    episodes = []
    for row in rows:
        episode = dict(row)
        if episode["embedding"] is None:
            raise AssertionError(
                f"Calibration episode {episode['id']} has no embedding"
            )
        episode["embedding"] = np.frombuffer(
            episode["embedding"],
            dtype=np.float32,
        )
        episodes.append(episode)
    return episodes

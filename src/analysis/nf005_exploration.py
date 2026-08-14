"""NF-005 pre-registration exploration of candidate information dilution."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from analysis.nf002_streams import DATASET_SHA256, episode_text

PART1 = Path(
    "experiments/components/biological_memory/nf_003/artifacts/part1_record.json"
)
PART1_LF_SHA256 = "2d29387251b109f780d7a2fe86e7a1d3244eb0f5a73515b1be1d8e7dda7e506f"
CACHE = Path(
    "experiments/external/longmemeval/runs/ec002_k_first/"
    "ec002_exact_solo_embeddings.db"
)
LOCOMO_SHA256 = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
OUTPUT = Path(
    "experiments/components/biological_memory/nf_005/artifacts/exploration.json"
)
_LOCOMO_SESSION = re.compile(r"session_(\d+)")


class NF005ExplorationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def content_digest(values: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for value in sorted(values):
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, byteorder="big", signed=False))
        digest.update(encoded)
    return digest.hexdigest()


def distribution(values: Iterable[int]) -> dict[str, float | int]:
    ordered = sorted(values)
    if not ordered:
        raise NF005ExplorationError("Cannot summarize an empty distribution")

    def nearest(percentile: float) -> int:
        return ordered[math.ceil(percentile * len(ordered)) - 1]

    return {
        "n": len(ordered),
        "min": ordered[0],
        "p10": nearest(0.10),
        "p50": nearest(0.50),
        "p90": nearest(0.90),
        "max": ordered[-1],
        "mean": round(sum(ordered) / len(ordered), 6),
    }


def _average_ranks(values: Sequence[float]) -> np.ndarray:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average = (start + 1 + end) / 2.0
        for position in order[start:end]:
            ranks[position] = average
        start = end
    return ranks


def spearman(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise NF005ExplorationError("Spearman inputs must have equal nontrivial size")
    correlation = np.corrcoef(_average_ranks(left), _average_ranks(right))[0, 1]
    return round(float(correlation), 6)


def turn_text(turn: dict[str, Any]) -> str:
    role = str(turn.get("role", "")).strip().capitalize()
    return f"{role}: {turn.get('content', '')}"


def _locomo_pair_lengths(dataset_path: Path) -> list[int]:
    if sha256_file(dataset_path) != LOCOMO_SHA256:
        raise NF005ExplorationError("LoCoMo source differs from its corpus lock")
    rows = json.loads(dataset_path.read_text(encoding="utf-8"))
    lengths: list[int] = []
    for row in rows:
        conversation = row["conversation"]
        session_keys = sorted(
            (key for key in conversation if _LOCOMO_SESSION.fullmatch(key)),
            key=lambda key: int(_LOCOMO_SESSION.fullmatch(key).group(1)),  # type: ignore[union-attr]
        )
        for session_key in session_keys:
            turns = conversation[session_key]
            for start in range(0, len(turns), 2):
                members = turns[start : start + 2]
                text = "\n".join(
                    f"{turn['speaker']}: {turn['text']}" for turn in members
                )
                lengths.append(len(text))
    return lengths


def _episode_rank_turn_pack_baseline(
    items: Sequence[dict[str, Any]],
    part1_rows: dict[str, dict[str, Any]],
    connection: sqlite3.Connection,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    def vector(text: str) -> np.ndarray:
        found = connection.execute(
            "select embedding from cache where text=?", (text,)
        ).fetchone()
        if found is None:
            raise NF005ExplorationError("Baseline reproduction encountered a cache miss")
        value = np.frombuffer(found[0], dtype=np.float32).astype(np.float64)
        norm = float(np.linalg.norm(value))
        if norm == 0.0:
            raise NF005ExplorationError("Baseline reproduction encountered a zero vector")
        return value / norm

    for item in items:
        episodes: list[str] = []
        turns: list[tuple[str, bool]] = []
        for session in item["haystack_sessions"]:
            for start in range(0, len(session) - 1, 2):
                first, second = session[start : start + 2]
                if first.get("role") != "user" or second.get("role") != "assistant":
                    continue
                episodes.append(
                    episode_text(
                        str(first.get("content", "")),
                        str(second.get("content", "")),
                    )
                )
                turns.extend(
                    (
                        (turn_text(first), bool(first.get("has_answer"))),
                        (turn_text(second), bool(second.get("has_answer"))),
                    )
                )

        query = vector(str(item["question"]))
        scores = np.vstack([vector(text) for text in episodes]) @ query
        order = np.lexsort((np.arange(len(episodes)), -scores))
        used = 0
        delivered_evidence = 0
        delivered_turns = 0
        evidence_total = sum(is_evidence for _, is_evidence in turns)
        for episode_position in order:
            for turn_position in (2 * int(episode_position), 2 * int(episode_position) + 1):
                text, is_evidence = turns[turn_position]
                if used + len(text) > 32_000:
                    continue
                used += len(text)
                delivered_turns += 1
                delivered_evidence += is_evidence
        rows.append(
            {
                "question_id": item["question_id"],
                "any_evidence": delivered_evidence > 0,
                "all_evidence": delivered_evidence == evidence_total,
                "packed_chars": used,
                "delivered_turns": delivered_turns,
                "total_chars": sum(len(text) for text, _ in turns),
            }
        )

    old = {
        question_id: row["episode_ranked_episodes_delivered"] > 0
        for question_id, row in part1_rows.items()
    }
    gains = sum(not old[row["question_id"]] and row["any_evidence"] for row in rows)
    losses = sum(old[row["question_id"]] and not row["any_evidence"] for row in rows)
    return {
        "items": len(rows),
        "episode_rank_episode_pack_any": sum(old.values()),
        "episode_rank_turn_pack_any": sum(row["any_evidence"] for row in rows),
        "episode_rank_turn_pack_all": sum(row["all_evidence"] for row in rows),
        "packing_contrast": {
            "gains": gains,
            "losses": losses,
            "ties": len(rows) - gains - losses,
            "net": gains - losses,
        },
        "any_evidence_misses": sum(not row["any_evidence"] for row in rows),
        "full_store_fits": sum(row["total_chars"] <= 32_000 for row in rows),
        "min_total_chars": min(row["total_chars"] for row in rows),
        "packed_chars": distribution(row["packed_chars"] for row in rows),
        "delivered_turns": distribution(row["delivered_turns"] for row in rows),
        "row_digest": hashlib.sha256(
            json.dumps(
                rows,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
    }


def explore(
    repository_root: Path,
    longmemeval_path: Path,
    locomo_path: Path,
) -> dict[str, Any]:
    if sha256_file(longmemeval_path) != DATASET_SHA256:
        raise NF005ExplorationError("LongMemEval source differs from its corpus lock")
    part1_path = repository_root / PART1
    if lf_sha256(part1_path) != PART1_LF_SHA256:
        raise NF005ExplorationError("NF-003 Part 1 record changed")

    part1 = json.loads(part1_path.read_text(encoding="utf-8"))
    part1_rows = {row["question_id"]: row for row in part1["rows"]}
    source = json.loads(longmemeval_path.read_text(encoding="utf-8"))
    items = [row for row in source if row.get("question_id") in part1_rows]
    if len(items) != len(part1_rows) != 0:
        raise NF005ExplorationError("LongMemEval population identity differs")

    episode_lengths: list[int] = []
    evidence_episode_lengths: list[int] = []
    turn_lengths: list[int] = []
    evidence_turn_lengths: list[int] = []
    role_lengths: dict[str, list[int]] = {"user": [], "assistant": []}
    evidence_roles: Counter[str] = Counter()
    evidence_flags_per_item: Counter[int] = Counter()
    malformed_pairs = 0
    unique_turn_texts: set[str] = set()
    questions: set[str] = set()

    for item in items:
        questions.add(str(item["question"]))
        item_flags = 0
        for session in item["haystack_sessions"]:
            for start in range(0, len(session) - 1, 2):
                first, second = session[start : start + 2]
                if first.get("role") != "user" or second.get("role") != "assistant":
                    malformed_pairs += 1
                    continue
                rendered_episode = episode_text(
                    str(first.get("content", "")), str(second.get("content", ""))
                )
                episode_lengths.append(len(rendered_episode))
                episode_is_evidence = bool(
                    first.get("has_answer") or second.get("has_answer")
                )
                if episode_is_evidence:
                    evidence_episode_lengths.append(len(rendered_episode))
                for turn in (first, second):
                    rendered_turn = turn_text(turn)
                    role = str(turn["role"])
                    turn_lengths.append(len(rendered_turn))
                    role_lengths[role].append(len(rendered_turn))
                    unique_turn_texts.add(rendered_turn)
                    if turn.get("has_answer"):
                        item_flags += 1
                        evidence_roles[role] += 1
                        evidence_turn_lengths.append(len(rendered_turn))
        evidence_flags_per_item[item_flags] += 1

    cache_path = repository_root / CACHE
    connection = sqlite3.connect(f"file:{cache_path.as_posix()}?mode=ro", uri=True)
    try:
        def hit_count(texts: Iterable[str]) -> int:
            return sum(
                connection.execute(
                    "select 1 from cache where text=?", (text,)
                ).fetchone()
                is not None
                for text in texts
            )

        query_hits = hit_count(questions)
        turn_hits = hit_count(unique_turn_texts)
        cache_entries = int(
            connection.execute("select count(*) from cache").fetchone()[0]
        )
        baseline = _episode_rank_turn_pack_baseline(
            items, part1_rows, connection
        )
    finally:
        connection.close()

    correlations: dict[str, Any] = {}
    groups = {"all": list(part1_rows.values())}
    for question_type in sorted({row["question_type"] for row in part1_rows.values()}):
        groups[question_type] = [
            row for row in part1_rows.values() if row["question_type"] == question_type
        ]
    for name, rows in groups.items():
        correlations[name] = {
            "n": len(rows),
            "spearman_episode_chars_vs_best_rank_fraction": spearman(
                [float(row["median_evidence_chars"]) for row in rows],
                [float(row["best_evidence_rank_fraction"]) for row in rows],
            ),
        }

    locomo_lengths = _locomo_pair_lengths(locomo_path)
    evidence_episode_p50 = int(distribution(evidence_episode_lengths)["p50"])
    evidence_turn_p50 = int(distribution(evidence_turn_lengths)["p50"])
    locomo_pair_p50 = int(distribution(locomo_lengths)["p50"])
    return {
        "schema": "nf005-exploration-v1",
        "inputs": {
            "longmemeval": {
                "path": str(longmemeval_path),
                "sha256": DATASET_SHA256,
                "items": len(source),
            },
            "locomo": {
                "path": str(locomo_path),
                "sha256": LOCOMO_SHA256,
            },
            "nf003_part1": {
                "path": PART1.as_posix(),
                "lf_sha256": PART1_LF_SHA256,
            },
            "embedding_cache": {
                "path": CACHE.as_posix(),
                "entries": cache_entries,
            },
        },
        "population": {
            "items": len(items),
            "comparison_key": "question_id",
            "comparison_key_digest": content_digest(part1_rows),
            "malformed_source_pairs": malformed_pairs,
            "evidence_flags_per_item": {
                str(key): value for key, value in sorted(evidence_flags_per_item.items())
            },
        },
        "candidate_lengths": {
            "locomo_adjacent_pairs": distribution(locomo_lengths),
            "longmemeval_episodes": distribution(episode_lengths),
            "longmemeval_evidence_episodes": distribution(evidence_episode_lengths),
            "longmemeval_source_turns": distribution(turn_lengths),
            "longmemeval_user_turns": distribution(role_lengths["user"]),
            "longmemeval_assistant_turns": distribution(role_lengths["assistant"]),
            "longmemeval_evidence_turns": distribution(evidence_turn_lengths),
            "evidence_episode_to_locomo_pair_p50_ratio": round(
                evidence_episode_p50 / locomo_pair_p50, 6
            ),
            "evidence_episode_to_evidence_turn_p50_ratio": round(
                evidence_episode_p50 / evidence_turn_p50, 6
            ),
        },
        "evidence_roles": dict(sorted(evidence_roles.items())),
        "length_rank_association": correlations,
        "cache_coverage": {
            "unique_queries": len(questions),
            "query_hits": query_hits,
            "unique_turn_texts": len(unique_turn_texts),
            "unique_turn_text_digest": content_digest(unique_turn_texts),
            "turn_hits": turn_hits,
            "turn_misses": len(unique_turn_texts) - turn_hits,
        },
        "registered_baseline_feasibility": baseline,
        "degenerate_states": {
            "turn_candidates_over_32000_chars": sum(
                length > 32_000 for length in turn_lengths
            ),
            "max_turn_chars": max(turn_lengths),
            "feedback": False,
            "full_store_fit_is_the_only_absorbing_delivery_ceiling": True,
        },
        "behavioral_identity": (
            "A LongMemEval episode pairs a usually short evidence-bearing user turn "
            "with a much longer assistant turn before one cosine is computed."
        ),
        "model_calls": 0,
        "embedding_calls": 0,
    }


def write(
    repository_root: Path,
    longmemeval_path: Path,
    locomo_path: Path,
) -> Path:
    output = repository_root / OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            explore(repository_root, longmemeval_path, locomo_path),
            ensure_ascii=True,
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output

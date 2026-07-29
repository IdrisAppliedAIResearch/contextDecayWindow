from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import sqlite3
import statistics
import subprocess
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable

from src.memory.context_matched_stm import extract_arm_l_payload, extract_stm_payload
from src.retrieval_bakeoff.tier6 import _calibration_n_key


REPO_ROOT = Path(__file__).resolve().parents[2]
SURVEY_ROOT = (
    REPO_ROOT / "experiments" / "surveys" / "retrieval_bakeoff"
)
TIER6_ROOT = SURVEY_ROOT / "tier6"
RUN_ID = os.environ.get("CDW_TIER6_ANALYSIS_RUN_ID", "tier6_live_121")
RUN_ROOT = TIER6_ROOT / "runs" / RUN_ID / "context_matched_stm"
ARM_S_ROOT = (
    REPO_ROOT
    / "experiments"
    / "study_009"
    / "runs"
    / "study_009_full_001"
    / "arm_s"
)
ARM_L_ROOT = (
    REPO_ROOT
    / "experiments"
    / "study_007"
    / "runs"
    / "study_007_full_001"
    / "condition_c"
)
EVALUATION_DIR = os.environ.get("CDW_TIER6_ANALYSIS_EVALUATION", "evaluation")
TIER6_SCORE = TIER6_ROOT / EVALUATION_DIR / "blinded_scores.json"
ARM_S_SCORE = (
    REPO_ROOT
    / "experiments"
    / "audits"
    / "scoring_integrity"
    / "corrected_scores"
    / "arms"
    / "s009_s_corrected.json"
)
ARM_L_SCORE = (
    REPO_ROOT
    / "experiments"
    / "audits"
    / "scoring_integrity"
    / "corrected_scores"
    / "arms"
    / "s009_l_corrected.json"
)
SETTINGS_PATH = (
    SURVEY_ROOT / "settings" / "tier6_context_match_settings.json"
)
OUTPUT_ROOT = TIER6_ROOT / os.environ.get(
    "CDW_TIER6_ANALYSIS_OUTPUT", "analysis_121"
)

SCORE_COMMIT = os.environ.get("CDW_TIER6_SCORE_COMMIT", "39423b02")
MAPPING_COMMIT = os.environ.get("CDW_TIER6_MAPPING_COMMIT", "35af70a4")
SEQUENCING_AMENDMENT_COMMIT = "c87de99e"
MECHANISM_ARTIFACT_COMMIT = "a3c80b07"


ATOMIC_ITEMS = (
    ("civil", "Halcyon Crossing", "halcyon crossing", (3,)),
    ("civil", "847", "847", (3,)),
    ("civil", "Dr. Anara Bekova", "anara bekova", (3,)),
    ("civil", "S460ML", "s460ml", (4,)),
    ("civil", "92.4", "92.4", (4,)),
    (
        "art",
        "The Annunciation of Forli",
        "annunciation of forli",
        (55,),
    ),
    ("art", "Melozzo da Forli", "melozzo da forli", (55,)),
    (
        "art",
        "Cardinal Giuliano della Rovere",
        "giuliano della rovere",
        (55, 60),
    ),
    ("art", "1483", "1483", (55,)),
    ("monetary", "Taylor Rule", "taylor rule", (61,)),
    ("monetary", "Federal Reserve", "federal reserve", (62,)),
    ("monetary", "Dr. Priya Mehta", "priya mehta", (65,)),
    ("monetary", "2.3%", "2.3%", (65,)),
    (
        "marine",
        "Vampyroteuthis infernalis",
        "vampyroteuthis infernalis",
        (100,),
    ),
    ("marine", "Dr. Kenji Watanabe", "kenji watanabe", (100,)),
    ("marine", "600", "600", (100,)),
    ("marine", "marine snow", "marine snow", (102,)),
)

TARGETED_ITEMS = {
    "Q1": (112, ("847", "s460ml")),
    "Q2": (113, ("anara bekova", "92.4")),
    "Q4": (
        115,
        (
            "annunciation of forli",
            "melozzo da forli",
            "giuliano della rovere",
            "1483",
        ),
    ),
    "Q5": (116, ("lead white", "ultramarine glaze")),
    "Q6": (117, ("giuliano della rovere", "pope julius ii")),
    "Q7": (
        118,
        (
            "vampyroteuthis infernalis",
            "kenji watanabe",
            "600",
            "900",
            "marine snow",
        ),
    ),
    "Q8": (119, ("photophores", "mantle margin")),
    "Q10": (
        118,
        ("vampyroteuthis infernalis", "kenji watanabe"),
    ),
}

ARM_CONFIG = {
    "T6": (RUN_ROOT, extract_stm_payload),
    "S": (ARM_S_ROOT, extract_stm_payload),
    "L": (ARM_L_ROOT, extract_arm_l_payload),
}

EPISODE_RE = re.compile(
    r'<episode\b[^>]*\bturn="(\d+)"[^>]*>.*?</episode>',
    re.DOTALL,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    ).lower()


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def verify_mechanism_seal(run_root: Path = RUN_ROOT) -> dict:
    seal_path = run_root / "mechanism_seal.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    actual = {}
    mismatches = []
    for relative, expected in seal["mechanism_files"].items():
        path = run_root / relative
        if not path.is_file():
            mismatches.append(
                {
                    "path": relative,
                    "status": "MISSING",
                    "expected": expected,
                    "actual": None,
                }
            )
            continue
        actual_digest = sha256(path)
        actual[relative] = actual_digest
        if actual_digest != expected:
            mismatches.append(
                {
                    "path": relative,
                    "status": "HASH_MISMATCH",
                    "expected": expected,
                    "actual": actual_digest,
                }
            )

    aggregate = hashlib.sha256()
    for relative, digest in sorted(actual.items()):
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\0")

    excluded = {"scoring_surface.json", "mechanism_seal.json"}
    observed_files = {
        path.relative_to(run_root).as_posix()
        for path in run_root.rglob("*")
        if path.is_file() and path.name not in excluded
    }
    expected_files = set(seal["mechanism_files"])
    extras = sorted(observed_files - expected_files)
    missing = sorted(expected_files - observed_files)
    status = (
        "PASS"
        if not mismatches
        and not extras
        and not missing
        and aggregate.hexdigest() == seal["aggregate_sha256"]
        else "FAIL"
    )
    return {
        "status": status,
        "seal_status": seal["status"],
        "mechanism_file_count": len(actual),
        "expected_file_count": seal["mechanism_file_count"],
        "aggregate_sha256": aggregate.hexdigest(),
        "expected_aggregate_sha256": seal["aggregate_sha256"],
        "mismatches": mismatches,
        "extra_files": extras,
        "missing_files": missing,
    }


def _window_match(
    *,
    turns: Iterable[int],
    live_by_turn: dict[int, dict],
    target_by_turn: dict[int, int],
) -> dict:
    ordered = list(turns)
    live = [
        int(live_by_turn[turn]["retrieval_payload_chars"])
        for turn in ordered
    ]
    target = [target_by_turn[turn] for turn in ordered]
    signed_errors = [
        delivered - expected
        for delivered, expected in zip(live, target, strict=True)
    ]
    absolute_errors = [abs(error) for error in signed_errors]
    apes = [
        error / expected
        for error, expected in zip(absolute_errors, target, strict=True)
    ]
    return {
        "turns": ordered,
        "live_vector": live,
        "target_vector": target,
        "signed_errors": signed_errors,
        "live_median": int(statistics.median(live)),
        "target_median": int(statistics.median(target)),
        "mean_absolute_error": statistics.fmean(absolute_errors),
        "maximum_absolute_error": max(absolute_errors),
        "median_absolute_percentage_error": statistics.median(apes),
        "turns_within_5_percent": sum(ape <= 0.05 for ape in apes),
        "turn_count": len(ordered),
    }


def context_match_analysis() -> tuple[dict, list[dict]]:
    rows = read_jsonl(RUN_ROOT / "logs" / "context_match.jsonl")
    live_by_turn = {int(row["turn_number"]): row for row in rows}
    target_by_turn = {
        turn: len(
            extract_arm_l_payload(
                (
                    ARM_L_ROOT
                    / "constructed_prompts"
                    / f"turn_{turn:03d}.txt"
                ).read_text(encoding="utf-8")
            )
        )
        for turn in range(1, 122)
    }
    calibration = _window_match(
        turns=range(92, 112),
        live_by_turn=live_by_turn,
        target_by_turn=target_by_turn,
    )
    probes = _window_match(
        turns=range(112, 122),
        live_by_turn=live_by_turn,
        target_by_turn=target_by_turn,
    )
    probe_rows = [
        {
            "turn": turn,
            "live_chars": live_by_turn[turn]["retrieval_payload_chars"],
            "arm_l_target_chars": target_by_turn[turn],
            "signed_error": (
                live_by_turn[turn]["retrieval_payload_chars"]
                - target_by_turn[turn]
            ),
            "absolute_percentage_error": abs(
                live_by_turn[turn]["retrieval_payload_chars"]
                - target_by_turn[turn]
            )
            / target_by_turn[turn],
            "n_candidate_count": live_by_turn[turn]["n_candidate_count"],
            "n_delivered_count": live_by_turn[turn]["n_delivered_count"],
            "k_candidate_count": live_by_turn[turn]["k_candidate_count"],
            "k_delivered_count": live_by_turn[turn]["k_delivered_count"],
            "k_only_delivered_count": live_by_turn[turn][
                "k_only_delivered_count"
            ],
            "skipped_k_count": len(live_by_turn[turn]["skipped_k_ids"]),
        }
        for turn in range(112, 122)
    ]
    return (
        {
            "registered_gate_window_92_111": calibration,
            "observational_probe_window_112_121": probes,
            "registered_gate_status": (
                "PASS"
                if calibration["median_absolute_percentage_error"] <= 0.05
                else "FAIL"
            ),
        },
        probe_rows,
    )


def _domain_for_turn(turn: int) -> str:
    if turn <= 30:
        return "civil"
    if turn <= 60:
        return "art"
    if turn <= 90:
        return "monetary"
    if turn <= 111:
        return "marine"
    return "probe"


def _retrieval_payload(arm: str, turn: int) -> str:
    root, extractor = ARM_CONFIG[arm]
    path = root / "constructed_prompts" / f"turn_{turn:03d}.txt"
    return extractor(path.read_text(encoding="utf-8"))


def retrieval_composition_analysis() -> tuple[dict, list[dict], list[dict]]:
    rows = read_jsonl(RUN_ROOT / "logs" / "context_match.jsonl")
    by_turn = {int(row["turn_number"]): row for row in rows}
    with sqlite3.connect(RUN_ROOT / "study.db") as connection:
        connection.row_factory = sqlite3.Row
        episodes = {
            str(row["id"]): dict(row)
            for row in connection.execute(
                "SELECT id, turn_number, ground_truth_domain, user_message, "
                "assistant_message, retrieval_count, last_retrieved_at "
                "FROM episodes"
            )
        }

    composition_rows = []
    for arm in ("T6", "S", "L"):
        for turn in (120, 121):
            payload = _retrieval_payload(arm, turn)
            matches = list(EPISODE_RE.finditer(payload))
            counts = {
                domain: sum(
                    _domain_for_turn(int(match.group(1))) == domain
                    for match in matches
                )
                for domain in (
                    "civil",
                    "art",
                    "monetary",
                    "marine",
                    "probe",
                )
            }
            chars = {
                domain: sum(
                    len(match.group(0))
                    for match in matches
                    if _domain_for_turn(int(match.group(1))) == domain
                )
                for domain in counts
            }
            composition_rows.append(
                {
                    "arm": arm,
                    "turn": turn,
                    "retrieval_payload_chars": len(payload),
                    "episode_count": len(matches),
                    **{
                        f"{domain}_episode_count": count
                        for domain, count in counts.items()
                    },
                    **{
                        f"{domain}_serialized_chars": value
                        for domain, value in chars.items()
                    },
                }
            )

    probe_selection_rows = []
    for turn in range(112, 122):
        row = by_turn[turn]
        selected = [
            episodes[str(episode_id)]
            for episode_id in row["selected_ids"]
        ]
        selected_turns = [int(episode["turn_number"]) for episode in selected]
        domain_counts = {
            domain: sum(
                str(episode["ground_truth_domain"]) == domain
                for episode in selected
            )
            for domain in (
                "civil_engineering",
                "renaissance_art",
                "monetary_policy",
                "marine_biology",
                "probe",
            )
        }
        probe_selection_rows.append(
            {
                "turn": turn,
                "selected_source_turns": ";".join(
                    str(source_turn) for source_turn in selected_turns
                ),
                "selected_count": len(selected),
                **{
                    f"{domain}_count": count
                    for domain, count in domain_counts.items()
                },
                "k_candidate_count": row["k_candidate_count"],
                "k_only_delivered_count": row["k_only_delivered_count"],
                "skipped_k_source_turns": ";".join(
                    str(episodes[str(episode_id)]["turn_number"])
                    for episode_id in row["skipped_k_ids"]
                ),
            }
        )

    plant_turns = (3, 4, 55, 56, 60, 61, 62, 65, 100, 101, 102)
    plant_retrieval_counts = {
        str(turn): {
            "domain": episodes[
                next(
                    episode_id
                    for episode_id, episode in episodes.items()
                    if int(episode["turn_number"]) == turn
                )
            ]["ground_truth_domain"],
            "retrieval_count": episodes[
                next(
                    episode_id
                    for episode_id, episode in episodes.items()
                    if int(episode["turn_number"]) == turn
                )
            ]["retrieval_count"],
        }
        for turn in plant_turns
    }
    return (
        {
            "turn_count": len(rows),
            "turns_with_k_candidates": sum(
                int(row["k_candidate_count"]) > 0 for row in rows
            ),
            "total_k_candidates": sum(
                int(row["k_candidate_count"]) for row in rows
            ),
            "turns_with_k_only_delivery": sum(
                int(row["k_only_delivered_count"]) > 0 for row in rows
            ),
            "total_k_only_delivered": sum(
                int(row["k_only_delivered_count"]) for row in rows
            ),
            "total_skipped_k": sum(
                len(row["skipped_k_ids"]) for row in rows
            ),
            "plant_retrieval_counts": plant_retrieval_counts,
            "top_retrieval_counts": sorted(
                (
                    {
                        "source_turn": int(episode["turn_number"]),
                        "domain": episode["ground_truth_domain"],
                        "retrieval_count": int(episode["retrieval_count"]),
                    }
                    for episode in episodes.values()
                ),
                key=lambda item: (
                    -item["retrieval_count"],
                    item["source_turn"],
                ),
            )[:25],
        },
        composition_rows,
        probe_selection_rows,
    )


def n_order_contract_analysis() -> dict:
    now = datetime.now(timezone.utc)
    episodes = [
        {
            "id": "old",
            "turn_number": 1,
            "last_retrieved_at": (now - timedelta(hours=10)).isoformat(),
        },
        {
            "id": "new",
            "turn_number": 2,
            "last_retrieved_at": (now - timedelta(hours=1)).isoformat(),
        },
        {
            "id": "never",
            "turn_number": 3,
            "last_retrieved_at": None,
        },
    ]
    calibration_last_generation = {"old": 1, "new": 2}
    calibration_order = [
        episode["id"]
        for episode in sorted(
            episodes,
            key=lambda episode: _calibration_n_key(
                episode,
                calibration_last_generation,
            ),
        )
    ]
    # Preserve the implementation that produced the sealed invalid run even
    # after the corrected engine replaces its wall-clock ranking.
    production_scores = {
        "old": math.exp(-0.1 * 10),
        "new": math.exp(-0.1 * 1),
        "never": 1.0,
    }
    production_order = sorted(
        production_scores,
        key=lambda episode_id: production_scores[episode_id],
        reverse=True,
    )
    return {
        "registered_calibration_semantics": (
            "unretrieved first, then least-recently retrieved generation"
        ),
        "calibration_order": calibration_order,
        "production_order": production_order,
        "production_decay_scores": production_scores,
        "orders_match": calibration_order == production_order,
        "finding": (
            "MATCH"
            if calibration_order == production_order
            else "DIVERGENCE_PRODUCTION_REINFORCES_RECENT_RETRIEVAL"
        ),
        "calibrator_source_sha256": (
            "221e0d0a687b65d2f34bb4c99e637bccfde909e0ee3f49b4974065c60ed90d51"
        ),
        "engine_source_sha256": (
            "68a0c9578c8355dc6dd4bd4834c6d00e8b90430cbc6251f96eb1a16a3bcee0ac"
        ),
    }


def _load_answers(root: Path) -> dict[int, str]:
    return {
        int(row["turn_number"]): str(row["assistant_message"])
        for row in read_jsonl(root / "logs" / "turns.jsonl")
    }


def fact_delivery_analysis() -> tuple[list[dict], list[dict], list[dict]]:
    answers = {
        arm: _load_answers(root)
        for arm, (root, _extractor) in ARM_CONFIG.items()
    }
    targeted_rows = []
    for question, (turn, needles) in TARGETED_ITEMS.items():
        for arm in ("T6", "S", "L"):
            payload = normalize(_retrieval_payload(arm, turn))
            for needle in needles:
                targeted_rows.append(
                    {
                        "arm": arm,
                        "question": question,
                        "turn": turn,
                        "item": needle,
                        "in_retrieval_payload": needle in payload,
                    }
                )

    breadth_rows = []
    for arm in ("T6", "S", "L"):
        for question, turn in (("Q11", 120), ("Q14", 121)):
            payload = normalize(_retrieval_payload(arm, turn))
            answer = normalize(answers[arm][turn])
            for domain, item, needle, plant_turns in ATOMIC_ITEMS:
                in_payload = needle in payload
                in_answer = needle in answer
                status = (
                    "recalled"
                    if in_payload and in_answer
                    else (
                        "unused"
                        if in_payload
                        else ("invented" if in_answer else "absent")
                    )
                )
                breadth_rows.append(
                    {
                        "arm": arm,
                        "question": question,
                        "turn": turn,
                        "domain": domain,
                        "item": item,
                        "plant_turns": ";".join(
                            str(value) for value in plant_turns
                        ),
                        "in_retrieval_payload": in_payload,
                        "in_answer": in_answer,
                        "status": status,
                    }
                )

    context_rows = {
        int(row["turn_number"]): row
        for row in read_jsonl(RUN_ROOT / "logs" / "context_match.jsonl")
    }
    with sqlite3.connect(RUN_ROOT / "study.db") as connection:
        connection.row_factory = sqlite3.Row
        episodes = {
            str(row["id"]): dict(row)
            for row in connection.execute(
                "SELECT id, turn_number, ground_truth_domain, user_message, "
                "assistant_message FROM episodes"
            )
        }
    origin_rows = []
    for question, turn in (("Q11", 120), ("Q14", 121)):
        selected = [
            episodes[str(episode_id)]
            for episode_id in context_rows[turn]["selected_ids"]
        ]
        for domain, item, needle, plant_turns in ATOMIC_ITEMS:
            matching = [
                episode
                for episode in selected
                if needle
                in normalize(
                    f"{episode['user_message']}\n"
                    f"{episode['assistant_message']}"
                )
            ]
            source_turns = sorted(
                {int(episode["turn_number"]) for episode in matching}
            )
            origin_rows.append(
                {
                    "question": question,
                    "turn": turn,
                    "domain": domain,
                    "item": item,
                    "matching_source_turns": ";".join(
                        str(value) for value in source_turns
                    ),
                    "matching_source_domains": ";".join(
                        sorted(
                            {
                                str(episode["ground_truth_domain"])
                                for episode in matching
                            }
                        )
                    ),
                    "registered_plant_turn_selected": any(
                        source_turn in plant_turns
                        for source_turn in source_turns
                    ),
                    "probe_derived_only": bool(source_turns)
                    and all(source_turn >= 112 for source_turn in source_turns),
                }
            )
    return targeted_rows, breadth_rows, origin_rows


def score_comparison() -> tuple[dict, list[dict]]:
    tier6 = json.loads(TIER6_SCORE.read_text(encoding="utf-8"))
    arm_s = json.loads(ARM_S_SCORE.read_text(encoding="utf-8"))
    arm_l = json.loads(ARM_L_SCORE.read_text(encoding="utf-8"))
    rows = []
    for number in range(1, 15):
        question = f"Q{number}"
        rows.append(
            {
                "question": question,
                "T6": float(tier6["scores"][question]["primary"])
                if question != "Q14"
                else float(tier6["q14_primary"]),
                "S": float(arm_s["items"][question]["corrected"]),
                "L": float(arm_l["items"][question]["corrected"]),
            }
        )
    for row in rows:
        row["T6_minus_S"] = row["T6"] - row["S"]
        row["T6_minus_L"] = row["T6"] - row["L"]
    q1_q13 = [row for row in rows if row["question"] != "Q14"]
    return (
        {
            "T6_Q1_Q13": sum(row["T6"] for row in q1_q13),
            "S_Q1_Q13": sum(row["S"] for row in q1_q13),
            "L_Q1_Q13": sum(row["L"] for row in q1_q13),
            "T6_Q14": rows[-1]["T6"],
            "S_Q14": rows[-1]["S"],
            "L_Q14": rows[-1]["L"],
            "T6_losses_vs_S": [
                row["question"]
                for row in q1_q13
                if row["T6_minus_S"] < 0
            ],
            "T6_gains_vs_S": [
                row["question"]
                for row in rows
                if row["T6_minus_S"] > 0
            ],
        },
        rows,
    )


def runtime_analysis() -> dict:
    turns = read_jsonl(RUN_ROOT / "logs" / "turns.jsonl")
    runtime_audit = json.loads(
        (RUN_ROOT / "runtime_audit.json").read_text(encoding="utf-8")
    )
    max_context = max(turns, key=lambda row: int(row["estimated_tokens"]))
    return {
        "turn_count": len(turns),
        "maximum_estimated_tokens": int(max_context["estimated_tokens"]),
        "maximum_context_turn": int(max_context["turn_number"]),
        "turn_120_estimated_tokens": int(turns[119]["estimated_tokens"]),
        "turn_121_estimated_tokens": int(turns[120]["estimated_tokens"]),
        "context_monitor_limit_tokens": 40_000,
        "empty_answer_count": sum(
            not str(row["assistant_message"]).strip() for row in turns
        ),
        "responses_at_2048_token_budget": sum(
            int(row["output_tokens"] or 0) >= 2048 for row in turns
        ),
        "maximum_output_tokens": max(
            int(row["output_tokens"] or 0) for row in turns
        ),
        "final_rule_store_count": int(turns[-1]["rule_store_count"]),
        "maximum_rule_store_count": max(
            int(row["rule_store_count"]) for row in turns
        ),
        "final_rule_token_estimate": int(turns[-1]["rule_token_estimate"]),
        "final_topic_count": int(turns[-1]["topic_count"]),
        "forbidden_modules_loaded": runtime_audit["forbidden_modules_loaded"],
    }


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _summarize_delivery(
    rows: list[dict],
    *,
    arm: str,
    question: str,
) -> dict:
    selected = [
        row
        for row in rows
        if row["arm"] == arm and row["question"] == question
    ]
    return {
        "delivered": sum(bool(row["in_retrieval_payload"]) for row in selected),
        "recalled": sum(row["status"] == "recalled" for row in selected),
        "unused": sum(row["status"] == "unused" for row in selected),
        "invented": sum(row["status"] == "invented" for row in selected),
        "absent": sum(row["status"] == "absent" for row in selected),
    }


def _targeted_count(
    rows: list[dict],
    *,
    arm: str,
    question: str,
) -> tuple[int, int]:
    selected = [
        row
        for row in rows
        if row["arm"] == arm and row["question"] == question
    ]
    return (
        sum(bool(row["in_retrieval_payload"]) for row in selected),
        len(selected),
    )


def _report(
    *,
    seal: dict,
    context_match: dict,
    composition: dict,
    n_order: dict,
    targeted_rows: list[dict],
    breadth_rows: list[dict],
    origin_rows: list[dict],
    scores: dict,
    runtime: dict,
) -> str:
    calibration = context_match["registered_gate_window_92_111"]
    probes = context_match["observational_probe_window_112_121"]
    lines = [
        "# Tier 6 121-Turn Mechanism Evaluation",
        "",
        f"**Blinded score commit:** `{SCORE_COMMIT}`  ",
        f"**Arm-mapping commit:** `{MAPPING_COMMIT}`  ",
        f"**Sequencing amendment:** `{SEQUENCING_AMENDMENT_COMMIT}`  ",
        f"**Sealed mechanism artifact commit:** `{MECHANISM_ARTIFACT_COMMIT}`",
        "",
        "## Verdict",
        "",
        "The observed 6.5/13.0 score is preserved, but it is **not valid evidence "
        "that a correctly widened STM arm stalls below Study 009 Arm L**. The "
        "live N ordering diverged from the ordering committed for calibration. "
        "That divergence locked the payload onto early civil episodes and "
        "starved K, so the run tested character volume under a different "
        "selection process.",
        "",
        "**Recommendation: do not run the 1,000-turn extension with this "
        "implementation.** First decide whether to authorize a corrected "
        "121-turn rerun whose live N order is mechanically proven identical to "
        "the registered calibration order. No 1,000-turn implementation or "
        "inference is authorized by this report.",
        "",
        "## Character Match",
        "",
        "| Window | Live median | Arm L median | MAE | Max error | Median APE | <=5% |",
        "|---|---:|---:|---:|---:|---:|---:|",
        (
            f"| Turns 92-111 (registered gate) | "
            f"{calibration['live_median']:,} | "
            f"{calibration['target_median']:,} | "
            f"{calibration['mean_absolute_error']:,.1f} | "
            f"{calibration['maximum_absolute_error']:,} | "
            f"{calibration['median_absolute_percentage_error']:.2%} | "
            f"{calibration['turns_within_5_percent']}/"
            f"{calibration['turn_count']} |"
        ),
        (
            f"| Turns 112-121 (observational) | "
            f"{probes['live_median']:,} | "
            f"{probes['target_median']:,} | "
            f"{probes['mean_absolute_error']:,.1f} | "
            f"{probes['maximum_absolute_error']:,} | "
            f"{probes['median_absolute_percentage_error']:.2%} | "
            f"{probes['turns_within_5_percent']}/{probes['turn_count']} |"
        ),
        "",
        "The registered volume gate genuinely passed. This is precisely why "
        "character count is insufficient as a surrogate for useful delivery: "
        "the resource amount matched while its allocation collapsed.",
        "",
        "## Ordering Divergence",
        "",
        f"- Registered/calibration toy order: "
        f"`{' -> '.join(n_order['calibration_order'])}`.",
        f"- Production toy order: "
        f"`{' -> '.join(n_order['production_order'])}`.",
        f"- Contract result: **{n_order['finding']}**.",
        (
            f"- K found {composition['total_k_candidates']} candidates on "
            f"{composition['turns_with_k_candidates']} turns, but delivered "
            f"{composition['total_k_only_delivered']} K-only episodes on "
            f"{composition['turns_with_k_only_delivery']} turns."
        ),
        "- Source turns 1-18 were retrieved 103-120 times each; the registered "
        "art, monetary, and marine plant turns were each retrieved only once.",
        "",
        "The calibrator orders unretrieved episodes first and then the least "
        "recent retrieval generation. The live engine sorts an exponentially "
        "decayed elapsed-time score in descending order, placing newly retrieved "
        "episodes ahead of older retrieved episodes. Rewriting retrieval "
        "timestamps after each turn therefore reinforces the same early set.",
        "",
        "## Targeted Delivery",
        "",
        "| Question | T6 | Study 009 S | Study 009 L |",
        "|---|---:|---:|---:|",
    ]
    for question in TARGETED_ITEMS:
        t6 = _targeted_count(targeted_rows, arm="T6", question=question)
        arm_s = _targeted_count(targeted_rows, arm="S", question=question)
        arm_l = _targeted_count(targeted_rows, arm="L", question=question)
        lines.append(
            f"| {question} | {t6[0]}/{t6[1]} | "
            f"{arm_s[0]}/{arm_s[1]} | {arm_l[0]}/{arm_l[1]} |"
        )
    lines.extend(
        [
            "",
            "Relative to corrected Study 009 S, widened STM lost Q4, Q6, and "
            "Q7, totaling 2.5 points. Those are exactly the probes where S "
            "delivered the required source facts and T6 delivered none. This "
            "is retrieval displacement, not a context-capacity or scorer effect.",
            "",
            "## Breadth Delivery And Use",
            "",
            "| Arm | Probe | Delivered / 17 | Recalled | Unused | Invented | Absent |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for arm in ("T6", "S", "L"):
        for question in ("Q11", "Q14"):
            summary = _summarize_delivery(
                breadth_rows,
                arm=arm,
                question=question,
            )
            lines.append(
                f"| {arm} | {question} | {summary['delivered']} | "
                f"{summary['recalled']} | {summary['unused']} | "
                f"{summary['invented']} | {summary['absent']} |"
            )
    t6_q11_origins = [
        row
        for row in origin_rows
        if row["question"] == "Q11" and row["matching_source_turns"]
    ]
    original_source_count = sum(
        bool(row["registered_plant_turn_selected"])
        for row in t6_q11_origins
    )
    probe_only_count = sum(
        bool(row["probe_derived_only"]) for row in t6_q11_origins
    )
    lines.extend(
        [
            "",
            "T6 used every atomic item it received at Q11 (7/7), with no "
            "atomic invention. Only "
            f"{original_source_count} of those seven items had their registered "
            "plant source selected; "
            f"{probe_only_count} were available only through earlier probe "
            "answers. At Q14 it used 4/7 delivered atoms. The model generally "
            "used available evidence; missing source delivery was the binding "
            "failure.",
            "",
            "At Q11 the 25 delivered episodes comprised 19 civil episodes, one "
            "generic art episode, and five prior probes. No original monetary "
            "or marine episode was present. Similarity found the turn-100 marine "
            "plant at Q7 and Q8, but N-first packing skipped it after the cap "
            "was consumed.",
            "",
            "## Non-Causes",
            "",
            f"- Maximum estimated context was "
            f"{runtime['maximum_estimated_tokens']:,} tokens at turn "
            f"{runtime['maximum_context_turn']}, below the 40,000-token monitor.",
            f"- Empty responses: {runtime['empty_answer_count']}; responses at "
            f"the 2,048-token budget: {runtime['responses_at_2048_token_budget']}.",
            f"- One pinned rule remained at "
            f"{runtime['final_rule_token_estimate']} estimated tokens; Q3, Q12, "
            "and Q13 all scored full credit.",
            f"- Forbidden memory-tier modules loaded: "
            f"{len(runtime['forbidden_modules_loaded'])}.",
            f"- Mechanism seal verification: **{seal['status']}**, "
            f"{seal['mechanism_file_count']} files, aggregate "
            f"`{seal['aggregate_sha256']}`.",
            "",
            "## Interpretation",
            "",
            "The run establishes a narrower negative result: adding volume to "
            "this live most-recently-retrieved/N-first implementation made pure "
            "STM worse than the corrected Study 009 S baseline (6.5 versus "
            "9.0), because extra N displaced useful K. It does not distinguish "
            "whether LTM's 12.0 advantage comes from the tier itself or from "
            "the diverse selection behavior that the registered widened-STM "
            "calibration intended but the live engine did not execute.",
            "",
            "A 1,000-turn run would magnify the same lock-in and cannot serve "
            "as the planned confirmation. The economical next step, if the "
            "owner wants further evidence, is one corrected 121-turn rerun with "
            "an exact offline/live N-order equivalence gate and otherwise "
            "unchanged score threshold, seed, script, budget, and scorer.",
            "",
        ]
    )
    return "\n".join(lines)


def _corrected_report(
    *,
    seal: dict,
    context_match: dict,
    composition: dict,
    n_order: dict,
    targeted_rows: list[dict],
    breadth_rows: list[dict],
    scores: dict,
    runtime: dict,
) -> str:
    targeted_losses = [
        question
        for question in scores["T6_losses_vs_S"]
        if question != "Q11"
    ]
    lines = [
        "# Tier 6 Corrected 121-Turn Mechanism Evaluation",
        "",
        f"**Blinded score commit:** `{SCORE_COMMIT}`  ",
        f"**Arm-mapping commit:** `{MAPPING_COMMIT}`  ",
        f"**Run:** `{RUN_ID}`",
        "",
        "## Outcome",
        "",
        f"The corrected widened-STM arm scored "
        f"**{scores['T6_Q1_Q13']:.1f}/13** with "
        f"**Q14 = {scores['T6_Q14']:.1f}**. Study 009 Arm S scored "
        f"{scores['S_Q1_Q13']:.1f}/13 and Arm L scored "
        f"{scores['L_Q1_Q13']:.1f}/13. Widening recovered "
        f"{scores['T6_Q1_Q13'] - scores['S_Q1_Q13']:.1f} points over S "
        "but remained one point below L.",
        "",
        f"The registered character-match gate remained "
        f"**{context_match['registered_gate_status']}**. The corrected "
        f"offline/live N-order equivalence gate was **{n_order['status']}**. "
        f"The run completed {runtime['turn_count']} turns with "
        f"{runtime['empty_answer_count']} empty answers and "
        f"{runtime['responses_at_2048_token_budget']} responses at the output "
        "limit.",
        "",
        "## Score Pattern",
        "",
        f"Relative to Study 009 S, the corrected arm lost on "
        f"{', '.join(scores['T6_losses_vs_S']) or 'no questions'} and gained "
        f"on {', '.join(scores['T6_gains_vs_S']) or 'no questions'}. "
        f"The targeted non-breadth losses were "
        f"{', '.join(targeted_losses) or 'none'}.",
        "",
        "The result rejects the simple claim that LTM's 12.0 was only a "
        "consequence of greater delivered character volume: matching that "
        "volume improved STM from 9.0 to 11.0, but did not reproduce LTM. "
        "Volume explains part, not all, of the observed advantage. This is "
        "consistent with relevance and selection policy still contributing.",
        "",
        "## Decision",
        "",
        "The registered score rule marks the 1,000-turn confirmation as "
        "eligible because the corrected score is below 12.0. It is not "
        "launched here: owner authorization explicitly requires reviewing "
        "this 121-turn result before committing that compute.",
        "",
        "## Integrity",
        "",
        f"Mechanism seal verification: **{seal['status']}**, "
        f"{seal['mechanism_file_count']} files, aggregate "
        f"`{seal['aggregate_sha256']}`. The preserved invalid 6.5 run remains "
        "diagnostic-only and was neither deleted nor used for the architectural "
        "conclusion.",
        "",
    ]
    return "\n".join(lines)


def generate_analysis(
    output_root: Path = OUTPUT_ROOT,
    *,
    refuse_existing: bool = True,
) -> dict:
    if refuse_existing and output_root.exists():
        raise FileExistsError(
            f"Refusing to overwrite analysis artifacts: {output_root}"
        )
    output_root.mkdir(parents=True, exist_ok=True)

    seal = verify_mechanism_seal()
    if seal["status"] != "PASS":
        raise RuntimeError("Tier 6 mechanism seal verification failed")
    context_match, probe_match_rows = context_match_analysis()
    composition, composition_rows, probe_selection_rows = (
        retrieval_composition_analysis()
    )
    if RUN_ID == "tier6_live_121":
        n_order = n_order_contract_analysis()
    else:
        equivalence = json.loads(
            (
                TIER6_ROOT
                / "equivalence_gate_corrected"
                / "equivalence_gate.json"
            ).read_text(encoding="utf-8")
        )
        n_order = {
            "status": equivalence["status"],
            "source": "equivalence_gate_corrected/equivalence_gate.json",
            "turns_compared": equivalence["turn_count"],
            "offline_live_n_order_exact": equivalence["all_turns_exact"],
        }
    targeted_rows, breadth_rows, origin_rows = fact_delivery_analysis()
    scores, score_rows = score_comparison()
    runtime = runtime_analysis()

    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    selected = settings["selected"]
    calibration_k_only = {
        "turns_with_k_only_delivery": sum(
            int(value) > 0 for value in selected["delivered_k_only_counts"]
        ),
        "total_k_only_delivered": sum(
            int(value) for value in selected["delivered_k_only_counts"]
        ),
    }

    _write_json(output_root / "seal_verification.json", seal)
    _write_json(output_root / "context_match_summary.json", context_match)
    _write_csv(output_root / "probe_context_match.csv", probe_match_rows)
    _write_json(
        output_root / "retrieval_composition_summary.json",
        {
            **composition,
            "calibration_selected_cell_k_only": calibration_k_only,
        },
    )
    _write_csv(
        output_root / "breadth_context_composition.csv",
        composition_rows,
    )
    _write_csv(
        output_root / "probe_selection_composition.csv",
        probe_selection_rows,
    )
    _write_json(output_root / "n_order_contract.json", n_order)
    _write_csv(output_root / "targeted_fact_delivery.csv", targeted_rows)
    _write_csv(output_root / "breadth_fact_delivery.csv", breadth_rows)
    _write_csv(output_root / "t6_breadth_fact_origins.csv", origin_rows)
    _write_json(output_root / "score_comparison_summary.json", scores)
    _write_csv(output_root / "score_comparison.csv", score_rows)
    _write_json(output_root / "runtime_summary.json", runtime)

    if RUN_ID == "tier6_live_121":
        report = _report(
            seal=seal,
            context_match=context_match,
            composition=composition,
            n_order=n_order,
            targeted_rows=targeted_rows,
            breadth_rows=breadth_rows,
            origin_rows=origin_rows,
            scores=scores,
            runtime=runtime,
        )
    else:
        report = _corrected_report(
            seal=seal,
            context_match=context_match,
            composition=composition,
            n_order=n_order,
            targeted_rows=targeted_rows,
            breadth_rows=breadth_rows,
            scores=scores,
            runtime=runtime,
        )
    report_path = output_root / "tier6_121_mechanism_evaluation.md"
    report_path.write_text(
        report,
        encoding="utf-8",
        newline="\n",
    )

    source_paths = {
        "mechanism_seal": RUN_ROOT / "mechanism_seal.json",
        "context_match_log": RUN_ROOT / "logs" / "context_match.jsonl",
        "turn_log": RUN_ROOT / "logs" / "turns.jsonl",
        "study_database": RUN_ROOT / "study.db",
        "tier6_score": TIER6_SCORE,
        "study009_s_score": ARM_S_SCORE,
        "study009_l_score": ARM_L_SCORE,
        "settings": SETTINGS_PATH,
        "analysis_code": Path(__file__),
    }
    current_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    artifact_paths = sorted(
        path
        for path in output_root.iterdir()
        if path.is_file() and path.name != "analysis_manifest.json"
    )
    manifest = {
        "status": "COMPLETE",
        "classification": (
            "PROTOCOL_INVALID_FOR_ARCHITECTURAL_INFERENCE"
            if RUN_ID == "tier6_live_121"
            else "VALID_CORRECTED_121_RESULT"
        ),
        "recommendation": (
            "DO_NOT_RUN_1000_WITH_CURRENT_IMPLEMENTATION"
            if RUN_ID == "tier6_live_121"
            else "OWNER_REVIEW_BEFORE_OPTIONAL_1000_TURN_CONFIRMATION"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "code_commit": current_commit,
        "score_commit": SCORE_COMMIT,
        "mapping_commit": MAPPING_COMMIT,
        "sequencing_amendment_commit": SEQUENCING_AMENDMENT_COMMIT,
        "mechanism_artifact_commit": MECHANISM_ARTIFACT_COMMIT,
        "source_hashes": {
            name: sha256(path) for name, path in source_paths.items()
        },
        "artifact_hashes": {
            path.name: sha256(path) for path in artifact_paths
        },
    }
    _write_json(output_root / "analysis_manifest.json", manifest)
    return manifest

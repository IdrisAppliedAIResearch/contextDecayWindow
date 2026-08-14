"""Synthesize NF-002/003's strict three-arm comparison from frozen artifacts."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

AUDIT = Path(
    "experiments/components/biological_memory/nf_003/artifacts/"
    "surrogate_audit.json"
)
PART1 = Path(
    "experiments/components/biological_memory/nf_003/artifacts/part1_record.json"
)
OUTPUT = Path(
    "experiments/components/biological_memory/nf_003/artifacts/"
    "three_arm_summary.json"
)
AUDIT_LF_SHA256 = "c71b7556b47397431aad01b5a1434d91af0fa9c2a27a3e51fb52ff478a619a5b"
PART1_LF_SHA256 = "2d29387251b109f780d7a2fe86e7a1d3244eb0f5a73515b1be1d8e7dda7e506f"


class ThreeArmSummaryError(RuntimeError):
    pass


def _lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _distribution(values: Iterable[int]) -> dict[str, int]:
    ordered = sorted(values)
    if not ordered:
        raise ThreeArmSummaryError("Cannot summarize an empty rank set")

    def nearest_rank(percentile: float) -> int:
        return ordered[math.ceil(percentile * len(ordered)) - 1]

    return {
        "n": len(ordered),
        "min": ordered[0],
        "p50": nearest_rank(0.50),
        "p90": nearest_rank(0.90),
        "max": ordered[-1],
    }


def summarize(repository_root: Path) -> dict[str, Any]:
    audit_path = repository_root / AUDIT
    part1_path = repository_root / PART1
    audit_sha = _lf_sha256(audit_path)
    part1_sha = _lf_sha256(part1_path)
    if audit_sha != AUDIT_LF_SHA256:
        raise ThreeArmSummaryError(f"Surrogate audit changed: {audit_sha}")
    if part1_sha != PART1_LF_SHA256:
        raise ThreeArmSummaryError(f"Part 1 artifact changed: {part1_sha}")

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    part1 = json.loads(part1_path.read_text(encoding="utf-8"))
    ranks = {row["question_id"]: row["best_evidence_rank"] for row in part1["rows"]}
    rows = audit["rows"]
    if set(ranks) != {row["question_id"] for row in rows}:
        raise ThreeArmSummaryError("The frozen artifacts do not cover identical items")

    def rank_group(predicate: Any) -> dict[str, int]:
        return _distribution(
            ranks[row["question_id"]] for row in rows if predicate(row)
        )

    whole = audit["nf002_strict_context"]
    fine = audit["strict_answer_episode_measure"]
    return {
        "schema": "nf003-three-arm-summary-v1",
        "inputs": {
            "surrogate_audit": {
                "path": AUDIT.as_posix(),
                "lf_sha256": audit_sha,
            },
            "part1_record": {
                "path": PART1.as_posix(),
                "lf_sha256": part1_sha,
            },
        },
        "population": audit["population"],
        "arms": [
            {
                "ranking_unit": "session",
                "packing_unit": "whole_session",
                "strict_delivery": whole["baseline_hits"],
            },
            {
                "ranking_unit": "session",
                "packing_unit": "episode",
                "strict_delivery": whole["treatment_hits"],
            },
            {
                "ranking_unit": "episode",
                "packing_unit": "episode",
                "strict_delivery": fine["treatment_hits"],
            },
        ],
        "one_factor_contrasts": {
            "pack_fine_at_session_rank": {
                "net": whole["treatment_hits"] - whole["baseline_hits"],
                **whole["paired"],
            },
            "rank_fine_at_episode_pack": {
                "net": fine["treatment_hits"] - fine["baseline_hits"],
                **fine["paired"],
            },
        },
        "own_cosine_rank_by_episode_pack_outcome": {
            "coarse_rank_rescues": rank_group(
                lambda row: row["baseline_answer_episode"]
                and not row["treatment_answer_episode"]
            ),
            "fine_rank_gains": rank_group(
                lambda row: not row["baseline_answer_episode"]
                and row["treatment_answer_episode"]
            ),
            "both_deliver": rank_group(
                lambda row: row["baseline_answer_episode"]
                and row["treatment_answer_episode"]
            ),
            "neither_delivers": rank_group(
                lambda row: not row["baseline_answer_episode"]
                and not row["treatment_answer_episode"]
            ),
        },
        "design_rule": "rank coarse, pack fine",
        "model_calls": 0,
        "embedding_calls": 0,
    }


def write(repository_root: Path) -> Path:
    output = repository_root / OUTPUT
    output.write_text(
        json.dumps(summarize(repository_root), indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output

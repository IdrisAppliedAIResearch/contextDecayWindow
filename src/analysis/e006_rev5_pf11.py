from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from src.analysis.e006_rev3_pf11 import (
    DATABASE,
    Q11_RANK_INVENTORY,
    Pf11Inputs,
    load_inputs,
    rank_indices,
    ranking_digest,
    reconstruct_query,
    sha256_file,
)
from src.analysis.e006_rev4_pf11 import vector_independence_audit
from src.analysis.e006_rev4_vector_reference import score_after_first_hits


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
)
DESIGN = COMPONENT_ROOT / "E006_PART2_REV5_chained_retrieval.md"
AUTHORIZATION = COMPONENT_ROOT / "E006_PART2_REV5_AUTHORIZATION.md"
VECTOR_REFERENCE = Path(__file__).with_name("e006_rev4_vector_reference.py")

DESIGN_SHA256 = "6a674682dd60370631caa834de43fe07e59f2e0683e2d0c435dfc1003cebe444"
AUTHORIZATION_SHA256 = (
    "031d98ffb8d16684bdc54bc5573ff6249c33cb11e318110de63d77b5369c2382"
)
DESIGN_COMMIT = "764396b2"
AUTHORIZATION_COMMIT = "ac81d8e1"
PER_STEP_COUNTS = (3, 5)
QUERY_WEIGHTS = (0.3, 0.5, 0.7)
CONTEXT_RETENTIONS = (0.5, 0.7)
SCORE_TOLERANCE = 1e-10


def registered_section2_scores(
    *,
    inputs: Pf11Inputs,
    hits: np.ndarray,
    query_weight: float,
    retention: float,
) -> tuple[np.ndarray, dict[str, float]]:
    context_episode_scores = inputs.query_cosines.copy()
    query_context = 1.0
    hit_mean_episode_scores = inputs.gram[hits].mean(axis=0)
    query_hit_mean = float(inputs.query_cosines[hits].mean())
    context_hit_mean = float(context_episode_scores[hits].mean())
    hit_mean_norm_squared = float(inputs.gram[np.ix_(hits, hits)].mean())
    reinstatement_weight = 1.0 - retention

    context_norm = np.sqrt(
        retention**2
        + reinstatement_weight**2 * hit_mean_norm_squared
        + 2.0 * retention * reinstatement_weight * context_hit_mean
    )
    context_episode_scores = (
        retention * context_episode_scores
        + reinstatement_weight * hit_mean_episode_scores
    ) / context_norm
    query_context = (
        retention * query_context + reinstatement_weight * query_hit_mean
    ) / context_norm

    context_weight = 1.0 - query_weight
    cue_norm = np.sqrt(
        query_weight**2
        + context_weight**2
        + 2.0 * query_weight * context_weight * query_context
    )
    scores = (
        query_weight * inputs.query_cosines
        + context_weight * context_episode_scores
    ) / cue_norm
    return scores, {
        "registered_context_norm": float(context_norm),
        "hit_mean_norm_squared": hit_mean_norm_squared,
    }


def evaluate_pf11(inputs: Pf11Inputs) -> dict[str, Any]:
    query, episodes, reconstruction = reconstruct_query(inputs)
    cells = []
    for per_step in PER_STEP_COUNTS:
        hits = np.arange(per_step, dtype=np.int64)
        for retention in CONTEXT_RETENTIONS:
            for query_weight in QUERY_WEIGHTS:
                vector_scores = score_after_first_hits(
                    query=query,
                    episodes=episodes,
                    hits=hits,
                    query_weight=query_weight,
                    retention=retention,
                )
                section2_scores, norm_evidence = registered_section2_scores(
                    inputs=inputs,
                    hits=hits,
                    query_weight=query_weight,
                    retention=retention,
                )
                vector_order = rank_indices(vector_scores, inputs.content_hashes)
                section2_order = rank_indices(
                    section2_scores, inputs.content_hashes
                )
                max_difference = float(
                    np.max(np.abs(vector_scores - section2_scores))
                )
                cells.append(
                    {
                        "m": per_step,
                        "RHO": retention,
                        "W_Q": query_weight,
                        "max_abs_score_difference": max_difference,
                        "score_tolerance_pass": max_difference < SCORE_TOLERANCE,
                        "full_ranking_equal": bool(
                            np.array_equal(vector_order, section2_order)
                        ),
                        "next_top_m_equal": bool(
                            np.array_equal(
                                vector_order[:per_step],
                                section2_order[:per_step],
                            )
                        ),
                        "vector_ranking_sha256": ranking_digest(
                            vector_order, inputs.content_hashes
                        ),
                        "section2_ranking_sha256": ranking_digest(
                            section2_order, inputs.content_hashes
                        ),
                        **norm_evidence,
                    }
                )

    passes = all(
        cell["score_tolerance_pass"]
        and cell["full_ranking_equal"]
        and cell["next_top_m_equal"]
        for cell in cells
    )
    return {
        "status": "PASS" if passes else "FAIL",
        "registered_tolerance": {
            "maximum_absolute_score_difference_strictly_less_than": (
                SCORE_TOLERANCE
            ),
            "identical_full_rankings": True,
            "identical_next_top_m": True,
            "required_cell_count": 12,
        },
        "comparison_key": "episode_content_sha256",
        "cell_count": len(cells),
        "score_tolerance_pass_count": sum(
            cell["score_tolerance_pass"] for cell in cells
        ),
        "full_ranking_equal_count": sum(
            cell["full_ranking_equal"] for cell in cells
        ),
        "next_top_m_equal_count": sum(
            cell["next_top_m_equal"] for cell in cells
        ),
        "max_abs_score_difference": max(
            cell["max_abs_score_difference"] for cell in cells
        ),
        "hit_mean_norm_squared_by_m": {
            str(per_step): next(
                cell["hit_mean_norm_squared"]
                for cell in cells
                if cell["m"] == per_step
            )
            for per_step in PER_STEP_COUNTS
        },
        "reconstruction": reconstruction,
        "cells": cells,
    }


def leakage_audit() -> dict[str, Any]:
    sources = (Path(__file__), VECTOR_REFERENCE)
    forbidden = (
        "q_" + "facts_key",
        "rub" + "ric",
        "ATOMIC_" + "ITEMS",
        "TARGETED_" + "ITEMS",
    )
    found = {
        path.relative_to(REPO_ROOT).as_posix(): [
            token
            for token in forbidden
            if token in path.read_text(encoding="utf-8")
        ]
        for path in sources
    }
    found = {path: tokens for path, tokens in found.items() if tokens}
    return {
        "status": "PASS" if not found else "FAIL",
        "audited_paths": [
            path.relative_to(REPO_ROOT).as_posix() for path in sources
        ],
        "found": found,
        "note": (
            "Selection code reads identities, turns, cosines, and vectors only; "
            "fact-bearing columns are not retained."
        ),
    }


def git_ordering() -> dict[str, str]:
    def run(*args: str) -> str:
        return subprocess.check_output(
            ("git", *args), cwd=REPO_ROOT, text=True
        ).strip()

    design = run("rev-parse", DESIGN_COMMIT)
    authorization = run("rev-parse", AUTHORIZATION_COMMIT)
    subprocess.check_call(
        ("git", "merge-base", "--is-ancestor", design, authorization),
        cwd=REPO_ROOT,
    )
    subprocess.check_call(
        ("git", "merge-base", "--is-ancestor", authorization, "HEAD"),
        cwd=REPO_ROOT,
    )
    return {
        "status": "PASS",
        "design_commit": design,
        "authorization_commit": authorization,
        "head_at_execution": run("rev-parse", "HEAD"),
    }


def input_inventory() -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in (
            DESIGN,
            AUTHORIZATION,
            DATABASE,
            Q11_RANK_INVENTORY,
            VECTOR_REFERENCE,
        )
    ]


def build_report() -> dict[str, Any]:
    if sha256_file(DESIGN) != DESIGN_SHA256:
        raise AssertionError("Rev 5 design anchor digest changed")
    if sha256_file(AUTHORIZATION) != AUTHORIZATION_SHA256:
        raise AssertionError("Rev 5 authorization digest changed")
    independence = vector_independence_audit()
    if independence["status"] != "PASS":
        raise AssertionError("PF11 vector-route independence audit failed")
    leakage = leakage_audit()
    if leakage["status"] != "PASS":
        raise AssertionError("PF11 leakage audit failed")
    inputs = load_inputs()
    pf11 = evaluate_pf11(inputs)
    return {
        "study": "E006 Part 2 Rev 5 chained retrieval",
        "stage": "PF11 computability verification",
        "status": pf11["status"],
        "decision": (
            "CONTINUE_PREFLIGHT"
            if pf11["status"] == "PASS"
            else "STOP_BEFORE_REMAINING_PREFLIGHT"
        ),
        "design_sha256": DESIGN_SHA256,
        "authorization_sha256": AUTHORIZATION_SHA256,
        "zero_model_calls": True,
        "zero_embedding_calls": True,
        "execution": {
            "launch_command": (
                ".venv/Scripts/python.exe -m src.analysis.e006_rev5_pf11 "
                "experiments/components/retrieval_mechanism_ledger/artifacts/"
                "e006_rev5_pf11/pf11.json"
            ),
            "auditor_source_sha256": sha256_file(Path(__file__)),
            "text_encoding": "UTF-8",
        },
        "gate_ordering": git_ordering(),
        "vector_route_independence": independence,
        "leakage_audit": leakage,
        "input_inventory": input_inventory(),
        "input_counts": {
            "q11_cosine_rows": len(inputs.ids),
            "eligible_episode_vectors": len(inputs.ids),
            "embedding_dimension": int(inputs.episode_vectors.shape[1]),
            "gram_shape": list(inputs.gram.shape),
        },
        "pf11": pf11,
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run E006 Rev 5 PF11")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    result = build_report()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    print(json.dumps({"status": result["status"], "output": str(output)}))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

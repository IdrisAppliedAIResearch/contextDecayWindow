from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
)
RUN_ROOT = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier6"
    / "runs"
    / "tier6_live_121_corrected_001"
    / "context_matched_stm"
)

DESIGN = COMPONENT_ROOT / "E006_PART2_REV3_chained_retrieval.md"
AUTHORIZATION = COMPONENT_ROOT / "E006_PART2_REV3_AUTHORIZATION.md"
DATABASE = RUN_ROOT / "study.db"
Q11_RANK_INVENTORY = (
    COMPONENT_ROOT / "artifacts" / "rd001" / "full_rank_inventory.csv"
)

DESIGN_SHA256 = "1a41013c3a079dd0bedd80307d4f6b699139f889cd705457e1d874bb3d24b325"
AUTHORIZATION_SHA256 = (
    "a2a9d335bd271558e67694894f15db176c1175e334f81b71972653d44ea4b591"
)
DESIGN_COMMIT = "42f710a3"
AUTHORIZATION_COMMIT = "38bdd153"
PER_STEP_COUNTS = (3, 5)
QUERY_WEIGHTS = (0.3, 0.5, 0.7)
CONTEXT_RETENTIONS = (0.5, 0.7)


@dataclass(frozen=True)
class Pf11Inputs:
    ids: tuple[str, ...]
    turns: np.ndarray
    content_hashes: tuple[str, ...]
    query_cosines: np.ndarray
    episode_vectors: np.ndarray
    gram: np.ndarray


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_sha256(episode: dict[str, Any]) -> str:
    stable = {
        "assistant_message": str(episode["assistant_message"]),
        "turn_number": int(episode["turn_number"]),
        "user_message": str(episode["user_message"]),
    }
    encoded = json.dumps(
        stable,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_inputs() -> Pf11Inputs:
    with Q11_RANK_INVENTORY.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [
            {
                "episode_id": str(row["episode_id"]),
                "source_turn": int(row["source_turn"]),
                "cosine": float(row["cosine"]),
            }
            for row in reader
        ]
    if len(rows) != 119:
        raise AssertionError("Q11 cosine trace must contain 119 eligible episodes")

    with sqlite3.connect(DATABASE) as connection:
        db_rows = connection.execute(
            """
            SELECT id, turn_number, user_message, assistant_message, embedding
            FROM episodes
            WHERE turn_number < 120
            ORDER BY turn_number, id
            """
        ).fetchall()
    by_id = {
        str(row[0]): {
            "id": str(row[0]),
            "turn_number": int(row[1]),
            "user_message": str(row[2]),
            "assistant_message": str(row[3]),
            "embedding": row[4],
        }
        for row in db_rows
    }
    ids = tuple(row["episode_id"] for row in rows)
    if set(ids) != set(by_id):
        raise AssertionError("Q11 trace identities differ from eligible store rows")
    turns = np.array([int(row["source_turn"]) for row in rows], dtype=np.int64)
    if not np.array_equal(
        turns,
        np.array([by_id[value]["turn_number"] for value in ids]),
    ):
        raise AssertionError("Q11 trace source turns differ from the store")

    vectors = np.stack(
        [
            np.frombuffer(by_id[value]["embedding"], dtype=np.float32).astype(
                np.float64
            )
            for value in ids
        ]
    )
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if np.any(norms == 0.0):
        raise AssertionError("Eligible store contains a zero episode vector")
    vectors /= norms
    gram = vectors @ vectors.T
    return Pf11Inputs(
        ids=ids,
        turns=turns,
        content_hashes=tuple(content_sha256(by_id[value]) for value in ids),
        query_cosines=np.array([row["cosine"] for row in rows], dtype=np.float64),
        episode_vectors=vectors,
        gram=gram,
    )


def reconstruct_query(inputs: Pf11Inputs) -> tuple[np.ndarray, np.ndarray, dict]:
    coefficients = np.linalg.lstsq(
        inputs.gram,
        inputs.query_cosines,
        rcond=None,
    )[0]
    projected = coefficients @ inputs.episode_vectors
    projection_norm2 = float(projected @ projected)
    residual_norm2 = 1.0 - projection_norm2
    if residual_norm2 < -1e-12:
        raise AssertionError("Committed Q11 cosines cannot belong to a unit query")
    residual_norm2 = max(0.0, residual_norm2)
    query = np.concatenate((projected, [np.sqrt(residual_norm2)]))
    episodes = np.pad(inputs.episode_vectors, ((0, 0), (0, 1)))
    fit_error = float(
        np.max(np.abs((episodes @ query) - inputs.query_cosines))
    )
    return query, episodes, {
        "projection_norm2": projection_norm2,
        "orthogonal_residual_norm2": residual_norm2,
        "unit_query_norm": float(np.linalg.norm(query)),
        "max_abs_committed_cosine_fit_error": fit_error,
    }


def direct_mechanism_scores(
    *,
    query: np.ndarray,
    episodes: np.ndarray,
    hits: np.ndarray,
    query_weight: float,
    retention: float,
) -> np.ndarray:
    reinstated = episodes[hits].mean(axis=0)
    context = retention * query + (1.0 - retention) * reinstated
    context /= np.linalg.norm(context)
    cue = query_weight * query + (1.0 - query_weight) * context
    cue /= np.linalg.norm(cue)
    return episodes @ cue


def registered_derivation_scores(
    *,
    inputs: Pf11Inputs,
    hits: np.ndarray,
    query_weight: float,
) -> np.ndarray:
    context_episode_scores = inputs.gram[hits].mean(axis=0)
    query_context = float(inputs.query_cosines[hits].mean())
    context_weight = 1.0 - query_weight
    denominator = np.sqrt(
        query_weight**2
        + context_weight**2
        + 2.0 * query_weight * context_weight * query_context
    )
    return (
        query_weight * inputs.query_cosines
        + context_weight * context_episode_scores
    ) / denominator


def corrected_recurrence_scores(
    *,
    inputs: Pf11Inputs,
    hits: np.ndarray,
    query_weight: float,
    retention: float,
) -> np.ndarray:
    reinstated_scores = inputs.gram[hits].mean(axis=0)
    query_reinstated = float(inputs.query_cosines[hits].mean())
    reinstated_norm2 = float(inputs.gram[np.ix_(hits, hits)].mean())
    reinstatement_weight = 1.0 - retention
    context_norm = np.sqrt(
        retention**2
        + reinstatement_weight**2 * reinstated_norm2
        + 2.0 * retention * reinstatement_weight * query_reinstated
    )
    context_scores = (
        retention * inputs.query_cosines
        + reinstatement_weight * reinstated_scores
    ) / context_norm
    query_context = (
        retention + reinstatement_weight * query_reinstated
    ) / context_norm
    context_weight = 1.0 - query_weight
    cue_norm = np.sqrt(
        query_weight**2
        + context_weight**2
        + 2.0 * query_weight * context_weight * query_context
    )
    return (
        query_weight * inputs.query_cosines + context_weight * context_scores
    ) / cue_norm


def rank_indices(scores: np.ndarray, content_hashes: tuple[str, ...]) -> np.ndarray:
    return np.array(
        sorted(
            range(len(scores)),
            key=lambda index: (-float(scores[index]), content_hashes[index]),
        ),
        dtype=np.int64,
    )


def ranking_digest(order: np.ndarray, content_hashes: tuple[str, ...]) -> str:
    payload = "\n".join(content_hashes[int(index)] for index in order)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def evaluate_pf11(inputs: Pf11Inputs) -> dict[str, Any]:
    query, episodes, reconstruction = reconstruct_query(inputs)
    cells = []
    for per_step in PER_STEP_COUNTS:
        hits = np.arange(per_step, dtype=np.int64)
        for retention in CONTEXT_RETENTIONS:
            for query_weight in QUERY_WEIGHTS:
                direct = direct_mechanism_scores(
                    query=query,
                    episodes=episodes,
                    hits=hits,
                    query_weight=query_weight,
                    retention=retention,
                )
                registered = registered_derivation_scores(
                    inputs=inputs,
                    hits=hits,
                    query_weight=query_weight,
                )
                corrected = corrected_recurrence_scores(
                    inputs=inputs,
                    hits=hits,
                    query_weight=query_weight,
                    retention=retention,
                )
                direct_order = rank_indices(direct, inputs.content_hashes)
                registered_order = rank_indices(registered, inputs.content_hashes)
                corrected_order = rank_indices(corrected, inputs.content_hashes)
                cells.append(
                    {
                        "m": per_step,
                        "RHO": retention,
                        "W_Q": query_weight,
                        "registered_max_abs_score_difference": float(
                            np.max(np.abs(direct - registered))
                        ),
                        "registered_full_ranking_equal": bool(
                            np.array_equal(direct_order, registered_order)
                        ),
                        "registered_next_top_m_equal": bool(
                            np.array_equal(
                                direct_order[:per_step],
                                registered_order[:per_step],
                            )
                        ),
                        "direct_ranking_sha256": ranking_digest(
                            direct_order, inputs.content_hashes
                        ),
                        "registered_ranking_sha256": ranking_digest(
                            registered_order, inputs.content_hashes
                        ),
                        "corrected_max_abs_score_difference": float(
                            np.max(np.abs(direct - corrected))
                        ),
                        "corrected_full_ranking_equal": bool(
                            np.array_equal(direct_order, corrected_order)
                        ),
                    }
                )
    registered_agrees = all(
        cell["registered_max_abs_score_difference"] == 0.0
        and cell["registered_full_ranking_equal"]
        for cell in cells
    )
    return {
        "status": "PASS" if registered_agrees else "FAIL",
        "registered_claim": (
            "Section 2 scores from mean-hit products agree with the unchanged "
            "recursive mechanism."
        ),
        "reconstruction": reconstruction,
        "comparison_key": "episode_content_sha256",
        "cell_count": len(cells),
        "registered_full_ranking_equal_count": sum(
            cell["registered_full_ranking_equal"] for cell in cells
        ),
        "registered_next_top_m_equal_count": sum(
            cell["registered_next_top_m_equal"] for cell in cells
        ),
        "registered_max_abs_score_difference_range": [
            min(cell["registered_max_abs_score_difference"] for cell in cells),
            max(cell["registered_max_abs_score_difference"] for cell in cells),
        ],
        "corrected_recurrence_diagnostic": {
            "status": "AGREES_NOT_REGISTERED",
            "purpose": (
                "Localizes the failure to the registered derivation. It is not "
                "used to pass PF11 or authorize later stages."
            ),
            "full_ranking_equal_count": sum(
                cell["corrected_full_ranking_equal"] for cell in cells
            ),
            "max_abs_score_difference": max(
                cell["corrected_max_abs_score_difference"] for cell in cells
            ),
        },
        "cells": cells,
        "binding_interpretation": (
            "The registered derivation replaces recursive c with the latest hit "
            "mean and therefore omits RHO. PF11 fails; Rev 3 requires a stop."
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


def leakage_audit() -> dict[str, Any]:
    source = Path(__file__).read_text(encoding="utf-8")
    forbidden = ("q_facts_key", "rubric", "ATOMIC_ITEMS", "TARGETED_ITEMS")
    audited_source = "\n".join(
        line for line in source.splitlines() if "forbidden =" not in line
    )
    found = [token for token in forbidden if token in audited_source]
    return {
        "status": "PASS" if not found else "FAIL",
        "forbidden_tokens": list(forbidden),
        "found": found,
        "note": (
            "The rank inventory is projected immediately to episode_id, "
            "source_turn, and cosine; fact/domain columns are not retained."
        ),
    }


def build_report() -> dict[str, Any]:
    if sha256_file(DESIGN) != DESIGN_SHA256:
        raise AssertionError("Rev 3 design anchor digest changed")
    if sha256_file(AUTHORIZATION) != AUTHORIZATION_SHA256:
        raise AssertionError("Rev 3 authorization digest changed")
    inputs = load_inputs()
    leakage = leakage_audit()
    if leakage["status"] != "PASS":
        raise AssertionError("PF11 leakage audit failed")
    pf11 = evaluate_pf11(inputs)
    return {
        "study": "E006 Part 2 Rev 3 chained retrieval",
        "stage": "PF11 computability verification",
        "status": pf11["status"],
        "decision": "STOP_BEFORE_REMAINING_PREFLIGHT"
        if pf11["status"] == "FAIL"
        else "CONTINUE_PREFLIGHT",
        "design_sha256": DESIGN_SHA256,
        "authorization_sha256": AUTHORIZATION_SHA256,
        "zero_model_calls": True,
        "zero_embedding_calls": True,
        "execution": {
            "launch_command": (
                ".venv/Scripts/python.exe -m src.analysis.e006_rev3_pf11 "
                "experiments/components/retrieval_mechanism_ledger/artifacts/"
                "e006_rev3_pf11/pf11.json"
            ),
            "auditor_source_sha256": sha256_file(Path(__file__)),
            "text_encoding": "UTF-8",
        },
        "input_inventory": [
            {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in (DESIGN, AUTHORIZATION, DATABASE, Q11_RANK_INVENTORY)
        ],
        "input_counts": {
            "q11_cosine_rows": len(inputs.ids),
            "eligible_episode_vectors": len(inputs.ids),
            "embedding_dimension": int(inputs.episode_vectors.shape[1]),
            "gram_shape": list(inputs.gram.shape),
        },
        "gate_ordering": git_ordering(),
        "leakage_audit": leakage,
        "pf11": pf11,
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run E006 Rev 3 PF11")
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

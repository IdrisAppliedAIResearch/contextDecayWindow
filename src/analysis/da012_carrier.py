"""Mechanical grouped carrier-scoring preflight for DA-012."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import FEATURES, read_gzip
from analysis.nf004_anatomy_analysis import _predict
from analysis.nf004_anatomy_features import sha256_file

HASHES = {
    "da011_result": "6f0925b181bcb62410d4ce346601db0d73070ee7f9b69455a5285f3b73994d56",
    "payload": "51e0e648f66bf2c5a7ab6161c5fbcbc9efaadff306beb9b98ffac6a2f19d47b3",
    "da010_result": "ef59203e80991132dffad38cd849bf161026a038490b9b518c095c612e54c1af",
    "da010_allocations": "d69a5e1a1585f0e1988bb6599af9fd53d2d84c5d4d70e3783d96c6427839d9b8",
    "role": "0fbe8e54d3385575749d779429488d3e1efe2e5b5815a87aa7403a4650cbf0bb",
    "perturbation": "e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4",
    "labels": "d111229d791477171b22a49899b42bbc9870b0e829e9d6925402ff9c5b467bca",
}


class DA012Error(RuntimeError):
    pass


def grouped_scores(matrix: np.ndarray, labels: np.ndarray, groups: np.ndarray) -> tuple[np.ndarray, dict[str, dict[str, int]]]:
    predictions = np.zeros(len(labels), dtype=float)
    audit: dict[str, dict[str, int]] = {}
    for group in sorted(set(groups)):
        test = groups == group
        train = ~test
        if len(set(labels[train])) != 2:
            raise DA012Error("DA-012 training fold lacks both carrier labels")
        predictions[test] = _predict(matrix[train], labels[train], matrix[test], 1.0)
        audit[str(group)] = {"train": int(train.sum()), "test": int(test.sum()),
                             "train_positives": int(labels[train].sum()), "test_positives": int(labels[test].sum()),
                             "overlap": int(np.logical_and(train, test).sum())}
    return predictions, audit


def edge_tie(row: Mapping[str, Any]) -> tuple[float, int, str]:
    feature = row["features"]
    return float(feature["seed_rank"]), 0 if float(feature["signed_direction"]) < 0 else 1, str(row["neighbor_id"])


def run_preflight(paths: Mapping[str, Path], output_dir: Path) -> dict[str, Any]:
    observed = {name: sha256_file(path) for name, path in paths.items()}
    if observed != HASHES:
        raise DA012Error("DA-012 sealed input hash differs")
    blind = read_gzip(paths["perturbation"])
    questions = {(row["comparison_key"], int(row["duplicate_ordinal"])) for row in blind}
    schema_ok = all(tuple(row["features"].keys()) == FEATURES or set(row["features"]) == set(FEATURES) for row in blind)
    matrix = np.asarray([[index, index % 3, 1.0] for index in range(18)], dtype=float)
    labels = np.asarray([index % 2 for index in range(18)], dtype=int)
    groups = np.asarray([f"g{index // 6}" for index in range(18)])
    first, audit = grouped_scores(matrix, labels, groups)
    second, replay_audit = grouped_scores(matrix, labels, groups)
    checks = {"blind_edges": len(blind) == 26_100, "blind_questions": len(questions) == 1_104,
              "feature_count": len(FEATURES) == 73, "feature_schema": schema_ok,
              "six_conversations_in_allocations": len({row["sample_id"] for row in read_gzip(paths["da010_allocations"])}) == 6,
              "group_exclusion": all(row["overlap"] == 0 for row in audit.values()),
              "deterministic_scores": np.array_equal(first, second) and audit == replay_audit,
              "finite_probabilities": bool(np.isfinite(first).all() and ((first >= 0) & (first <= 1)).all()),
              "stable_tie": edge_tie({"neighbor_id": "n", "features": {"seed_rank": 2, "signed_direction": -1}}) == (2.0, 0, "n")}
    status = "PASS" if all(checks.values()) else "FAIL"
    result = {"schema": "da012-mechanical-preflight-v1", "status": status, "hashes": observed,
              "checks": checks, "features": list(FEATURES), "synthetic_group_audit": audit,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if status != "PASS":
        raise DA012Error("DA-012 mechanical preflight failed")
    return result


__all__ = ["DA012Error", "edge_tie", "grouped_scores", "run_preflight"]


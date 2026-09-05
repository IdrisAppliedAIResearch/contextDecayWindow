"""Blind legacy-equivalence gate for the indexed DA-099 codec."""

from __future__ import annotations

import gzip
import hashlib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da006_reserved_links import _member_maps
from analysis.da013_preflight import sha256_file
from analysis.da098_budget_replay import (
    DA035_SHA256,
    DA098Error,
    allocate_32,
    allocate_32_legacy,
)
from analysis.nf004_anatomy_features import load_blind_cases
from analysis.nf004_mechanism import ranking_orders
from retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _key(row: Mapping[str, Any]) -> tuple[str, int]:
    return str(row["comparison_key"]), int(row["duplicate_ordinal"])


def subset_keys(rows: Sequence[Mapping[str, Any]]) -> set[tuple[str, int]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row["sample_id"])].append(row)
    selected: set[tuple[str, int]] = set()
    for sample_id in sorted(groups):
        ordered = sorted(groups[sample_id], key=lambda row: (
            int(row["treatment"]["final_chars"]), *_key(row)
        ))
        for index in (0, len(ordered) // 2, len(ordered) - 1):
            selected.add(_key(ordered[index]))
    return selected


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()


def run_equivalence(dataset_path: Path, cache_path: Path, manifest_path: Path,
                    da035_path: Path, output_dir: Path) -> dict[str, Any]:
    if sha256_file(da035_path) != DA035_SHA256:
        raise DA098Error("Sealed DA-035 allocation differs")
    from episodic import EmbeddingCache

    controls_list = _read(da035_path)
    wanted = subset_keys(controls_list)
    controls = {_key(row): row for row in controls_list if _key(row) in wanted}
    if len(wanted) != 18 or set(controls) != wanted:
        raise DA098Error("DA-099 equivalence subset differs")
    cases = load_blind_cases(dataset_path)
    members, _ = _member_maps(dataset_path, cases)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cache_record = manifest["cache"]
    comparisons = []
    legacy_ms, indexed_ms = [], []
    with EmbeddingCache(
        cache_path,
        mode="reuse",
        expected_file_sha256=cache_record["file_sha256"],
        expected_content_sha256=cache_record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    ) as cache:
        for case in cases:
            questions = [question for question in case["questions"] if (
                str(question["comparison_key"]), int(question["duplicate_ordinal"])
            ) in wanted]
            if not questions:
                continue
            candidates = case["candidates"]
            matrix = np.vstack([
                np.asarray(cache(candidate.text), dtype=np.float32)
                for candidate in candidates
            ])
            for question in questions:
                key = (str(question["comparison_key"]), int(question["duplicate_ordinal"]))
                query = np.asarray(cache(question["text"]), dtype=np.float32)
                _, order = ranking_orders(candidates, matrix, query)
                pair_order = [candidates[index].identity for index in order]
                pair_for = lambda identity: members[identity]
                started = time.perf_counter_ns()
                legacy = allocate_32_legacy(controls[key], pair_for, pair_order)
                legacy_ms.append((time.perf_counter_ns() - started) / 1_000_000)
                timings: list[int] = []
                indexed = allocate_32(controls[key], pair_for, pair_order, timings)
                indexed_ms.append(timings[0] / 1_000_000)
                if indexed != legacy:
                    raise DA098Error(f"DA-099 allocation mismatch for {key}")
                comparisons.append({
                    "comparison_key": key[0],
                    "duplicate_ordinal": key[1],
                    "sample_id": str(question["sample_id"]),
                    "prefix_chars": int(indexed["prefix_chars"]),
                    "allocation_sha256": _digest(indexed),
                })
        reuse = cache.record()
    comparisons.sort(key=lambda row: (row["comparison_key"], row["duplicate_ordinal"]))
    conversations = Counter(row["sample_id"] for row in comparisons)
    passed = (len(comparisons) == 18 and set(conversations.values()) == {3}
              and reuse["misses"] == 0)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "equivalent_allocations.json"
    artifact.write_text(json.dumps(comparisons, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    result = {
        "schema": "da099-indexed-equivalence-v1",
        "status": "PASS" if passed else "FAIL",
        "rows": len(comparisons),
        "conversations": dict(sorted(conversations.items())),
        "exact_allocations": len(comparisons),
        "artifact_sha256": sha256_file(artifact),
        "legacy_ms": {
            "p50": float(np.percentile(legacy_ms, 50)),
            "p95": float(np.percentile(legacy_ms, 95)),
            "max": float(np.max(legacy_ms)),
            "total": float(np.sum(legacy_ms)),
        },
        "indexed_ms": {
            "p50": float(np.percentile(indexed_ms, 50)),
            "p95": float(np.percentile(indexed_ms, 95)),
            "max": float(np.max(indexed_ms)),
            "total": float(np.sum(indexed_ms)),
        },
        "cache": {"hits": reuse["hits"], "misses": reuse["misses"]},
        "calls": {"embedding": 0, "model": 0, "cache_access": reuse["hits"]},
    }
    (output_dir / "equivalence.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not passed:
        raise DA098Error("DA-099 equivalence gate failed")
    return result


def run_indexed_replay(dataset_path: Path, cache_path: Path, manifest_path: Path,
                       da035_path: Path, oracle_path: Path,
                       output_path: Path) -> dict[str, Any]:
    if sha256_file(da035_path) != DA035_SHA256:
        raise DA098Error("Sealed DA-035 allocation differs")
    from episodic import EmbeddingCache

    oracle_rows = json.loads(oracle_path.read_text(encoding="utf-8"))
    expected = {
        (str(row["comparison_key"]), int(row["duplicate_ordinal"])): row
        for row in oracle_rows
    }
    controls_list = _read(da035_path)
    controls = {_key(row): row for row in controls_list if _key(row) in expected}
    cases = load_blind_cases(dataset_path)
    members, _ = _member_maps(dataset_path, cases)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cache_record = manifest["cache"]
    timings_ms, matched = [], []
    with EmbeddingCache(
        cache_path,
        mode="reuse",
        expected_file_sha256=cache_record["file_sha256"],
        expected_content_sha256=cache_record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    ) as cache:
        for case in cases:
            questions = [question for question in case["questions"] if (
                str(question["comparison_key"]), int(question["duplicate_ordinal"])
            ) in expected]
            if not questions:
                continue
            candidates = case["candidates"]
            matrix = np.vstack([
                np.asarray(cache(candidate.text), dtype=np.float32)
                for candidate in candidates
            ])
            for question in questions:
                key = (str(question["comparison_key"]), int(question["duplicate_ordinal"]))
                query = np.asarray(cache(question["text"]), dtype=np.float32)
                _, order = ranking_orders(candidates, matrix, query)
                pair_order = [candidates[index].identity for index in order]
                timing: list[int] = []
                allocation = allocate_32(
                    controls[key], lambda identity: members[identity], pair_order, timing
                )
                digest = _digest(allocation)
                if digest != expected[key]["allocation_sha256"]:
                    raise DA098Error(f"DA-099 sealed allocation mismatch for {key}")
                timings_ms.append(timing[0] / 1_000_000)
                matched.append(key)
        reuse = cache.record()
    passed = set(matched) == set(expected) and len(matched) == 18 and reuse["misses"] == 0
    result = {
        "schema": "da099-indexed-sealed-replay-v1",
        "status": "PASS" if passed else "FAIL",
        "rows": len(matched),
        "oracle_sha256": sha256_file(oracle_path),
        "exact_allocations": len(matched),
        "indexed_ms": {
            "p50": float(np.percentile(timings_ms, 50)),
            "p95": float(np.percentile(timings_ms, 95)),
            "max": float(np.max(timings_ms)),
            "total": float(np.sum(timings_ms)),
        },
        "cache": {"hits": reuse["hits"], "misses": reuse["misses"]},
        "calls": {"embedding": 0, "model": 0, "cache_access": reuse["hits"]},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    if not passed:
        raise DA098Error("DA-099 sealed indexed replay failed")
    return result


__all__ = ["run_equivalence", "run_indexed_replay", "subset_keys"]

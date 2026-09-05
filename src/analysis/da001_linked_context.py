"""Label-blind linked-context traversal for DA-001."""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.nf004_anatomy_features import load_blind_cases, sha256_file
from analysis.nf004_mechanism import Candidate, Delivery, pack, ranking_orders
from retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256

BUDGET = 16_000
SEED_COUNTS = (1, 2, 4, 8, 16)
ARMS = ("DIRECT",) + tuple(
    f"{mode}_{count}" for mode in ("TEMPORAL", "EVENT") for count in SEED_COUNTS
)


class DA001Error(RuntimeError):
    pass


def linked_order(
    candidates: Sequence[Candidate], direct_order: Sequence[int], mode: str, seed_count: int
) -> tuple[tuple[int, ...], frozenset[int]]:
    if mode not in {"TEMPORAL", "EVENT"}:
        raise DA001Error(f"Unknown traversal mode: {mode}")
    if seed_count < 0:
        raise DA001Error("Seed count must be nonnegative")
    by_session: dict[str, list[int]] = {}
    for index, candidate in enumerate(candidates):
        by_session.setdefault(candidate.session_identity, []).append(index)
    for members in by_session.values():
        members.sort(key=lambda index: candidates[index].pair_order)

    emitted: list[int] = []
    seen: set[int] = set()
    linked_first: set[int] = set()

    def emit(index: int, *, linked: bool) -> None:
        if index in seen:
            return
        seen.add(index)
        emitted.append(index)
        if linked:
            linked_first.add(index)

    for seed in tuple(direct_order)[:seed_count]:
        emit(seed, linked=False)
        members = by_session[candidates[seed].session_identity]
        position = members.index(seed)
        if mode == "TEMPORAL":
            neighbors = [
                members[neighbor]
                for neighbor in (position - 1, position + 1)
                if 0 <= neighbor < len(members)
            ]
        else:
            neighbors = sorted(
                (index for index in members if index != seed),
                key=lambda index: (
                    abs(candidates[index].pair_order - candidates[seed].pair_order),
                    candidates[index].pair_order,
                ),
            )
        for neighbor in neighbors:
            if candidates[neighbor].session_identity != candidates[seed].session_identity:
                raise DA001Error("Traversal crossed a session boundary")
            emit(neighbor, linked=True)
    for index in direct_order:
        emit(index, linked=False)
    if len(emitted) != len(candidates) or len(seen) != len(candidates):
        raise DA001Error("Linked traversal did not emit every candidate exactly once")
    return tuple(emitted), frozenset(linked_first)


def _identity_digest(identities: Sequence[str]) -> str:
    return hashlib.sha256("\0".join(identities).encode("ascii")).hexdigest()


def _arm_record(
    candidates: Sequence[Candidate], order: Sequence[int], linked_first: frozenset[int],
    direct_delivery: Delivery,
) -> dict[str, Any]:
    delivery = pack(candidates, order, BUDGET)
    selected_set = set(delivery.selected)
    direct_set = set(direct_delivery.selected)
    linked_selected = [
        candidates[index].identity
        for index in order
        if index in linked_first and candidates[index].identity in selected_set
    ]
    displaced = [identity for identity in direct_delivery.selected if identity not in selected_set]
    by_id = {candidate.identity: candidate for candidate in candidates}
    return {
        "order_sha256": _identity_digest([candidates[index].identity for index in order]),
        "selected_sha256": _identity_digest(delivery.selected),
        "selected_ids": list(delivery.selected),
        "linked_selected_ids": linked_selected,
        "displaced_direct_ids": displaced,
        "packed_chars": delivery.packed_chars,
        "selected_count": len(delivery.selected),
        "sessions_touched": len({by_id[item].session_identity for item in delivery.selected}),
        "linked_admissions": len(linked_selected),
        "linked_chars": sum(by_id[item].chars for item in linked_selected),
        "displaced_count": len(displaced),
        "displaced_chars": sum(by_id[item].chars for item in displaced),
    }


def build_blind_rows(dataset_path: Path, cache_path: Path, manifest_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from episodic import EmbeddingCache

    cases = load_blind_cases(dataset_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cache_record = manifest["cache"]
    rows = []
    with EmbeddingCache(
        cache_path, mode="reuse", expected_file_sha256=cache_record["file_sha256"],
        expected_content_sha256=cache_record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    ) as cache:
        for case in cases:
            candidates = case["candidates"]
            matrix = np.vstack([np.asarray(cache(candidate.text), dtype=np.float32) for candidate in candidates])
            for question in case["questions"]:
                query = np.asarray(cache(question["text"]), dtype=np.float32)
                _, direct_order = ranking_orders(candidates, matrix, query)
                zero_order, zero_linked = linked_order(candidates, direct_order, "TEMPORAL", 0)
                if zero_order != direct_order or zero_linked:
                    raise DA001Error("Planted m=0 traversal differs from DIRECT")
                direct_delivery = pack(candidates, direct_order, BUDGET)
                direct = _arm_record(candidates, direct_order, frozenset(), direct_delivery)
                arms: dict[str, Any] = {"DIRECT": direct}
                for mode in ("TEMPORAL", "EVENT"):
                    for count in SEED_COUNTS:
                        order, linked_first = linked_order(candidates, direct_order, mode, count)
                        arms[f"{mode}_{count}"] = _arm_record(
                            candidates, order, linked_first, direct_delivery
                        )
                rows.append({
                    "comparison_key": question["comparison_key"],
                    "duplicate_ordinal": question["duplicate_ordinal"],
                    "sample_id": question["sample_id"],
                    "source_index": question["source_index"],
                    "arms": arms,
                })
        reuse = cache.record()
    rows.sort(key=lambda row: (row["comparison_key"], row["duplicate_ordinal"]))
    if len(rows) != 1_104 or any(set(row["arms"]) != set(ARMS) for row in rows):
        raise DA001Error("Blind linked-context population or arm set drifted")
    return rows, reuse


def _write_gzip_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            for row in rows:
                compressed.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))


def _distribution(values: Sequence[int]) -> dict[str, int]:
    array = np.asarray(values, dtype=int)
    return {
        "min": int(np.min(array)), "p10": int(np.percentile(array, 10, method="nearest")),
        "p50": int(np.percentile(array, 50, method="nearest")),
        "p90": int(np.percentile(array, 90, method="nearest")), "max": int(np.max(array)),
    }


def _blind_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    summary = {}
    for arm in ARMS:
        summary[arm] = {
            field: _distribution([int(row["arms"][arm][field]) for row in rows])
            for field in (
                "linked_admissions", "linked_chars", "displaced_count", "displaced_chars",
                "packed_chars", "selected_count", "sessions_touched",
            )
        }
        summary[arm]["questions_different_from_direct"] = sum(
            row["arms"][arm]["selected_sha256"] != row["arms"]["DIRECT"]["selected_sha256"]
            for row in rows
        )
    return summary


def run_preflight(dataset_path: Path, cache_path: Path, manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows, reuse = build_blind_rows(dataset_path, cache_path, manifest_path)
    selection_path = output_dir / "blind_selections.jsonl.gz"
    _write_gzip_jsonl(selection_path, rows)
    with tempfile.TemporaryDirectory(prefix="da001-") as directory:
        replay_rows, replay_reuse = build_blind_rows(dataset_path, cache_path, manifest_path)
        replay_path = Path(directory) / "blind_selections.jsonl.gz"
        _write_gzip_jsonl(replay_path, replay_rows)
        replay_identical = selection_path.read_bytes() == replay_path.read_bytes()
    source = Path(__file__).read_text(encoding="utf-8").lower()
    forbidden_declaration = "forbidden_tokens ="
    forbidden_tokens = ("nf004_measurement", "g6_holdout_outcomes", '["category"]', '["answer"]', '["evidence"]')
    scanned = "\n".join(line for line in source.splitlines() if forbidden_declaration not in line)
    leakage_clean = not any(token in scanned for token in forbidden_tokens)
    result = {
        "schema": "da001-linked-context-preflight-v1",
        "status": "PASS" if replay_identical and leakage_clean and reuse["misses"] == 0 else "FAIL",
        "selection_sha256": sha256_file(selection_path),
        "rows": len(rows), "arms": list(ARMS), "blind_summary": _blind_summary(rows),
        "replay_byte_identical": replay_identical,
        "replay_cache_misses": replay_reuse["misses"],
        "leakage_scan_clean": leakage_clean,
        "m_zero_control": "covered by linked_order unit test; planted direct order is unchanged",
        "cache": {"hits": reuse["hits"], "misses": reuse["misses"]},
        "calls": {"embedding": 0, "model": 0},
        "claim_boundary": "label-blind traversal characterization only",
    }
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise DA001Error("DA-001 preflight failed")
    return result


__all__ = ["ARMS", "DA001Error", "SEED_COUNTS", "build_blind_rows", "linked_order", "run_preflight"]

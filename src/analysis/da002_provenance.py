"""Label-blind seed and link provenance replay for DA-002."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da001_linked_context import ARMS, BUDGET, SEED_COUNTS
from analysis.nf004_anatomy_features import load_blind_cases, sha256_file
from analysis.nf004_mechanism import Candidate, pack, ranking_orders
from retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256


class DA002Error(RuntimeError):
    pass


def order_with_provenance(
    candidates: Sequence[Candidate], direct_order: Sequence[int], mode: str, seed_count: int
) -> tuple[tuple[int, ...], dict[int, dict[str, Any]]]:
    if mode not in {"TEMPORAL", "EVENT"}:
        raise DA002Error(f"Unknown mode: {mode}")
    by_session: dict[str, list[int]] = {}
    for index, candidate in enumerate(candidates):
        by_session.setdefault(candidate.session_identity, []).append(index)
    for members in by_session.values():
        members.sort(key=lambda index: candidates[index].pair_order)
    direct_rank = {index: rank for rank, index in enumerate(direct_order, 1)}
    emitted: list[int] = []
    seen: set[int] = set()
    provenance: dict[int, dict[str, Any]] = {}

    def emit(index: int, seed: int | None) -> None:
        if index in seen:
            return
        seen.add(index)
        emitted.append(index)
        if seed is not None:
            offset = candidates[index].pair_order - candidates[seed].pair_order
            provenance[index] = {
                "seed_index": seed,
                "seed_direct_rank": direct_rank[seed],
                "signed_offset": offset,
                "graph_distance": abs(offset),
                "relation": "previous" if offset == -1 else "next" if offset == 1 else "deep_previous" if offset < -1 else "deep_next",
            }

    for seed in tuple(direct_order)[:seed_count]:
        emit(seed, None)
        members = by_session[candidates[seed].session_identity]
        position = members.index(seed)
        if mode == "TEMPORAL":
            linked = [
                members[neighbor] for neighbor in (position - 1, position + 1)
                if 0 <= neighbor < len(members)
            ]
        else:
            linked = sorted(
                (index for index in members if index != seed),
                key=lambda index: (
                    abs(candidates[index].pair_order - candidates[seed].pair_order),
                    candidates[index].pair_order,
                ),
            )
        for index in linked:
            emit(index, seed)
    for index in direct_order:
        emit(index, None)
    if len(emitted) != len(candidates):
        raise DA002Error("Provenance traversal omitted a candidate")
    return tuple(emitted), provenance


def _digest(identities: Sequence[str]) -> str:
    return hashlib.sha256("\0".join(identities).encode("ascii")).hexdigest()


def _read_da001(path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    return {(row["comparison_key"], int(row["duplicate_ordinal"])): row for row in rows}


def build_provenance(
    dataset_path: Path, cache_path: Path, manifest_path: Path, da001_path: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from episodic import EmbeddingCache

    da001 = _read_da001(da001_path)
    cases = load_blind_cases(dataset_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record = manifest["cache"]
    rows = []
    digest_checks = 0
    with EmbeddingCache(
        cache_path, mode="reuse", expected_file_sha256=record["file_sha256"],
        expected_content_sha256=record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    ) as cache:
        for case in cases:
            candidates = case["candidates"]
            matrix = np.vstack([np.asarray(cache(candidate.text), dtype=np.float32) for candidate in candidates])
            norms = np.linalg.norm(matrix, axis=1)
            for question in case["questions"]:
                key = (question["comparison_key"], int(question["duplicate_ordinal"]))
                accepted = da001[key]
                query = np.asarray(cache(question["text"]), dtype=np.float32)
                scores = (matrix / norms[:, None]) @ (query / np.linalg.norm(query))
                _, direct_order = ranking_orders(candidates, matrix, query)
                direct_rank = {index: rank for rank, index in enumerate(direct_order, 1)}
                direct_delivery = pack(candidates, direct_order, BUDGET)
                direct_position = {identity: position for position, identity in enumerate(direct_delivery.selected, 1)}
                candidate_rows = {
                    candidate.identity: {
                        "session_identity": candidate.session_identity,
                        "pair_order": candidate.pair_order,
                        "chars": candidate.chars,
                        "direct_rank": direct_rank[index],
                        "direct_score": float(scores[index]),
                        "direct_selected_position": direct_position.get(candidate.identity),
                        "direct_selected_count": len(direct_delivery.selected),
                    }
                    for index, candidate in enumerate(candidates)
                }
                arms = {}
                for arm in ARMS:
                    if arm == "DIRECT":
                        order, provenance = tuple(direct_order), {}
                    else:
                        mode, raw_count = arm.split("_")
                        order, provenance = order_with_provenance(
                            candidates, direct_order, mode, int(raw_count)
                        )
                    delivery = pack(candidates, order, BUDGET)
                    expected = accepted["arms"][arm]
                    if list(delivery.selected) != expected["selected_ids"] or _digest(delivery.selected) != expected["selected_sha256"]:
                        raise DA002Error(f"{key} {arm}: selected identities differ from DA-001")
                    digest_checks += 1
                    selected_position = {identity: position for position, identity in enumerate(delivery.selected, 1)}
                    linked = {}
                    for index, detail in provenance.items():
                        identity = candidates[index].identity
                        if identity not in selected_position:
                            continue
                        seed = int(detail["seed_index"])
                        linked[identity] = {
                            "selected_position": selected_position[identity],
                            "seed_identity": candidates[seed].identity,
                            "seed_direct_rank": detail["seed_direct_rank"],
                            "seed_score": float(scores[seed]),
                            "seed_chars": candidates[seed].chars,
                            "signed_offset": detail["signed_offset"],
                            "graph_distance": detail["graph_distance"],
                            "relation": detail["relation"],
                        }
                    arms[arm] = {
                        "selected_sha256": expected["selected_sha256"],
                        "selected_ids": list(delivery.selected),
                        "linked_provenance": linked,
                        "displaced_direct_ids": expected["displaced_direct_ids"],
                        "linked_chars": expected["linked_chars"],
                        "displaced_count": expected["displaced_count"],
                        "displaced_chars": expected["displaced_chars"],
                    }
                rows.append({
                    "comparison_key": key[0], "duplicate_ordinal": key[1],
                    "sample_id": question["sample_id"], "source_index": question["source_index"],
                    "candidates": candidate_rows, "arms": arms,
                })
        reuse = cache.record()
    rows.sort(key=lambda row: (row["comparison_key"], row["duplicate_ordinal"]))
    if len(rows) != 1_104 or digest_checks != 12_144:
        raise DA002Error("DA-002 provenance population or digest count differs")
    return rows, {"digest_checks": digest_checks, "cache": reuse}


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            for row in rows:
                compressed.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(
    dataset_path: Path, cache_path: Path, manifest_path: Path, da001_path: Path, output_dir: Path
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows, audit = build_provenance(dataset_path, cache_path, manifest_path, da001_path)
    path = output_dir / "blind_provenance.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da002-") as directory:
        replay, replay_audit = build_provenance(dataset_path, cache_path, manifest_path, da001_path)
        replay_path = Path(directory) / "blind_provenance.jsonl.gz"
        _write(replay_path, replay)
        identical = path.read_bytes() == replay_path.read_bytes()
    source = Path(__file__).read_text(encoding="utf-8").lower()
    forbidden_declaration = "forbidden_tokens ="
    forbidden_tokens = ("nf004_measurement", "g6_holdout_outcomes", '["category"]', '["answer"]', '["evidence"]')
    scanned = "\n".join(line for line in source.splitlines() if forbidden_declaration not in line)
    clean = not any(token in scanned for token in forbidden_tokens)
    result = {
        "schema": "da002-provenance-preflight-v1",
        "status": "PASS" if identical and clean and audit["cache"]["misses"] == 0 else "FAIL",
        "provenance_sha256": sha256_file(path), "rows": len(rows),
        "selected_digest_checks": audit["digest_checks"],
        "replay_digest_checks": replay_audit["digest_checks"],
        "replay_byte_identical": identical, "leakage_scan_clean": clean,
        "cache": {"hits": audit["cache"]["hits"], "misses": audit["cache"]["misses"]},
        "calls": {"embedding": 0, "model": 0},
    }
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise DA002Error("DA-002 provenance preflight failed")
    return result


__all__ = ["DA002Error", "build_provenance", "order_with_provenance", "run_preflight"]

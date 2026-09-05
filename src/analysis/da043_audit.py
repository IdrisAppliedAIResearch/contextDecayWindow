"""Traversal-depth and transient-payload audit for DA-042 heads."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, load_blind_population, sha256_file
from analysis.da032_audit import distribution
from analysis.nf005_measurement import adapt_population

ENVELOPE_SHA256 = "e1f4ece6c1e55010ee7825a4ff8c56778834a8ae03cc6fa9eea5795a7ee0d7cc"
AUDIT_SHA256 = "b12532da99fe17d713a1918dc64fc553ab0872cf980425bd1763bf3893cd4727"


class DA043Error(RuntimeError):
    pass


def _ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA043Error("Population differs")
    data = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(str(row["question_id"]) for row in data["rows"])


def _band(depth: int) -> str:
    if depth == 1:
        return "1"
    if depth <= 8:
        return "2-8"
    if depth <= 32:
        return "9-32"
    if depth <= 128:
        return "33-128"
    return ">128"


def audit(longmem_path: Path, population_path: Path, envelope_path: Path,
          residual_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(envelope_path) != ENVELOPE_SHA256 or sha256_file(residual_path) != AUDIT_SHA256:
        raise DA043Error("Sealed input differs")
    envelopes = {str(row["question_id"]): row for row in read_gzip(envelope_path)}
    residuals = {str(row["key"]): row for row in read_gzip(residual_path)}
    blind = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    evidence = {record.question_id: record for record in adapt_population(longmem_path, _ids(population_path))}
    rows = []
    for question_id, residual in residuals.items():
        envelope, blind_record, evidence_record = envelopes[question_id], blind[question_id], evidence[question_id]
        blind_by_id = {episode.candidate.identity: episode for episode in blind_record.episodes}
        identities = {episode.candidate.identity: tuple(episode.turn_identities)
                      for episode in evidence_record.episodes}
        identity_nodes: dict[str, list[dict[str, Any]]] = {}
        for ordinal, (neighbor, member) in enumerate(envelope["treatment"]["targets"], 1):
            neighbor, member = str(neighbor), int(member)
            identity = identities[neighbor][member]
            source = blind_by_id[neighbor].members[member]
            text = str(source["text"])
            node = {"ordinal": ordinal, "neighbor_id": neighbor, "member": member,
                    "identity": identity, "raw_chars": len(text),
                    "rendered_chars": len(str(source["speaker"])) + 2 + len(text)}
            identity_nodes.setdefault(identity, []).append(node)
        required = []
        for identity in map(str, residual["remaining_missing"]):
            matches = identity_nodes.get(identity, [])
            if len(matches) != 1:
                raise DA043Error(f"Required identity resolves {len(matches)} times")
            required.append(matches[0])
        if not required:
            raise DA043Error("Residual has no required nodes")
        depth = max(node["ordinal"] for node in required)
        rendered = [node["rendered_chars"] for node in required]
        rows.append({"question_id": question_id, "question_type": evidence_record.question_type,
                     "blocker": residual["blocker"], "required_nodes": len(required),
                     "first_ordinal": min(node["ordinal"] for node in required),
                     "last_ordinal": depth, "sequential_nodes_visited": depth,
                     "depth_band": _band(depth), "nodes": required,
                     "all_fit_256": all(value <= 256 for value in rendered),
                     "all_fit_512": all(value <= 512 for value in rendered),
                     "all_fit_1024": all(value <= 1024 for value in rendered),
                     "all_fit_2048": all(value <= 2048 for value in rendered)})
    if len(rows) != 18:
        raise DA043Error("Residual cardinality differs")
    node_rows = [node for row in rows for node in row["nodes"]]
    result = {"schema": "da043-dereference-burden-audit-v1", "status": "COMPLETE",
              "residuals": len(rows), "required_nodes": len(node_rows),
              "conjunctions": sum(row["required_nodes"] > 1 for row in rows),
              "depth_bands": dict(Counter(row["depth_band"] for row in rows)),
              "sequential_depth": distribution([row["sequential_nodes_visited"] for row in rows]),
              "max_sequential_depth": max(row["sequential_nodes_visited"] for row in rows),
              "raw_payload_chars": distribution([node["raw_chars"] for node in node_rows]),
              "rendered_payload_chars": distribution([node["rendered_chars"] for node in node_rows]),
              "max_rendered_payload_chars": max(node["rendered_chars"] for node in node_rows),
              "all_nodes_fit": {str(limit): sum(row[f"all_fit_{limit}"] for row in rows)
                                for limit in (256, 512, 1024, 2048)},
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent evidence-aware dereference burden only; no reader or delivery"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_audit(longmem_path: Path, population_path: Path, envelope_path: Path,
              residual_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = audit(longmem_path, population_path, envelope_path, residual_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "burden.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da043-") as directory:
        replay_result, replay_rows = audit(longmem_path, population_path, envelope_path, residual_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "burden_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA043Error("Audit replay differs")
    return result


__all__ = ["DA043Error", "audit", "run_audit"]

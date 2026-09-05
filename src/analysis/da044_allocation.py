"""Blind first-32 auxiliary payload page over immutable DA-038."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da031_varint_backrefs import decode_uint, encode_uint

PAGE_BUDGET = 16_000
PAGE_DEPTH = 32
DA042_SHA256 = "e1f4ece6c1e55010ee7825a4ff8c56778834a8ae03cc6fa9eea5795a7ee0d7cc"


class DA044Error(RuntimeError):
    pass


def render_block(sentinel: str, ordinal: int, member: Mapping[str, str]) -> str:
    if ordinal < 1 or not sentinel or set(sentinel) != {"~"}:
        raise DA044Error("Invalid auxiliary node")
    return f"{sentinel}N{encode_uint(ordinal)}{sentinel}{member['speaker']}: {member['text']}"


def parse_block(block: str, sentinel: str) -> tuple[int, str, str]:
    opening = sentinel + "N"
    if not block.startswith(opening):
        raise DA044Error("Malformed auxiliary node")
    end = block.find(sentinel, len(opening))
    if end < 0:
        raise DA044Error("Unterminated auxiliary node")
    ordinal, cursor = decode_uint(block[len(opening):end], 0)
    if cursor != end - len(opening):
        raise DA044Error("Trailing ordinal data")
    payload = block[end + len(sentinel):]
    if ": " not in payload:
        raise DA044Error("Malformed auxiliary payload")
    speaker, text = payload.split(": ", 1)
    return ordinal, speaker, text


def parse_page(page: str, sentinel: str) -> list[tuple[int, str, str]]:
    if not page:
        return []
    marker = "\n" + sentinel + "N"
    starts, cursor = [0], 0
    while True:
        boundary = page.find(marker, cursor)
        if boundary < 0:
            break
        starts.append(boundary + 1)
        cursor = boundary + len(marker)
    blocks = [page[start:(starts[index + 1] - 1 if index + 1 < len(starts) else len(page))]
              for index, start in enumerate(starts)]
    decoded = [parse_block(block, sentinel) for block in blocks]
    rebuilt = "\n".join(render_block(sentinel, ordinal, {"speaker": speaker, "text": text})
                         for ordinal, speaker, text in decoded)
    if rebuilt != page:
        raise DA044Error("Auxiliary page is not canonical")
    return decoded


def allocate(row: Mapping[str, Any], pair_for: Any) -> dict[str, Any]:
    sentinel = str(row["da038_control"]["sentinel"])
    blocks, nodes = [], []
    overflow = False
    for ordinal, (neighbor, member_index) in enumerate(row["treatment"]["targets"][:PAGE_DEPTH], 1):
        neighbor, member_index = str(neighbor), int(member_index)
        member = pair_for(neighbor)[member_index]
        block = render_block(sentinel, ordinal, member)
        if parse_block(block, sentinel) != (ordinal, str(member["speaker"]), str(member["text"])):
            raise DA044Error("Auxiliary node decode differs")
        candidate = "\n".join((*blocks, block))
        if len(candidate) > PAGE_BUDGET:
            overflow = True
            break
        blocks.append(block)
        nodes.append({"ordinal": ordinal, "neighbor_id": neighbor, "member": member_index,
                      "block_chars": len(block),
                      "block_sha256": hashlib.sha256(block.encode()).hexdigest()})
    page = "\n".join(blocks)
    return {"codec": "AUXILIARY_FRONTIER_PAGE", "page_depth": PAGE_DEPTH,
            "page_budget": PAGE_BUDGET, "page_chars": len(page), "page": page,
            "page_sha256": hashlib.sha256(page.encode()).hexdigest(), "nodes": nodes,
            "overflow": overflow, "frontier_targets": len(row["treatment"]["targets"]),
            "depth_truncated": len(row["treatment"]["targets"]) > PAGE_DEPTH,
            "immutable_prompt_chars": int(row["da038_control"]["final_chars"]),
            "prompt_char_delta": 0,
            "immutable_order_sha256": str(row["treatment"]["immutable_order_sha256"])}


def build_rows(longmem_path: Path, population_path: Path, da042_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da042_path) != DA042_SHA256:
        raise DA044Error("DA-042 blind artifact differs")
    source = list(read_gzip(da042_path))
    records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    output = []
    for row in source:
        by_id = {episode.candidate.identity: episode for episode in records[str(row["question_id"])].episodes}
        treatment = allocate(row, lambda identity: by_id[identity].members)
        output.append({**row, "da042_control": row["treatment"], "treatment": treatment})
    if len(output) != 465:
        raise DA044Error("DA-044 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(longmem_path: Path, population_path: Path, da042_path: Path,
                  output_dir: Path) -> dict[str, Any]:
    rows = build_rows(longmem_path, population_path, da042_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_pages.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da044-") as directory:
        replay = Path(directory) / path.name
        _write(replay, build_rows(longmem_path, population_path, da042_path))
        identical = path.read_bytes() == replay.read_bytes()
    immutable = all(row["treatment"]["immutable_prompt_chars"] == row["da038_control"]["final_chars"]
                    and row["treatment"]["prompt_char_delta"] == 0 for row in rows)
    prefix_only = all([node["ordinal"] for node in row["treatment"]["nodes"]]
                      == list(range(1, len(row["treatment"]["nodes"]) + 1)) for row in rows)
    canonical_decode = all(
        [ordinal for ordinal, _, _ in parse_page(row["treatment"]["page"],
                                                  str(row["da038_control"]["sentinel"]))]
        == [node["ordinal"] for node in row["treatment"]["nodes"]]
        for row in rows
    )
    truncated = sum(row["treatment"]["overflow"] or row["treatment"]["depth_truncated"] for row in rows)
    page_chars = [row["treatment"]["page_chars"] for row in rows]
    page_nodes = [len(row["treatment"]["nodes"]) for row in rows]
    passed = (identical and immutable and prefix_only and canonical_decode and truncated > 0 and max(page_chars) <= PAGE_BUDGET
              and max(page_nodes) <= PAGE_DEPTH and sum(value > 0 for value in page_nodes) > 0)
    result = {"schema": "da044-auxiliary-frontier-page-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "immutable_da038": immutable, "prefix_only": prefix_only,
              "canonical_page_decode": canonical_decode,
              "overflow_or_depth_truncated": truncated,
              "page_chars": {"p10": float(np.percentile(page_chars, 10)),
                             "p50": float(np.percentile(page_chars, 50)),
                             "p90": float(np.percentile(page_chars, 90))},
              "page_nodes": {"p10": float(np.percentile(page_nodes, 10)),
                             "p50": float(np.percentile(page_nodes, 50)),
                             "p90": float(np.percentile(page_nodes, 90))},
              "max_page_chars": max(page_chars), "max_page_nodes": max(page_nodes),
              "replay_byte_identical": identical, "allocation_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA044Error("DA-044 blind preflight failed")
    return result


__all__ = ["DA044Error", "allocate", "parse_block", "parse_page", "render_block", "run_preflight"]

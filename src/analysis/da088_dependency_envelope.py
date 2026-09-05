"""Deterministic protected dependency-envelope composition for 13 residuals."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import sha256_file
from analysis.da032_audit import distribution

FRAME_CAP = 2_048
DA083_SHA256 = "c26c814c8c8ef0528c33480767e885e018865afbe86e310e380af1d5b8cdca55"
DA079_SHA256 = "08c06d6640edd6cd4579fb350033db11b7d912e7664b6659e27d603882e60ed1"
DA045_SHA256 = "ba527732771e4bcba3d7e5b289b5cb8f3f9daf9b53f0601acac293e401ef2a0a"
DA087_SHA256 = "ebf95ba5ecbd7ea51dbab3f4483ad7e0ee505c71b5f1895255c26cd71021274d"


class DA088Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def analyze(da083_path: Path, da079_path: Path, da045_path: Path,
            da087_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = (
        (da083_path, DA083_SHA256),
        (da079_path, DA079_SHA256),
        (da045_path, DA045_SHA256),
        (da087_path, DA087_SHA256),
    )
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA088Error("Sealed input differs")
    paths = {str(row["key"]): row for row in _read(da083_path)}
    residuals = {str(row["key"]): row for row in _read(da079_path)}
    streams = {str(row["question_id"]): row for row in read_gzip(da045_path)}
    orphans = {str(row["key"]): row for row in _read(da087_path)}
    if len(paths) != 13 or set(paths) != set(residuals) or len(orphans) != 5:
        raise DA088Error("Envelope population differs")

    rows = []
    for question_id in sorted(paths):
        path = paths[question_id]
        residual = residuals[question_id]
        stream = streams[question_id]
        state = str(path["state"])
        if state == "ORPHAN_PARENT":
            orphan = orphans.get(question_id)
            if orphan is None or orphan["state"] != "COMPLETE_ANCHORED_EDGE_SLICES":
                raise DA088Error("Orphan route is not sealed complete")
            route = "ANCHORED_EDGE_SLICES"
            frames = int(orphan["frames"])
            peak = int(orphan["peak_frame_chars"])
            cumulative = int(orphan["cumulative_frame_chars"])
            edge = dict(orphan["edge"])
            payload_manifest = list(orphan["frame_manifest"])
        else:
            required = (str(residual["carrier"]), int(residual["required_member"]))
            matches = [
                action for action in stream["treatment"]["actions"]
                if action["kind"] == "FRAME"
                and (str(action["neighbor_id"]), int(action["member"])) == required
            ]
            if len(matches) != 1:
                raise DA088Error("Required sealed child frame is not unique")
            action = matches[0]
            frames = 1
            peak = cumulative = int(action["cost"])
            payload_manifest = [{
                "ordinal": int(action["ordinal"]),
                "neighbor_id": required[0],
                "member": required[1],
                "chars": int(action["cost"]),
                "block_sha256": str(action["block_sha256"]),
            }]
            if state == "ROOT_MEMBER":
                route = "PROMPT_SIBLING_FRAME"
                edge = {
                    "type": "same_carrier_sibling",
                    "parent": required[0],
                    "child": required[0],
                    "member": required[1],
                }
            elif state == "LINKED_PATH":
                ordinals = list(path["path_edge_ordinals"])
                if len(ordinals) != 1:
                    raise DA088Error("Linked route is not one edge")
                source = stream["baseline_actions"][int(ordinals[0]) - 1]
                if str(source["neighbor_id"]) != required[0]:
                    raise DA088Error("Linked edge target differs")
                route = "PROMPT_LINKED_FRAME"
                edge = {
                    "type": "temporal_parent_child",
                    "parent": str(source["seed_id"]),
                    "child": required[0],
                    "member": required[1],
                    "direction": int(source["direction"]),
                }
            else:
                raise DA088Error("Unknown structural route state")
        if peak > FRAME_CAP or frames < 1 or cumulative < peak:
            raise DA088Error("Envelope frame gate fails")
        rows.append({
            "key": question_id,
            "question_type": str(path["question_type"]),
            "blocker": str(path["blocker"]),
            "source_state": state,
            "route": route,
            "frames": frames,
            "peak_frame_chars": peak,
            "cumulative_frame_chars": cumulative,
            "prompt_char_delta": 0,
            "edge": edge,
            "payload_manifest": payload_manifest,
        })

    routes = Counter(row["route"] for row in rows)
    complete = sum(
        row["prompt_char_delta"] == 0
        and row["peak_frame_chars"] <= FRAME_CAP
        and row["frames"] >= 1
        for row in rows
    )
    result = {
        "schema": "da088-protected-dependency-envelope-v1",
        "status": (
            "PROTECTED_DEPENDENCY_ENVELOPE_SIGNAL"
            if complete == 13 else "NO_PROTECTED_DEPENDENCY_ENVELOPE_SIGNAL"
        ),
        "residuals": len(rows),
        "complete": complete,
        "routes": dict(routes),
        "frames": distribution([row["frames"] for row in rows]),
        "peak_frame_chars": distribution([row["peak_frame_chars"] for row in rows]),
        "cumulative_frame_chars": distribution([
            row["cumulative_frame_chars"] for row in rows
        ]),
        "protected_da078_mutations": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "deterministic protected dependency exposure only; no reader, retention, stopping, transfer, delivery, runtime, or adoption",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                payload = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                output.write(payload.encode())


def run_analysis(da083_path: Path, da079_path: Path, da045_path: Path,
                 da087_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(da083_path, da079_path, da045_path, da087_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "envelopes.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da088-") as directory:
        replay_result, replay_rows = analyze(
            da083_path, da079_path, da045_path, da087_path
        )
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["envelopes_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA088Error("DA-088 replay differs")
    return result


__all__ = ["DA088Error", "analyze", "run_analysis"]

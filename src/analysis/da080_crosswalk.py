"""Crosswalk DA-079 residuals to sealed DA-045 replaceable frames."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da013_preflight import sha256_file
from analysis.da032_audit import distribution

DA079_SHA256 = "08c06d6640edd6cd4579fb350033db11b7d912e7664b6659e27d603882e60ed1"
DA045_SHA256 = "174204459562cee0c8062632b607e1e3960add2ab418bf2f922871dbaf818fc1"


class DA080Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def analyze(da079_path: Path, da045_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(da079_path) != DA079_SHA256 or sha256_file(da045_path) != DA045_SHA256:
        raise DA080Error("Sealed input differs")
    residuals = {str(row["key"]): row for row in _read(da079_path)}
    exposures = {str(row["question_id"]): row for row in _read(da045_path)}
    if len(residuals) != 13 or not set(residuals) <= set(exposures):
        raise DA080Error("Crosswalk population differs")
    rows = []
    for question_id in sorted(residuals):
        residual, exposure = residuals[question_id], exposures[question_id]
        rows.append({
            "question_id": question_id,
            "question_type": str(residual["question_type"]),
            "da079_blocker": str(residual["blocker"]),
            "exposed": bool(exposure["exposed"]),
            "required_nodes": int(exposure["required_nodes"]),
            "last_required_ordinal": int(exposure["last_required_ordinal"]),
            "frames_through_requirement": int(exposure["frames_through_requirement"]),
            "overflows_through_requirement": int(exposure["overflows_through_requirement"]),
            "cumulative_chars_through_requirement": int(exposure["cumulative_chars_through_requirement"]),
            "peak_frame_chars": int(exposure["peak_frame_chars"]),
        })
    exposed = sum(row["exposed"] for row in rows)
    result = {
        "schema": "da080-protected-stream-crosswalk-v1",
        "status": "PROTECTED_STREAM_CROSSWALK_COMPLETE" if exposed == 13 else "INCOMPLETE_STREAM_CROSSWALK",
        "residuals": len(rows),
        "exposed": exposed,
        "not_exposed": len(rows) - exposed,
        "blockers": dict(Counter(row["da079_blocker"] for row in rows)),
        "required_nodes": distribution([row["required_nodes"] for row in rows]),
        "frames_through_requirement": distribution([row["frames_through_requirement"] for row in rows]),
        "cumulative_chars_through_requirement": distribution([
            row["cumulative_chars_through_requirement"] for row in rows
        ]),
        "peak_frame_chars": distribution([row["peak_frame_chars"] for row in rows]),
        "protected_da078_mutations": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "sealed structural exposure crosswalk only; no reader recognition, retention, stopping, or answer use",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                payload = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                output.write(payload.encode())


def run_analysis(da079_path: Path, da045_path: Path,
                 output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(da079_path, da045_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "crosswalk.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da080-") as directory:
        replay_result, replay_rows = analyze(da079_path, da045_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["crosswalk_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA080Error("DA-080 replay differs")
    return result


__all__ = ["DA080Error", "analyze", "run_analysis"]

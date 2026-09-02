"""Frozen NF-only subset gate for DA-022."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import sha256_file

SOURCE_SHA256 = "2e1eb8795f9f8a06ec5900ff7297a6b962a5257c56fac2f8ac1925954c17aed9"


class DA022Error(RuntimeError):
    pass


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(source_path: Path, output_dir: Path) -> dict[str, Any]:
    if sha256_file(source_path) != SOURCE_SHA256:
        raise DA022Error("DA-021 source artifact differs")
    rows = [row for row in read_gzip(source_path) if row["corpus"] == "NF004"]
    if len(rows) != 1_098:
        raise DA022Error("DA-022 NF subset differs")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_allocations.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da022-") as directory:
        replay = Path(directory) / path.name
        _write(replay, rows)
        identical = path.read_bytes() == replay.read_bytes()
    actions = Counter(action["kind"] for row in rows for action in row["treatment"]["additions"])
    savings = [int(row["treatment"]["recovered_chars"]) for row in rows]
    summary = {"rows": len(rows),
               "joint_renderers": sum(row["treatment"]["renderer"] == "JOINT" for row in rows),
               "median_recovered_chars": float(np.median(savings)),
               "added_pairs": actions["PAIR"], "added_turns": actions["TURN"],
               "remaining_skips": actions["SKIP"],
               "expanding_rows": sum(row["treatment"]["baseline_chars"] > row["treatment"]["control_chars"] for row in rows),
               "max_final_chars": max(row["treatment"]["final_chars"] for row in rows)}
    expected = {"rows": 1_098, "joint_renderers": 1_098, "median_recovered_chars": 480.5,
                "added_pairs": 1_544, "added_turns": 1_038, "remaining_skips": 7_687,
                "expanding_rows": 0, "max_final_chars": 16_000}
    passed = identical and summary == expected
    result = {"schema": "da022-nf-blind-subset-v1", "status": "PASS" if passed else "FAIL",
              "summary": summary, "byte_identical_replay": identical,
              "selection_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA022Error("DA-022 blind subset gate failed")
    return result


__all__ = ["DA022Error", "run_preflight"]


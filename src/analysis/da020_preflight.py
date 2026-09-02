"""Frozen DA-019 blind reproduction and corrected identity gate for DA-020."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import sha256_file
from analysis.da019_substitution import duplicate_rejection

DA019_SELECTION_SHA256 = "b418495e649c96befa33a738a9fda0f68e56127b76f881ccc71ac4c853acd31f"


class DA020Error(RuntimeError):
    pass


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(source_path: Path, output_dir: Path) -> dict[str, Any]:
    if sha256_file(source_path) != DA019_SELECTION_SHA256:
        raise DA020Error("DA-019 blind selection differs")
    rows = list(read_gzip(source_path))
    if len(rows) != 1_563:
        raise DA020Error("DA-020 population differs")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_substitutions.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da020-") as directory:
        replay = Path(directory) / path.name
        _write(replay, rows)
        identical = path.read_bytes() == replay.read_bytes() == source_path.read_bytes()
    activity = {corpus: sum(row["treatment"]["executed"] for row in rows if row["corpus"] == corpus)
                for corpus in ("NF004", "LONGMEM")}
    rejections = Counter(reason for row in rows for evaluation in row["treatment"]["evaluations"]
                         for reason in evaluation["reasons"])
    real_duplicates = rejections["DUPLICATE"]
    synthetic = (duplicate_rejection("kept", {"kept"}, "tail") == ("DUPLICATE",) and
                 duplicate_rejection("tail", {"kept"}, "tail") == ("DUPLICATE",) and
                 duplicate_rejection("new", {"kept"}, "tail") == ())
    expected = (activity == {"NF004": 571, "LONGMEM": 188} and
                {name: rejections[name] for name in ("FIT", "LEXICAL", "SEMANTIC")} ==
                {"FIT": 8_631, "LEXICAL": 359, "SEMANTIC": 6_786})
    passed = identical and expected and real_duplicates == 0 and synthetic
    result = {"schema": "da020-blind-reproduction-v1", "status": "PASS" if passed else "FAIL",
              "questions": len(rows), "activity": activity,
              "real_rejections": dict(sorted(rejections.items())),
              "real_duplicate_opportunities": real_duplicates,
              "synthetic_duplicate_test": synthetic,
              "selection_sha256": sha256_file(path), "byte_identical_to_da019": identical,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA020Error("DA-020 corrected blind preflight failed")
    return result


__all__ = ["DA020Error", "run_preflight"]


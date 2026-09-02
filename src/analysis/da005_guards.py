"""Blind structural displacement guards for DA-005."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da003_edge_features import write_rows
from analysis.nf004_anatomy_features import sha256_file

INPUT_SHA256 = "e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4"
GUARDS = ("OPEN", "COUNT_0", "COUNT_1", "COUNT_2", "COUNT_4",
          "CHARS_256", "CHARS_512", "CHARS_1024", "DUAL_1_512")


class DA005Error(RuntimeError):
    pass


def decisions(added_count: int, displaced_count: int, displaced_chars: int) -> dict[str, bool]:
    active = added_count > 0
    return {
        "OPEN": active,
        "COUNT_0": active and displaced_count <= 0,
        "COUNT_1": active and displaced_count <= 1,
        "COUNT_2": active and displaced_count <= 2,
        "COUNT_4": active and displaced_count <= 4,
        "CHARS_256": active and displaced_chars <= 256,
        "CHARS_512": active and displaced_chars <= 512,
        "CHARS_1024": active and displaced_chars <= 1024,
        "DUAL_1_512": active and displaced_count <= 1 and displaced_chars <= 512,
    }


def read_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def build_rows(input_path: Path) -> list[dict[str, Any]]:
    if sha256_file(input_path) != INPUT_SHA256:
        raise DA005Error("DA-005 blind input hash differs")
    output, seen = [], set()
    for row in read_rows(input_path):
        key = (row["comparison_key"], int(row["duplicate_ordinal"]), row["seed_id"], row["neighbor_id"])
        if key in seen:
            raise DA005Error("Duplicate DA-005 edge key")
        seen.add(key)
        features = row["features"]
        choice = decisions(int(features["added_count"]), int(features["set_displaced_count"]),
                           int(features["set_displaced_chars"]))
        if set(choice) != set(GUARDS):
            raise DA005Error("DA-005 guard schema differs")
        if not (choice["COUNT_0"] <= choice["COUNT_1"] <= choice["COUNT_2"] <= choice["COUNT_4"] <= choice["OPEN"]):
            raise DA005Error("DA-005 count guards are not nested")
        if not (choice["CHARS_256"] <= choice["CHARS_512"] <= choice["CHARS_1024"] <= choice["OPEN"]):
            raise DA005Error("DA-005 character guards are not nested")
        output.append({"comparison_key": key[0], "duplicate_ordinal": key[1], "sample_id": row["sample_id"],
                       "source_index": row["source_index"], "seed_id": key[2], "neighbor_id": key[3],
                       "added_count": int(features["added_count"]),
                       "displaced_count": int(features["set_displaced_count"]),
                       "displaced_chars": int(features["set_displaced_chars"]), "decisions": choice})
    if len(output) != 26_100:
        raise DA005Error("DA-005 blind population differs")
    return output


def run_preflight(input_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows(input_path)
    path = output_dir / "blind_guard_decisions.jsonl.gz"
    write_rows(path, rows)
    with tempfile.TemporaryDirectory(prefix="da005-") as directory:
        replay = build_rows(input_path)
        replay_path = Path(directory) / path.name
        write_rows(replay_path, replay)
        identical = path.read_bytes() == replay_path.read_bytes()
    counts = {guard: sum(row["decisions"][guard] for row in rows) for guard in GUARDS}
    if any(counts[guard] in (0, len(rows)) for guard in GUARDS if guard != "OPEN"):
        raise DA005Error("DA-005 guard lacks blind reachability")
    if any(row["displaced_count"] for row in rows if row["decisions"]["COUNT_0"]):
        raise DA005Error("COUNT_0 admitted displacement")
    result = {"schema": "da005-guard-preflight-v1", "status": "PASS" if identical else "FAIL",
              "rows": len(rows), "guards": list(GUARDS), "admit_counts": counts,
              "decision_sha256": sha256_file(path), "replay_byte_identical": identical,
              "calls": {"embedding": 0, "model": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise DA005Error("DA-005 preflight failed")
    return result


__all__ = ["DA005Error", "GUARDS", "decisions", "run_preflight"]

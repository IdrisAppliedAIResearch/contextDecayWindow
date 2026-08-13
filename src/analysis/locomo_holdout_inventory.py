"""Metadata-only inventory of the locked LoCoMo holdout population."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from analysis.locomo_nf_development import DATASET_BYTES, DATASET_SHA256, sha256_file

HOLDOUT_IDS = frozenset(
    {"conv-26", "conv-30", "conv-43", "conv-44", "conv-49", "conv-50"}
)
SCHEMA = "locomo-holdout-inventory-v1"


class HoldoutInventoryError(RuntimeError):
    pass


def _identity(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def inventory(dataset_path: Path) -> dict[str, Any]:
    if dataset_path.stat().st_size != DATASET_BYTES:
        raise HoldoutInventoryError("LoCoMo byte count differs from the corpus lock")
    if sha256_file(dataset_path) != DATASET_SHA256:
        raise HoldoutInventoryError("LoCoMo SHA-256 differs from the corpus lock")
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    selected = [row for row in raw if row.get("sample_id") in HOLDOUT_IDS]
    if {row["sample_id"] for row in selected} != HOLDOUT_IDS:
        raise HoldoutInventoryError("Locked holdout conversations are incomplete")

    records: list[dict[str, Any]] = []
    unresolved_references = 0
    for row in sorted(selected, key=lambda value: value["sample_id"]):
        sample_id = str(row["sample_id"])
        known_dialog_ids = {
            str(turn["dia_id"])
            for key, turns in row["conversation"].items()
            if key.startswith("session_") and isinstance(turns, list)
            for turn in turns
        }
        occurrences: Counter[str] = Counter()
        for qa in row["qa"]:
            canonical = json.dumps(
                qa, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            content_sha256 = _identity(sample_id, canonical)
            ordinal = occurrences[content_sha256]
            occurrences[content_sha256] += 1
            evidence = tuple(str(value) for value in (qa.get("evidence") or ()))
            unresolved = sum(value not in known_dialog_ids for value in evidence)
            unresolved_references += unresolved
            records.append(
                {
                    "comparison_key": content_sha256,
                    "duplicate_ordinal": ordinal,
                    "evidence_references": len(evidence),
                    "all_evidence_references_resolve": unresolved == 0,
                }
            )

    unique = [row for row in records if row["duplicate_ordinal"] == 0]
    if len({row["comparison_key"] for row in unique}) != len(unique):
        raise HoldoutInventoryError("Canonical holdout comparison keys are not unique")
    return {
        "schema": SCHEMA,
        "source": {
            "sha256": DATASET_SHA256,
            "bytes": DATASET_BYTES,
            "holdout_ids_sha256": _identity(*sorted(HOLDOUT_IDS)),
        },
        "counts": {
            "conversations": len(selected),
            "source_qa_records": len(records),
            "canonical_unique_qa_records": len(unique),
            "duplicate_qa_records": len(records) - len(unique),
            "all_evidence_evaluable_unique_records": sum(
                row["all_evidence_references_resolve"] for row in unique
            ),
            "unresolved_evidence_references": unresolved_references,
        },
        "population": sorted(unique, key=lambda row: row["comparison_key"]),
        "content_exposed": False,
        "retrieval_outcomes_computed": False,
        "model_calls": 0,
        "embedding_calls": 0,
    }


def write(dataset_path: Path, output: Path) -> Path:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    output.write_text(
        json.dumps(inventory(dataset_path), indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output

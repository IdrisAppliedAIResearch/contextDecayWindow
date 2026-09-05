"""Sealed BEAM-001 outcome reader for a future registered measurement stage."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any


def load_outcomes(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            key = str(row["question_key"])
            if key in rows:
                raise ValueError(f"Duplicate outcome key: {key}")
            rows[key] = dict(row["official_fields"])
    return rows


__all__ = ["load_outcomes"]

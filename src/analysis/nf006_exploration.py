from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from pathlib import Path
from typing import Any

from src.analysis.e005_diversity_selection import DATABASE, load_candidates
from src.retrieval_mechanism_ledger.e005 import eligible_candidates


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "biological_memory"
    / "nf_006"
    / "artifacts"
    / "part1_exploration.json"
)
_NUMBERED_START = re.compile(r"(?m)^\d+\.\s+")
_RISK_ONLY = re.compile(r"\(Risk:\s*[^)]+\)", re.IGNORECASE)


def split_assistant_statements(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    starts = [match.start() for match in _NUMBERED_START.finditer(normalized)]
    if len(starts) >= 2:
        boundaries = [*starts, len(normalized)]
        parts = []
        prefix = normalized[: starts[0]].strip()
        if prefix:
            parts.append(prefix)
        parts.extend(
            normalized[boundaries[index] : boundaries[index + 1]].strip()
            for index in range(len(starts))
        )
    else:
        parts = [part.strip() for part in re.split(r"\n\s*\n+", normalized)]
    return [
        part
        for part in parts
        if part and _RISK_ONLY.fullmatch(part) is None
    ]


def statement_units(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    turn = int(candidate["turn_number"])
    episode_id = str(candidate["id"])
    units = [
        {
            "parent_episode_id": episode_id,
            "source_turn": turn,
            "role": "user",
            "ordinal": 0,
            "text": str(candidate["user_message"]).strip(),
        }
    ]
    units.extend(
        {
            "parent_episode_id": episode_id,
            "source_turn": turn,
            "role": "assistant",
            "ordinal": ordinal,
            "text": text,
        }
        for ordinal, text in enumerate(
            split_assistant_statements(str(candidate["assistant_message"])),
            start=1,
        )
    )
    if any(not unit["text"] for unit in units):
        raise AssertionError("Statement splitter emitted an empty unit")
    return units


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[int(fraction * (len(ordered) - 1))]


def explore() -> dict[str, Any]:
    episodes = eligible_candidates(load_candidates(), probe_turn=120)
    units = [unit for episode in episodes for unit in statement_units(episode)]
    lengths = [len(str(unit["text"])) for unit in units]
    per_episode = [len(statement_units(episode)) for episode in episodes]
    turn_90 = [unit for unit in units if int(unit["source_turn"]) == 90]
    text_hashes = [
        hashlib.sha256(str(unit["text"]).encode("utf-8")).hexdigest()
        for unit in units
    ]
    return {
        "status": "PART1_EXPLORATION_ONLY",
        "outcomes_opened": False,
        "input": {
            "database": str(DATABASE.relative_to(REPO_ROOT)),
            "database_sha256": _sha256(DATABASE),
            "eligible_episodes": len(episodes),
        },
        "behavioral_identity": (
            "Each user message remains one unit; assistant text splits at two or "
            "more top-level numbered starts, otherwise at blank paragraphs; only "
            "standalone Risk metadata is dropped."
        ),
        "units": {
            "count": len(units),
            "unique_text_count": len(set(text_hashes)),
            "user_count": sum(unit["role"] == "user" for unit in units),
            "assistant_count": sum(unit["role"] == "assistant" for unit in units),
            "characters": {
                "min": min(lengths),
                "p50": statistics.median(lengths),
                "p90": percentile(lengths, 0.9),
                "max": max(lengths),
            },
            "per_episode": {
                "min": min(per_episode),
                "p50": statistics.median(per_episode),
                "p90": percentile(per_episode, 0.9),
                "max": max(per_episode),
            },
        },
        "degenerate_states": {
            "empty_units": sum(not str(unit["text"]) for unit in units),
            "duplicate_texts": len(units) - len(set(text_hashes)),
            "unsplit_episodes": sum(count == 2 for count in per_episode),
            "long_units_over_1800_chars": sum(length > 1800 for length in lengths),
        },
        "turn_90": [
            {
                "role": unit["role"],
                "ordinal": unit["ordinal"],
                "characters": len(str(unit["text"])),
                "text_sha256": hashlib.sha256(
                    str(unit["text"]).encode("utf-8")
                ).hexdigest(),
            }
            for unit in turn_90
        ],
        "leakage_boundary": {
            "query_text_read": False,
            "q11_key_read": False,
            "targeted_key_read": False,
            "embedding_calls": 0,
            "model_calls": 0,
        },
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = explore()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

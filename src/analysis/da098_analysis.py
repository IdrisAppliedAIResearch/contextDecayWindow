"""Opened exact evidence analysis for the frozen DA-098 budget replay."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da013_preflight import sha256_file
from analysis.da035_analysis import paired
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split

SELECTION_SHA256 = "f5327a9b5946f217910f2de5df222da66bda59d5f7b18267f8154763f98d44f9"


class DA098AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _distribution(values: Sequence[int | float]) -> dict[str, float] | None:
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    return {name: float(np.percentile(array, q))
            for name, q in (("p10", 10), ("p50", 50), ("p90", 90))}


def analyze(locomo_path: Path, selection_path: Path) -> tuple[
    dict[str, Any], list[dict[str, Any]]
]:
    if sha256_file(selection_path) != SELECTION_SHA256:
        raise DA098AnalysisError("Sealed DA-098 allocation differs")
    selections = {
        (str(row["comparison_key"]), int(row["duplicate_ordinal"])): row
        for row in _read(selection_path)
    }
    evidence: dict[tuple[str, int], set[str]] = {}
    groups: dict[tuple[str, int], str] = {}
    identities: dict[str, tuple[str, ...]] = {}
    dialogue_to_member: dict[tuple[str, str], tuple[str, int]] = {}
    for record in adapt_split(locomo_path, HOLDOUT_IDS):
        for source in record.candidates:
            identity = source.candidate.identity
            identities[identity] = tuple(source.dialogue_ids)
            for index, dialogue_id in enumerate(source.dialogue_ids):
                dialogue_to_member[(record.sample_id, dialogue_id)] = (identity, index)
        for question in record.questions:
            key = (question.comparison_key, question.duplicate_ordinal)
            evidence[key] = set(question.resolved_dialogue_ids)
            groups[key] = question.sample_id

    rows = []
    for key in sorted(selections):
        selection = selections[key]
        gold = evidence[key]
        pair16 = set().union(*(
            identities[identity] for identity in selection["pair16"]["selected_ids"]
        ))
        pair32 = set().union(*(
            identities[identity] for identity in selection["pair32"]["selected_ids"]
        ))
        members = [tuple(value) for value in selection["arch32"]["selected_members"]]
        prefix_count = int(selection["arch32"]["prefix_members"])
        arch16 = {
            identities[str(identity)][int(index)]
            for identity, index in members[:prefix_count]
        }
        arch32 = {
            identities[str(identity)][int(index)] for identity, index in members
        }
        outcomes = {
            "PAIR_16": gold <= pair16,
            "PAIR_32": gold <= pair32,
            "ARCH_16": gold <= arch16,
            "ARCH_32": gold <= arch32,
        }
        missing = sorted(gold - arch32)
        action_for = {
            (str(action["identity"]), int(action["member"])): str(action["kind"])
            for action in selection["arch32"]["actions"]
        }
        missing_actions = [
            action_for.get(dialogue_to_member[(groups[key], value)], "UNADDRESSED")
            for value in missing
        ]
        if not missing:
            blocker = None
        elif all(kind == "SKIP_MEMBER" for kind in missing_actions):
            blocker = "FIT_OVERFLOW"
        else:
            blocker = "ADDRESSABILITY_OR_UNACCOUNTED"
        rows.append({
            "key": f"{key[0]}:{key[1]}",
            "group": groups[key],
            **outcomes,
            "pair32_over_arch16_gap": outcomes["PAIR_32"] and not outcomes["ARCH_16"],
            "gap_recovered": (outcomes["PAIR_32"] and not outcomes["ARCH_16"]
                              and outcomes["ARCH_32"]),
            "blocker": blocker,
            "missing_count": len(missing),
            "final_chars": int(selection["arch32"]["final_chars"]),
            "actions": selection["arch32"]["actions"],
        })

    arms = ("PAIR_16", "PAIR_32", "ARCH_16", "ARCH_32")
    complete = {arm: sum(row[arm] for row in rows) for arm in arms}
    anchors = {"PAIR_16": 935, "PAIR_32": 1024, "ARCH_16": 986}
    if len(rows) != 1098 or any(complete[arm] != value for arm, value in anchors.items()):
        raise DA098AnalysisError(f"DA-098 control anchor differs: {complete}")

    def contrast(control: str, treatment: str,
                 subset: Sequence[Mapping[str, Any]] = rows) -> dict[str, Any]:
        return paired([{"CONTROL": row[control], "TREATMENT": row[treatment]}
                       for row in subset])

    comparisons = {
        "ARCH16_vs_PAIR16": contrast("PAIR_16", "ARCH_16"),
        "ARCH32_vs_PAIR32": contrast("PAIR_32", "ARCH_32"),
        "ARCH32_vs_ARCH16": contrast("ARCH_16", "ARCH_32"),
        "PAIR32_vs_PAIR16": contrast("PAIR_16", "PAIR_32"),
    }
    by_conversation = {}
    for group in sorted(set(groups.values())):
        subset = [row for row in rows if row["group"] == group]
        by_conversation[group] = {
            "n": len(subset),
            "complete": {arm: sum(row[arm] for row in subset) for arm in arms},
            "ARCH32_vs_PAIR32": contrast("PAIR_32", "ARCH_32", subset),
            "ARCH32_vs_ARCH16": contrast("ARCH_16", "ARCH_32", subset),
        }

    admitted = [action for row in rows for action in row["actions"]
                if action["kind"] == "MEMBER"]
    skipped = [action for row in rows for action in row["actions"]
               if action["kind"] == "SKIP_MEMBER"]
    gap = [row for row in rows if row["pair32_over_arch16_gap"]]
    remaining = [row for row in rows if not row["ARCH_32"]]
    bar = (complete["ARCH_32"] >= complete["PAIR_32"]
           and comparisons["ARCH32_vs_ARCH16"]["losses"] == 0
           and all(cell["ARCH32_vs_PAIR32"]["net"] >= 0
                   for cell in by_conversation.values()))
    status = "FROZEN_BUDGET_REPLAY_SIGNAL" if bar else "NO_FROZEN_BUDGET_REPLAY_SIGNAL"
    result = {
        "schema": "da098-frozen-budget-result-v1",
        "status": status,
        "population": len(rows),
        "complete": complete,
        "comparisons": comparisons,
        "by_conversation": by_conversation,
        "pair32_over_arch16_gap": {
            "items": len(gap),
            "recovered_by_ARCH32": sum(row["gap_recovered"] for row in gap),
        },
        "mechanism": {
            "admitted_members": len(admitted),
            "skipped_members": len(skipped),
            "admitted_cost": _distribution([action["cost"] for action in admitted]),
            "admitted_rank": _distribution([action["rank"] for action in admitted]),
            "attempted_overflow_cost": _distribution([
                action["attempt_cost"] for action in skipped
            ]),
            "final_chars": _distribution([row["final_chars"] for row in rows]),
            "remaining_misses": len(remaining),
            "remaining_blockers": dict(sorted(Counter(
                row["blocker"] for row in remaining
            ).items())),
        },
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "spent LoCoMo exact availability; reader use and fresh transfer untested",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":"))
                              + "\n").encode())


def run_analysis(locomo_path: Path, selection_path: Path,
                 output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(locomo_path, selection_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "outcomes.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da098-result-") as directory:
        replay_result, replay_rows = analyze(locomo_path, selection_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result.update({
        "replay_byte_identical": identical,
        "outcomes_sha256": sha256_file(artifact),
    })
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA098AnalysisError("DA-098 outcome replay differs")
    return result


__all__ = ["DA098AnalysisError", "analyze", "run_analysis"]

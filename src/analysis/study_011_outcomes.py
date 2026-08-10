"""Study 011 section 6.2: what each arm delivered.

Everything here is a delivery measurement, read from the arms' own
constructed prompts and context logs. **None of it is an outcome.**
Section 6.1 is explicit: the outcome is the scored rubric, and LV-001 is
the standing proof of why -- 16/16 offline availability against 1.5/8
live. Availability is a secondary diagnostic and is never the bar.

Reported per arm, per section 6.2:

2. Q11 facts available and per-domain counts.
3. The eight targeted probes, per probe, on the 21-item grain.
4. Episodes and characters delivered, split by path.
5. Oracle-set overlap, both AR-001 sets.

Item 1 (scored rubric) and item 6 (paired gains and losses) need the
blind scores and are produced after those are committed, so that no
mechanism number can be read before a score is fixed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.analysis.ic001_internal_packing import (
    _normalize,
    oracle_sets,
    q11_availability,
    targeted_availability,
)
from src.analysis.study_011_achievability import (
    PROBE_TURNS,
    QUESTION_TURNS,
    STUDY_ROOT,
)
from src.memory.context_matched_stm import extract_stm_payload

REPO_ROOT = Path(__file__).resolve().parents[2]
Q11_TURN = 120
ARMS = ("A", "B", "C", "D")


class OutcomeError(RuntimeError):
    """Raised when an arm's evidence cannot be read."""


def _repo_relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def payloads_for(directory: Path) -> dict[int, str]:
    """The delivered retrieval payload at each probe turn.

    Taken from the constructed prompt, not from a re-pack: what the model
    was actually given is the only thing a delivery claim may rest on.
    """

    payloads = {}
    for turn in (*PROBE_TURNS, Q11_TURN):
        prompt_path = directory / "constructed_prompts" / f"turn_{turn:03d}.txt"
        if not prompt_path.is_file():
            raise OutcomeError(f"no constructed prompt for turn {turn}: {prompt_path}")
        payloads[turn] = extract_stm_payload(
            prompt_path.read_text(encoding="utf-8")
        )
    return payloads


def path_split(records: dict[int, dict]) -> dict:
    """Episodes and characters delivered, split by path (item 4)."""

    rows = []
    for turn in sorted(records):
        record = records[turn]
        rows.append(
            {
                "probe_turn": turn,
                "questions": sorted(
                    question
                    for question, mapped in QUESTION_TURNS.items()
                    if mapped == turn
                ),
                "recency_episodes": record["n_delivered_count"],
                "k_only_episodes": record["k_only_delivered_count"],
                "serialized_chars": record["retrieval_payload_chars"],
                "k_candidates": record["k_candidate_count"],
                "n_candidates": record["n_candidate_count"],
            }
        )
    return {
        "per_probe": rows,
        "totals": {
            "recency_episodes": sum(row["recency_episodes"] for row in rows),
            "k_only_episodes": sum(row["k_only_episodes"] for row in rows),
            "serialized_chars": sum(row["serialized_chars"] for row in rows),
        },
        "warning": (
            "Totals conceal composition. IC-001 found both arms delivering "
            "exactly 71 recency episodes in different compositions; only the "
            "paired per-probe rows showed the change."
        ),
    }


def oracle_overlap(payload_ids: list[str]) -> dict:
    """Overlap with both AR-001 oracle sets (item 5)."""

    delivered = set(payload_ids)
    result = {}
    for name, oracle in oracle_sets().items():
        episode_ids = set(oracle["episode_ids"])
        hit = sorted(delivered & episode_ids)
        result[name] = {
            "oracle_size": len(episode_ids),
            "delivered_from_oracle": len(hit),
            "episode_ids": hit,
        }
    return result


def assess_arm(arm: str, directory: Path) -> dict:
    context_log = directory / "logs" / "context_match.jsonl"
    if not context_log.is_file():
        raise OutcomeError(f"no context log for arm {arm}: {context_log}")
    records = {
        int(row["turn_number"]): row
        for row in _read_jsonl(context_log)
        if int(row["turn_number"]) in {*PROBE_TURNS, Q11_TURN}
    }
    missing = sorted({*PROBE_TURNS, Q11_TURN} - set(records))
    if missing:
        raise OutcomeError(f"arm {arm} has no record at probe turns {missing}")

    payloads = payloads_for(directory)
    q11 = q11_availability(payloads[Q11_TURN])
    targeted = targeted_availability(payloads)
    delivered_at_q11 = list(records[Q11_TURN]["selected_ids"])

    return {
        "arm": arm,
        "run_directory": _repo_relative(directory),
        "q11_availability": {
            "fact_count": q11["fact_count"],
            "domain_count": q11["domain_count"],
            "per_domain": q11["per_domain"],
            "items": q11["items"],
        },
        "targeted_per_probe": targeted,
        "targeted_totals": {
            "available": sum(row["available_count"] for row in targeted.values()),
            "items": sum(row["item_count"] for row in targeted.values()),
        },
        "path_split": path_split(records),
        "oracle_overlap_at_q11": oracle_overlap(delivered_at_q11),
        "not_an_outcome": (
            "Delivery only. The registered outcome is the scored rubric "
            "(section 6.1); availability is never the bar."
        ),
    }


def build(run_dirs: dict[str, Path]) -> dict:
    return {
        "study": "011",
        "section": "6.2",
        "arms": {arm: assess_arm(arm, path) for arm, path in run_dirs.items()},
        "outcome_is_elsewhere": (
            "Scores (item 1) and paired per-question gains and losses "
            "(item 6) are produced after the blind scores are committed."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for arm in ARMS:
        parser.add_argument(f"--dir-{arm.lower()}", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=STUDY_ROOT / "analysis" / "delivery_by_arm.json",
    )
    args = parser.parse_args(argv)

    run_dirs = {arm: getattr(args, f"dir_{arm.lower()}") for arm in ARMS}
    try:
        result = build(run_dirs)
    except OutcomeError as error:
        print(f"STOP: {error}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for arm, row in result["arms"].items():
        print(
            f"arm {arm}: Q11 {row['q11_availability']['fact_count']}/17 "
            f"({row['q11_availability']['domain_count']} domains), "
            f"targeted {row['targeted_totals']['available']}/"
            f"{row['targeted_totals']['items']}, "
            f"K-only episodes {row['path_split']['totals']['k_only_episodes']}"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

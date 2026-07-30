from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from src.analysis.q4_packing_reanalysis import (
    PLANT_TURN,
    REPO_ROOT,
    _context_row,
    _ordered_candidates,
    _turn_55_id,
)
from src.memory.context_matched_stm import render_stm_payload


AS_ROOT = REPO_ROOT / "experiments" / "components" / "q4_packing"
CANDIDATE_MANIFEST = AS_ROOT / "artifacts" / "analysis" / "candidate_manifest.csv"
CONTEXT_LOG = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier6"
    / "runs"
    / "tier6_live_121_corrected_001"
    / "context_matched_stm"
    / "logs"
    / "context_match.jsonl"
)


def generate_reachability(output_dir: Path) -> dict:
    inputs = [CANDIDATE_MANIFEST, CONTEXT_LOG]
    before = _hash_paths(inputs)
    candidates = _ordered_candidates(_context_row())
    _verify_manifest(candidates)
    trace = trace_minimum_target_budget(candidates, _turn_55_id(candidates))
    after = _hash_paths(inputs)
    result = {
        "analysis": "AS-001 post-result diagnostic",
        "status": "PASS" if trace["target_selected"] and before == after else "FAIL",
        "decision_commit": "689a647e",
        "inference_calls": 0,
        "interpretation": (
            "This is the exact reachability boundary under the joint preserved "
            "rank order, greedy N-first packer, compact renderer, and character "
            "budget. It does not identify a separate primacy mechanism."
        ),
        "inputs_unchanged": before == after,
        "input_hashes_before": before,
        "input_hashes_after": after,
        **trace,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "reachability.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output_dir / "reachability.md").write_text(
        _render_markdown(result),
        encoding="utf-8",
        newline="\n",
    )
    return result


def trace_minimum_target_budget(
    candidates: list[dict],
    target_id: str,
) -> dict:
    budget = len(render_stm_payload([], []))
    transitions = []
    while True:
        state = _pack_state(candidates, budget)
        transitions.append(
            {
                "budget_chars": budget,
                "fitted_episodes": len(state["selected"]),
                "serialized_chars": len(state["payload"]),
                "target_selected": target_id in state["selected_ids"],
            }
        )
        if target_id in state["selected_ids"]:
            target = next(
                candidate
                for candidate in state["selected"]
                if str(candidate["id"]) == target_id
            )
            return {
                "target_turn": int(target["turn_number"]),
                "target_rank": next(
                    rank
                    for rank, candidate in enumerate(candidates, 1)
                    if str(candidate["id"]) == target_id
                ),
                "target_selected": True,
                "minimum_budget_chars": budget,
                "fitted_episodes_at_entry": len(state["selected"]),
                "serialized_chars_at_entry": len(state["payload"]),
                "selected_source_turns_at_entry": [
                    int(candidate["turn_number"])
                    for candidate in state["selected"]
                ],
                "transition_count_to_entry": len(transitions),
                "transition_trace": transitions,
            }
        next_budget = min(state["rejected_costs"], default=None)
        if next_budget is None:
            return {
                "target_turn": PLANT_TURN,
                "target_rank": None,
                "target_selected": False,
                "minimum_budget_chars": None,
                "transition_count_to_entry": len(transitions),
                "transition_trace": transitions,
            }
        if next_budget <= budget:
            raise AssertionError("Packing transition did not advance the budget")
        budget = next_budget


def _pack_state(candidates: list[dict], budget: int) -> dict:
    selected = []
    rejected_costs = []
    for candidate in candidates:
        attempted = render_stm_payload([*selected, candidate], [])
        if len(attempted) <= budget:
            selected.append(candidate)
        else:
            rejected_costs.append(len(attempted))
    payload = render_stm_payload(selected, [])
    return {
        "selected": selected,
        "selected_ids": [str(candidate["id"]) for candidate in selected],
        "payload": payload,
        "rejected_costs": [cost for cost in rejected_costs if cost > budget],
    }


def _verify_manifest(candidates: list[dict]) -> None:
    with CANDIDATE_MANIFEST.open(encoding="utf-8", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    observed = [
        (str(candidate["id"]), int(candidate["turn_number"]))
        for candidate in candidates
    ]
    expected = [
        (row["episode_id"], int(row["source_turn"]))
        for row in manifest
    ]
    if observed != expected:
        raise AssertionError("Reconstructed candidate order differs from manifest")


def _hash_paths(paths: list[Path]) -> dict[str, str]:
    return {
        path.relative_to(REPO_ROOT).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in paths
    }


def _render_markdown(result: dict) -> str:
    return "\n".join(
        [
            "# AS-001 Post-Result Rank-27 Reachability",
            "",
            f"**Status:** {result['status']}",
            "**Classification:** diagnostic; opened after the locked AS-001 result",
            "",
            "Under the unchanged compact renderer, preserved candidate order, and",
            "greedy N-first packer, turn 55 first enters at an exact budget of",
            f"**{result['minimum_budget_chars']:,} characters**. The resulting payload",
            f"uses {result['serialized_chars_at_entry']:,} characters and contains",
            f"{result['fitted_episodes_at_entry']} episodes.",
            "",
            f"The registered 32,000-character point is "
            f"{result['minimum_budget_chars'] - 32_000:,} characters below this",
            "reachability boundary. The locked 64,000-character sweep is also below",
            "it.",
            "",
            "This establishes a joint rank/packing/budget boundary. It does not",
            "identify primacy as a separate mechanism and does not restore the",
            "invalidated Branch D verdict.",
            "",
            "## Integrity",
            "",
            f"- Packing transitions evaluated: {result['transition_count_to_entry']}",
            f"- Inputs unchanged: {result['inputs_unchanged']}",
            "- Inference calls: 0",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=AS_ROOT / "artifacts" / "post_result_reachability",
    )
    args = parser.parse_args()
    result = generate_reachability(args.output_dir)
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

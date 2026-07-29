from src.analysis.q4_packing_reachability import (
    _pack_state,
    trace_minimum_target_budget,
)
from src.memory.context_matched_stm import render_stm_payload


def _candidate(candidate_id: str, turn: int, chars: int) -> dict:
    return {
        "id": candidate_id,
        "turn_number": turn,
        "user_message": "u" * chars,
        "assistant_message": "",
    }


def test_pack_state_matches_greedy_skip_behavior():
    candidates = [
        _candidate("large", 1, 100),
        _candidate("small", 2, 1),
    ]
    small_only = len(render_stm_payload([candidates[1]], []))

    state = _pack_state(candidates, small_only)

    assert state["selected_ids"] == ["small"]


def test_trace_finds_exact_first_target_transition():
    candidates = [
        _candidate("first", 1, 5),
        _candidate("target", 2, 7),
        _candidate("last", 3, 3),
    ]
    expected = len(render_stm_payload(candidates[:2], []))

    result = trace_minimum_target_budget(candidates, "target")

    assert result["target_selected"]
    assert result["minimum_budget_chars"] == expected
    assert result["target_rank"] == 2

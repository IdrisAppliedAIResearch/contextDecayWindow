from analysis.da009_role_pattern import role_pattern_pairs
from analysis.da010_analysis import allocate_turn_payloads


def _payload(selected: int = 0) -> dict:
    return {"comparison_key": "q", "duplicate_ordinal": 0, "seed_id": "s", "neighbor_id": "n",
            "selected_member_index": selected, "member_order": [selected, 1 - selected]}


def test_pair_then_turn_falls_back_only_on_pair_overflow() -> None:
    members = {"d": [{"speaker": "A", "text": "core"}, {"speaker": "B", "text": "base"}],
               "n": [{"speaker": "A", "text": "short", "dialogue_id": "x"},
                     {"speaker": "B", "text": "x" * 30, "dialogue_id": "y"}]}
    context = role_pattern_pairs([members["d"]])
    edge = {"comparison_key": "q", "duplicate_ordinal": 0, "seed_id": "s", "neighbor_id": "n"}
    payloads = {("q", 0, "s", "n"): _payload()}
    result = allocate_turn_payloads(context, ["d"], [edge], members, payloads, "PAIR_THEN_TURN", context.chars + len("0:short"))
    assert result["pair_admissions"] == 0
    assert result["fallback_admissions"] == 1
    assert result["linked_dialogue_ids"] == ["x"]


def test_atomic_continues_to_second_member_after_first_overflow() -> None:
    members = {"d": [{"speaker": "A", "text": "core"}, {"speaker": "B", "text": "base"}],
               "n": [{"speaker": "A", "text": "x" * 30, "dialogue_id": "x"},
                     {"speaker": "B", "text": "ok", "dialogue_id": "y"}]}
    context = role_pattern_pairs([members["d"]])
    edge = {"comparison_key": "q", "duplicate_ordinal": 0, "seed_id": "s", "neighbor_id": "n"}
    payloads = {("q", 0, "s", "n"): _payload()}
    result = allocate_turn_payloads(context, ["d"], [edge], members, payloads, "ATOMIC_TURNS", context.chars + len("1:ok"))
    assert result["linked_dialogue_ids"] == ["y"]
    assert result["member_overflows"] == 1

from analysis.da009_role_pattern import role_pattern_pairs
from analysis.da011_analysis import minimum_missing_cost, trace_fallback


def _fixture():
    members = {
        "d": [{"speaker": "A", "text": "core", "dialogue_id": "d0"},
              {"speaker": "B", "text": "base", "dialogue_id": "d1"}],
        "n": [{"speaker": "A", "text": "wrong", "dialogue_id": "n0"},
              {"speaker": "B", "text": "right", "dialogue_id": "n1"}],
    }
    edge = {"comparison_key": "q", "duplicate_ordinal": 0, "seed_id": "s", "neighbor_id": "n",
            "benefit_score": .9}
    payloads = {("q", 0, "s", "n"): {"member_order": [0, 1]}}
    return members, edge, payloads


def test_oracle_member_changes_only_overflow_fallback_choice() -> None:
    members, edge, payloads = _fixture()
    context = role_pattern_pairs([members["d"]])
    budget = context.chars + len("1:right")
    baseline = trace_fallback(context, ["d"], [edge], members, payloads, {"n1"}, budget=budget)
    oracle = trace_fallback(context, ["d"], [edge], members, payloads, {"n1"}, oracle_member=True, budget=budget)
    assert baseline["linked_dialogue_ids"] == ["n0"]
    assert oracle["linked_dialogue_ids"] == ["n1"]
    assert baseline["actions"][0]["pair_overflow"]
    assert baseline["actions"][0]["members"][1]["fits"]


def test_full_pair_fit_prevents_oracle_member_intervention() -> None:
    members, edge, payloads = _fixture()
    context = role_pattern_pairs([members["d"]])
    result = trace_fallback(context, ["d"], [edge], members, payloads, {"n1"}, oracle_member=True, budget=100)
    assert result["linked_dialogue_ids"] == ["n0", "n1"]
    assert result["actions"][0]["pair_admitted"]
    assert not result["actions"][0]["fallback_attempted"]


def test_minimum_missing_cost_uses_full_pair_when_both_members_required() -> None:
    members, _, _ = _fixture()
    context = role_pattern_pairs([members["d"]])
    assert minimum_missing_cost(context, ["n"], {"n0", "n1"}, members) == len("wrong\nright")
    assert minimum_missing_cost(context, ["n"], {"n1"}, members) == len("1:right")

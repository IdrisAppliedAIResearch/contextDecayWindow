from analysis.da009_role_pattern import role_pattern_pairs
from analysis.da010_payloads import member_order, payload_costs


def test_member_order_uses_weighted_coverage_then_source_index() -> None:
    members = [{"speaker": "A", "text": "project cedar"}, {"speaker": "B", "text": "launched 2024"}]
    order, coverage = member_order("when launched 2024", members, {"when": 1, "launched": 2, "2024": 3})
    assert order == (1, 0)
    assert coverage[1] > coverage[0]
    assert member_order("unmatched", members, {"unmatched": 1})[0] == (0, 1)


def test_payload_costs_charge_singletons_explicitly() -> None:
    context = role_pattern_pairs([[{"speaker": "A", "text": "x"}, {"speaker": "B", "text": "y"}]])
    pair = [{"speaker": "A", "text": "one"}, {"speaker": "B", "text": "two"}]
    full, turns = payload_costs(context, pair)
    assert full == len("one\ntwo")
    assert turns == (len("0:one"), len("1:two"))


def test_payload_cost_adds_new_speaker_dictionary_entry() -> None:
    context = role_pattern_pairs([[{"speaker": "A", "text": "x"}, {"speaker": "B", "text": "y"}]])
    full, turns = payload_costs(context, [{"speaker": "C", "text": "new"}])
    assert full == turns[0] == len("@2=C") + len("2:new")

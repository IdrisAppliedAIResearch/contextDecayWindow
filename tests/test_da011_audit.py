from analysis.da011_audit import carrier_first, classify_blocker


def test_blocker_hierarchy_is_mutually_exclusive() -> None:
    common = {"required_cost": 20, "initial_slack": 10, "arrival_slack": 0}
    assert classify_blocker(carrier_pair_count=2, both_members_required=True, wrong_member_fits=True, **common) == "MULTI_PAIR_CONJUNCTION"
    assert classify_blocker(carrier_pair_count=1, both_members_required=True, wrong_member_fits=True, **common) == "BOTH_MEMBER_CONJUNCTION"
    assert classify_blocker(carrier_pair_count=1, both_members_required=False, wrong_member_fits=True, **common) == "WRONG_MEMBER"
    assert classify_blocker(carrier_pair_count=1, both_members_required=False, wrong_member_fits=False,
                            required_cost=8, initial_slack=10, arrival_slack=3) == "PRIOR_CONSUMPTION"
    assert classify_blocker(carrier_pair_count=1, both_members_required=False, wrong_member_fits=False,
                            required_cost=11, initial_slack=10, arrival_slack=3) == "BASE_CAPACITY"


def test_carrier_first_is_a_stable_partition() -> None:
    edges = [{"neighbor_id": "a", "rank": 1}, {"neighbor_id": "b", "rank": 2}, {"neighbor_id": "c", "rank": 3}]
    assert carrier_first(edges, {"b", "c"}) == [edges[1], edges[2], edges[0]]

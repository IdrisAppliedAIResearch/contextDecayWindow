from analysis.da014_audit import classify


def test_conjunction_precedes_capacity() -> None:
    missing = {"a", "b"}
    carriers = {"x": {"a"}, "y": {"b"}}
    initial = {key: {"initial_slack": 1, "full_cost": 10, "turn_costs": [10, 10]} for key in carriers}
    arrival = {key: {"arrival_slack": 0, "full_cost": 10, "turn_costs": [10, 10], "selected_member": 0} for key in carriers}
    label, detail = classify(missing, carriers, initial, arrival, {"x": ("a", "z"), "y": ("b", "w")})
    assert label == "MULTI_CARRIER_CONJUNCTION"
    assert detail["minimum_carriers"] == 2


def test_wrong_member_precedes_prior_consumption() -> None:
    missing = {"b"}
    carriers = {"x": {"b"}}
    initial = {"x": {"initial_slack": 10, "full_cost": 12, "turn_costs": [2, 3]}}
    arrival = {"x": {"arrival_slack": 3, "full_cost": 12, "turn_costs": [2, 3], "selected_member": 0}}
    label, _ = classify(missing, carriers, initial, arrival, {"x": ("a", "b")})
    assert label == "WRONG_MEMBER_CHOICE"

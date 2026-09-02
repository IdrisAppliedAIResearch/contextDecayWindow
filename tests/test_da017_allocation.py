from analysis.da017_allocation import _tie


def test_benefit_tie_preserves_seed_direction_neighbor() -> None:
    prior = {"neighbor_id": "b", "features": {"seed_rank": 2, "signed_direction": -1}}
    following = {"neighbor_id": "a", "features": {"seed_rank": 2, "signed_direction": 1}}
    assert _tie(prior) < _tie(following)

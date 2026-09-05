from analysis.da004_pack_features import perturbation_features


def test_full_perturbation_counts_downstream_and_displaced() -> None:
    edge = {
        "features": {}, "neighbor_id": "n", "direct_selected_ids": ["s", "d"],
        "counterfactual_selected_ids": ["s", "n", "x"], "displaced_ids": ["d"],
    }
    candidates = {
        "s": {"chars": 10, "direct_score": .9}, "d": {"chars": 8, "direct_score": .4},
        "n": {"chars": 6, "direct_score": .2}, "x": {"chars": 4, "direct_score": .3},
    }
    texts = {"s": "alpha", "d": "beta", "n": "gamma", "x": "year 2024"}
    from analysis import da004_pack_features as module
    original = module.FEATURES
    module.FEATURES = module.SET_FEATURES
    try:
        result = perturbation_features(edge, candidates, texts, "what year 2024", {"what": 1, "year": 1, "2024": 1})
    finally:
        module.FEATURES = original
    assert result["added_count"] == 2
    assert result["downstream_count"] == 1
    assert result["set_displaced_count"] == 1
    assert result["added_query_coverage"] == 2 / 3
    assert result["balance_chars"] == 2
    assert result["changed_identity_count"] == 3

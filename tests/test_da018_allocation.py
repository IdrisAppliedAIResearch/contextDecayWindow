from analysis.da018_allocation import uncovered_coverage, utility


def test_frozen_utility_rewards_uncovered_terms_and_penalizes_cost_and_seed_rank() -> None:
    idf = {"a": 1.0, "b": 3.0}
    low = uncovered_coverage(frozenset({"a", "b"}), frozenset({"a"}), set(), idf)
    high = uncovered_coverage(frozenset({"a", "b"}), frozenset({"b"}), set(), idf)
    assert high > low
    assert utility("MARGINAL_UTILITY", .5, 1, 10, high) > utility("MARGINAL_UTILITY", .5, 2, 10, high)
    assert utility("MARGINAL_UTILITY", .5, 1, 10, high) > utility("MARGINAL_UTILITY", .5, 1, 20, high)


def test_covered_query_terms_have_zero_marginal_coverage() -> None:
    assert uncovered_coverage(frozenset({"x"}), frozenset({"x"}), {"x"}, {"x": 2.0}) == 0.0


def test_negative_cosine_has_zero_cost_utility_but_preserves_raw_order() -> None:
    assert utility("PAYLOAD_COSINE", -.2, 1, 5, 0.0) == -.2
    assert utility("COSINE_PER_CHAR", -.2, 1, 5, 0.0) == 0.0


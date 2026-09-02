from analysis.da003_edge_analysis import distribution


def test_distribution_preserves_empty_and_quantiles() -> None:
    assert distribution([])["n"] == 0
    result = distribution([1, 2, 3])
    assert result["n"] == 3
    assert result["p50"] == 2

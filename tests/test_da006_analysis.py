from analysis.da006_analysis import distribution


def test_distribution_uses_fixed_quantiles() -> None:
    assert distribution([1, 2, 3, 4, 5])["p50"] == 3

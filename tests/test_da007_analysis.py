from analysis.da007_analysis import distribution


def test_distribution_is_stable() -> None:
    assert distribution([1, 2, 3])["p50"] == 2

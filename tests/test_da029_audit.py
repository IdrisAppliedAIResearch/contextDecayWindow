from analysis.da029_audit import distribution


def test_distribution_median() -> None:
    assert distribution([1, 2, 3])["p50"] == 2.0


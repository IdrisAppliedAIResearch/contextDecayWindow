from analysis.da015_analysis import PHRASE_SHA256, TRACE_SHA256


def test_sealed_hashes_are_locked() -> None:
    assert len(PHRASE_SHA256) == 64
    assert len(TRACE_SHA256) == 64

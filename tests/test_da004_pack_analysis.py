from analysis.da004_pack_analysis import fast_auc


def test_fast_auc_counts_wins_and_ties() -> None:
    assert fast_auc([1, 2, 3, 4], [0, 0, 1, 1]) == 1
    assert fast_auc([1, 1], [0, 1]) == .5
    assert fast_auc([2, 1], [0, 1]) == 0

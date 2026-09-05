from analysis.da019_substitution import duplicate_rejection


def test_synthetic_duplicate_branch_does_not_reject_new_identity() -> None:
    assert duplicate_rejection("same", {"same"}, "tail") == ("DUPLICATE",)
    assert duplicate_rejection("fresh", {"same"}, "tail") == ()


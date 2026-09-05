from analysis.da019_substitution import duplicate_rejection, guard, unique_query_tokens


def test_unique_query_tokens_excludes_terms_already_retained() -> None:
    assert unique_query_tokens(frozenset({"a", "b"}), frozenset({"a", "b"}), frozenset({"a"})) == frozenset({"b"})


def test_guard_requires_fit_lexical_preservation_and_semantic_dominance() -> None:
    assert guard(True, frozenset({"x"}), frozenset({"x", "y"}), .4, .4) == (True, ())
    accepted, reasons = guard(False, frozenset({"x"}), frozenset(), .5, .4)
    assert not accepted
    assert reasons == ("FIT", "LEXICAL", "SEMANTIC")


def test_duplicate_rejection_is_identity_exact_and_inert_for_new_neighbor() -> None:
    assert duplicate_rejection("kept", {"kept"}, "tail") == ("DUPLICATE",)
    assert duplicate_rejection("tail", {"kept"}, "tail") == ("DUPLICATE",)
    assert duplicate_rejection("new", {"kept"}, "tail") == ()


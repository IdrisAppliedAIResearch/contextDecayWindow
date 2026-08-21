from __future__ import annotations

import pytest

from analysis.hh001_endpoints import (
    HH001EndpointError,
    aggregate,
    contains_gold,
    majority,
    normalize,
    sign_check,
    unanimity_rate,
)


class TestNormalize:
    def test_casefold_and_punctuation(self):
        assert normalize("Melanie's Car!") == "melanie s car"

    def test_whitespace_collapses(self):
        assert normalize("a   b\n\tc") == "a b c"

    def test_thousands_separators_removed(self):
        assert normalize("1,200") == "1200"

    def test_leading_zeros_canonicalized(self):
        assert normalize("007") == "7"

    def test_month_names_map_to_ordinals(self):
        assert normalize("7 May 2023") == normalize("7 may 2023")
        assert normalize("May") == "5"
        assert normalize("Sept") == normalize("September")

    def test_ordinal_suffix_dropped(self):
        assert normalize("7th May") == normalize("7 May")

    def test_unicode_normalized(self):
        assert normalize("café") == normalize("café")

    def test_none_and_empty(self):
        assert normalize(None) == ""
        assert normalize("") == ""

    def test_does_not_reorder_ambiguous_dates(self):
        # 05/07 is genuinely ambiguous; guessing would make the endpoint wrong
        # rather than strict. These must stay distinct.
        assert normalize("5 7 2023") != normalize("7 5 2023")


class TestContainsGold:
    def test_exact(self):
        assert contains_gold("The answer is Paris", "Paris")

    def test_case_and_punctuation_insensitive(self):
        assert contains_gold("paris!", "Paris")

    def test_paraphrase_is_missed_by_design(self):
        # Containment is the weaker endpoint. It is allowed to miss this.
        assert not contains_gold("the capital of France", "Paris")

    def test_token_boundary_respected(self):
        # The whole reason for token-sequence matching rather than substring.
        assert not contains_gold("she is 120 years old", "12")
        assert contains_gold("she is 12 years old", "12")

    def test_multiword_gold_must_be_contiguous(self):
        assert contains_gold("he bought a red bicycle today", "red bicycle")
        assert not contains_gold("red car and blue bicycle", "red bicycle")

    def test_integer_gold_coerced(self):
        assert contains_gold("there were 6", str(6))

    def test_gold_longer_than_answer(self):
        assert not contains_gold("no", "a very long reference answer indeed")

    def test_empty_gold_raises(self):
        with pytest.raises(HH001EndpointError):
            contains_gold("anything", "!!!")

    def test_empty_answer_is_false_not_error(self):
        assert not contains_gold("", "Paris")


class TestMajority:
    def test_odd_majorities(self):
        assert majority([True, True, False])
        assert not majority([True, False, False])
        assert majority([True])

    def test_even_count_refused(self):
        # An even count can tie, and a tie would need a tiebreak rule that
        # nobody registered.
        with pytest.raises(HH001EndpointError):
            majority([True, False])

    def test_empty_refused(self):
        with pytest.raises(HH001EndpointError):
            majority([])


class TestAggregate:
    def test_both_endpoints_folded(self):
        outcome = aggregate("k", "A2", [True, True, False], [True, False, False])
        assert outcome.judged_correct is True
        assert outcome.contained is False
        assert outcome.replicates == 3

    def test_mismatched_replicate_counts_refused(self):
        with pytest.raises(HH001EndpointError):
            aggregate("k", "A2", [True, True, False], [True, False])

    def test_unanimity_flags(self):
        unanimous = aggregate("k", "A2", [True, True, True], [False, False, False])
        assert unanimous.judged_unanimous
        assert unanimous.contained_unanimous
        split = aggregate("k", "A2", [True, True, False], [True, True, True])
        assert not split.judged_unanimous
        assert split.contained_unanimous


class TestUnanimityRate:
    def test_measures_this_instrument_not_the_carried_band(self):
        outcomes = [
            aggregate("a", "A2", [True, True, True], [True, True, True]),
            aggregate("b", "A2", [True, True, False], [True, True, True]),
        ]
        assert unanimity_rate(outcomes, "judged") == 0.5
        assert unanimity_rate(outcomes, "contained") == 1.0

    def test_unknown_endpoint(self):
        outcomes = [aggregate("a", "A2", [True], [True])]
        with pytest.raises(HH001EndpointError):
            unanimity_rate(outcomes, "vibes")


class TestSignCheck:
    def test_agreement_permits_a_claim(self):
        check = sign_check(12, 4)
        assert check.agree
        assert not check.blocks_directional_claim

    def test_reversal_blocks_the_claim(self):
        # NF-003's shape: the loose measure said +49/0, the strict one said
        # 26 gains and 63 losses. Opposite sign, not a smaller effect.
        check = sign_check(49, -37)
        assert not check.agree
        assert check.blocks_directional_claim

    def test_negative_agreement_still_agrees(self):
        check = sign_check(-8, -3)
        assert check.agree

    def test_tie_is_not_a_reversal(self):
        assert sign_check(0, 5).agree
        assert sign_check(5, 0).agree
        assert sign_check(0, 0).agree

from __future__ import annotations

import os
from pathlib import Path

import pytest

from analysis.hh001_corpus import (
    HH001CorpusError,
    Item,
    adversarial_population,
    load_corpus,
    primary_population,
    select_subsample,
    subsample_manifest,
)

DATASET = Path(
    os.environ.get("HH001_LOCOMO_PATH", r"C:\Users\muzaf\Downloads\locomo10.json")
)

corpus_required = pytest.mark.skipif(
    not DATASET.is_file(),
    reason="LoCoMo bytes are not committed; bound by manifest, not by copy",
)


def item(key, sample_id="conv-26", category=1, answerable=True):
    return Item(
        comparison_key=key,
        sample_id=sample_id,
        source_index=0,
        category=category,
        question="q?",
        gold_answer="a",
        answerable=answerable,
        evidence_dialogue_ids=(),
    )


class TestSubsampleSelection:
    def test_is_a_pure_function_of_seed_and_key(self):
        items = [item(f"k{i:03d}") for i in range(100)]
        first = select_subsample(items, 20)
        second = select_subsample(list(reversed(items)), 20)
        assert [i.comparison_key for i in first] == [i.comparison_key for i in second]

    def test_different_seed_selects_differently(self):
        items = [item(f"k{i:03d}") for i in range(100)]
        a = {i.comparison_key for i in select_subsample(items, 20, "5005")}
        b = {i.comparison_key for i in select_subsample(items, 20, "9999")}
        assert a != b

    def test_size_is_exact(self):
        items = [item(f"k{i:03d}") for i in range(100)]
        for size in (1, 7, 33, 99):
            assert len(select_subsample(items, size)) == size

    def test_oversize_returns_everything(self):
        items = [item(f"k{i}") for i in range(5)]
        assert len(select_subsample(items, 500)) == 5

    def test_strata_are_proportional(self):
        # Largest-remainder allocation, so the sample's stratum shape follows
        # the population's rather than whichever stratum iterates first.
        items = [item(f"a{i}", "conv-26", 1) for i in range(80)]
        items += [item(f"b{i}", "conv-30", 2) for i in range(20)]
        chosen = select_subsample(items, 10)
        by_stratum: dict[str, int] = {}
        for entry in chosen:
            by_stratum[entry.stratum] = by_stratum.get(entry.stratum, 0) + 1
        assert by_stratum == {"conv-26/1": 8, "conv-30/2": 2}

    def test_manifest_digest_is_stable(self):
        items = [item(f"k{i:03d}") for i in range(50)]
        a = subsample_manifest(items, 10)
        b = subsample_manifest(items, 10)
        assert a["selection_digest"] == b["selection_digest"]
        assert a["size"] == 10

    def test_negative_size_refused(self):
        with pytest.raises(HH001CorpusError):
            select_subsample([item("k")], -1)


class TestPopulationSplit:
    def test_adversarial_items_are_not_in_the_primary(self):
        # AGENTS.md §7 forbids scoring an answerless item above zero. An
        # adversarial record's correct behaviour is a refusal.
        items = [item("a"), item("b", answerable=False, category=5)]
        assert [i.comparison_key for i in primary_population(items)] == ["a"]
        assert [i.comparison_key for i in adversarial_population(items)] == ["b"]


@corpus_required
class TestAgainstTheRealCorpus:
    """Reads the locked bytes. No model, no server, no generation."""

    @pytest.fixture(scope="class")
    def corpus(self):
        return load_corpus(DATASET)

    def test_holdout_shape_matches_nf004(self, corpus):
        conversations, items = corpus
        assert len(conversations) == 6
        assert {c.sample_id for c in conversations} == {
            "conv-26", "conv-30", "conv-43", "conv-44", "conv-49", "conv-50",
        }
        # NF-004's canonical de-duplication: 1,104 unique records, zero exact
        # duplicates.
        assert len(items) == 1_104

    def test_malformed_evidence_reconciles_to_nf004s_primary(self, corpus):
        # NF-004's primary was the 1,098 records whose evidence list fully
        # resolves. The judged endpoint here does not need evidence, so those
        # six stay in the primary population and are excluded only from the
        # availability secondary.
        _, items = corpus
        complete = [entry for entry in items if entry.evidence_complete]
        assert len(complete) == 1_098

    def test_population_split_counts(self, corpus):
        _, items = corpus
        answerable = primary_population(items)
        adversarial = adversarial_population(items)
        assert len(answerable) + len(adversarial) == len(items)
        # Category 5 is LoCoMo's adversarial class.
        assert all(i.category == 5 for i in adversarial)
        assert len(answerable) == 850
        assert len(adversarial) == 254

    def test_availability_secondary_excludes_unjoinable_items(self, corpus):
        _, items = corpus
        # Nine records resolve no evidence at all and six name a dialogue id
        # the conversation lacks; neither can join NF-004's availability rows.
        assert sum(1 for entry in items if not entry.availability_scorable) >= 9

    def test_every_gold_answer_is_a_non_empty_string(self, corpus):
        _, items = corpus
        for entry in primary_population(items):
            assert isinstance(entry.gold_answer, str)
            assert entry.gold_answer.strip()

    def test_integer_answers_are_coerced(self, corpus):
        _, items = corpus
        # Six holdout answers are integers in the source.
        numeric = [i for i in primary_population(items) if i.gold_answer.isdigit()]
        assert numeric

    def test_conversation_rendering_matches_candidate_rendering(self, corpus):
        conversations, _ = corpus
        for conversation in conversations:
            # Every pair candidate's text must appear verbatim in the full
            # render, or A1 and A2 are not reading the same conversation.
            for source in conversation.record.candidates[:20]:
                assert source.candidate.text in conversation.full_text

    def test_full_context_can_exceed_the_reader_window(self, corpus):
        conversations, _ = corpus
        longest = max(c.chars for c in conversations)
        # 90,034 characters at the top end. A1 must record truncation rather
        # than silently deliver a partial ceiling.
        assert longest > 80_000

    def test_subsample_covers_every_conversation(self, corpus):
        _, items = corpus
        chosen = select_subsample(primary_population(items), 300)
        assert len({entry.sample_id for entry in chosen}) == 6

    def test_dataset_hash_is_verified_on_load(self, tmp_path):
        bad = tmp_path / "locomo10.json"
        bad.write_text("[]", encoding="utf-8")
        with pytest.raises(HH001CorpusError):
            load_corpus(bad)

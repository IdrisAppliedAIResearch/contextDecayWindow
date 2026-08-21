from __future__ import annotations

import numpy as np
import pytest

from analysis.hh001_arms import (
    BLOCK_SEPARATOR,
    CdwPairArm,
    FullContextArm,
    HH001ArmError,
    Mem0Arm,
    NoMemoryArm,
    RagFixedArm,
    _mem0_memory_texts,
    chunk_text,
)
from analysis.hh001_corpus import Conversation, Item
from analysis.hh001_stats import (
    HH001StatsError,
    exact_sign_test,
    exact_sign_test_two_sided,
    paired,
    reachability,
)
from analysis.hh001_endpoints import aggregate
from analysis.nf004_mechanism import Candidate
from analysis.nf004_measurement import CandidateSource, ConversationRecord


def make_conversation(texts, sample_id="conv-26"):
    sources = []
    for index, text in enumerate(texts):
        sources.append(
            CandidateSource(
                Candidate(
                    identity=f"cand-{index}",
                    session_identity="session_1",
                    session_order=0,
                    pair_order=index,
                    text=text,
                    chars=len(text),
                ),
                (f"D{index}",),
            )
        )
    record = ConversationRecord(sample_id, tuple(sources), ())
    full = "\n".join(texts)
    return Conversation(sample_id, record, full, len(texts))


def make_item(question="what colour?", key="k1", sample_id="conv-26"):
    return Item(
        comparison_key=key,
        sample_id=sample_id,
        source_index=0,
        category=1,
        question=question,
        gold_answer="red",
        answerable=True,
        evidence_dialogue_ids=("D0",),
    )


def keyword_embedder(vocabulary):
    """Deterministic bag-of-words embedder, so arm tests need no model."""

    def embed(text: str) -> np.ndarray:
        vector = np.zeros(1024, dtype=np.float32)
        lowered = text.lower()
        for index, word in enumerate(vocabulary):
            if word in lowered:
                vector[index] = 1.0
        vector[1023] = 0.01  # keeps the norm non-zero for empty overlap
        return vector

    return embed


class TestNoMemoryArm:
    def test_delivers_nothing(self):
        block = NoMemoryArm().block(make_item(), make_conversation(["a: hi"]), 16_000)
        assert block.text == ""
        assert block.chars == 0
        assert not block.truncated


class TestFullContextArm:
    def test_delivers_whole_conversation_ignoring_budget(self):
        conv = make_conversation(["a: " + "x" * 10_000, "b: " + "y" * 10_000])
        block = FullContextArm().block(make_item(), conv, 16_000)
        assert block.chars > 16_000
        assert block.detail["unbudgeted"] is True
        assert not block.truncated

    def test_records_truncation_against_the_reader_window(self):
        # Holdout conversations run to 90,034 characters. A ceiling that
        # silently truncates is not a ceiling.
        conv = make_conversation(["a: " + "x" * 5_000])
        block = FullContextArm(reader_char_allowance=1_000).block(
            make_item(), conv, 16_000
        )
        assert block.truncated
        assert block.chars == 1_000
        assert block.detail["source_chars"] > 1_000


class TestCdwPairArm:
    def test_ranks_by_own_pair_cosine_and_respects_budget(self):
        embed = keyword_embedder(["red", "blue", "green"])
        conv = make_conversation(
            ["a: the car is blue", "b: the bicycle is red", "c: the door is green"]
        )
        arm = CdwPairArm(embed)
        block = arm.block(make_item("which thing is red?"), conv, 16_000)
        assert block.text.startswith("b: the bicycle is red")
        assert block.units_delivered == 3

    def test_budget_binds_and_marks_truncation(self):
        embed = keyword_embedder(["red", "blue", "green"])
        conv = make_conversation(
            ["a: the car is blue", "b: the bicycle is red", "c: the door is green"]
        )
        block = CdwPairArm(embed).block(make_item("which thing is red?"), conv, 25)
        assert block.chars <= 25
        assert block.truncated
        assert block.units_delivered < block.units_available

    def test_empty_candidate_set_refused(self):
        with pytest.raises(HH001ArmError):
            CdwPairArm(keyword_embedder(["red"])).block(
                make_item(), make_conversation([]), 16_000
            )


class TestChunking:
    def test_covers_the_whole_text(self):
        text = "".join(str(i % 10) for i in range(2_500))
        chunks = chunk_text(text, 1_000, 200)
        assert "".join(dict.fromkeys(chunks))  # non-empty
        assert chunks[0] == text[:1_000]
        # every character appears in at least one chunk
        assert set(text) <= set("".join(chunks))

    def test_overlap_must_be_below_size(self):
        with pytest.raises(HH001ArmError):
            chunk_text("abc", 10, 10)

    def test_zero_size_refused(self):
        with pytest.raises(HH001ArmError):
            chunk_text("abc", 0, 0)

    def test_empty_text(self):
        assert chunk_text("", 10, 2) == ()


class TestRagFixedArm:
    def test_ranks_chunks_and_fills_budget(self):
        embed = keyword_embedder(["red", "blue"])
        conv = make_conversation(["a: " + "blue " * 100, "b: " + "red " * 100])
        block = RagFixedArm(embed, chunk_size=100, chunk_overlap=20).block(
            make_item("which is red?"), conv, 16_000
        )
        assert "red" in block.text

    def test_budget_binds(self):
        embed = keyword_embedder(["red", "blue"])
        conv = make_conversation(["a: " + "blue " * 100, "b: " + "red " * 100])
        block = RagFixedArm(embed, chunk_size=100, chunk_overlap=20).block(
            make_item("which is red?"), conv, 150
        )
        assert block.chars <= 150
        assert block.truncated


class TestMem0ResultParsing:
    def test_bare_list_of_dicts(self):
        assert _mem0_memory_texts([{"memory": "a"}, {"memory": "b"}]) == ["a", "b"]

    def test_results_envelope(self):
        assert _mem0_memory_texts({"results": [{"memory": "a"}]}) == ["a"]

    def test_text_and_content_keys(self):
        assert _mem0_memory_texts([{"text": "a"}, {"content": "b"}]) == ["a", "b"]

    def test_bare_strings(self):
        assert _mem0_memory_texts(["a", "b"]) == ["a", "b"]

    def test_unknown_envelope_raises_rather_than_returning_empty(self):
        # A silently empty block would read downstream as an arm that
        # retrieved nothing, which is a mechanism result, not a parse failure.
        with pytest.raises(HH001ArmError):
            _mem0_memory_texts({"data": []})
        with pytest.raises(HH001ArmError):
            _mem0_memory_texts([{"id": 1}])

    def test_arm_packs_within_budget(self):
        class FakeClient:
            # Mem0 2.x signature, observed against 2.0.18: keyword-only
            # `top_k`, `threshold` and `filters`. Positional `user_id`/`limit`
            # are rejected by the real client, so the fake rejects them too.
            def search(self, query, *, top_k, threshold, filters):
                assert "user_id" in filters
                return {"results": [{"memory": "x" * 40} for _ in range(10)]}

        arm = Mem0Arm(lambda: FakeClient())
        block = arm.block(make_item(), make_conversation(["a: hi"]), 100)
        assert block.chars <= 100
        assert block.truncated


class TestExactSignTest:
    def test_matches_nf004_registered_values(self):
        # NF-004 §6 states these exact reachability configurations.
        assert exact_sign_test(6, 0) == pytest.approx(0.015625)
        assert exact_sign_test(4, 1) == pytest.approx(0.1875)
        assert exact_sign_test(1, 1) == pytest.approx(0.75)

    def test_no_discordant_pairs(self):
        assert exact_sign_test(0, 0) == 1.0

    def test_two_sided_is_bounded(self):
        assert exact_sign_test_two_sided(5, 5) <= 1.0
        assert exact_sign_test_two_sided(10, 0) == pytest.approx(2 * 0.5**10)

    def test_negative_counts_refused(self):
        with pytest.raises(HH001StatsError):
            exact_sign_test(-1, 2)


class TestPaired:
    def outcomes(self, arm, values):
        return {
            key: aggregate(key, arm, [v], [v]) for key, v in values.items()
        }

    def test_pairs_by_key_and_counts_correctly(self):
        t = self.outcomes("A2", {"a": True, "b": True, "c": False})
        c = self.outcomes("A3", {"a": True, "b": False, "c": True})
        result = paired(t, c, treatment_name="A2", control_name="A3")
        assert (result.gains, result.losses, result.ties) == (1, 1, 1)
        assert result.net == 0
        assert result.n == 3
        assert result.discordance_rate == pytest.approx(2 / 3)

    def test_misaligned_keys_refused(self):
        # A positional pairing would silently misalign; this must stop.
        t = self.outcomes("A2", {"a": True, "b": True})
        c = self.outcomes("A3", {"a": True})
        with pytest.raises(HH001StatsError):
            paired(t, c, treatment_name="A2", control_name="A3")

    def test_no_shared_keys_refused(self):
        t = self.outcomes("A2", {"a": True})
        c = self.outcomes("A3", {"z": True})
        with pytest.raises(HH001StatsError):
            paired(t, c, treatment_name="A2", control_name="A3")

    def test_ratio_when_no_losses(self):
        t = self.outcomes("A2", {"a": True})
        c = self.outcomes("A3", {"a": False})
        result = paired(t, c, treatment_name="A2", control_name="A3")
        assert result.ratio == float("inf")


class TestReachability:
    def test_both_directions_possible_at_a_real_sample_size(self):
        # PF4's question asked before any number exists. DMR-001 locked a bar
        # that was unreachable by construction.
        report = reachability(300)
        assert report["reachable"]
        assert report["smallest_all_gain_discordant_reaching_alpha"] == 5
        assert report["null_reachable"] and report["reversal_reachable"]

    def test_tiny_sample_cannot_reach_alpha(self):
        report = reachability(3)
        assert report["smallest_all_gain_discordant_reaching_alpha"] is None
        assert not report["reachable"]

    def test_zero_refused(self):
        with pytest.raises(HH001StatsError):
            reachability(0)


class TestBudgetIsChargedOnTheDeliveredString:
    """Every budgeted arm is charged len() of what the reader actually gets.

    A2 overran a 16,000-character budget by 120 in the timing pilot: NF-004's
    packer charges candidate text only, and the rendered block adds two
    characters per join. Charging one arm for its separators and not another
    would be a thumb on the scale.
    """

    def conv(self, n, width):
        return make_conversation([f"s{i}: " + ("x" * width) for i in range(n)])

    def test_a2_never_exceeds_its_budget(self):
        embed = keyword_embedder(["x"])
        conv = self.conv(80, 200)
        for budget in (0, 1, 205, 500, 4_000, 16_000):
            block = CdwPairArm(embed).block(make_item(), conv, budget)
            assert block.chars <= budget, f"budget {budget}"

    def test_a4_never_exceeds_its_budget(self):
        embed = keyword_embedder(["x"])
        conv = self.conv(80, 200)
        for budget in (0, 1, 205, 500, 4_000, 16_000):
            block = RagFixedArm(embed, chunk_size=200, chunk_overlap=40).block(
                make_item(), conv, budget
            )
            assert block.chars <= budget, f"budget {budget}"

    def test_a2_charges_the_separator_not_just_the_text(self):
        # Two 10-char units cost 10 + 2 + 10 = 22, not 20.
        embed = keyword_embedder(["x"])
        conv = make_conversation(["a" * 10, "b" * 10])
        assert CdwPairArm(embed).block(make_item(), conv, 21).units_delivered == 1
        assert CdwPairArm(embed).block(make_item(), conv, 22).units_delivered == 2

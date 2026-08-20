from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from analysis.hh001_arms import NoMemoryArm
from analysis.hh001_commitments import (
    Commitments,
    HH001CommitmentError,
    default_commitments,
    verify_run,
)
from analysis.hh001_cost import (
    CountingClient,
    CountingEmbedder,
    HH001CostError,
    Ledger,
    assert_zero_generative,
)
from analysis.hh001_prompt import (
    HH001PromptError,
    blinded_surface,
    parse_judge_verdict,
    render_reader_prompt,
    template_manifest,
)
from analysis.hh001_run import (
    Answer,
    HH001RunError,
    analyze,
    build_outcomes,
    generate_arm,
    judge_answers,
    run,
    seal_answers,
)

from analysis.hh001_corpus import Conversation, Item
from analysis.nf004_mechanism import Candidate
from analysis.nf004_measurement import CandidateSource, ConversationRecord


def make_conversation(texts, sample_id="conv-26"):
    sources = tuple(
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
        for index, text in enumerate(texts)
    )
    return Conversation(
        sample_id,
        ConversationRecord(sample_id, sources, ()),
        "\n".join(texts),
        len(texts),
    )


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


def commitments(size=2, replicates=3):
    return default_commitments(subsample_size=size, replicates=replicates)


class TestCommitments:
    def test_even_replicates_refused(self):
        with pytest.raises(HH001CommitmentError):
            default_commitments(subsample_size=10, replicates=4)

    def test_contrast_must_name_committed_arms(self):
        with pytest.raises(HH001CommitmentError):
            Commitments(
                arms=("A0",),
                primary_endpoint="judged",
                cross_check_endpoint="contained",
                budget_chars=16_000,
                subsample_size=10,
                replicates=3,
                contrast=("A2", "A3"),
            )

    def test_cross_check_must_differ_from_primary(self):
        with pytest.raises(HH001CommitmentError):
            Commitments(
                arms=("A2", "A3"),
                primary_endpoint="judged",
                cross_check_endpoint="judged",
                budget_chars=16_000,
                subsample_size=10,
                replicates=3,
                contrast=("A2", "A3"),
            )

    def test_development_replicates_flagged_against_confirmatory_minimum(self):
        assert commitments(replicates=3).below_confirmatory_replicates
        assert not commitments(replicates=5).below_confirmatory_replicates

    def test_digest_is_stable_and_roundtrips(self, tmp_path):
        c = commitments()
        path = tmp_path / "commitments.json"
        digest = c.write(path)
        assert digest == c.digest
        assert Commitments.load(path).digest == digest

    def test_dropping_an_arm_is_a_stop(self):
        c = commitments()
        with pytest.raises(HH001CommitmentError, match="did not run"):
            verify_run(
                c,
                arms_run=("A0_NO_MEMORY",),
                budget_chars=16_000,
                items_scored=2,
                replicates=3,
            )

    def test_shortened_sample_is_a_stop(self):
        c = commitments(size=100)
        with pytest.raises(HH001CommitmentError, match="Scored"):
            verify_run(
                c,
                arms_run=c.arms,
                budget_chars=16_000,
                items_scored=40,
                replicates=3,
            )

    def test_changed_budget_is_a_stop(self):
        c = commitments()
        with pytest.raises(HH001CommitmentError, match="Budget"):
            verify_run(
                c, arms_run=c.arms, budget_chars=32_000, items_scored=2, replicates=3
            )

    def test_changed_template_is_a_stop(self):
        c = default_commitments(
            subsample_size=2,
            replicates=3,
            template_manifest=template_manifest().as_dict(),
        )
        drifted = dict(c.template_manifest)
        drifted["reader_template_sha256"] = "0" * 64
        with pytest.raises(HH001CommitmentError, match="templates changed"):
            verify_run(
                c,
                arms_run=c.arms,
                budget_chars=16_000,
                items_scored=2,
                replicates=3,
                template_manifest=drifted,
            )


class TestPrompt:
    def test_only_the_block_varies(self):
        a = render_reader_prompt("Q?", "block one")
        b = render_reader_prompt("Q?", "block two")
        assert a.replace("block one", "BLOCK") == b.replace("block two", "BLOCK")

    def test_no_memory_arm_gets_the_same_shape(self):
        prompt = render_reader_prompt("Q?", "")
        assert "no record" in prompt
        assert prompt.rstrip().endswith("Answer:")

    def test_empty_question_refused(self):
        with pytest.raises(HH001PromptError):
            render_reader_prompt("   ", "block")

    def test_verdict_parsing(self):
        assert parse_judge_verdict("VERDICT: CORRECT\nREASON: same fact")[0] is True
        assert parse_judge_verdict("VERDICT: INCORRECT\nREASON: wrong")[0] is False
        assert parse_judge_verdict(" correct \nREASON: ok")[0] is True

    def test_reason_is_captured(self):
        _, reason = parse_judge_verdict("VERDICT: CORRECT\nREASON: matches gold")
        assert reason == "matches gold"

    def test_incorrect_is_not_read_as_correct(self):
        # "INCORRECT" contains "CORRECT" as a substring; this is the trap.
        assert parse_judge_verdict("VERDICT: INCORRECT")[0] is False

    def test_unparseable_verdict_raises_rather_than_defaulting(self):
        # A default would be a silent vote with a direction nobody registered.
        with pytest.raises(HH001PromptError):
            parse_judge_verdict("hmm, hard to say")
        with pytest.raises(HH001PromptError):
            parse_judge_verdict("")

    def test_reason_text_cannot_flip_the_verdict(self):
        assert parse_judge_verdict(
            "VERDICT: INCORRECT\nREASON: it would be correct if the year matched"
        )[0] is False


class TestBlinding:
    def rows(self):
        return [
            {
                "comparison_key": "k1",
                "arm": "A2_CDW_PAIR",
                "replicate": 0,
                "question": "Q?",
                "gold": "red",
                "answer": "red",
            },
            {
                "comparison_key": "k1",
                "arm": "A3_MEM0",
                "replicate": 0,
                "question": "Q?",
                "gold": "red",
                "answer": "blue",
            },
        ]

    def test_surface_carries_no_arm_identity(self):
        surface, mapping = blinded_surface(self.rows())
        serialized = json.dumps(surface)
        assert "A2_CDW_PAIR" not in serialized
        assert "A3_MEM0" not in serialized
        assert "replicate" not in serialized
        assert len(mapping) == 2

    def test_order_is_seeded_not_arm_order(self):
        surface, _ = blinded_surface(self.rows())
        assert [entry["blind_id"] for entry in surface] == sorted(
            entry["blind_id"] for entry in surface
        )

    def test_missing_field_refused(self):
        bad = self.rows()
        del bad[0]["gold"]
        with pytest.raises(HH001PromptError):
            blinded_surface(bad)


class TestCostLedger:
    def test_generative_and_embedding_counts_stay_separate(self):
        ledger = Ledger(arm="A2_CDW_PAIR")
        embed = CountingEmbedder(lambda t: np.zeros(4), ledger, "query")
        embed("hello")
        embed("world")
        assert sum(ledger.embedding_calls.values()) == 2
        assert sum(ledger.generative_calls.values()) == 0
        # The headline claim is "no generative calls", not "no calls".
        assert_zero_generative(ledger)

    def test_generative_call_in_a_call_free_path_is_a_stop(self):
        ledger = Ledger(arm="A2_CDW_PAIR")
        client = CountingClient(lambda p: {"usage": {}}, ledger, "query")
        client("prompt")
        with pytest.raises(HH001CostError):
            assert_zero_generative(ledger)

    def test_token_counts_from_llama_server_shape(self):
        ledger = Ledger(arm="A3_MEM0")
        client = CountingClient(
            lambda p: {"tokens_evaluated": 100, "tokens_predicted": 20}, ledger, "ingest"
        )
        client("prompt")
        payload = ledger.as_dict()
        assert payload["total_prompt_tokens"] == 100
        assert payload["total_completion_tokens"] == 20
        assert payload["by_phase"]["ingest"]["generative_calls"] == 1


class TestRunOrdering:
    def items(self, n=2):
        return [make_item(f"question {i}?", key=f"k{i}") for i in range(n)]

    def conversations(self):
        return {"conv-26": make_conversation(["a: the bicycle is red"])}

    def test_generate_respects_replicate_schedule(self):
        answers = generate_arm(
            NoMemoryArm(),
            self.items(2),
            self.conversations(),
            reader=lambda p, r=0: "red",
            budget=16_000,
            replicates=3,
        )
        assert len(answers) == 6
        assert sorted({a.replicate for a in answers}) == [0, 1, 2]

    def test_prompt_digest_is_shared_across_replicates(self):
        answers = generate_arm(
            NoMemoryArm(),
            self.items(1),
            self.conversations(),
            reader=lambda p, r=0: "red",
            budget=16_000,
            replicates=3,
        )
        assert len({a.prompt_sha256 for a in answers}) == 1

    def test_answers_are_sealed_before_judging(self, tmp_path):
        answers = generate_arm(
            NoMemoryArm(),
            self.items(1),
            self.conversations(),
            reader=lambda p, r=0: "red",
            budget=16_000,
            replicates=1,
        )
        path = tmp_path / "A0.json"
        seal = seal_answers(answers, path)
        assert path.is_file()
        assert len(seal) == 64
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["count"] == 1
        # Re-sealing identical answers reproduces the digest.
        assert seal_answers(answers, tmp_path / "again.json") == seal

    def test_reader_calls_are_actually_counted(self):
        # A ledger that is passed in and ignored would report zero calls for
        # every arm, which is the exact number this study has to earn.
        ledger = Ledger(arm="A0_NO_MEMORY")
        generate_arm(
            NoMemoryArm(),
            self.items(2),
            self.conversations(),
            reader=lambda p, r=0: "red",
            budget=16_000,
            replicates=3,
            ledger=ledger,
        )
        assert ledger.generative_calls["read"] == 6
        assert ledger.seconds["query"] > 0 or ledger.seconds["query"] == 0.0

    def test_missing_conversation_refused(self):
        with pytest.raises(HH001RunError):
            generate_arm(
                NoMemoryArm(),
                [make_item(sample_id="conv-99")],
                self.conversations(),
                reader=lambda p, r=0: "x",
                budget=16_000,
                replicates=1,
            )

    def test_missing_verdict_refused(self):
        answers = generate_arm(
            NoMemoryArm(),
            self.items(1),
            self.conversations(),
            reader=lambda p, r=0: "red",
            budget=16_000,
            replicates=1,
        )
        with pytest.raises(HH001RunError):
            build_outcomes(answers, {})


class TestEndToEndOrdering:
    """The whole pipeline with injected reader and judge. No model involved."""

    def build(self, a2_answer, a3_answer, judge_says):
        items = [make_item(f"q{i}?", key=f"k{i}") for i in range(3)]
        conversations = {"conv-26": make_conversation(["a: the bicycle is red"])}

        class FixedArm:
            def __init__(self, name, answer):
                self.name = name
                self.answer = answer

            def block(self, item, conversation, budget):
                return NoMemoryArm().block(item, conversation, budget)

        arms = [FixedArm(name, "") for name in (
            "A0_NO_MEMORY",
            "A1_FULL_CONTEXT",
            "A2_CDW_PAIR",
            "A3_MEM0",
            "A4_RAG_FIXED",
        )]
        return items, conversations, arms

    def test_full_run_produces_a_gated_result(self, tmp_path):
        items, conversations, arms = self.build("red", "blue", True)
        c = default_commitments(
            subsample_size=3,
            replicates=3,
            template_manifest=template_manifest().as_dict(),
        )
        result = run(
            arms,
            items,
            conversations,
            c,
            reader=lambda p, r=0: "red",
            judge=lambda p: "VERDICT: CORRECT\nREASON: ok",
            outcome_dir=tmp_path,
        )
        assert result["directional_claim_permitted"] is True
        assert result["below_confirmatory_replicates"] is True
        assert set(result["per_arm"]) == set(c.arms)
        assert len(result["answer_seals"]) == 5
        for arm in c.arms:
            assert (tmp_path / f"{arm}.json").is_file()

    def test_item_count_mismatch_is_a_stop(self, tmp_path):
        items, conversations, arms = self.build("red", "blue", True)
        c = default_commitments(subsample_size=99, replicates=3)
        with pytest.raises(HH001RunError):
            run(
                arms,
                items,
                conversations,
                c,
                reader=lambda p, r=0: "red",
                judge=lambda p: "VERDICT: CORRECT",
                outcome_dir=tmp_path,
            )

    def test_sign_disagreement_blocks_the_directional_claim(self):
        from analysis.hh001_endpoints import aggregate

        # Judge says A2 wins everywhere; containment says the reverse.
        treatment = {
            "k0": aggregate("k0", "A2_CDW_PAIR", [True], [False]),
            "k1": aggregate("k1", "A2_CDW_PAIR", [True], [False]),
        }
        control = {
            "k0": aggregate("k0", "A3_MEM0", [False], [True]),
            "k1": aggregate("k1", "A3_MEM0", [False], [True]),
        }
        c = default_commitments(subsample_size=2, replicates=1)
        result = analyze({"A2_CDW_PAIR": treatment, "A3_MEM0": control}, c)
        assert result["contrast"]["judged"]["net"] == 2
        assert result["contrast"]["contained"]["net"] == -2
        assert result["sign_check"]["blocks_directional_claim"] is True
        assert result["directional_claim_permitted"] is False

    def test_result_records_its_own_standing(self):
        from analysis.hh001_endpoints import aggregate

        outcomes = {
            "A2_CDW_PAIR": {"k": aggregate("k", "A2_CDW_PAIR", [True], [True])},
            "A3_MEM0": {"k": aggregate("k", "A3_MEM0", [False], [False])},
        }
        c = default_commitments(subsample_size=1, replicates=1)
        result = analyze(outcomes, c)
        assert "not confirmatory" in result["standing"]
        assert "published" in result["substrate"]


class TestPerCallCostIsRecorded:
    """Cost lives on the answer row, not only in an aggregate ledger.

    A report that can say "A1 spent 20k prompt tokens a call and A3 spent 500"
    needs the number per call. An aggregate cannot be broken back down, and
    prompt tokens are the axis these arms differ most on.
    """

    def reply(self, text="red", prompt_tokens=1234, completion_tokens=7):
        from analysis.hh001_reader import ReaderReply

        return ReaderReply(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cached_tokens=11,
            seconds=0.42,
            seed=5005,
            truncated=False,
        )

    def test_tokens_and_latency_survive_onto_the_row(self):
        answers = generate_arm(
            NoMemoryArm(),
            [make_item("q?", key="k0")],
            {"conv-26": make_conversation(["a: the bicycle is red"])},
            reader=lambda p, r=0: self.reply(),
            budget=16_000,
            replicates=1,
        )
        row = answers[0].as_dict()
        assert row["prompt_tokens"] == 1234
        assert row["completion_tokens"] == 7
        assert row["cached_tokens"] == 11
        assert row["seconds"] == 0.42
        assert row["seed"] == 5005
        assert "block_seconds" in row

    def test_seed_varies_with_replicate_so_unanimity_measures_something(self):
        # A fixed seed on an identical prompt makes every replicate identical
        # and the unanimity rate reads 1.0 by construction.
        from analysis.hh001_reader import LlamaReader

        reader = LlamaReader("http://127.0.0.1:9", seed_base=5005)
        seeds = {reader.seed_base + r for r in range(3)}
        assert seeds == {5005, 5006, 5007}
        assert reader.runtime_record()["seed_rule"] == "seed_base + replicate"

    def test_plain_string_readers_still_work(self):
        answers = generate_arm(
            NoMemoryArm(),
            [make_item("q?", key="k0")],
            {"conv-26": make_conversation(["a: hi"])},
            reader=lambda p, r=0: "plain",
            budget=16_000,
            replicates=1,
        )
        assert answers[0].answer == "plain"
        assert answers[0].prompt_tokens == 0

    def test_a_reader_returning_junk_is_refused(self):
        from analysis.hh001_reader import HH001ReaderError

        with pytest.raises(HH001ReaderError):
            generate_arm(
                NoMemoryArm(),
                [make_item("q?", key="k0")],
                {"conv-26": make_conversation(["a: hi"])},
                reader=lambda p, r=0: 42,
                budget=16_000,
                replicates=1,
            )

"""Fidelity tests for HH-002.

Every claim this study makes about running "their harness" rests on the three
things checked here: the prompts are the upstream bytes, the ranking is
NF-004's ordering, and the deterministic metric is theirs.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from analysis import hh002_arms, hh002_harness
from analysis.hh002_dataset import load_corpus
from analysis.nf004_mechanism import Candidate, ranking_orders

DATASET = Path(r"C:\Users\muzaf\Downloads\locomo10.json")


# --------------------------------------------------------------------------
# Prompts are the upstream blobs
# --------------------------------------------------------------------------


def test_vendored_prompts_match_upstream_digests():
    for name, expected in hh002_harness.VENDOR_DIGESTS.items():
        raw = (hh002_harness.VENDOR_DIR / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected, name
        assert b"\r" not in raw, f"{name} must stay LF"


def test_answer_prompt_keeps_upstream_trailing_spaces():
    # rag.py's template has a space after "# Question:" and "# Context:".
    assert hh002_harness.ANSWER_PROMPT_TEMPLATE == (
        "\n# Question: \n{{QUESTION}}\n\n# Context: \n{{CONTEXT}}\n\n"
        "# Short answer:\n"
    )


def test_system_message_reproduces_upstream_missing_spaces():
    # Five adjacent literals concatenated with no separator upstream.
    message = hh002_harness.ANSWER_SYSTEM_MESSAGE
    assert "provided context.If the question" in message
    assert "reference.Provide the shortest" in message
    assert message.startswith("You are a helpful assistant")
    assert message.endswith("Avoid using subjects in your answer.")


def test_render_answer_prompt_equals_jinja2():
    jinja2 = pytest.importorskip("jinja2")
    question = "When did Caroline go to the {{ support }} group?"
    context = "1:56 pm on 8 May, 2023 | Caroline: Hey Mel! {{QUESTION}}"
    rendered = jinja2.Template(hh002_harness.ANSWER_PROMPT_TEMPLATE).render(
        CONTEXT=context, QUESTION=question
    )
    assert hh002_harness.render_answer_prompt(question, context) == rendered


def test_judge_prompt_keeps_curly_quotes_and_placeholders():
    template = hh002_harness.JUDGE_PROMPT_TEMPLATE
    assert "\u2019CORRECT\u2019" in template
    rendered = hh002_harness.render_judge_prompt("q?", "gold", "gen")
    assert "Question: q?" in rendered
    assert "Gold answer: gold" in rendered
    assert "Generated answer: gen" in rendered


# --------------------------------------------------------------------------
# Ranking is NF-004's, only the dimension guard moved
# --------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_rank_pairs_equals_frozen_ranking_orders_at_1024(seed):
    rng = np.random.default_rng(seed)
    n = 60
    frozen = [
        Candidate(
            identity=str(i),
            session_identity=f"session_{i % 7 + 1}",
            session_order=i % 7,
            pair_order=i // 7,
            text=f"pair {i}",
            chars=7,
        )
        for i in range(n)
    ]
    ours = [
        hh002_arms.PairCandidate(
            text=c.text,
            session_order=c.session_order,
            pair_order=c.pair_order,
            dia_ids=(str(c.identity),),
        )
        for c in frozen
    ]
    matrix = rng.normal(size=(n, 1024)).astype(np.float32)
    query = rng.normal(size=(1024,)).astype(np.float32)

    _, expected_pair_order = ranking_orders(frozen, matrix, query)
    assert hh002_arms.rank_pairs(ours, matrix, query) == expected_pair_order


def test_rank_pairs_accepts_1536_dimensions():
    rng = np.random.default_rng(7)
    cands = [
        hh002_arms.PairCandidate(f"pair {i}", i % 3, i // 3, (str(i),))
        for i in range(12)
    ]
    matrix = rng.normal(size=(12, 1536)).astype(np.float32)
    query = rng.normal(size=(1536,)).astype(np.float32)
    order = hh002_arms.rank_pairs(cands, matrix, query)
    assert sorted(order) == list(range(12))


def test_rank_pairs_ties_break_by_position():
    # Identical vectors: every score is equal, so the sort must fall through
    # to (session_order, pair_order) exactly as the frozen function does.
    cands = [
        hh002_arms.PairCandidate("a", 1, 1, ("x",)),
        hh002_arms.PairCandidate("b", 0, 5, ("y",)),
        hh002_arms.PairCandidate("c", 0, 2, ("z",)),
    ]
    matrix = np.ones((3, 8), dtype=np.float32)
    query = np.ones((8,), dtype=np.float32)
    assert hh002_arms.rank_pairs(cands, matrix, query) == (2, 1, 0)


def test_rank_pairs_rejects_dimension_mismatch():
    cands = [hh002_arms.PairCandidate("a", 0, 0, ("x",))]
    with pytest.raises(hh002_arms.HH002ArmError):
        hh002_arms.rank_pairs(cands, np.ones((1, 8)), np.ones((16,)))


# --------------------------------------------------------------------------
# Deterministic metric is theirs
# --------------------------------------------------------------------------


def test_simple_tokenize_matches_upstream_punctuation_rules():
    assert hh002_harness.simple_tokenize("Hi, there. OK!?") == [
        "hi",
        "there",
        "ok",
    ]


def test_f1_is_set_overlap_not_multiset():
    # Upstream builds sets, so a repeated token cannot raise recall.
    metrics = hh002_harness.deterministic_metrics("shell shell necklace", "shell necklace")
    assert metrics["f1"] == pytest.approx(1.0)


def test_f1_and_exact_match_on_empty_inputs():
    assert hh002_harness.deterministic_metrics("", "gold") == {
        "exact_match": 0.0,
        "f1": 0.0,
    }


def test_exact_match_is_case_insensitive():
    assert hh002_harness.deterministic_metrics("7 May 2023", "7 may 2023")[
        "exact_match"
    ] == 1.0


# --------------------------------------------------------------------------
# Corpus shape
# --------------------------------------------------------------------------


@pytest.mark.skipif(not DATASET.exists(), reason="LoCoMo not present")
def test_corpus_matches_the_published_question_count():
    convs = load_corpus(DATASET)
    assert len(convs) == 10
    assert sum(len(c.questions) for c in convs) == 1986
    # The count every row of the published table is averaged over.
    assert sum(len(c.scored_questions) for c in convs) == 1540
    assert sum(len(c.turns) for c in convs) == 5882


@pytest.mark.skipif(not DATASET.exists(), reason="LoCoMo not present")
def test_clean_chat_history_matches_upstream_rendering():
    conv = load_corpus(DATASET)[0]
    rendered = conv.clean_chat_history()
    first = conv.turns[0]
    assert rendered.startswith(
        f"{first.timestamp} | {first.speaker}: {first.text}\n"
    )
    assert rendered.endswith("\n")
    assert rendered.count("\n") >= len(conv.turns)


@pytest.mark.skipif(not DATASET.exists(), reason="LoCoMo not present")
def test_sessions_are_ordered_numerically_not_lexically():
    # conv-41 has 32 sessions; lexical ordering would put session_10 second.
    conv = next(c for c in load_corpus(DATASET) if c.sample_id == "conv-41")
    orders = [t.session_order for t in conv.turns]
    assert orders == sorted(orders)
    ids = []
    for turn in conv.turns:
        if turn.session_id not in ids:
            ids.append(turn.session_id)
    assert ids[:3] == ["session_1", "session_2", "session_3"]
    assert len(ids) == 32


@pytest.mark.skipif(not DATASET.exists(), reason="LoCoMo not present")
def test_pair_candidates_cover_every_turn_once():
    conv = load_corpus(DATASET)[0]
    for with_ts in (True, False):
        cands = hh002_arms.build_pair_candidates(conv, with_ts)
        seen = [d for c in cands for d in c.dia_ids]
        assert len(seen) == len(conv.turns)
        assert len(set(seen)) == len(conv.turns)


@pytest.mark.skipif(not DATASET.exists(), reason="LoCoMo not present")
def test_timestamped_candidates_carry_dates_and_plain_ones_do_not():
    conv = load_corpus(DATASET)[0]
    stamped = hh002_arms.build_pair_candidates(conv, True)[0].text
    plain = hh002_arms.build_pair_candidates(conv, False)[0].text
    assert " | " in stamped and conv.turns[0].timestamp in stamped
    assert " | " not in plain
    assert plain.startswith(f"{conv.turns[0].speaker}: ")


# --------------------------------------------------------------------------
# A partial context cache must not be mistaken for a finished one
# --------------------------------------------------------------------------


class _StubClient:
    """Enough of MeteredClient for build_contexts' progress line."""

    class _Usage:
        embedding_calls = 0

    usage = _Usage()


class _StubArm:
    """Records how many conversations it was asked to prepare."""

    name = "A_STUB"

    def __init__(self):
        self.prepared = []

    def prepare(self, conversation, client):
        self.prepared.append(conversation.sample_id)
        return conversation

    def context(self, state, question, client):
        return f"ctx {question.source_index}", 0.0, {"chars": 3}


@pytest.mark.skipif(not DATASET.exists(), reason="LoCoMo not present")
def test_partial_context_cache_is_completed_not_adopted(tmp_path):
    """The bug this guards: a half-written cache scored an arm on 762 of
    1,540 items while every other arm had all 1,540."""
    from analysis.hh002_batch_run import build_contexts
    from analysis.hh002_run import _write_json

    conversations = load_corpus(DATASET)[:3]
    expected = {
        f"{c.sample_id}#{q.source_index}"
        for c in conversations
        for q in c.scored_questions
    }

    # Seed a cache holding only the first conversation.
    first = conversations[0]
    partial = {
        f"{first.sample_id}#{q.source_index}": {
            "sample_id": first.sample_id,
            "source_index": q.source_index,
            "category": q.category,
            "question": q.question,
            "answer": q.answer,
            "context": "stale",
            "context_chars": 5,
            "units_delivered": 1,
            "search_time": 0.0,
        }
        for q in first.scored_questions
    }
    _write_json(tmp_path / "contexts.json",
                {"arm": "A_STUB", "items": partial})

    arm = _StubArm()
    items = build_contexts(arm, conversations, _StubClient(), tmp_path)

    assert set(items) == expected
    # The cached conversation is not rebuilt; the missing two are.
    assert first.sample_id not in arm.prepared
    assert {c.sample_id for c in conversations[1:]} == set(arm.prepared)


@pytest.mark.skipif(not DATASET.exists(), reason="LoCoMo not present")
def test_complete_context_cache_is_adopted_without_rebuilding(tmp_path):
    from analysis.hh002_batch_run import build_contexts
    from analysis.hh002_run import _write_json

    conversations = load_corpus(DATASET)[:2]
    complete = {
        f"{c.sample_id}#{q.source_index}": {"sample_id": c.sample_id}
        for c in conversations
        for q in c.scored_questions
    }
    _write_json(tmp_path / "contexts.json",
                {"arm": "A_STUB", "items": complete})

    arm = _StubArm()
    items = build_contexts(arm, conversations, _StubClient(), tmp_path)
    assert items == complete
    assert arm.prepared == []

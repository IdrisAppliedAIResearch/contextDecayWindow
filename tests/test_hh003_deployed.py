from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from analysis.hh002_dataset import Conversation, Question, Turn
from analysis.hh003_arms import EpisodicArm, SharedEmbedder, stable_item_key
from analysis.hh003_report import two_sided_exact_binomial
from episodic._config import CARRIED_EMBEDDER_SHA256


class _FakeCarried:
    model_sha256 = CARRIED_EMBEDDER_SHA256

    def __call__(self, text: str) -> np.ndarray:
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        raw = np.frombuffer(seed * 128, dtype=np.uint8)[:1024].astype(np.float32)
        return raw - raw.mean()


def _conversation() -> Conversation:
    turns = tuple(
        Turn(
            timestamp=f"2026-08-{index + 1:02d}",
            speaker="Alice" if index % 2 == 0 else "Bob",
            text=f"message {index}",
            dia_id=f"d{index}",
            session_id="session_1",
            session_order=0,
        )
        for index in range(7)
    )
    question = Question("What was message 2?", "message 2", 1, ("d2",), 4)
    return Conversation("conv-test", "Alice", "Bob", turns, (question,))


def test_stable_item_key_uses_content_not_path_or_generated_id() -> None:
    question = _conversation().questions[0]
    first = stable_item_key("conv-test", question)
    assert first == stable_item_key("conv-test", question)
    assert first != stable_item_key("conv-other", question)
    assert len(first) == 64


def test_shared_embedder_reuses_exact_solo_vector() -> None:
    shared = SharedEmbedder(_FakeCarried())
    first = shared.embed("same")
    second = shared.embed("same")
    assert np.array_equal(first, second)
    assert (shared.hits, shared.misses) == (1, 1)
    second[0] += 1
    assert not np.array_equal(second, shared.embed("same"))


def test_public_arm_ingests_complete_timestamped_pairs_and_maps_sources(
    tmp_path: Path,
) -> None:
    conversation = _conversation()
    arm = EpisodicArm(
        tmp_path, aspect_enabled=False, embedder=SharedEmbedder(_FakeCarried())
    )
    state = arm.prepare(conversation, None)
    try:
        rows = state.store._conn.execute(
            "SELECT turn_number, user_message, assistant_message FROM episodes "
            "ORDER BY turn_number"
        ).fetchall()
        assert len(rows) == 3
        assert rows[0][1].startswith("2026-08-01 | Alice: message 0")
        assert rows[0][2].startswith("2026-08-02 | Bob: message 1")
        assert state.dangling_turns == ("d6",)

        before = state.db_path.read_bytes()
        payload, _, detail = arm.context(state, conversation.questions[0], None)
        assert state.db_path.read_bytes() == before
        assert detail["store_unchanged"] is True
        assert detail["retrieval_chars_delivered"] <= 32_000
        assert detail["aspect_enabled"] is False
        assert detail["stable_item_key"] == stable_item_key(
            conversation.sample_id, conversation.questions[0]
        )
        assert set(detail["delivered_source_ids"]).issubset(
            {turn.dia_id for turn in conversation.turns[:-1]}
        )
        assert "<recent_context>" in payload
    finally:
        arm.close_state(state)


def test_aspect_is_the_only_public_config_difference(tmp_path: Path) -> None:
    shared = SharedEmbedder(_FakeCarried())
    default = EpisodicArm(tmp_path, aspect_enabled=False, embedder=shared)
    aspect = EpisodicArm(tmp_path, aspect_enabled=True, embedder=shared)
    left = default.config.__dict__.copy()
    right = aspect.config.__dict__.copy()
    assert left.pop("aspect_enabled") is False
    assert right.pop("aspect_enabled") is True
    assert left == right


def test_two_sided_exact_binomial_is_symmetric_and_handles_ties() -> None:
    assert two_sided_exact_binomial(0, 0) == 1.0
    assert two_sided_exact_binomial(3, 1) == two_sided_exact_binomial(1, 3)
    assert two_sided_exact_binomial(4, 0) == 0.125

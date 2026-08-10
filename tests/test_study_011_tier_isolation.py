"""Tests for Study 011's tier-isolation engine."""

from __future__ import annotations

import numpy as np
import pytest

from src.db.episode import store_episode
from src.db.schema import init_db
from src.memory.context_matched_stm import ContextMatchedStmRetrievalEngine
from src.tier_isolation.study011 import (
    ARM_CONFIGS,
    ArmConfig,
    TierIsolationEngine,
    TierIsolationError,
    arm_accounting,
)

BUDGET = 32_000
N_CAP = 32
K_THRESHOLD = 0.48


def _unit(index: int) -> np.ndarray:
    vector = np.zeros(1_024, dtype=np.float32)
    vector[index % 8] = 1.0
    return vector


@pytest.fixture()
def store(tmp_path):
    conn = init_db(str(tmp_path / "study011.db"))
    for index in range(20):
        store_episode(
            conn,
            f"user {index} " + ("x" * 300),
            f"assistant {index} " + ("y" * 300),
            _unit(index),
            index + 1,
        )
    return conn


def _engine(conn, arm: str, provider) -> TierIsolationEngine:
    return TierIsolationEngine(
        conn,
        arm=arm,
        n_cap=N_CAP,
        k_threshold=K_THRESHOLD,
        payload_budget=BUDGET,
        embedding_provider=provider,
        system_prompt="system",
    )


@pytest.fixture()
def provider():
    return lambda _text: _unit(0)


# --------------------------------------------------------------------------
# The control is not served here
# --------------------------------------------------------------------------


def test_arm_d_is_refused_with_the_reason(store, provider) -> None:
    with pytest.raises(TierIsolationError, match="checked-out prior code"):
        _engine(store, "D", provider)


def test_an_unregistered_arm_is_refused(store, provider) -> None:
    with pytest.raises(TierIsolationError, match="Unregistered arm"):
        _engine(store, "Z", provider)


def test_arm_accounting_names_who_serves_each_arm() -> None:
    assert arm_accounting("D")["served_by"].startswith("deployed code")
    assert arm_accounting("C")["served_by"].endswith("study011.py")


# --------------------------------------------------------------------------
# Tier switches. A disabled tier is not consulted, not merely outvoted.
# --------------------------------------------------------------------------


def test_arm_a_delivers_recency_and_no_k_candidates(store, provider) -> None:
    result = _engine(store, "A", provider).retrieve("query", 21)
    assert result.n_candidate_count > 0
    assert result.k_candidate_count == 0
    assert result.retrieved_stm_episodes == []


def test_arm_a_makes_no_embedding_call(store) -> None:
    """No K tier means no query vector. The arms differ in tiers only."""

    calls = []

    def counting(text):
        calls.append(text)
        return _unit(0)

    _engine(store, "A", counting).retrieve("query", 21)
    assert calls == []


def test_arm_b_delivers_k_and_no_recency(store, provider) -> None:
    result = _engine(store, "B", provider).retrieve("query", 21)
    assert result.n_candidate_count == 0
    assert result.recent_episodes == []
    assert result.k_candidate_count > 0


def test_arm_b_still_embeds_the_query(store) -> None:
    calls = []

    def counting(text):
        calls.append(text)
        return _unit(0)

    _engine(store, "B", counting).retrieve("query", 21)
    assert calls == ["query"]


def test_arm_c_delivers_both_paths(store, provider) -> None:
    result = _engine(store, "C", provider).retrieve("query", 21)
    assert result.n_candidate_count > 0
    assert result.k_candidate_count > 0
    assert result.recent_episodes


def test_a_disabled_recency_tier_rejects_no_n_cap(store, provider) -> None:
    """Arm B carries no N cap, so the carried cap check must not apply."""

    engine = TierIsolationEngine(
        store,
        arm="B",
        n_cap=0,
        k_threshold=K_THRESHOLD,
        payload_budget=BUDGET,
        embedding_provider=provider,
        system_prompt="system",
    )
    assert engine.n_cap == 0


def test_an_enabled_recency_tier_keeps_the_carried_cap_check(
    store, provider
) -> None:
    with pytest.raises(TierIsolationError, match="above the carried cap"):
        TierIsolationEngine(
            store,
            arm="C",
            n_cap=4,
            k_threshold=K_THRESHOLD,
            payload_budget=BUDGET,
            embedding_provider=provider,
            system_prompt="system",
        )


def test_an_enabled_k_tier_keeps_the_carried_threshold_check(
    store, provider
) -> None:
    with pytest.raises(TierIsolationError, match="below the carried threshold"):
        TierIsolationEngine(
            store,
            arm="C",
            n_cap=N_CAP,
            k_threshold=0.7,
            payload_budget=BUDGET,
            embedding_provider=provider,
            system_prompt="system",
        )


# --------------------------------------------------------------------------
# Fidelity. The switches must not perturb anything but the switch.
# --------------------------------------------------------------------------


def test_both_tiers_recency_first_matches_the_deployed_engine(
    store, provider, monkeypatch
) -> None:
    """The one test that makes the C-vs-D contrast a fill-order contrast.

    Arm D is refused in production, so a test-only arm with both tiers and
    the deployed order stands in. If this prompt were not byte-identical to
    the carried engine's, the live difference between arms would be a
    rewrite rather than a packing order.
    """

    monkeypatch.setitem(
        ARM_CONFIGS,
        "TEST_D",
        ArmConfig("TEST_D", True, True, "B0", "test-only deployed equivalent"),
    )
    mine = _engine(store, "TEST_D", provider).retrieve("query", 21)

    deployed = ContextMatchedStmRetrievalEngine(
        store,
        n_cap=N_CAP,
        k_threshold=K_THRESHOLD,
        payload_budget=BUDGET,
        embedding_provider=provider,
        system_prompt="system",
    ).retrieve("query", 22)

    assert mine.constructed_prompt == deployed.constructed_prompt
    assert mine.retrieval_payload_sha256 == deployed.retrieval_payload_sha256
    assert mine.n_episode_ids == deployed.n_episode_ids
    assert mine.delivered_k_only_ids == deployed.delivered_k_only_ids


def test_k_first_and_recency_first_see_the_same_candidates(
    store, provider, monkeypatch
) -> None:
    """Order changes the fill, never the candidate sets."""

    monkeypatch.setitem(
        ARM_CONFIGS,
        "TEST_D",
        ArmConfig("TEST_D", True, True, "B0", "test-only deployed equivalent"),
    )
    first = _engine(store, "TEST_D", provider).retrieve("query", 21)
    second = _engine(store, "C", provider).retrieve("query", 21)

    assert set(first.n_candidate_ids) == set(second.n_candidate_ids)
    assert set(first.k_candidate_ids) == set(second.k_candidate_ids)


def test_every_arm_respects_the_registered_budget(store, provider) -> None:
    for arm in ("A", "B", "C"):
        result = _engine(store, arm, provider).retrieve("query", 21)
        assert result.retrieval_payload_chars <= BUDGET


def test_dropped_candidates_are_attributed_to_their_path(
    store, provider
) -> None:
    result = _engine(store, "C", provider).retrieve("query", 21)
    delivered = set(result.n_episode_ids) | set(result.delivered_k_only_ids)
    for episode_id in result.skipped_n_ids + result.skipped_k_ids:
        assert episode_id not in delivered

"""The dual arm's standing guarantees, held independently of any one study.

TC-001B measured `A_DUAL` and `A_DUAL_RANKED` and the author's instruction
afterwards was that the dual arm travels with the TC arc from there on. An arm
that travels needs to mean the same thing in the study that inherits it as it
did in the study that measured it, and nothing in a report enforces that.

These tests do. They are deliberately not TC-002's tests: they name no budget,
no bar, no contrast and no corpus, and they fail if a later change quietly
alters what "the dual arm" is. Every claim below is one a report has already
relied on:

* TC-001B section 1 attributed 158 questions to the recency tier's removal.
  That number means what it says only if `A_DUAL` is the shipped composition
  with the tier removed and nothing else changed.
* TC-001B section 3 rested C1's fairness on `A_DUAL` rendering the same empty
  `recent_context` wrapper `A_FLAT` renders, at 52 characters against 52.
* TC-001B section 1 attributed 276 questions to the K tier's delivery order.
  That number means what it says only if `A_DUAL_RANKED` differs from `A_DUAL`
  in that order and in nothing else.

The stores here are constructed, so each answer is known without running a
study and without touching the embedding cache.
"""

from __future__ import annotations

import numpy as np
import pytest

from analysis import tc_standing_arms as arms
from analysis.tc001_exploration import Episode, flat_context
from analysis.tc001b_exploration import (
    DUAL_CONFIG,
    SHIPPED_CONFIG,
    compose_context,
    dual_context,
    dual_ranked_context,
)
from episodic._config import EpisodicConfig
from episodic._context import _recency_window, build_context
from episodic._embedding import EMBEDDING_DIMENSION
from episodic._render import render_episode_element, render_stm_payload
from episodic._selection import relevance_vector


class _Pair:
    """The attributes ``Episode`` reads off a LoCoMo pair, and no more."""

    def __init__(self, identity: str, order: int) -> None:
        self.identity = identity
        self.text = f"pair {identity}"
        self.session_order = 1
        self.pair_order = order
        self.dialog_ids = (identity,)
        self.session_id = "s1"


def _records(count: int) -> list[dict]:
    """A synthetic store in the carried embedder's dimension.

    The vectors are sparse and collide across episodes, so the K threshold
    fires on some and not others and the cluster assignment has something to
    separate. Lengths vary so the budget binds unevenly.
    """
    rows = []
    for index in range(count):
        vector = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
        vector[index % 8] = 1.0
        vector[(index * 3) % 8] += 0.5
        rows.append(
            {
                "id": f"e{index:03d}",
                "turn_number": index + 1,
                "user_message": f"question about topic {index % 5}",
                "assistant_message": f"answer number {index} " + "x" * (index % 23),
                "ground_truth_domain": "s1",
                "embedding": vector,
            }
        )
    return rows


def _episodes(count: int) -> tuple[Episode, ...]:
    return tuple(
        Episode(
            record=record,
            pair=_Pair(record["id"], index + 1),
            element_chars=len(render_episode_element(record)),
        )
        for index, record in enumerate(_records(count))
    )


def _query() -> np.ndarray:
    query = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    query[0] = 1.0
    query[3] = 0.4
    return query


BUDGETS = (1_500, 4_000, 40_000)


# --------------------------------------------------------------------------
# The registry
# --------------------------------------------------------------------------


def test_the_dual_arm_is_standing() -> None:
    assert "dual" in arms.STANDING_ARMS
    assert "dual_ranked" in arms.STANDING_ARMS


def test_every_standing_arm_has_a_constructor_and_an_origin() -> None:
    for arm in arms.STANDING_ARMS:
        assert arm in arms.STANDING_ARM_ORIGIN
        payload, delivered = arms.deliver(arm, _episodes(20), _query(), 4_000)
        assert isinstance(payload, str)
        assert len(delivered) == len(set(delivered))


def test_an_unregistered_arm_is_refused_rather_than_guessed() -> None:
    with pytest.raises(arms.TCArmError):
        arms.deliver("recency_only", _episodes(4), _query(), 4_000)


def test_the_shipped_arm_is_defined_but_does_not_travel() -> None:
    """``tiered`` is available and deliberately not standing.

    It is the configuration under test when a study tests it, and carrying it
    unconditionally would make every arc study look like a referendum on the
    shipped stack. The three that travel are the reference and the dual pair.
    """
    assert "tiered" not in arms.STANDING_ARMS
    payload, _delivered = arms.deliver("tiered", _episodes(20), _query(), 4_000)
    assert payload


# --------------------------------------------------------------------------
# A_DUAL is build_context with one field changed
# --------------------------------------------------------------------------


def test_dual_config_differs_from_shipped_in_exactly_one_field() -> None:
    shipped = SHIPPED_CONFIG.__dict__ if hasattr(SHIPPED_CONFIG, "__dict__") else {}
    differing = [
        field
        for field in EpisodicConfig.__dataclass_fields__
        if getattr(SHIPPED_CONFIG, field) != getattr(DUAL_CONFIG, field)
    ]
    assert differing == ["recency_window_n"]
    assert DUAL_CONFIG.recency_window_n == 0
    assert shipped is not None


@pytest.mark.parametrize("budget", BUDGETS)
def test_dual_is_build_context_with_the_recency_window_at_zero(budget: int) -> None:
    episodes = _episodes(30)
    records = [episode.record for episode in episodes]
    expected, report = build_context(
        episodes=records,
        query_embedding=_query(),
        budget=budget,
        config=DUAL_CONFIG,
    )
    payload, delivered, dual_report = dual_context(episodes, _query(), budget)
    assert payload == expected
    assert dual_report.stm_count == report.stm_count == 0
    assert len(delivered) == report.episodes_delivered


def test_the_recency_window_is_empty_at_zero_rather_than_defaulting() -> None:
    """``_recency_window`` returns nothing at N=0, so no new code was needed.

    If this ever changed to, say, a minimum of one, ``A_DUAL`` would silently
    stop being a no-recency arm and TC-001B's 158 would stop meaning what it
    says.
    """
    records = _records(30)
    assert _recency_window(records, 0) == []
    assert _recency_window(records, -1) == []
    assert len(_recency_window(records, 5)) == 5


@pytest.mark.parametrize("budget", BUDGETS)
def test_dual_renders_the_same_empty_wrapper_the_flat_arm_renders(
    budget: int,
) -> None:
    """TC-001B section 3's wrapper-symmetry claim, held as an invariant.

    A contrast between two arms that pay different fixed serialization costs is
    a contrast confounded by the renderer. ``A_DUAL`` and ``A_FLAT`` both leave
    ``recent_context`` empty, so they pay the same wrapper and the confound is
    absent by construction rather than by argument.
    """
    episodes = _episodes(30)
    dual_payload, _delivered, _report = dual_context(episodes, _query(), budget)
    flat_payload, _flat_ids = flat_context(episodes, _query(), budget)

    # The fixed serialization cost both arms pay: an empty recency block plus
    # a non-empty retrieved_stm wrapper. Derived from the renderer rather than
    # transcribed, so a renderer change fails this test instead of passing it.
    sample = _records(1)[0]
    wrapper = len(render_stm_payload([], [sample])) - len(
        render_episode_element(sample)
    )
    assert wrapper == 52

    by_turn = {record["turn_number"]: record for record in _records(30)}
    for payload in (dual_payload, flat_payload):
        assert payload.startswith("<recent_context/>")
        # Everything delivered is in the stm block: re-rendering the payload's
        # own episodes with an empty recency tier reproduces it exactly.
        delivered = [
            by_turn[turn]
            for turn in sorted(by_turn)
            if f'<episode turn="{turn}">' in payload
        ]
        assert len(payload) == len(render_stm_payload([], delivered))


# --------------------------------------------------------------------------
# A_DUAL_RANKED differs from A_DUAL in the K tier's order and nothing else
# --------------------------------------------------------------------------


@pytest.mark.parametrize("budget", BUDGETS)
def test_compose_context_under_store_order_is_the_shipped_function(
    budget: int,
) -> None:
    """The gate that makes the ranked arm admissible, on a constructed store.

    ``compose_context`` restates ``build_context`` so that one line of it can
    be varied. A restatement proven equal to the original is measurable; one
    merely believed equal is not, and this is where that proof lives outside a
    study run.
    """
    records = _records(30)
    for config in (SHIPPED_CONFIG, DUAL_CONFIG):
        expected, _report = build_context(
            episodes=records,
            query_embedding=_query(),
            budget=budget,
            config=config,
        )
        local, _ids, _counts = compose_context(
            records, _query(), budget, config, k_order="store"
        )
        assert local == expected


@pytest.mark.parametrize("budget", BUDGETS)
def test_the_ranked_arm_offers_the_k_tier_best_first(budget: int) -> None:
    episodes = _episodes(30)
    records = [episode.record for episode in episodes]
    _payload, delivered, counts = dual_ranked_context(episodes, _query(), budget)
    if counts["k"] < 2:
        pytest.skip("the K tier delivered fewer than two episodes at this budget")

    relevance = relevance_vector(_query(), records)
    by_id = {
        str(record["id"]): float(relevance[index])
        for index, record in enumerate(records)
    }
    scores = [by_id[identity] for identity in delivered[: counts["k"]]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize("budget", BUDGETS)
def test_both_dual_arms_draw_from_the_same_k_tier(budget: int) -> None:
    """Ordering changes which K episodes survive the budget, never which qualify.

    The K tier is defined by a cosine threshold, and a threshold does not care
    about order. So the two arms' delivered K sets may differ, but neither may
    contain an episode below the threshold.
    """
    episodes = _episodes(30)
    records = [episode.record for episode in episodes]
    relevance = relevance_vector(_query(), records)
    qualifying = {
        str(record["id"])
        for index, record in enumerate(records)
        if float(relevance[index]) >= DUAL_CONFIG.k_threshold
    }
    _payload, dual_ids, dual_report = dual_context(episodes, _query(), budget)
    _payload, ranked_ids, ranked_counts = dual_ranked_context(
        episodes, _query(), budget
    )
    assert set(dual_ids[: dual_report.k_count]) <= qualifying
    assert set(ranked_ids[: ranked_counts["k"]]) <= qualifying


def test_an_unregistered_k_order_is_refused() -> None:
    from analysis.tc001b_exploration import TC001BExplorationError

    with pytest.raises(TC001BExplorationError):
        compose_context(
            _records(4), _query(), 8_000, DUAL_CONFIG, k_order="chronological"
        )

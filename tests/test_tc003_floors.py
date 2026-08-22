"""The reserved-floors allocator's behavioural identity, held on constructed stores.

`TC_ARC_ROADMAP.md` section 4 proposes floors so that "allocation stops
depending on order." That sentence contains three separable claims and these
tests keep them apart, because the study's whole value rests on not conflating
them:

* the allocator is a **generalization of the two committed packers** - with its
  floors at zero it reproduces them byte-for-byte, so a contrast against them
  measures the floors and not a rewrite;
* the **service order** of the tiers cannot change what is delivered;
* the **ownership order** - which tier pays for, and renders, a candidate that
  belongs to two tiers - still can, and the allocator does not pretend
  otherwise.

The stores here are constructed, so each answer is known without running a
study and without touching the embedding cache. These tests name no budget the
study registers, no bar and no corpus: they hold the mechanism, and a study's
numbers mean what they say only if the mechanism is what its report claims.
"""

from __future__ import annotations

import numpy as np
import pytest

from analysis.ec002_k_first_packing import build_candidate_state, pack_k_first
from analysis.tc001_exploration import Episode
from analysis.tc001b_exploration import DUAL_CONFIG, SHIPPED_CONFIG
from analysis import tc003_exploration as floors
from episodic._config import EpisodicConfig
from episodic._embedding import EMBEDDING_DIMENSION
from episodic._packing import EMPTY_PAYLOAD_CHARS, pack_stm_payload
from episodic._render import render_episode_element, render_stm_payload


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

    Sparse, colliding vectors so the K threshold fires on some episodes and
    not others and the cluster assignment has something to separate; uneven
    lengths so the budget binds unevenly and a floor can bind on one tier
    while another has slack.
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


def _state(records, budget: int, config: EpisodicConfig):
    return build_candidate_state(
        episodes=records,
        query_embedding=_query(),
        budget=budget,
        config=config,
    )


#: Small enough to bind hard, mid, and not at all.
BUDGETS = (1_500, 4_000, 40_000)
CONFIGS = (SHIPPED_CONFIG, DUAL_CONFIG)
ZERO = {tier: 0.0 for tier in floors.TIERS}


# --------------------------------------------------------------------------
# The reduction: this allocator is the committed packers, generalized
# --------------------------------------------------------------------------


@pytest.mark.parametrize("budget", BUDGETS)
@pytest.mark.parametrize("config", CONFIGS, ids=("shipped", "dual"))
def test_zero_floors_in_tier_order_is_the_shipped_packer(
    budget: int, config: EpisodicConfig
) -> None:
    records = _records(40)
    state = _state(records, budget, config)
    pack = floors.allocate(
        state, budget=budget, floors=ZERO, service=("n", "k", "c"), contest="tier"
    )
    shipped = pack_stm_payload(
        list(state.recent), [*state.k_hits, *state.coverage], budget
    )
    assert pack.payload == shipped.payload


@pytest.mark.parametrize("budget", BUDGETS)
@pytest.mark.parametrize("config", CONFIGS, ids=("shipped", "dual"))
def test_zero_floors_in_k_first_order_is_ec002s_packer(
    budget: int, config: EpisodicConfig
) -> None:
    records = _records(40)
    state = _state(records, budget, config)
    pack = floors.allocate(
        state, budget=budget, floors=ZERO, service=("k", "n", "c"), contest="tier"
    )
    assert pack.payload == pack_k_first(state, budget=budget).payload


def test_the_reduction_gate_reproduces_build_context_too() -> None:
    """The whole chain, not just the packer: allocator to library payload."""
    records = _records(40)
    for budget in BUDGETS:
        for config in CONFIGS:
            state = _state(records, budget, config)
            floors.assert_zero_floor_reduction(
                state, records, _query(), budget, config
            )


def test_the_two_zero_floor_orders_are_not_the_same_thing() -> None:
    """The reduction would be uninteresting if both orders always agreed.

    This is the control for the invariance checks below: at a budget that
    binds, sequential fill demonstrably depends on the order it is served in.
    """
    records = _records(40)
    state = _state(records, 1_500, SHIPPED_CONFIG)
    n_first = floors.allocate(
        state, budget=1_500, floors=ZERO, service=("n", "k", "c"), contest="tier"
    )
    k_first = floors.allocate(
        state, budget=1_500, floors=ZERO, service=("k", "n", "c"), contest="tier"
    )
    assert n_first.delivered != k_first.delivered


# --------------------------------------------------------------------------
# The floor rule
# --------------------------------------------------------------------------


def test_equal_shares_splits_between_the_populated_tiers_only() -> None:
    records = _records(40)
    shipped = floors.equal_shares(_state(records, 4_000, SHIPPED_CONFIG))
    assert shipped["n"] == pytest.approx(1 / 3)
    assert shipped["k"] == pytest.approx(1 / 3)
    assert shipped["c"] == pytest.approx(1 / 3)

    dual = floors.equal_shares(_state(records, 4_000, DUAL_CONFIG))
    assert dual["n"] == 0.0
    assert dual["k"] == pytest.approx(0.5)
    assert dual["c"] == pytest.approx(0.5)


def test_an_unpopulated_k_tier_does_not_reserve_anything() -> None:
    """A threshold no episode clears leaves two tiers, not three shares.

    The rule is equal shares among the tiers that have members, so a tier that
    offers nothing cannot hold budget hostage.
    """
    records = _records(40)
    unreachable = EpisodicConfig(k_threshold=1.0)
    shares = floors.equal_shares(_state(records, 4_000, unreachable))
    assert shares["k"] == 0.0
    assert shares["n"] == pytest.approx(0.5)
    assert shares["c"] == pytest.approx(0.5)


def test_the_floor_rule_has_no_free_parameter() -> None:
    """``equal_shares`` reads only the candidate state - no tuning surface.

    If this ever gains an argument, the arm stops being one rule at two
    configurations and becomes two tunings, which is a different study under
    AGENTS.md section 5.
    """
    import inspect

    signature = inspect.signature(floors.equal_shares)
    assert list(signature.parameters) == ["state"]


# --------------------------------------------------------------------------
# Cost accounting
# --------------------------------------------------------------------------


@pytest.mark.parametrize("tier", ["n", "k", "c"])
def test_tier_spend_is_read_off_the_renderer(tier: str) -> None:
    records = _records(6)
    spend = floors.tier_spend(tier, records)
    if floors.BLOCK_OF[tier] == "recent":
        expected = len(render_stm_payload(records, [])) - EMPTY_PAYLOAD_CHARS
    else:
        expected = len(render_stm_payload([], records)) - EMPTY_PAYLOAD_CHARS
    assert spend == expected


def test_an_empty_tier_spends_nothing() -> None:
    assert floors.tier_spend("n", []) == 0
    assert floors.tier_spend("k", []) == 0


def test_solo_accounting_never_undercharges() -> None:
    """The reserved phase can overshoot no budget, and this is why.

    Two tiers sharing ``retrieved_stm`` each pay its opening tags, so the sum
    of solo spends is at least the true payload cost. If that ever inverted,
    a reserved phase could exceed the budget before the contest even opened.
    """
    records = _records(20)
    k_side = records[:7]
    c_side = records[7:14]
    combined = len(render_stm_payload([], [*k_side, *c_side])) - EMPTY_PAYLOAD_CHARS
    solo = floors.tier_spend("k", k_side) + floors.tier_spend("c", c_side)
    assert solo >= combined


@pytest.mark.parametrize("budget", BUDGETS)
@pytest.mark.parametrize("config", CONFIGS, ids=("shipped", "dual"))
def test_the_payload_never_exceeds_the_budget(
    budget: int, config: EpisodicConfig
) -> None:
    records = _records(40)
    state = _state(records, budget, config)
    pack = floors.floors_pack(
        state, floors.relevance_map(records, _query()), budget
    )
    assert len(pack.payload) <= budget


def test_a_budget_below_the_empty_tags_delivers_nothing() -> None:
    """The absorbing state, exercised rather than assumed.

    Below the cost of the two empty block tags there is no payload to return,
    which is ``pack_stm_payload``'s own degraded behaviour after CC-003.
    """
    records = _records(10)
    state = _state(records, 4_000, SHIPPED_CONFIG)
    pack = floors.floors_pack(
        state, floors.relevance_map(records, _query()), EMPTY_PAYLOAD_CHARS - 1
    )
    assert pack.payload == ""
    assert pack.selected_ids == ()
    assert pack.dropped_ids


# --------------------------------------------------------------------------
# Order: the one floors remove, and the one they do not
# --------------------------------------------------------------------------


@pytest.mark.parametrize("budget", BUDGETS)
@pytest.mark.parametrize("config", CONFIGS, ids=("shipped", "dual"))
def test_the_service_order_cannot_change_what_is_delivered(
    budget: int, config: EpisodicConfig
) -> None:
    records = _records(40)
    state = _state(records, budget, config)
    relevance = floors.relevance_map(records, _query())
    payloads = {
        order: floors.floors_pack(
            state, relevance, budget, service=order
        ).payload
        for order in floors.SERVICE_ORDERS
    }
    assert len(set(payloads.values())) == 1


def test_the_service_order_check_can_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """A check that cannot register a difference is not evidence.

    The zero-floor control is the same allocator with its reservations
    removed, and it is order-dependent at a binding budget. Without this the
    test above would pass on an instrument that had never been shown able to
    say otherwise.
    """
    records = _records(40)
    state = _state(records, 1_500, SHIPPED_CONFIG)
    sets = {
        order: floors.allocate(
            state, budget=1_500, floors=ZERO, service=order, contest="tier"
        ).delivered
        for order in floors.SERVICE_ORDERS
    }
    assert len({tuple(sorted(value)) for value in sets.values()}) > 1


def test_ownership_decides_which_block_renders_an_overlapping_candidate() -> None:
    """A recency/K overlap renders where its owner says, not where it was served.

    ``build_context`` counts such an episode as recency and EC-002 renders it
    in ``recent_context`` while considering it at K priority. The allocator
    keeps that separation explicit rather than inheriting it by accident.
    """
    records = _records(40)
    budget = 40_000
    state = _state(records, budget, SHIPPED_CONFIG)
    recent_ids = {str(e["id"]) for e in state.recent}
    k_ids = {str(e["id"]) for e in state.k_hits}
    assert recent_ids & k_ids, "fixture must produce an overlap to test"

    relevance = floors.relevance_map(records, _query())
    default = floors.floors_pack(state, relevance, budget)
    swapped = floors.floors_pack(
        state, relevance, budget, ownership=("k", "n", "c")
    )
    overlap = next(iter(recent_ids & k_ids))
    assert default.owner[overlap] == "n"
    assert swapped.owner[overlap] == "k"


def test_floors_do_not_claim_ownership_order_invariance() -> None:
    """The honest limit, held as a test rather than left to the report.

    Reserved floors remove the dependence on which tier is *served* first.
    They do not remove the dependence on which tier *owns* a shared candidate,
    because that decides which allowance pays for it. If this test ever starts
    failing on this fixture, the allocator has changed and the study's stated
    limit no longer describes it.
    """
    records = _records(40)
    budget = 1_500
    state = _state(records, budget, SHIPPED_CONFIG)
    relevance = floors.relevance_map(records, _query())
    sets = {
        order: floors.floors_pack(
            state, relevance, budget, ownership=order
        ).delivered
        for order in floors.SERVICE_ORDERS
    }
    assert len({tuple(sorted(value)) for value in sets.values()}) > 1


# --------------------------------------------------------------------------
# Refusals
# --------------------------------------------------------------------------


def test_an_unregistered_contest_is_refused_rather_than_guessed() -> None:
    records = _records(10)
    state = _state(records, 4_000, SHIPPED_CONFIG)
    with pytest.raises(floors.TC003ExplorationError):
        floors.allocate(state, budget=4_000, floors=ZERO, contest="round_robin")


def test_a_service_order_that_is_not_a_permutation_is_refused() -> None:
    records = _records(10)
    state = _state(records, 4_000, SHIPPED_CONFIG)
    with pytest.raises(floors.TC003ExplorationError):
        floors.allocate(
            state, budget=4_000, floors=ZERO, service=("n", "n", "k"), contest="tier"
        )


def test_floors_summing_above_the_whole_budget_are_refused() -> None:
    records = _records(10)
    state = _state(records, 4_000, SHIPPED_CONFIG)
    with pytest.raises(floors.TC003ExplorationError):
        floors.allocate(
            state,
            budget=4_000,
            floors={"n": 0.5, "k": 0.5, "c": 0.5},
            relevance_by_id=floors.relevance_map(records, _query()),
        )


def test_a_negative_floor_is_refused() -> None:
    records = _records(10)
    state = _state(records, 4_000, SHIPPED_CONFIG)
    with pytest.raises(floors.TC003ExplorationError):
        floors.allocate(
            state,
            budget=4_000,
            floors={"n": -0.1, "k": 0.5, "c": 0.5},
            relevance_by_id=floors.relevance_map(records, _query()),
        )


def test_the_relevance_contest_refuses_to_run_without_relevance() -> None:
    """No silent fallback to tier order: that would be a different allocator."""
    records = _records(10)
    state = _state(records, 4_000, SHIPPED_CONFIG)
    with pytest.raises(floors.TC003ExplorationError):
        floors.allocate(
            state,
            budget=4_000,
            floors=floors.equal_shares(state),
            contest="relevance",
        )

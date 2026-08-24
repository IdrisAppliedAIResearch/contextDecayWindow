"""TC-003 Preflight Part 1: characterize reserved floors before any bar is locked.

``TC_ARC_ROADMAP.md`` section 4 proposes replacing greedy sequential fill with
reserved floors: *give each tier a guaranteed minimum share of the budget and
let them compete only for the remainder, so allocation stops depending on
order.*

This module builds that allocator and records what it does. It deliberately
does not compute any treatment contrast: no artifact it writes contains an
arm's absolute availability, because the null band in the pre-registration is
derived from measurements taken here and a band chosen after seeing the
contrast would not be a band.

The allocator is a **generalization of the two committed packers, not a
rewrite of them.** With every floor set to zero and the remainder contested in
tier order it reduces exactly - byte-for-byte, on every question - to:

    service (n, k, c)  ->  ``episodic._packing.pack_stm_payload``, and so to
                           ``build_context``: the shipped N-first order
    service (k, n, c)  ->  ``ec002_k_first_packing.pack_k_first``: EC-002's
                           reversed order

``assert_zero_floor_reduction`` holds that identity on real data rather than in
prose, and it is what makes "only the allocation differs" a checked statement
instead of a claim.

Three orders are separable inside this allocator and the study needs them kept
apart:

    service order    which tier is *served* when. Floors are supposed to make
                     this irrelevant, and by the accounting below they do.
    ownership order  which tier *owns* a candidate that is in more than one
                     tier - and therefore which floor pays for it and which
                     block renders it. Floors do **not** make this irrelevant.
    contest order    how the unreserved remainder is allocated. An
                     order-invariant allocator needs an order-invariant contest
                     key, so the registered one is global cosine relevance;
                     ``"tier"`` exists only for the reduction above.

Zero model calls. The cache is opened in ``reuse`` mode with its file and
content digests asserted, so a miss raises rather than embedding.
"""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from analysis.ec002_k_first_packing import (
    CandidateState,
    build_candidate_state,
    pack_k_first,
)
from analysis.locomo_nf_development import (
    ConversationCase,
    adapt_development,
    sha256_file,
)
from analysis.tc001_exploration import (
    BUDGETS,
    CACHE_PATH,
    DATASET_PATH,
    REPO_ROOT,
    SHAM_FRACTIONS,
    VECTOR_MANIFEST,
    Episode,
    _delivered_ids,
    _evidence_index,
    _repo_relative,
    _score,
    _sham_row,
    build_episodes,
)
from analysis.tc001b_exploration import DUAL_CONFIG, SHIPPED_CONFIG
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256, EpisodicConfig
from episodic._context import build_context
from episodic._packing import EMPTY_PAYLOAD_CHARS, pack_stm_payload
from episodic._render import render_stm_payload
from episodic._selection import relevance_vector, vector

SCHEMA = "tc003-preflight-part1-v1"

ARTIFACT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "tier_cost" / "artifacts" / "tc003"
)

#: The three tiers, in the shipped composition's own naming.
TIERS: tuple[str, str, str] = ("n", "k", "c")

#: Which rendered block each tier's members appear in. Two blocks, three
#: tiers: the K and coverage tiers share ``retrieved_stm``, which is why a
#: tier's reserved spend is accounted solo (see ``tier_spend``).
BLOCK_OF: dict[str, str] = {"n": "recent", "k": "stm", "c": "stm"}

#: Every permutation of the tier service order. Six, not two: the point of
#: floors is that *no* permutation changes the result, and checking only the
#: two orders the arc has shipped would not test that.
SERVICE_ORDERS: tuple[tuple[str, ...], ...] = (
    ("n", "k", "c"),
    ("n", "c", "k"),
    ("k", "n", "c"),
    ("k", "c", "n"),
    ("c", "n", "k"),
    ("c", "k", "n"),
)

#: The library's own precedence for a candidate that is in more than one tier:
#: ``build_context`` counts a recency/K overlap as recency, and EC-002 renders
#: one in ``recent_context`` even though it considers it at K priority.
OWNERSHIP_DEFAULT: tuple[str, ...] = ("n", "k", "c")

CONTESTS = ("relevance", "tier")

#: Configurations the floor rule is applied to. One rule, two configurations.
FLOOR_CONFIGS: dict[str, EpisodicConfig] = {
    "floors": SHIPPED_CONFIG,
    "floors_dual": DUAL_CONFIG,
}


class TC003ExplorationError(RuntimeError):
    """Raised when a Preflight invariant does not hold."""


# --------------------------------------------------------------------------
# The allocator
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FloorsPack:
    payload: str
    selected_ids: tuple[str, ...]
    dropped_ids: tuple[str, ...]
    owner: dict[str, str]
    shares: dict[str, float]
    allowances: dict[str, int]
    reserved_spend: dict[str, int]
    reserved_admitted: dict[str, int]
    contested_admitted: dict[str, int]
    remainder_chars: int

    @property
    def delivered(self) -> frozenset[str]:
        return frozenset(self.selected_ids)


def tier_offers(state: CandidateState) -> dict[str, list[dict]]:
    """What each tier offers, in the order that tier offers it.

    These are the unchanged EC-001 candidate lists ``build_candidate_state``
    reconstructs: the recency window in conversation order, the K-threshold
    hits in store order, and the A3 coverage selection in the selector's own
    descending marginal-gain order. Nothing is filtered here - a candidate in
    two tiers appears in both lists, and ownership resolves it later.
    """
    return {
        "n": list(state.recent),
        "k": list(state.k_hits),
        "c": list(state.coverage),
    }


def equal_shares(state: CandidateState) -> dict[str, float]:
    """The registered floor rule: equal shares among the populated tiers.

    This has no free parameter. Under the shipped configuration the three
    tiers are normally all populated and each reserves a third; under the
    arc's standing dual configuration the recency tier is empty and the other
    two reserve a half each. It is one rule at two configurations, not two
    tunings.

    "Populated" is read off tier *membership*, before ownership. That keeps
    the floor vector itself invariant under an ownership permutation, so the
    ownership check measures what ownership does and not what ownership did
    to the floors.
    """
    offers = tier_offers(state)
    populated = [tier for tier in TIERS if offers[tier]]
    if not populated:
        return {tier: 0.0 for tier in TIERS}
    share = 1.0 / len(populated)
    return {tier: (share if tier in populated else 0.0) for tier in TIERS}


def tier_spend(tier: str, admitted: Sequence[dict]) -> int:
    """One tier's reserved spend, charged as if it were alone in the payload.

    Exact serialized cost is not additive across tiers - the K and coverage
    tiers share one block, so together they pay its opening tags once. Solo
    accounting therefore over-charges by exactly the shared block's 16-tag
    delta when both are non-empty, and never under-charges. That matters for
    two reasons: the reserved phase can never exceed the budget, and a tier's
    spend depends on *its own* admissions only, which is what makes the
    reserved phase invariant under tier service order rather than merely
    observed to be.
    """
    if not admitted:
        return 0
    if BLOCK_OF[tier] == "recent":
        return len(render_stm_payload(admitted, [])) - EMPTY_PAYLOAD_CHARS
    return len(render_stm_payload([], admitted)) - EMPTY_PAYLOAD_CHARS


def allocate(
    state: CandidateState,
    *,
    budget: int,
    floors: Mapping[str, float],
    relevance_by_id: Mapping[str, float] | None = None,
    service: Sequence[str] = OWNERSHIP_DEFAULT,
    ownership: Sequence[str] = OWNERSHIP_DEFAULT,
    contest: str = "relevance",
) -> FloorsPack:
    """Reserved floors, then a contested remainder, at exact serialized cost.

    Phase 1 gives tier ``t`` an allowance of ``floors[t]`` of the content
    budget and lets it pack its own owned candidates into that allowance
    alone. Phase 2 hands every candidate that did not get in - from any tier -
    to a single contest for whatever room is actually left.

    Both phases charge exact serialized cost and skip on overflow rather than
    stopping, which is ``episodic._packing.DROP_POLICY`` unchanged.
    """
    if contest not in CONTESTS:
        raise TC003ExplorationError(f"Unregistered contest order: {contest!r}")
    if sorted(service) != sorted(TIERS) or sorted(ownership) != sorted(TIERS):
        raise TC003ExplorationError(
            f"service and ownership must each permute {TIERS}"
        )
    if any(floors.get(tier, 0.0) < 0.0 for tier in TIERS):
        raise TC003ExplorationError("A floor share may not be negative")
    if sum(floors.get(tier, 0.0) for tier in TIERS) > 1.0 + 1e-9:
        raise TC003ExplorationError("Floor shares may not exceed the budget")

    offers = tier_offers(state)
    owner: dict[str, str] = {}
    record_by_id: dict[str, dict] = {}
    for tier in ownership:
        for episode in offers[tier]:
            identifier = str(episode["id"])
            record_by_id.setdefault(identifier, episode)
            owner.setdefault(identifier, tier)

    if budget < EMPTY_PAYLOAD_CHARS:
        return FloorsPack(
            payload="",
            selected_ids=(),
            dropped_ids=tuple(_consideration_ids(offers, service)),
            owner=owner,
            shares={tier: float(floors.get(tier, 0.0)) for tier in TIERS},
            allowances={tier: 0 for tier in TIERS},
            reserved_spend={tier: 0 for tier in TIERS},
            reserved_admitted={tier: 0 for tier in TIERS},
            contested_admitted={tier: 0 for tier in TIERS},
            remainder_chars=0,
        )

    content_budget = budget - EMPTY_PAYLOAD_CHARS
    allowances = {
        tier: int(floors.get(tier, 0.0) * content_budget) for tier in TIERS
    }

    # ---- Phase 1: reserved, and independent between tiers ------------------
    admitted: dict[str, list[dict]] = {tier: [] for tier in TIERS}
    admitted_ids: set[str] = set()
    for tier in service:
        allowance = allowances[tier]
        if allowance <= 0:
            continue
        for episode in offers[tier]:
            identifier = str(episode["id"])
            if owner[identifier] != tier or identifier in admitted_ids:
                continue
            candidate = [*admitted[tier], episode]
            if tier_spend(tier, candidate) <= allowance:
                admitted[tier] = candidate
                admitted_ids.add(identifier)

    reserved_spend = {tier: tier_spend(tier, admitted[tier]) for tier in TIERS}
    reserved_admitted = {tier: len(admitted[tier]) for tier in TIERS}
    payload = _render(admitted, ownership)
    if len(payload) > budget:
        raise TC003ExplorationError(
            "Reserved phase exceeded the budget, which solo accounting "
            f"forbids: {len(payload)} > {budget}"
        )
    remainder_chars = budget - len(payload)

    # ---- Phase 2: one contest for whatever room is left ---------------------
    contested_admitted = {tier: 0 for tier in TIERS}
    dropped: list[str] = []
    for identifier in _contest_order(
        offers, service, contest, relevance_by_id, admitted_ids
    ):
        episode = record_by_id[identifier]
        tier = owner[identifier]
        trial = {key: list(value) for key, value in admitted.items()}
        trial[tier].append(episode)
        rendered = _render(trial, ownership)
        if len(rendered) <= budget:
            admitted = trial
            admitted_ids.add(identifier)
            contested_admitted[tier] += 1
        else:
            dropped.append(identifier)

    # Only now is the block order made canonical. Exact serialized cost
    # depends on the delivered *set* and not on its arrangement, so the
    # admission tests above are unaffected by the order candidates happened
    # to arrive in - but the delivered bytes are, and the committed packers
    # each render a tier in that tier's own offer order.
    admitted = _canonical(admitted, offers)
    payload = _render(admitted, ownership)
    if len(payload) > budget:
        raise TC003ExplorationError("Floors payload exceeded its budget")
    selected_ids = tuple(
        str(episode["id"]) for episode in _render_order(admitted, ownership)
    )
    if len(selected_ids) != len(set(selected_ids)):
        raise TC003ExplorationError("Floors payload contains a duplicate episode")
    return FloorsPack(
        payload=payload,
        selected_ids=selected_ids,
        dropped_ids=tuple(dropped),
        owner=owner,
        shares={tier: float(floors.get(tier, 0.0)) for tier in TIERS},
        allowances=allowances,
        reserved_spend=reserved_spend,
        reserved_admitted=reserved_admitted,
        contested_admitted=contested_admitted,
        remainder_chars=remainder_chars,
    )


def _canonical(
    admitted: Mapping[str, Sequence[dict]],
    offers: Mapping[str, Sequence[dict]],
) -> dict[str, list[dict]]:
    """Each tier's admissions restored to that tier's own offer order."""
    result: dict[str, list[dict]] = {}
    for tier in TIERS:
        chosen = {str(episode["id"]) for episode in admitted[tier]}
        result[tier] = [
            episode
            for episode in offers[tier]
            if str(episode["id"]) in chosen
        ]
    return result


def _blocks(
    admitted: Mapping[str, Sequence[dict]], ownership: Sequence[str]
) -> tuple[list[dict], list[dict]]:
    """Rendered contents of the two blocks, in ownership order within each.

    Ownership order, not service order: this is what makes a floors payload
    byte-identical under a service permutation rather than merely
    set-identical, and it is also what reproduces both committed packers,
    which each render a recency/K overlap in ``recent_context``.
    """
    recent: list[dict] = []
    stm: list[dict] = []
    for tier in ownership:
        target = recent if BLOCK_OF[tier] == "recent" else stm
        target.extend(admitted[tier])
    return recent, stm


def _render_order(
    admitted: Mapping[str, Sequence[dict]], ownership: Sequence[str]
) -> list[dict]:
    recent, stm = _blocks(admitted, ownership)
    return [*recent, *stm]


def _render(
    admitted: Mapping[str, Sequence[dict]], ownership: Sequence[str]
) -> str:
    recent, stm = _blocks(admitted, ownership)
    return render_stm_payload(recent, stm)


def _consideration_ids(
    offers: Mapping[str, Sequence[dict]], service: Sequence[str]
) -> list[str]:
    seen: set[str] = set()
    order: list[str] = []
    for tier in service:
        for episode in offers[tier]:
            identifier = str(episode["id"])
            if identifier in seen:
                continue
            seen.add(identifier)
            order.append(identifier)
    return order


def _contest_order(
    offers: Mapping[str, Sequence[dict]],
    service: Sequence[str],
    contest: str,
    relevance_by_id: Mapping[str, float] | None,
    admitted_ids: set[str],
) -> list[str]:
    """Who competes for the remainder, and in what order.

    ``relevance`` is the registered contest: every candidate the reserved
    phase did not admit, ranked by its own cosine with the library's own
    ``(-relevance, turn_number, id)`` tie-break. The key names no tier, so
    permuting the tiers cannot move it. That is not a convenience - an
    allocator whose remainder is contested in tier order is order-dependent
    again the moment the remainder is non-empty, which is most of the time.

    ``tier`` is the sequential contest, and exists so that zeroing the floors
    reproduces the two committed packers exactly.
    """
    pending = [
        identifier
        for identifier in _consideration_ids(offers, service)
        if identifier not in admitted_ids
    ]
    if contest == "tier":
        return pending
    if relevance_by_id is None:
        raise TC003ExplorationError(
            "The relevance contest needs relevance scores; none were supplied"
        )
    record_by_id = {
        str(episode["id"]): episode
        for tier in TIERS
        for episode in offers[tier]
    }
    return sorted(
        pending,
        key=lambda identifier: (
            -relevance_by_id[identifier],
            int(record_by_id[identifier]["turn_number"]),
            identifier,
        ),
    )


# --------------------------------------------------------------------------
# The arms
# --------------------------------------------------------------------------


def relevance_map(records: Sequence[dict], query_embedding) -> dict[str, float]:
    """The library's own cosine, keyed by identity."""
    if not records:
        return {}
    scores = relevance_vector(vector(query_embedding), records)
    return {
        str(record["id"]): float(scores[index])
        for index, record in enumerate(records)
    }


def floors_context(
    episodes: Sequence[Episode],
    query: np.ndarray,
    budget: int,
    config: EpisodicConfig,
    *,
    service: Sequence[str] = OWNERSHIP_DEFAULT,
    ownership: Sequence[str] = OWNERSHIP_DEFAULT,
) -> tuple[str, tuple[str, ...], dict[str, Any]]:
    """A_FLOORS (shipped config) and A_FLOORS_DUAL (dual config).

    One rule, two configurations. The candidate sets are built once at the
    full budget by the unchanged ``build_candidate_state``, so the only thing
    that differs from the fixed-order arms is how the budget is allocated
    between tiers that were handed identical members.
    """
    records = [episode.record for episode in episodes]
    state = build_candidate_state(
        episodes=records,
        query_embedding=query,
        budget=budget,
        config=config,
    )
    pack = floors_pack(
        state,
        relevance_map(records, query),
        budget,
        service=service,
        ownership=ownership,
    )
    return pack.payload, _delivered_ids(pack.payload, records), _counts(pack, state)


def floors_pack(
    state: CandidateState,
    relevance: Mapping[str, float],
    budget: int,
    *,
    service: Sequence[str] = OWNERSHIP_DEFAULT,
    ownership: Sequence[str] = OWNERSHIP_DEFAULT,
) -> FloorsPack:
    """The registered floors arm over an already-built candidate state.

    Split out so a caller that has already paid for the clustering does not
    pay for it again. That cost is not incidental: at this corpus's pool size
    ``build_candidate_state`` is roughly 97 ms and one allocation is under 6.
    """
    return allocate(
        state,
        budget=budget,
        floors=equal_shares(state),
        relevance_by_id=relevance,
        service=service,
        ownership=ownership,
        contest="relevance",
    )


def _counts(pack: FloorsPack, state: CandidateState) -> dict[str, Any]:
    delivered = pack.delivered
    per_tier = {
        tier: sum(
            1 for identifier in delivered if pack.owner.get(identifier) == tier
        )
        for tier in TIERS
    }
    return {
        "recency": per_tier["n"],
        "k": per_tier["k"],
        "coverage": per_tier["c"],
        "n_offered": len(state.recent),
        "k_offered": len(state.k_hits),
        "coverage_offered": len(state.coverage),
        "pool_size": state.pool_size,
        "chars_delivered": len(pack.payload),
        "shares": pack.shares,
        "allowances": pack.allowances,
        "reserved_spend": pack.reserved_spend,
        "reserved_admitted": pack.reserved_admitted,
        "contested_admitted": pack.contested_admitted,
        "remainder_chars": pack.remainder_chars,
    }


# --------------------------------------------------------------------------
# Identity and invariance gates
# --------------------------------------------------------------------------


def assert_zero_floor_reduction(
    state: CandidateState,
    records: Sequence[dict],
    query: np.ndarray,
    budget: int,
    config: EpisodicConfig,
) -> dict[str, Any]:
    """The allocator with no floors *is* the two committed packers.

    Not "behaves like": the payload strings are compared byte-for-byte. If
    this ever fails, the floors arm is a rewrite of the packers and every
    contrast built on it is measuring the rewrite as well as the floors.
    """
    zero = {tier: 0.0 for tier in TIERS}

    n_first = allocate(
        state, budget=budget, floors=zero, service=("n", "k", "c"), contest="tier"
    )
    shipped_n = pack_stm_payload(
        list(state.recent), [*state.k_hits, *state.coverage], budget
    )
    if n_first.payload != shipped_n.payload:
        raise TC003ExplorationError(
            "Zero-floor (n, k, c) diverged from pack_stm_payload at budget "
            f"{budget}, N={config.recency_window_n}"
        )

    k_first = allocate(
        state, budget=budget, floors=zero, service=("k", "n", "c"), contest="tier"
    )
    shipped_k = pack_k_first(state, budget=budget)
    if k_first.payload != shipped_k.payload:
        raise TC003ExplorationError(
            "Zero-floor (k, n, c) diverged from pack_k_first at budget "
            f"{budget}, N={config.recency_window_n}"
        )

    library, _report = build_context(
        episodes=records,
        query_embedding=query,
        budget=budget,
        config=config,
    )
    if n_first.payload != library:
        raise TC003ExplorationError(
            "Zero-floor (n, k, c) diverged from build_context at budget "
            f"{budget}, N={config.recency_window_n}"
        )
    return {
        "n_first_chars": len(n_first.payload),
        "k_first_chars": len(k_first.payload),
        "orders_agree": n_first.payload == k_first.payload,
    }


def _shares_for(state: CandidateState, floors: str) -> dict[str, float]:
    if floors == "equal":
        return equal_shares(state)
    if floors == "zero":
        return {tier: 0.0 for tier in TIERS}
    raise TC003ExplorationError(f"Unregistered floor rule: {floors!r}")


def service_permutation(
    state: CandidateState,
    relevance: Mapping[str, float],
    budget: int,
    *,
    floors: str,
) -> dict[str, Any]:
    """Does permuting the tier service order change what is delivered?

    ``floors="equal"`` is the arm under test; ``floors="zero"`` is the
    control, and the control is not optional. Without it, "the floors
    allocator is order-invariant" is a claim about an instrument that has
    never been shown capable of registering a difference.
    """
    shares = _shares_for(state, floors)
    contest = "relevance" if floors == "equal" else "tier"

    payloads: dict[str, str] = {}
    sets: dict[str, frozenset[str]] = {}
    for order in SERVICE_ORDERS:
        pack = allocate(
            state,
            budget=budget,
            floors=shares,
            relevance_by_id=relevance,
            service=order,
            contest=contest,
        )
        payloads["".join(order)] = pack.payload
        sets["".join(order)] = pack.delivered
    reference = "".join(SERVICE_ORDERS[0])
    return {
        "floors": floors,
        "contest": contest,
        "orders": len(SERVICE_ORDERS),
        "set_invariant": all(value == sets[reference] for value in sets.values()),
        "payload_invariant": all(
            value == payloads[reference] for value in payloads.values()
        ),
        "distinct_sets": len({tuple(sorted(value)) for value in sets.values()}),
        "distinct_payloads": len(set(payloads.values())),
    }


def ownership_permutation(
    state: CandidateState,
    relevance: Mapping[str, float],
    budget: int,
    *,
    floors: str,
) -> dict[str, Any]:
    """Floors remove the service order. They do not remove this one.

    A candidate in more than one tier has to be paid for by exactly one floor
    and rendered in exactly one block. Which one is a fixed convention -
    ``build_context``'s recency-wins rule - and permuting *that* is a second
    order the design still depends on. This function measures the effect; it
    asserts nothing, because whether the effect exists at all depends on
    whether the tiers overlap on this corpus, which is PF4's question.

    ``floors="zero"`` is the reference, and it is the one that says whether
    floors *created* this sensitivity or merely inherited it: under
    sequential fill ownership decides only which block renders a candidate,
    while under floors it also decides which allowance pays for it.
    """
    shares = _shares_for(state, floors)
    contest = "relevance" if floors == "equal" else "tier"
    offers = tier_offers(state)
    membership: dict[str, set[str]] = {
        tier: {str(episode["id"]) for episode in offers[tier]} for tier in TIERS
    }
    everything = set().union(*membership.values()) if membership else set()
    overlaps = {
        "n_and_k": len(membership["n"] & membership["k"]),
        "n_and_c": len(membership["n"] & membership["c"]),
        "k_and_c": len(membership["k"] & membership["c"]),
        "in_two_or_more": sum(
            1
            for identifier in everything
            if sum(identifier in members for members in membership.values()) > 1
        ),
    }

    sets: dict[str, frozenset[str]] = {}
    for order in SERVICE_ORDERS:
        pack = allocate(
            state,
            budget=budget,
            floors=shares,
            relevance_by_id=relevance,
            service=OWNERSHIP_DEFAULT,
            ownership=order,
            contest=contest,
        )
        sets["".join(order)] = pack.delivered
    reference = "".join(OWNERSHIP_DEFAULT)
    return {
        "floors": floors,
        "overlaps": overlaps,
        "set_invariant": all(value == sets[reference] for value in sets.values()),
        "distinct_sets": len({tuple(sorted(value)) for value in sets.values()}),
        "max_symmetric_difference": max(
            len(value ^ sets[reference]) for value in sets.values()
        ),
    }


# --------------------------------------------------------------------------
# Part 1
# --------------------------------------------------------------------------


def explore(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    conversations = adapt_development(DATASET_PATH)

    with EmbeddingCache(
        CACHE_PATH,
        mode="reuse",
        expected_file_sha256=manifest["cache"]["file_sha256"],
        expected_content_sha256=manifest["cache"]["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDER_SHA256,
    ) as cache:
        vectors = {
            text: np.asarray(cache(text), dtype=np.float32)
            for case in conversations
            for text in (
                *(pair.text for pair in case.pairs),
                *(question.question for question in case.questions),
            )
        }
        reuse = cache.record()
    if reuse["misses"]:
        raise TC003ExplorationError(
            f"Read-only cache reported {reuse['misses']} misses; Part 1 must "
            "cost zero model calls"
        )

    by_conversation = {
        case.sample_id: build_episodes(case, vectors) for case in conversations
    }

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PREFLIGHT_PART_1_EXPLORATION_ONLY",
        "note": (
            "No arm's absolute availability appears in this artifact. The "
            "null band registered from it is derived from within-arm sham "
            "budget perturbations only, and the invariance sections report "
            "delivered-set identity, never evidence."
        ),
        "inputs": _inputs(manifest, reuse),
        "floor_rule": {
            "name": "equal_shares_among_populated_tiers",
            "free_parameters": 0,
            "shipped_config": "1/3 each when all three tiers are populated",
            "dual_config": "0, 1/2, 1/2 - the recency tier is empty",
            "populated_read_from": "tier membership, before ownership",
        },
        "corpus": _corpus_shape(conversations, by_conversation),
        "sweep": {},
        "sham_band": {},
        "cost": {},
    }

    for budget in BUDGETS:
        result["sweep"][str(budget)] = _sweep(
            conversations, by_conversation, vectors, budget
        )
        result["sham_band"][str(budget)] = _sham_band(
            conversations, by_conversation, vectors, budget
        )
    result["sham_band"]["max_abs_net"] = max(
        result["sham_band"][str(budget)]["max_abs_net"] for budget in BUDGETS
    )
    result["sham_band"]["band_definition"] = (
        "The largest absolute gains-minus-losses any sham budget perturbation "
        "produced within a single floors arm, over both budgets and both "
        "endpoints. TC-001 measured 4, TC-001B 3, and TC-002 7 at 32,000 and "
        "4 at 16,000 for the arms this study inherits; the registration takes "
        "the maximum over all of them at each budget."
    )
    result["cost"] = _cost(conversations, by_conversation, vectors)
    result["elapsed_seconds"] = round(time.time() - started, 3)

    path = output_dir / "tc003_preflight_part1.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _inputs(manifest: dict, reuse: dict) -> dict[str, Any]:
    return {
        "dataset_sha256": sha256_file(DATASET_PATH),
        "cache": manifest["cache"],
        "cache_reuse": reuse,
        "embedder_sha256": CARRIED_EMBEDDER_SHA256,
        "sources": {
            _repo_relative(REPO_ROOT / relative): sha256_file(REPO_ROOT / relative)
            for relative in (
                "src/analysis/tc003_exploration.py",
                "src/analysis/ec002_k_first_packing.py",
                "episodic/src/episodic/_context.py",
                "episodic/src/episodic/_packing.py",
                "episodic/src/episodic/_render.py",
                "episodic/src/episodic/_selection.py",
            )
        },
    }


def _corpus_shape(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
) -> dict[str, Any]:
    evaluable = [
        question
        for case in conversations
        for question in case.questions
        if not question.duplicate_ordinal and question.resolved_evidence_ids
    ]
    return {
        "conversations": len(conversations),
        "episodes": {
            case.sample_id: len(by_conversation[case.sample_id])
            for case in conversations
        },
        "evaluable_questions": len(evaluable),
        "empty_payload_chars": EMPTY_PAYLOAD_CHARS,
    }


def _sweep(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    budget: int,
) -> dict[str, Any]:
    """One pass per configuration: identity gate, behaviour, invariance.

    Each question's candidate state is built once and every check below reads
    it, because the clustering is the cost and the allocation is not.
    """
    out: dict[str, Any] = {}
    for arm, config in FLOOR_CONFIGS.items():
        reductions = 0
        rows: list[dict[str, Any]] = []
        service_equal: list[dict[str, Any]] = []
        service_zero: list[dict[str, Any]] = []
        ownership_equal: list[dict[str, Any]] = []
        ownership_zero: list[dict[str, Any]] = []

        for case in conversations:
            episodes = by_conversation[case.sample_id]
            records = [episode.record for episode in episodes]
            for question in case.questions:
                if question.duplicate_ordinal or not question.resolved_evidence_ids:
                    continue
                query = vectors[question.question]
                state = build_candidate_state(
                    episodes=records,
                    query_embedding=query,
                    budget=budget,
                    config=config,
                )
                relevance = relevance_map(records, query)
                assert_zero_floor_reduction(state, records, query, budget, config)
                reductions += 1

                pack = floors_pack(state, relevance, budget)
                rows.append(_row(pack, state, budget))
                service_equal.append(
                    service_permutation(state, relevance, budget, floors="equal")
                )
                service_zero.append(
                    service_permutation(state, relevance, budget, floors="zero")
                )
                ownership_equal.append(
                    ownership_permutation(state, relevance, budget, floors="equal")
                )
                ownership_zero.append(
                    ownership_permutation(state, relevance, budget, floors="zero")
                )

        out[arm] = {
            "config": {
                "recency_window_n": config.recency_window_n,
                "k_threshold": config.k_threshold,
            },
            "identity": {
                "questions_checked": reductions,
                "claim": (
                    "With every floor at zero and the remainder contested in "
                    "tier order, the allocator produced byte-identical "
                    "payloads to pack_stm_payload, to build_context, and to "
                    "EC-002's pack_k_first, on every question checked."
                ),
                "status": "PASS",
            },
            "behaviour": _behaviour(rows),
            "invariance": {
                "service_floors": _invariance_summary(service_equal),
                "service_zero_control": _invariance_summary(service_zero),
                "ownership_floors": _ownership_summary(ownership_equal),
                "ownership_zero_reference": _ownership_summary(ownership_zero),
            },
        }
    return out


def _row(pack: FloorsPack, state: CandidateState, budget: int) -> dict[str, Any]:
    offers = tier_offers(state)
    owned = {
        tier: sum(
            1 for episode in offers[tier] if pack.owner[str(episode["id"])] == tier
        )
        for tier in TIERS
    }
    delivered = pack.delivered
    per_tier = {
        tier: sum(
            1 for identifier in delivered if pack.owner.get(identifier) == tier
        )
        for tier in TIERS
    }
    return {
        "budget_chars": budget,
        "chars_delivered": len(pack.payload),
        "episodes_delivered": len(delivered),
        "remainder_chars": pack.remainder_chars,
        "offered": {tier: len(offers[tier]) for tier in TIERS},
        "owned": owned,
        "allowances": pack.allowances,
        "reserved_spend": pack.reserved_spend,
        "reserved_admitted": pack.reserved_admitted,
        "contested_admitted": pack.contested_admitted,
        "delivered_by_tier": per_tier,
        # A floor *binds* when its tier had owned candidates it could not fit
        # inside the allowance. A floor that never binds is decoration.
        "floor_binds": {
            tier: owned[tier] > pack.reserved_admitted[tier] for tier in TIERS
        },
        # A floor is *slack* when the tier ran out of candidates before it ran
        # out of allowance, so the reservation went back to the contest.
        "floor_slack": {
            tier: owned[tier] == pack.reserved_admitted[tier]
            and pack.allowances[tier] > 0
            for tier in TIERS
        },
        "everything_fits": len(delivered)
        == len({str(e["id"]) for tier in TIERS for e in offers[tier]}),
    }


def _behaviour(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"questions": 0}
    return {
        "questions": len(rows),
        "chars_delivered": _distribution(r["chars_delivered"] for r in rows),
        "episodes_delivered": _distribution(r["episodes_delivered"] for r in rows),
        "remainder_after_reserved": _distribution(
            r["remainder_chars"] for r in rows
        ),
        "offered": {
            tier: _distribution(r["offered"][tier] for r in rows) for tier in TIERS
        },
        "delivered_by_tier": _distribution_by_tier(rows, "delivered_by_tier"),
        "reserved_admitted": _distribution_by_tier(rows, "reserved_admitted"),
        "contested_admitted": _distribution_by_tier(rows, "contested_admitted"),
        "allowance_chars": _distribution_by_tier(rows, "allowances"),
        "floor_binds_questions": {
            tier: sum(1 for r in rows if r["floor_binds"][tier]) for tier in TIERS
        },
        "floor_slack_questions": {
            tier: sum(1 for r in rows if r["floor_slack"][tier]) for tier in TIERS
        },
        # The degenerate state, demonstrated rather than assumed: when every
        # offered candidate fits, allocation cannot matter and no arm can
        # differ from any other.
        "everything_fits_questions": sum(1 for r in rows if r["everything_fits"]),
        "contest_admitted_nothing_questions": sum(
            1 for r in rows if sum(r["contested_admitted"].values()) == 0
        ),
    }


def _distribution_by_tier(
    rows: Sequence[dict[str, Any]], key: str
) -> dict[str, Any]:
    return {tier: _distribution(row[key][tier] for row in rows) for tier in TIERS}


def _invariance_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"questions": 0}
    return {
        "questions": len(rows),
        "orders_compared": rows[0]["orders"],
        "contest": rows[0]["contest"],
        "set_invariant_questions": sum(1 for r in rows if r["set_invariant"]),
        "payload_invariant_questions": sum(
            1 for r in rows if r["payload_invariant"]
        ),
        "distinct_sets": _distribution(r["distinct_sets"] for r in rows),
    }


def _ownership_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"questions": 0}
    return {
        "questions": len(rows),
        "set_invariant_questions": sum(1 for r in rows if r["set_invariant"]),
        "distinct_sets": _distribution(r["distinct_sets"] for r in rows),
        "symmetric_difference": _distribution(
            r["max_symmetric_difference"] for r in rows
        ),
        "candidates_in_two_or_more_tiers": _distribution(
            r["overlaps"]["in_two_or_more"] for r in rows
        ),
        "overlap_n_and_k": _distribution(r["overlaps"]["n_and_k"] for r in rows),
        "overlap_k_and_c": _distribution(r["overlaps"]["k_and_c"] for r in rows),
        "overlap_n_and_c": _distribution(r["overlaps"]["n_and_c"] for r in rows),
        "questions_with_no_overlap": sum(
            1 for r in rows if r["overlaps"]["in_two_or_more"] == 0
        ),
    }


def _sham_band(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    budget: int,
) -> dict[str, Any]:
    """The null band for the two floors arms, measured within each arm.

    TC-001's method, TC-001B's correction (both endpoints, not just one) and
    TC-002's correction (per budget, because the band moved from 4 to 7 when
    the budget changed). The arms this study inherits are not re-measured;
    their bands are already committed and the registration carries the maximum.
    """
    endpoints = ("any", "complete")
    arms = tuple(FLOOR_CONFIGS)
    baseline: dict[str, dict[str, dict[str, bool]]] = {
        arm: {endpoint: {} for endpoint in endpoints} for arm in arms
    }
    wanted: dict[str, frozenset[str]] = {}

    for case in conversations:
        episodes = by_conversation[case.sample_id]
        evidence = _evidence_index(case, episodes)
        for question in case.questions:
            if question.duplicate_ordinal or not question.resolved_evidence_ids:
                continue
            query = vectors[question.question]
            target = evidence[question.identity]
            wanted[question.identity] = target
            for arm, delivered in _floor_arms(episodes, query, budget):
                hits = set(delivered)
                baseline[arm]["any"][question.identity] = bool(target & hits)
                baseline[arm]["complete"][question.identity] = target <= hits

    per_arm: dict[str, dict[str, list]] = {
        arm: {endpoint: [] for endpoint in endpoints} for arm in arms
    }
    for fraction in SHAM_FRACTIONS:
        nudged = int(round(budget * (1.0 + fraction)))
        counts = {arm: {endpoint: [0, 0] for endpoint in endpoints} for arm in arms}
        for case in conversations:
            episodes = by_conversation[case.sample_id]
            for question in case.questions:
                if question.duplicate_ordinal or not question.resolved_evidence_ids:
                    continue
                query = vectors[question.question]
                target = wanted[question.identity]
                for arm, delivered in _floor_arms(episodes, query, nudged):
                    hits = set(delivered)
                    _score(
                        counts[arm]["any"],
                        baseline[arm]["any"][question.identity],
                        bool(target & hits),
                    )
                    _score(
                        counts[arm]["complete"],
                        baseline[arm]["complete"][question.identity],
                        target <= hits,
                    )
        for arm in arms:
            for endpoint in endpoints:
                gains, losses = counts[arm][endpoint]
                per_arm[arm][endpoint].append(
                    _sham_row(fraction, budget, nudged, gains, losses)
                )

    nets = [
        abs(row["net"])
        for arm in arms
        for endpoint in endpoints
        for row in per_arm[arm][endpoint]
    ]
    return {
        "budget_chars": budget,
        "arms": list(arms),
        "endpoints": list(endpoints),
        "evaluable_questions": len(wanted),
        "perturbations": per_arm,
        "max_abs_net": max(nets),
    }


def _floor_arms(
    episodes: Sequence[Episode], query: np.ndarray, budget: int
) -> tuple[tuple[str, Sequence[str]], ...]:
    out: list[tuple[str, Sequence[str]]] = []
    for arm, config in FLOOR_CONFIGS.items():
        _payload, delivered, _tier_counts = floors_context(
            episodes, query, budget, config
        )
        out.append((arm, delivered))
    return tuple(out)


def _cost(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
) -> dict[str, Any]:
    """What allocation costs, separated from what candidate selection costs.

    Section 10 of the roadmap puts clustering at 81% of selection latency and
    rising. If floors are to be argued about on cost as well as on delivery,
    the allocator's own share has to be visible next to the clustering's.
    """
    allocate_ms: list[float] = []
    state_ms: list[float] = []
    for case in conversations:
        episodes = by_conversation[case.sample_id]
        records = [episode.record for episode in episodes]
        for question in [q for q in case.questions if not q.duplicate_ordinal][:40]:
            query = vectors[question.question]
            started = time.perf_counter()
            state = build_candidate_state(
                episodes=records,
                query_embedding=query,
                budget=BUDGETS[0],
                config=SHIPPED_CONFIG,
            )
            state_ms.append((time.perf_counter() - started) * 1_000.0)
            relevance = relevance_map(records, query)
            started = time.perf_counter()
            floors_pack(state, relevance, BUDGETS[0])
            allocate_ms.append((time.perf_counter() - started) * 1_000.0)
    return {
        "budget_chars": BUDGETS[0],
        "questions": len(allocate_ms),
        "build_candidate_state_ms": _float_distribution(state_ms),
        "allocate_ms": _float_distribution(allocate_ms),
    }


def _distribution(values: Iterable[int]) -> dict[str, Any]:
    ordered = sorted(int(value) for value in values)
    if not ordered:
        return {"n": 0}
    return {
        "n": len(ordered),
        "min": ordered[0],
        "p25": ordered[len(ordered) // 4],
        "median": int(statistics.median(ordered)),
        "p75": ordered[(3 * len(ordered)) // 4],
        "max": ordered[-1],
        "mean": round(statistics.fmean(ordered), 3),
    }


def _float_distribution(values: Iterable[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {"n": 0}
    return {
        "n": len(ordered),
        "min": round(ordered[0], 3),
        "median": round(statistics.median(ordered), 3),
        "p95": round(ordered[int(0.95 * (len(ordered) - 1))], 3),
        "max": round(ordered[-1], 3),
        "mean": round(statistics.fmean(ordered), 3),
    }


__all__ = [
    "BLOCK_OF",
    "CONTESTS",
    "FLOOR_CONFIGS",
    "FloorsPack",
    "OWNERSHIP_DEFAULT",
    "SCHEMA",
    "SERVICE_ORDERS",
    "TIERS",
    "TC003ExplorationError",
    "allocate",
    "assert_zero_floor_reduction",
    "equal_shares",
    "explore",
    "floors_context",
    "floors_pack",
    "ownership_permutation",
    "relevance_map",
    "service_permutation",
    "tier_offers",
    "tier_spend",
]

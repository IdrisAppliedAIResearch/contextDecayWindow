"""IC-001: packing order as the single variable, on the internal corpus.

Two arms differ in exactly one respect - the order in which unique episode
identities are offered to the exact serializer:

    B0  recency -> K -> coverage   (the deployed order, carried since Study 001)
    B1  K -> recency -> coverage   (EC-002's A1 order)

Everything else is held fixed. The candidate lists themselves are not
recomputed: they are the identities the deployed run committed to its
context log, so no vector is re-derived and no model is called. Selected
episodes keep their original render tier, so a K/recency overlap is
*considered* at K priority in B1 but still renders inside
``recent_context`` - EC-002's rule, unchanged.

Charging is the post-DR-001 exact serialized cost of the whole two-block
payload, and a candidate that does not fit is skipped rather than
stopping the walk. That is `episodic._packing.DROP_POLICY`; B0 is
required to reproduce `pack_stm_payload` byte-for-byte, and
`assert_b0_matches_deployed_packer` is the check.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from episodic._packing import EMPTY_PAYLOAD_CHARS, pack_stm_payload
from episodic._render import render_episode_element, render_stm_payload

#: Tier names in their deployed priority order.
TIERS = ("recency", "k", "coverage")

#: The registered arms. The value is the consideration order; the render
#: tier of an admitted episode is independent of it.
PACKING_ORDERS: dict[str, tuple[str, ...]] = {
    "B0": ("recency", "k", "coverage"),
    "B1": ("k", "recency", "coverage"),
}

#: Same overflow policy as the deployed packer, renamed for this replay so
#: an arm's drop behaviour is never inferred from its arm label.
DROP_POLICY = "exact_cost_skip_on_overflow"

FORBIDDEN_MECHANISM_PATH_PARTS = (
    "q_facts_key",
    "rubric",
    "atomic_items",
    "targeted_items",
)


class IC001Error(ValueError):
    """Raised when the registered replay boundary is violated."""


def assert_mechanism_path_allowed(path: str | Path) -> None:
    normalized = str(path).replace("\\", "/").lower()
    if any(part in normalized for part in FORBIDDEN_MECHANISM_PATH_PARTS):
        raise ValueError(
            f"Mechanism path crosses the measurement boundary: {path}"
        )


@dataclass(frozen=True)
class TierState:
    """The deployed run's frozen candidate lists for one probe turn."""

    probe_turn: int
    recency: tuple[dict, ...]
    k_hits: tuple[dict, ...]
    coverage: tuple[dict, ...] = ()

    @property
    def recency_ids(self) -> frozenset[str]:
        return frozenset(str(episode["id"]) for episode in self.recency)

    @property
    def k_ids(self) -> frozenset[str]:
        return frozenset(str(episode["id"]) for episode in self.k_hits)

    def tier_of(self, episode_id: str) -> str:
        if episode_id in self.recency_ids:
            return "recency"
        if episode_id in self.k_ids:
            return "k"
        return "coverage"


@dataclass(frozen=True)
class PackedArm:
    arm: str
    order: tuple[str, ...]
    payload: str
    recent_episodes: tuple[dict, ...]
    stm_episodes: tuple[dict, ...]
    selected_ids: tuple[str, ...]
    dropped_ids: tuple[str, ...]
    considered_ids: tuple[str, ...]
    budget_chars: int

    @property
    def serialized_chars(self) -> int:
        return len(self.payload)

    @property
    def payload_sha256(self) -> str:
        return hashlib.sha256(self.payload.encode("utf-8")).hexdigest()


def pack_arm(state: TierState, *, arm: str, budget: int) -> PackedArm:
    """Fill the window in ``arm``'s consideration order at exact cost."""

    try:
        order = PACKING_ORDERS[arm]
    except KeyError as error:
        raise IC001Error(f"Unregistered arm: {arm}") from error

    tiers = {
        "recency": state.recency,
        "k": state.k_hits,
        "coverage": state.coverage,
    }
    recency_ids = state.recency_ids

    # Render tiers are fixed by membership, never by consideration order:
    # the recency window renders in `recent_context`, K and coverage render
    # in `retrieved_stm` in that priority, deduplicated against recency.
    stm_order = _unique(
        [
            episode
            for episode in (*state.k_hits, *state.coverage)
            if str(episode["id"]) not in recency_ids
        ]
    )

    def render(selected: set[str]) -> tuple[str, tuple[dict, ...], tuple[dict, ...]]:
        recent = tuple(
            episode
            for episode in state.recency
            if str(episode["id"]) in selected
        )
        stm = tuple(
            episode for episode in stm_order if str(episode["id"]) in selected
        )
        return render_stm_payload(recent, stm), recent, stm

    consideration = _unique([episode for tier in order for episode in tiers[tier]])
    considered_ids = tuple(str(episode["id"]) for episode in consideration)

    if budget < EMPTY_PAYLOAD_CHARS:
        return PackedArm(
            arm=arm,
            order=order,
            payload="",
            recent_episodes=(),
            stm_episodes=(),
            selected_ids=(),
            dropped_ids=considered_ids,
            considered_ids=considered_ids,
            budget_chars=budget,
        )

    selected: set[str] = set()
    dropped: list[str] = []
    for candidate in consideration:
        identifier = str(candidate["id"])
        payload, _recent, _stm = render({*selected, identifier})
        if len(payload) <= budget:
            selected.add(identifier)
        else:
            dropped.append(identifier)

    payload, recent, stm = render(selected)
    if len(payload) > budget:
        raise AssertionError(f"{arm} payload exceeded its character budget")
    selected_ids = tuple(
        str(episode["id"]) for episode in (*recent, *stm)
    )
    if len(selected_ids) != len(set(selected_ids)):
        raise AssertionError(f"{arm} payload contains a duplicate episode")
    return PackedArm(
        arm=arm,
        order=order,
        payload=payload,
        recent_episodes=recent,
        stm_episodes=stm,
        selected_ids=selected_ids,
        dropped_ids=tuple(dropped),
        considered_ids=considered_ids,
        budget_chars=budget,
    )


def assert_b0_matches_deployed_packer(
    state: TierState,
    packed: PackedArm,
    *,
    budget: int,
) -> dict:
    """B0 must be the deployed packer, not a re-implementation of it.

    `pack_stm_payload` is the shipped N-first function. If this replay's
    generic ordered packer disagrees with it on the deployed order, every
    B1 number downstream is measuring the rewrite rather than the order.
    """

    if packed.arm != "B0":
        raise IC001Error("Deployed-packer equivalence applies to B0 only")
    if state.coverage:
        raise IC001Error(
            "Deployed equivalence is defined for the two-tier deployed "
            "configuration; this state carries a coverage tier"
        )
    recency_ids = state.recency_ids
    deployed = pack_stm_payload(
        state.recency,
        [
            episode
            for episode in state.k_hits
            if str(episode["id"]) not in recency_ids
        ],
        budget,
    )
    equivalent = (
        deployed.payload == packed.payload
        and tuple(deployed.selected_ids) == packed.selected_ids
    )
    if not equivalent:
        raise AssertionError(
            "B0 did not reproduce the deployed pack_stm_payload output"
        )
    return {
        "status": "PASS",
        "deployed_payload_sha256": hashlib.sha256(
            deployed.payload.encode("utf-8")
        ).hexdigest(),
        "replay_payload_sha256": packed.payload_sha256,
        "deployed_serialized_chars": deployed.serialized_chars,
        "replay_serialized_chars": packed.serialized_chars,
        "deployed_selected_ids": list(deployed.selected_ids),
        "replay_selected_ids": list(packed.selected_ids),
    }


def path_accounting(state: TierState, packed: PackedArm) -> dict:
    """Split delivered episodes and characters across the three paths.

    Element characters are the exact serialized cost of each rendered
    ``<episode>`` element. What the elements do not account for is the
    two-block wrapper, reported separately as ``overhead_chars`` so the
    parts sum to the payload exactly.
    """

    episodes = {"recency": [], "k": [], "coverage": []}
    chars = {"recency": 0, "k": 0, "coverage": 0}
    for episode in (*packed.recent_episodes, *packed.stm_episodes):
        identifier = str(episode["id"])
        tier = state.tier_of(identifier)
        episodes[tier].append(identifier)
        chars[tier] += len(render_episode_element(episode))
    element_total = sum(chars.values())
    return {
        "episodes_by_path": {tier: len(ids) for tier, ids in episodes.items()},
        "episode_ids_by_path": episodes,
        "element_chars_by_path": chars,
        "element_chars_total": element_total,
        "overhead_chars": packed.serialized_chars - element_total,
        "serialized_chars": packed.serialized_chars,
        "candidates_by_path": {
            "recency": len(state.recency),
            "k": len(state.k_hits),
            "coverage": len(state.coverage),
        },
    }


def dropped_by_path(state: TierState, packed: PackedArm) -> dict[str, list[str]]:
    dropped: dict[str, list[str]] = {"recency": [], "k": [], "coverage": []}
    for identifier in packed.dropped_ids:
        dropped[state.tier_of(identifier)].append(identifier)
    return dropped


def _unique(episodes: Iterable[dict]) -> tuple[dict, ...]:
    seen: set[str] = set()
    ordered: list[dict] = []
    for episode in episodes:
        identifier = str(episode["id"])
        if identifier in seen:
            continue
        seen.add(identifier)
        ordered.append(episode)
    return tuple(ordered)


def build_tier_state(
    *,
    probe_turn: int,
    n_candidate_ids: Sequence[str],
    k_candidate_ids: Sequence[str],
    by_id: dict[str, dict],
    coverage_ids: Sequence[str] = (),
) -> TierState:
    """Rebuild one probe turn's frozen tiers from committed identities."""

    missing = [
        identifier
        for identifier in (*n_candidate_ids, *k_candidate_ids, *coverage_ids)
        if identifier not in by_id
    ]
    if missing:
        raise IC001Error(
            f"Committed candidate identities absent from the store: {missing}"
        )
    return TierState(
        probe_turn=probe_turn,
        recency=tuple(by_id[str(value)] for value in n_candidate_ids),
        k_hits=tuple(by_id[str(value)] for value in k_candidate_ids),
        coverage=tuple(by_id[str(value)] for value in coverage_ids),
    )

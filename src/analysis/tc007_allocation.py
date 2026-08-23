"""Label-blind rankers and admission-resolved allocator for TC-007.

Only candidate text/vectors, a query vector, and registered allocation constants
enter this module.  Evidence labels and question outcomes are deliberately absent.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.tc005_ranking import PreparedRankers, prepare_rankers, rank_all
from episodic._packing import EMPTY_PAYLOAD_CHARS, pack_stm_payload
from episodic._render import render_stm_payload
from episodic._selection import (
    ClusterDiversitySelector,
    additive_weight,
    deterministic_clusters,
    relevance_vector,
    select,
    unit_vectors,
    vector,
    wrapper_chars,
)
from retrieval_mechanism_ledger.e005 import FacilityLocationSelector

TOTAL_BUDGETS = (16_000, 32_000)
SPREAD_ARMS = ("a3", "facility")
A3_LAMBDA = 0.1
A3_COST_EXPONENT = 0.0
A3_CLUSTER_COUNT = 16
FACILITY_COST_EXPONENT = 0.0


class TC007AllocationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SpreadPrepared:
    episodes: tuple[Any, ...]
    rankers: PreparedRankers
    assignments: np.ndarray
    facility_order: tuple[int, ...]


@dataclass(frozen=True)
class Allocation:
    payload: str
    selected_ids: tuple[str, ...]
    initial_relevance_ids: tuple[str, ...]
    spread_ids: tuple[str, ...]
    returned_relevance_ids: tuple[str, ...]
    skipped_spread_duplicates: tuple[str, ...]
    dropped_relevance_ids: tuple[str, ...]
    dropped_spread_ids: tuple[str, ...]
    owner: Mapping[str, str]
    phase: Mapping[str, str]
    total_budget: int
    half_allowance: int
    initial_relevance_solo_chars: int
    spread_solo_chars: int
    merged_initial_chars: int
    wrapper_savings: int
    returned_capacity: int

    @property
    def payload_sha256(self) -> str:
        return hashlib.sha256(self.payload.encode("utf-8")).hexdigest()


def _records(episodes: Sequence[Any]) -> list[dict]:
    return [episode.record for episode in episodes]


def _complete_budget(records: Sequence[dict]) -> int:
    if not records:
        return EMPTY_PAYLOAD_CHARS
    return wrapper_chars() + sum(additive_weight(record) for record in records)


def prepare(episodes: Sequence[Any], query_vector: np.ndarray) -> SpreadPrepared:
    """Prepare the frozen dense store, k=16 clusters, and pure facility order."""

    frozen = tuple(episodes)
    if not frozen:
        raise TC007AllocationError("TC-007 requires at least one candidate")
    records = _records(frozen)
    assignments = deterministic_clusters(records, A3_CLUSTER_COUNT)
    similarity = unit_vectors(records) @ unit_vectors(records).T
    facility = FacilityLocationSelector(
        cost_exponent=FACILITY_COST_EXPONENT,
        similarity=similarity,
    )
    result = select(
        candidates=records,
        query_embedding=query_vector,
        selector=facility,
        budget_chars=_complete_budget(records),
    )
    by_id = {episode.identity: index for index, episode in enumerate(frozen)}
    order = tuple(by_id[identifier] for identifier in result.selected_ids)
    if sorted(order) != list(range(len(frozen))):
        raise TC007AllocationError("Facility order did not permute the store")
    return SpreadPrepared(
        episodes=frozen,
        rankers=prepare_rankers(frozen),
        assignments=assignments,
        facility_order=order,
    )


def orders(
    prepared: SpreadPrepared,
    question_text: str,
    query_vector: np.ndarray,
) -> dict[str, tuple[int, ...]]:
    """Return complete dense, shipped-A3, and pure-facility orders."""

    episodes = prepared.episodes
    dense = rank_all(
        episodes, question_text, query_vector, prepared.rankers
    )["dense"].order
    selector = ClusterDiversitySelector(
        lambda_=A3_LAMBDA,
        cost_exponent=A3_COST_EXPONENT,
        assignments=prepared.assignments,
        cluster_count=A3_CLUSTER_COUNT,
    )
    result = select(
        candidates=_records(episodes),
        query_embedding=query_vector,
        selector=selector,
        budget_chars=_complete_budget(_records(episodes)),
    )
    by_id = {episode.identity: index for index, episode in enumerate(episodes)}
    a3 = tuple(by_id[identifier] for identifier in result.selected_ids)
    output = {"dense": tuple(dense), "a3": a3, "facility": prepared.facility_order}
    expected = list(range(len(episodes)))
    if any(sorted(order) != expected for order in output.values()):
        raise TC007AllocationError("A TC-007 order did not permute the store")
    return output


def allocate(
    episodes: Sequence[Any],
    relevance_order: Sequence[int],
    spread_order: Sequence[int],
    total_budget: int,
) -> Allocation:
    """50/50 solo admissions, spread dedup, then relevance slack return."""

    if total_budget not in TOTAL_BUDGETS:
        raise TC007AllocationError(f"Unregistered budget: {total_budget}")
    expected = list(range(len(episodes)))
    if sorted(relevance_order) != expected or (
        spread_order and sorted(spread_order) != expected
    ):
        raise TC007AllocationError("Candidate orders must be full permutations")

    records = _records(episodes)
    half = total_budget // 2
    relevance_records = [records[index] for index in relevance_order]
    initial = pack_stm_payload([], relevance_records, half)
    initial_ids = tuple(initial.selected_ids)
    admitted = set(initial_ids)

    spread_candidates = [
        records[index]
        for index in spread_order
        if str(records[index]["id"]) not in admitted
    ]
    spread_duplicates = tuple(
        str(records[index]["id"])
        for index in spread_order
        if str(records[index]["id"]) in admitted
    )
    spread = pack_stm_payload([], spread_candidates, half)
    spread_ids = tuple(spread.selected_ids)
    admitted.update(spread_ids)

    by_id = {str(record["id"]): record for record in records}
    initial_merged = [by_id[identifier] for identifier in (*initial_ids, *spread_ids)]
    merged_initial_payload = render_stm_payload([], initial_merged)
    if len(merged_initial_payload) > total_budget:
        raise TC007AllocationError("Solo-accounted initial phases exceeded total budget")

    returned: list[str] = []
    dropped_relevance: list[str] = []
    final_records = list(initial_merged)
    current_chars = len(merged_initial_payload)
    for index in relevance_order:
        identifier = str(records[index]["id"])
        if identifier in admitted:
            continue
        cost = additive_weight(records[index])
        if current_chars + cost <= total_budget:
            final_records.append(records[index])
            admitted.add(identifier)
            returned.append(identifier)
            current_chars += cost
        else:
            dropped_relevance.append(identifier)

    payload = render_stm_payload([], final_records)
    if len(payload) != current_chars or len(payload) > total_budget:
        raise TC007AllocationError("Exact merged accounting failed")
    selected = tuple(str(record["id"]) for record in final_records)
    if len(selected) != len(set(selected)):
        raise TC007AllocationError("A candidate serialized more than once")

    owner = {
        **{identifier: "relevance" for identifier in initial_ids},
        **{identifier: "spread" for identifier in spread_ids},
        **{identifier: "relevance" for identifier in returned},
    }
    phase = {
        **{identifier: "initial_relevance" for identifier in initial_ids},
        **{identifier: "protected_spread" for identifier in spread_ids},
        **{identifier: "returned_relevance" for identifier in returned},
    }
    return Allocation(
        payload=payload,
        selected_ids=selected,
        initial_relevance_ids=initial_ids,
        spread_ids=spread_ids,
        returned_relevance_ids=tuple(returned),
        skipped_spread_duplicates=spread_duplicates,
        dropped_relevance_ids=tuple(dropped_relevance),
        dropped_spread_ids=tuple(spread.skipped_k_ids),
        owner=owner,
        phase=phase,
        total_budget=total_budget,
        half_allowance=half,
        initial_relevance_solo_chars=len(initial.payload),
        spread_solo_chars=len(spread.payload),
        merged_initial_chars=len(merged_initial_payload),
        wrapper_savings=len(initial.payload) + len(spread.payload) - len(merged_initial_payload),
        returned_capacity=total_budget - len(merged_initial_payload),
    )


def full_relevance(
    episodes: Sequence[Any], relevance_order: Sequence[int], total_budget: int
) -> Allocation:
    """Binding control represented in the same attribution type."""

    if total_budget not in TOTAL_BUDGETS:
        raise TC007AllocationError(f"Unregistered budget: {total_budget}")
    records = [episodes[index].record for index in relevance_order]
    packed = pack_stm_payload([], records, total_budget)
    selected = tuple(packed.selected_ids)
    return Allocation(
        payload=packed.payload,
        selected_ids=selected,
        initial_relevance_ids=selected,
        spread_ids=(),
        returned_relevance_ids=(),
        skipped_spread_duplicates=(),
        dropped_relevance_ids=tuple(packed.skipped_k_ids),
        dropped_spread_ids=(),
        owner={identifier: "relevance" for identifier in selected},
        phase={identifier: "full_relevance" for identifier in selected},
        total_budget=total_budget,
        half_allowance=total_budget // 2,
        initial_relevance_solo_chars=len(packed.payload),
        spread_solo_chars=EMPTY_PAYLOAD_CHARS,
        merged_initial_chars=len(packed.payload),
        wrapper_savings=0,
        returned_capacity=total_budget - len(packed.payload),
    )


__all__ = [
    "A3_CLUSTER_COUNT",
    "A3_COST_EXPONENT",
    "A3_LAMBDA",
    "FACILITY_COST_EXPONENT",
    "SPREAD_ARMS",
    "TOTAL_BUDGETS",
    "Allocation",
    "SpreadPrepared",
    "TC007AllocationError",
    "allocate",
    "full_relevance",
    "orders",
    "prepare",
]

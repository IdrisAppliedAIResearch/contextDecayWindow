"""Study-private BEAM-001 parent-opportunity ASPECT selector.

This module ports the frozen TC-013 fan-out and TC-014 opportunity admission
without adding a public ``episodic-chat`` configuration surface. Recent
continuity is removed before allocation and composed additively afterwards.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.tc010_study import allocate_subset
from analysis.tc013_fanout import FanoutTrace, fanout_aspect
from episodic._aspect import prepare_facets
from episodic._config import EpisodicConfig
from episodic._packing import EMPTY_PAYLOAD_CHARS, pack_stm_payload
from episodic._ranking import CC80Ranking, rank_cc80
from episodic._render import render_stm_payload
from episodic._selection import additive_weight


class BeamParentOpportunityError(RuntimeError):
    pass


def deterministic_weighted_facet_overlap(
    candidate_facets: Sequence[frozenset[str]], idf: Mapping[str, float]
) -> tuple[np.ndarray, np.ndarray]:
    """Accumulate overlap once and derive exact self-overlap totals."""

    count = len(candidate_facets)
    overlap = np.zeros((count, count), dtype=np.float64)
    postings: dict[str, list[int]] = {}
    for index, facets in enumerate(candidate_facets):
        for facet in sorted(facets):
            weight = idf.get(facet)
            if weight is None or not np.isfinite(float(weight)) or float(weight) < 0.0:
                raise BeamParentOpportunityError(
                    "Missing, negative, or non-finite facet IDF"
                )
            postings.setdefault(facet, []).append(index)
    for facet in sorted(postings):
        indices = np.asarray(postings[facet], dtype=np.int64)
        overlap[np.ix_(indices, indices)] += float(idf[facet])
    totals = np.diag(overlap).copy()
    if not np.array_equal(np.diag(overlap), totals):
        raise BeamParentOpportunityError("Facet self-overlap identity drifted")
    if not np.isfinite(totals).all() or np.any(totals < 0.0):
        raise BeamParentOpportunityError("Facet totals escaped their valid range")
    return totals, overlap


@dataclass(frozen=True)
class EpisodeView:
    record: dict[str, Any]

    @property
    def identity(self) -> str:
        return str(self.record["id"])


@dataclass(frozen=True)
class OpportunityDecision:
    parent_index: int
    child_index: int
    raw_marginal: float
    ratio: float
    exact_additive_chars: int
    admitted: bool
    accepted: bool
    reason: str
    displaced_indices: tuple[int, ...]
    displaced_cc80_value: float


@dataclass(frozen=True)
class ParentOpportunityTrace:
    parents: tuple[int, ...]
    proposed_children: tuple[int, ...]
    parent_for_child: tuple[int, ...]
    retained_children: tuple[int, ...]
    decisions: tuple[OpportunityDecision, ...]
    no_positive_child: int
    no_fitting_child: int
    rejected_capacity: int
    rejected_value: int
    finite_attempts: int


@dataclass(frozen=True)
class ParentOpportunityResult:
    payload: str
    retrieval_payload: str
    selected_indices: tuple[int, ...]
    selected_ids: tuple[str, ...]
    recent_indices: tuple[int, ...]
    recent_ids: tuple[str, ...]
    semantic_parent_indices: tuple[int, ...]
    aspect_indices: tuple[int, ...]
    returned_semantic_indices: tuple[int, ...]
    dropped_indices: tuple[int, ...]
    ranking: CC80Ranking
    trace: ParentOpportunityTrace
    facet_families: Mapping[str, int]

    @property
    def payload_sha256(self) -> str:
        return hashlib.sha256(self.payload.encode("utf-8")).hexdigest()

    @property
    def retrieval_payload_sha256(self) -> str:
        return hashlib.sha256(self.retrieval_payload.encode("utf-8")).hexdigest()


def _unique_ids(episodes: Sequence[dict[str, Any]]) -> tuple[str, ...]:
    identifiers = tuple(str(episode["id"]) for episode in episodes)
    if len(identifiers) != len(set(identifiers)):
        raise BeamParentOpportunityError("Episode ids must be unique")
    return identifiers


def _full_cc80(
    episodes: Sequence[dict[str, Any]], eligible_order: Sequence[int], budget: int
) -> tuple[str, tuple[int, ...], tuple[int, ...]]:
    packed = pack_stm_payload([], [episodes[index] for index in eligible_order], budget)
    by_id = {str(episode["id"]): index for index, episode in enumerate(episodes)}
    selected = tuple(by_id[identifier] for identifier in packed.selected_ids)
    selected_set = set(selected)
    dropped = tuple(index for index in eligible_order if index not in selected_set)
    return packed.payload, selected, dropped


def _admit_opportunities(
    episodes: Sequence[EpisodeView],
    relevance_order: Sequence[int],
    fanout: FanoutTrace,
    scores: np.ndarray,
    facet_weight: np.ndarray,
    budget: int,
) -> tuple[Any, ParentOpportunityTrace]:
    kept: list[int] = []
    decisions: list[OpportunityDecision] = []
    rejected_capacity = 0
    rejected_value = 0
    current = allocate_subset(episodes, relevance_order, (), budget)

    for position, child in enumerate(fanout.proposed):
        with_child = allocate_subset(
            episodes, relevance_order, tuple((*kept, child)), budget
        )
        admitted = episodes[child].identity in with_child.spread_ids
        displaced_indices: tuple[int, ...] = ()
        displaced_value = 0.0
        accepted = False
        if not admitted:
            reason = "rejected_capacity"
            rejected_capacity += 1
        else:
            by_id = {episode.identity: index for index, episode in enumerate(episodes)}
            lost_ids = set(current.selected_ids) - set(with_child.selected_ids)
            displaced_indices = tuple(
                index
                for index in relevance_order
                if episodes[index].identity in lost_ids
            )
            displaced_value = sum(
                float(scores[by_id[identifier]] * facet_weight[by_id[identifier]])
                for identifier in lost_ids
            )
            accepted = float(fanout.marginal[position]) + 1e-12 >= displaced_value
            if accepted:
                reason = "accepted"
                kept.append(child)
                current = with_child
            else:
                reason = "rejected_value"
                rejected_value += 1
        decisions.append(
            OpportunityDecision(
                parent_index=fanout.parent_for_child[position],
                child_index=child,
                raw_marginal=float(fanout.marginal[position]),
                ratio=float(fanout.ratio[position]),
                exact_additive_chars=additive_weight(episodes[child].record),
                admitted=admitted,
                accepted=accepted,
                reason=reason,
                displaced_indices=displaced_indices,
                displaced_cc80_value=float(displaced_value),
            )
        )

    if len(fanout.proposed) + fanout.no_positive_child + fanout.no_fitting_child != len(
        fanout.parents
    ):
        raise BeamParentOpportunityError("Parent fan-out did not terminate once per parent")
    trace = ParentOpportunityTrace(
        parents=fanout.parents,
        proposed_children=fanout.proposed,
        parent_for_child=fanout.parent_for_child,
        retained_children=tuple(kept),
        decisions=tuple(decisions),
        no_positive_child=fanout.no_positive_child,
        no_fitting_child=fanout.no_fitting_child,
        rejected_capacity=rejected_capacity,
        rejected_value=rejected_value,
        finite_attempts=len(fanout.parents),
    )
    return current, trace


def select_parent_opportunity(
    *,
    episodes: Sequence[dict[str, Any]],
    ranking: CC80Ranking,
    excluded_ids: Sequence[str],
    facets: Sequence[frozenset[str]],
    idf: Mapping[str, float],
    facet_families: Mapping[str, int],
    budget: int = 32_000,
) -> ParentOpportunityResult:
    """Apply T1 to an already ranked store and compose additive recency."""

    if budget != 32_000:
        raise BeamParentOpportunityError("BEAM-001 T1 is frozen to 32,000 chars")
    identifiers = _unique_ids(episodes)
    if sorted(ranking.order) != list(range(len(episodes))):
        raise BeamParentOpportunityError("CC80 order must permute the full store")
    if len(ranking.scores) != len(episodes) or len(facets) != len(episodes):
        raise BeamParentOpportunityError("Ranking/facet shape drift")
    excluded = set(map(str, excluded_ids))
    if not excluded.issubset(identifiers):
        raise BeamParentOpportunityError("Excluded ids escaped the store")

    recent_indices = tuple(
        index for index, identifier in enumerate(identifiers) if identifier in excluded
    )
    eligible_source_indices = tuple(
        index for index, identifier in enumerate(identifiers) if identifier not in excluded
    )
    full_to_local = {
        full_index: local_index
        for local_index, full_index in enumerate(eligible_source_indices)
    }
    local_to_full = dict(enumerate(eligible_source_indices))
    eligible_order_full = tuple(
        index for index in ranking.order if identifiers[index] not in excluded
    )
    eligible_order = tuple(full_to_local[index] for index in eligible_order_full)

    if not eligible_order:
        recent = [episodes[index] for index in recent_indices]
        payload = render_stm_payload(recent, [])
        empty_trace = ParentOpportunityTrace((), (), (), (), (), 0, 0, 0, 0, 0)
        return ParentOpportunityResult(
            payload=payload,
            retrieval_payload="",
            selected_indices=(),
            selected_ids=(),
            recent_indices=recent_indices,
            recent_ids=tuple(identifiers[index] for index in recent_indices),
            semantic_parent_indices=(),
            aspect_indices=(),
            returned_semantic_indices=(),
            dropped_indices=(),
            ranking=ranking,
            trace=empty_trace,
            facet_families=dict(facet_families),
        )

    local = tuple(EpisodeView(episodes[index]) for index in eligible_source_indices)
    local_scores = np.asarray(
        [ranking.scores[index] for index in eligible_source_indices], dtype=np.float64
    )
    local_facets = tuple(facets[index] for index in eligible_source_indices)
    facet_weight, facet_overlap = deterministic_weighted_facet_overlap(
        local_facets, idf
    )
    half = budget // 2
    initial = pack_stm_payload(
        [], [local[index].record for index in eligible_order], half
    )
    if not initial.selected_ids:
        retrieval_payload, selected_full, dropped_full = _full_cc80(
            episodes, eligible_order_full, budget
        )
        recent = [episodes[index] for index in recent_indices]
        long_term = [episodes[index] for index in selected_full]
        payload = render_stm_payload(recent, long_term)
        empty_trace = ParentOpportunityTrace((), (), (), (), (), 0, 0, 0, 0, 0)
        return ParentOpportunityResult(
            payload=payload,
            retrieval_payload=retrieval_payload,
            selected_indices=selected_full,
            selected_ids=tuple(identifiers[index] for index in selected_full),
            recent_indices=recent_indices,
            recent_ids=tuple(identifiers[index] for index in recent_indices),
            semantic_parent_indices=selected_full,
            aspect_indices=(),
            returned_semantic_indices=(),
            dropped_indices=dropped_full,
            ranking=ranking,
            trace=empty_trace,
            facet_families=dict(facet_families),
        )

    local_by_id = {episode.identity: index for index, episode in enumerate(local)}
    parents = tuple(local_by_id[identifier] for identifier in initial.selected_ids)
    fanout = fanout_aspect(
        local,
        facet_weight,
        facet_overlap,
        local_scores,
        eligible_order,
        parents,
        half,
    )
    allocation, local_trace = _admit_opportunities(
        local,
        eligible_order,
        fanout,
        local_scores,
        facet_weight,
        budget,
    )

    def full(indices: Sequence[int]) -> tuple[int, ...]:
        return tuple(local_to_full[index] for index in indices)

    decisions = tuple(
        OpportunityDecision(
            **{
                **asdict(decision),
                "parent_index": local_to_full[decision.parent_index],
                "child_index": local_to_full[decision.child_index],
                "displaced_indices": full(decision.displaced_indices),
            }
        )
        for decision in local_trace.decisions
    )
    trace = ParentOpportunityTrace(
        parents=full(local_trace.parents),
        proposed_children=full(local_trace.proposed_children),
        parent_for_child=full(local_trace.parent_for_child),
        retained_children=full(local_trace.retained_children),
        decisions=decisions,
        no_positive_child=local_trace.no_positive_child,
        no_fitting_child=local_trace.no_fitting_child,
        rejected_capacity=local_trace.rejected_capacity,
        rejected_value=local_trace.rejected_value,
        finite_attempts=local_trace.finite_attempts,
    )
    selected_local = tuple(local_by_id[identifier] for identifier in allocation.selected_ids)
    selected_full = full(selected_local)
    selected_set = set(selected_local)
    dropped_full = full(
        tuple(index for index in eligible_order if index not in selected_set)
    )
    parent_full = full(
        tuple(local_by_id[identifier] for identifier in allocation.initial_relevance_ids)
    )
    aspect_full = full(
        tuple(local_by_id[identifier] for identifier in allocation.spread_ids)
    )
    returned_full = full(
        tuple(local_by_id[identifier] for identifier in allocation.returned_relevance_ids)
    )
    recent = [episodes[index] for index in recent_indices]
    long_term = [episodes[index] for index in selected_full]
    payload = render_stm_payload(recent, long_term)
    delivered = (*recent_indices, *selected_full)
    if len(delivered) != len(set(delivered)):
        raise BeamParentOpportunityError("Recent and long-term identities overlapped")
    if len(allocation.payload) > budget:
        raise BeamParentOpportunityError("T1 exceeded its long-term budget")
    return ParentOpportunityResult(
        payload=payload,
        retrieval_payload=allocation.payload,
        selected_indices=selected_full,
        selected_ids=tuple(identifiers[index] for index in selected_full),
        recent_indices=recent_indices,
        recent_ids=tuple(identifiers[index] for index in recent_indices),
        semantic_parent_indices=parent_full,
        aspect_indices=aspect_full,
        returned_semantic_indices=returned_full,
        dropped_indices=dropped_full,
        ranking=ranking,
        trace=trace,
        facet_families=dict(facet_families),
    )


def build_parent_opportunity_context(
    *,
    episodes: Sequence[dict[str, Any]],
    query_text: str,
    query_embedding: object,
    config: EpisodicConfig | None = None,
    facet_bundle: tuple[
        Sequence[frozenset[str]], Mapping[str, float], Mapping[str, int]
    ]
    | None = None,
) -> ParentOpportunityResult:
    """Rank the full store and construct the frozen BEAM-001 T1 context."""

    frozen = config if config is not None else EpisodicConfig()
    if frozen.aspect_share != 0.5 or frozen.retrieval_budget_chars != 32_000:
        raise BeamParentOpportunityError("Common BEAM-001 parameters drifted")
    ranking = rank_cc80(
        episodes,
        query_text,
        query_embedding,
        dense_weight=frozen.semantic_dense_weight,
        bm25_k1=frozen.bm25_k1,
        bm25_b=frozen.bm25_b,
    )
    recent_count = min(frozen.recency_window_n, len(episodes))
    recent_ids = tuple(str(episode["id"]) for episode in episodes[-recent_count:])
    facets, idf, families = (
        facet_bundle
        if facet_bundle is not None
        else prepare_facets(episodes, frozen.aspect_model)
    )
    return select_parent_opportunity(
        episodes=episodes,
        ranking=ranking,
        excluded_ids=recent_ids,
        facets=facets,
        idf=idf,
        facet_families=families,
        budget=frozen.retrieval_budget_chars,
    )


__all__ = [
    "BeamParentOpportunityError",
    "EpisodeView",
    "OpportunityDecision",
    "ParentOpportunityResult",
    "ParentOpportunityTrace",
    "build_parent_opportunity_context",
    "deterministic_weighted_facet_overlap",
    "select_parent_opportunity",
]

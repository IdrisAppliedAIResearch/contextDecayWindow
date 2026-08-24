"""CC80 retrieval and optional protected static ASPECT allocation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ._aspect import AspectTrace, aspect_spread, prepare_facets
from ._config import EpisodicConfig
from ._errors import EpisodicError
from ._packing import EMPTY_PAYLOAD_CHARS, pack_stm_payload
from ._ranking import CC80Ranking, rank_cc80
from ._render import render_stm_payload
from ._selection import additive_weight


@dataclass(frozen=True)
class RetrievalAllocation:
    payload: str
    selected_ids: tuple[str, ...]
    selected_indices: tuple[int, ...]
    initial_semantic_ids: tuple[str, ...]
    aspect_ids: tuple[str, ...]
    returned_semantic_ids: tuple[str, ...]
    dropped_ids: tuple[str, ...]
    chars_wanted: int
    ranking: CC80Ranking
    aspect_trace: AspectTrace | None


def _ids(episodes: Sequence[dict]) -> tuple[str, ...]:
    identifiers = tuple(str(episode["id"]) for episode in episodes)
    if len(identifiers) != len(set(identifiers)):
        raise EpisodicError("Episode ids must be unique for retrieval and deduplication")
    return identifiers


def _wanted_chars(records: Sequence[dict]) -> int:
    if not records:
        return EMPTY_PAYLOAD_CHARS
    return len(render_stm_payload([], records))


def _full_cc80(
    episodes: Sequence[dict],
    ranking: CC80Ranking,
    eligible_order: Sequence[int],
    budget: int,
) -> RetrievalAllocation:
    records = [episodes[index] for index in eligible_order]
    packed = pack_stm_payload([], records, budget)
    by_id = {str(episode["id"]): index for index, episode in enumerate(episodes)}
    selected = tuple(packed.selected_ids)
    selected_set = set(selected)
    return RetrievalAllocation(
        payload=packed.payload,
        selected_ids=selected,
        selected_indices=tuple(by_id[identifier] for identifier in selected),
        initial_semantic_ids=selected,
        aspect_ids=(),
        returned_semantic_ids=(),
        dropped_ids=tuple(
            str(episodes[index]["id"])
            for index in eligible_order
            if str(episodes[index]["id"]) not in selected_set
        ),
        chars_wanted=_wanted_chars(records),
        ranking=ranking,
        aspect_trace=None,
    )


def _protected_aspect(
    episodes: Sequence[dict],
    ranking: CC80Ranking,
    eligible_order: Sequence[int],
    excluded_indices: Sequence[int],
    budget: int,
    config: EpisodicConfig,
    *,
    facet_bundle: tuple[
        Sequence[frozenset[str]], dict[str, float], dict[str, int]
    ]
    | None = None,
) -> RetrievalAllocation:
    half = int(budget * config.aspect_share)
    initial = pack_stm_payload(
        [], [episodes[index] for index in eligible_order], half
    )
    if not initial.selected_ids:
        return _full_cc80(episodes, ranking, eligible_order, budget)

    by_id = {str(episode["id"]): index for index, episode in enumerate(episodes)}
    initial_ids = tuple(initial.selected_ids)
    initial_indices = tuple(by_id[identifier] for identifier in initial_ids)
    facets, idf, _families = (
        facet_bundle
        if facet_bundle is not None
        else prepare_facets(episodes, config.aspect_model)
    )
    trace = aspect_spread(
        episodes,
        facets,
        idf,
        ranking.scores,
        ranking.order,
        initial_indices,
        half,
        excluded=excluded_indices,
    )

    admitted = set(initial_ids)
    spread_candidates = [
        episodes[index]
        for index in trace.order
        if str(episodes[index]["id"]) not in admitted
    ]
    spread = pack_stm_payload([], spread_candidates, half)
    aspect_ids = tuple(spread.selected_ids)
    admitted.update(aspect_ids)

    final_records = [
        episodes[by_id[identifier]] for identifier in (*initial_ids, *aspect_ids)
    ]
    current_chars = len(render_stm_payload([], final_records))
    returned: list[str] = []
    for index in eligible_order:
        identifier = str(episodes[index]["id"])
        if identifier in admitted:
            continue
        cost = additive_weight(episodes[index])
        if current_chars + cost <= budget:
            final_records.append(episodes[index])
            admitted.add(identifier)
            returned.append(identifier)
            current_chars += cost

    payload = render_stm_payload([], final_records) if budget >= EMPTY_PAYLOAD_CHARS else ""
    if len(payload) != current_chars or len(payload) > budget:
        raise AssertionError("Protected ASPECT exact allocation drifted")
    selected = tuple(str(record["id"]) for record in final_records)
    if len(selected) != len(set(selected)):
        raise AssertionError("Protected ASPECT serialized a duplicate episode")
    selected_set = set(selected)
    eligible_records = [episodes[index] for index in eligible_order]
    return RetrievalAllocation(
        payload=payload,
        selected_ids=selected,
        selected_indices=tuple(by_id[identifier] for identifier in selected),
        initial_semantic_ids=initial_ids,
        aspect_ids=aspect_ids,
        returned_semantic_ids=tuple(returned),
        dropped_ids=tuple(
            str(episodes[index]["id"])
            for index in eligible_order
            if str(episodes[index]["id"]) not in selected_set
        ),
        chars_wanted=_wanted_chars(eligible_records),
        ranking=ranking,
        aspect_trace=trace,
    )


def retrieve_long_term(
    *,
    episodes: Sequence[dict],
    query_text: str,
    query_embedding: object,
    budget: int,
    config: EpisodicConfig,
    excluded_ids: Sequence[str] = (),
) -> RetrievalAllocation:
    """Retrieve a budgeted long-term block, independently of additive recency."""

    if not isinstance(budget, int):
        raise EpisodicError("retrieval budget must be an integer character count")
    identifiers = _ids(episodes)
    excluded = set(str(identifier) for identifier in excluded_ids)
    unknown = excluded - set(identifiers)
    if unknown:
        raise EpisodicError(f"Excluded episode ids are not in the store: {sorted(unknown)}")
    ranking = rank_cc80(
        episodes,
        query_text,
        query_embedding,
        dense_weight=config.semantic_dense_weight,
        bm25_k1=config.bm25_k1,
        bm25_b=config.bm25_b,
    )
    eligible_order = tuple(
        index for index in ranking.order if identifiers[index] not in excluded
    )
    excluded_indices = tuple(
        index for index, identifier in enumerate(identifiers) if identifier in excluded
    )
    effective_budget = max(budget, 0)
    if not config.aspect_enabled or not eligible_order:
        return _full_cc80(episodes, ranking, eligible_order, effective_budget)
    return _protected_aspect(
        episodes,
        ranking,
        eligible_order,
        excluded_indices,
        effective_budget,
        config,
    )


__all__ = ["RetrievalAllocation", "retrieve_long_term"]

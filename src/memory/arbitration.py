"""Arbitration for STM and LTM candidates.

Study 004 established tier-neutral count-ranking: merge both tiers, sort by
similarity, cap at `k_stm + ltm_top_m`. That design assumed both tiers emit
comparable units.

Study 007 replaces it with **tier-budgeted assembly** for the LTM tier, a named
departure recorded in `decisions/DECISION_retrieval_budget_study007.md`. The
assumption stopped holding in Study 006, when LTM began emitting sentence spans
while STM continued emitting whole episodes. STM's path is unchanged.
"""

from dataclasses import dataclass, field

from src.memory.retrieval_budget import (
    FLOOR_SIMILARITY,
    RENDER_EPISODE,
    RENDER_SPAN,
    BudgetSelection,
    episode_key,
    selection_key,
    select_within_budget,
)


@dataclass
class ArbitrationResult:
    episodes: list[dict] = field(default_factory=list)
    stm_candidates: int = 0
    ltm_candidates: int = 0
    duplicates_removed: int = 0
    final_set_size: int = 0
    ltm_episodes_in_final_set: int = 0
    provenance_list: list[str] = field(default_factory=list)
    # Study 007 budget accounting; unset under the carried count-based policy.
    budget: BudgetSelection | None = None
    containment_drops: int = 0
    refills: int = 0


def arbitrate_budgeted(
    stm_candidates: list[dict],
    ltm_candidates: list[dict],
    stm_block_episode_ids: set[str],
    ltm_budget: int,
    ltm_k_min: int,
    floor_ranking: str = FLOOR_SIMILARITY,
    fill_cap: int | None = None,
    render_mode: str = RENDER_EPISODE,
) -> ArbitrationResult:
    """Study 007 tier-budgeted assembly.

    Order is constrained, not incidental:

    1. **Containment dedup first.** An LTM record whose source episode is
       already in the STM block would render as an exact duplicate of text the
       model already has. Excluding those episodes up front means the budget is
       never spent on them, so "refill" is structural rather than a repair pass:
       the same phase rules run once over the eligible pool, and a floor
       selection displaced by containment is replaced from its own topic
       automatically.
    2. **Identifier dedup, inside the budget.** `select_within_budget` collapses
       records by source episode before charging, because many records render as
       one element.
    3. **Floor protection.** Floor selections are chosen inside the budget and
       nothing downstream re-ranks or caps the LTM tier, so no path can evict
       one. The assertion below states that as an invariant rather than trusting
       it.

    STM is untouched: it contributes exactly the candidates it was given.
    """
    if render_mode == RENDER_SPAN:
        missing = [
            candidate.get("distilled_id")
            for candidate in ltm_candidates
            if candidate.get("span_text") is None
            or candidate.get("span_start") is None
            or candidate.get("span_end") is None
            or not candidate.get("role")
        ]
        if missing:
            raise ValueError(
                "Span rendering requires text, role, and recorded offsets "
                f"for every candidate; invalid records: {missing[:5]}"
            )

    dropped = [
        candidate
        for candidate in ltm_candidates
        if episode_key(candidate) in stm_block_episode_ids
    ]
    containment_episodes = {episode_key(candidate) for candidate in dropped}

    selection = select_within_budget(
        ltm_candidates,
        budget=ltm_budget,
        k_min=ltm_k_min,
        excluded_episode_ids=stm_block_episode_ids,
        floor_ranking=floor_ranking,
        fill_cap=fill_cap,
        render_mode=render_mode,
    )

    # What the containment drop bought: selections admitted that a budget spent
    # on duplicated STM text could not have afforded.
    unconstrained = select_within_budget(
        ltm_candidates,
        budget=ltm_budget,
        k_min=ltm_k_min,
        floor_ranking=floor_ranking,
        fill_cap=fill_cap,
        render_mode=render_mode,
    )
    refills = max(0, len(selection.selected) - len(unconstrained.selected))

    merged: dict[str, dict] = {}
    provenance: dict[str, set[str]] = {}
    for candidate in stm_candidates:
        key = f"episode:{episode_key(candidate)}"
        merged.setdefault(key, dict(candidate))
        provenance.setdefault(key, set()).add("stm")
    for candidate in selection.selected:
        unit_key = selection_key(candidate, render_mode)
        key = (
            f"episode:{unit_key}"
            if render_mode == RENDER_EPISODE
            else f"span:{unit_key}"
        )
        existing = merged.get(key)
        # LTM carries the provenance metadata the tagged renderer needs.
        ltm_candidate = {**candidate, "render_mode": render_mode}
        merged[key] = (
            {**existing, **ltm_candidate}
            if existing
            else ltm_candidate
        )
        provenance.setdefault(key, set()).add("ltm")

    final = []
    for key, candidate in merged.items():
        sources = provenance[key]
        candidate["provenance"] = (
            "both" if sources == {"stm", "ltm"} else next(iter(sources))
        )
        final.append(candidate)
    final.sort(
        key=lambda item: (
            -float(item["similarity"]),
            selection_key(item, item.get("render_mode", RENDER_EPISODE)),
        )
    )

    final_ids = [
        selection_key(episode, episode.get("render_mode", RENDER_EPISODE))
        for episode in final
    ]
    assert len(final_ids) == len(set(final_ids)), (
        "Arbitration emitted a duplicate episode_id"
    )
    surviving = {str(i) for i in final_ids}
    evicted_floor = selection.floor_ids - surviving
    assert not evicted_floor, (
        f"Floor selections were evicted from the final set: {sorted(evicted_floor)}"
    )
    assert not any(
        episode_key(candidate) in containment_episodes
        for candidate in selection.selected
    ), (
        "A containment-dropped episode was admitted as a floor selection"
    )

    return ArbitrationResult(
        episodes=final,
        stm_candidates=len(stm_candidates),
        ltm_candidates=len(ltm_candidates),
        duplicates_removed=(
            len(stm_candidates) + len(selection.selected) - len(merged)
        ),
        final_set_size=len(final),
        ltm_episodes_in_final_set=sum(
            episode["provenance"] in {"ltm", "both"} for episode in final
        ),
        provenance_list=[episode["provenance"] for episode in final],
        budget=selection,
        containment_drops=len(containment_episodes),
        refills=refills,
    )


def arbitrate_candidates(
    stm_candidates: list[dict],
    ltm_candidates: list[dict],
    k_stm: int,
    ltm_top_m: int = 5,
    context_candidate_cap: int | None = None,
) -> ArbitrationResult:
    """Deduplicate before tier-neutral ranking and cap the final union.

    Study 004's policy, carried unchanged. Used by Studies 003-006 and by the
    Study 007 control arm.
    """
    by_episode_id: dict[str, dict] = {}
    provenance: dict[str, set[str]] = {}

    for source, candidates in (("stm", stm_candidates), ("ltm", ltm_candidates)):
        for candidate in candidates:
            episode_id = candidate["id"]
            provenance.setdefault(episode_id, set()).add(source)
            existing = by_episode_id.get(episode_id)
            if existing is None:
                by_episode_id[episode_id] = dict(candidate)
            elif source == "ltm":
                # LTM carries promotion metadata required by the tagged renderer.
                by_episode_id[episode_id] = {**existing, **candidate}

    duplicates_removed = len(stm_candidates) + len(ltm_candidates) - len(by_episode_id)
    merged = []
    for episode_id, candidate in by_episode_id.items():
        sources = provenance[episode_id]
        if sources == {"stm", "ltm"}:
            candidate["provenance"] = "both"
        else:
            candidate["provenance"] = next(iter(sources))
        merged.append(candidate)

    # The episode id is the tie-breaker so equal similarities receive no tier bias.
    merged.sort(key=lambda item: (-float(item["similarity"]), str(item["id"])))
    registered_cap = k_stm + ltm_top_m
    final_cap = (
        min(registered_cap, context_candidate_cap)
        if context_candidate_cap is not None
        else registered_cap
    )
    final = merged[:max(0, final_cap)]

    final_ids = [episode["id"] for episode in final]
    assert len(final_ids) == len(set(final_ids)), (
        "Arbitration emitted a duplicate episode_id"
    )

    provenance_list = [episode["provenance"] for episode in final]
    return ArbitrationResult(
        episodes=final,
        stm_candidates=len(stm_candidates),
        ltm_candidates=len(ltm_candidates),
        duplicates_removed=duplicates_removed,
        final_set_size=len(final),
        ltm_episodes_in_final_set=sum(
            episode["provenance"] in {"ltm", "both"} for episode in final
        ),
        provenance_list=provenance_list,
    )

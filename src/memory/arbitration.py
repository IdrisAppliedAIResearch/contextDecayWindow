"""Tier-agnostic arbitration for Study 004 STM and LTM candidates."""

from dataclasses import dataclass, field


@dataclass
class ArbitrationResult:
    episodes: list[dict] = field(default_factory=list)
    stm_candidates: int = 0
    ltm_candidates: int = 0
    duplicates_removed: int = 0
    final_set_size: int = 0
    ltm_episodes_in_final_set: int = 0
    provenance_list: list[str] = field(default_factory=list)


def arbitrate_candidates(
    stm_candidates: list[dict],
    ltm_candidates: list[dict],
    k_stm: int,
    ltm_top_m: int = 5,
    context_candidate_cap: int | None = None,
) -> ArbitrationResult:
    """Deduplicate before tier-neutral ranking and cap the final union."""
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

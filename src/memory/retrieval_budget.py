"""Study 007 — information-expressed, diversity-floored LTM retrieval.

Study 006 fixed formation and lost breadth. Its store held all four domains'
planted facts; at the breadth probe two domains reached the model. Retrieval
selected the top 5 LTM records by cosine similarity, and at span granularity
the top 5 cluster in whichever topic the query's wording most resembles.

Coarse granularity had been supplying per-domain coverage accidentally: when a
record was a whole turn, the top 5 records were 5 different turns spread across
topics. Study 006 removed the accident without replacing it. This module is the
explicit replacement.

Two changes, and nothing else:

  1. The block is filled to a **character budget**, not a record count, so
     record granularity no longer silently determines how much memory the model
     receives.
  2. Each topic present in distilled LTM is guaranteed a **floor** of `k_min`
     selections before the remaining budget is filled by pure global
     similarity. Coverage becomes structural; relevance still gets the majority
     of the budget.

Two subtleties, both established by measurement before this module was written
(`experiments/study_007/amendments/AMENDMENT_001_delivered_information.md`):

  * **Cost is rendered cost, not stored cost.** The read path renders a
    distilled record's whole source episode, not its selected span — mean 3,940
    characters against a 146-character span. Charging the budget at span size
    would constrain a quantity the model never sees, which is the same class of
    error this module exists to fix, one interface further down.

  * **Many records resolve to one episode.** Study 006's 200 records resolve to
    69 distinct source episodes. Records are therefore collapsed by episode
    *before* the budget is charged, and a record whose episode is already
    admitted is free.
"""

from dataclasses import dataclass, field


DEFAULT_B_LTM = 16000
DEFAULT_K_MIN = 3

PHASE_FLOOR = "floor"
PHASE_FILL = "fill"

FLOOR_SIMILARITY = "similarity"
FLOOR_DENSITY = "density"
FLOOR_RANKINGS = {FLOOR_SIMILARITY, FLOOR_DENSITY}

RENDER_EPISODE = "episode"
RENDER_SPAN = "span"
RENDER_MODES = {RENDER_EPISODE, RENDER_SPAN}


def selection_key(
    candidate: dict,
    render_mode: str = RENDER_EPISODE,
) -> str:
    """Identity of one independently rendered LTM unit."""
    if render_mode == RENDER_SPAN:
        distilled_id = candidate.get("distilled_id")
        if not distilled_id:
            raise ValueError("Span rendering requires a distilled_id")
        return str(distilled_id)
    return episode_key(candidate)


def rendered_text(
    candidate: dict,
    render_mode: str = RENDER_EPISODE,
) -> str:
    if render_mode == RENDER_SPAN:
        text = candidate.get("span_text")
        if text is None:
            raise ValueError("Span rendering requires span_text")
        return str(text)
    return (
        f"{candidate.get('user_message') or ''}"
        f"{candidate.get('assistant_message') or ''}"
    )


def rendered_cost(
    candidate: dict,
    render_mode: str = RENDER_EPISODE,
) -> int:
    """Exact serialized characters in this candidate's LTM element."""
    if render_mode == RENDER_SPAN:
        # Amendment 001: provenance scaffolding scales with the number of span
        # units and is part of what the model receives. Use the production
        # serializer as the authority so selection and rendering cannot drift.
        from src.memory.context_builder import render_ltm_span_element

        return len(
            render_ltm_span_element(
                {**candidate, "render_mode": RENDER_SPAN}
            )
        )
    from src.memory.context_builder import render_episode_element

    return len(render_episode_element(candidate))


def rendered_block_cost(
    candidates: list[dict],
    render_mode: str = RENDER_EPISODE,
) -> int:
    """Exact serialized length of the complete production LTM block."""
    from src.memory.context_builder import render_ltm_block

    return len(
        render_ltm_block(
            [
                {**candidate, "render_mode": render_mode}
                for candidate in candidates
            ]
        )
    )


def episode_key(candidate: dict) -> str:
    """The identity the renderer and arbitration collapse on."""
    return str(candidate["id"])


def topic_key(candidate: dict) -> str:
    """Canonical topic for floor accounting.

    `topic_id` is already resolved through the consolidation mapping by the
    retrieval query's COALESCE over the episodes table, so two labels that
    consolidated into one topic share one floor. `topic_label` is a display
    string and is not used for grouping.
    """
    return str(candidate.get("topic_id") or candidate.get("topic_label") or "")


@dataclass
class BudgetSelection:
    """One turn's LTM selection, with the accounting that makes it checkable."""

    selected: list[dict] = field(default_factory=list)
    phases: dict[str, str] = field(default_factory=dict)
    chars_used: int = 0
    budget: int = DEFAULT_B_LTM
    k_min: int = DEFAULT_K_MIN
    floor_ranking: str = FLOOR_SIMILARITY
    fill_cap: int | None = None
    render_mode: str = RENDER_EPISODE
    topics_present: list[str] = field(default_factory=list)
    floor_per_topic: dict[str, int] = field(default_factory=dict)
    fill_selected: int = 0
    fill_per_topic: dict[str, int] = field(default_factory=dict)
    cap_skips: int = 0
    chars_per_topic: dict[str, int] = field(default_factory=dict)
    collapsed_to_episode: int = 0
    skipped_oversized: int = 0
    block_overhead_chars: int = 0

    @property
    def utilization(self) -> float:
        return self.chars_used / self.budget if self.budget else 0.0

    @property
    def floor_ids(self) -> set[str]:
        return {
            episode_id
            for episode_id, phase in self.phases.items()
            if phase == PHASE_FLOOR
        }


def _rank_key(
    candidate: dict,
    render_mode: str = RENDER_EPISODE,
) -> tuple:
    """Similarity descending, episode id ascending as a deterministic tie-break."""
    return (
        -float(candidate["similarity"]),
        selection_key(candidate, render_mode),
    )


def _floor_rank_key(
    candidate: dict,
    floor_ranking: str,
    render_mode: str,
) -> tuple:
    if floor_ranking == FLOOR_DENSITY:
        return (
            -float(candidate.get("rendered_density") or 0.0),
            -float(candidate["similarity"]),
            selection_key(candidate, render_mode),
        )
    return _rank_key(candidate, render_mode)


def collapse_by_rendered_unit(
    candidates: list[dict],
    render_mode: str = RENDER_EPISODE,
) -> tuple[list[dict], int]:
    """Keep the highest-similarity record per independently rendered unit.

    Distinct spans sharing a source episode render as one element, so they must
    become one budget item under episode rendering. Under span rendering each
    distilled record is independently selectable.
    """
    best: dict[str, dict] = {}
    collapsed = 0
    for candidate in sorted(
        candidates,
        key=lambda item: _rank_key(item, render_mode),
    ):
        key = selection_key(candidate, render_mode)
        if key in best:
            collapsed += 1
            continue
        best[key] = candidate
    return (
        sorted(best.values(), key=lambda item: _rank_key(item, render_mode)),
        collapsed,
    )


def collapse_by_episode(candidates: list[dict]) -> tuple[list[dict], int]:
    """Compatibility wrapper for Study 007 episode rendering."""
    return collapse_by_rendered_unit(candidates, RENDER_EPISODE)


def select_within_budget(
    candidates: list[dict],
    budget: int = DEFAULT_B_LTM,
    k_min: int = DEFAULT_K_MIN,
    excluded_episode_ids: set[str] | None = None,
    floor_ranking: str = FLOOR_SIMILARITY,
    fill_cap: int | None = None,
    render_mode: str = RENDER_EPISODE,
) -> BudgetSelection:
    """Select LTM records under a character budget with a per-topic floor.

    `candidates` must be **every** scored LTM record, not a pre-truncated top-M.
    A floor computed over an already-truncated list could never reach a topic
    ranked below the cut, and would guarantee nothing while appearing to work.

    `excluded_episode_ids` are source episodes already present in the STM block;
    they are dropped before selection so containment dedup never spends budget
    it will have to refill.
    """
    empty_block_cost = rendered_block_cost([], render_mode)
    if budget < empty_block_cost:
        raise ValueError(
            "B_ltm cannot serialize an empty LTM block: "
            f"{budget} < {empty_block_cost}"
        )
    if k_min < 0:
        raise ValueError(f"k_min must be non-negative, got {k_min}")
    if floor_ranking not in FLOOR_RANKINGS:
        raise ValueError(f"Unsupported floor ranking: {floor_ranking}")
    if render_mode not in RENDER_MODES:
        raise ValueError(f"Unsupported rendering mode: {render_mode}")
    if fill_cap is not None and fill_cap < 0:
        raise ValueError(f"c_fill must be non-negative, got {fill_cap}")

    excluded = excluded_episode_ids or set()
    eligible = [c for c in candidates if episode_key(c) not in excluded]
    pool, collapsed = collapse_by_rendered_unit(eligible, render_mode)

    selection = BudgetSelection(
        budget=budget,
        k_min=k_min,
        floor_ranking=floor_ranking,
        fill_cap=fill_cap,
        render_mode=render_mode,
    )
    selection.chars_used = empty_block_cost
    selection.block_overhead_chars = empty_block_cost
    selection.collapsed_to_episode = collapsed
    selection.topics_present = sorted({topic_key(c) for c in pool})

    # `pool` is already similarity-ordered, so inserting in order leaves each
    # bucket ranked and leaves `by_topic` keyed in order of each topic's best
    # candidate. That ordering is the round-robin's cross-topic order.
    #
    # The pre-registration specifies the within-topic order ("highest-similarity
    # first") but not the order topics are visited in. It only matters when the
    # budget binds mid-floor. Serving the most query-relevant topic first is the
    # defensible reading; the alternative, alphabetical by topic id, would let
    # an arbitrary naming detail decide which domain is dropped under pressure.
    by_topic: dict[str, list[dict]] = {}
    for candidate in pool:
        by_topic.setdefault(topic_key(candidate), []).append(candidate)
    for bucket in by_topic.values():
        bucket.sort(
            key=lambda item: _floor_rank_key(
                item,
                floor_ranking,
                render_mode,
            )
        )
    floor_order = list(by_topic)

    chosen: dict[str, dict] = {}

    def admit(candidate: dict, phase: str) -> bool:
        trial = [*chosen.values(), candidate]
        trial_cost = rendered_block_cost(trial, render_mode)
        if trial_cost > budget:
            return False
        key = selection_key(candidate, render_mode)
        chosen[key] = candidate
        selection.phases[key] = phase
        selection.chars_used = trial_cost
        topic = topic_key(candidate)
        selection.chars_per_topic[topic] = (
            selection.chars_per_topic.get(topic, 0)
            + rendered_cost(candidate, render_mode)
        )
        return True

    # Phase 1 — floor. Round-robin across topics so a topic with long episodes
    # cannot starve the others by consuming the budget on its own first pick.
    # Within a topic, highest similarity first.
    for rank in range(k_min):
        for topic in floor_order:
            bucket = by_topic[topic]
            if rank >= len(bucket):
                continue
            candidate = bucket[rank]
            if admit(candidate, PHASE_FLOOR):
                selection.floor_per_topic[topic] = (
                    selection.floor_per_topic.get(topic, 0) + 1
                )

    # Phase 2 — fill. Pure global similarity, topic-agnostic, no per-topic cap:
    # a query genuinely about one domain should be free to spend most of the
    # remaining budget there. A candidate that does not fit is skipped rather
    # than terminating the loop, so a single oversized episode cannot strand
    # budget that smaller candidates could still use.
    for candidate in pool:
        key = selection_key(candidate, render_mode)
        if key in chosen:
            continue
        topic = topic_key(candidate)
        if (
            fill_cap is not None
            and selection.fill_per_topic.get(topic, 0) >= fill_cap
        ):
            selection.cap_skips += 1
            continue
        if admit(candidate, PHASE_FILL):
            selection.fill_selected += 1
            selection.fill_per_topic[topic] = (
                selection.fill_per_topic.get(topic, 0) + 1
            )
        else:
            selection.skipped_oversized += 1

    selection.selected = sorted(
        chosen.values(),
        key=lambda item: _rank_key(item, render_mode),
    )
    selection.chars_used = rendered_block_cost(
        selection.selected,
        render_mode,
    )
    selection.block_overhead_chars = (
        selection.chars_used
        - sum(
            rendered_cost(candidate, render_mode)
            for candidate in selection.selected
        )
    )
    assert selection.chars_used <= budget, (
        f"LTM budget exceeded: {selection.chars_used} > {budget}"
    )
    return selection


def select_top_m(candidates: list[dict], top_m: int = 5) -> BudgetSelection:
    """Study 006's count-based policy, for the replay harness fidelity check.

    Kept here rather than in the harness so the comparison runs against the same
    collapse-by-episode accounting and the difference is the policy alone.
    """
    pool, collapsed = collapse_by_episode(candidates)
    ranked = sorted(candidates, key=_rank_key)[:top_m]
    kept, _ = collapse_by_episode(ranked)

    selection = BudgetSelection(budget=0, k_min=0)
    selection.collapsed_to_episode = collapsed
    selection.topics_present = sorted({topic_key(c) for c in pool})
    selection.selected = kept
    selection.fill_selected = len(kept)
    for candidate in kept:
        key = episode_key(candidate)
        selection.phases[key] = PHASE_FILL
        cost = rendered_cost(candidate)
        topic = topic_key(candidate)
        selection.chars_per_topic[topic] = (
            selection.chars_per_topic.get(topic, 0) + cost
        )
    selection.chars_used = rendered_block_cost(selection.selected)
    selection.block_overhead_chars = (
        selection.chars_used - sum(selection.chars_per_topic.values())
    )
    selection.budget = selection.chars_used
    return selection

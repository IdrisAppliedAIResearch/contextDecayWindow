"""Study 007 S7_002 — character budgeting, per-domain floor, similarity fill."""

import random

import pytest

from src.memory.retrieval_budget import (
    PHASE_FILL,
    PHASE_FLOOR,
    BudgetSelection,
    collapse_by_episode,
    episode_key,
    rendered_block_cost,
    rendered_cost,
    select_top_m,
    select_within_budget,
    topic_key,
)


def candidate(
    episode_id: str,
    topic: str,
    similarity: float,
    chars: int = 100,
    user_chars: int | None = None,
) -> dict:
    """A scored LTM candidate shaped like `_score_ltm_rows` emits."""
    user = "u" * (user_chars if user_chars is not None else 0)
    return {
        "id": episode_id,
        "distilled_id": f"d-{episode_id}",
        "topic_id": topic,
        "topic_label": topic,
        "similarity": similarity,
        "user_message": user,
        "assistant_message": "a" * max(0, chars - len(user)),
        "turn_number": 1,
    }


# --------------------------------------------------------------------------
# S7-T-006 — character budgeting
# --------------------------------------------------------------------------


def test_budget_is_never_exceeded_across_randomized_lengths():
    rng = random.Random(5005)
    for trial in range(200):
        budget = rng.randint(rendered_block_cost([]), 4000)
        candidates = [
            candidate(
                f"e{i}",
                f"t{i % 4}",
                rng.random(),
                chars=rng.randint(1, 900),
            )
            for i in range(40)
        ]
        selection = select_within_budget(
            candidates, budget=budget, k_min=rng.randint(0, 4)
        )
        assert selection.chars_used <= budget, f"trial {trial}"
        assert selection.chars_used == rendered_block_cost(selection.selected)


def test_record_larger_than_whole_budget_is_skipped_not_deadlocked():
    candidates = [
        candidate("huge", "t0", 0.99, chars=5000),
        candidate("small", "t0", 0.10, chars=50),
    ]
    selection = select_within_budget(candidates, budget=1000, k_min=1)

    assert [c["id"] for c in selection.selected] == ["small"]
    assert selection.chars_used == rendered_block_cost([candidates[1]])
    assert selection.skipped_oversized >= 1


def test_oversized_candidate_does_not_strand_remaining_budget():
    """A candidate that does not fit must be skipped, not end the fill."""
    candidates = [
        candidate("a", "t0", 0.90, chars=100),
        candidate("toobig", "t0", 0.80, chars=5000),
        candidate("b", "t0", 0.70, chars=100),
        candidate("c", "t0", 0.60, chars=100),
    ]
    selection = select_within_budget(
        candidates,
        budget=rendered_block_cost([candidates[0], candidates[2], candidates[3]]),
        k_min=0,
    )

    assert sorted(c["id"] for c in selection.selected) == ["a", "b", "c"]


def test_budget_must_fit_the_empty_serialized_block():
    with pytest.raises(ValueError, match="cannot serialize an empty LTM block"):
        select_within_budget(
            [candidate("a", "t0", 0.9, chars=10)], budget=0, k_min=3
        )

    selection = select_within_budget(
        [candidate("a", "t0", 0.9, chars=10)],
        budget=rendered_block_cost([]),
        k_min=3,
    )
    assert selection.selected == []
    assert selection.chars_used == rendered_block_cost([])
    assert selection.utilization == 1.0


def test_utilization_reported():
    candidates = [candidate("a", "t0", 0.9, chars=250)]
    selection = select_within_budget(candidates, budget=1000, k_min=1)
    assert selection.chars_used == rendered_block_cost(candidates)
    assert selection.utilization == pytest.approx(
        rendered_block_cost(candidates) / 1000
    )


def test_negative_parameters_rejected():
    with pytest.raises(ValueError):
        select_within_budget([], budget=-1)
    with pytest.raises(ValueError):
        select_within_budget([], k_min=-1)


def test_rendered_cost_counts_both_message_fields():
    from src.memory.context_builder import render_episode_element

    populated = {"user_message": "abc", "assistant_message": "de"}
    assert rendered_cost(populated) == len(render_episode_element(populated))
    empty = {"user_message": None, "assistant_message": None}
    assert rendered_cost(empty) == len(render_episode_element(empty))
    assert rendered_cost({}) == len(render_episode_element({}))


# --------------------------------------------------------------------------
# S7-T-007 — Phase 1, per-domain floor
# --------------------------------------------------------------------------


def test_each_topic_receives_up_to_k_min():
    candidates = [
        candidate(f"{topic}-{i}", topic, 0.9 - i * 0.01, chars=100)
        for topic in ("civil", "art", "monetary", "marine")
        for i in range(10)
    ]
    selection = select_within_budget(candidates, budget=100_000, k_min=3)

    assert selection.floor_per_topic == {
        "civil": 3, "art": 3, "monetary": 3, "marine": 3
    }
    assert len(selection.floor_ids) == 12


def test_floor_reaches_a_topic_far_below_the_global_top_m():
    """The whole point of the floor, and Study 006's exact failure mode.

    Every civil span outranks every marine span. Under top-5 the block is all
    civil. The floor must reach marine anyway.
    """
    candidates = [
        candidate(f"civil-{i}", "civil", 0.90 - i * 0.001, chars=100)
        for i in range(50)
    ] + [
        candidate(f"marine-{i}", "marine", 0.30 - i * 0.001, chars=100)
        for i in range(50)
    ]

    top_m = select_top_m(candidates, top_m=5)
    assert {topic_key(c) for c in top_m.selected} == {"civil"}

    floored = select_within_budget(candidates, budget=100_000, k_min=3)
    assert {topic_key(c) for c in floored.selected} == {"civil", "marine"}
    assert floored.floor_per_topic["marine"] == 3


def test_sparse_topic_contributes_what_it_has():
    candidates = [
        candidate("civil-0", "civil", 0.9, chars=100),
        candidate("civil-1", "civil", 0.8, chars=100),
        candidate("civil-2", "civil", 0.7, chars=100),
        candidate("marine-0", "marine", 0.2, chars=100),
    ]
    selection = select_within_budget(candidates, budget=100_000, k_min=3)

    assert selection.floor_per_topic["marine"] == 1
    assert selection.floor_per_topic["civil"] == 3


def test_round_robin_prevents_starvation_by_a_long_episode():
    """Under tight budget, one topic's long first pick must not exclude others.

    Sequential (topic-at-a-time) admission would spend 900 of a 1,000 budget on
    civil's first episode and leave marine and art unrepresented.
    """
    candidates = [
        candidate("civil-0", "civil", 0.90, chars=400),
        candidate("civil-1", "civil", 0.89, chars=400),
        candidate("art-0", "art", 0.50, chars=300),
        candidate("marine-0", "marine", 0.20, chars=300),
    ]
    budget = rendered_block_cost(
        [candidates[0], candidates[2], candidates[3]]
    )
    selection = select_within_budget(
        candidates,
        budget=budget,
        k_min=2,
    )

    topics = {topic_key(c) for c in selection.selected}
    assert topics == {"civil", "art", "marine"}
    assert selection.chars_used == budget


def test_floor_visits_topics_by_query_relevance_under_pressure():
    """When the budget binds mid-floor, the most relevant topic is served first.

    Topic ids are chosen so alphabetical order is the reverse of similarity
    order: a visit order driven by naming would keep `aaa` and drop `zzz`.
    """
    candidates = [
        candidate("zzz-0", "zzz", 0.90, chars=400),
        candidate("mmm-0", "mmm", 0.50, chars=400),
        candidate("aaa-0", "aaa", 0.10, chars=400),
    ]
    selection = select_within_budget(
        candidates,
        budget=rendered_block_cost(candidates[:2]),
        k_min=1,
    )

    assert [c["id"] for c in selection.selected] == ["zzz-0", "mmm-0"]
    assert "aaa" not in selection.floor_per_topic


def test_topics_present_is_reported_independently_of_visit_order():
    candidates = [
        candidate("zzz-0", "zzz", 0.90),
        candidate("aaa-0", "aaa", 0.10),
    ]
    selection = select_within_budget(candidates, budget=100_000, k_min=1)
    assert selection.topics_present == ["aaa", "zzz"]


def test_canonical_mapping_shares_one_floor():
    """Two labels resolving to one topic_id must not each get their own floor."""
    candidates = [
        {**candidate(f"a{i}", "topic_2", 0.9 - i * 0.01), "topic_label": "civil"}
        for i in range(3)
    ] + [
        {
            **candidate(f"b{i}", "topic_2", 0.5 - i * 0.01),
            "topic_label": "bridges",
        }
        for i in range(3)
    ]
    selection = select_within_budget(candidates, budget=100_000, k_min=2)

    assert selection.topics_present == ["topic_2"]
    assert selection.floor_per_topic == {"topic_2": 2}


def test_k_min_zero_is_pure_similarity():
    candidates = [
        candidate("civil-0", "civil", 0.9, chars=100),
        candidate("marine-0", "marine", 0.1, chars=100),
    ]
    selection = select_within_budget(
        candidates,
        budget=rendered_block_cost(candidates[:1]),
        k_min=0,
    )

    assert [c["id"] for c in selection.selected] == ["civil-0"]
    assert selection.floor_per_topic == {}


def test_empty_ltm_is_handled():
    selection = select_within_budget([], budget=16000, k_min=3)
    assert selection.selected == []
    assert selection.topics_present == []
    assert selection.chars_used == rendered_block_cost([])


def test_single_topic_degenerate_case():
    """The state the 35-turn ablation reaches: exactly one topic in LTM."""
    candidates = [
        candidate(f"c{i}", "civil", 0.9 - i * 0.01, chars=100) for i in range(10)
    ]
    selection = select_within_budget(
        candidates,
        budget=rendered_block_cost(candidates[:5]),
        k_min=3,
    )

    assert selection.topics_present == ["civil"]
    assert selection.floor_per_topic == {"civil": 3}
    assert len(selection.selected) == 5
    assert selection.chars_used == rendered_block_cost(candidates[:5])


# --------------------------------------------------------------------------
# S7-T-008 — Phase 2, similarity fill
# --------------------------------------------------------------------------


def test_fill_order_is_strictly_by_similarity():
    candidates = [
        candidate("a", "t0", 0.10, chars=100),
        candidate("b", "t0", 0.90, chars=100),
        candidate("c", "t0", 0.50, chars=100),
    ]
    selection = select_within_budget(
        candidates,
        budget=rendered_block_cost([candidates[1], candidates[2]]),
        k_min=0,
    )

    assert [c["id"] for c in selection.selected] == ["b", "c"]


def test_fill_never_displaces_a_floor_selection():
    """A low-similarity floor pick survives while higher-similarity fill exists."""
    candidates = [
        candidate(f"civil-{i}", "civil", 0.90 - i * 0.001, chars=100)
        for i in range(20)
    ] + [candidate("marine-0", "marine", 0.05, chars=100)]

    selection = select_within_budget(
        candidates,
        budget=rendered_block_cost(
            [*candidates[:4], candidates[-1]]
        ),
        k_min=1,
    )

    assert "marine-0" in {c["id"] for c in selection.selected}
    assert selection.phases["marine-0"] == PHASE_FLOOR
    assert len(selection.selected) == 5


def test_fill_may_concentrate_in_one_domain():
    """No per-topic cap during fill — a targeted query keeps its budget."""
    candidates = [
        candidate(f"civil-{i}", "civil", 0.90 - i * 0.001, chars=100)
        for i in range(20)
    ] + [
        candidate(f"marine-{i}", "marine", 0.10 - i * 0.001, chars=100)
        for i in range(20)
    ]
    selection = select_within_budget(candidates, budget=2000, k_min=1)

    civil_chars = selection.chars_per_topic["civil"]
    assert civil_chars > selection.chars_per_topic["marine"]
    assert civil_chars / selection.chars_used > 0.5


def test_phases_are_labelled_for_every_selection():
    candidates = [
        candidate(f"{t}-{i}", t, 0.9 - i * 0.01, chars=100)
        for t in ("civil", "art")
        for i in range(5)
    ]
    selection = select_within_budget(candidates, budget=100_000, k_min=2)

    assert set(selection.phases) == {episode_key(c) for c in selection.selected}
    assert set(selection.phases.values()) == {PHASE_FLOOR, PHASE_FILL}
    assert sum(v == PHASE_FLOOR for v in selection.phases.values()) == 4


def test_per_topic_chars_sum_to_chars_used():
    candidates = [
        candidate(f"{t}-{i}", t, 0.9 - i * 0.01, chars=100 + i)
        for t in ("civil", "art", "marine")
        for i in range(6)
    ]
    selection = select_within_budget(candidates, budget=1200, k_min=2)

    assert (
        sum(selection.chars_per_topic.values())
        + selection.block_overhead_chars
        == selection.chars_used
    )


# --------------------------------------------------------------------------
# Record-to-episode collapse (Amendment 001 §3.4)
# --------------------------------------------------------------------------


def test_records_sharing_a_source_episode_collapse_to_one_budget_item():
    """Three spans of one episode render as one element and cost it once."""
    candidates = [
        candidate("ep1", "civil", 0.90, chars=300),
        candidate("ep1", "civil", 0.80, chars=300),
        candidate("ep1", "civil", 0.70, chars=300),
        candidate("ep2", "civil", 0.60, chars=300),
    ]
    selection = select_within_budget(candidates, budget=10_000, k_min=0)

    assert [c["id"] for c in selection.selected] == ["ep1", "ep2"]
    assert selection.chars_used == rendered_block_cost(
        [candidates[0], candidates[3]]
    )
    assert selection.collapsed_to_episode == 2


def test_collapse_keeps_the_highest_similarity_record():
    kept, collapsed = collapse_by_episode([
        candidate("ep1", "civil", 0.40),
        candidate("ep1", "civil", 0.90),
    ])
    assert collapsed == 1
    assert kept[0]["similarity"] == pytest.approx(0.90)


def test_collapse_is_deterministic_under_similarity_ties():
    tied = [
        candidate("b", "t", 0.5),
        candidate("a", "t", 0.5),
        candidate("c", "t", 0.5),
    ]
    first, _ = collapse_by_episode(tied)
    second, _ = collapse_by_episode(list(reversed(tied)))
    assert [c["id"] for c in first] == [c["id"] for c in second] == ["a", "b", "c"]


def test_excluded_episodes_are_dropped_before_selection():
    candidates = [
        candidate("ep1", "civil", 0.90, chars=300),
        candidate("ep2", "civil", 0.80, chars=300),
    ]
    selection = select_within_budget(
        candidates, budget=10_000, k_min=1, excluded_episode_ids={"ep1"}
    )

    assert [c["id"] for c in selection.selected] == ["ep2"]
    assert selection.chars_used == rendered_block_cost([candidates[1]])


# --------------------------------------------------------------------------
# select_top_m — the Study 006 policy, for the harness fidelity check
# --------------------------------------------------------------------------


def test_top_m_reproduces_count_based_selection():
    candidates = [
        candidate(f"e{i}", f"t{i % 4}", 0.9 - i * 0.01, chars=100)
        for i in range(20)
    ]
    selection = select_top_m(candidates, top_m=5)

    assert [c["id"] for c in selection.selected] == ["e0", "e1", "e2", "e3", "e4"]
    assert selection.chars_used == rendered_block_cost(candidates[:5])


def test_top_m_can_deliver_fewer_elements_than_its_cap():
    """Study 006's observed behaviour: 5 spans, 4 rendered elements."""
    candidates = [
        candidate("ep1", "civil", 0.95, chars=300),
        candidate("ep1", "civil", 0.94, chars=300),
        candidate("ep2", "civil", 0.93, chars=300),
        candidate("ep3", "civil", 0.92, chars=300),
        candidate("ep4", "civil", 0.91, chars=300),
        candidate("ep5", "civil", 0.10, chars=300),
    ]
    selection = select_top_m(candidates, top_m=5)

    assert len(selection.selected) == 4
    assert "ep5" not in {c["id"] for c in selection.selected}

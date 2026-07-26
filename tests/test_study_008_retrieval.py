"""Study 008 Factors F and R."""

import pytest

from src.memory.arbitration import arbitrate_budgeted
from src.memory.context_builder import (
    build_tagged_context,
    render_ltm_span_element,
)
from src.memory.informativeness import density_score
from src.memory.retrieval_budget import (
    FLOOR_DENSITY,
    FLOOR_SIMILARITY,
    PHASE_FILL,
    PHASE_FLOOR,
    RENDER_EPISODE,
    RENDER_SPAN,
    rendered_cost,
    selection_key,
    select_within_budget,
)


def candidate(
    episode_id: str,
    distilled_id: str,
    topic: str,
    similarity: float,
    *,
    episode_chars: int = 100,
    span_text: str = "dense fact 847 S460ML",
    rendered_density: float = 0.1,
    turn: int = 3,
    role: str = "user",
    span_start: int = 0,
) -> dict:
    return {
        "id": episode_id,
        "distilled_id": distilled_id,
        "topic_id": topic,
        "topic_label": topic,
        "similarity": similarity,
        "user_message": "u" * episode_chars,
        "assistant_message": "",
        "span_text": span_text,
        "role": role,
        "span_start": span_start,
        "span_end": span_start + len(span_text),
        "turn_number": turn,
        "source_turns": [turn],
        "dream_event": 31,
        "event_type": "transition",
        "rendered_density": rendered_density,
    }


def selected_ids(selection) -> set[str]:
    return {
        selection_key(item, selection.render_mode)
        for item in selection.selected
    }


def test_density_formula_is_the_formation_formula():
    assert density_score(3, 2, 10) == pytest.approx(0.7)


def test_density_floor_prefers_fact_over_equal_similarity_overview():
    overview = candidate(
        "overview",
        "d-overview",
        "art",
        0.5,
        rendered_density=0.05,
    )
    fact = candidate(
        "fact",
        "d-fact",
        "art",
        0.5,
        rendered_density=0.75,
    )
    selection = select_within_budget(
        [overview, fact],
        budget=10_000,
        k_min=1,
        floor_ranking=FLOOR_DENSITY,
        fill_cap=0,
    )

    assert selected_ids(selection) == {"fact"}
    assert selection.phases["fact"] == PHASE_FLOOR


def test_equal_density_floor_tiebreaks_by_similarity():
    lower = candidate(
        "lower",
        "d-lower",
        "art",
        0.4,
        rendered_density=0.5,
    )
    higher = candidate(
        "higher",
        "d-higher",
        "art",
        0.8,
        rendered_density=0.5,
    )
    selection = select_within_budget(
        [lower, higher],
        budget=10_000,
        k_min=1,
        floor_ranking=FLOOR_DENSITY,
        fill_cap=0,
    )
    assert selected_ids(selection) == {"higher"}


def test_fill_cap_prevents_one_topic_from_taking_all_fill():
    candidates = [
        candidate(f"civil-{i}", f"dc-{i}", "civil", 0.99 - i * 0.01)
        for i in range(5)
    ] + [
        candidate(f"art-{i}", f"da-{i}", "art", 0.30 - i * 0.01)
        for i in range(3)
    ]

    uncapped = select_within_budget(
        candidates,
        budget=500,
        k_min=1,
        floor_ranking=FLOOR_SIMILARITY,
    )
    capped = select_within_budget(
        candidates,
        budget=500,
        k_min=1,
        floor_ranking=FLOOR_SIMILARITY,
        fill_cap=2,
    )

    assert uncapped.fill_per_topic == {"civil": 3}
    assert capped.fill_per_topic == {"civil": 2, "art": 1}
    assert capped.cap_skips > 0


def test_floor_does_not_consume_fill_cap():
    items = [
        candidate(f"civil-{i}", f"d-{i}", "civil", 0.9 - i * 0.1)
        for i in range(4)
    ]
    selection = select_within_budget(
        items,
        budget=10_000,
        k_min=1,
        fill_cap=2,
    )
    assert selection.floor_per_topic == {"civil": 1}
    assert selection.fill_per_topic == {"civil": 2}
    assert len(selection.selected) == 3


def test_span_rendering_keeps_multiple_spans_from_one_episode():
    spans = [
        candidate("episode-1", f"span-{i}", "civil", 0.9 - i * 0.1)
        for i in range(3)
    ]
    episode_selection = select_within_budget(
        spans,
        budget=10_000,
        k_min=0,
        render_mode=RENDER_EPISODE,
    )
    span_selection = select_within_budget(
        spans,
        budget=10_000,
        k_min=0,
        render_mode=RENDER_SPAN,
    )

    assert len(episode_selection.selected) == 1
    assert len(span_selection.selected) == 3
    assert episode_selection.collapsed_to_episode == 2
    assert span_selection.collapsed_to_episode == 0


def test_span_renderer_snapshot_is_verbatim_with_provenance():
    span = candidate(
        "episode-55",
        "distilled-art",
        "Renaissance art",
        0.456789,
        span_text="The Annunciation was completed in 1483.",
        turn=55,
        span_start=12,
    )
    span["render_mode"] = RENDER_SPAN

    rendered = build_tagged_context(
        system_prompt="System",
        current_user_message="Probe",
        ltm_episodes=[span],
    )

    expected = """System

<pinned_rules/>

<recent_context/>

<retrieved_stm/>

<retrieved_ltm>
  <span distilled_id="distilled-art" source_episode_id="episode-55" source_turn="55" role="user" topic="Renaissance art" dream_event="31" span_start="12" span_end="51" event_type="transition" similarity="0.456789">The Annunciation was completed in 1483.</span>
</retrieved_ltm>

<current_turn>
  <user_message>Probe</user_message>
</current_turn>"""
    assert rendered == expected
    assert "u" * 100 not in rendered


def test_span_budget_charges_exact_serialized_element_not_episode_text():
    item = candidate(
        "episode",
        "span",
        "civil",
        0.9,
        episode_chars=4000,
        span_text="847 meters",
    )
    assert rendered_cost(item, RENDER_EPISODE) == 4000
    assert rendered_cost(item, RENDER_SPAN) == len(
        render_ltm_span_element({**item, "render_mode": RENDER_SPAN})
    )
    assert rendered_cost(item, RENDER_SPAN) > len("847 meters")


def test_span_containment_drops_by_source_episode_and_refills_floor():
    candidates = [
        candidate("stm-source", "span-drop", "art", 0.9),
        candidate("replacement", "span-keep", "art", 0.8),
        candidate("civil", "span-civil", "civil", 0.7),
    ]
    result = arbitrate_budgeted(
        stm_candidates=[],
        ltm_candidates=candidates,
        stm_block_episode_ids={"stm-source"},
        ltm_budget=10_000,
        ltm_k_min=1,
        render_mode=RENDER_SPAN,
    )

    keys = {
        selection_key(item, RENDER_SPAN)
        for item in result.budget.selected
    }
    assert "span-drop" not in keys
    assert {"span-keep", "span-civil"} <= keys
    assert result.budget.phases["span-keep"] == PHASE_FLOOR
    assert result.containment_drops == 1


def test_character_budget_uses_each_arms_registered_cost():
    episode = candidate(
        "episode",
        "episode-span",
        "civil",
        0.9,
        episode_chars=1000,
    )
    span = candidate(
        "source",
        "span",
        "civil",
        0.9,
        episode_chars=5000,
        span_text="x" * 1000,
    )
    episode_selection = select_within_budget(
        [episode],
        budget=1000,
        k_min=1,
        render_mode=RENDER_EPISODE,
    )
    span_selection = select_within_budget(
        [span],
        budget=2000,
        k_min=1,
        render_mode=RENDER_SPAN,
    )
    assert episode_selection.chars_used == 1000
    assert span_selection.chars_used == rendered_cost(span, RENDER_SPAN)
    assert span_selection.chars_used <= 2000

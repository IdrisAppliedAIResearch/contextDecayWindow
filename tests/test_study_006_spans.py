"""S6_002 — sentence segmentation, offsets, and the eligibility filter."""

import pytest

from src.memory import span_segmenter
from src.memory.span_segmenter import (
    MAX_SPAN_WORDS,
    MIN_SPAN_WORDS,
    REJECT_NO_CONTENT,
    REJECT_TOO_LONG,
    REJECT_TOO_SHORT,
    ROLE_ASSISTANT,
    ROLE_USER,
    Span,
    _regex_sentence_bounds,
    assert_span_offsets_faithful,
    eligible_spans,
    evaluate_eligibility,
    role_segments,
    segment_episode,
    segmenter_name,
)


def make_episode(user_message: str, assistant_message: str = "", **overrides):
    episode = {
        "id": "episode-1",
        "turn_number": 3,
        "user_message": user_message,
        "assistant_message": assistant_message,
        "text": f"User: {user_message}\nAssistant: {assistant_message}",
        "role": "conversation",
    }
    episode.update(overrides)
    return episode


# --- S6-T-004: segmentation with offsets ---------------------------------


def test_multi_sentence_turn_yields_expected_spans():
    episode = make_episode(
        "We are beginning work on a major infrastructure project called "
        "Halcyon Crossing — a long-span cable-stayed bridge. "
        "The total main span is 847 meters. "
        "The lead structural engineer assigned to the project is Dr. Anara Bekova. "
        "Please acknowledge these project parameters."
    )
    spans = [s for s in segment_episode(episode) if s.role == ROLE_USER]

    assert len(spans) == 4
    assert spans[0].text.endswith("cable-stayed bridge.")
    assert spans[1].text == "The total main span is 847 meters."
    assert spans[2].text.endswith("Dr. Anara Bekova.")
    assert spans[3].text == "Please acknowledge these project parameters."


def test_abbreviations_do_not_split():
    episode = make_episode(
        "The lead structural engineer assigned to the project is Dr. Anara Bekova."
    )
    spans = [s for s in segment_episode(episode) if s.role == ROLE_USER]

    assert len(spans) == 1
    assert "Dr. Anara Bekova" in spans[0].text


def test_decimals_and_percentages_do_not_split():
    episode = make_episode(
        "The measured drift was 2.3% under load. The tolerance is 4.75 mm."
    )
    spans = [s for s in segment_episode(episode) if s.role == ROLE_USER]

    assert len(spans) == 2
    assert spans[0].text == "The measured drift was 2.3% under load."
    assert spans[1].text == "The tolerance is 4.75 mm."


def test_offsets_round_trip_for_every_span():
    episode = make_episode(
        "The total main span is 847 meters. The pigment is Verdigris Green. "
        "Dr. Priya Mehta signed off on 12 of the 15 sections.",
        "1. Fatigue Failure: cyclic loading at 92.4 metric tons is the "
        "governing case.\n2. Corrosion: exposure is Risk: Medium.",
    )
    spans = segment_episode(episode)
    source = episode["text"]

    assert spans, "expected at least one span"
    for span in spans:
        assert source[span.start:span.end] == span.text

    assert_span_offsets_faithful(episode, spans)


def test_offset_assertion_trips_on_corrupted_span():
    episode = make_episode("The total main span is 847 meters.")
    spans = segment_episode(episode)
    mangled = [
        Span(
            text="The total main span is 999 meters.",
            start=spans[0].start,
            end=spans[0].end,
            episode_id=spans[0].episode_id,
            turn_number=spans[0].turn_number,
            role=spans[0].role,
            word_count=spans[0].word_count,
            named_entities=spans[0].named_entities,
            numeric_tokens=spans[0].numeric_tokens,
            eligible=spans[0].eligible,
        )
    ]

    with pytest.raises(AssertionError, match="do not round-trip"):
        assert_span_offsets_faithful(episode, mangled)


def test_roles_are_recovered_from_stored_layout():
    episode = make_episode(
        "The total main span is 847 meters.",
        "Acknowledged for Halcyon Crossing at 847 meters.",
    )
    segments = role_segments(episode)

    assert [role for role, _, _ in segments] == [ROLE_USER, ROLE_ASSISTANT]
    source = episode["text"]
    assert source[segments[0][1]:segments[0][2]] == (
        "The total main span is 847 meters."
    )
    assert source[segments[1][1]:segments[1][2]] == (
        "Acknowledged for Halcyon Crossing at 847 meters."
    )


def test_spans_are_tagged_with_their_role():
    episode = make_episode(
        "The total main span is 847 meters.",
        "Acknowledged for Halcyon Crossing at 847 meters.",
    )
    roles = {span.role for span in segment_episode(episode)}

    assert roles == {ROLE_USER, ROLE_ASSISTANT}


def test_episode_without_assistant_text_yields_user_spans_only():
    episode = make_episode("The total main span is 847 meters.", "")
    spans = segment_episode(episode)

    assert {span.role for span in spans} == {ROLE_USER}


def test_role_attribution_falls_back_to_separator_search():
    episode = make_episode("a", "b")
    episode["user_message"] = None
    episode["assistant_message"] = None
    episode["text"] = (
        "User: The total main span is 847 meters.\n"
        "Assistant: Acknowledged for Halcyon Crossing."
    )
    segments = role_segments(episode)

    assert [role for role, _, _ in segments] == [ROLE_USER, ROLE_ASSISTANT]
    source = episode["text"]
    assert source[segments[1][1]:segments[1][2]] == (
        "Acknowledged for Halcyon Crossing."
    )


def test_unattributable_layout_raises():
    episode = make_episode("a", "b")
    episode["user_message"] = None
    episode["assistant_message"] = None
    episode["text"] = "no role markers at all"

    with pytest.raises(ValueError, match="Cannot attribute span roles"):
        role_segments(episode)


def test_segmenter_is_recorded():
    name = segmenter_name()

    assert name
    if span_segmenter.spacy_available():
        assert name.startswith("spacy:en_core_web_sm:")
        assert name.endswith(":sentencizer")
    else:
        assert name == "regex_sentence_fallback"


# --- the documented regex fallback ---------------------------------------


def test_regex_fallback_splits_sentences():
    text = "The span is 847 meters. The engineer approved it."
    bounds = _regex_sentence_bounds(text)

    assert [text[a:b].strip() for a, b in bounds] == [
        "The span is 847 meters.",
        "The engineer approved it.",
    ]


def test_regex_fallback_protects_abbreviations_and_decimals():
    text = "Dr. Anara Bekova measured 2.3% drift. The result was accepted."
    bounds = _regex_sentence_bounds(text)

    assert [text[a:b].strip() for a, b in bounds] == [
        "Dr. Anara Bekova measured 2.3% drift.",
        "The result was accepted.",
    ]


# --- S6-T-005: eligibility filter ----------------------------------------


def test_two_word_fragment_is_rejected_for_length():
    eligible, reason = evaluate_eligibility(
        word_count=2, named_entities=1, numeric_tokens=1
    )

    assert eligible is False
    assert reason == REJECT_TOO_SHORT


def test_run_on_span_is_rejected_for_length():
    eligible, reason = evaluate_eligibility(
        word_count=70, named_entities=5, numeric_tokens=5
    )

    assert eligible is False
    assert reason == REJECT_TOO_LONG


def test_prose_without_entity_or_number_is_rejected_for_content():
    eligible, reason = evaluate_eligibility(
        word_count=20, named_entities=0, numeric_tokens=0
    )

    assert eligible is False
    assert reason == REJECT_NO_CONTENT


def test_window_boundaries_are_inclusive():
    assert evaluate_eligibility(MIN_SPAN_WORDS, 1, 0) == (True, None)
    assert evaluate_eligibility(MAX_SPAN_WORDS, 1, 0) == (True, None)
    assert evaluate_eligibility(MIN_SPAN_WORDS - 1, 1, 0)[0] is False
    assert evaluate_eligibility(MAX_SPAN_WORDS + 1, 1, 0)[0] is False


def test_entity_alone_or_number_alone_satisfies_content():
    assert evaluate_eligibility(10, 1, 0) == (True, None)
    assert evaluate_eligibility(10, 0, 1) == (True, None)


def test_planted_fact_is_accepted():
    episode = make_episode("The total main span is 847 meters.")
    spans = eligible_spans(episode)

    assert len(spans) == 1
    assert spans[0].text == "The total main span is 847 meters."
    assert spans[0].numeric_tokens >= 1


def test_short_acknowledgment_is_rejected_and_reason_logged():
    episode = make_episode(
        "Understood.",
        "Acknowledged.",
    )
    spans = segment_episode(episode)

    assert spans, "segmentation should still produce spans"
    assert all(not span.eligible for span in spans)
    assert all(
        span.rejection_reason == REJECT_TOO_SHORT for span in spans
    )


def test_ineligible_spans_are_returned_with_reasons_but_excluded():
    episode = make_episode(
        "The total main span is 847 meters. It seems fine to me overall.",
    )
    all_spans = [s for s in segment_episode(episode) if s.role == ROLE_USER]
    kept = eligible_spans(episode)

    assert len(all_spans) == 2
    assert len(kept) == 1
    rejected = [s for s in all_spans if not s.eligible]
    assert len(rejected) == 1
    assert rejected[0].rejection_reason == REJECT_NO_CONTENT


def test_base_reflects_the_double_weight_on_numerics():
    span = Span(
        text="x",
        start=0,
        end=1,
        episode_id="e",
        turn_number=1,
        role=ROLE_USER,
        word_count=10,
        named_entities=1,
        numeric_tokens=2,
        eligible=True,
    )

    assert span.base == 1 + 2 * 2

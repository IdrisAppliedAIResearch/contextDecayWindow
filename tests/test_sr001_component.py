from __future__ import annotations

import pytest

from src.retrieval_bakeoff.models import Candidate
from src.retrieval_mechanism_ledger.sr001 import (
    assert_mechanism_path_allowed,
    episode_to_spans,
    pack_control,
    pack_treatment,
    rank_sources,
    source_content_sha256,
    source_identity_sequence,
)


def episode(candidate_id: str, turn: int, user: str, assistant: str) -> Candidate:
    return Candidate(
        candidate_id=candidate_id,
        source_episode_id=candidate_id,
        turn_number=turn,
        unit_type="episode",
        user_message=user,
        assistant_message=assistant,
        topic_id="topic",
        topic_label="label",
    )


def test_spans_are_faithful_ordered_and_provenanced() -> None:
    source = episode("e1", 1, "First user sentence. Second one!", "Assistant fact 42. Final note.")
    spans = episode_to_spans(source)
    assert [span.role for span in spans] == ["user", "user", "assistant", "assistant"]
    assert all(span.source_episode_id == "e1" for span in spans)
    full = f"User: {source.user_message}\nAssistant: {source.assistant_message}"
    assert all(full[span.span_start : span.span_end] == span.span_text for span in spans)


def test_empty_roles_emit_no_empty_spans() -> None:
    source = episode("e1", 1, "", "One retained sentence.")
    spans = episode_to_spans(source)
    assert [span.span_text for span in spans] == ["One retained sentence."]


def test_rank_uses_score_then_stable_content_hash() -> None:
    left = episode("generated-z", 1, "A.", "B.")
    right = episode("generated-a", 2, "C.", "D.")
    ranked = rank_sources([left, right], [0.5, 0.5])
    expected = sorted([left, right], key=source_content_sha256)
    assert [row.candidate for row in ranked] == expected
    assert all(row.component_scores == {"dense": 0.5} for row in ranked)


def test_treatment_preserves_source_rank_and_scores() -> None:
    ranked = rank_sources(
        [episode("e1", 1, "One.", "Two."), episode("e2", 2, "Three.", "Four.")],
        [0.9, 0.8],
    )
    treatment = pack_treatment(ranked, budget=10_000)
    assert list(dict.fromkeys(row.candidate.source_episode_id for row in treatment.selected)) == [
        row.candidate.source_episode_id for row in ranked
    ]
    assert [row.score for row in treatment.selected] == [0.9, 0.9, 0.8, 0.8]
    assert source_identity_sequence(ranked) == tuple(source_content_sha256(row.candidate) for row in ranked)


def test_span_packing_can_partially_admit_a_source_and_continue() -> None:
    ranked = rank_sources(
        [
            episode("e1", 1, "Short fact.", "A" * 400 + "."),
            episode("e2", 2, "Later fact.", "Tail."),
        ],
        [0.9, 0.8],
    )
    treatment = pack_treatment(ranked, budget=500)
    selected_sources = [row.candidate.source_episode_id for row in treatment.selected]
    assert "e1" in selected_sources
    assert "e2" in selected_sources
    assert treatment.skipped_oversized >= 1


def test_control_and_treatment_obey_exact_budget() -> None:
    ranked = rank_sources([episode("e1", 1, "Fact.", "Detail.")], [1.0])
    assert len(pack_control(ranked, budget=32_000).rendered_block) <= 32_000
    assert len(pack_treatment(ranked, budget=32_000).rendered_block) <= 32_000


def test_forbidden_measurement_paths_stop() -> None:
    with pytest.raises(PermissionError):
        assert_mechanism_path_allowed("sealed/answer_key_121.json")
    assert_mechanism_path_allowed("sealed/queries_121.json")


def test_source_rank_rejects_spans_and_length_mismatch() -> None:
    source = episode("e1", 1, "Fact.", "Detail.")
    span = episode_to_spans(source)[0]
    with pytest.raises(ValueError):
        rank_sources([source], [])
    with pytest.raises(ValueError):
        rank_sources([span], [1.0])

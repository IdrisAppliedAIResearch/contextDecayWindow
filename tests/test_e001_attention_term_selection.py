from pathlib import Path

import numpy as np
import pytest

from src.analysis.e001_attention_capture import leakage_audit
from src.analysis.e001_attention_term_selection import build_sweep_rows
from src.analysis.e002_segmented_query import RUN_ROOT
from src.retrieval_mechanism_ledger.e001 import (
    assert_mechanism_path_allowed,
    calibration_cases,
    overlapping_token_indices,
    score_retrieval_heads,
    select_cue,
    unit_scores,
    whitespace_units,
)
from src.retrieval_mechanism_ledger.seal import verify_mixed_source_seal


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_calibration_grid_is_complete_and_deterministic() -> None:
    cases = calibration_cases()

    assert len(cases) == 32
    assert len({case.case_id for case in cases}) == 32
    assert {case.needle_position for case in cases} == {0, 8, 16, 24}
    assert all(case.text[case.needle_code_start:case.needle_code_end] == case.code for case in cases)
    assert all(case.text[case.answer_code_start:case.answer_code_end] == case.code for case in cases)


def test_overlap_mapping_requires_real_character_overlap() -> None:
    offsets = [(0, 3), (4, 7), (8, 12)]

    assert overlapping_token_indices(offsets, start=4, end=7) == (1,)
    assert overlapping_token_indices(offsets, start=6, end=9) == (1, 2)


def test_retrieval_head_score_uses_preceding_row_and_haystack_only() -> None:
    attention = np.zeros((1, 2, 5, 5), dtype=np.float32)
    attention[0, 0, 2, 1] = 1.0
    attention[0, 1, 2, 0] = 1.0

    hits, observations = score_retrieval_heads(
        attention,
        haystack_indices=(0, 1),
        answer_indices=(3,),
        needle_indices=(1,),
    )

    assert observations == 1
    assert hits.tolist() == [[1.0, 0.0]]


def test_unit_scores_sum_subwords_and_cue_preserves_query_order() -> None:
    query = "marine snow details"
    offsets = [(0, 3), (3, 6), (7, 11), (12, 19)]
    scores = [0.2, 0.3, 0.4, 0.1]
    scored = unit_scores(query, token_offsets=offsets, token_scores=scores)

    assert [(unit.text, score) for unit, score in scored] == [
        ("marine", 0.5),
        ("snow", 0.4),
        ("details", 0.1),
    ]
    cue, selected, mass = select_cue(scored, k=2)
    assert cue == "marine snow"
    assert selected == (0, 1)
    assert mass == pytest.approx(0.9)


def test_whitespace_units_preserve_punctuation_and_spans() -> None:
    units = whitespace_units("who painted it, and when?")

    assert [unit.text for unit in units] == ["who", "painted", "it,", "and", "when?"]
    assert all(unit.text == "who painted it, and when?"[unit.start:unit.end] for unit in units)


def test_attention_sweep_covers_both_arms_and_full_query_cue() -> None:
    attention = np.zeros((1, 2, 3, 3), dtype=np.float32)
    attention[:, :, 1, :2] = (0.8, 0.2)
    attention[:, :, 2, :2] = (0.3, 0.7)
    tokenization = {
        "query_token_count": 2,
        "eos_token_index": 2,
        "offsets": [[0, 5], [6, 10], [10, 10]],
        "tokens": ["alpha", "beta", "<eos>"],
    }

    rows = build_sweep_rows(
        query="alpha beta",
        attention=attention,
        tokenization=tokenization,
        retrieval_heads=[(0, 0)],
    )

    assert {row["arm"] for row in rows} == {"all_heads", "retrieval_heads"}
    assert any(row["cue"] == "alpha beta" and row["k"] == 2 for row in rows)
    assert all(row["cue"] for row in rows)


def test_mechanism_rejects_measurement_paths_and_imports() -> None:
    with pytest.raises(ValueError, match="measurement boundary"):
        assert_mechanism_path_allowed("experiments/study_009/q_facts_key.md")

    result = leakage_audit()
    assert result["status"] == "PASS"
    assert result["forbidden_imports"] == []
    assert result["planted_forbidden_path_rejected"] is True


def test_shared_mixed_seal_gate_matches_corrected_source() -> None:
    result = verify_mixed_source_seal(REPO_ROOT, RUN_ROOT)

    assert result["status"] == "PASS"
    assert result["representations"] == {
        "sealed_canonical_lf": 2,
        "sealed_materialized_crlf": 262,
        "exact_untracked_binary": 1,
    }

from __future__ import annotations

import numpy as np

from src.analysis.e006_rev4_pf11 import (
    AUTHORIZATION,
    AUTHORIZATION_SHA256,
    DESIGN,
    DESIGN_SHA256,
    SCORE_TOLERANCE,
    build_report,
    evaluate_pf11,
    load_inputs,
    registered_section2_scores,
    sha256_file,
    vector_independence_audit,
)


def test_rev4_design_and_authorization_are_locked() -> None:
    assert sha256_file(DESIGN) == DESIGN_SHA256
    assert sha256_file(AUTHORIZATION) == AUTHORIZATION_SHA256


def test_vector_route_is_independent_of_registered_derivation() -> None:
    audit = vector_independence_audit()

    assert audit["status"] == "PASS"
    assert audit["unexpected_imports"] == []
    assert audit["found"] == []


def test_registered_section2_uses_its_literal_context_norm() -> None:
    inputs = load_inputs()
    hits = np.arange(3, dtype=np.int64)

    _scores, evidence = registered_section2_scores(
        inputs=inputs,
        hits=hits,
        query_weight=0.5,
        retention=0.7,
    )

    query_hit_mean = float(inputs.query_cosines[hits].mean())
    expected = np.sqrt(0.7**2 + 0.3**2 + 2.0 * 0.7 * 0.3 * query_hit_mean)
    np.testing.assert_allclose(
        evidence["registered_context_norm"], expected, rtol=0.0, atol=1e-15
    )


def test_pf11_status_is_the_conjunction_of_all_registered_criteria() -> None:
    result = evaluate_pf11(load_inputs())
    expected_pass = all(
        cell["max_abs_score_difference"] < SCORE_TOLERANCE
        and cell["full_ranking_equal"]
        and cell["next_top_m_equal"]
        for cell in result["cells"]
    )

    assert result["cell_count"] == 12
    assert (result["status"] == "PASS") is expected_pass


def test_pf11_controls_the_next_stage() -> None:
    report = build_report()

    expected = (
        "CONTINUE_PREFLIGHT"
        if report["status"] == "PASS"
        else "STOP_BEFORE_REMAINING_PREFLIGHT"
    )
    assert report["decision"] == expected
    assert report["zero_model_calls"] is True
    assert report["zero_embedding_calls"] is True
    assert report["vector_route_independence"]["status"] == "PASS"

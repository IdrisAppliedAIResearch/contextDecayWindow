from __future__ import annotations

import numpy as np

from src.analysis.e006_rev3_pf11 import (
    AUTHORIZATION,
    AUTHORIZATION_SHA256,
    DESIGN,
    DESIGN_SHA256,
    build_report,
    corrected_recurrence_scores,
    direct_mechanism_scores,
    evaluate_pf11,
    load_inputs,
    reconstruct_query,
    sha256_file,
)


def test_rev3_design_and_authorization_are_locked() -> None:
    assert sha256_file(DESIGN) == DESIGN_SHA256
    assert sha256_file(AUTHORIZATION) == AUTHORIZATION_SHA256


def test_q11_cosines_admit_a_unit_query_reconstruction() -> None:
    inputs = load_inputs()

    query, episodes, evidence = reconstruct_query(inputs)

    assert query.shape == (1025,)
    assert episodes.shape == (119, 1025)
    np.testing.assert_allclose(
        evidence["unit_query_norm"], 1.0, rtol=0.0, atol=1e-12
    )


def test_corrected_recurrence_matches_the_independent_vector_route() -> None:
    inputs = load_inputs()
    query, episodes, _evidence = reconstruct_query(inputs)
    hits = np.arange(3, dtype=np.int64)

    direct = direct_mechanism_scores(
        query=query,
        episodes=episodes,
        hits=hits,
        query_weight=0.5,
        retention=0.7,
    )
    corrected = corrected_recurrence_scores(
        inputs=inputs,
        hits=hits,
        query_weight=0.5,
        retention=0.7,
    )

    np.testing.assert_allclose(direct, corrected, rtol=0.0, atol=1e-12)


def test_registered_derivation_fails_pf11_on_the_real_trace() -> None:
    result = evaluate_pf11(load_inputs())

    assert result["status"] == "FAIL"
    assert result["cell_count"] == 12
    assert result["registered_full_ranking_equal_count"] == 0
    assert result["registered_max_abs_score_difference_range"][0] > 0.03
    assert result["corrected_recurrence_diagnostic"][
        "full_ranking_equal_count"
    ] == 12


def test_pf11_failure_stops_before_remaining_preflight() -> None:
    report = build_report()

    assert report["status"] == "FAIL"
    assert report["decision"] == "STOP_BEFORE_REMAINING_PREFLIGHT"
    assert report["zero_model_calls"] is True
    assert report["zero_embedding_calls"] is True
    assert report["leakage_audit"]["status"] == "PASS"

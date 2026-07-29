import json
from pathlib import Path

from src.analysis.retrieval_bakeoff_tier6_121 import (
    RUN_ROOT,
    context_match_analysis,
    fact_delivery_analysis,
    n_order_contract_analysis,
    retrieval_composition_analysis,
    score_comparison,
    verify_mechanism_seal,
)


def test_committed_mechanism_seal_verifies() -> None:
    result = verify_mechanism_seal(RUN_ROOT)

    assert result["status"] == "PASS"
    assert result["mechanism_file_count"] == 265
    assert (
        result["aggregate_sha256"]
        == "8f131532e3f63918babd77d6c01bae4030848553c9fd9fcac4a8f88ceb523462"
    )


def test_live_context_passed_registered_character_gate() -> None:
    summary, probe_rows = context_match_analysis()

    registered = summary["registered_gate_window_92_111"]
    assert summary["registered_gate_status"] == "PASS"
    assert registered["median_absolute_percentage_error"] <= 0.05
    assert registered["turns_within_5_percent"] == 20
    assert len(probe_rows) == 10


def test_live_engine_n_order_diverges_from_calibration_contract() -> None:
    result = n_order_contract_analysis()

    assert result["calibration_order"] == ["never", "old", "new"]
    assert result["production_order"] == ["never", "new", "old"]
    assert result["orders_match"] is False
    assert result["finding"].startswith("DIVERGENCE")


def test_k_found_candidates_but_never_added_context() -> None:
    summary, _composition_rows, _probe_rows = (
        retrieval_composition_analysis()
    )

    assert summary["total_k_candidates"] == 167
    assert summary["turns_with_k_candidates"] == 74
    assert summary["total_k_only_delivered"] == 0
    assert summary["turns_with_k_only_delivery"] == 0


def test_targeted_delivery_loss_matches_score_loss() -> None:
    targeted, _breadth, _origins = fact_delivery_analysis()

    def delivered(arm: str, question: str) -> int:
        return sum(
            bool(row["in_retrieval_payload"])
            for row in targeted
            if row["arm"] == arm and row["question"] == question
        )

    assert delivered("T6", "Q4") == 0
    assert delivered("S", "Q4") == 4
    assert delivered("T6", "Q6") == 0
    assert delivered("S", "Q6") == 2
    assert delivered("T6", "Q7") == 0
    assert delivered("S", "Q7") == 5


def test_t6_used_all_q11_atomic_facts_it_received() -> None:
    _targeted, breadth, origins = fact_delivery_analysis()
    q11 = [
        row
        for row in breadth
        if row["arm"] == "T6" and row["question"] == "Q11"
    ]
    delivered = [row for row in q11 if row["in_retrieval_payload"]]

    assert len(delivered) == 7
    assert all(row["status"] == "recalled" for row in delivered)
    assert sum(
        row["registered_plant_turn_selected"]
        for row in origins
        if row["question"] == "Q11" and row["matching_source_turns"]
    ) == 5


def test_score_comparison_uses_corrected_study009_scores() -> None:
    summary, rows = score_comparison()

    assert summary["T6_Q1_Q13"] == 6.5
    assert summary["S_Q1_Q13"] == 9.0
    assert summary["L_Q1_Q13"] == 12.0
    assert summary["T6_losses_vs_S"] == ["Q4", "Q6", "Q7"]
    assert {
        row["question"]
        for row in rows
        if row["T6_minus_S"] > 0
    } == {"Q14"}

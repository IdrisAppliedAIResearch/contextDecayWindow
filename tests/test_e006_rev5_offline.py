from __future__ import annotations

from src.analysis.e006_rev5_offline import deterministic_evaluate, evaluate


def test_s4_reproduces_all_preflight_selection_identities() -> None:
    result, records, _payloads = evaluate()

    assert result["selection_reproduction"] == "PASS"
    assert result["registered_cell_count"] == 48
    assert len(records) == 48


def test_s4_payloads_respect_exact_budget_and_fact_range() -> None:
    _result, records, _payloads = evaluate()

    assert all(record["serialized_chars"] <= 32_000 for record in records)
    assert all(0 <= record["q11_fact_count"] <= 17 for record in records)
    assert all(
        record["selected_episode_count"] <= record["candidate_count"]
        for record in records
    )


def test_s4_d0_control_remains_single_shot() -> None:
    result, _records, _payloads = evaluate()

    control = result["x1_single_shot_control"]
    assert control["status"] == "PASS"
    assert control["cell_count"] == 12


def test_s4_is_deterministic_and_capped_at_characterized() -> None:
    result, _records, _payloads = deterministic_evaluate()

    assert result["determinism"]["status"] == "PASS"
    assert result["outcome_ceiling"] == "CHARACTERIZED"
    assert result["zero_model_calls"] is True
    assert result["zero_embedding_calls"] is True
    assert result["live_evaluation"] is False

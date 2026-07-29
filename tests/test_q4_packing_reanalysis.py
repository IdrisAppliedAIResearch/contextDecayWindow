from src.analysis.q4_packing_reanalysis import (
    B_SWEEP,
    HISTORICAL_FITTED_EPISODES,
    HISTORICAL_PAYLOAD_CHARS,
    N_CAP,
    PLANT_TURN,
    REGISTERED_B_LTM,
    _context_row,
    _decision,
    _historical_reproduction,
    _ordered_candidates,
    _pack_row,
    _turn_55_id,
    verify_canonical_source_seal,
)


def test_corrected_source_run_canonical_blobs_match_seal() -> None:
    result = verify_canonical_source_seal()

    assert result["status"] == "FAIL_MISSING_COMMITTED_DB"
    assert result["analysis_source_status"] == "PASS"
    assert result["expected_mechanism_file_count"] == 265
    assert result["tracked_mechanism_file_count"] == 264
    assert result["missing_committed_files"] == ["study.db"]
    assert result["matched_representations"] == {
        "canonical_lf": 2,
        "materialized_crlf": 262,
    }
    assert not result["canonical_mismatches"]


def test_historical_q4_payload_reproduces_before_reanalysis() -> None:
    context_row = _context_row()
    candidates = _ordered_candidates(context_row)
    result = _historical_reproduction(candidates, context_row)

    assert result["status"] == "PASS"
    assert result["episode_count"] == HISTORICAL_FITTED_EPISODES
    assert result["serialized_chars"] == HISTORICAL_PAYLOAD_CHARS


def test_q4_candidate_contract_is_preserved() -> None:
    candidates = _ordered_candidates(_context_row())

    assert len(candidates) == N_CAP
    assert len({candidate["id"] for candidate in candidates}) == N_CAP
    assert int(candidates[26]["turn_number"]) == PLANT_TURN
    assert str(candidates[26]["id"]) == _turn_55_id(candidates)


def test_locked_sweep_changes_only_exact_budget() -> None:
    candidates = _ordered_candidates(_context_row())
    rows = [_pack_row(candidates, budget) for budget in B_SWEEP]

    assert [row["budget_chars"] for row in rows] == list(B_SWEEP)
    assert REGISTERED_B_LTM in B_SWEEP
    assert all(row["serialized_chars"] <= row["budget_chars"] for row in rows)
    assert all(
        row["selected_ids"]
        == [
            candidate["id"]
            for candidate in candidates
            if candidate["id"] in set(row["selected_ids"])
        ]
        for row in rows
    )


def test_decision_rule_is_mechanical() -> None:
    assert _decision({"fitted_episodes": 29, "turn_55_selected": True}, 32_000)[
        "branch"
    ] == "A"
    assert _decision({"fitted_episodes": 27, "turn_55_selected": True}, 32_000)[
        "branch"
    ] == "B"
    assert _decision({"fitted_episodes": 15, "turn_55_selected": False}, 48_000)[
        "branch"
    ] == "C"
    assert _decision({"fitted_episodes": 15, "turn_55_selected": False}, None)[
        "branch"
    ] == "D"

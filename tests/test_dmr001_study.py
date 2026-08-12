"""DMR-001 study harness: corpus selection, measurement, gates, and artifacts.

The mechanism's own contract is in `test_dmr001_event_context.py`. This file
covers the code that selects the corpus, scores agreement, and decides the
gates, plus the committed artifacts those produced.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.analysis.dmr001_corpus import (
    canonical_pair_sha256,
    corpus_manifest,
    episode_hash,
    holdout_script_sha256,
    session_hash_for_realization,
)
from src.analysis.dmr001_exploration import boundary_agreement, periodic_boundaries
from src.analysis.dmr001_gates import (
    BARS,
    DISPOSITIONS,
    PASS_DISPOSITION,
    evaluate_gates,
)
from src.analysis.dmr001_preflight import _passing_inputs

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "experiments" / "components" / "biological_memory" / "dmr_001"
CORPUS_LOCK = STUDY / "artifacts" / "dmr001_corpus" / "corpus_lock.json"
PART1 = STUDY / "exploration" / "DMR_001_PART1_EXPLORATION.json"
PREFLIGHT = STUDY / "artifacts" / "dmr001_preflight" / "preflight.json"
GATES = STUDY / "artifacts" / "dmr001_gates" / "gate_report.json"
POSTSTOP = STUDY / "artifacts" / "dmr001_gates" / "post_stop_characterization.json"
REGISTRATION = STUDY / "DMR_001_PRE_REGISTRATION.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_pair_identity_is_canonical_and_order_sensitive() -> None:
    assert canonical_pair_sha256("a", "b") == canonical_pair_sha256("a", "b")
    assert canonical_pair_sha256("a", "b") != canonical_pair_sha256("b", "a")


def test_episode_identity_separates_duplicate_text_by_position() -> None:
    session = session_hash_for_realization("f" * 64)
    pair = canonical_pair_sha256("same", "same")
    assert episode_hash(session, 3, pair) != episode_hash(session, 4, pair)
    assert episode_hash(session, 3, pair) == episode_hash(session, 3, pair)


def test_episode_identity_separates_sessions() -> None:
    pair = canonical_pair_sha256("same", "same")
    first = session_hash_for_realization("a" * 64)
    second = session_hash_for_realization("b" * 64)
    assert episode_hash(first, 0, pair) != episode_hash(second, 0, pair)


def test_negative_stream_index_is_rejected() -> None:
    from src.analysis.dmr001_corpus import CorpusError

    with pytest.raises(CorpusError):
        episode_hash("a" * 64, -1, "b" * 64)


# ---------------------------------------------------------------------------
# Boundary agreement
# ---------------------------------------------------------------------------


def test_one_prediction_cannot_cover_two_annotations() -> None:
    result = boundary_agreement({5}, {4, 5, 6}, tolerance=1, stream_length=20)
    assert result["matched"] == 1
    assert result["recalled"] == 1
    assert result["recall"] == pytest.approx(1 / 3)


def test_perfect_and_empty_agreement() -> None:
    perfect = boundary_agreement({0, 10}, {0, 10}, tolerance=0, stream_length=20)
    assert perfect["f1"] == 1.0
    empty = boundary_agreement(set(), {0, 10}, tolerance=0, stream_length=20)
    assert empty["f1"] == 0.0


def test_predicting_everything_gets_full_recall_and_poor_precision() -> None:
    result = boundary_agreement(set(range(100)), {10, 50}, tolerance=0, stream_length=100)
    assert result["recall"] == 1.0
    assert result["precision"] == pytest.approx(0.02)
    assert result["f1"] < 0.05


def test_tolerance_widens_matching_monotonically() -> None:
    scores = [
        boundary_agreement({9}, {10}, tolerance=t, stream_length=20)["f1"] for t in (0, 1, 2)
    ]
    assert scores == sorted(scores)


def test_periodic_boundaries_respect_session_starts() -> None:
    boundaries = periodic_boundaries(10, 4, {0, 5})
    assert boundaries == {0, 4, 5, 9}


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------


def test_gate_bars_match_the_committed_registration_text() -> None:
    """The bars in code must be the bars in the registration, not near them."""
    text = REGISTRATION.read_text(encoding="utf-8")
    assert "Singleton fraction <= 0.20" in text
    assert "forced fraction <= 0.35" in text
    assert "more than 25% of its session" in text
    assert "`C_SESSION` F1 + 0.05" in text
    assert "`C_PERIODIC_k` F1 + 0.05" in text
    assert "recall >= 0.50" in text
    assert "precision >= 0.20" in text
    assert "macro context AUC >= 0.70" in text
    assert "every holdout session's context AUC >= 0.60" in text

    assert BARS["G3"]["max_singleton_fraction"] == 0.20
    assert BARS["G3"]["max_forced_fraction"] == 0.35
    assert BARS["G3"]["max_largest_event_share_of_session"] == 0.25
    assert BARS["G4"]["margin_over_c_session"] == 0.05
    assert BARS["G4"]["margin_over_best_periodic"] == 0.05
    assert BARS["G4"]["min_recall"] == 0.50
    assert BARS["G4"]["min_precision"] == 0.20
    assert BARS["G5"]["min_context_auc_macro"] == 0.70
    assert BARS["G5"]["min_per_session_context_auc"] == 0.60


def test_gates_stop_at_the_first_failure() -> None:
    inputs = _passing_inputs()
    inputs["partition"]["members"] = 9
    verdict = evaluate_gates(**inputs)
    assert verdict["stopped_at"] == "G2"
    assert verdict["disposition"] == DISPOSITIONS["G2"]
    evaluated = {gate["gate"]: gate["evaluated"] for gate in verdict["gates"]}
    assert evaluated == {
        "G1": True,
        "G2": True,
        "G3": False,
        "G4": False,
        "G5": False,
    }


def test_a_clean_run_reaches_the_pass_disposition() -> None:
    assert evaluate_gates(**_passing_inputs())["disposition"] == PASS_DISPOSITION


def test_g5_derives_the_raw_margin_rather_than_trusting_the_report() -> None:
    inputs = _passing_inputs()
    separation = inputs["split_reports"]["holdout"]["arms"]["T_EVENT"]["context_separation"]
    separation["raw_auc_macro"] = 0.95
    separation["context_minus_raw"] = 0.99  # an inconsistent, flattering field
    verdict = evaluate_gates(**inputs)
    assert verdict["disposition"] == DISPOSITIONS["G5"]


def test_identity_with_a_periodic_control_fails_g3() -> None:
    inputs = _passing_inputs()
    inputs["split_reports"]["holdout"]["arms"]["T_EVENT"]["identical_to"] = ["C_PERIODIC_8"]
    assert evaluate_gates(**inputs)["disposition"] == DISPOSITIONS["G3"]


# ---------------------------------------------------------------------------
# Committed artifacts
# ---------------------------------------------------------------------------


def test_committed_corpus_lock_has_the_registered_shape() -> None:
    manifest = load(CORPUS_LOCK)
    counts = manifest["counts"]
    assert counts["sessions"] == 17
    assert counts["episodes"] == 3724
    assert counts["development_episodes"] == 1724
    assert counts["holdout_episodes"] == 2000
    assert counts["development_annotated_boundaries"] == 60
    assert counts["holdout_annotated_boundaries"] == 36
    assert len({row["session_sha256"] for row in manifest["sessions"]}) == 17


def test_the_holdout_is_the_single_longest_script() -> None:
    manifest = load(CORPUS_LOCK)
    holdout = [row for row in manifest["sessions"] if row["split"] == "holdout"]
    development = [row for row in manifest["sessions"] if row["split"] == "development"]
    assert {row["script_sha256"] for row in holdout} == {manifest["holdout_script_sha256"]}
    assert min(row["episode_count"] for row in holdout) > max(
        row["episode_count"] for row in development
    )


def test_part1_record_carries_no_holdout_outcome() -> None:
    """Part 1 may count the holdout. It may not score it."""
    record = load(PART1)
    structure = record["holdout_structure"]
    for session in structure["sessions"]:
        assert set(session) == {
            "session_sha256",
            "episode_count",
            "annotated_boundary_count",
            "stream_digest",
            "vector_digest",
        }
    serialized = json.dumps(record["threshold_grid"])
    assert "holdout" not in serialized
    assert record["rho_sweep"]["boundary_config"]["drift_threshold"] == 0.7


def test_committed_preflight_passes_every_check() -> None:
    report = load(PREFLIGHT)
    assert report["status"] == "PASS"
    assert report["failed_checks"] == []
    for key, value in report.items():
        if key.startswith("PF") and isinstance(value, dict) and "checks" in value:
            assert value["checks"], key
            assert all(check["passed"] for check in value["checks"]), key


def test_committed_gate_report_stops_at_g3() -> None:
    report = load(GATES)
    verdict = report["verdict"]
    assert verdict["stopped_at"] == "G3"
    assert verdict["disposition"] == "DEGENERATE_FORMATION"
    assert verdict["passed"] is False
    by_gate = {gate["gate"]: gate for gate in verdict["gates"]}
    assert by_gate["G1"]["passed"] and by_gate["G1"]["evaluated"]
    assert by_gate["G2"]["passed"] and by_gate["G2"]["evaluated"]
    assert by_gate["G3"]["evaluated"] and not by_gate["G3"]["passed"]
    assert not by_gate["G4"]["evaluated"]
    assert not by_gate["G5"]["evaluated"]


def test_the_stop_survives_removing_the_defective_bar() -> None:
    """The disposition must not rest on the bar PF4 failed to check."""
    report = load(GATES)
    g3 = next(gate for gate in report["verdict"]["gates"] if gate["gate"] == "G3")
    failures = [check for check in g3["checks"] if not check["passed"]]
    remaining = [
        check for check in failures if "largest event share" not in check["check"]
    ]
    assert remaining, "the stop would rest entirely on the unverified bar"
    assert any("holdout: forced fraction" in check["check"] for check in remaining)


def test_post_stop_characterization_is_labelled_and_consistent() -> None:
    report = load(POSTSTOP)
    assert report["status"] == "POST_STOP_DESCRIPTIVE_ONLY"
    assert report["stopped_at"] == "G3"
    assert report["bar_reachability_defect"]["affects_disposition"] is False
    holdout = report["splits"]["holdout"]["matches"]
    assert holdout["matched_by_reason"].get("forced", 0) == 0
    assert holdout["precision_by_reason"]["drift"] == 1.0
    assert holdout["share_of_boundaries_from_forced"] > BARS["G3"]["max_forced_fraction"]

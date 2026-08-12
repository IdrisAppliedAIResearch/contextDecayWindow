"""DMR-001C: corpus construction, blinding, and the committed sealed-holdout result."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.analysis.dmr001c_corpus import (
    DATASET_SHA256,
    RANK_HIGH,
    RANK_LOW,
    episode_identity,
    episode_text,
    pair_sha256,
    strict_exchanges,
    stream_token,
)
from src.analysis.dmr001c_gates import BARS, PERIODS, PASS_DISPOSITION

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "experiments" / "components" / "biological_memory" / "dmr_001c"
CORPUS = STUDY / "artifacts" / "dmr001c_corpus" / "corpus_lock.json"
GATES = STUDY / "artifacts" / "dmr001c_gates" / "gate_report.json"
REGISTRATION = STUDY / "DMR_001C_PRE_REGISTRATION.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Corpus construction
# ---------------------------------------------------------------------------


def test_episode_text_is_the_cache_key_format() -> None:
    assert episode_text("hi", "there") == "User: hi\nAssistant: there"


def test_irregular_sessions_are_rejected_not_repaired() -> None:
    good = [
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
    ]
    assert strict_exchanges(good) == [("a", "b")]
    assert strict_exchanges(good[:1]) is None
    assert strict_exchanges([{"role": "assistant", "content": "b"}, *good]) is None
    assert strict_exchanges(good + [{"role": "user", "content": "c"}]) is None


def test_identity_is_content_addressed_and_position_bearing() -> None:
    token = stream_token("q1")
    pair = pair_sha256("same", "same")
    assert episode_identity(token, 3, pair) != episode_identity(token, 4, pair)
    assert episode_identity(token, 3, pair) == episode_identity(token, 3, pair)
    assert stream_token("q1") != stream_token("q2")


def test_the_selection_slice_does_not_overlap_earlier_studies() -> None:
    """EC-001 registered ranks 1-20 and SAL-001 ranks 21-30."""
    assert RANK_LOW == 31 and RANK_HIGH == 40


# ---------------------------------------------------------------------------
# Committed corpus
# ---------------------------------------------------------------------------


def test_committed_corpus_has_the_registered_shape() -> None:
    manifest = load(CORPUS)
    counts = manifest["counts"]
    assert manifest["dataset"]["sha256"] == DATASET_SHA256
    assert counts["streams"] == 50
    assert counts["episodes"] == 11453
    assert counts["seams"] == 2128
    assert manifest["excluded"]["uncached_episodes"] == 0
    assert manifest["excluded"]["streams_below_minimum"] == []


def test_every_stream_token_is_distinct() -> None:
    manifest = load(CORPUS)
    tokens = [row["stream_token"] for row in manifest["streams"]]
    assert len(set(tokens)) == len(tokens)


def test_the_registration_records_the_base_rate_before_the_run() -> None:
    """The bar-shaping facts must predate the result, not explain it after."""
    text = REGISTRATION.read_text(encoding="utf-8")
    assert "18.6%" in text
    assert "structurally cannot recover seams that fall closer together than 5" in text
    assert "expected to be the harder of the two" in text


# ---------------------------------------------------------------------------
# Committed result
# ---------------------------------------------------------------------------


def test_the_former_was_blind_to_every_session_seam() -> None:
    report = load(GATES)
    assert sum(row["hard_boundaries"] for row in report["streams"]) == 0


def test_g4_passed_and_g5_failed_on_its_registered_statistic() -> None:
    report = load(GATES)
    by_gate = {gate["gate"]: gate for gate in report["verdict"]["gates"]}
    assert by_gate["G4"]["passed"] and by_gate["G4"]["evaluated"]
    assert by_gate["G5"]["evaluated"] and not by_gate["G5"]["passed"]
    assert report["verdict"]["disposition"] == "NO_BOUNDARY_EVIDENCE"
    assert report["verdict"]["disposition"] != PASS_DISPOSITION


def test_stability_holds_across_every_stream() -> None:
    report = load(GATES)
    summary = report["summary"]
    assert summary["fire_rate_p95_p05_ratio"] <= BARS["G4"]["max_p95_p05_ratio"]
    assert all(row["adaptive_boundaries"] > 0 for row in report["streams"])


def test_precision_is_reported_but_is_not_the_gate() -> None:
    """The failure stands on F1. Precision is characterization, not a substitute."""
    report = load(GATES)
    summary = report["summary"]
    assert summary["macro_precision"] > 0.8
    assert summary["macro_precision"] > summary["c_pair_macro_precision"] * 4
    best = summary["best_periodic"]
    assert summary["macro_f1"] < summary["periodic_macro_f1"][best]
    g5 = next(g for g in report["verdict"]["gates"] if g["gate"] == "G5")
    assert any("macro F1 margin" in check["check"] for check in g5["checks"])


def test_a_dense_base_rate_makes_frequent_firing_score_well() -> None:
    """The registration defect, asserted so it cannot be quietly forgotten."""
    report = load(GATES)
    summary = report["summary"]
    assert summary["seam_base_rate"] > 0.15
    assert summary["periodic_macro_f1"]["C_PERIODIC_2"] > summary["macro_f1"]
    assert summary["c_pair_macro_precision"] == pytest.approx(
        summary["seam_base_rate"], abs=0.02
    )


def test_all_registered_periodic_controls_were_run() -> None:
    report = load(GATES)
    assert set(report["summary"]["periodic_macro_f1"]) == {
        f"C_PERIODIC_{period}" for period in PERIODS
    }
    assert 5 in PERIODS and 6 in PERIODS


def test_the_cap_never_bound_and_nothing_degenerated() -> None:
    report = load(GATES)
    assert sum(row["capped_closures"] for row in report["streams"]) == 0
    assert all(row["singleton_fraction"] == 0.0 for row in report["streams"])
    assert report["summary"]["max_event_size_observed"] < 128

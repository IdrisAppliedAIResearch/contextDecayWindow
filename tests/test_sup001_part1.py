from __future__ import annotations

import json

from src.analysis.sup001_benchmark import build
from src.analysis.sup001_part1 import (
    build_ledger,
    failure_witnesses,
    ledger_digest,
    read_purity,
)


def test_full_registered_transition_distribution() -> None:
    mechanism, _key = build()
    ledger, transitions = build_ledger(mechanism)
    assert len(transitions) == 192
    assert transitions[63]["distribution"] == {
        "record_count": 64,
        "lineage_count": 64,
        "accessible_count": 64,
        "silent_count": 0,
    }
    assert transitions[-1]["distribution"] == {
        "record_count": 192,
        "lineage_count": 64,
        "accessible_count": 64,
        "silent_count": 128,
    }


def test_all_registered_degenerate_states_fail_closed() -> None:
    mechanism, _key = build()
    ledger, _transitions = build_ledger(mechanism)
    failures = failure_witnesses(mechanism, ledger)
    assert len(failures) == 8
    assert all(row["status"] == "PASS" for row in failures)


def test_reads_are_repeatable_and_leave_state_unchanged() -> None:
    mechanism, _key = build()
    ledger, _transitions = build_ledger(mechanism)
    population = [
        {"episode_sha256": row["episode_sha256"], "cosine": 1.0 - index / 1000}
        for index, row in enumerate(mechanism["episodes"])
    ]
    control = {"queries": [{"population": population} for _ in mechanism["queries"]]}
    before = ledger_digest(ledger)
    report = read_purity(mechanism, control, ledger)
    assert report["state_unchanged"]
    assert report["natural_reads_identity_equal"]
    assert report["lineage_reads_identity_equal"]
    assert ledger_digest(ledger) == before

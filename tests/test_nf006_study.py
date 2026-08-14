from __future__ import annotations

from analysis.nf006_study import NF006Stop, _require_committed, mechanism_violations


def test_leakage_audit_detects_planted_import() -> None:
    assert not mechanism_violations("import hashlib\nvalue = 1\n")
    assert mechanism_violations("import analysis.nf006_measurement\n")
    assert mechanism_violations("ATOMIC_ITEMS = ()\n")


def test_ordering_gate_fails_for_absent_selection(tmp_path) -> None:
    try:
        _require_committed(tmp_path / "not_committed.json")
    except (NF006Stop, ValueError):
        pass
    else:
        raise AssertionError("An absent selection seal must fail closed")

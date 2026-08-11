from __future__ import annotations

from pathlib import Path

from src.analysis.sup001_preflight import source_leakage, synthetic_reachability


def test_every_gate_and_stop_disposition_is_reachable() -> None:
    report = synthetic_reachability()
    assert report["all_reachable"]
    assert set(report["observed"].values()) == {
        "INTEGRITY_STOP",
        "CURRENT_VALUE_NOT_SURFACED",
        "UNCHANGED_FACT_REGRESSION",
        "LINEAGE_OR_SILENCE_FAILURE",
        "PROVENANCE_OR_INVARIANT_FAILURE",
        "SUPERSESSION_OFFLINE_ELIGIBLE",
    }


def test_leakage_scan_rejects_planted_forbidden_reference(tmp_path: Path) -> None:
    clean = tmp_path / "clean.py"
    clean.write_text("import hashlib\nVALUE = 1\n", encoding="utf-8")
    assert source_leakage((clean,))["pass"]
    planted = tmp_path / "planted.py"
    planted.write_text("KEY = 'SEALED_KEY_DO_NOT_OPEN'\n", encoding="utf-8")
    result = source_leakage((planted,))
    assert not result["pass"]
    assert result["violations"]

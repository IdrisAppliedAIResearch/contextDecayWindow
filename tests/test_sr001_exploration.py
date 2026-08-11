from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.analysis.sr001_exploration import canonical_digest, compare, source_audit


def test_component_source_audit_passes() -> None:
    assert source_audit()["status"] == "PASS"


def test_canonical_digest_ignores_mapping_order() -> None:
    assert canonical_digest({"a": 1, "b": 2}) == canonical_digest({"b": 2, "a": 1})


def test_compare_requires_equal_deterministic_digest(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "exploration.json").write_text(json.dumps({"deterministic_digest": "same"}), encoding="utf-8")
    (second / "exploration.json").write_text(json.dumps({"deterministic_digest": "same"}), encoding="utf-8")
    assert compare(first, second, tmp_path / "comparison.json")["status"] == "PASS"


def test_compare_rejects_mismatch(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "exploration.json").write_text(json.dumps({"deterministic_digest": "one"}), encoding="utf-8")
    (second / "exploration.json").write_text(json.dumps({"deterministic_digest": "two"}), encoding="utf-8")
    with pytest.raises(AssertionError):
        compare(first, second, tmp_path / "comparison.json")

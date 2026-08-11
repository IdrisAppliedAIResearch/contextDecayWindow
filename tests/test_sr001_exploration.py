from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.analysis.sr001_exploration import (
    anchor_committed_display_scores,
    canonical_digest,
    compare,
    source_audit,
)
from src.retrieval_bakeoff.models import Candidate, RankedCandidate


def test_component_source_audit_passes() -> None:
    assert source_audit()["status"] == "PASS"


def test_canonical_digest_ignores_mapping_order() -> None:
    assert canonical_digest({"a": 1, "b": 2}) == canonical_digest({"b": 2, "a": 1})


def test_score_anchor_changes_display_value_without_reordering() -> None:
    candidates = [
        Candidate(candidate_id=value, source_episode_id=value, turn_number=index, unit_type="episode")
        for index, value in enumerate(("a", "b"), start=1)
    ]
    ranked = [
        RankedCandidate(candidate=candidates[0], score=0.50000006),
        RankedCandidate(candidate=candidates[1], score=0.4),
    ]
    anchored, audit = anchor_committed_display_scores(
        ranked, {"selected": [{"candidate_id": "a", "score": 0.49999999}]}
    )
    assert [row.candidate.source_episode_id for row in anchored] == ["a", "b"]
    assert anchored[0].score == 0.49999999
    assert audit["source_order_unchanged"] is True


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

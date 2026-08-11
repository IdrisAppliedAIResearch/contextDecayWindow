from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.analysis.ta001_exploration import compare, run


def test_part1_runs_label_blind_and_reproduces_control(tmp_path: Path) -> None:
    result = run(tmp_path / "one", "test")
    assert result["eligibility"]["status"] == "PASS"
    assert result["q11_reproduction"]["status"] == "PASS"
    assert result["calls"] == {"embedding": 0, "model_generation": 0}
    assert result["query_cache_hits"] == 24
    assert len(result["records"]) == 25
    assert all(len(row["C0"]["candidate_content_sha256"]) == 15 for row in result["records"])
    assert all(len(row["T1"]["candidate_content_sha256"]) == 15 for row in result["records"])


def test_part1_fresh_process_digest_and_overwrite_refusal(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    left = run(first, "one")
    right = run(second, "two")
    assert left["deterministic_digest"] == right["deterministic_digest"]
    comparison = compare(first, second, tmp_path / "comparison.json")
    assert comparison["status"] == "PASS"
    with pytest.raises(FileExistsError):
        run(first, "again")


def test_exploration_artifact_has_no_measurement_fields(tmp_path: Path) -> None:
    output = tmp_path / "run"
    run(output, "boundary")
    data = json.loads((output / "exploration.json").read_text(encoding="utf-8"))
    serialized = json.dumps(data["records"], sort_keys=True).lower()
    for forbidden in ("required_fact", "fact_recall", "available", "required_domains"):
        assert forbidden not in serialized

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.analysis.ba001_benchmark_causal_audit import (
    LabelBoundary,
    chain_disposition,
    run,
    sha256_file,
    verify_frozen_inputs,
)


def _cell(candidate_facts: set[str], packed_facts: set[str]) -> dict:
    def rows(values: set[str]) -> list[dict]:
        return [
            {
                "domain": value.split(":", 1)[0],
                "item": value.split(":", 1)[1],
                "available": True,
            }
            for value in sorted(values)
        ]

    return {
        "candidate_items": rows(candidate_facts),
        "packed_items": rows(packed_facts),
    }


@pytest.mark.parametrize(
    ("a0", "a1", "expected"),
    [
        (
            _cell({"civil:a"}, {"civil:a"}),
            _cell({"civil:a", "art:b"}, {"civil:a"}),
            "CHAIN_DISCOVERY_GAIN",
        ),
        (
            _cell({"civil:a", "art:b"}, {"civil:a"}),
            _cell({"civil:a", "art:b"}, {"civil:a", "art:b"}),
            "CHAIN_PACKING_ONLY_GAIN",
        ),
        (
            _cell({"civil:a"}, {"civil:a"}),
            _cell({"civil:a"}, {"civil:a"}),
            "CHAIN_NO_GAIN",
        ),
        (
            _cell({"civil:a", "art:b"}, {"civil:a"}),
            _cell({"civil:a"}, {"civil:a"}),
            "CHAIN_REGRESSION",
        ),
    ],
)
def test_chain_dispositions_are_reachable(a0: dict, a1: dict, expected: str) -> None:
    assert chain_disposition(a0, a1) == expected


def test_label_boundary_rejects_early_measurement() -> None:
    boundary = LabelBoundary()
    with pytest.raises(RuntimeError, match="before identities were sealed"):
        boundary.require_open()
    digest = boundary.seal(("a" * 64, "b" * 64))
    assert boundary.require_open() == digest


def test_frozen_inventory_is_exact() -> None:
    inventory = verify_frozen_inputs()
    assert inventory
    assert {row["status"] for row in inventory} == {"PASS"}


def test_end_to_end_registered_dispositions(tmp_path: Path) -> None:
    results = run(tmp_path)

    assert results["primary_disposition"] == "CHAIN_PACKING_ONLY_GAIN"
    d1 = {row["arm"]: row for row in results["d1_chain_decomposition"]["rows"]}
    assert d1["A0"]["candidate_fact_count"] == 9
    assert d1["A1"]["candidate_fact_count"] == 9
    assert d1["A0"]["candidate_facts"] == d1["A1"]["candidate_facts"]
    assert d1["A0"]["packed_fact_count"] == 7
    assert d1["A1"]["packed_fact_count"] == 9

    d2 = results["d2_adjacency_opportunity"]
    assert d2["disposition"] == "ADJACENCY_OPPORTUNITY_PRESENT"
    assert d2["1"]["turn_55_reachable"] is True
    assert d2["1"]["new_art_fact_count"] == 4
    assert d2["interpretation_ceiling"] == "ORACLE_REACHABILITY_ONLY"

    d3 = results["d3_representation"]
    assert d3["disposition"] == "ENUMERATION_GRANULARITY_GAP"
    assert d3["query_outcomes"] == {"gains": 10, "losses": 0, "ties": 14}

    d4 = results["d4_art_recall"]
    assert "STORED_BUT_NOT_BROADLY_CUED" in d4["dispositions"]
    assert "DIRECT_CUE_RECALL_OBSERVED" in d4["dispositions"]
    assert d4["prior_conflict_status"] == "NOT_IDENTIFIED"
    assert results["calls"] == {
        "model_generation": 0,
        "embedding": 0,
        "live_runs": 0,
    }

    preflight = json.loads((tmp_path / "preflight.json").read_text(encoding="utf-8"))
    assert preflight["status"] == "PASS"
    assert all(row["pass"] for row in preflight["checks"].values())


def test_two_process_outputs_are_content_identical(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_result = run(first)
    second_result = run(second)

    assert first_result["result_digest_sha256"] == second_result["result_digest_sha256"]
    first_files = {
        path.name: sha256_file(path)
        for path in first.iterdir()
        if path.name != "manifest.json"
    }
    second_files = {
        path.name: sha256_file(path)
        for path in second.iterdir()
        if path.name != "manifest.json"
    }
    assert first_files == second_files

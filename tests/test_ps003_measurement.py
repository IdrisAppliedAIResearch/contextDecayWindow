from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from src.analysis.ps003_measurement import (
    MEASUREMENT_SOURCE,
    PS003_MECHANISM_SOURCE,
    episode_matches_fact,
    execute_ordered_gates,
    load_episodes,
    measurement_prerequisites,
)


def test_measurement_requires_exact_committed_pass_preflight() -> None:
    result = measurement_prerequisites()

    assert result["status"] == "PASS"
    assert result["preflight_sha256"].startswith("d70e2a20")
    assert result["selected_digest"].startswith("70b23e1d")


def test_measurement_rejects_missing_or_failing_preflight(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(RuntimeError, match="required"):
        measurement_prerequisites(missing)

    failing = tmp_path / "failing.json"
    failing.write_text(json.dumps({"status": "FAIL"}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="not passing"):
        measurement_prerequisites(failing)


def test_same_episode_match_requires_terms_turn_and_source_role() -> None:
    episode = {
        "turn_number": 12,
        "user_message": "The bridge has a 100-year service life.",
        "assistant_message": "Acknowledged.",
    }
    fact = {
        "required_terms": ["100-year service life"],
        "source_turns": [12],
        "source_role": "user",
    }

    assert episode_matches_fact(episode, fact)
    assert not episode_matches_fact(dict(episode, turn_number=13), fact)
    assert not episode_matches_fact(
        dict(episode, user_message="No term here", assistant_message="100-year service life"),
        fact,
    )


def test_measurement_episode_inventory_has_stable_content_identities() -> None:
    episodes = load_episodes()

    assert len(episodes) == 119
    assert len({row["content_sha256"] for row in episodes}) == 119
    assert all(len(row["content_sha256"]) == 64 for row in episodes)


def test_ordered_gates_stop_at_first_failure() -> None:
    calls: list[str] = []

    def stage(name: str, status: str):
        def run() -> dict[str, str]:
            calls.append(name)
            return {"status": status}

        return run

    results = execute_ordered_gates(
        [
            ("G1", stage("G1", "PASS")),
            ("G2", stage("G2", "PASS")),
            ("G3", stage("G3", "FAIL")),
            ("G4", stage("G4", "PASS")),
            ("G5", stage("G5", "PASS")),
        ]
    )

    assert calls == ["G1", "G2", "G3"]
    assert results["G4"] == "NOT_REACHED"
    assert results["G5"] == "NOT_REACHED"


def test_mechanism_cannot_import_measurement_module() -> None:
    tree = ast.parse(PS003_MECHANISM_SOURCE.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert "src.analysis.ps003_measurement" not in imports
    assert MEASUREMENT_SOURCE != PS003_MECHANISM_SOURCE

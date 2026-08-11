from __future__ import annotations

from pathlib import Path

import pytest

from src.analysis.ta001_measurement import evaluate_gates, fact_available, run
from src.analysis.ta001_exploration import load_episodes


def q11_fixture(c0_candidate: int = 7, c0_packed: int = 7, t1_candidate: int = 11, t1_packed: int = 11, art: int = 4) -> dict:
    return {
        "C0": {"candidate_count": 15, "delivered_chars": 31_000, "candidate_fact_count": c0_candidate, "packed_fact_count": c0_packed, "candidate_per_domain": {"art": 0}, "packed_per_domain": {"art": 0}},
        "T1": {"candidate_count": 15, "delivered_chars": 31_000, "candidate_fact_count": t1_candidate, "packed_fact_count": t1_packed, "candidate_per_domain": {"art": art}, "packed_per_domain": {"art": art}},
    }


def query_fixture(direction: str = "TIE") -> dict:
    values = {"GAIN": (0.0, 1.0), "LOSS": (1.0, 0.0), "TIE": (1.0, 1.0)}[direction]
    return {"query_id": "q", "direction": direction, "C0": {"candidate_count": 15, "delivered_chars": 31_000, "packed_recall": values[0]}, "T1": {"candidate_count": 15, "delivered_chars": 31_000, "packed_recall": values[1]}}


def aggregates(c0: float = 1.0, t1: float = 1.0) -> list[dict]:
    return [{"group_type": "class", "group": "lookup", "C0_macro_packed_recall": c0, "T1_macro_packed_recall": t1}]


@pytest.mark.parametrize(
    ("q11", "queries", "groups", "integrity", "expected"),
    [
        (q11_fixture(), [query_fixture()], aggregates(), False, "INTEGRITY_STOP"),
        ({**q11_fixture(), "T1": {**q11_fixture()["T1"], "candidate_count": 14}}, [query_fixture()], aggregates(), True, "UNMATCHED_OPPORTUNITY"),
        (q11_fixture(t1_candidate=7, t1_packed=7), [query_fixture()], aggregates(), True, "NO_BROAD_GAIN"),
        (q11_fixture(art=3), [query_fixture()], aggregates(), True, "ART_NOT_DELIVERED"),
        (q11_fixture(), [query_fixture("LOSS")], aggregates(1.0, 0.0), True, "TARGETED_REGRESSION"),
        (q11_fixture(), [query_fixture()], aggregates(), True, "ADJACENCY_BRIDGE_OFFLINE_ELIGIBLE"),
    ],
)
def test_every_disposition_is_reachable(q11: dict, queries: list[dict], groups: list[dict], integrity: bool, expected: str) -> None:
    assert evaluate_gates(q11, queries, groups, integrity_pass=integrity)["disposition"] == expected


def test_fact_match_requires_source_turn_and_all_terms() -> None:
    episode = load_episodes(1)[0]
    text = f"{episode['user_message']} {episode['assistant_message']}"
    terms = [word for word in text.split() if len(word) > 4][:2]
    fact = {"source_turns": [1], "required_terms": terms}
    assert fact_available(fact, [episode])[0]
    assert not fact_available({**fact, "source_turns": [2]}, [episode])[0]
    assert not fact_available({**fact, "required_terms": [*terms, "absent-token"]}, [episode])[0]


def test_registered_measurement_runs_and_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "measurement"
    result = run(output)
    assert result["status"] == "COMPLETE"
    assert len(result["targeted_queries"]) == 24
    assert result["q11"]["C0"]["packed_fact_count"] == 7
    with pytest.raises(FileExistsError):
        run(output)

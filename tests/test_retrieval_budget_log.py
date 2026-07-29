"""Study 007 S7-T-011 — retrieval_budget.csv.

This log is what makes Bar 1's attribution checkable: a breadth pass counts as a
retrieval-budget effect only if the probe-turn row shows four-domain coverage.
Verified on synthetic data here, before the ablation is run.
"""

import csv
import json
import os

import pytest

from src.memory.arbitration import arbitrate_budgeted
from src.memory.retrieval_budget import rendered_block_cost, rendered_cost
from src.observability.file_writer import FileWriter
from src.observability.run_config import RunConfig
from src.observability.turn_record import TurnRecord
from src.runners.iterative_runner import IterativeRunner


HEADER = [
    "turn", "b_ltm", "k_min", "floor_ranking", "fill_cap", "render_mode",
    "topics_present", "topic_count",
    "floor_selected_per_topic", "floor_selected", "fill_selected",
    "fill_selected_per_topic", "fill_cap_skips", "containment_drops",
    "refills", "collapsed_to_episode", "ltm_chars_used",
    "ltm_content_chars", "block_overhead_chars",
    "ltm_records_used", "budget_utilization", "chars_per_topic", "selection",
]


def ltm(episode_id: str, topic: str, similarity: float, chars: int = 200) -> dict:
    return {
        "id": episode_id,
        "distilled_id": f"d-{episode_id}",
        "topic_id": topic,
        "topic_label": topic,
        "similarity": similarity,
        "user_message": "",
        "assistant_message": "x" * chars,
        "turn_number": 2,
    }


@pytest.fixture
def writer(tmp_path):
    config = RunConfig(
        condition="iterative",
        run_id="run_001",
        output_dir=str(tmp_path / "condition_c"),
        study_dir=str(tmp_path),
    )
    file_writer = FileWriter(config)
    file_writer.init_run()
    return file_writer, tmp_path / "condition_c" / "logs" / "retrieval_budget.csv"


def read_rows(path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def record_for(arbitration, turn: int = 120) -> TurnRecord:
    return TurnRecord(
        turn_number=turn,
        condition="iterative",
        user_message="probe",
        **IterativeRunner._budget_fields(arbitration),
    )


def test_header_is_written_on_initialize(writer):
    _, path = writer
    assert path.exists()
    with open(path, encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == HEADER


def test_one_row_per_turn_with_all_fields(writer):
    file_writer, path = writer
    candidates = [
        ltm(f"{topic}-{i}", topic, 0.9 - i * 0.01)
        for topic in ("civil", "art", "monetary", "marine")
        for i in range(5)
    ]
    for turn in (118, 119, 120):
        arbitration = arbitrate_budgeted(
            [], candidates, set(), ltm_budget=4000, ltm_k_min=2
        )
        file_writer.write_turn(record_for(arbitration, turn))

    rows = read_rows(path)
    assert [int(row["turn"]) for row in rows] == [118, 119, 120]
    for row in rows:
        assert set(row) == set(HEADER)
        assert row["b_ltm"] == "4000"
        assert row["k_min"] == "2"


def test_per_domain_split_sums_to_chars_used(writer):
    file_writer, path = writer
    candidates = [
        ltm(f"{topic}-{i}", topic, 0.9 - i * 0.01, chars=150 + i)
        for topic in ("civil", "art", "marine")
        for i in range(6)
    ]
    arbitration = arbitrate_budgeted(
        [], candidates, set(), ltm_budget=1800, ltm_k_min=2
    )
    file_writer.write_turn(record_for(arbitration))

    row = read_rows(path)[0]
    split = json.loads(row["chars_per_topic"])
    assert (
        sum(split.values())
        + int(row["block_overhead_chars"])
        == int(row["ltm_chars_used"])
    )
    assert int(row["ltm_chars_used"]) <= 1800


def test_four_domain_coverage_is_visible_in_the_row(writer):
    """The Bar 1 attribution check, exercised on the shape it will read."""
    file_writer, path = writer
    candidates = [
        ltm("civil-0", "civil", 0.90),
        ltm("civil-1", "civil", 0.89),
        ltm("art-0", "art", 0.20),
        ltm("monetary-0", "monetary", 0.15),
        ltm("marine-0", "marine", 0.10),
    ]
    arbitration = arbitrate_budgeted(
        [], candidates, set(), ltm_budget=16_000, ltm_k_min=1
    )
    file_writer.write_turn(record_for(arbitration))

    row = read_rows(path)[0]
    assert int(row["topic_count"]) == 4
    assert set(json.loads(row["topics_present"])) == {
        "civil", "art", "monetary", "marine"
    }
    assert set(json.loads(row["chars_per_topic"])) == {
        "civil", "art", "monetary", "marine"
    }


def test_phase_labels_are_correct_against_a_hand_checked_turn(writer):
    """civil-0 and marine-0 are each topic's best, so both are floor at k_min=1.

    Everything else admitted is fill, in strict similarity order.
    """
    file_writer, path = writer
    candidates = [
        ltm("civil-0", "civil", 0.90, chars=100),
        ltm("civil-1", "civil", 0.80, chars=100),
        ltm("civil-2", "civil", 0.70, chars=100),
        ltm("marine-0", "marine", 0.05, chars=100),
    ]
    budget = rendered_block_cost(candidates)
    arbitration = arbitrate_budgeted(
        [], candidates, set(), ltm_budget=budget, ltm_k_min=1
    )
    file_writer.write_turn(record_for(arbitration))

    row = read_rows(path)[0]
    selection = {item["episode_id"]: item for item in json.loads(row["selection"])}

    assert selection["civil-0"]["phase"] == "floor"
    assert selection["marine-0"]["phase"] == "floor"
    assert selection["civil-1"]["phase"] == "fill"
    assert selection["civil-2"]["phase"] == "fill"
    assert row["floor_selected"] == "2"
    assert row["fill_selected"] == "2"
    assert json.loads(row["floor_selected_per_topic"]) == {"civil": 1, "marine": 1}


def test_selection_carries_ids_topics_similarities_and_chars(writer):
    file_writer, path = writer
    arbitration = arbitrate_budgeted(
        [], [ltm("ep1", "civil", 0.123456789, chars=250)], set(),
        ltm_budget=16_000, ltm_k_min=1,
    )
    file_writer.write_turn(record_for(arbitration))

    item = json.loads(read_rows(path)[0]["selection"])[0]
    assert item["episode_id"] == "ep1"
    assert item["distilled_id"] == "d-ep1"
    assert item["topic"] == "civil"
    assert item["similarity"] == pytest.approx(0.123457)
    assert item["chars"] == rendered_cost(
        ltm("ep1", "civil", 0.123456789, chars=250)
    )


def test_containment_drops_and_refills_are_logged(writer):
    file_writer, path = writer
    candidates = [ltm(f"ep{i}", "civil", 0.9 - i * 0.1, chars=400) for i in range(3)]
    budget = rendered_block_cost(candidates[1:])
    arbitration = arbitrate_budgeted(
        [], candidates, {"ep0"}, ltm_budget=budget, ltm_k_min=0
    )
    file_writer.write_turn(record_for(arbitration))

    row = read_rows(path)[0]
    assert int(row["containment_drops"]) == 1
    assert int(row["ltm_chars_used"]) == budget


def test_collapsed_records_are_logged(writer):
    file_writer, path = writer
    candidates = [
        ltm("ep1", "civil", 0.90),
        ltm("ep1", "civil", 0.80),
        ltm("ep1", "civil", 0.70),
    ]
    arbitration = arbitrate_budgeted(
        [], candidates, set(), ltm_budget=16_000, ltm_k_min=0
    )
    file_writer.write_turn(record_for(arbitration))

    row = read_rows(path)[0]
    assert int(row["collapsed_to_episode"]) == 2
    assert int(row["ltm_records_used"]) == 1


def test_utilization_is_reported(writer):
    file_writer, path = writer
    arbitration = arbitrate_budgeted(
        [], [ltm("ep1", "civil", 0.9, chars=400)], set(),
        ltm_budget=1000, ltm_k_min=1,
    )
    file_writer.write_turn(record_for(arbitration))
    expected = rendered_block_cost([ltm("ep1", "civil", 0.9, chars=400)])
    assert read_rows(path)[0]["budget_utilization"] == f"{expected / 1000:.4f}"


def test_control_arm_writes_no_rows(writer):
    """The count-based policy leaves budget_active False and the log empty."""
    file_writer, path = writer
    file_writer.write_turn(
        TurnRecord(turn_number=1, condition="iterative", user_message="x")
    )
    assert read_rows(path) == []


def test_empty_ltm_turn_still_writes_a_row(writer):
    """Turns before the first dream pass must be visible as zero, not missing."""
    file_writer, path = writer
    arbitration = arbitrate_budgeted([], [], set(), ltm_budget=16_000, ltm_k_min=3)
    file_writer.write_turn(record_for(arbitration, turn=5))

    row = read_rows(path)[0]
    assert int(row["topic_count"]) == 0
    assert int(row["ltm_chars_used"]) == rendered_block_cost([])
    assert int(row["block_overhead_chars"]) == rendered_block_cost([])
    assert int(row["ltm_records_used"]) == 0
    assert json.loads(row["selection"]) == []

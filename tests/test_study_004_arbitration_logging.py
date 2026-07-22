import csv
import json

from src.observability.file_writer import FileWriter
from src.observability.run_config import RunConfig
from src.observability.turn_record import TurnRecord


def test_arbitration_and_ltm_provenance_rows_are_faithful(tmp_path):
    output_dir = tmp_path / "run" / "iterative"
    writer = FileWriter(RunConfig(
        condition="iterative",
        run_id="synthetic",
        output_dir=str(output_dir),
        study_dir=str(tmp_path),
    ))
    writer.init_run()
    record = TurnRecord(
        turn_number=12,
        condition="iterative",
        user_message="breadth query",
        arbitration_stm_candidates=2,
        arbitration_ltm_candidates=2,
        arbitration_duplicates_removed=1,
        arbitration_final_set_size=3,
        arbitration_ltm_in_final_set=2,
        arbitration_provenance_list=[
            {"episode_id": "both-1", "provenance": "both"},
            {"episode_id": "ltm-1", "provenance": "ltm"},
            {"episode_id": "stm-1", "provenance": "stm"},
        ],
        ltm_context_episodes=[{
            "id": "both-1",
            "turn_number": 2,
            "topic_label": "topic_a",
            "similarity": 0.91,
            "provenance": "both",
            "promoted_at_turn": 7,
            "trigger_type": "weighted_threshold",
            "triggered_filter": None,
        }, {
            "id": "ltm-1",
            "turn_number": 5,
            "topic_label": "topic_b",
            "similarity": 0.82,
            "provenance": "ltm",
            "promoted_at_turn": 10,
            "trigger_type": "all_or_nothing",
            "triggered_filter": "novelty",
        }],
    )

    writer.write_turn(record)

    with open(
        output_dir / "logs" / "arbitration_events.csv",
        newline="",
        encoding="utf-8",
    ) as handle:
        arbitration_rows = list(csv.DictReader(handle))
    assert len(arbitration_rows) == 1
    assert arbitration_rows[0]["duplicates_removed"] == "1"
    assert json.loads(arbitration_rows[0]["provenance_list"])[0] == {
        "episode_id": "both-1",
        "provenance": "both",
    }

    with open(
        output_dir / "logs" / "ltm_context_episodes.csv",
        newline="",
        encoding="utf-8",
    ) as handle:
        ltm_rows = list(csv.DictReader(handle))
    assert len(ltm_rows) == 2
    assert ltm_rows[0]["promoted_at_turn"] == "7"
    assert ltm_rows[0]["trigger_type"] == "weighted_threshold"
    assert ltm_rows[1]["triggered_filter"] == "novelty"

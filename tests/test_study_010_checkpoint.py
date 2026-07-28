import hashlib
import json
import sqlite3
from pathlib import Path

from src.study.checkpoint import restore_checkpoint, write_checkpoint
from src.study.script_loader import load_script


ROOT = Path(__file__).parents[1]
STUDY = ROOT / "experiments" / "study_010"


def test_locked_artifact_hashes_and_script_shape():
    lock = json.loads((STUDY / "artifact_lock.json").read_text(encoding="utf-8"))
    for name, expected in lock["artifacts"].items():
        text = (STUDY / name).read_text(encoding="utf-8")
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        actual = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        assert actual == expected

    script = load_script(str(STUDY / "script_1000.json"), minimum_turns=1000)
    assert len(script["turns"]) == 1000
    assert len(script["rubric_turns"]) == 23
    assert script["interim_probe_turns"] == [
        250,
        251,
        252,
        500,
        501,
        502,
        750,
        751,
        752,
    ]
    assert script["probe_turn_start"] == 987
    assert script["probe_turn_end"] == 1000
    assert len([turn for turn in script["turns"] if turn.get("plant_stage")]) == 36


def test_checkpoint_restores_database_and_output_boundary(tmp_path):
    output = tmp_path / "run"
    logs = output / "logs"
    logs.mkdir(parents=True)
    turns = logs / "turns.jsonl"
    turns.write_text('{"turn": 1}\n', encoding="utf-8")

    conn = sqlite3.connect(output / "study.db")
    conn.execute("CREATE TABLE events (turn INTEGER)")
    conn.execute("INSERT INTO events VALUES (1)")
    conn.commit()

    checkpoint = write_checkpoint(
        output,
        conn,
        100,
        {"previous_episode_id": "episode-100"},
    )
    turns.write_text(
        turns.read_text(encoding="utf-8") + '{"turn": 101}\n',
        encoding="utf-8",
    )
    (logs / "partial.jsonl").write_text("partial", encoding="utf-8")
    conn.execute("INSERT INTO events VALUES (101)")
    conn.commit()
    conn.close()

    payload = restore_checkpoint(output, checkpoint)
    assert payload["turn"] == 100
    assert payload["state"]["previous_episode_id"] == "episode-100"
    assert turns.read_text(encoding="utf-8") == '{"turn": 1}\n'
    assert not (logs / "partial.jsonl").exists()

    restored = sqlite3.connect(output / "study.db")
    assert restored.execute("SELECT turn FROM events").fetchall() == [(1,)]
    # Deterministic continuation after restore must equal the uninterrupted
    # reference state for the same fixture turns.
    with turns.open("a", encoding="utf-8") as handle:
        handle.write('{"turn": 101}\n{"turn": 102}\n')
    restored.executemany("INSERT INTO events VALUES (?)", [(101,), (102,)])
    restored.commit()
    assert turns.read_text(encoding="utf-8") == (
        '{"turn": 1}\n{"turn": 101}\n{"turn": 102}\n'
    )
    assert restored.execute("SELECT turn FROM events").fetchall() == [
        (1,),
        (101,),
        (102,),
    ]
    restored.close()

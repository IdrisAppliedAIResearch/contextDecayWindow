import hashlib
import json
import re
from pathlib import Path

from src.memory.dream_engine import calculate_salience


ROOT = Path(__file__).resolve().parents[1]
STUDY_004_SCRIPT = ROOT / "experiments" / "study_004" / "script.json"
STUDY_005_SCRIPT = ROOT / "experiments" / "study_005" / "script.json"
SYNTHETIC_SCRIPT = (
    ROOT
    / "experiments"
    / "study_005"
    / "tests"
    / "synthetic_study005_script.json"
)
Q14_CRITERIA = ROOT / "experiments" / "study_004" / "q14_criteria.md"


def _normalized_turn_payload(path: Path) -> bytes:
    content = path.read_bytes().replace(b"\r\n", b"\n")
    marker = b'  "turns": [\n'
    start = content.index(marker) + len(marker)
    end = content.rindex(b"\n  ]")
    return content[start:end]


def test_study_005_turns_are_byte_identical_to_study_004():
    study_004 = _normalized_turn_payload(STUDY_004_SCRIPT)
    study_005 = _normalized_turn_payload(STUDY_005_SCRIPT)

    assert study_005 == study_004
    assert hashlib.sha256(study_005).hexdigest() == hashlib.sha256(
        study_004
    ).hexdigest()


def test_study_005_has_locked_cadence_and_q14():
    script = json.loads(STUDY_005_SCRIPT.read_text(encoding="utf-8"))
    criteria = Q14_CRITERIA.read_text(encoding="utf-8")
    locked_q14 = re.search(
        r"^> (Before we finish,.*)$",
        criteria,
        re.MULTILINE,
    ).group(1)

    assert script["study"] == "study_005"
    assert len(script["turns"]) == 121
    assert script["promotion_flush_turn"] == 111
    assert script["probe_turn_start"] == 112
    assert script["probe_turn_end"] == 121
    assert script["rubric_turns"] == list(range(112, 122))
    assert script["turns"][120] == {"turn": 121, "user": locked_q14}


def test_synthetic_fixture_covers_registered_mechanisms():
    script = json.loads(SYNTHETIC_SCRIPT.read_text(encoding="utf-8"))
    turns = script["turns"]
    sparse_turns = turns[5:9]
    probe_turns = turns[20:]

    assert script["fixture_only"] is True
    assert len(turns) == 30
    assert script["promotion_flush_turn"] == 20
    assert script["probe_turn_start"] == 21
    assert script["probe_turn_end"] == 30
    assert script["rubric_turns"][-1] == 30
    assert {
        turn["ground_truth_domain"] for turn in turns[:20]
    } == {
        "pulsar_timing",
        "acknowledgments",
        "orchid_germination",
        "maritime_treaty",
    }
    assert all(
        calculate_salience(turn["user"])[0] == 0
        for turn in sparse_turns
    )
    assert "AX-17" in turns[1]["user"] and "AX-17" in turns[2]["user"]
    assert "Breadth check" in probe_turns[0]["user"]
    assert "AX-17" in probe_turns[1]["user"]
    assert "DZ-53" in probe_turns[1]["user"]
    assert all(
        turn["ground_truth_domain"] == "probe"
        for turn in probe_turns
    )

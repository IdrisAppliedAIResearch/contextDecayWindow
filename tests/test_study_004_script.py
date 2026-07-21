import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDY_003_SCRIPT = ROOT / "experiments" / "study_003" / "script.json"
STUDY_004_SCRIPT = ROOT / "experiments" / "study_004" / "script.json"
Q14_CRITERIA = ROOT / "experiments" / "study_004" / "q14_criteria.md"
REGISTERED_PAYLOAD_SHA256 = (
    "d2260351c3de6ce88a9bfce16a92fbaaa4311aef7bfd50e589513c2f245de7f9"
)


def _normalized_turn_payload(path: Path, includes_q14: bool) -> bytes:
    content = path.read_bytes().replace(b"\r\n", b"\n")
    marker = b'  "turns": [\n'
    start = content.index(marker) + len(marker)
    if includes_q14:
        end = content.index(b',\n    {\n      "turn": 121', start)
    else:
        end = content.rindex(b"\n  ]")
    return content[start:end]


def test_turns_1_through_120_are_byte_identical_to_study_003():
    study_003 = _normalized_turn_payload(STUDY_003_SCRIPT, includes_q14=False)
    study_004 = _normalized_turn_payload(STUDY_004_SCRIPT, includes_q14=True)

    assert study_004 == study_003
    assert hashlib.sha256(study_004).hexdigest() == REGISTERED_PAYLOAD_SHA256


def test_q14_is_exact_locked_text_at_turn_121():
    script = json.loads(STUDY_004_SCRIPT.read_text(encoding="utf-8"))
    criteria = Q14_CRITERIA.read_text(encoding="utf-8")
    locked_text = re.search(
        r"^> (Before we finish,.*)$", criteria, re.MULTILINE
    ).group(1)

    assert len(script["turns"]) == 121
    assert script["turns"][120] == {"turn": 121, "user": locked_text}

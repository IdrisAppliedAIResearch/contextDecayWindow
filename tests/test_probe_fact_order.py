import json
from pathlib import Path

from scripts.check_probe_fact_order import audit


def write_fixture(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_probe_fact_order_passes_when_all_facts_precede_probe(tmp_path):
    script = write_fixture(
        tmp_path / "script.json",
        {
            "turns": [
                {"turn": 1, "user": "Lock Alpha and 42 units."},
                {"turn": 2, "user": "What were Alpha and 42 units?"},
            ]
        },
    )
    rubric = tmp_path / "rubric.md"
    rubric.write_text(
        "| Label | Turn | Type/domain | Expected locked items |\n"
        "|---|---:|---|---|\n"
        "| Q1 | 2 | breadth | Alpha + 42 units |\n",
        encoding="utf-8",
    )

    result = audit(script, rubric)

    assert result["result"] == "PASS"
    assert result["failure_count"] == 0


def test_probe_fact_order_fails_when_fact_is_planted_later(tmp_path):
    script = write_fixture(
        tmp_path / "script.json",
        {
            "turns": [
                {"turn": 1, "user": "Lock Alpha."},
                {"turn": 2, "user": "What were Alpha and Beta?"},
                {"turn": 3, "user": "Lock Beta."},
            ]
        },
    )
    rubric = tmp_path / "rubric.md"
    rubric.write_text(
        "| Label | Turn | Type/domain | Expected locked items |\n"
        "|---|---:|---|---|\n"
        "| Q1 | 2 | targeted | Alpha; Beta |\n",
        encoding="utf-8",
    )

    result = audit(script, rubric)

    assert result["result"] == "FAIL"
    assert result["failures"] == [
        {"label": "Q1", "probe_turn": 2, "unavailable_items": ["Beta"]}
    ]

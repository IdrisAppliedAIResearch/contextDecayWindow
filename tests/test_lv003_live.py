from __future__ import annotations

from analysis.lv003_live import READER_LIMIT, validate_answer_schedule


def _prompt_rows() -> list[dict]:
    return [{"comparison_key": "q"}]


def _answers(reason: str = "stop") -> list[dict]:
    return [
        {
            "comparison_key": "q",
            "arm": arm,
            "replicate": replicate,
            "response": {"done_reason": reason},
        }
        for replicate in range(5)
        for arm in ("FULL_CC80", "OPPORTUNITY")
    ]


def test_successor_uses_carried_reader_allowance() -> None:
    assert READER_LIMIT == 512


def test_complete_schedule_passes() -> None:
    result = validate_answer_schedule(_answers(), _prompt_rows())
    assert result["pass"]
    assert result["rows"] == 10


def test_truncation_is_preserved_and_stops() -> None:
    rows = _answers()
    rows[0]["response"]["done_reason"] = "length"
    result = validate_answer_schedule(rows, _prompt_rows())
    assert not result["pass"]
    assert result["truncated"] == 1


def test_duplicate_and_missing_schedule_stops() -> None:
    rows = _answers()
    rows[-1] = rows[0]
    result = validate_answer_schedule(rows, _prompt_rows())
    assert not result["pass"]
    assert result["duplicates"] == 1
    assert result["missing"] == 1

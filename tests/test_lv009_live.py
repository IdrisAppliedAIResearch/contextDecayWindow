from analysis.lv009_exploration import load_blind_population, ordered_schedule
from analysis.lv009_live import _read_prompts, _structural_checks, validate_answer_schedule


def test_registered_schedule_population_and_determinism() -> None:
    rows = load_blind_population()
    first = ordered_schedule(rows)
    assert first == ordered_schedule(rows)
    assert len(first) == 7_944
    assert len(set((key, arm) for key, arm, _ in first)) == 7_944


def test_sealed_prompt_structure() -> None:
    prompts = _read_prompts()
    checks = _structural_checks(prompts)
    assert checks["set_exact"] == 7_944
    assert checks["element_exact"] == 7_944
    assert checks["reminder_rows"] == 1_986
    assert checks["qeach_active_rows"] == 1_986


def test_incomplete_schedule_is_rejected() -> None:
    prompts = _read_prompts()
    result = validate_answer_schedule([], prompts)
    assert not result["pass"]
    assert result["missing"] == 7_944

from analysis.lv009_exploration import load_blind_population, ordered_schedule
from analysis.lv009_live import (
    JUDGE_SEEDS,
    _holm_rejections,
    _read_prompts,
    _structural_checks,
    blind_id,
    judge_prompt,
    validate_answer_schedule,
    validate_judgments,
)


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


def test_blind_ids_and_judge_prompt_are_frozen() -> None:
    key = "a" * 64
    assert len(blind_id(key, "PAIRWISE")) == 64
    assert blind_id(key, "PAIRWISE") != blind_id(key, "COMMUNITY")
    prompt = judge_prompt({"question": "Q?", "gold": "A", "answer": "A"})
    assert prompt.endswith("<think>\n</think>\nVERDICT:")


def test_judgment_validation_requires_three_registered_passes() -> None:
    surface = [{"blind_id": "x"}]
    rows = [
        {"blind_id": "x", "judge_pass": judge_pass, "seed": seed, "verdict": True, "stop_type": "stop"}
        for judge_pass, seed in enumerate(JUDGE_SEEDS)
    ]
    assert validate_judgments(rows, surface)["pass"]
    assert not validate_judgments(rows[:-1], surface)["pass"]


def test_holm_stops_after_first_non_rejection() -> None:
    assert _holm_rejections({"a": 0.004, "b": 0.009}) == {"a", "b"}
    assert _holm_rejections({"a": 0.011, "b": 0.0001}) == {"b"}

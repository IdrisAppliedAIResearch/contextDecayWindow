from __future__ import annotations

import json

import numpy as np
import pytest

from analysis.beam001_live import (
    bootstrap_interval,
    classify_disposition,
    extract_string_constant,
    parse_judge_body,
    render_judge_prompt,
    render_reader_prompt,
    sign_flip_p,
)


def response(content: str, finish_reason: str = "stop") -> dict:
    return {
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {"content": content, "refusal": None},
            }
        ]
    }


def disposition(**overrides: object) -> str:
    values = {
        "primary": 0.03,
        "primary_p": 0.01,
        "primary_low": 0.005,
        "primary_high": 0.05,
        "a0_difference": 0.0,
        "a0_lower": -0.005,
        "scale_primary": [0.0, 0.01, 0.02],
        "scale_a0": [-0.01, 0.0, 0.01],
        "category_primary": [0.0] * 10,
    }
    values.update(overrides)
    return classify_disposition(**values)


def test_extracts_exact_python_string_constant(tmp_path) -> None:
    source = tmp_path / "prompts.py"
    source.write_text('target = """\\nhello \\n"""\n', encoding="utf-8")
    assert extract_string_constant(source, "target") == "\nhello \n"


def test_prompt_rendering_resolves_all_registered_placeholders() -> None:
    assert render_reader_prompt("<context>|<question>", "Q", "C") == "C|Q"
    assert render_judge_prompt(
        "<question>|<rubric_item>|<llm_response>", "Q", "R", "A"
    ) == "Q|R|A"


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ('{"score":0.5,"reason":"partial"}', (0.5, "partial")),
        ('```json\n{"score": 1, "reason": "yes"}\n```', (1.0, "yes")),
        ('prefix {"score": 0, "reason": "no"} suffix', (0.0, "no")),
        ('{"score":0.25,"reason":"bad"}', None),
        ('{"score":1,"reason":""}', None),
        ('{"score":1,"reason":"yes","extra":1}', None),
        ("not json", None),
    ],
)
def test_judge_parser_is_bounded(content: str, expected: tuple[float, str] | None) -> None:
    assert parse_judge_body(response(content)) == expected


def test_judge_parser_rejects_non_stop() -> None:
    assert parse_judge_body(response('{"score":1,"reason":"yes"}', "length")) is None


def test_every_registered_disposition_is_reachable() -> None:
    assert disposition() == "WORKS"
    assert disposition(primary=0.01) == "GAIN_WITH_GUARDRAIL_FAILURE"
    assert disposition(a0_lower=-0.01) == "GAIN_WITH_GUARDRAIL_FAILURE"
    assert disposition(scale_primary=[-0.011, 0.0, 0.0]) == "GAIN_WITH_GUARDRAIL_FAILURE"
    assert disposition(category_primary=[-0.031] + [0.0] * 9) == "GAIN_WITH_GUARDRAIL_FAILURE"
    assert disposition(primary=-0.03, primary_low=-0.05, primary_high=-0.005) == "REGRESSES"
    assert disposition(
        primary=0.0,
        primary_p=1.0,
        primary_low=-0.01,
        primary_high=0.01,
        a0_difference=-0.02,
        a0_lower=-0.01,
    ) == "REGRESSES"
    assert disposition(primary=0.01, primary_p=0.2, primary_low=-0.01) == "NO_DEMONSTRATED_GAIN"
    assert disposition(primary=0.0, primary_p=1.0, primary_low=0.0) == "NO_DEMONSTRATED_GAIN"


def test_threshold_equalities_follow_registration() -> None:
    assert disposition(scale_primary=[-0.01, 0.0, 0.0]) == "WORKS"
    assert disposition(scale_a0=[-0.02, 0.0, 0.0]) == "WORKS"
    assert disposition(category_primary=[-0.03] + [0.0] * 9) == "WORKS"
    assert disposition(primary_p=0.05) == "WORKS"
    assert disposition(primary_low=0.0) == "GAIN_WITH_GUARDRAIL_FAILURE"


def test_statistics_are_seed_reproducible() -> None:
    differences = np.array([-0.1, 0.0, 0.2, 0.3], dtype=np.float64)
    assert sign_flip_p(differences, 1000, 7) == sign_flip_p(differences, 1000, 7)
    assert bootstrap_interval(differences, 1000, 8) == bootstrap_interval(
        differences, 1000, 8
    )
    low, high = bootstrap_interval(differences, 1000, 8)
    assert high is not None and low <= differences.mean() <= high


def test_json_score_values_round_trip() -> None:
    body = response(json.dumps({"score": 1.0, "reason": "complete"}))
    assert parse_judge_body(body) == (1.0, "complete")

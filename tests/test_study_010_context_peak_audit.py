from pathlib import Path

from src.analysis.study_010_context_peak_audit import (
    ASSISTANT_CUE,
    _audit_arm,
    _digest_mapping,
)


def _write_arm(root: Path, *, logged_tokens: int) -> Path:
    arm = root / "arm_l"
    (arm / "metrics").mkdir(parents=True)
    (arm / "constructed_prompts").mkdir()
    (arm / "metrics" / "context_sizes.csv").write_text(
        "turn,estimated_tokens,rule_token_estimate,k_token_estimate,"
        "n_token_estimate,total_episodes_in_context\n"
        f"1,{logged_tokens},0,0,0,0\n",
        encoding="utf-8",
    )
    (arm / "constructed_prompts" / "turn_001.txt").write_text(
        ("x" * 16) + ASSISTANT_CUE,
        encoding="utf-8",
    )
    return arm


def test_audit_arm_matches_serialized_prompt_before_assistant_cue(tmp_path):
    arm = _write_arm(tmp_path, logged_tokens=4)

    result = _audit_arm(arm)

    assert result["all_rows_match"]
    assert result["peak"] == {
        "turn": 1,
        "logged_estimated_tokens": 4,
        "recomputed_estimated_tokens": 4,
        "serialized_prompt_chars": 28,
        "estimated_prompt_chars": 16,
    }


def test_audit_arm_reports_metric_mismatch(tmp_path):
    arm = _write_arm(tmp_path, logged_tokens=3)

    result = _audit_arm(arm)

    assert not result["all_rows_match"]
    assert result["mismatches"] == [
        {
            "turn": 1,
            "has_expected_cue": True,
            "logged_estimated_tokens": 3,
            "recomputed_estimated_tokens": 4,
        }
    ]


def test_digest_mapping_is_order_independent():
    assert _digest_mapping({"a": "1", "b": "2"}) == _digest_mapping(
        {"b": "2", "a": "1"}
    )

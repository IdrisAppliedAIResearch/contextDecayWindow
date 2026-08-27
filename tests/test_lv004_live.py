from __future__ import annotations

from analysis.lv004_live import REPAIR_KEYS, REPAIR_LIMIT, merge_repaired, validate_repair_batch


def _original(arm: str, replicate: int, seed: int, prompt_tokens: int) -> dict:
    return {
        "comparison_key": "key", "sample_id": "conv-42", "source_index": 79,
        "arm": arm, "replicate": replicate, "prompt_sha256": f"p-{arm}",
        "response": {"text": "prefix", "seed": seed, "prompt_eval_count": prompt_tokens, "done_reason": "length"},
    }


def _repair(original: dict, text: str = "prefix completed", reason: str = "stop") -> dict:
    from analysis.lv004_live import _canonical_sha
    return {
        "comparison_key": original["comparison_key"], "sample_id": "conv-42", "source_index": 79,
        "arm": original["arm"], "replicate": original["replicate"], "prompt_sha256": original["prompt_sha256"],
        "original_response_sha256": _canonical_sha(original["response"]),
        "response": {"text": text, "seed": original["response"]["seed"], "prompt_eval_count": original["response"]["prompt_eval_count"], "done_reason": reason},
    }


def _batch() -> tuple[list[dict], list[dict]]:
    originals = [_original(arm, replicate, spec["seed"], spec["prompt_eval_count"]) for (arm, replicate), spec in REPAIR_KEYS.items()]
    return originals, [_repair(row) for row in originals]


def test_repair_limit_is_locked() -> None:
    assert REPAIR_LIMIT == 2048


def test_exact_prefix_preserving_batch_passes() -> None:
    originals, repairs = _batch()
    result = validate_repair_batch(originals, repairs)
    assert result["pass"]
    assert result["prefix_identity"]


def test_prefix_change_or_truncation_stops() -> None:
    originals, repairs = _batch()
    repairs[0]["response"]["text"] = "changed"
    assert not validate_repair_batch(originals, repairs)["pass"]
    repairs = [_repair(row) for row in originals]
    repairs[1]["response"]["done_reason"] = "length"
    assert not validate_repair_batch(originals, repairs)["pass"]


def test_unregistered_replacement_key_stops() -> None:
    originals, repairs = _batch()
    repairs[0]["replicate"] = 4
    assert not validate_repair_batch(originals, repairs)["pass"]


def test_merge_changes_only_two_registered_rows() -> None:
    originals, repairs = _batch()
    untouched = {"comparison_key": "other", "sample_id": "conv-41", "source_index": 1, "arm": "FULL_CC80", "replicate": 0, "response": {"text": "same", "done_reason": "stop"}}
    source = [untouched, *originals]
    merged = merge_repaired(source, repairs)
    assert merged[0] == untouched
    assert all(row["response"]["text"] == "prefix completed" for row in merged[1:])
    assert all(row["repair"]["num_predict"] == 2048 for row in merged[1:])

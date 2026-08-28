from __future__ import annotations

import ast
import gzip
import inspect
import json

import pytest

import analysis.beam001_exploration as exploration
from episodic._retrieval import retrieve_long_term


def test_exploration_has_no_outcome_import_and_anchor_is_bound() -> None:
    assert exploration._separation_gate() == {
        "planted_field_rejected": True,
        "forbidden_imports": [],
    }
    anchor = exploration._anchors()
    assert anchor["status"] == "PASS"
    assert anchor["selector_sha256"] == exploration.SELECTOR_SHA256
    assert anchor["tc014_opportunity"] == {
        "cache_hits": 2236,
        "cache_misses": 0,
        "checked": 871,
        "mismatches": 0,
    }


def test_checkpoint_resume_rejects_conflicting_duplicates(tmp_path, monkeypatch) -> None:
    checkpoint = tmp_path / "checkpoint.jsonl"
    monkeypatch.setattr(exploration, "CHECKPOINT_PATH", checkpoint)
    row = {"question_key": "q1", "arm": exploration.ARMS[0], "value": 1}
    exploration._append_checkpoint(row)
    exploration._append_checkpoint(row)
    assert exploration._load_checkpoints()[("q1", exploration.ARMS[0])] == row

    conflict = {**row, "value": 2}
    with checkpoint.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(conflict) + "\n")
    with pytest.raises(exploration.BeamExplorationError, match="Conflicting"):
        exploration._load_checkpoints()


def test_disjoint_shard_checkpoints_merge_by_stable_key(tmp_path, monkeypatch) -> None:
    checkpoint = tmp_path / "checkpoint.jsonl"
    monkeypatch.setattr(exploration, "CHECKPOINT_PATH", checkpoint)
    first = {"question_key": "q1", "arm": exploration.ARMS[0], "value": 1}
    second = {"question_key": "q2", "arm": exploration.ARMS[1], "value": 2}
    exploration._append_checkpoint(first, tmp_path / "checkpoint.shard-00.jsonl")
    exploration._append_checkpoint(second, tmp_path / "checkpoint.shard-01.jsonl")

    assert exploration._load_checkpoints() == {
        ("q1", exploration.ARMS[0]): first,
        ("q2", exploration.ARMS[1]): second,
    }


def test_invalid_parallel_and_conversation_shards_fail_before_work() -> None:
    with pytest.raises(exploration.BeamExplorationError, match="worker count"):
        exploration.parallel_run(1)
    with pytest.raises(exploration.BeamExplorationError, match="Invalid"):
        exploration._run_with_embedder({}, shard_index=2, shard_count=2)


def test_frozen_question_shuffle_is_deterministic_and_changes_order() -> None:
    questions = [
        {"question_key": f"{index:064x}"}
        for index in range(20)
    ]
    first = exploration._shuffled_questions(questions)
    second = exploration._shuffled_questions(list(reversed(questions)))
    assert first == second
    assert first != questions
    assert {item["question_key"] for item in first} == {
        item["question_key"] for item in questions
    }


def test_shuffle_requires_complete_exploration(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(exploration, "CHECKPOINT_PATH", tmp_path / "missing.jsonl")
    with pytest.raises(exploration.BeamExplorationError, match="requires complete"):
        exploration.run_shuffle_shard(0, 1)


def test_baseline_trace_and_composition_gates_fail_loudly() -> None:
    valid = {
        "arm": exploration.ARMS[0],
        "retrieval_chars": 32_000,
        "recent_ids": ["recent"],
        "selected_long_term_ids": ["long"],
        "aspect": {
            "order": [],
            "marginal": [],
            "covered_counts": [],
            "solo_chars": 0,
        },
    }
    exploration._assert_composition(valid)
    with pytest.raises(exploration.BeamExplorationError, match="duplicated"):
        exploration._assert_composition(
            {**valid, "selected_long_term_ids": ["recent"]}
        )
    with pytest.raises(exploration.BeamExplorationError, match="ASPECT"):
        exploration._assert_composition(
            {**valid, "aspect": {**valid["aspect"], "order": ["long"]}}
        )


def test_gzip_jsonl_is_canonical_and_timestamp_free(tmp_path) -> None:
    path = tmp_path / "rows.jsonl.gz"
    rows = [{"b": 2, "a": 1}, {"text": "exact"}]
    exploration._write_gzip_jsonl(path, rows)
    first = path.read_bytes()
    exploration._write_gzip_jsonl(path, rows)
    assert path.read_bytes() == first
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        assert [json.loads(line) for line in handle] == rows


def test_retrieval_introspection_uses_only_public_call_parameters() -> None:
    tree = ast.parse(inspect.getsource(exploration))
    allowed = set(inspect.signature(retrieve_long_term).parameters)
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "retrieve_long_term"
    ]
    assert calls
    for call in calls:
        assert {keyword.arg for keyword in call.keywords} <= allowed

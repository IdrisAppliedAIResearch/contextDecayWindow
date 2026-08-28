from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from analysis.beam001_adapter import (
    BeamAdapterError,
    adapt_conversation,
    assert_mechanism_only,
    load_mechanism_surface,
)
from analysis.beam001_corpus import conversation_key, prepare
from analysis.beam001_outcomes import load_outcomes


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _row() -> dict:
    chat = [
        [
            {
                "content": "Question one",
                "id": 1,
                "index": "1",
                "question_type": "main_question",
                "role": "user",
                "time_anchor": "2025-01-01",
            },
            {
                "content": "Answer one",
                "id": 2,
                "index": "2",
                "question_type": "",
                "role": "assistant",
                "time_anchor": "2025-01-01",
            },
            {
                "content": "Question one",
                "id": 3,
                "index": "3",
                "question_type": "main_question",
                "role": "user",
                "time_anchor": "2025-01-02",
            },
            {
                "content": "Answer one",
                "id": 4,
                "index": "4",
                "question_type": "",
                "role": "assistant",
                "time_anchor": "2025-01-02",
            },
        ]
    ]
    questions = {
        "information_extraction": [
            {
                "question": "What was answered?",
                "ideal_response": "Sealed value",
                "rubric": ["Sealed criterion"],
                "difficulty": "easy",
                "plan_reference": "sealed",
                "abstention_type": "",
                "why_unanswerable": "",
            }
        ]
    }
    return {
        "conversation_id": "fixture-1",
        "conversation_seed": {
            "category": "fixture",
            "id": 1,
            "subtopics": ["fixture"],
            "theme": "fixture",
            "title": "fixture",
        },
        "narratives": "sealed metadata",
        "user_profile": {
            "user_info": "sealed metadata",
            "user_relationships": "sealed metadata",
        },
        "conversation_plan": "sealed metadata",
        "user_questions": [],
        "chat": chat,
        "probing_questions": repr(questions),
    }


def _manifest(tmp_path: Path, parquet_path: Path) -> Path:
    readme = tmp_path / "README.md"
    attrs = tmp_path / ".gitattributes"
    readme.write_text("license: cc-by-sa-4.0\n", encoding="utf-8")
    attrs.write_text("", encoding="utf-8")
    files = []
    for path in (attrs, readme, parquet_path):
        files.append(
            {
                "path": path.relative_to(tmp_path).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _hash(path),
                **(
                    {"rows": 1, "row_groups": 1, "split": "100K"}
                    if path == parquet_path
                    else {}
                ),
            }
        )
    manifest = {
        "dataset": {
            "external_root": str(tmp_path),
            "revision": "fixture-revision",
            "files": files,
            "normal_scale_rows": 1,
        }
    }
    path = tmp_path / "source_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_trusted_split_separates_questions_from_outcomes(tmp_path: Path) -> None:
    parquet_path = tmp_path / "data" / "100K.parquet"
    parquet_path.parent.mkdir()
    pq.write_table(pa.Table.from_pylist([_row()]), parquet_path)
    manifest = _manifest(tmp_path, parquet_path)
    mechanism = tmp_path / "mechanism.jsonl.gz"
    outcome = tmp_path / "outcomes.jsonl.gz"
    schema = tmp_path / "schema.json"
    surfaces = tmp_path / "surfaces.json"

    result = prepare(
        manifest_path=manifest,
        mechanism_path=mechanism,
        outcome_path=outcome,
        schema_path=schema,
        surface_manifest_path=surfaces,
    )

    rows = load_mechanism_surface(mechanism)
    outcomes = load_outcomes(outcome)
    assert result["question_key_sets_equal"] is True
    assert len(rows) == len(outcomes) == 1
    assert "ideal_response" not in json.dumps(rows)
    assert next(iter(outcomes.values()))["ideal_response"] == "Sealed value"
    assert json.loads(schema.read_text())["gate"] == "PASS"


def test_adapter_uses_strict_pairs_and_duplicate_ordinals() -> None:
    source = _row()
    chat = source["chat"]
    row = {
        "domain": "BEAM",
        "split": "100K",
        "conversation_key": conversation_key("100K", chat),
        "chat_batches": chat,
        "questions": [],
    }
    episodes = adapt_conversation(row)
    assert len(episodes) == 2
    assert episodes[0]["id"] != episodes[1]["id"]
    assert [item["occurrence_ordinal"] for item in episodes] == [0, 0]
    moved = json.loads(json.dumps(row))
    assert adapt_conversation(moved) == episodes


def test_planted_outcome_field_is_rejected() -> None:
    with pytest.raises(BeamAdapterError, match="Outcome fields"):
        assert_mechanism_only(
            {
                "questions": [
                    {
                        "question": "safe",
                        "rubric": [],
                        "source_chat_ids": [1],
                        "ideal_answer": "sealed",
                    }
                ]
            }
        )


def test_adapter_rejects_non_alternating_chat() -> None:
    source = _row()
    source["chat"][0][1]["role"] = "user"
    row = {
        "domain": "BEAM",
        "split": "100K",
        "conversation_key": conversation_key("100K", source["chat"]),
        "chat_batches": source["chat"],
        "questions": [],
    }
    with pytest.raises(BeamAdapterError, match="Strict alternation"):
        adapt_conversation(row)

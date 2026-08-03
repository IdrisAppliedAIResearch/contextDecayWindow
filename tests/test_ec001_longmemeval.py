from __future__ import annotations

import inspect
import json
from dataclasses import fields
from pathlib import Path

import numpy as np
import pytest

from src.analysis.ec001_longmemeval import (
    EXPECTED_STRATA,
    EC001Error,
    EpisodeInput,
    EvidenceTurn,
    InstanceBundle,
    MechanismInstance,
    MeasurementInstance,
    build_instrument_audit_registration,
    build_subset_manifest,
    load_longmemeval,
    mechanism_surface_fields,
    parse_delivered_block,
    retrieve_block,
    retrieve_tier1_instance,
    score_retrieval,
    session_cosine_ranking,
    sha256_file,
    validate_subset_manifest,
)


CARRIED_MODEL_SHA = (
    "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
)


def _entry(
    question_id: str,
    question_type: str,
    *,
    abstention: bool = False,
) -> dict:
    session_id = f"session-{question_id}"
    user = {"role": "user", "content": f"fact for {question_id}"}
    if not abstention:
        user["has_answer"] = True
    return {
        "question_id": question_id,
        "question_type": question_type,
        "question": f"question for {question_id}",
        "answer": f"answer for {question_id}",
        "question_date": "2023/05/02 (Tue) 12:00",
        "answer_session_ids": [] if abstention else [session_id],
        "haystack_dates": ["2023/05/01 (Mon) 12:00"],
        "haystack_session_ids": [session_id],
        "haystack_sessions": [
            [
                user,
                {"role": "assistant", "content": "acknowledged"},
            ]
        ],
    }


def _write_dataset(path: Path) -> str:
    rows = [
        _entry(f"q-{question_type}", question_type)
        for question_type in EXPECTED_STRATA
        if question_type != "abstention"
    ]
    rows.append(_entry("q-abstention_abs", "single-session-user",
                       abstention=True))
    path.write_text(json.dumps(rows), encoding="utf-8")
    return sha256_file(path)


def test_loader_separates_mechanism_from_reference_fields(tmp_path: Path) -> None:
    path = tmp_path / "longmemeval.json"
    source_sha = _write_dataset(path)

    dataset = load_longmemeval(
        path,
        expected_sha256=source_sha,
        expected_count=len(EXPECTED_STRATA),
    )
    bundle = dataset.instances[0]

    assert mechanism_surface_fields() == (
        "question_id",
        "question",
        "episodes",
    )
    assert {field.name for field in fields(bundle.mechanism)} == {
        "question_id",
        "question",
        "episodes",
    }
    assert not hasattr(bundle.mechanism, "answer")
    assert not hasattr(bundle.mechanism, "answer_session_ids")
    assert bundle.measurement.evidence_turns[0].content.startswith("fact for")
    assert dataset.annotation_findings == ()


def test_loader_losslessly_adapts_unpaired_source_turn(tmp_path: Path) -> None:
    path = tmp_path / "irregular.json"
    entry = _entry("q", "single-session-user")
    entry["haystack_sessions"][0].append(
        {"role": "user", "content": "unpaired"}
    )
    path.write_text(json.dumps([entry]), encoding="utf-8")

    dataset = load_longmemeval(path, expected_count=1)
    bundle = dataset.instances[0]

    assert len(bundle.mechanism.episodes) == 2
    assert bundle.mechanism.episodes[1] == EpisodeInput(
        2,
        "unpaired",
        "",
    )
    assert [turn.content for turn in bundle.measurement.source_turns] == [
        "fact for q",
        "acknowledged",
        "unpaired",
    ]
    assert bundle.measurement.singleton_episode_turn_numbers == (2,)
    assert dataset.adaptation_stats["lossless_turn_count"] == 3
    assert dataset.adaptation_stats["status"] == "PASS"


def test_loader_preserves_assistant_first_evidence(tmp_path: Path) -> None:
    path = tmp_path / "assistant-first.json"
    entry = _entry("q", "single-session-assistant")
    entry["haystack_sessions"] = [
        [
            {
                "role": "assistant",
                "content": "required assistant fact",
                "has_answer": True,
            },
            {"role": "user", "content": "follow-up"},
            {"role": "assistant", "content": "reply"},
        ]
    ]
    path.write_text(json.dumps([entry]), encoding="utf-8")

    dataset = load_longmemeval(path, expected_count=1)
    bundle = dataset.instances[0]

    assert bundle.mechanism.episodes == (
        EpisodeInput(1, "", "required assistant fact"),
        EpisodeInput(2, "follow-up", "reply"),
    )
    assert bundle.measurement.evidence_turns == (
        EvidenceTurn(
            session_id="session-q::position=0",
            episode_turn_number=1,
            role="assistant",
            content="required assistant fact",
            raw_session_id="session-q",
        ),
    )
    assert dataset.adaptation_stats["singleton_assistant_episodes"] == 1


def test_loader_preserves_duplicate_filler_session_occurrences(
    tmp_path: Path,
) -> None:
    path = tmp_path / "duplicate-filler.json"
    entry = _entry("q", "multi-session")
    filler = [
        {"role": "user", "content": "same filler"},
        {"role": "assistant", "content": "same reply"},
    ]
    entry["haystack_session_ids"].extend(["filler", "filler"])
    entry["haystack_dates"].extend(
        ["2023/05/01 (Mon) 10:00", "2023/05/01 (Mon) 11:00"]
    )
    entry["haystack_sessions"].extend([filler, filler])
    path.write_text(json.dumps([entry]), encoding="utf-8")

    dataset = load_longmemeval(path, expected_count=1)
    measurement = dataset.instances[0].measurement

    assert measurement.session_ids == (
        "session-q::position=0",
        "filler::position=1",
        "filler::position=2",
    )
    assert measurement.raw_session_ids == ("session-q", "filler", "filler")
    assert measurement.answer_session_keys == ("session-q::position=0",)
    assert len(dataset.instances[0].mechanism.episodes) == 3
    assert dataset.adaptation_stats["duplicate_session_occurrences"] == 1
    assert dataset.adaptation_stats["questions_with_duplicate_session_ids"] == 1


def test_loader_fails_on_ambiguous_duplicate_evidence_session(
    tmp_path: Path,
) -> None:
    path = tmp_path / "duplicate-evidence.json"
    entry = _entry("q", "multi-session")
    entry["haystack_session_ids"].append("session-q")
    entry["haystack_dates"].append("2023/05/01 (Mon) 13:00")
    entry["haystack_sessions"].append(
        [
            {"role": "user", "content": "duplicate evidence id"},
            {"role": "assistant", "content": "reply"},
        ]
    )
    path.write_text(json.dumps([entry]), encoding="utf-8")

    with pytest.raises(EC001Error, match="duplicated raw evidence"):
        load_longmemeval(path, expected_count=1)


def test_loader_preserves_file_order_and_audits_timestamp_anomalies(
    tmp_path: Path,
) -> None:
    path = tmp_path / "timestamp-anomaly.json"
    entry = _entry("q", "temporal-reasoning")
    entry["haystack_session_ids"].append("earlier-second")
    entry["haystack_dates"].append("2023/04/30 (Sun) 12:00")
    entry["haystack_sessions"].append(
        [
            {"role": "user", "content": "earlier by timestamp"},
            {"role": "assistant", "content": "reply"},
        ]
    )
    path.write_text(json.dumps([entry]), encoding="utf-8")

    dataset = load_longmemeval(path, expected_count=1)

    assert dataset.instances[0].measurement.raw_session_ids == (
        "session-q",
        "earlier-second",
    )
    assert any(
        finding["kind"] == "nonchronological_session_timestamps"
        and finding["adjacent_inversions"] == 1
        for finding in dataset.annotation_findings
    )


def test_loader_preserves_empty_source_turn(tmp_path: Path) -> None:
    path = tmp_path / "empty-turn.json"
    entry = _entry("q", "single-session-user")
    entry["haystack_sessions"][0][1]["content"] = ""
    path.write_text(json.dumps([entry]), encoding="utf-8")

    dataset = load_longmemeval(path, expected_count=1)

    assert dataset.instances[0].mechanism.episodes[0].assistant_message == ""
    assert dataset.instances[0].measurement.source_turns[1].content == ""
    assert dataset.adaptation_stats["empty_source_turns"] == 1
    assert dataset.adaptation_stats["lossless_turn_count"] == 2


def test_subset_is_deterministic_and_covers_every_stratum(
    tmp_path: Path,
) -> None:
    path = tmp_path / "longmemeval.json"
    _write_dataset(path)
    dataset = load_longmemeval(path, expected_count=len(EXPECTED_STRATA))
    quotas = {stratum: 1 for stratum in EXPECTED_STRATA}

    first = build_subset_manifest(dataset, quotas, seed=5005)
    second = build_subset_manifest(dataset, quotas, seed=5005)

    assert first == second
    assert len(validate_subset_manifest(first, dataset)) == len(EXPECTED_STRATA)
    assert first["size"] == len(EXPECTED_STRATA)


def test_subset_rejects_result_shaped_fields(tmp_path: Path) -> None:
    path = tmp_path / "longmemeval.json"
    _write_dataset(path)
    dataset = load_longmemeval(path, expected_count=len(EXPECTED_STRATA))
    manifest = build_subset_manifest(
        dataset,
        {stratum: 1 for stratum in EXPECTED_STRATA},
        seed=5005,
    )
    manifest["retrieval_score"] = 0.9

    with pytest.raises(EC001Error, match="result-shaped"):
        validate_subset_manifest(manifest, dataset)


def test_session_recall_can_pass_when_fact_availability_fails() -> None:
    measurement = MeasurementInstance(
        question_id="q",
        question_type="multi-session",
        is_abstention=False,
        question_date="2023/05/02 (Tue) 12:00",
        session_ids=("evidence-session",),
        session_dates=("2023/05/01 (Mon) 12:00",),
        episode_session_ids=("evidence-session", "evidence-session"),
        answer_session_ids=("evidence-session",),
        evidence_turns=(
            EvidenceTurn(
                session_id="evidence-session",
                episode_turn_number=1,
                role="user",
                content="the actual fact",
            ),
        ),
    )
    delivered = {
        2: {
            "user": "same session, wrong exchange",
            "assistant": "ack",
        }
    }
    ranking = [{"rank": 1, "session_id": "evidence-session", "cosine": 1.0}]

    result = score_retrieval(measurement, delivered, ranking)

    assert result["evidence_session_recall_all"] is True
    assert result["availability_any"] is False
    assert result["availability_all"] is False


def test_incomplete_turn_labels_cannot_certify_exact_availability() -> None:
    measurement = MeasurementInstance(
        question_id="q",
        question_type="multi-session",
        is_abstention=False,
        question_date="2023/05/02 (Tue) 12:00",
        session_ids=("marked", "unmarked"),
        session_dates=(
            "2023/05/01 (Mon) 12:00",
            "2023/05/01 (Mon) 13:00",
        ),
        episode_session_ids=("marked", "unmarked"),
        answer_session_ids=("marked", "unmarked"),
        evidence_turns=(
            EvidenceTurn("marked", 1, "user", "positive evidence"),
        ),
    )
    delivered = {
        1: {"user": "positive evidence", "assistant": "ack"},
        2: {"user": "exclusion evidence", "assistant": "ack"},
    }
    ranking = [
        {"rank": 1, "session_id": "marked", "cosine": 1.0},
        {"rank": 2, "session_id": "unmarked", "cosine": 0.5},
    ]

    result = score_retrieval(measurement, delivered, ranking)

    assert result["marker_availability_all"] is True
    assert result["availability_all"] is True
    assert result["turn_label_complete"] is False
    assert result["exact_gap_evaluable"] is False


def test_abstention_has_no_invented_retrieval_metric() -> None:
    measurement = MeasurementInstance(
        question_id="q_abs",
        question_type="single-session-user",
        is_abstention=True,
        question_date="2023/05/02 (Tue) 12:00",
        session_ids=("s",),
        session_dates=("2023/05/01 (Mon) 12:00",),
        episode_session_ids=("s",),
        answer_session_ids=(),
        evidence_turns=(),
    )

    result = score_retrieval(
        measurement,
        {1: {"user": "irrelevant", "assistant": "ack"}},
        [{"rank": 1, "session_id": "s", "cosine": 0.5}],
    )

    assert result["evidence_session_recall_any"] is None
    assert result["availability_all"] is None
    assert result["component_abstention_signal"] is False


def test_pre_retrieval_audit_registers_incomplete_turn_labels(
    tmp_path: Path,
) -> None:
    path = tmp_path / "incomplete-label.json"
    entry = _entry("q", "multi-session")
    entry["haystack_session_ids"].append("unmarked")
    entry["haystack_dates"].append("2023/05/01 (Mon) 13:00")
    entry["haystack_sessions"].append(
        [
            {"role": "user", "content": "exclusion evidence"},
            {"role": "assistant", "content": "ack"},
        ]
    )
    entry["answer_session_ids"].append("unmarked")
    path.write_text(json.dumps([entry]), encoding="utf-8")

    audit = build_instrument_audit_registration(
        load_longmemeval(path, expected_count=1)
    )

    assert audit["tier_1_results_consulted"] is False
    assert audit["incomplete_turn_label_question_count"] == 1
    assert audit["incomplete_turn_label_session_count"] == 1
    assert audit["incomplete_turn_labels"][0][
        "raw_answer_session_ids_without_turn_label"
    ] == ["unmarked"]


def test_session_rank_uses_best_episode_and_stable_session_order() -> None:
    mechanism = MechanismInstance(
        question_id="q",
        question="query",
        episodes=(
            EpisodeInput(1, "first", "ack"),
            EpisodeInput(2, "second", "ack"),
            EpisodeInput(3, "third", "ack"),
        ),
    )
    measurement = MeasurementInstance(
        question_id="q",
        question_type="multi-session",
        is_abstention=False,
        question_date="2023/05/02 (Tue) 12:00",
        session_ids=("s1", "s2"),
        session_dates=(
            "2023/05/01 (Mon) 10:00",
            "2023/05/01 (Mon) 11:00",
        ),
        episode_session_ids=("s1", "s1", "s2"),
        answer_session_ids=("s1",),
        evidence_turns=(),
    )
    vectors = {
        "query": np.array([1.0, 0.0], dtype=np.float32),
        mechanism.episodes[0].embedded_text: np.array([0.0, 1.0]),
        mechanism.episodes[1].embedded_text: np.array([1.0, 0.0]),
        mechanism.episodes[2].embedded_text: np.array([0.5, 0.5]),
    }

    ranking = session_cosine_ranking(
        mechanism,
        measurement,
        lambda text: vectors[text],
    )

    assert [row["session_id"] for row in ranking] == ["s1", "s2"]
    assert ranking[0]["cosine"] == 1.0


def test_public_block_parser_preserves_exact_text() -> None:
    block = (
        "<recent_context>\n"
        '<episode turn="7">\n'
        "<user>A &amp; B</user>\n"
        "<assistant>&lt;ack&gt;</assistant>\n"
        "</episode>\n"
        "</recent_context>\n\n"
        "<retrieved_stm/>"
    )

    assert parse_delivered_block(block) == {
        7: {"user": "A & B", "assistant": "<ack>"}
    }


class _FakeEmbedder:
    model_sha256 = CARRIED_MODEL_SHA

    def __call__(self, text: str) -> np.ndarray:
        vector = np.zeros(1024, dtype=np.float32)
        vector[sum(text.encode("utf-8")) % len(vector)] = 1.0
        return vector


def test_retrieval_boundary_replays_byte_identically(tmp_path: Path) -> None:
    mechanism = MechanismInstance(
        question_id="q",
        question="What is the fact?",
        episodes=(EpisodeInput(1, "the fact", "ack"),),
    )

    block, report = retrieve_block(
        mechanism,
        store_path=tmp_path / "store.db",
        embedder=_FakeEmbedder(),
        budget_chars=32_000,
    )

    assert "the fact" in block
    assert report.episodes_delivered == 1
    assert tuple(inspect.signature(retrieve_block).parameters) == (
        "mechanism",
        "store_path",
        "embedder",
        "budget_chars",
    )


def test_tier1_join_reports_ranks_without_reference_leakage(
    tmp_path: Path,
) -> None:
    mechanism = MechanismInstance(
        question_id="q",
        question="What is the fact?",
        episodes=(EpisodeInput(1, "the fact", "ack"),),
    )
    measurement = MeasurementInstance(
        question_id="q",
        question_type="single-session-user",
        is_abstention=False,
        question_date="2023/05/02 (Tue) 12:00",
        session_ids=("s",),
        session_dates=("2023/05/01 (Mon) 12:00",),
        episode_session_ids=("s",),
        answer_session_ids=("s",),
        evidence_turns=(EvidenceTurn("s", 1, "user", "the fact"),),
    )

    scores, mechanism_log = retrieve_tier1_instance(
        InstanceBundle(mechanism, measurement),
        store_path=tmp_path / "store.db",
        embedder=_FakeEmbedder(),
        budget_chars=32_000,
    )

    assert scores["availability_all"] is True
    assert scores["evidence_session_ranks"] == [1]
    assert "answer_session_ids" not in mechanism_log
    assert "q_facts_key" not in inspect.getsource(retrieve_block)
    assert "rubric" not in inspect.getsource(retrieve_block).casefold()

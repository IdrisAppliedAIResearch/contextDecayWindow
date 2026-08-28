from __future__ import annotations

import json
import time

import numpy as np
import pytest
import analysis.hh002_batch as batch_transport

from analysis.beam001_live import (
    BATCH_TOKEN_BUDGET,
    IN_FLIGHT_TOKEN_TARGET,
    OPTIMIZED_QUESTIONS,
    OPTIMIZED_READER_CALLS,
    bootstrap_interval,
    classify_disposition,
    extract_string_constant,
    parse_bundled_judge_body,
    load_questions,
    optimized_question_keys,
    render_judge_prompt,
    render_reader_prompt,
    run_synchronous_with_one_retry,
    run_synchronous_schedule,
    sign_flip_p,
)
from analysis.hh002_batch import BatchRequest
from analysis.hh002_batch import BatchLedger, HH002BatchError, await_file_ready


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


def bundled_payload() -> dict:
    return {
        "evaluations": [
            {
                "slot": slot,
                "criteria": [
                    {"rubric_index": 0, "score": 1.0, "reason": "yes"},
                    {"rubric_index": 1, "score": 0.5, "reason": "partial"},
                ],
            }
            for slot in ("R0", "R1", "R2")
        ]
    }


def test_bundled_judge_parser_requires_complete_matrix() -> None:
    source = {"slots": ["R0", "R1", "R2"], "rubric_count": 2}
    parsed = parse_bundled_judge_body(source, response(json.dumps(bundled_payload())))
    assert parsed is not None and len(parsed) == 3
    broken = bundled_payload()
    broken["evaluations"][0]["criteria"].pop()
    assert parse_bundled_judge_body(source, response(json.dumps(broken))) is None


def test_bundled_judge_parser_rejects_duplicate_slot_and_bad_score() -> None:
    source = {"slots": ["R0", "R1", "R2"], "rubric_count": 2}
    duplicate = bundled_payload()
    duplicate["evaluations"][1]["slot"] = "R0"
    assert parse_bundled_judge_body(source, response(json.dumps(duplicate))) is None
    bad_score = bundled_payload()
    bad_score["evaluations"][0]["criteria"][0]["score"] = 0.25
    assert parse_bundled_judge_body(source, response(json.dumps(bad_score))) is None


def test_judge_parser_rejects_non_stop() -> None:
    source = {"slots": ["R0", "R1", "R2"], "rubric_count": 2}
    assert parse_bundled_judge_body(
        source, response(json.dumps(bundled_payload()), "length")
    ) is None


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
    source = {"slots": ["R0", "R1", "R2"], "rubric_count": 2}
    body = response(json.dumps(bundled_payload()))
    assert parse_bundled_judge_body(source, body) is not None


def test_synchronous_smoke_retries_once_and_preserves_body() -> None:
    class Result:
        def __init__(self, body: dict) -> None:
            self.body = body

        def model_dump(self, mode: str) -> dict:
            assert mode == "json"
            return self.body

    class Completions:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def create(self, **body: object) -> Result:
            self.calls.append(body)
            if len(self.calls) == 1:
                return Result(response("", "length"))
            return Result(response("answer"))

    completions = Completions()
    client = type("Client", (), {"chat": type("Chat", (), {"completions": completions})()})()
    request = BatchRequest("id", {"model": "m", "messages": []}, 1)
    results = run_synchronous_with_one_retry(
        client, [request], lambda body: None if body.get("choices", [{}])[0].get("finish_reason") == "stop" else "bad"
    )
    assert len(completions.calls) == 2
    assert completions.calls[0] == completions.calls[1] == request.body
    assert results["id"]["choices"][0]["message"]["content"] == "answer"


def test_batch_utilization_constants_match_amendment() -> None:
    assert BATCH_TOKEN_BUDGET == 600_000
    assert IN_FLIGHT_TOKEN_TARGET == 1_900_000


def test_optimized_sample_retains_all_conversations_and_balances_categories() -> None:
    questions = load_questions()
    selected = optimized_question_keys(questions)
    assert len(selected) == OPTIMIZED_QUESTIONS
    categories: dict[str, int] = {}
    conversations: dict[str, int] = {}
    scales: dict[str, int] = {}
    for key in selected:
        row = questions[key]
        categories[row["category"]] = categories.get(row["category"], 0) + 1
        conversations[row["conversation_key"]] = conversations.get(
            row["conversation_key"], 0
        ) + 1
        scales[row["scale"]] = scales.get(row["scale"], 0) + 1
    assert set(categories.values()) == {36}
    assert len(conversations) == 90 and set(conversations.values()) == {4}
    assert scales == {"100K": 80, "500K": 140, "1M": 140}
    assert len(selected) * 3 == OPTIMIZED_READER_CALLS


def test_file_readiness_waits_for_processed_state() -> None:
    class Files:
        def __init__(self) -> None:
            self.statuses = iter(("uploaded", "processed"))

        def retrieve(self, file_id: str) -> object:
            assert file_id == "file-1"
            return type("Uploaded", (), {"status": next(self.statuses)})()

    client = type("Client", (), {"files": Files()})()
    await_file_ready(client, "file-1", timeout_seconds=1, poll_seconds=0)


def test_file_readiness_rejects_terminal_error() -> None:
    files = type(
        "Files",
        (),
        {"retrieve": lambda self, file_id: type("Uploaded", (), {"status": "error"})()},
    )()
    client = type("Client", (), {"files": files})()
    with pytest.raises(HH002BatchError, match="ended error"):
        await_file_ready(client, "file-1", timeout_seconds=1, poll_seconds=0)


def test_scheduler_stops_after_one_terminal_job_retry(monkeypatch, tmp_path) -> None:
    submissions: list[str] = []

    def submit(client, requests, ledger, key, log, study, file_ready_timeout_seconds):
        submissions.append(key)
        return f"batch-{len(submissions)}"

    def poll(client, batch_id, ledger, key):
        return {
            "status": "failed",
            "completed": 0,
            "failed": 0,
            "total": 0,
            "output_file_id": None,
            "error_file_id": None,
        }

    monkeypatch.setattr(batch_transport, "submit_job", submit)
    monkeypatch.setattr(batch_transport, "poll_job", poll)
    request = BatchRequest("id", {"model": "m"}, 1)
    with pytest.raises(HH002BatchError, match="exhausted 1 batch retry"):
        batch_transport.run_scheduled(
            object(),
            [("reader", [request])],
            BatchLedger(tmp_path / "ledger.json"),
            poll_seconds=0,
            max_job_retries=1,
        )
    assert submissions == ["reader.000", "reader.000"]


def test_synchronous_schedule_fsyncs_and_adopts_completed_ids(tmp_path) -> None:
    class Result:
        def __init__(self, content: str) -> None:
            self.content = content

        def model_dump(self, mode: str) -> dict:
            assert mode == "json"
            return response(self.content)

    class Completions:
        def __init__(self) -> None:
            self.calls = 0

        def create(self, **body: object) -> Result:
            self.calls += 1
            return Result(str(body["model"]))

    completions = Completions()
    client = type("Client", (), {"chat": type("Chat", (), {"completions": completions})()})()
    schedule = [
        {
            "body": {"model": f"m-{index}", "messages": [], "max_tokens": 1},
            "body_sha256": f"sha-{index}",
            "custom_id": f"id-{index}",
            "prompt_tokens": 1,
        }
        for index in range(2)
    ]

    def record(source: dict, body: dict) -> dict:
        return {
            "body_sha256": source["body_sha256"],
            "custom_id": source["custom_id"],
            "text": body["choices"][0]["message"]["content"],
        }

    kwargs = {
        "checkpoint_path": tmp_path / "checkpoint.jsonl",
        "final_path": tmp_path / "final.jsonl",
        "workers": 2,
        "deadline_unix": time.time() + 30,
        "validator": lambda row, body: None,
        "record_builder": record,
        "stage": "TEST",
    }
    first = run_synchronous_schedule(client, schedule, **kwargs)
    second = run_synchronous_schedule(client, schedule, **kwargs)
    assert len(first) == len(second) == 2
    assert completions.calls == 2
    assert len((tmp_path / "checkpoint.jsonl").read_text().splitlines()) == 2

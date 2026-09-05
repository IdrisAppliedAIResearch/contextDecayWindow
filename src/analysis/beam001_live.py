"""Registered BEAM-001 GPT-4o mini reader, blind judge, and scorer."""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import tiktoken
from openai import OpenAI

from analysis.beam001_outcomes import load_outcomes
from analysis.hh002_batch import (
    BatchLedger,
    BatchRequest,
    HH002BatchError,
    run_scheduled,
    text_of,
    usage_of,
)
from analysis.hh002_sync_arm import RateBucket


MODEL = "gpt-4o-mini-2024-07-18"
ARMS = (
    "A0_CC80_QWEN_GPU_COMMON",
    "C0_STATIC_ASPECT_QWEN_GPU_COMMON",
    "T1_PARENT_OPPORTUNITY_ASPECT_QWEN_GPU_COMMON",
)
A0, C0, T1 = ARMS
READER_MAX_TOKENS = 2048
JUDGE_MAX_TOKENS = 4096
JUDGE_REPAIR_MAX_TOKENS = 16_384
JUDGE_REPAIR_ATTEMPTS = 4
INPUT_LIMIT = 125_952
BATCH_TOKEN_BUDGET = 600_000
IN_FLIGHT_TOKEN_TARGET = 1_900_000
RUNTIME_SECONDS = 5 * 60 * 60
OPTIMIZED_QUESTIONS = 360
OPTIMIZED_READER_CALLS = 1080
OPTIMIZED_RUBRIC_ITEMS = 1061
OPTIMIZED_JUDGE_CALLS = 360
OPTIMIZED_CRITERION_SCORES = 3183
OPTIMIZED_INPUT_TOKENS = 43_077_320
OPTIMIZED_CHARGED_TOKENS = 45_289_160
TOKENS_PER_MINUTE_TARGET = 195_000
REQUESTS_PER_MINUTE_TARGET = 6.8
READER_WORKERS = 8
JUDGE_WORKERS = 32
CONTINUATION_DEVIATION = "DEVIATION_002"
JUDGE_REPAIR_DEVIATION = "DEVIATION_003"
STRICT_JUDGE_REPAIR_DEVIATION = "DEVIATION_004"
STRICT_JUDGE_REPAIR_ID = (
    "33c2b09a0f2bab25631122351fcae938a65ee2f5389a95d58a463a0972214d22"
)
SAMPLE_DOMAIN = "beam001-optimized-4q-sample-v1"
READER_DOMAIN = "beam001-sync-reader-v1"
JUDGE_DOMAIN = "beam001-bundled-judge-v1"
JUDGE_SLOT_DOMAIN = "beam001-bundled-judge-slot-v1"
ORDER_DOMAIN = "beam001-sync-reader-order-v1"
ROOT = Path(__file__).resolve().parents[2]
BEAM = ROOT / "experiments" / "comparisons" / "beam_001"
CORPUS = BEAM / "artifacts" / "corpus"
EXPLORATION = BEAM / "artifacts" / "exploration"
RUN = BEAM / "artifacts" / "live_sync"
DEFAULT_OFFICIAL_REPO = Path(
    r"C:\Users\muzaf\Downloads\beam_001_source\repo_3e12035532eb85768f1a7cd779832b650c4b2ef9"
)

BUNDLED_JUDGE_TEMPLATE = """You are an expert evaluator. Independently score each RESPONSE against each
ordered RUBRIC CRITERION for the QUESTION.

QUESTION:
<question>

RUBRIC CRITERIA (zero-based JSON array):
<rubric_json>

RESPONSES (JSON object keyed by blind slot):
<responses_json>

For every response and criterion, first require that the response addresses the
QUESTION. A non-responsive answer scores 0.0. Judge semantic meaning rather
than exact wording. Accept equivalent paraphrases, numbers, currencies and
dates. Ignore style unless the criterion explicitly requires format. For a
positive criterion, score 1.0 when fully satisfied, 0.5 when partially
satisfied, and 0.0 when missing or incorrect. For a negative constraint, score
1.0 only when the response is responsive and the prohibited element is absent,
0.5 for a minor or edge violation, and 0.0 when the prohibited element is
present or the response is non-responsive. Evaluate each slot independently;
do not rank or compare responses.

Return only JSON with this shape:
{"evaluations":[{"slot":"R0","criteria":[{"rubric_index":0,"score":1.0,
"reason":"concise justification"}]}]}

Include every supplied slot and every rubric index exactly once. Scores must be
0.0, 0.5 or 1.0. Keep each reason concise.
"""

ORIGINAL_JUDGE_OUTPUT_BLOCK = """Return only JSON with this shape:
{"evaluations":[{"slot":"R0","criteria":[{"rubric_index":0,"score":1.0,
"reason":"concise justification"}]}]}

Include every supplied slot and every rubric index exactly once. Scores must be
0.0, 0.5 or 1.0. Keep each reason concise.
"""

STRICT_JUDGE_OUTPUT_BLOCK = """Return only JSON matching the supplied strict schema. The `evaluations`
object contains the three blind slot keys. Within each slot, each rubric index
is a string key. Score every supplied slot and rubric index exactly once.
Scores must be 0.0, 0.5 or 1.0. Keep each reason concise and nonempty.
"""


class BeamLiveError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def content_id(domain: str, *parts: str) -> str:
    payload = b"\0".join([domain.encode("ascii"), *(p.encode("utf-8") for p in parts)])
    return sha256_bytes(payload)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def append_jsonl_fsync(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def run_synchronous_schedule(
    client: OpenAI,
    schedule: Sequence[dict[str, Any]],
    *,
    checkpoint_path: Path,
    final_path: Path,
    workers: int,
    deadline_unix: float,
    validator: Any,
    record_builder: Any,
    stage: str,
) -> list[dict[str, Any]]:
    existing_rows = read_jsonl(checkpoint_path)
    by_id = {str(row["custom_id"]): row for row in existing_rows}
    if len(by_id) != len(existing_rows):
        raise BeamLiveError(f"Duplicate {stage} checkpoint id")
    schedule_by_id = {str(row["custom_id"]): row for row in schedule}
    for custom_id, row in by_id.items():
        source = schedule_by_id.get(custom_id)
        if source is None or row.get("body_sha256") != source["body_sha256"]:
            raise BeamLiveError(f"{stage} checkpoint body drift: {custom_id}")
    pending = [row for row in schedule if row["custom_id"] not in by_id]
    if not pending:
        rows = sorted(by_id.values(), key=lambda row: row["custom_id"])
        write_jsonl(final_path, rows)
        return rows

    token_bucket = RateBucket(TOKENS_PER_MINUTE_TARGET)
    request_bucket = RateBucket(REQUESTS_PER_MINUTE_TARGET)
    stop = threading.Event()
    diagnostic_lock = threading.Lock()

    def one(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        request = as_batch_request(row)
        body: dict[str, Any] = {"error": "not_attempted"}
        attempts = int(row.get("max_attempts", 2))
        for attempt in range(1, attempts + 1):
            if stop.is_set():
                raise BeamLiveError(f"{stage} stopped")
            try:
                request_bucket.acquire(1, deadline_unix)
                token_bucket.acquire(request.approx_tokens, deadline_unix)
            except TimeoutError as error:
                raise BeamLiveError("RUNTIME_BUDGET_EXCEEDED") from error
            try:
                body = synchronous_body(client, request)
            except Exception as error:  # noqa: BLE001
                body = {
                    "error": {"type": type(error).__name__, "message": str(error)}
                }
            validation_error = validator(row, body)
            if validation_error is None:
                return row, body
            if row.get("persist_invalid_attempts"):
                try:
                    prompt_tokens, completion_tokens = usage_of(body)
                except Exception:  # noqa: BLE001
                    prompt_tokens, completion_tokens = 0, 0
                try:
                    response_text = text_of(body)
                except Exception:  # noqa: BLE001
                    response_text = ""
                diagnostic = {
                    "attempt": attempt,
                    "body_sha256": row["body_sha256"],
                    "completion_tokens": completion_tokens,
                    "custom_id": request.custom_id,
                    "error": body.get("error"),
                    "finish_reason": response_finish_reason(body),
                    "prompt_tokens": prompt_tokens,
                    "response_text_sha256": sha256_bytes(response_text.encode("utf-8")),
                    "validation_error": validation_error,
                }
                with diagnostic_lock:
                    append_jsonl_fsync(
                        RUN / f"{stage.lower()}.invalid_attempts.jsonl", diagnostic
                    )
        raise BeamLiveError(
            f"{stage} request exhausted {attempts} attempts: {request.custom_id}"
        )

    failures: list[Exception] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, row): str(row["custom_id"]) for row in pending}
        for future in as_completed(futures):
            if future.cancelled():
                continue
            try:
                source, body = future.result()
                record = record_builder(source, body)
            except Exception as error:  # noqa: BLE001
                if not failures:
                    stop.set()
                    for other in futures:
                        if other is not future:
                            other.cancel()
                failures.append(error)
                continue
            append_jsonl_fsync(checkpoint_path, record)
            by_id[record["custom_id"]] = record
            if len(by_id) % 10 == 0:
                write_json(
                    RUN / "progress.json",
                    {
                        "completed": len(by_id),
                        "stage": stage,
                        "status": "RUNNING",
                        "total": len(schedule),
                    },
                )
    if failures:
        raise failures[0]
    rows = sorted(by_id.values(), key=lambda row: row["custom_id"])
    if len(rows) != len(schedule):
        raise BeamLiveError(f"{stage} has {len(rows)} of {len(schedule)} records")
    write_jsonl(final_path, rows)
    return rows


def extract_string_constant(path: Path, name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            value = ast.literal_eval(node.value)
            if not isinstance(value, str):
                break
            return value
    raise BeamLiveError(f"String constant {name!r} not found in {path}")


def load_prompts(official_repo: Path) -> tuple[str, str]:
    path = official_repo / "src" / "prompts.py"
    if file_sha256(path) != "a06319493dfd98ee2aeacfa41952e19831c663b1a8c0f0471761a560c675214c":
        raise BeamLiveError("Official prompts.py hash drift")
    return (
        extract_string_constant(path, "answer_generation_for_rag"),
        extract_string_constant(path, "unified_llm_judge_base_prompt"),
    )


def load_questions() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    path = CORPUS / "mechanism_surface.jsonl.gz"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            conversation = json.loads(line)
            for question in conversation["questions"]:
                key = str(question["question_key"])
                if key in rows:
                    raise BeamLiveError(f"Duplicate question key: {key}")
                rows[key] = {
                    "question_key": key,
                    "conversation_key": str(conversation["conversation_key"]),
                    "scale": str(conversation["split"]),
                    "category": str(question["category"]),
                    "question": str(question["question"]),
                }
    if len(rows) != 1800:
        raise BeamLiveError(f"Expected 1800 questions, found {len(rows)}")
    return rows


def optimized_question_keys(
    questions: dict[str, dict[str, str]],
) -> set[str]:
    categories = sorted({row["category"] for row in questions.values()})
    if len(categories) != 10:
        raise BeamLiveError(f"Expected ten categories, found {len(categories)}")
    grouped: dict[str, dict[str, dict[str, list[str]]]] = {}
    for key, row in questions.items():
        grouped.setdefault(row["scale"], {}).setdefault(
            row["conversation_key"], {}
        ).setdefault(row["category"], []).append(key)
    offsets = {"100K": 0, "500K": 0, "1M": 5}
    selected: set[str] = set()
    for scale in ("100K", "500K", "1M"):
        conversations = sorted(grouped[scale])
        for index, conversation_key in enumerate(conversations):
            chosen_categories = {
                categories[(index + offsets[scale] + step) % 10]
                for step in range(4)
            }
            for category in chosen_categories:
                candidates = grouped[scale][conversation_key].get(category, [])
                if len(candidates) != 2:
                    raise BeamLiveError(
                        f"Expected two {category} questions in {conversation_key}"
                    )
                selected.add(
                    min(
                        candidates,
                        key=lambda key: sha256_bytes(
                            f"{SAMPLE_DOMAIN}\0{key}".encode("utf-8")
                        ),
                    )
                )
    if len(selected) != OPTIMIZED_QUESTIONS:
        raise BeamLiveError(
            f"Expected {OPTIMIZED_QUESTIONS} optimized questions, found {len(selected)}"
        )
    return selected


def load_payloads() -> dict[tuple[str, str], dict[str, str]]:
    rows: dict[tuple[str, str], dict[str, str]] = {}
    path = EXPLORATION / "payloads.sealed.jsonl.gz"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            key = (str(row["question_key"]), str(row["arm"]))
            payload = str(row["payload"])
            if key in rows or sha256_bytes(payload.encode("utf-8")) != row["payload_sha256"]:
                raise BeamLiveError(f"Duplicate or corrupt payload: {key}")
            rows[key] = {
                "payload": payload,
                "payload_sha256": str(row["payload_sha256"]),
            }
    if len(rows) != 5400:
        raise BeamLiveError(f"Expected 5400 payloads, found {len(rows)}")
    return rows


def render_reader_prompt(template: str, question: str, context: str) -> str:
    rendered = template.replace("<context>", context).replace("<question>", question)
    if "<context>" in rendered or "<question>" in rendered:
        raise BeamLiveError("Unresolved reader placeholder")
    return rendered


def request_digest(body: dict[str, Any]) -> str:
    return sha256_bytes(canonical_bytes(body))


def build_reader_schedule(
    template: str,
    questions: dict[str, dict[str, str]],
    payloads: dict[tuple[str, str], dict[str, str]],
    selected_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    encoding = tiktoken.encoding_for_model(MODEL)
    schedule: list[dict[str, Any]] = []
    population = sorted(selected_keys if selected_keys is not None else questions)
    for question_key in population:
        question = questions[question_key]["question"]
        arm_order = sorted(
            ARMS,
            key=lambda arm: content_id(ORDER_DOMAIN, question_key, arm),
        )
        for arm in arm_order:
            prompt = render_reader_prompt(
                template, question, payloads[(question_key, arm)]["payload"]
            )
            prompt_tokens = len(encoding.encode(prompt)) + 8
            if prompt_tokens > INPUT_LIMIT:
                raise BeamLiveError(f"Reader prompt over limit: {question_key} {arm}")
            body = {
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": READER_MAX_TOKENS,
            }
            schedule.append(
                {
                    **questions[question_key],
                    "arm": arm,
                    "custom_id": content_id(READER_DOMAIN, question_key, arm),
                    "payload_sha256": payloads[(question_key, arm)]["payload_sha256"],
                    "prompt_tokens": prompt_tokens,
                    "body": body,
                    "body_sha256": request_digest(body),
                }
            )
    expected = len(population) * len(ARMS)
    if len(schedule) != expected or len({row["custom_id"] for row in schedule}) != expected:
        raise BeamLiveError("Reader schedule count or identity failure")
    return schedule


def as_batch_request(row: dict[str, Any]) -> BatchRequest:
    return BatchRequest(
        custom_id=str(row["custom_id"]),
        body=dict(row["body"]),
        approx_tokens=int(row.get("prompt_tokens", 0)) + int(
            row["body"].get("max_tokens", 0)
        ),
    )


def response_finish_reason(body: dict[str, Any]) -> str:
    try:
        return str(body["choices"][0]["finish_reason"])
    except (KeyError, IndexError, TypeError):
        return ""


def response_refusal(body: dict[str, Any]) -> str:
    try:
        return str(body["choices"][0]["message"].get("refusal") or "")
    except (KeyError, IndexError, TypeError):
        return ""


def validate_reader_body(body: dict[str, Any]) -> str | None:
    if "error" in body:
        return "api_error"
    if response_finish_reason(body) != "stop":
        return f"finish_reason:{response_finish_reason(body) or 'missing'}"
    if response_refusal(body):
        return "refusal"
    if not text_of(body):
        return "empty"
    return None


def merge_answer_results(
    schedule: Sequence[dict[str, Any]],
    results: dict[str, dict[str, Any]],
    existing: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    by_id = {str(row["custom_id"]): dict(row) for row in existing}
    schedule_by_id = {str(row["custom_id"]): row for row in schedule}
    failed: list[str] = []
    for custom_id, body in results.items():
        error = validate_reader_body(body)
        if error:
            failed.append(custom_id)
            continue
        source = schedule_by_id[custom_id]
        prompt_tokens, completion_tokens = usage_of(body)
        by_id[custom_id] = {
            "answer": text_of(body),
            "arm": source["arm"],
            "body_sha256": source["body_sha256"],
            "completion_tokens": completion_tokens,
            "conversation_key": source["conversation_key"],
            "custom_id": custom_id,
            "finish_reason": response_finish_reason(body),
            "prompt_tokens": prompt_tokens,
            "question_key": source["question_key"],
            "scale": source["scale"],
            "category": source["category"],
        }
    return sorted(by_id.values(), key=lambda row: row["custom_id"]), sorted(failed)


def run_requests_with_one_retry(
    client: OpenAI,
    requests: Sequence[BatchRequest],
    ledger: BatchLedger,
    prefix: str,
    poll_seconds: int,
    validator: Any,
    deadline_unix: float,
) -> dict[str, dict[str, Any]]:
    try:
        results = run_scheduled(
            client,
            [(prefix, requests)],
            ledger,
            poll_seconds=poll_seconds,
            token_budget=BATCH_TOKEN_BUDGET,
            in_flight_target=IN_FLIGHT_TOKEN_TARGET,
            study="BEAM-001-OPTIMIZED",
            max_job_retries=1,
            deadline_unix=deadline_unix,
        )[prefix]
    except HH002BatchError as error:
        if "deadline" in str(error).lower():
            raise BeamLiveError(f"RUNTIME_BUDGET_EXCEEDED: {error}") from error
        raise BeamLiveError(str(error)) from error
    failed = [request for request in requests if validator(results.get(request.custom_id, {"error": "missing"}))]
    if failed:
        retry_prefix = f"{prefix}.retry1"
        try:
            retry = run_scheduled(
                client,
                [(retry_prefix, failed)],
                ledger,
                poll_seconds=poll_seconds,
                token_budget=BATCH_TOKEN_BUDGET,
                in_flight_target=IN_FLIGHT_TOKEN_TARGET,
                study="BEAM-001-OPTIMIZED",
                max_job_retries=1,
                deadline_unix=deadline_unix,
            )[retry_prefix]
        except HH002BatchError as error:
            if "deadline" in str(error).lower():
                raise BeamLiveError(f"RUNTIME_BUDGET_EXCEEDED: {error}") from error
            raise BeamLiveError(str(error)) from error
        results.update(retry)
    exhausted = [request.custom_id for request in requests if validator(results.get(request.custom_id, {"error": "missing"}))]
    if exhausted:
        raise BeamLiveError(f"{prefix} exhausted one retry for {len(exhausted)} request(s)")
    return results


def synchronous_body(client: OpenAI, request: BatchRequest) -> dict[str, Any]:
    response = client.chat.completions.create(**request.body)
    return response.model_dump(mode="json")


def run_synchronous_with_one_retry(
    client: OpenAI,
    requests: Sequence[BatchRequest],
    validator: Any,
    deadline_unix: float | None = None,
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for request in requests:
        if deadline_unix is not None and time.time() >= deadline_unix:
            raise BeamLiveError("RUNTIME_BUDGET_EXCEEDED before synchronous request")
        body: dict[str, Any] = {"error": "not_attempted"}
        for _attempt in range(2):
            try:
                body = synchronous_body(client, request)
            except Exception as error:  # noqa: BLE001
                body = {"error": {"type": type(error).__name__, "message": str(error)}}
            if validator(body) is None:
                break
        if validator(body) is not None:
            raise BeamLiveError(f"{request.custom_id} exhausted one synchronous retry")
        results[request.custom_id] = body
    return results


def run_reader(
    client: OpenAI,
    schedule: Sequence[dict[str, Any]],
    *,
    deadline_unix: float,
) -> list[dict[str, Any]]:
    def build_record(source: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
        prompt_tokens, completion_tokens = usage_of(body)
        return {
            "answer": text_of(body),
            "arm": source["arm"],
            "body_sha256": source["body_sha256"],
            "completion_tokens": completion_tokens,
            "conversation_key": source["conversation_key"],
            "custom_id": source["custom_id"],
            "finish_reason": response_finish_reason(body),
            "prompt_tokens": prompt_tokens,
            "question_key": source["question_key"],
            "scale": source["scale"],
            "category": source["category"],
        }

    return run_synchronous_schedule(
        client,
        schedule,
        checkpoint_path=RUN / "answers.checkpoint.jsonl",
        final_path=RUN / "answers.jsonl",
        workers=READER_WORKERS,
        deadline_unix=deadline_unix,
        validator=lambda _row, body: validate_reader_body(body),
        record_builder=build_record,
        stage="POPULATION_READER",
    )


def seal_answers(answers: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if len(answers) != OPTIMIZED_READER_CALLS:
        raise BeamLiveError("Cannot seal an incomplete answer population")
    keys = {(row["question_key"], row["arm"]) for row in answers}
    if len(keys) != OPTIMIZED_READER_CALLS or any(
        row["finish_reason"] != "stop" or not row["answer"] for row in answers
    ):
        raise BeamLiveError("Answer seal validity failure")
    seal = {
        "answers": OPTIMIZED_READER_CALLS,
        "answers_sha256": file_sha256(RUN / "answers.jsonl"),
        "sealed_at_unix": time.time(),
        "status": "SEALED",
    }
    write_json(RUN / "answers.seal.json", seal)
    return seal


def render_judge_prompt(template: str, question: str, rubric: str, answer: str) -> str:
    rendered = (
        template.replace("<question>", question)
        .replace("<rubric_item>", rubric)
        .replace("<llm_response>", answer)
    )
    if any(token in rendered for token in ("<question>", "<rubric_item>", "<llm_response>")):
        raise BeamLiveError("Unresolved judge placeholder")
    return rendered


def strict_judge_schema(rubric_count: int) -> dict[str, Any]:
    criterion = {
        "additionalProperties": False,
        "properties": {
            "reason": {"minLength": 1, "type": "string"},
            "score": {"enum": [0.0, 0.5, 1.0], "type": "number"},
        },
        "required": ["score", "reason"],
        "type": "object",
    }
    rubric_keys = [str(index) for index in range(rubric_count)]

    def slot_schema() -> dict[str, Any]:
        return {
            "additionalProperties": False,
            "properties": {key: criterion for key in rubric_keys},
            "required": rubric_keys,
            "type": "object",
        }

    slots = ["R0", "R1", "R2"]
    return {
        "additionalProperties": False,
        "properties": {
            "evaluations": {
                "additionalProperties": False,
                "properties": {slot: slot_schema() for slot in slots},
                "required": slots,
                "type": "object",
            }
        },
        "required": ["evaluations"],
        "type": "object",
    }


def prepare_judge_surfaces(
    answers: Sequence[dict[str, Any]], judge_template: str
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not (RUN / "answers.seal.json").exists():
        raise BeamLiveError("Judge construction before answer seal")
    outcomes = load_outcomes(CORPUS / "outcome_surface.sealed.jsonl.gz")
    questions = load_questions()
    encoding = tiktoken.encoding_for_model(MODEL)
    surface: list[dict[str, Any]] = []
    mapping: list[dict[str, str]] = []
    existing_judgments = {
        str(row["custom_id"]): str(row["body_sha256"])
        for row in read_jsonl(RUN / "judgments.checkpoint.blind.jsonl")
    }
    repair_authorized = (RUN / "judge_repair_runtime.json").exists()
    strict_repair_authorized = (RUN / "strict_judge_repair_runtime.json").exists()
    by_question: dict[str, dict[str, dict[str, Any]]] = {}
    for answer in answers:
        by_question.setdefault(str(answer["question_key"]), {})[
            str(answer["arm"])
        ] = dict(answer)
    for qkey in sorted(by_question):
        arm_answers = by_question[qkey]
        if set(arm_answers) != set(ARMS):
            raise BeamLiveError(f"Incomplete answer triplet: {qkey}")
        rubric = outcomes[qkey].get("rubric")
        if not isinstance(rubric, list) or not rubric:
            raise BeamLiveError(f"Missing rubric: {qkey}")
        arm_order = sorted(
            ARMS, key=lambda arm: content_id(JUDGE_SLOT_DOMAIN, qkey, arm)
        )
        responses = {
            f"R{index}": str(arm_answers[arm]["answer"])
            for index, arm in enumerate(arm_order)
        }
        answer_hashes = [
            sha256_bytes(responses[f"R{index}"].encode("utf-8"))
            for index in range(len(ARMS))
        ]
        blind_id = content_id(JUDGE_DOMAIN, qkey, *answer_hashes)
        prompt = (
            BUNDLED_JUDGE_TEMPLATE.replace("<question>", questions[qkey]["question"])
            .replace(
                "<rubric_json>",
                json.dumps(rubric, ensure_ascii=False, separators=(",", ":")),
            )
            .replace(
                "<responses_json>",
                json.dumps(
                    responses,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )
        )
        if any(
            placeholder in prompt
            for placeholder in ("<question>", "<rubric_json>", "<responses_json>")
        ):
            raise BeamLiveError("Unresolved bundled judge placeholder")
        original_body = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
            "max_tokens": JUDGE_MAX_TOKENS,
        }
        repaired_body = {**original_body, "max_tokens": JUDGE_REPAIR_MAX_TOKENS}
        strict_prompt = prompt.replace(
            ORIGINAL_JUDGE_OUTPUT_BLOCK, STRICT_JUDGE_OUTPUT_BLOCK
        )
        if strict_repair_authorized and strict_prompt == prompt:
            raise BeamLiveError("Strict judge output block replacement failed")
        strict_body = {
            **repaired_body,
            "messages": [{"role": "user", "content": strict_prompt}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "beam001_bundled_judge_matrix",
                    "schema": strict_judge_schema(len(rubric)),
                    "strict": True,
                },
            },
        }
        existing_digest = existing_judgments.get(blind_id)
        original_digest = request_digest(original_body)
        repaired_digest = request_digest(repaired_body)
        strict_digest = request_digest(strict_body)
        strict_request = False
        if existing_digest == original_digest:
            body = original_body
            attempts = 2
        elif existing_digest == repaired_digest:
            body = repaired_body
            attempts = JUDGE_REPAIR_ATTEMPTS
        elif existing_digest == strict_digest and blind_id == STRICT_JUDGE_REPAIR_ID:
            body = strict_body
            attempts = 2
            strict_request = True
        elif existing_digest is not None:
            raise BeamLiveError(f"BLIND_JUDGE checkpoint body drift: {blind_id}")
        elif strict_repair_authorized and blind_id == STRICT_JUDGE_REPAIR_ID:
            body = strict_body
            attempts = 2
            strict_request = True
        elif repair_authorized:
            body = repaired_body
            attempts = JUDGE_REPAIR_ATTEMPTS
        else:
            body = original_body
            attempts = 2
        surface.append(
            {
                "body": body,
                "body_sha256": request_digest(body),
                "custom_id": blind_id,
                "max_attempts": attempts,
                "persist_invalid_attempts": repair_authorized
                and body["max_tokens"] == JUDGE_REPAIR_MAX_TOKENS,
                "prompt_tokens": len(
                    encoding.encode(strict_prompt if strict_request else prompt)
                )
                + 8,
                "rubric_count": len(rubric),
                "slots": ["R0", "R1", "R2"],
                "strict_matrix": strict_request,
            }
        )
        for index, arm in enumerate(arm_order):
            mapping.append(
                {
                    "arm": arm,
                    "blind_id": blind_id,
                    "category": str(arm_answers[arm]["category"]),
                    "conversation_key": str(arm_answers[arm]["conversation_key"]),
                    "question_key": qkey,
                    "rubric_count": str(len(rubric)),
                    "scale": str(arm_answers[arm]["scale"]),
                    "slot": f"R{index}",
                }
            )
    if (
        len(surface) != OPTIMIZED_JUDGE_CALLS
        or len({row["custom_id"] for row in surface}) != OPTIMIZED_JUDGE_CALLS
        or len(mapping) != OPTIMIZED_READER_CALLS
    ):
        raise BeamLiveError("Judge surface count or identity failure")
    write_jsonl(RUN / "judge_surface.blind.jsonl", surface)
    write_jsonl(RUN / "judge_mapping.sealed.jsonl", mapping)
    write_json(
        RUN / "judge_surface.seal.json",
        {
            "blind_requests": len(surface),
            "mapping_sha256": file_sha256(RUN / "judge_mapping.sealed.jsonl"),
            "surface_sha256": file_sha256(RUN / "judge_surface.blind.jsonl"),
            "status": "SEALED",
        },
    )
    return surface, mapping


def parse_bundled_judge_body(
    source: dict[str, Any], body: dict[str, Any]
) -> list[dict[str, Any]] | None:
    if "error" in body or response_finish_reason(body) != "stop":
        return None
    raw = text_of(body).strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None
    if not isinstance(parsed, dict) or set(parsed) != {"evaluations"}:
        return None
    evaluations = parsed["evaluations"]
    if source.get("strict_matrix"):
        expected_slots = set(source["slots"])
        if not isinstance(evaluations, dict) or set(evaluations) != expected_slots:
            return None
        expected_indices = {
            str(index) for index in range(int(source["rubric_count"]))
        }
        normalized: list[dict[str, Any]] = []
        for slot in sorted(expected_slots):
            criteria = evaluations[slot]
            if not isinstance(criteria, dict) or set(criteria) != expected_indices:
                return None
            normalized_criteria: list[dict[str, Any]] = []
            for index in range(int(source["rubric_count"])):
                criterion = criteria[str(index)]
                if (
                    not isinstance(criterion, dict)
                    or set(criterion) != {"score", "reason"}
                ):
                    return None
                try:
                    score = float(criterion["score"])
                except (TypeError, ValueError):
                    return None
                reason = str(criterion["reason"]).strip()
                if score not in {0.0, 0.5, 1.0} or not reason:
                    return None
                normalized_criteria.append(
                    {"reason": reason, "rubric_index": index, "score": score}
                )
            normalized.append({"criteria": normalized_criteria, "slot": slot})
        return normalized
    if not isinstance(evaluations, list):
        return None
    expected_slots = set(source["slots"])
    normalized: list[dict[str, Any]] = []
    seen_slots: set[str] = set()
    for evaluation in evaluations:
        if not isinstance(evaluation, dict) or set(evaluation) != {"slot", "criteria"}:
            return None
        slot = str(evaluation["slot"])
        if slot not in expected_slots or slot in seen_slots:
            return None
        seen_slots.add(slot)
        criteria = evaluation["criteria"]
        if not isinstance(criteria, list):
            return None
        seen_indices: set[int] = set()
        normalized_criteria: list[dict[str, Any]] = []
        for criterion in criteria:
            if not isinstance(criterion, dict) or set(criterion) != {
                "rubric_index",
                "score",
                "reason",
            }:
                return None
            try:
                index = int(criterion["rubric_index"])
                score = float(criterion["score"])
            except (TypeError, ValueError):
                return None
            reason = str(criterion["reason"]).strip()
            if (
                index in seen_indices
                or index < 0
                or index >= int(source["rubric_count"])
                or score not in {0.0, 0.5, 1.0}
                or not reason
            ):
                return None
            seen_indices.add(index)
            normalized_criteria.append(
                {"reason": reason, "rubric_index": index, "score": score}
            )
        if seen_indices != set(range(int(source["rubric_count"]))):
            return None
        normalized.append(
            {
                "criteria": sorted(
                    normalized_criteria, key=lambda row: row["rubric_index"]
                ),
                "slot": slot,
            }
        )
    if seen_slots != expected_slots:
        return None
    return sorted(normalized, key=lambda row: row["slot"])


def run_judges(
    client: OpenAI,
    surface: Sequence[dict[str, Any]],
    poll_seconds: int,
    deadline_unix: float,
) -> list[dict[str, Any]]:
    def validator(source: dict[str, Any], body: dict[str, Any]) -> str | None:
        return (
            None
            if parse_bundled_judge_body(source, body) is not None
            else "invalid_bundled_judgment"
        )

    def build_record(source: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
        evaluations = parse_bundled_judge_body(source, body)
        if evaluations is None:
            raise BeamLiveError(f"Invalid bundled judgment: {source['custom_id']}")
        prompt_tokens, completion_tokens = usage_of(body)
        return {
            "body_sha256": source["body_sha256"],
            "completion_tokens": completion_tokens,
            "custom_id": source["custom_id"],
            "evaluations": evaluations,
            "finish_reason": response_finish_reason(body),
            "prompt_tokens": prompt_tokens,
        }

    existing = run_synchronous_schedule(
        client,
        surface,
        checkpoint_path=RUN / "judgments.checkpoint.blind.jsonl",
        final_path=RUN / "judgments.blind.jsonl",
        workers=JUDGE_WORKERS,
        deadline_unix=deadline_unix,
        validator=validator,
        record_builder=build_record,
        stage="BLIND_JUDGE",
    )
    if len(existing) != OPTIMIZED_JUDGE_CALLS:
        raise BeamLiveError(
            f"Expected {OPTIMIZED_JUDGE_CALLS} judgments, found {len(existing)}"
        )
    judgment_path = RUN / "judgments.blind.jsonl"
    write_json(
        RUN / "judgments.seal.json",
        {
            "judgments": OPTIMIZED_JUDGE_CALLS,
            "judgments_sha256": file_sha256(judgment_path),
            "status": "SEALED",
        },
    )
    return existing


def sign_flip_p(differences: np.ndarray, draws: int, seed: int) -> float:
    observed = abs(float(differences.mean()))
    rng = np.random.Generator(np.random.PCG64(seed))
    extreme = 0
    remaining = draws
    while remaining:
        size = min(20_000, remaining)
        signs = rng.integers(0, 2, size=(size, len(differences)), dtype=np.int8) * 2 - 1
        permuted = (signs * differences).mean(axis=1)
        extreme += int(np.count_nonzero(np.abs(permuted) >= observed))
        remaining -= size
    return (1 + extreme) / (draws + 1)


def bootstrap_interval(
    differences: np.ndarray, draws: int, seed: int, *, one_sided: bool = False
) -> tuple[float, float | None]:
    rng = np.random.Generator(np.random.PCG64(seed))
    means = np.empty(draws, dtype=np.float64)
    offset = 0
    while offset < draws:
        size = min(20_000, draws - offset)
        indices = rng.integers(0, len(differences), size=(size, len(differences)))
        means[offset : offset + size] = differences[indices].mean(axis=1)
        offset += size
    if one_sided:
        return float(np.quantile(means, 0.05)), None
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)


def classify_disposition(
    *,
    primary: float,
    primary_p: float,
    primary_low: float,
    primary_high: float,
    a0_difference: float,
    a0_lower: float,
    scale_primary: Sequence[float],
    scale_a0: Sequence[float],
    category_primary: Sequence[float],
) -> str:
    guards = (
        a0_lower > -0.01
        and all(value >= -0.01 for value in scale_primary)
        and all(value >= -0.02 for value in scale_a0)
        and all(value >= -0.03 for value in category_primary)
    )
    if primary >= 0.02 and primary_p <= 0.05 and primary_low > 0 and guards:
        return "WORKS"
    if primary > 0 and primary_p <= 0.05:
        return "GAIN_WITH_GUARDRAIL_FAILURE"
    if (
        primary <= -0.02 and primary_p <= 0.05 and primary_high < 0
    ) or (a0_difference <= -0.02 and a0_lower <= -0.01):
        return "REGRESSES"
    return "NO_DEMONSTRATED_GAIN"


def score_results(
    judgments: Sequence[dict[str, Any]], mapping: Sequence[dict[str, str]]
) -> dict[str, Any]:
    judgment_by_id = {str(row["custom_id"]): row for row in judgments}
    criterion_rows: list[dict[str, Any]] = []
    for row in mapping:
        judgment = judgment_by_id[row["blind_id"]]
        evaluations = {
            str(evaluation["slot"]): evaluation
            for evaluation in judgment["evaluations"]
        }
        evaluation = evaluations[row["slot"]]
        for criterion in evaluation["criteria"]:
            criterion_rows.append(
                {
                    **row,
                    "reason": criterion["reason"],
                    "rubric_index": int(criterion["rubric_index"]),
                    "score": float(criterion["score"]),
                }
            )
    if len(criterion_rows) != OPTIMIZED_CRITERION_SCORES:
        raise BeamLiveError(
            f"Expected {OPTIMIZED_CRITERION_SCORES} criterion scores, "
            f"found {len(criterion_rows)}"
        )
    grouped: dict[tuple[str, str], list[float]] = {}
    metadata: dict[tuple[str, str], dict[str, str]] = {}
    for row in criterion_rows:
        key = (row["question_key"], row["arm"])
        grouped.setdefault(key, []).append(float(row["score"]))
        metadata[key] = row
    question_rows = [
        {
            **metadata[key],
            "question_score": float(np.mean(scores)),
            "rubric_items": len(scores),
        }
        for key, scores in sorted(grouped.items())
    ]
    if len(question_rows) != OPTIMIZED_READER_CALLS:
        raise BeamLiveError("Question score count failure")
    qscore = {(row["question_key"], row["arm"]): row["question_score"] for row in question_rows}
    conversation_meta = {
        row["conversation_key"]: (row["scale"], row["category"])
        for row in question_rows
    }
    conversation_questions: dict[str, set[str]] = {}
    for row in question_rows:
        conversation_questions.setdefault(row["conversation_key"], set()).add(row["question_key"])
    conversation_arm: dict[tuple[str, str], float] = {}
    for conversation_key, question_keys in conversation_questions.items():
        for arm in ARMS:
            conversation_arm[(conversation_key, arm)] = float(
                np.mean([qscore[(key, arm)] for key in sorted(question_keys)])
            )
    conversations = sorted(conversation_questions)
    primary = np.array([conversation_arm[(key, T1)] - conversation_arm[(key, C0)] for key in conversations])
    a0 = np.array([conversation_arm[(key, T1)] - conversation_arm[(key, A0)] for key in conversations])
    primary_p = sign_flip_p(primary, 1_000_000, 2026082801)
    primary_low, primary_high = bootstrap_interval(primary, 200_000, 2026082802)
    a0_lower, _ = bootstrap_interval(a0, 200_000, 2026082803, one_sided=True)

    def paired_subset(left: str, right: str, field: str, value: str) -> float:
        rows = [row for row in question_rows if row[field] == value]
        keys = sorted({row["question_key"] for row in rows})
        return float(np.mean([qscore[(key, left)] - qscore[(key, right)] for key in keys]))

    scales = ["100K", "500K", "1M"]
    categories = sorted({row["category"] for row in question_rows})
    scale_primary = {scale: paired_subset(T1, C0, "scale", scale) for scale in scales}
    scale_a0 = {scale: paired_subset(T1, A0, "scale", scale) for scale in scales}
    category_primary = {
        category: paired_subset(T1, C0, "category", category)
        for category in categories
    }
    disposition = classify_disposition(
        primary=float(primary.mean()),
        primary_p=primary_p,
        primary_low=primary_low,
        primary_high=float(primary_high),
        a0_difference=float(a0.mean()),
        a0_lower=a0_lower,
        scale_primary=list(scale_primary.values()),
        scale_a0=list(scale_a0.values()),
        category_primary=list(category_primary.values()),
    )
    arm_means = {
        arm: float(np.mean([row["question_score"] for row in question_rows if row["arm"] == arm]))
        for arm in ARMS
    }
    result = {
        "a0_guardrail": {
            "difference": float(a0.mean()),
            "one_sided_95_lower": a0_lower,
        },
        "arm_means": arm_means,
        "category_t1_minus_c0": category_primary,
        "conversations": 90,
        "disposition": disposition,
        "primary": {
            "bootstrap_95": [primary_low, float(primary_high)],
            "difference": float(primary.mean()),
            "sign_flip_p": primary_p,
        },
        "questions": OPTIMIZED_QUESTIONS,
        "scale_t1_minus_a0": scale_a0,
        "scale_t1_minus_c0": scale_primary,
    }
    if (RUN / "interruption_continuation.json").exists():
        result["diagnostic_disposition"] = result["disposition"]
        result["disposition"] = "CHARACTERIZED"
        deviations = [CONTINUATION_DEVIATION]
        if (RUN / "judge_repair_runtime.json").exists():
            deviations.append(JUDGE_REPAIR_DEVIATION)
            result["registered_g_judges"] = "FAIL"
        if (RUN / "strict_judge_repair_runtime.json").exists():
            deviations.append(STRICT_JUDGE_REPAIR_DEVIATION)
        result["deviations"] = deviations
        result["registered_g_runtime"] = "FAIL"
    write_jsonl(RUN / "question_scores.jsonl", question_rows)
    write_json(RUN / "results.json", result)
    return result


def write_report(result: dict[str, Any]) -> None:
    lines = [
        "# BEAM-001 Live Result",
        "",
        f"**Disposition:** `{result['disposition']}`",
        "",
        "## Primary",
        "",
        f"T1-C0: {result['primary']['difference']:.6f}; "
        f"95% cluster bootstrap [{result['primary']['bootstrap_95'][0]:.6f}, "
        f"{result['primary']['bootstrap_95'][1]:.6f}]; "
        f"paired sign-flip p={result['primary']['sign_flip_p']:.8f}.",
        "",
        "## A0 Guardrail",
        "",
        f"T1-A0: {result['a0_guardrail']['difference']:.6f}; "
        f"one-sided 95% lower={result['a0_guardrail']['one_sided_95_lower']:.6f}.",
        "",
        "## Arm Means",
        "",
    ]
    if "deviations" in result:
        lines[4:4] = [
            f"**Deviations:** "
            f"{', '.join(f'`{value}`' for value in result['deviations'])}; "
            "registered completion gates failed.",
            "",
            f"**Diagnostic numerical disposition:** "
            f"`{result['diagnostic_disposition']}`",
            "",
        ]
    lines.extend(f"- `{arm}`: {value:.6f}" for arm, value in result["arm_means"].items())
    lines.extend(["", "## Scale Guardrails", ""])
    lines.extend(
        f"- `{scale}`: T1-C0 {result['scale_t1_minus_c0'][scale]:.6f}; "
        f"T1-A0 {result['scale_t1_minus_a0'][scale]:.6f}"
        for scale in ("100K", "500K", "1M")
    )
    lines.extend(["", "## Category Guardrails", ""])
    lines.extend(
        f"- `{category}`: {value:.6f}"
        for category, value in result["category_t1_minus_c0"].items()
    )
    path = BEAM / "BEAM_001_RESULT.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def preflight(official_repo: Path) -> tuple[list[dict[str, Any]], str]:
    expected = {
        CORPUS / "mechanism_surface.jsonl.gz": "0377df4ddafa6899f9b21c4f908a5061852b75580958dd480d31511b9261acec",
        CORPUS / "outcome_surface.sealed.jsonl.gz": "954bde7b7a5dba3d1656cb74d7c56b9bfec5acd272922957cf0c5f4aa3108943",
        EXPLORATION / "payloads.sealed.jsonl.gz": "59f12e55f7f851633b049fdb416d990eda32820ee83897cbd7b10a804f8124dd",
    }
    for path, digest in expected.items():
        if file_sha256(path) != digest:
            raise BeamLiveError(f"Input hash drift: {path}")
    reader_template, judge_template = load_prompts(official_repo)
    questions = load_questions()
    selected = optimized_question_keys(questions)
    schedule = build_reader_schedule(
        reader_template, questions, load_payloads(), selected
    )
    counts = sorted(row["prompt_tokens"] for row in schedule)
    input_tokens = sum(counts)
    charged_tokens = input_tokens + len(schedule) * READER_MAX_TOKENS
    if (
        len(schedule) != OPTIMIZED_READER_CALLS
        or input_tokens != OPTIMIZED_INPUT_TOKENS
        or charged_tokens != OPTIMIZED_CHARGED_TOKENS
    ):
        raise BeamLiveError(
            "Optimized schedule drift: "
            f"{len(schedule)} calls, {input_tokens} input, {charged_tokens} charged"
        )
    category_counts: dict[str, int] = {}
    scale_counts: dict[str, int] = {}
    conversation_counts: dict[str, int] = {}
    for key in selected:
        row = questions[key]
        category_counts[row["category"]] = category_counts.get(row["category"], 0) + 1
        scale_counts[row["scale"]] = scale_counts.get(row["scale"], 0) + 1
        conversation_counts[row["conversation_key"]] = (
            conversation_counts.get(row["conversation_key"], 0) + 1
        )
    if (
        set(category_counts.values()) != {36}
        or set(conversation_counts.values()) != {4}
        or scale_counts != {"100K": 80, "500K": 140, "1M": 140}
    ):
        raise BeamLiveError("Optimized sample balance drift")
    outcomes = load_outcomes(CORPUS / "outcome_surface.sealed.jsonl.gz")
    rubric_items = sum(len(outcomes[key]["rubric"]) for key in selected)
    if rubric_items != OPTIMIZED_RUBRIC_ITEMS:
        raise BeamLiveError(
            f"Expected {OPTIMIZED_RUBRIC_ITEMS} rubric items, found {rubric_items}"
        )
    write_json(
        RUN / "sample.json",
        {
            "category_counts": category_counts,
            "conversation_counts": len(conversation_counts),
            "question_keys": sorted(selected),
            "scale_counts": scale_counts,
            "status": "SEALED",
        },
    )
    requests_path = RUN / "reader_requests.jsonl"
    if not requests_path.exists():
        write_jsonl(requests_path, schedule)
    write_json(
        RUN / "preflight.json",
        {
            "api_requests_made_before_first_pass": 0,
            "judge_template_sha256": sha256_bytes(judge_template.encode("utf-8")),
            "bundled_judge_template_sha256": sha256_bytes(
                BUNDLED_JUDGE_TEMPLATE.encode("utf-8")
            ),
            "charged_reader_tokens": charged_tokens,
            "input_reader_tokens": input_tokens,
            "max_prompt_tokens": counts[-1],
            "judge_requests": OPTIMIZED_JUDGE_CALLS,
            "reader_requests_sha256": file_sha256(requests_path),
            "reader_requests": len(schedule),
            "reader_template_sha256": sha256_bytes(reader_template.encode("utf-8")),
            "status": "PASS",
        },
    )
    return schedule, judge_template


def run_pipeline(official_repo: Path, poll_seconds: int, pilot_only: bool) -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise BeamLiveError("OPENAI_API_KEY is missing")
    schedule, judge_template = preflight(official_repo)
    if pilot_only:
        raise BeamLiveError("Optimized design carries the excluded synchronous pilot")
    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"], max_retries=0, timeout=120.0
    )
    runtime_path = RUN / "runtime_budget.json"
    if runtime_path.exists():
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    else:
        started = time.time()
        runtime = {
            "deadline_unix": started + RUNTIME_SECONDS,
            "runtime_seconds": RUNTIME_SECONDS,
            "started_at_unix": started,
        }
        write_json(runtime_path, runtime)
    deadline_unix = float(runtime["deadline_unix"])
    write_json(
        RUN / "progress.json",
        {"stage": "PILOT_READER" if pilot_only else "POPULATION_READER", "status": "RUNNING"},
    )
    answers = run_reader(
        client,
        schedule,
        deadline_unix=deadline_unix,
    )
    seal_answers(answers)
    write_json(RUN / "progress.json", {"stage": "ANSWERS_SEALED", "status": "PASS"})
    surface, mapping = prepare_judge_surfaces(answers, judge_template)
    write_json(
        RUN / "progress.json",
        {"requests": len(surface), "stage": "BLIND_JUDGE", "status": "RUNNING"},
    )
    judgments = run_judges(client, surface, poll_seconds, deadline_unix)
    result = score_results(judgments, mapping)
    write_report(result)
    write_json(
        RUN / "progress.json",
        {"disposition": result["disposition"], "stage": "COMPLETE", "status": "PASS"},
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preflight", "pilot", "run", "score"))
    parser.add_argument("--official-repo", type=Path, default=DEFAULT_OFFICIAL_REPO)
    parser.add_argument("--poll-seconds", type=int, default=60)
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            preflight(args.official_repo)
        elif args.command == "pilot":
            run_pipeline(args.official_repo, args.poll_seconds, True)
        elif args.command == "run":
            run_pipeline(args.official_repo, args.poll_seconds, False)
        else:
            if not (RUN / "judgments.seal.json").exists():
                raise BeamLiveError("Judgment seal is missing")
            result = score_results(
                read_jsonl(RUN / "judgments.blind.jsonl"),
                read_jsonl(RUN / "judge_mapping.sealed.jsonl"),
            )
            write_report(result)
    except BeamLiveError as error:
        write_json(RUN / "failure.json", {"error": str(error), "status": "FAILED"})
        print(f"BEAM-001 failed: {error}", file=sys.stderr)
        return 1
    except Exception as error:  # noqa: BLE001
        write_json(
            RUN / "failure.json",
            {"error": str(error), "error_type": type(error).__name__, "status": "FAILED"},
        )
        print(f"BEAM-001 failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BeamLiveError",
    "bootstrap_interval",
    "build_reader_schedule",
    "classify_disposition",
    "content_id",
    "extract_string_constant",
    "parse_bundled_judge_body",
    "render_judge_prompt",
    "render_reader_prompt",
    "sign_flip_p",
]

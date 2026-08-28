"""Registered BEAM-001 GPT-4o mini reader, blind judge, and scorer."""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import tiktoken
from openai import OpenAI

from analysis.beam001_outcomes import load_outcomes
from analysis.hh002_batch import (
    BatchLedger,
    BatchRequest,
    run_scheduled,
    text_of,
    usage_of,
)


MODEL = "gpt-4o-mini-2024-07-18"
ARMS = (
    "A0_CC80_QWEN_GPU_COMMON",
    "C0_STATIC_ASPECT_QWEN_GPU_COMMON",
    "T1_PARENT_OPPORTUNITY_ASPECT_QWEN_GPU_COMMON",
)
A0, C0, T1 = ARMS
READER_MAX_TOKENS = 2048
JUDGE_MAX_TOKENS = 512
INPUT_LIMIT = 125_952
READER_DOMAIN = "beam001-reader-v1"
JUDGE_DOMAIN = "beam001-judge-v1"
ORDER_DOMAIN = "beam001-reader-order-v1"
ROOT = Path(__file__).resolve().parents[2]
BEAM = ROOT / "experiments" / "comparisons" / "beam_001"
CORPUS = BEAM / "artifacts" / "corpus"
EXPLORATION = BEAM / "artifacts" / "exploration"
RUN = BEAM / "artifacts" / "live"
DEFAULT_OFFICIAL_REPO = Path(
    r"C:\Users\muzaf\Downloads\beam_001_source\repo_3e12035532eb85768f1a7cd779832b650c4b2ef9"
)


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
) -> list[dict[str, Any]]:
    encoding = tiktoken.encoding_for_model(MODEL)
    schedule: list[dict[str, Any]] = []
    for question_key in sorted(questions):
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
    if len(schedule) != 5400 or len({row["custom_id"] for row in schedule}) != 5400:
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
) -> dict[str, dict[str, Any]]:
    results = run_scheduled(
        client,
        [(prefix, requests)],
        ledger,
        poll_seconds=poll_seconds,
        study="BEAM-001",
    )[prefix]
    failed = [request for request in requests if validator(results.get(request.custom_id, {"error": "missing"}))]
    if failed:
        retry_prefix = f"{prefix}.retry1"
        retry = run_scheduled(
            client,
            [(retry_prefix, failed)],
            ledger,
            poll_seconds=poll_seconds,
            study="BEAM-001",
        )[retry_prefix]
        results.update(retry)
    exhausted = [request.custom_id for request in requests if validator(results.get(request.custom_id, {"error": "missing"}))]
    if exhausted:
        raise BeamLiveError(f"{prefix} exhausted one retry for {len(exhausted)} request(s)")
    return results


def run_reader(
    client: OpenAI,
    schedule: Sequence[dict[str, Any]],
    *,
    pilot_only: bool,
    poll_seconds: int,
) -> list[dict[str, Any]]:
    answers_path = RUN / "answers.jsonl"
    existing = read_jsonl(answers_path)
    done = {str(row["custom_id"]) for row in existing}
    pilot_keys = set(sorted({str(row["question_key"]) for row in schedule})[:2])
    target = [
        row for row in schedule
        if row["custom_id"] not in done
        and (not pilot_only or row["question_key"] in pilot_keys)
    ]
    if target:
        ledger = BatchLedger.load(RUN / "batch_ledger.json")
        prefix = "reader.pilot" if pilot_only else "reader.population"
        results = run_requests_with_one_retry(
            client,
            [as_batch_request(row) for row in target],
            ledger,
            prefix,
            poll_seconds,
            validate_reader_body,
        )
        merged, failed = merge_answer_results(target, results, existing)
        if failed:
            raise BeamLiveError(f"Unexpected failed reader results: {failed[:3]}")
        write_jsonl(answers_path, merged)
        existing = merged
    required = 6 if pilot_only else 5400
    if len(existing) < required:
        raise BeamLiveError(f"Reader stage has {len(existing)} of {required} required answers")
    if pilot_only:
        pilot_rows = [row for row in existing if row["question_key"] in pilot_keys]
        if len(pilot_rows) != 6:
            raise BeamLiveError("Pilot is not exactly six answers")
        write_json(
            RUN / "pilot.json",
            {
                "api_judge_calls": 0,
                "answers": 6,
                "question_keys": sorted(pilot_keys),
                "status": "PASS",
            },
        )
    return existing


def seal_answers(answers: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if len(answers) != 5400:
        raise BeamLiveError("Cannot seal an incomplete answer population")
    keys = {(row["question_key"], row["arm"]) for row in answers}
    if len(keys) != 5400 or any(row["finish_reason"] != "stop" or not row["answer"] for row in answers):
        raise BeamLiveError("Answer seal validity failure")
    seal = {
        "answers": 5400,
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


def prepare_judge_surfaces(
    answers: Sequence[dict[str, Any]], judge_template: str
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not (RUN / "answers.seal.json").exists():
        raise BeamLiveError("Judge construction before answer seal")
    outcomes = load_outcomes(CORPUS / "outcome_surface.sealed.jsonl.gz")
    questions = load_questions()
    surface: list[dict[str, Any]] = []
    mapping: list[dict[str, str]] = []
    for answer in sorted(answers, key=lambda row: row["custom_id"]):
        qkey, arm = str(answer["question_key"]), str(answer["arm"])
        rubric = outcomes[qkey].get("rubric")
        if not isinstance(rubric, list) or not rubric:
            raise BeamLiveError(f"Missing rubric: {qkey}")
        for index, item in enumerate(rubric):
            blind_id = content_id(JUDGE_DOMAIN, qkey, arm, str(index), sha256_bytes(answer["answer"].encode("utf-8")))
            prompt = render_judge_prompt(
                judge_template, questions[qkey]["question"], str(item), answer["answer"]
            )
            body = {
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
                "max_tokens": JUDGE_MAX_TOKENS,
            }
            surface.append(
                {
                    "blind_id": blind_id,
                    "body": body,
                    "body_sha256": request_digest(body),
                    "prompt_tokens": len(prompt) // 4 + 32,
                }
            )
            mapping.append(
                {
                    "arm": arm,
                    "blind_id": blind_id,
                    "category": str(answer["category"]),
                    "conversation_key": str(answer["conversation_key"]),
                    "question_key": qkey,
                    "rubric_index": str(index),
                    "scale": str(answer["scale"]),
                }
            )
    if len(surface) != 16275 or len({row["blind_id"] for row in surface}) != 16275:
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


def parse_judge_body(body: dict[str, Any]) -> tuple[float, str] | None:
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
    if not isinstance(parsed, dict) or set(parsed) != {"score", "reason"}:
        return None
    try:
        score = float(parsed["score"])
    except (TypeError, ValueError):
        return None
    reason = str(parsed["reason"]).strip()
    if score not in {0.0, 0.5, 1.0} or not reason:
        return None
    return score, reason


def validate_judge_body(body: dict[str, Any]) -> str | None:
    return None if parse_judge_body(body) is not None else "invalid_judgment"


def run_judges(
    client: OpenAI,
    surface: Sequence[dict[str, Any]],
    poll_seconds: int,
) -> list[dict[str, Any]]:
    path = RUN / "judgments.blind.jsonl"
    existing = read_jsonl(path)
    done = {str(row["blind_id"]) for row in existing}
    pending = [row for row in surface if row["blind_id"] not in done]
    if pending:
        requests = [
            BatchRequest(
                custom_id=str(row["blind_id"]),
                body=dict(row["body"]),
                approx_tokens=int(row["prompt_tokens"]) + JUDGE_MAX_TOKENS,
            )
            for row in pending
        ]
        ledger = BatchLedger.load(RUN / "batch_ledger.json")
        results = run_requests_with_one_retry(
            client, requests, ledger, "judge.population", poll_seconds, validate_judge_body
        )
        by_id = {str(row["blind_id"]): dict(row) for row in existing}
        surface_by_id = {str(row["blind_id"]): row for row in pending}
        for blind_id, body in results.items():
            parsed = parse_judge_body(body)
            if parsed is None:
                raise BeamLiveError(f"Invalid judgment after retry: {blind_id}")
            score, reason = parsed
            prompt_tokens, completion_tokens = usage_of(body)
            by_id[blind_id] = {
                "blind_id": blind_id,
                "body_sha256": surface_by_id[blind_id]["body_sha256"],
                "completion_tokens": completion_tokens,
                "finish_reason": response_finish_reason(body),
                "prompt_tokens": prompt_tokens,
                "reason": reason,
                "score": score,
            }
        write_jsonl(path, sorted(by_id.values(), key=lambda row: row["blind_id"]))
        existing = list(by_id.values())
    if len(existing) != 16275:
        raise BeamLiveError(f"Expected 16275 judgments, found {len(existing)}")
    write_json(
        RUN / "judgments.seal.json",
        {
            "judgments": 16275,
            "judgments_sha256": file_sha256(path),
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
    score_by_blind = {str(row["blind_id"]): float(row["score"]) for row in judgments}
    criterion_rows = [{**row, "score": score_by_blind[row["blind_id"]]} for row in mapping]
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
    if len(question_rows) != 5400:
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
                np.mean([qscore[(key, arm)] for key in question_keys])
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
        "questions": 1800,
        "scale_t1_minus_a0": scale_a0,
        "scale_t1_minus_c0": scale_primary,
    }
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
    schedule = build_reader_schedule(reader_template, load_questions(), load_payloads())
    counts = sorted(row["prompt_tokens"] for row in schedule)
    if counts[0] != 28518 or counts[-1] != 64742:
        raise BeamLiveError(f"Prompt token audit drift: {counts[0]}..{counts[-1]}")
    requests_path = RUN / "reader_requests.jsonl"
    if not requests_path.exists():
        write_jsonl(requests_path, schedule)
    write_json(
        RUN / "preflight.json",
        {
            "api_requests_made_before_first_pass": 0,
            "judge_template_sha256": sha256_bytes(judge_template.encode("utf-8")),
            "max_prompt_tokens": counts[-1],
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
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0)
    write_json(
        RUN / "progress.json",
        {"stage": "PILOT_READER" if pilot_only else "POPULATION_READER", "status": "RUNNING"},
    )
    answers = run_reader(client, schedule, pilot_only=pilot_only, poll_seconds=poll_seconds)
    if pilot_only:
        write_json(RUN / "progress.json", {"stage": "PILOT_READER", "status": "PASS"})
        return
    seal_answers(answers)
    write_json(RUN / "progress.json", {"stage": "ANSWERS_SEALED", "status": "PASS"})
    surface, mapping = prepare_judge_surfaces(answers, judge_template)
    write_json(
        RUN / "progress.json",
        {"requests": len(surface), "stage": "BLIND_JUDGE", "status": "RUNNING"},
    )
    judgments = run_judges(client, surface, poll_seconds)
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
    "parse_judge_body",
    "render_judge_prompt",
    "render_reader_prompt",
    "sign_flip_p",
]

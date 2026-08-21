"""Batch transport for HH-002.

The synchronous path is unusable on this account: the chat endpoint reports
``x-ratelimit-limit-requests: 50`` on a 24-hour reset, and the study needs
roughly eighteen thousand generation and judging calls.  The Batch API is
metered separately, so it is the only transport on which this run completes at
all.  It also costs half as much.

**This is transport, not method.**  A batch line carries the same ``model``,
the same ``messages`` and the same ``temperature`` as the synchronous call in
``hh002_harness.MeteredClient``; the request bodies are built by that module's
own render functions.  What changes is when the answer comes back.

Batch jobs outlive a process, so every submission is recorded to disk with its
input digest.  A resumed run adopts jobs already in flight rather than paying
for them twice.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from analysis.hh002_harness import (
    ANSWER_SYSTEM_MESSAGE,
    DEFAULT_MODEL,
    HH002HarnessError,
    render_answer_prompt,
    render_judge_prompt,
)

#: Conservative ceiling on tokens enqueued in one batch.  The account's true
#: batch queue limit is discovered at submit time from the API's own error and
#: recorded; this is the starting guess and is halved on refusal.
DEFAULT_BATCH_TOKEN_BUDGET = 1_800_000

#: Batch lines per job, independent of tokens.  Keeps a failed job small
#: enough to resubmit cheaply.
DEFAULT_BATCH_MAX_LINES = 2_000

TERMINAL = {"completed", "failed", "expired", "cancelled"}


class HH002BatchError(RuntimeError):
    pass


@dataclass
class BatchRequest:
    custom_id: str
    body: dict[str, Any]
    approx_tokens: int

    def as_line(self) -> str:
        return json.dumps(
            {
                "custom_id": self.custom_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": self.body,
            },
            ensure_ascii=False,
        )


def answer_request(
    custom_id: str, question: str, context: str, model: str = DEFAULT_MODEL
) -> BatchRequest:
    """One generation call, identical in body to the synchronous path."""
    prompt = render_answer_prompt(question, context)
    return BatchRequest(
        custom_id=custom_id,
        body={
            "model": model,
            "messages": [
                {"role": "system", "content": ANSWER_SYSTEM_MESSAGE},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        },
        approx_tokens=(len(prompt) + len(ANSWER_SYSTEM_MESSAGE)) // 4 + 64,
    )


def judge_request(
    custom_id: str,
    question: str,
    gold_answer: str,
    generated_answer: str,
    model: str = DEFAULT_MODEL,
) -> BatchRequest:
    """One judging call, identical in body to the synchronous path."""
    prompt = render_judge_prompt(question, gold_answer, generated_answer)
    return BatchRequest(
        custom_id=custom_id,
        body={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        },
        approx_tokens=len(prompt) // 4 + 32,
    )


def chunk_requests(
    requests: Sequence[BatchRequest],
    token_budget: int = DEFAULT_BATCH_TOKEN_BUDGET,
    max_lines: int = DEFAULT_BATCH_MAX_LINES,
) -> list[list[BatchRequest]]:
    """Split into jobs that fit the queue limit.

    A single request larger than the budget still gets its own job rather than
    being dropped: refusing it is the API's call to make, not this function's.
    """
    jobs: list[list[BatchRequest]] = []
    current: list[BatchRequest] = []
    used = 0
    for request in requests:
        if current and (
            used + request.approx_tokens > token_budget
            or len(current) >= max_lines
        ):
            jobs.append(current)
            current, used = [], 0
        current.append(request)
        used += request.approx_tokens
    if current:
        jobs.append(current)
    return jobs


@dataclass
class BatchLedger:
    """Every job this study has submitted, so nothing is paid for twice."""

    path: Path
    jobs: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "BatchLedger":
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return cls(path=path, jobs=payload.get("jobs", {}))
        return cls(path=path)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"jobs": self.jobs}, indent=2, sort_keys=True),
            encoding="utf-8",
            newline="\n",
        )
        tmp.replace(self.path)

    def record(self, key: str, **fields: Any) -> None:
        self.jobs.setdefault(key, {}).update(fields)
        self.save()

    def get(self, key: str) -> dict[str, Any]:
        return self.jobs.get(key, {})


def _digest(requests: Sequence[BatchRequest]) -> str:
    h = hashlib.sha256()
    for request in requests:
        h.update(request.as_line().encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def submit_job(
    client: Any,
    requests: Sequence[BatchRequest],
    ledger: BatchLedger,
    key: str,
    log: Callable[[str], None] = print,
) -> str:
    """Upload and enqueue one job, or adopt one already in flight."""
    digest = _digest(requests)
    known = ledger.get(key)
    if known.get("digest") == digest and known.get("batch_id"):
        log(f"    {key}: adopting {known['batch_id']} ({known.get('status')})")
        return str(known["batch_id"])

    payload = ("\n".join(r.as_line() for r in requests) + "\n").encode("utf-8")
    uploaded = client.files.create(
        file=(f"{key}.jsonl", payload), purpose="batch"
    )
    batch = client.batches.create(
        input_file_id=uploaded.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={"study": "HH-002", "key": key},
    )
    ledger.record(
        key,
        digest=digest,
        batch_id=batch.id,
        input_file_id=uploaded.id,
        lines=len(requests),
        approx_tokens=sum(r.approx_tokens for r in requests),
        status=batch.status,
        submitted_at=time.time(),
    )
    log(f"    {key}: submitted {batch.id} ({len(requests)} lines)")
    return batch.id


def poll_job(
    client: Any, batch_id: str, ledger: BatchLedger, key: str
) -> dict[str, Any]:
    batch = client.batches.retrieve(batch_id)
    counts = batch.request_counts
    ledger.record(
        key,
        status=batch.status,
        completed=getattr(counts, "completed", 0),
        failed=getattr(counts, "failed", 0),
        total=getattr(counts, "total", 0),
        output_file_id=batch.output_file_id,
        error_file_id=batch.error_file_id,
    )
    return {
        "status": batch.status,
        "completed": getattr(counts, "completed", 0),
        "failed": getattr(counts, "failed", 0),
        "total": getattr(counts, "total", 0),
        "output_file_id": batch.output_file_id,
        "error_file_id": batch.error_file_id,
    }


def collect_job(client: Any, output_file_id: str) -> dict[str, dict[str, Any]]:
    """Map ``custom_id`` to the response body.

    Batch output is not ordered, which is why every line carries its own id and
    nothing here relies on position.
    """
    raw = client.files.content(output_file_id).read().decode("utf-8")
    out: dict[str, dict[str, Any]] = {}
    for line in raw.strip().split("\n"):
        if not line:
            continue
        record = json.loads(line)
        custom_id = record["custom_id"]
        response = record.get("response") or {}
        if record.get("error") or response.get("status_code") != 200:
            out[custom_id] = {"error": record.get("error") or response}
            continue
        out[custom_id] = response["body"]
    return out


def usage_of(body: dict[str, Any]) -> tuple[int, int]:
    usage = body.get("usage") or {}
    return int(usage.get("prompt_tokens", 0)), int(
        usage.get("completion_tokens", 0)
    )


def text_of(body: dict[str, Any]) -> str:
    try:
        return (body["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError):
        return ""


def submit_only(
    client: Any,
    requests: Sequence[BatchRequest],
    ledger: BatchLedger,
    prefix: str,
    token_budget: int = DEFAULT_BATCH_TOKEN_BUDGET,
    max_lines: int = DEFAULT_BATCH_MAX_LINES,
    log: Callable[[str], None] = print,
) -> list[str]:
    """Enqueue every job for one prefix and return immediately.

    Queue latency dominates a batch job and does not scale with its size, so
    every arm's work is enqueued before anything is waited on.  Submitting
    arm by arm would serialise that latency once per arm per stage.
    """
    jobs = chunk_requests(requests, token_budget, max_lines)
    log(
        f"  {prefix}: {len(requests)} requests in {len(jobs)} job(s), "
        f"~{sum(r.approx_tokens for r in requests):,} tokens"
    )
    keys = [f"{prefix}.{i:03d}" for i in range(len(jobs))]
    for key, job in zip(keys, jobs):
        submit_job(client, job, ledger, key, log)
    return keys


def await_and_collect(
    client: Any,
    ledger: BatchLedger,
    keys: Sequence[str],
    poll_seconds: int = 60,
    log: Callable[[str], None] = print,
) -> dict[str, dict[str, Any]]:
    """Wait on jobs already submitted, then collect them together."""
    results: dict[str, dict[str, Any]] = {}
    outstanding = {
        key: str(ledger.get(key)["batch_id"])
        for key in keys
        if ledger.get(key).get("batch_id")
    }
    while outstanding:
        for key, batch_id in list(outstanding.items()):
            state = poll_job(client, batch_id, ledger, key)
            if state["status"] not in TERMINAL:
                continue
            outstanding.pop(key)
            if state["output_file_id"]:
                results.update(collect_job(client, state["output_file_id"]))
                log(
                    f"    {key}: {state['status']}, "
                    f"{state['completed']}/{state['total']} collected"
                )
            else:
                log(f"    {key}: {state['status']} with no output")
        if outstanding:
            log(
                f"  waiting on {len(outstanding)} job(s): "
                f"{', '.join(sorted(outstanding))} ({poll_seconds}s)"
            )
            time.sleep(poll_seconds)
    return results


def run_batches(
    client: Any,
    requests: Sequence[BatchRequest],
    ledger: BatchLedger,
    prefix: str,
    poll_seconds: int = 30,
    token_budget: int = DEFAULT_BATCH_TOKEN_BUDGET,
    max_lines: int = DEFAULT_BATCH_MAX_LINES,
    log: Callable[[str], None] = print,
    wait: bool = True,
) -> dict[str, dict[str, Any]]:
    """Submit, wait, and collect.  Returns ``custom_id -> response body``."""
    jobs = chunk_requests(requests, token_budget, max_lines)
    log(
        f"  {prefix}: {len(requests)} requests in {len(jobs)} job(s), "
        f"~{sum(r.approx_tokens for r in requests):,} tokens"
    )
    keys = [f"{prefix}.{i:03d}" for i in range(len(jobs))]
    batch_ids: dict[str, str] = {}
    for key, job in zip(keys, jobs):
        batch_ids[key] = submit_job(client, job, ledger, key, log)

    if not wait:
        return {}

    results: dict[str, dict[str, Any]] = {}
    outstanding = dict(batch_ids)
    while outstanding:
        for key, batch_id in list(outstanding.items()):
            state = poll_job(client, batch_id, ledger, key)
            if state["status"] not in TERMINAL:
                continue
            outstanding.pop(key)
            if state["status"] != "completed":
                log(
                    f"    {key}: {state['status']} "
                    f"({state['failed']} failed of {state['total']})"
                )
                if not state["output_file_id"]:
                    raise HH002BatchError(
                        f"{key} ended {state['status']} with no output"
                    )
            if state["output_file_id"]:
                results.update(collect_job(client, state["output_file_id"]))
                log(
                    f"    {key}: {state['status']}, "
                    f"{state['completed']}/{state['total']} collected"
                )
        if outstanding:
            done = len(batch_ids) - len(outstanding)
            log(
                f"  {prefix}: {done}/{len(batch_ids)} jobs done, waiting "
                f"{poll_seconds}s"
            )
            time.sleep(poll_seconds)
    return results


__all__ = [
    "BatchLedger",
    "BatchRequest",
    "DEFAULT_BATCH_MAX_LINES",
    "DEFAULT_BATCH_TOKEN_BUDGET",
    "HH002BatchError",
    "answer_request",
    "chunk_requests",
    "collect_job",
    "judge_request",
    "poll_job",
    "run_batches",
    "submit_job",
    "text_of",
    "usage_of",
]

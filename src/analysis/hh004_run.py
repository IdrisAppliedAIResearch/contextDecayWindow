"""Checkpointed single-arm synchronous execution for HH-004."""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Sequence

from analysis.hh002_batch import answer_request, judge_request
from analysis.hh002_harness import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_MODEL,
    MeteredClient,
    Usage,
    deterministic_metrics,
)
from analysis.hh002_run import _read_json, _write_json
from analysis.hh002_sync_arm import RateBucket
from analysis.hh004_contexts import (
    ARM,
    EXPECTED,
    PREFLIGHT,
    RUN,
    HH004GateError,
    assert_paid_preconditions,
)
from openai import OpenAI

WORKERS = 8
TOKENS_PER_MINUTE = 170_000
ANSWER_REQUESTS_PER_MINUTE = 6.6


class HH004RunError(RuntimeError):
    pass


def _records(path: Path) -> dict[str, dict[str, Any]]:
    return {str(row["key"]): row
            for row in ((_read_json(path) or {}).get("records", []))}


def _client() -> MeteredClient:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise HH004RunError("OPENAI_API_KEY is not set")
    return MeteredClient(OpenAI(api_key=key, max_retries=0),
                         model=DEFAULT_MODEL,
                         embedding_model=DEFAULT_EMBEDDING_MODEL,
                         max_retries=0, usage=Usage())


def _contexts() -> dict[str, dict[str, Any]]:
    values = (_read_json(RUN / ARM / "contexts.json") or {}).get("items", {})
    if len(values) != EXPECTED:
        raise HH004RunError(f"HH-004 contexts are {len(values)}/{EXPECTED}")
    return values


def pilot_keys(contexts: dict[str, dict[str, Any]]) -> list[str]:
    rows = [(key, row) for key, row in contexts.items()
            if row["sample_id"] == "conv-26"]
    rows.sort(key=lambda value: int(value[1]["source_index"]))
    keys = [key for key, _ in rows[:8]]
    if len(keys) != 8:
        raise HH004RunError("HH-004 pilot is not eight items")
    return keys


def stage_counts() -> dict[str, int]:
    return {
        "answers": len(_records(RUN / ARM / "predictions.json")),
        "judgements": len(_records(RUN / ARM / "judged_r1.json")),
    }


def run_answers(*, pilot: bool) -> dict[str, Any]:
    assert_paid_preconditions()
    contexts = _contexts()
    done = _records(RUN / ARM / "predictions.json")
    keys = pilot_keys(contexts) if pilot else sorted(contexts)
    pending = [key for key in keys if key not in done]
    client = _client()
    token_bucket = RateBucket(TOKENS_PER_MINUTE)
    request_bucket = RateBucket(ANSWER_REQUESTS_PER_MINUTE)

    def one(key: str) -> tuple[str, dict[str, Any]]:
        item = contexts[key]
        estimate = answer_request(key, item["question"], item["context"],
                                  DEFAULT_MODEL).approx_tokens
        request_bucket.acquire(1.0)
        token_bucket.acquire(estimate)
        response, elapsed, usage = client.answer(item["question"], item["context"])
        return key, {
            "key": key, "sample_id": item["sample_id"],
            "source_index": item["source_index"], "category": item["category"],
            "question": item["question"], "answer": item["answer"],
            "response": response, "context_chars": item["context_chars"],
            "units_delivered": item["units_delivered"],
            "search_time": item["search_time"], "response_time": round(elapsed, 4),
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "cached_tokens": usage["cached_tokens"],
        }

    started = time.time()
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(one, key) for key in pending]
        for count, future in enumerate(as_completed(futures), start=1):
            key, row = future.result()
            with lock:
                done[key] = row
                _write_json(RUN / ARM / "predictions.json", {
                    "arm": ARM, "model": DEFAULT_MODEL, "transport": "sync",
                    "usage": client.usage.as_dict(),
                    "records": sorted(done.values(), key=lambda value: value["key"]),
                })
            if count % 10 == 0 or count == len(pending):
                print(f"answers {count}/{len(pending)} total={len(done)}/{EXPECTED} "
                      f"elapsed={(time.time()-started)/60:.1f}m", flush=True)
    return {"submitted": len(pending), "completed": len(done),
            "usage": client.usage.as_dict()}


def run_judging(*, pilot: bool) -> dict[str, Any]:
    assert_paid_preconditions()
    contexts = _contexts()
    predictions = _records(RUN / ARM / "predictions.json")
    if not pilot and len(predictions) != EXPECTED:
        raise HH004RunError("all 842 answers must be sealed before full judging")
    keys = pilot_keys(contexts) if pilot else sorted(predictions)
    if any(key not in predictions for key in keys):
        raise HH004RunError("HH-004 pilot answers are incomplete")
    done = _records(RUN / ARM / "judged_r1.json")
    pending = [key for key in keys if key not in done]
    client = _client()
    token_bucket = RateBucket(TOKENS_PER_MINUTE)

    def one(key: str) -> tuple[str, dict[str, Any]]:
        prediction = predictions[key]
        estimate = judge_request(key, prediction["question"], prediction["answer"],
                                 prediction["response"], DEFAULT_MODEL).approx_tokens
        token_bucket.acquire(estimate)
        llm_score, label = client.judge(prediction["question"],
                                        prediction["answer"], prediction["response"])
        metrics = deterministic_metrics(prediction["response"], prediction["answer"])
        return key, {
            "key": key, "sample_id": prediction["sample_id"],
            "source_index": prediction["source_index"],
            "category": prediction["category"], "llm_score": llm_score,
            "judge_label": label, "f1": metrics["f1"],
            "exact_match": metrics["exact_match"],
        }

    started = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(one, key) for key in pending]
        for count, future in enumerate(as_completed(futures), start=1):
            key, row = future.result()
            done[key] = row
            _write_json(RUN / ARM / "judged_r1.json", {
                "arm": ARM, "replicate": 1, "transport": "sync",
                "usage": client.usage.as_dict(),
                "records": sorted(done.values(), key=lambda value: value["key"]),
            })
            if count % 10 == 0 or count == len(pending):
                print(f"judgements {count}/{len(pending)} total={len(done)}/{EXPECTED} "
                      f"elapsed={(time.time()-started)/60:.1f}m", flush=True)
    return {"submitted": len(pending), "completed": len(done),
            "usage": client.usage.as_dict()}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HH-004 paid runner")
    parser.add_argument("stage", choices=("pilot", "answers", "judge"))
    args = parser.parse_args(argv)
    if args.stage == "pilot":
        answer = run_answers(pilot=True)
        judge = run_judging(pilot=True)
        result = {"answers": answer, "judge": judge}
        if answer["completed"] < 8 or judge["completed"] < 8:
            raise HH004GateError("HH-004 pilot is incomplete")
        _write_json(PREFLIGHT / "g4_paid_pilot.json", result)
    elif args.stage == "answers":
        result = run_answers(pilot=False)
    else:
        result = run_judging(pilot=False)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["pilot_keys", "run_answers", "run_judging", "stage_counts"]

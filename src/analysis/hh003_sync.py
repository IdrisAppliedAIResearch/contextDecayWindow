"""Synchronous transport authorized by HH-003 Amendment 003."""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Sequence

from analysis.hh002_harness import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_MODEL,
    MeteredClient,
    Usage,
    deterministic_metrics,
)
from analysis.hh002_batch import answer_request
from analysis.hh002_run import _read_json, _write_json, score
from analysis.hh002_sync_arm import RateBucket
from analysis.hh003_drive import ARMS, PREFLIGHT, RUN, _assert_paid_preconditions
from openai import OpenAI

WORKERS = 8
TOKENS_PER_MINUTE = 170_000
REQUESTS_PER_MINUTE = 6.6


class HH003SyncError(RuntimeError):
    pass


def _records(path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(path) or {}
    return {row["key"]: row for row in payload.get("records", [])}


def _client() -> MeteredClient:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise HH003SyncError("OPENAI_API_KEY is not set")
    return MeteredClient(
        OpenAI(api_key=key, max_retries=0),
        model=DEFAULT_MODEL,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        max_retries=0,
        usage=Usage(),
    )


def _pilot_keys(contexts: dict[str, dict[str, Any]]) -> list[str]:
    rows = [
        (key, item) for key, item in contexts.items()
        if item["sample_id"] == "conv-26"
    ]
    rows.sort(key=lambda pair: int(pair[1]["source_index"]))
    keys = [key for key, _ in rows[:8]]
    if len(keys) != 8:
        raise HH003SyncError("registered pilot prefix is not eight items")
    return keys


def run_answers(*, pilot: bool) -> dict[str, Any]:
    _assert_paid_preconditions()
    client = _client()
    contexts = {
        arm: (_read_json(RUN / arm / "contexts.json") or {})["items"]
        for arm in ARMS
    }
    done = {arm: _records(RUN / arm / "predictions.json") for arm in ARMS}
    token_bucket = RateBucket(TOKENS_PER_MINUTE)
    request_bucket = RateBucket(REQUESTS_PER_MINUTE)
    work: list[tuple[str, str]] = []
    for arm in ARMS:
        keys = _pilot_keys(contexts[arm]) if pilot else sorted(contexts[arm])
        work.extend((arm, key) for key in keys if key not in done[arm])

    def one(arm: str, key: str) -> tuple[str, str, dict[str, Any]]:
        item = contexts[arm][key]
        estimate = answer_request(
            key, item["question"], item["context"], DEFAULT_MODEL
        ).approx_tokens
        request_bucket.acquire(1.0)
        token_bucket.acquire(estimate)
        response, elapsed, usage = client.answer(item["question"], item["context"])
        return arm, key, {
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

    lock = threading.Lock()
    started = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(one, arm, key) for arm, key in work]
        for count, future in enumerate(as_completed(futures), start=1):
            arm, key, row = future.result()
            with lock:
                done[arm][key] = row
                for name in ARMS:
                    _write_json(RUN / name / "predictions.json", {
                        "arm": name, "model": DEFAULT_MODEL, "transport": "sync",
                        "usage": client.usage.as_dict(),
                        "records": sorted(done[name].values(), key=lambda value: value["key"]),
                    })
            if count % 25 == 0 or count == len(work):
                print(f"answers {count}/{len(work)} elapsed={(time.time()-started)/60:.1f}m",
                      flush=True)
    return {"submitted": len(work), "usage": client.usage.as_dict()}


def run_judging(*, pilot: bool) -> dict[str, Any]:
    _assert_paid_preconditions()
    client = _client()
    contexts = {
        arm: (_read_json(RUN / arm / "contexts.json") or {})["items"]
        for arm in ARMS
    }
    predictions = {arm: _records(RUN / arm / "predictions.json") for arm in ARMS}
    if not pilot and any(len(rows) != 1540 for rows in predictions.values()):
        raise HH003SyncError("all 3,080 answers must be sealed before full judging")
    done = {arm: _records(RUN / arm / "judged_r1.json") for arm in ARMS}
    work: list[tuple[str, str]] = []
    for arm in ARMS:
        keys = _pilot_keys(contexts[arm]) if pilot else sorted(predictions[arm])
        if any(key not in predictions[arm] for key in keys):
            raise HH003SyncError(f"{arm} answers are incomplete for judging")
        work.extend((arm, key) for key in keys if key not in done[arm])

    def one(arm: str, key: str) -> tuple[str, str, dict[str, Any]]:
        prediction = predictions[arm][key]
        llm_score, label = client.judge(
            prediction["question"], prediction["answer"], prediction["response"]
        )
        metrics = deterministic_metrics(prediction["response"], prediction["answer"])
        return arm, key, {
            "key": key, "sample_id": prediction["sample_id"],
            "source_index": prediction["source_index"],
            "category": prediction["category"], "llm_score": llm_score,
            "judge_label": label, "f1": metrics["f1"],
            "exact_match": metrics["exact_match"],
        }

    started = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(one, arm, key) for arm, key in work]
        for count, future in enumerate(as_completed(futures), start=1):
            arm, key, row = future.result()
            done[arm][key] = row
            if count % 25 == 0 or count == len(work):
                for name in ARMS:
                    _write_json(RUN / name / "judged_r1.json", {
                        "arm": name, "replicate": 1, "transport": "sync",
                        "usage": client.usage.as_dict(),
                        "records": sorted(done[name].values(), key=lambda value: value["key"]),
                    })
                print(f"judgements {count}/{len(work)} elapsed={(time.time()-started)/60:.1f}m",
                      flush=True)
    result = {"submitted": len(work), "usage": client.usage.as_dict()}
    if pilot:
        result["malformed"] = {
            arm: sum(row["judge_label"] == "__MALFORMED__" for row in done[arm].values())
            for arm in ARMS
        }
        result["status"] = "PASS" if all(len(done[arm]) >= 8 for arm in ARMS) else "FAIL"
        _write_json(PREFLIGHT / "g4_paid_pilot.json", result)
    elif all(len(done[arm]) == 1540 for arm in ARMS):
        summary = {arm: score(list(done[arm].values())) for arm in ARMS}
        _write_json(RUN / "summary.json", {
            "model": DEFAULT_MODEL, "transport": "sync", "arms": summary
        })
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HH-003 synchronous transport")
    parser.add_argument("stage", choices=("pilot", "answers", "judge"))
    args = parser.parse_args(argv)
    if args.stage == "pilot":
        run_answers(pilot=True)
        result = run_judging(pilot=True)
    elif args.stage == "answers":
        result = run_answers(pilot=False)
    else:
        result = run_judging(pilot=False)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

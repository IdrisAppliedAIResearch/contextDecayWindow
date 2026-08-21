"""Run one arm through the synchronous endpoint, under a token budget.

The full-context arm is 1,540 requests of roughly 26,000 tokens each - forty
million tokens, 77% of this study's generation, and 103 of its 134 batch jobs.
Behind the batch queue's measured throughput it alone would take ten hours.

The synchronous endpoint is metered separately from batch, so this arm runs
here while everything else runs through batch and the two do not compete.
Its ceilings, read from the live response headers, are 200,000 tokens per
minute and 10,000 requests per day.

Which ceiling binds depends on the arm, and for this one it is the requests.
At 26,000 tokens a call the token budget would allow about 6.5 calls a minute;
the daily request bucket refills at about 6.9. So 1,540 calls take roughly
four hours whatever the token budget says, and pacing to the *request* refill
is what keeps the run alive.

The limiter is the point. An earlier attempt to drive this endpoint with a
thread pool and 429-backoff drained the daily bucket in minutes, because a
refused request still counts against it. Both budgets are charged before a
call is sent rather than after it is refused.
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from analysis.hh002_batch_run import build_contexts, log
from analysis.hh002_dataset import load_corpus
from analysis.hh002_harness import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_MODEL,
    Usage,
    price,
)
from analysis.hh002_run import (
    ARTIFACTS,
    DATASET,
    Prediction,
    _read_json,
    _write_json,
    build_arms,
    make_client,
)

#: The account's synchronous ceiling, read from ``x-ratelimit-limit-tokens``.
TOKENS_PER_MINUTE_LIMIT = 200_000

#: What to actually spend.  Headroom covers the estimate being low - measured
#: at about 9% low on the RAG arm - and leaves room for the judge if it ever
#: shares this endpoint.
TOKENS_PER_MINUTE_TARGET = 170_000

#: The account's daily request bucket, read from
#: ``x-ratelimit-limit-requests`` / ``x-ratelimit-reset-requests``: 10,000 on a
#: 24-hour reset, which refills continuously at about 6.9 a minute.
REQUESTS_PER_DAY_LIMIT = 10_000

#: For a 26,000-token arm this, not the token budget, is what binds: 170,000
#: tokens a minute would allow 6.5 requests and the daily bucket allows 6.9.
#: Pacing to the refill rate matters because a refused request still counts
#: against the bucket - an earlier unpaced run drained it in minutes and then
#: could make no progress at all.
REQUESTS_PER_MINUTE_TARGET = 6.6


class RateBucket:
    """Continuously refilling budget, shared across threads.

    Used for both tokens per minute and requests per minute; the units are
    the caller's business.
    """

    def __init__(self, per_minute: float) -> None:
        self.per_minute = float(per_minute)
        self.capacity = float(per_minute)
        self._available = float(per_minute)
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, amount: float) -> None:
        """Block until ``amount`` is available, then spend it.

        A request larger than the whole per-minute budget would never be
        satisfiable, so it is clamped to the capacity: it waits for a full
        bucket and then proceeds rather than deadlocking.
        """
        want = min(float(amount), self.capacity)
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._updated
                self._updated = now
                self._available = min(
                    self.capacity,
                    self._available + elapsed * self.per_minute / 60.0,
                )
                if self._available >= want:
                    self._available -= want
                    return
                deficit = want - self._available
            time.sleep(min(deficit * 60.0 / self.per_minute, 5.0))


def run_sync_arm(
    arm_name: str,
    budget: int,
    workers: int,
    tokens_per_minute: int,
    requests_per_minute: float,
    base: Path,
    model: str,
    embedding_model: str,
) -> int:
    conversations = load_corpus(DATASET)
    arm = build_arms([arm_name], budget)[0]
    usage = Usage()
    client = make_client(model, embedding_model, usage, base / "embeddings.db")

    log(f"[{arm_name}] contexts")
    contexts = build_contexts(arm, conversations, client, base / arm_name)

    path = base / arm_name / "predictions.json"
    done = {r["key"]: r for r in (_read_json(path) or {}).get("records", [])}
    pending = [k for k in sorted(contexts) if k not in done]
    log(f"[{arm_name}] {len(done)} done, {len(pending)} pending")
    if not pending:
        return 0

    tokens = RateBucket(tokens_per_minute)
    requests = RateBucket(requests_per_minute)
    lock = threading.Lock()
    started = time.time()
    completed = 0
    failed = 0

    def one(key: str) -> tuple[str, dict[str, Any] | None]:
        item = contexts[key]
        # Charge the bucket before sending, not after being refused.
        estimate = len(item["context"]) // 4 + len(item["question"]) // 4 + 128
        # Requests first: on a long-context arm the daily request bucket runs
        # out long before the per-minute token budget does.
        requests.acquire(1)
        tokens.acquire(estimate)
        try:
            response, elapsed, call_usage = client.answer(
                item["question"], item["context"]
            )
        except Exception as exc:  # noqa: BLE001
            log(f"    {key}: {str(exc)[:120]}")
            return key, None
        return key, asdict(Prediction(
            sample_id=item["sample_id"],
            source_index=item["source_index"],
            category=item["category"],
            question=item["question"],
            answer=item["answer"],
            response=response,
            context_chars=item["context_chars"],
            units_delivered=item["units_delivered"],
            search_time=item["search_time"],
            response_time=round(elapsed, 4),
            prompt_tokens=call_usage["prompt_tokens"],
            completion_tokens=call_usage["completion_tokens"],
            cached_tokens=call_usage["cached_tokens"],
        )) | {"key": key}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, key) for key in pending]
        for future in as_completed(futures):
            key, record = future.result()
            with lock:
                if record is None:
                    failed += 1
                else:
                    done[key] = record
                    completed += 1
                if completed and completed % 25 == 0:
                    _write_json(path, {
                        "arm": arm_name, "model": model, "transport": "sync",
                        "failures": failed,
                        "records": sorted(done.values(), key=lambda r: r["key"]),
                    })
                    rate = completed / max((time.time() - started) / 60, 1e-9)
                    remaining = (len(pending) - completed) / max(rate, 1e-9)
                    log(
                        f"[{arm_name}] {len(done)}/{len(contexts)}  "
                        f"{rate:.1f}/min  ~{remaining/60:.1f}h left  "
                        f"${price(usage):.2f}  retries={usage.retries}"
                    )

    _write_json(path, {
        "arm": arm_name, "model": model, "transport": "sync",
        "failures": failed,
        "records": sorted(done.values(), key=lambda r: r["key"]),
    })
    log(f"[{arm_name}] complete: {len(done)} answers, {failed} failed, "
        f"${price(usage):.2f}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one arm synchronously")
    parser.add_argument("--arm", default="A_FULL")
    parser.add_argument("--budget", type=int, default=16000)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--tokens-per-minute", type=int,
                        default=TOKENS_PER_MINUTE_TARGET)
    parser.add_argument("--requests-per-minute", type=float,
                        default=REQUESTS_PER_MINUTE_TARGET)
    parser.add_argument("--base", type=Path, default=ARTIFACTS)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    args = parser.parse_args(argv)
    return run_sync_arm(
        args.arm, args.budget, args.workers, args.tokens_per_minute,
        args.requests_per_minute, args.base, args.model, args.embedding_model,
    )


if __name__ == "__main__":
    sys.exit(main())

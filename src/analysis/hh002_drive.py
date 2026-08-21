"""Drive HH-002 to completion unattended.

Phases, in order, with every arm's work enqueued before anything is waited on:

    contexts -> submit answers (all arms) -> collect answers
             -> submit judging (all arms) -> collect judging
             -> submit judge replicate 2 on one arm -> collect -> score

Batch queue latency dominates and does not scale with job size, so submitting
arm by arm and waiting each time would multiply the wall clock by the number of
arms.  Everything that can be in flight together, is.

Restart-safe throughout: the batch ledger holds every submitted job keyed by
the digest of its input, so a resumed run adopts jobs already in flight instead
of paying for them twice.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from analysis.hh002_batch import (
    BatchLedger,
    answer_request,
    await_and_collect,
    judge_request,
    submit_only,
    text_of,
    usage_of,
)
from analysis.hh002_batch_run import build_contexts, log
from analysis.hh002_dataset import load_corpus
from analysis.hh002_harness import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_MODEL,
    Usage,
    deterministic_metrics,
)
from analysis.hh002_run import (
    ARTIFACTS,
    DATASET,
    Prediction,
    _read_json,
    _write_json,
    build_arms,
    build_commitments,
    commitments_digest,
    make_client,
    score,
)

#: Judged twice so the judge's own run-to-run variance can be measured; named
#: in the pre-registration before any score existed.
VARIANCE_ARM = "A_RAG"


def _load_records(path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(path) or {}
    return {r["key"]: r for r in payload.get("records", [])}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Drive HH-002 to completion")
    parser.add_argument("--arms", nargs="+",
                        default=["A_RAG", "A_CDW", "A_NONE", "A_FULL",
                                 "A_CDW_NOTS"])
    parser.add_argument("--budget", type=int, default=16000)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--poll-seconds", type=int, default=90)
    parser.add_argument("--base", type=Path, default=ARTIFACTS)
    parser.add_argument("--skip-variance", action="store_true")
    args = parser.parse_args(argv)

    base = args.base
    conversations = load_corpus(DATASET)
    arms = build_arms(args.arms, args.budget)

    commitments = build_commitments(
        args.arms, args.budget, 0, args.model, args.embedding_model
    ) | {"transport": "openai batch api", "variance_arm": VARIANCE_ARM}
    digest = commitments_digest(commitments)
    _write_json(base / "commitments.json",
                {"digest": digest, "commitments": commitments})
    log(f"commitments {digest[:16]}  arms={args.arms}")

    usage = Usage()
    metered = make_client(args.model, args.embedding_model, usage,
                          base / "embeddings.db")
    raw = metered._client
    ledger = BatchLedger.load(base / "batch_ledger.json")

    # ---- phase 1: contexts ---------------------------------------------
    contexts: dict[str, dict[str, dict[str, Any]]] = {}
    for arm in arms:
        log(f"[{arm.name}] contexts")
        contexts[arm.name] = build_contexts(
            arm, conversations, metered, base / arm.name
        )
    log(f"embeddings: {usage.embedding_calls} calls, "
        f"{usage.embedding_tokens:,} tokens")

    # ---- phase 2: submit every answer job -------------------------------
    answer_keys: dict[str, list[str]] = {}
    for arm in arms:
        existing = _load_records(base / arm.name / "predictions.json")
        pending = [k for k in sorted(contexts[arm.name]) if k not in existing]
        if not pending:
            log(f"[{arm.name}] answers already collected ({len(existing)})")
            continue
        requests = [
            answer_request(
                custom_id=key,
                question=contexts[arm.name][key]["question"],
                context=contexts[arm.name][key]["context"],
                model=args.model,
            )
            for key in pending
        ]
        log(f"[{arm.name}] submitting answers")
        answer_keys[arm.name] = submit_only(
            raw, requests, ledger, f"{arm.name}.answers", log=log
        )

    # ---- phase 3: collect answers ---------------------------------------
    predictions: dict[str, list[Prediction]] = {}
    for arm in arms:
        path = base / arm.name / "predictions.json"
        done = _load_records(path)
        keys = answer_keys.get(arm.name)
        if keys:
            log(f"[{arm.name}] awaiting answers")
            results = await_and_collect(
                raw, ledger, keys, args.poll_seconds, log
            )
            failures = 0
            for key, body in results.items():
                if "error" in body:
                    failures += 1
                    continue
                prompt_tokens, completion_tokens = usage_of(body)
                item = contexts[arm.name][key]
                done[key] = asdict(Prediction(
                    sample_id=item["sample_id"],
                    source_index=item["source_index"],
                    category=item["category"],
                    question=item["question"],
                    answer=item["answer"],
                    response=text_of(body),
                    context_chars=item["context_chars"],
                    units_delivered=item["units_delivered"],
                    search_time=item["search_time"],
                    response_time=0.0,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cached_tokens=0,
                )) | {"key": key}
            _write_json(path, {
                "arm": arm.name, "model": args.model, "transport": "batch",
                "failures": failures,
                "records": sorted(done.values(), key=lambda r: r["key"]),
            })
            log(f"[{arm.name}] {len(done)} answers, {failures} failed")
        predictions[arm.name] = [
            Prediction(**{k: v for k, v in r.items() if k != "key"})
            for r in sorted(done.values(), key=lambda r: r["key"])
        ]

    # ---- phase 4: submit every judging job ------------------------------
    plan: list[tuple[str, int]] = [(arm.name, 1) for arm in arms]
    if not args.skip_variance:
        plan.append((VARIANCE_ARM, 2))

    judge_keys: dict[tuple[str, int], list[str]] = {}
    for arm_name, replicate in plan:
        rows = predictions.get(arm_name) or []
        if not rows:
            continue
        path = base / arm_name / f"judged_r{replicate}.json"
        existing = _load_records(path)
        pending = [p for p in rows if p.key not in existing]
        if not pending:
            log(f"[{arm_name}] judgements r{replicate} already collected")
            continue
        requests = [
            judge_request(
                custom_id=p.key,
                question=p.question,
                gold_answer=p.answer,
                generated_answer=p.response,
                model=args.model,
            )
            for p in pending
        ]
        log(f"[{arm_name}] submitting judging r{replicate}")
        judge_keys[(arm_name, replicate)] = submit_only(
            raw, requests, ledger, f"{arm_name}.judge.r{replicate}", log=log
        )

    # ---- phase 5: collect judging ---------------------------------------
    for arm_name, replicate in plan:
        rows = predictions.get(arm_name) or []
        if not rows:
            continue
        path = base / arm_name / f"judged_r{replicate}.json"
        done = _load_records(path)
        keys = judge_keys.get((arm_name, replicate))
        if keys:
            log(f"[{arm_name}] awaiting judging r{replicate}")
            results = await_and_collect(
                raw, ledger, keys, args.poll_seconds, log
            )
            by_key = {p.key: p for p in rows}
            for key, body in results.items():
                prediction = by_key[key]
                if "error" in body:
                    label, llm_score = "__MALFORMED__", 0
                else:
                    try:
                        label = str(json.loads(text_of(body))["label"])
                    except Exception:  # noqa: BLE001
                        label = "__MALFORMED__"
                    llm_score = 1 if label == "CORRECT" else 0
                metrics = deterministic_metrics(
                    prediction.response, prediction.answer
                )
                done[key] = {
                    "key": key,
                    "sample_id": prediction.sample_id,
                    "source_index": prediction.source_index,
                    "category": prediction.category,
                    "llm_score": llm_score,
                    "judge_label": label,
                    "f1": metrics["f1"],
                    "exact_match": metrics["exact_match"],
                }
            _write_json(path, {
                "arm": arm_name, "replicate": replicate, "transport": "batch",
                "records": sorted(done.values(), key=lambda r: r["key"]),
            })
        if done:
            result = score(list(done.values()))
            log(f"[{arm_name}] r{replicate} llm_score="
                f"{result['llm_score']*100:.2f}%  f1={result['f1']:.4f}  "
                f"n={result['n']}")

    log("HH-002 drive complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())

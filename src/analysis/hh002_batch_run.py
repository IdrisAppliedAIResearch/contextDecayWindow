"""HH-002 end to end over the Batch API.

Five stages, each resumable, each checkpointed to disk:

1. ``contexts``  - build the memory block every arm delivers for every scored
   question.  Embeddings only; no generation.
2. ``answers``   - one batch job per chunk of generation calls.
3. ``predictions`` - collect answers into the same record shape the synchronous
   runner writes, so the analysis module cannot tell which transport was used.
4. ``judge``     - one batch job per chunk of judging calls, over sealed answers.
5. ``score``     - the leaderboard, G-CTRL, and the paired contrasts.

Answers are generated for every arm before any judging is submitted.  That is
not an implementation detail: it is the seal.  No judgement exists while any
answer can still be regenerated.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from analysis.hh002_arms import Arm
from analysis.hh002_batch import (
    BatchLedger,
    BatchRequest,
    answer_request,
    judge_request,
    run_batches,
    text_of,
    usage_of,
)
from analysis.hh002_dataset import Conversation, load_corpus
from analysis.hh002_harness import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_MODEL,
    MeteredClient,
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


class HH002BatchRunError(RuntimeError):
    pass


def log(message: str) -> None:
    print(message, flush=True)


# --------------------------------------------------------------------------
# Stage 1 - contexts
# --------------------------------------------------------------------------


def build_contexts(
    arm: Arm,
    conversations: Sequence[Conversation],
    client: MeteredClient,
    out_dir: Path,
) -> dict[str, dict[str, Any]]:
    """Every memory block this arm delivers, keyed by item.

    Cached to disk: retrieval is deterministic given the embeddings, and
    re-running it would re-spend the embedding budget for no change.
    """
    # A_FULL hands every item the whole conversation and A_NONE hands every
    # item nothing.  Caching either means writing 1,540 copies of a 94 KB
    # string to disk once per conversation - about 1.5 GB of writes for a
    # value that costs no API call and no measurable time to rebuild.
    cacheable = getattr(arm, "cacheable_contexts", True)
    path = out_dir / "contexts.json"
    expected = {
        f"{c.sample_id}#{q.source_index}"
        for c in conversations
        for q in c.scored_questions
    }
    items: dict[str, dict[str, Any]] = {}
    if cacheable:
        cached = _read_json(path)
        if cached and cached.get("arm") == arm.name:
            items = cached["items"]
            missing = expected - set(items)
            if not missing:
                log(f"  [{arm.name}] contexts cached ({len(items)})")
                return items
            # A partial cache is a resumed run, not a finished one.  Adopting
            # it wholesale would silently score this arm on fewer items than
            # the arms it is compared against.
            log(
                f"  [{arm.name}] contexts partial: {len(items)} cached, "
                f"{len(missing)} missing"
            )

    for index, conversation in enumerate(conversations, start=1):
        if all(
            f"{conversation.sample_id}#{q.source_index}" in items
            for q in conversation.scored_questions
        ):
            continue
        state = arm.prepare(conversation, client)
        for question in conversation.scored_questions:
            context, search_time, detail = arm.context(state, question, client)
            items[f"{conversation.sample_id}#{question.source_index}"] = {
                "sample_id": conversation.sample_id,
                "source_index": question.source_index,
                "category": question.category,
                "question": question.question,
                "answer": question.answer,
                "context": context,
                "context_chars": detail.get("chars", len(context)),
                "units_delivered": detail.get("units_delivered", 0),
                "search_time": round(search_time, 4),
            }
        log(
            f"  [{arm.name}] {conversation.sample_id} "
            f"({index}/{len(conversations)}) {len(items)} contexts  "
            f"embed_calls={client.usage.embedding_calls}"
        )
        if cacheable:
            _write_json(path, {"arm": arm.name, "items": items})
    if cacheable:
        _write_json(path, {"arm": arm.name, "items": items})
    return items


# --------------------------------------------------------------------------
# Stage 2/3 - answers
# --------------------------------------------------------------------------


def generate_answers(
    arm_name: str,
    contexts: dict[str, dict[str, Any]],
    client: Any,
    ledger: BatchLedger,
    out_dir: Path,
    model: str,
    wait: bool,
    poll_seconds: int,
) -> list[Prediction] | None:
    path = out_dir / "predictions.json"
    cached = _read_json(path)
    done = {r["key"]: r for r in (cached or {}).get("records", [])}
    pending = [k for k in sorted(contexts) if k not in done]
    if not pending:
        log(f"  [{arm_name}] all {len(done)} answers present")
        return _as_predictions(done)

    requests = [
        answer_request(
            custom_id=key,
            question=contexts[key]["question"],
            context=contexts[key]["context"],
            model=model,
        )
        for key in pending
    ]
    results = run_batches(
        client, requests, ledger, f"{arm_name}.answers",
        poll_seconds=poll_seconds, log=log, wait=wait,
    )
    if not wait:
        return None

    failures = 0
    for key, body in results.items():
        if "error" in body:
            failures += 1
            continue
        prompt_tokens, completion_tokens = usage_of(body)
        item = contexts[key]
        done[key] = asdict(
            Prediction(
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
            )
        ) | {"key": key}
    _write_json(
        path,
        {
            "arm": arm_name,
            "model": model,
            "transport": "batch",
            "failures": failures,
            "records": sorted(done.values(), key=lambda r: r["key"]),
        },
    )
    log(f"  [{arm_name}] {len(done)} answers collected, {failures} failed")
    return _as_predictions(done)


def _as_predictions(rows: dict[str, dict[str, Any]]) -> list[Prediction]:
    return [
        Prediction(**{k: v for k, v in row.items() if k != "key"})
        for row in sorted(rows.values(), key=lambda r: r["key"])
    ]


# --------------------------------------------------------------------------
# Stage 4 - judging
# --------------------------------------------------------------------------


def judge_answers(
    arm_name: str,
    predictions: Sequence[Prediction],
    client: Any,
    ledger: BatchLedger,
    out_dir: Path,
    model: str,
    replicate: int,
    wait: bool,
    poll_seconds: int,
) -> list[dict[str, Any]] | None:
    path = out_dir / f"judged_r{replicate}.json"
    cached = _read_json(path)
    done = {r["key"]: r for r in (cached or {}).get("records", [])}
    by_key = {p.key: p for p in predictions}
    pending = [k for k in sorted(by_key) if k not in done]
    if not pending:
        log(f"  [{arm_name}] all {len(done)} judgements present (r{replicate})")
        return sorted(done.values(), key=lambda r: r["key"])

    requests = [
        judge_request(
            custom_id=key,
            question=by_key[key].question,
            gold_answer=by_key[key].answer,
            generated_answer=by_key[key].response,
            model=model,
        )
        for key in pending
    ]
    results = run_batches(
        client, requests, ledger, f"{arm_name}.judge.r{replicate}",
        poll_seconds=poll_seconds, log=log, wait=wait,
    )
    if not wait:
        return None

    for key, body in results.items():
        prediction = by_key[key]
        if "error" in body:
            label, llm_score = "__MALFORMED__", 0
        else:
            content = text_of(body)
            try:
                label = str(json.loads(content)["label"])
            except Exception:  # noqa: BLE001
                label = "__MALFORMED__"
            llm_score = 1 if label == "CORRECT" else 0
        metrics = deterministic_metrics(prediction.response, prediction.answer)
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
    _write_json(
        path,
        {
            "arm": arm_name,
            "replicate": replicate,
            "transport": "batch",
            "records": sorted(done.values(), key=lambda r: r["key"]),
        },
    )
    return sorted(done.values(), key=lambda r: r["key"])


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run HH-002 over the Batch API")
    parser.add_argument("--arms", nargs="+",
                        default=["A_RAG", "A_FULL", "A_CDW", "A_CDW_NOTS", "A_NONE"])
    parser.add_argument("--budget", type=int, default=16000)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--judge-replicate", type=int, default=1)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--stage", default="all",
                        choices=["contexts", "answers", "judge", "score", "all"])
    parser.add_argument("--no-wait", action="store_true",
                        help="submit jobs and exit without polling")
    parser.add_argument("--conversations", nargs="*", default=None)
    parser.add_argument("--limit-questions", type=int, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    base = args.out or ARTIFACTS
    conversations = load_corpus(DATASET)
    if args.conversations:
        wanted = set(args.conversations)
        conversations = tuple(c for c in conversations if c.sample_id in wanted)
    if args.limit_questions:
        conversations = tuple(
            Conversation(
                sample_id=c.sample_id, speaker_a=c.speaker_a,
                speaker_b=c.speaker_b, turns=c.turns,
                questions=tuple(c.scored_questions[: args.limit_questions]),
            )
            for c in conversations
        )

    arms = build_arms(args.arms, args.budget)
    commitments = build_commitments(
        args.arms, args.budget, 0, args.model, args.embedding_model
    ) | {"transport": "openai batch api", "judge_replicate": args.judge_replicate}
    digest = commitments_digest(commitments)
    _write_json(base / "commitments.json",
                {"digest": digest, "commitments": commitments})
    n_questions = sum(len(c.scored_questions) for c in conversations)
    log(f"commitments {digest[:16]}  arms={args.arms}  questions={n_questions}")

    usage = Usage()
    metered = make_client(args.model, args.embedding_model, usage)
    raw = metered._client  # batch calls take the bare client
    ledger = BatchLedger.load(base / "batch_ledger.json")
    wait = not args.no_wait

    # -- stage 1 ----------------------------------------------------------
    contexts: dict[str, dict[str, dict[str, Any]]] = {}
    for arm in arms:
        log(f"[{arm.name}] contexts")
        contexts[arm.name] = build_contexts(
            arm, conversations, metered, base / arm.name
        )
    log(f"embeddings: {usage.embedding_calls} calls, "
        f"{usage.embedding_tokens:,} tokens")
    if args.stage == "contexts":
        return 0

    # -- stage 2/3 --------------------------------------------------------
    predictions: dict[str, list[Prediction]] = {}
    for arm in arms:
        log(f"[{arm.name}] answers")
        got = generate_answers(
            arm.name, contexts[arm.name], raw, ledger, base / arm.name,
            args.model, wait, args.poll_seconds,
        )
        if got is None:
            log(f"[{arm.name}] submitted, not waiting")
            continue
        predictions[arm.name] = got
    if args.stage == "answers" or not wait:
        return 0

    # -- stage 4 ----------------------------------------------------------
    judged: dict[str, list[dict[str, Any]]] = {}
    for arm in arms:
        if arm.name not in predictions:
            continue
        log(f"[{arm.name}] judging r{args.judge_replicate}")
        rows = judge_answers(
            arm.name, predictions[arm.name], raw, ledger, base / arm.name,
            args.model, args.judge_replicate, wait, args.poll_seconds,
        )
        if rows is not None:
            judged[arm.name] = rows
    if args.stage == "judge":
        return 0

    # -- stage 5 ----------------------------------------------------------
    summary = {}
    for name, rows in judged.items():
        result = score(rows)
        summary[name] = result
        log(f"[{name}] llm_score={result['llm_score']*100:.2f}%  "
            f"f1={result['f1']:.4f}  n={result['n']}")
    _write_json(base / "summary.json", {
        "commitments_digest": digest,
        "transport": "batch",
        "embedding_usage": usage.as_dict(),
        "arms": summary,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())

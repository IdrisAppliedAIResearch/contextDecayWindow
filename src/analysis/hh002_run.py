"""HH-002 execution: generate, judge, score, against the paper-era harness.

Ordering is the same discipline HH-001 used and ``AGENTS.md`` §4 requires:
commitments are written and hashed before the first generation call, answers
are sealed before any judge sees them, and the judge is blind to which arm
produced the answer it is scoring - ``evaluate_llm_judge`` receives a question,
a gold answer and a generated answer, and nothing else.

Stages run independently so a long run can be resumed without re-spending:
predictions and judgements are checkpointed per arm.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from analysis.hh002_arms import (
    Arm,
    CdwArm,
    FullContextArm,
    NoMemoryArm,
    RagArm,
)
from analysis.hh002_dataset import Conversation, Question, load_corpus
from analysis.hh002_harness import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_MODEL,
    UPSTREAM,
    VENDOR_DIGESTS,
    MeteredClient,
    Usage,
    deterministic_metrics,
    price,
)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "experiments" / "comparisons" / "hh_002" / "artifacts"
DATASET = Path(r"C:\Users\muzaf\Downloads\locomo10.json")

#: The rows this rig must reproduce before any claim is made about the
#: component.  arXiv:2504.19413 Table 2, LLM-as-a-Judge column.
PUBLISHED = {
    "A_FULL": 72.90,
    "A_RAG": 60.53,
}

#: Rows the harness can produce but this run does not, because they need a
#: vendor account this study does not have.  Quoted with attribution, never
#: re-measured here.
INHERITED = {
    "Mem0": 66.88,
    "Mem0g": 68.44,
    "Zep": 65.99,
    "OpenAI memory": 52.90,
    "A-MEM": 48.38,
}


class HH002RunError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------


@dataclass
class Prediction:
    sample_id: str
    source_index: int
    category: int
    question: str
    answer: str
    response: str
    context_chars: int
    units_delivered: int
    search_time: float
    response_time: float
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int

    @property
    def key(self) -> str:
        return f"{self.sample_id}#{self.source_index}"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )
    tmp.replace(path)


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------


def run_arm(
    arm: Arm,
    conversations: Sequence[Conversation],
    client: MeteredClient,
    workers: int = 8,
    out_dir: Path | None = None,
    progress: bool = True,
) -> list[Prediction]:
    """Answer every scored question under one memory layer.

    One ``prepare`` per conversation, matching ``process_all_conversations``,
    which builds chunks once and reuses them across that conversation's
    questions.
    """
    out_dir = out_dir or (ARTIFACTS / arm.name)
    checkpoint = out_dir / "predictions.json"
    existing = _read_json(checkpoint) or {}
    done: dict[str, dict] = {r["key"]: r for r in existing.get("records", [])}

    records: list[Prediction] = []
    lock = threading.Lock()
    started = time.time()

    for index, conversation in enumerate(conversations, start=1):
        pending = [
            q
            for q in conversation.scored_questions
            if f"{conversation.sample_id}#{q.source_index}" not in done
        ]
        if not pending:
            if progress:
                print(
                    f"  [{arm.name}] {conversation.sample_id} "
                    f"({index}/{len(conversations)}) cached",
                    flush=True,
                )
            continue

        state = arm.prepare(conversation, client)

        def answer_one(question: Question) -> Prediction:
            context, search_time, detail = arm.context(state, question, client)
            response, response_time, usage = client.answer(
                question.question, context
            )
            return Prediction(
                sample_id=conversation.sample_id,
                source_index=question.source_index,
                category=question.category,
                question=question.question,
                answer=question.answer,
                response=response,
                context_chars=detail.get("chars", len(context)),
                units_delivered=detail.get("units_delivered", 0),
                search_time=round(search_time, 4),
                response_time=round(response_time, 4),
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                cached_tokens=usage["cached_tokens"],
            )

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(answer_one, q): q for q in pending}
            for future in as_completed(futures):
                prediction = future.result()
                with lock:
                    done[prediction.key] = asdict(prediction) | {
                        "key": prediction.key
                    }

        _write_json(
            checkpoint,
            {
                "arm": arm.name,
                "model": client.model,
                "embedding_model": client.embedding_model,
                "usage": client.usage.as_dict(),
                "records": sorted(done.values(), key=lambda r: r["key"]),
            },
        )
        if progress:
            elapsed = time.time() - started
            print(
                f"  [{arm.name}] {conversation.sample_id} "
                f"({index}/{len(conversations)}) "
                f"{len(done)} answered  ${price(client.usage):.2f}  "
                f"{elapsed/60:.1f} min",
                flush=True,
            )

    for row in sorted(done.values(), key=lambda r: r["key"]):
        payload = {k: v for k, v in row.items() if k != "key"}
        records.append(Prediction(**payload))
    return records


# --------------------------------------------------------------------------
# Judging
# --------------------------------------------------------------------------


def judge_arm(
    arm_name: str,
    predictions: Sequence[Prediction],
    client: MeteredClient,
    workers: int = 10,
    out_dir: Path | None = None,
    replicate: int = 1,
    progress: bool = True,
) -> list[dict[str, Any]]:
    """Score sealed answers.

    The judge sees ``(question, gold, generated)`` and never the arm name,
    which is what makes the comparison blind.  ``replicate`` writes to its own
    file so the same answer set can be scored twice and the judge's own
    run-to-run variance measured - that variance is what sets G-CTRL's
    tolerance, rather than a round number chosen in advance.
    """
    out_dir = out_dir or (ARTIFACTS / arm_name)
    checkpoint = out_dir / f"judged_r{replicate}.json"
    existing = _read_json(checkpoint) or {}
    done: dict[str, dict] = {r["key"]: r for r in existing.get("records", [])}

    pending = [p for p in predictions if p.key not in done]
    if pending:
        lock = threading.Lock()

        def judge_one(prediction: Prediction) -> dict[str, Any]:
            score, label = client.judge(
                prediction.question, prediction.answer, prediction.response
            )
            metrics = deterministic_metrics(
                prediction.response, prediction.answer
            )
            return {
                "key": prediction.key,
                "sample_id": prediction.sample_id,
                "source_index": prediction.source_index,
                "category": prediction.category,
                "llm_score": score,
                "judge_label": label,
                "f1": metrics["f1"],
                "exact_match": metrics["exact_match"],
            }

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(judge_one, p) for p in pending]
            for count, future in enumerate(as_completed(futures), start=1):
                row = future.result()
                with lock:
                    done[row["key"]] = row
                if progress and count % 250 == 0:
                    print(
                        f"  [judge {arm_name} r{replicate}] "
                        f"{count}/{len(pending)}  ${price(client.usage):.2f}",
                        flush=True,
                    )
                    _write_json(
                        checkpoint,
                        {"arm": arm_name, "replicate": replicate,
                         "records": sorted(done.values(), key=lambda r: r["key"])},
                    )

        _write_json(
            checkpoint,
            {
                "arm": arm_name,
                "replicate": replicate,
                "records": sorted(done.values(), key=lambda r: r["key"]),
            },
        )
    return sorted(done.values(), key=lambda r: r["key"])


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------


def score(judged: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """``generate_scores.py``: mean per category, then overall mean.

    The published table's column is the overall mean of ``llm_score`` over
    every scored record - not the mean of the per-category means.  Both are
    reported; ``llm_score`` is the headline.
    """
    if not judged:
        return {"n": 0}
    by_category: dict[int, list[dict]] = {}
    for row in judged:
        by_category.setdefault(int(row["category"]), []).append(row)

    def mean(rows: Sequence[dict], field: str) -> float:
        return sum(float(r[field]) for r in rows) / len(rows)

    return {
        "n": len(judged),
        "llm_score": mean(judged, "llm_score"),
        "f1": mean(judged, "f1"),
        "exact_match": mean(judged, "exact_match"),
        "malformed_judgements": sum(
            1 for r in judged if r["judge_label"] == "__MALFORMED__"
        ),
        "per_category": {
            str(category): {
                "n": len(rows),
                "llm_score": mean(rows, "llm_score"),
                "f1": mean(rows, "f1"),
            }
            for category, rows in sorted(by_category.items())
        },
    }


# --------------------------------------------------------------------------
# Commitments
# --------------------------------------------------------------------------


def build_commitments(
    arms: Sequence[str],
    budget_chars: int,
    workers: int,
    model: str,
    embedding_model: str,
) -> dict[str, Any]:
    return {
        "study": "HH-002",
        "upstream": UPSTREAM,
        "vendor_prompt_digests": VENDOR_DIGESTS,
        "model": model,
        "embedding_model": embedding_model,
        "arms": list(arms),
        "component_budget_chars": budget_chars,
        "population": {
            "conversations": 10,
            "questions_total": 1986,
            "questions_scored": 1540,
            "excluded": "category 5 (adversarial), skipped by evals.py:22",
        },
        "primary_endpoint": "llm_score, mean over the 1,540 scored records",
        "secondary_endpoint": "f1, deterministic, no model in the loop",
        "gctrl": {
            "targets": PUBLISHED,
            "rule": (
                "Both reproduced rows must land within the tolerance derived "
                "from measured judge variance. A failure is reported as a "
                "result, not an abort."
            ),
        },
        "inherited_rows_not_rerun": INHERITED,
        "workers": workers,
    }


def commitments_digest(commitments: dict[str, Any]) -> str:
    payload = json.dumps(commitments, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def make_client(
    model: str,
    embedding_model: str,
    usage: Usage | None = None,
    cache_path: Path | None = None,
):
    from openai import OpenAI

    from analysis.hh002_embed_cache import EmbedCache

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise HH002RunError("OPENAI_API_KEY is not set")
    cache = EmbedCache(cache_path or (ARTIFACTS / "embeddings.db"))
    return MeteredClient(
        OpenAI(api_key=key, max_retries=0),
        model=model,
        embedding_model=embedding_model,
        usage=usage,
        cache=cache,
    )


def build_arms(names: Sequence[str], budget: int) -> list[Arm]:
    catalogue: dict[str, Arm] = {
        "A_FULL": FullContextArm(),
        "A_RAG": RagArm(),
        # Post-hoc G-CTRL diagnostics, added after A_RAG missed its target.
        # The published row is "RAG (best variant)" - the top of a sweep the
        # paper does not fully specify - and the Makefile's run-rag recipe
        # (500/k=1) is one point in it, not necessarily the best. These
        # bracket the sweep. They are diagnostic and carry no claim about
        # this component; see HH_002_RESULTS.md.
        "A_RAG_1000_K1": RagArm(chunk_tokens=1000, k=1),
        "A_RAG_1000_K2": RagArm(chunk_tokens=1000, k=2),
        "A_RAG_500_K4": RagArm(chunk_tokens=500, k=4),
        "A_NONE": NoMemoryArm(),
        "A_CDW": CdwArm(budget=budget, with_timestamps=True, name="A_CDW"),
        "A_CDW_NOTS": CdwArm(
            budget=budget, with_timestamps=False, name="A_CDW_NOTS"
        ),
    }
    missing = [n for n in names if n not in catalogue]
    if missing:
        raise HH002RunError(f"unknown arms: {missing}")
    return [catalogue[n] for n in names]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run HH-002")
    parser.add_argument("--arms", nargs="+", default=["A_RAG"])
    parser.add_argument("--budget", type=int, default=16000)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--judge-workers", type=int, default=10)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--conversations", nargs="*", default=None,
                        help="sample_ids to restrict to (pilot mode)")
    parser.add_argument("--limit-questions", type=int, default=None,
                        help="per-conversation question cap (pilot mode)")
    parser.add_argument("--judge-replicate", type=int, default=1)
    parser.add_argument("--skip-generation", action="store_true")
    parser.add_argument("--skip-judging", action="store_true")
    parser.add_argument("--max-spend", type=float, default=20.0)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    conversations = load_corpus(DATASET)
    if args.conversations:
        wanted = set(args.conversations)
        conversations = tuple(
            c for c in conversations if c.sample_id in wanted
        )
        if not conversations:
            raise HH002RunError(f"no conversations matched {wanted}")
    if args.limit_questions:
        conversations = tuple(
            Conversation(
                sample_id=c.sample_id,
                speaker_a=c.speaker_a,
                speaker_b=c.speaker_b,
                turns=c.turns,
                questions=tuple(c.scored_questions[: args.limit_questions]),
            )
            for c in conversations
        )

    arms = build_arms(args.arms, args.budget)
    commitments = build_commitments(
        args.arms, args.budget, args.workers, args.model, args.embedding_model
    )
    digest = commitments_digest(commitments)
    base = args.out or ARTIFACTS
    _write_json(
        base / "commitments.json",
        {"digest": digest, "commitments": commitments},
    )
    print(f"commitments {digest[:16]}  arms={args.arms}  "
          f"questions={sum(len(c.scored_questions) for c in conversations)}",
          flush=True)

    usage = Usage()
    client = make_client(args.model, args.embedding_model, usage)
    summary: dict[str, Any] = {}

    for arm in arms:
        out_dir = base / arm.name
        if not args.skip_generation:
            print(f"[{arm.name}] generating", flush=True)
            predictions = run_arm(
                arm, conversations, client, args.workers, out_dir
            )
        else:
            payload = _read_json(out_dir / "predictions.json") or {"records": []}
            predictions = [
                Prediction(**{k: v for k, v in r.items() if k != "key"})
                for r in payload["records"]
            ]
        if price(usage) > args.max_spend:
            raise HH002RunError(
                f"spend ceiling reached: ${price(usage):.2f} > "
                f"${args.max_spend:.2f}"
            )

        if not args.skip_judging:
            print(f"[{arm.name}] judging r{args.judge_replicate}", flush=True)
            judged = judge_arm(
                arm.name, predictions, client, args.judge_workers,
                out_dir, args.judge_replicate,
            )
            result = score(judged)
            summary[arm.name] = result
            target = PUBLISHED.get(arm.name)
            line = (
                f"[{arm.name}] llm_score={result['llm_score']*100:.2f}%  "
                f"f1={result['f1']:.4f}  n={result['n']}"
            )
            if target is not None:
                line += f"  published={target:.2f}%  delta={result['llm_score']*100-target:+.2f}"
            print(line, flush=True)

    _write_json(
        base / "summary.json",
        {
            "commitments_digest": digest,
            "usage": usage.as_dict(),
            "usd": round(price(usage), 4),
            "published": PUBLISHED,
            "inherited": INHERITED,
            "arms": summary,
        },
    )
    print(f"\nspend ${price(usage):.2f}  {usage.as_dict()}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

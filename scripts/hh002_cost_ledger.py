"""The full cost ledger for HH-002, and an honest account of its holes.

HH-001 reported build cost, read cost, latency and store size per arm. HH-002's
run recorded the read side per item and left three of those unrecorded. This
script assembles what exists, recomputes what is deterministically
recoverable, and names what is gone.

Three provenance classes, kept apart because they are not equally strong:

  MEASURED     - read from a committed artifact. The API returned it.
  RECOMPUTED   - derived deterministically from committed inputs. The prompt a
                 call would have carried is rebuilt and tokenised with the same
                 tokeniser the model uses. Exact for prompts; completion tokens
                 are measured where stored and omitted where not.
  UNAVAILABLE  - not recorded and not recoverable. Named, never estimated.

The one genuinely lost quantity is per-request generation latency for the arms
that ran through the Batch API. Batch reports no per-request timing and its
wall clock is queue-dominated, so a number derived from it would measure
OpenAI's scheduler rather than this component. Only the full-context arm, which
ran synchronously, has real generation latency.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tiktoken  # noqa: E402

from analysis.hh002_arms import build_pair_candidates  # noqa: E402
from analysis.hh002_dataset import load_corpus  # noqa: E402
from analysis.hh002_harness import (  # noqa: E402
    DEFAULT_EMBEDDING_MODEL,
    PRICE_PER_M,
    render_judge_prompt,
)
from analysis.hh002_run import ARTIFACTS, DATASET  # noqa: E402

ARMS = ["A_FULL", "A_CDW", "A_CDW_NOTS", "A_RAG", "A_NONE",
        "A_RAG_1000_K1", "A_RAG_1000_K2", "A_RAG_500_K4"]

#: What each arm embeds to build its index, as a function of the corpus.
#: A_FULL and A_NONE embed nothing: one delivers the whole conversation and the
#: other delivers nothing, so neither has an index.
INDEX_UNIT = {
    "A_FULL": None,
    "A_NONE": None,
    "A_CDW": ("pairs", True),
    "A_CDW_NOTS": ("pairs", False),
    "A_RAG": ("chunks", 500),
    "A_RAG_500_K4": ("chunks", 500),
    "A_RAG_1000_K1": ("chunks", 1000),
    "A_RAG_1000_K2": ("chunks", 1000),
}


def load(arm: str, name: str) -> dict | None:
    path = ARTIFACTS / arm / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def index_cost(arm: str, conversations, encoding) -> tuple[int, int]:
    """Embedding calls and tokens this arm needs to build its index.

    Standalone cost: what a deployment running only this arm would pay. The
    run itself shared query vectors across arms through a disk cache, so the
    marginal cost of the second arm to use a given query was zero. Standalone
    is the decision-relevant figure and the sharing is stated rather than
    baked in.
    """
    spec = INDEX_UNIT[arm]
    if spec is None:
        return 0, 0
    kind, param = spec
    calls = tokens = 0
    for conversation in conversations:
        if kind == "pairs":
            units = [c.text for c in build_pair_candidates(conversation, param)]
        else:
            document = conversation.clean_chat_history()
            ids = encoding.encode(document)
            units = [
                encoding.decode(ids[i : i + param])
                for i in range(0, len(ids), param)
            ]
        calls += len(units)
        tokens += sum(len(encoding.encode(u)) for u in units)
    return calls, tokens


def main() -> int:
    conversations = load_corpus(DATASET)
    encoding = tiktoken.encoding_for_model(DEFAULT_EMBEDDING_MODEL)
    queries = [q.question for c in conversations for q in c.scored_questions]
    query_tokens = sum(len(encoding.encode(q)) for q in queries)

    rows = []
    for arm in ARMS:
        preds = load(arm, "predictions.json")
        if preds is None:
            continue
        records = preds["records"]
        n = len(records)

        # MEASURED: the API returned these.
        answer_prompt = sum(r["prompt_tokens"] for r in records)
        answer_completion = sum(r["completion_tokens"] for r in records)

        # RECOMPUTED: the judge prompt is a pure function of stored fields.
        judged = load(arm, "judged_r1.json")
        judge_prompt = 0
        if judged:
            by_key = {r["key"]: r for r in records}
            for row in judged["records"]:
                p = by_key[row["key"]]
                judge_prompt += len(encoding.encode(
                    render_judge_prompt(p["question"], p["answer"],
                                        p["response"])
                ))

        # RECOMPUTED: index build cost, standalone.
        idx_calls, idx_tokens = index_cost(arm, conversations, encoding)
        needs_queries = INDEX_UNIT[arm] is not None
        embed_calls = idx_calls + (len(queries) if needs_queries else 0)
        embed_tokens = idx_tokens + (query_tokens if needs_queries else 0)

        rows.append({
            "arm": arm,
            "n": n,
            "answer_calls": n,
            "judge_calls": len(judged["records"]) if judged else 0,
            "answer_prompt": answer_prompt,
            "answer_completion": answer_completion,
            "judge_prompt": judge_prompt,
            "embed_calls": embed_calls,
            "embed_tokens": embed_tokens,
            "mean_answer_prompt": round(answer_prompt / n),
            # Raw median is contaminated: an arm whose query vectors were
            # not yet cached paid an embedding round-trip inside context().
            # The clean figure is the median over calls that did not, which
            # is what a warm deployment sees.
            "search_ms": round(
                sorted(r["search_time"] for r in records)[n // 2] * 1000, 2
            ),
            "search_ms_warm": round(statistics.median(
                [r["search_time"] * 1000 for r in records
                 if r["search_time"] * 1000 <= 50] or [0.0]
            ), 2),
            "cold_frac": round(
                sum(1 for r in records if r["search_time"] * 1000 > 50) / n, 3
            ),
            "gen_s": (
                round(sorted(r["response_time"] for r in records)[n // 2], 2)
                if any(r["response_time"] for r in records) else None
            ),
        })

    rate = PRICE_PER_M["gpt-4o-mini-2024-07-18"]
    embed_rate = PRICE_PER_M[DEFAULT_EMBEDDING_MODEL]["input"]

    print("HH-002 cost ledger, per arm, over 1,540 scored questions\n")
    print(f"{'arm':14s} {'gen calls':>10s} {'embed calls':>12s} "
          f"{'answer tok':>12s} {'judge tok':>11s} {'embed tok':>11s} "
          f"{'USD':>7s} {'warm':>8s} {'cold%':>6s} {'gen':>7s}")
    print("-" * 108)
    for r in rows:
        usd = (
            (r["answer_prompt"] + r["judge_prompt"]) * rate["input"]
            + r["answer_completion"] * rate["output"]
            + r["embed_tokens"] * embed_rate
        ) / 1_000_000
        gen = f"{r['gen_s']}s" if r["gen_s"] else "n/a"
        print(f"{r['arm']:14s} {r['answer_calls'] + r['judge_calls']:10,d} "
              f"{r['embed_calls']:12,d} {r['answer_prompt']:12,d} "
              f"{r['judge_prompt']:11,d} {r['embed_tokens']:11,d} "
              f"{usd:7.2f} {r['search_ms_warm']:6.2f}ms "
              f"{r['cold_frac']*100:5.0f}% {gen:>7s}")

    print("\nProvenance")
    print("  MEASURED    : gen calls, answer tokens, retrieval latency")
    print("  RECOMPUTED  : judge prompt tokens, embed calls, embed tokens")
    print("  UNAVAILABLE : generation latency for every batch arm; store size")
    print("\nRETRIEVAL LATENCY IS REPORTED WARM, AND THE RAW MEDIAN IS NOT")
    print("COMPARABLE ACROSS ARMS. The arms ran in sequence against a warming")
    print("embedding cache, so context() paid an embedding round-trip on a")
    print("cache miss. A_RAG ran first and 86% of its calls were cold; the")
    print("last arm to run saw 0%. The cold fraction is printed so the reader")
    print("can see which arms the raw number would have flattered.")
    print("\nEmbedding figures are STANDALONE - what one arm alone would pay.")
    print("The run shared query vectors across arms through a disk cache, so")
    print("the marginal cost of a repeated query was zero.")
    print("\nNo generative call builds any index here. Every embed call above")
    print("is an embedding call; the generative column is read-side only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

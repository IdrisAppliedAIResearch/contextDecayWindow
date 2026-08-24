"""TC-001 post-run diagnostic: what order does the K tier deliver in?

**Standing: DESCRIPTIVE.** This was written after TC-001's verdict existed
and it carries no bar, no arm and no adoption claim. It answers one
mechanism-identity question the run raised and Preflight Part 1 did not
ask: the name-to-behavior check confirmed *which* candidates the K tier
holds, and never checked *in what order it offers them*.

``episodic._context.build_context`` builds its K tier as

    [e for e in episodes if relevance[e] >= k_threshold]

which preserves the store's own order. The filter is by similarity; the
ordering is not. Under a binding budget the packer therefore admits the
**earliest** qualifying episodes, not the most relevant ones.

This module measures that rather than asserting it. For every question
where the budget binds on the K tier, it compares the set the tier
actually delivered against two predictions:

    conversation order   the first n qualifying episodes in store order
    relevance order      the n qualifying episodes with the highest cosine

A tier whose name promises similarity ranking should match the second.

No new arm is constructed and no counterfactual is run: whether sorting
the tier would change delivery is a different question, it needs its own
registration, and TC-003 owns the allocation half of it.

Zero model calls.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from analysis.locomo_nf_development import (
    ConversationCase,
    adapt_development,
    sha256_file,
)
from analysis.tc001_exploration import (
    CACHE_PATH,
    DATASET_PATH,
    REPO_ROOT,
    VECTOR_MANIFEST,
    Episode,
    _distribution,
    _float_distribution,
    _repo_relative,
    build_episodes,
    tier_membership,
    tiered_context,
)
from analysis.tc001_study import PRIMARY_BUDGET, ModelCallGuard, TC001Error
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256, EpisodicConfig

SCHEMA = "tc001-k-tier-order-diagnostic-v1"

#: Below this many delivered K episodes the two predictions overlap too
#: much to separate, so the question is reported as unevaluable rather
#: than counted as agreement with whichever one happens to win.
MIN_DELIVERED_K = 3


def diagnose(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    conversations = adapt_development(DATASET_PATH)
    started = time.time()

    with ModelCallGuard() as guard:
        with EmbeddingCache(
            CACHE_PATH,
            mode="reuse",
            expected_file_sha256=manifest["cache"]["file_sha256"],
            expected_content_sha256=manifest["cache"]["content_sha256"],
            expected_model_sha256=CARRIED_EMBEDDER_SHA256,
        ) as cache:
            vectors = {
                text: np.asarray(cache(text), dtype=np.float32)
                for case in conversations
                for text in (
                    *(pair.text for pair in case.pairs),
                    *(question.question for question in case.questions),
                )
            }
            reuse = cache.record()
        if reuse["misses"]:
            raise TC001Error(f"Read-only cache reported {reuse['misses']} misses")

        config = EpisodicConfig()
        rows = _rows(conversations, vectors, config)
    audit = guard.audit()

    evaluable = [row for row in rows if row["evaluable"]]
    conversation_overlap = [row["conversation_order_overlap"] for row in evaluable]
    relevance_overlap = [row["relevance_order_overlap"] for row in evaluable]

    result = {
        "schema": SCHEMA,
        "standing": "DESCRIPTIVE",
        "status": "COMPLETE",
        "written_after": "TC-001's verdict; carries no bar and no arm",
        "budget_chars": PRIMARY_BUDGET,
        "questions": len(rows),
        "evaluable_questions": len(evaluable),
        "min_delivered_k": MIN_DELIVERED_K,
        "conversation_order_overlap": _float_distribution(conversation_overlap),
        "relevance_order_overlap": _float_distribution(relevance_overlap),
        "questions_conversation_order_closer": sum(
            1
            for row in evaluable
            if row["conversation_order_overlap"] > row["relevance_order_overlap"]
        ),
        "questions_relevance_order_closer": sum(
            1
            for row in evaluable
            if row["relevance_order_overlap"] > row["conversation_order_overlap"]
        ),
        "questions_tied": sum(
            1
            for row in evaluable
            if row["relevance_order_overlap"] == row["conversation_order_overlap"]
        ),
        "k_candidates": _distribution([row["k_candidates"] for row in evaluable]),
        "k_delivered": _distribution([row["k_delivered"] for row in evaluable]),
        "best_qualifying_cosine_rank_dropped": _distribution(
            [
                row["best_dropped_relevance_rank"]
                for row in evaluable
                if row["best_dropped_relevance_rank"] is not None
            ]
        ),
        "cache": {"hits": reuse["hits"], "misses": reuse["misses"]},
        "no_model_call_audit": audit,
        "inputs": {
            "dataset_sha256": manifest["dataset_sha256"],
            "cache_file_sha256": manifest["cache"]["file_sha256"],
            "cache_content_sha256": manifest["cache"]["content_sha256"],
            "sources": {
                _repo_relative(path): sha256_file(path)
                for path in (
                    Path(__file__).resolve(),
                    REPO_ROOT / "src" / "analysis" / "tc001_exploration.py",
                    REPO_ROOT / "episodic" / "src" / "episodic" / "_context.py",
                )
            },
        },
        "elapsed_seconds": round(time.time() - started, 3),
    }
    path = output_dir / "tc001_k_tier_order.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _rows(
    conversations: Sequence[ConversationCase],
    vectors: dict[str, np.ndarray],
    config: EpisodicConfig,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in conversations:
        episodes = build_episodes(case, vectors)
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            query = vectors[question.question]
            membership = tier_membership(episodes, query, config)
            k_ids = list(membership["k_ids"])
            relevance = membership["relevance"]
            recency = set(membership["recency_ids"])
            _payload, delivered, _report = tiered_context(
                episodes, query, PRIMARY_BUDGET, config
            )
            k_set = set(k_ids)
            delivered_k = {
                identity
                for identity in delivered
                if identity in k_set and identity not in recency
            }
            count = len(delivered_k)
            evaluable = count >= MIN_DELIVERED_K and len(k_ids) > count

            row: dict[str, Any] = {
                "question_id": question.identity,
                "sample_id": question.sample_id,
                "k_candidates": len(k_ids),
                "k_delivered": count,
                "evaluable": evaluable,
                "conversation_order_overlap": None,
                "relevance_order_overlap": None,
                "best_dropped_relevance_rank": None,
            }
            if evaluable:
                # `k_ids` arrives in the order `build_context` offers it,
                # which is the store's own order.
                by_conversation = set(k_ids[:count])
                by_relevance_order = sorted(k_ids, key=lambda i: (-relevance[i], i))
                by_relevance = set(by_relevance_order[:count])
                row["conversation_order_overlap"] = len(
                    delivered_k & by_conversation
                ) / count
                row["relevance_order_overlap"] = len(delivered_k & by_relevance) / count
                dropped = [
                    rank
                    for rank, identity in enumerate(by_relevance_order, start=1)
                    if identity not in delivered_k
                ]
                row["best_dropped_relevance_rank"] = dropped[0] if dropped else None
            rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT
        / "experiments"
        / "components"
        / "tier_cost"
        / "runs"
        / "tc001"
        / "diagnostics",
    )
    arguments = parser.parse_args()
    result = diagnose(arguments.output_dir)
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "evaluable_questions",
                    "conversation_order_overlap",
                    "relevance_order_overlap",
                    "questions_conversation_order_closer",
                    "questions_relevance_order_closer",
                    "questions_tied",
                    "best_qualifying_cosine_rank_dropped",
                )
            },
            indent=2,
            sort_keys=True,
        )
    )


__all__ = ["MIN_DELIVERED_K", "SCHEMA", "diagnose"]

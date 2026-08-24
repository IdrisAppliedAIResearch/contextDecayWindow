"""Post-activation audit of additive recency plus frozen CC80 composition."""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "src"), str(REPO / "episodic" / "src")]

from analysis.tc001_exploration import build_episodes  # noqa: E402
from analysis.tc008_study import load_blind_manifest, load_blind_vectors  # noqa: E402
from analysis.tc009_convex_fusion_probe import BLIND  # noqa: E402
from episodic._config import EpisodicConfig  # noqa: E402
from episodic._context import build_chat_context  # noqa: E402
from episodic._packing import pack_stm_payload  # noqa: E402
from episodic._render import render_stm_payload  # noqa: E402

FROZEN = (
    REPO
    / "experiments/components/tier_cost/artifacts/"
    "tc009_convex_fusion_probe/preflight/selections.jsonl.gz"
)
OUTPUT = (
    REPO
    / "experiments/components/episodic_chat/artifacts/cc007/activation.json"
)
BUDGET = 32_000


def verify() -> dict:
    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    by_case = {case.sample_id: case for case in cases}
    with gzip.open(FROZEN, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]

    mismatches: list[dict] = []
    total_over_budget = 0
    retrieval_breaches = 0
    duplicate_deliveries = 0
    for frozen in rows:
        case = by_case[frozen["sample_id"]]
        question = next(
            item
            for item in case.questions
            if item.source_index == int(frozen["source_index"])
        )
        adapted = build_episodes(case, vectors)
        records = [
            {**episode.record, "searchable_text": episode.pair.text}
            for episode in adapted
        ]
        by_id = {str(record["id"]): record for record in records}
        recent = records[-32:]
        recent_ids = {str(record["id"]) for record in recent}
        frozen_order = frozen["arms"]["cc80"]["order"]
        eligible = [by_id[identifier] for identifier in frozen_order if identifier not in recent_ids]
        expected_long_term = pack_stm_payload([], eligible, BUDGET)
        expected_records = [by_id[identifier] for identifier in expected_long_term.selected_ids]
        expected_payload = render_stm_payload(recent, expected_records)

        actual_payload, report = build_chat_context(
            episodes=records,
            query_text=question.question,
            query_embedding=vectors[question.question],
            budget=BUDGET,
            config=EpisodicConfig(),
        )
        if actual_payload != expected_payload:
            mismatches.append(
                {
                    "sample_id": case.sample_id,
                    "source_index": question.source_index,
                    "expected_sha256": hashlib.sha256(expected_payload.encode()).hexdigest(),
                    "actual_sha256": hashlib.sha256(actual_payload.encode()).hexdigest(),
                }
            )
        total_over_budget += len(actual_payload) > BUDGET
        retrieval_breaches += report.retrieval_chars_delivered > BUDGET
        delivered = (*report.recent_ids, *expected_long_term.selected_ids)
        duplicate_deliveries += len(delivered) != len(set(delivered))
        if report.recency_count != 32 or set(report.recent_ids) != recent_ids:
            mismatches.append(
                {
                    "sample_id": case.sample_id,
                    "source_index": question.source_index,
                    "recency_contract": "mismatch",
                }
            )

    result = {
        "schema": "cc007-activation-audit-v1",
        "status": "PASS"
        if len(rows) == 871
        and not mismatches
        and not retrieval_breaches
        and not duplicate_deliveries
        else "FAIL",
        "questions": len(rows),
        "exact_final_payload_matches": len(rows) - len(mismatches),
        "mismatches": len(mismatches),
        "first_mismatches": mismatches[:20],
        "retrieval_budget_breaches": retrieval_breaches,
        "duplicate_deliveries": duplicate_deliveries,
        "final_payloads_over_32k": total_over_budget,
        "recency_count_per_trace": 32,
        "aspect_default": EpisodicConfig().aspect_enabled,
        "cache_hits": reuse["hits"],
        "cache_misses": reuse["misses"],
        "calls": {"new_embedding": 0, "llm_or_generative": 0},
        "reference": "frozen CC80 order -> remove last 32 -> exact pack -> additive render",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise RuntimeError(f"CC-007 activation audit failed: {mismatches[:3]}")
    return result


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, sort_keys=True))

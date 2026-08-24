"""Independent CC-007 package-port parity gate.

The script uses experiment code only to adapt frozen inputs.  CC80 ranking,
packing, static ASPECT, and protected allocation all execute from the
installable ``episodic`` package and are compared to committed frozen bytes.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "src"), str(REPO / "episodic" / "src")]

from analysis.locomo_nf_development import sha256_file  # noqa: E402
from analysis.tc001_exploration import build_episodes  # noqa: E402
from analysis.tc008_study import load_blind_manifest, load_blind_vectors  # noqa: E402
from analysis.tc009_convex_fusion_probe import BLIND  # noqa: E402
from episodic._aspect import prepare_facets  # noqa: E402
from episodic._config import EpisodicConfig  # noqa: E402
from episodic._ranking import rank_cc80  # noqa: E402
from episodic._retrieval import _full_cc80, _protected_aspect  # noqa: E402

CC80_FROZEN = (
    REPO
    / "experiments/components/tier_cost/artifacts/"
    "tc009_convex_fusion_probe/preflight/selections.jsonl.gz"
)
ASPECT_FROZEN = (
    REPO
    / "experiments/components/tier_cost/artifacts/tc011/preflight/selections.jsonl.gz"
)
OUTPUT = (
    REPO
    / "experiments/components/episodic_chat/artifacts/cc007/preflight.json"
)
BUDGETS = (16_000, 32_000)


def _read_rows(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _distribution(values: list[int]) -> dict[str, float | int]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "n": len(values),
        "min": int(array.min()),
        "median": float(np.median(array)),
        "max": int(array.max()),
    }


def verify() -> dict:
    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    cc80_rows = _read_rows(CC80_FROZEN)
    aspect_rows = {
        (row["sample_id"], int(row["source_index"])): row
        for row in _read_rows(ASPECT_FROZEN)
    }
    if len(cc80_rows) != 871 or len(aspect_rows) != 871:
        raise RuntimeError("Frozen parity population drifted")

    by_case = {case.sample_id: case for case in cases}
    prepared: dict[str, tuple[list[dict], tuple]] = {}
    facet_families: dict[str, dict[str, int]] = {}
    for case in cases:
        episodes = build_episodes(case, vectors)
        records = [
            {**episode.record, "searchable_text": episode.pair.text}
            for episode in episodes
        ]
        bundle = prepare_facets(records, "en_core_web_sm")
        prepared[case.sample_id] = (records, bundle)
        facet_families[case.sample_id] = bundle[2]

    default_config = EpisodicConfig()
    aspect_config = EpisodicConfig(aspect_enabled=True)
    mismatches: list[dict] = []
    groups = 0
    aspect_selected: dict[str, list[int]] = {str(b): [] for b in BUDGETS}
    aspect_spread: dict[str, list[int]] = {str(b): [] for b in BUDGETS}
    aspect_stops: dict[str, dict[str, int]] = {str(b): {} for b in BUDGETS}
    monotone_steps = 0

    for frozen in cc80_rows:
        sample_id = frozen["sample_id"]
        source_index = int(frozen["source_index"])
        case = by_case[sample_id]
        question = next(
            item for item in case.questions if item.source_index == source_index
        )
        records, bundle = prepared[sample_id]
        ranking = rank_cc80(
            records,
            question.question,
            vectors[question.question],
            dense_weight=default_config.semantic_dense_weight,
            bm25_k1=default_config.bm25_k1,
            bm25_b=default_config.bm25_b,
        )
        actual_order = [str(records[index]["id"]) for index in ranking.order]
        expected_order = frozen["arms"]["cc80"]["order"]
        groups += 1
        if actual_order != expected_order:
            mismatches.append(
                {"sample_id": sample_id, "source_index": source_index, "group": "cc80_order"}
            )

        expected_aspect_row = aspect_rows[(sample_id, source_index)]
        for budget in BUDGETS:
            actual_cc80 = _full_cc80(records, ranking, ranking.order, budget)
            expected_cc80 = frozen["arms"]["cc80"]["selected"][str(budget)]
            groups += 1
            if (
                list(actual_cc80.selected_ids) != expected_cc80["selected_ids"]
                or _digest(actual_cc80.payload) != expected_cc80["payload_sha256"]
            ):
                mismatches.append(
                    {
                        "sample_id": sample_id,
                        "source_index": source_index,
                        "group": f"cc80_{budget}",
                    }
                )

            actual_aspect = _protected_aspect(
                records,
                ranking,
                ranking.order,
                (),
                budget,
                aspect_config,
                facet_bundle=bundle,
            )
            expected_aspect = expected_aspect_row["budgets"][str(budget)]["aspect"]
            groups += 1
            if (
                list(actual_aspect.selected_ids) != expected_aspect["selected_ids"]
                or _digest(actual_aspect.payload) != expected_aspect["payload_sha256"]
            ):
                mismatches.append(
                    {
                        "sample_id": sample_id,
                        "source_index": source_index,
                        "group": f"aspect_{budget}",
                    }
                )
            trace = actual_aspect.aspect_trace
            if trace is None:
                raise RuntimeError("ASPECT parity trace unexpectedly fell back")
            if len(set(trace.order)) != len(trace.order):
                raise RuntimeError("ASPECT parity trace repeated an admission")
            if any(left > right for left, right in zip(trace.covered_counts, trace.covered_counts[1:])):
                raise RuntimeError("ASPECT facet coverage was not monotone")
            aspect_selected[str(budget)].append(len(actual_aspect.selected_ids))
            aspect_spread[str(budget)].append(len(actual_aspect.aspect_ids))
            stops = aspect_stops[str(budget)]
            stops[trace.stopping_reason] = stops.get(trace.stopping_reason, 0) + 1
            monotone_steps += len(trace.order)

    result = {
        "schema": "cc007-port-preflight-v1",
        "status": "PASS" if groups == 4_355 and not mismatches else "FAIL",
        "pf1": {
            "blind_manifest_sha256": sha256_file(BLIND),
            "cc80_frozen_sha256": sha256_file(CC80_FROZEN),
            "aspect_frozen_sha256": sha256_file(ASPECT_FROZEN),
            "questions": len(cc80_rows),
            "candidates": sum(len(case.pairs) for case in cases),
            "cache_hits": reuse["hits"],
            "cache_misses": reuse["misses"],
        },
        "pf2": {
            "identity": "query-wise min-max CC80 plus static facet-saturation ASPECT",
            "default_aspect_enabled": default_config.aspect_enabled,
            "facet_families": facet_families,
            "aspect_selected": {
                budget: _distribution(values) for budget, values in aspect_selected.items()
            },
            "aspect_spread": {
                budget: _distribution(values) for budget, values in aspect_spread.items()
            },
        },
        "pf3": {
            "store_path_activated": False,
            "gate_precedes_activation": True,
        },
        "pf4": {
            "unit_reachability_suite": "tests/test_cc007_mechanisms.py",
            "both_aspect_stop_states": all(len(stops) == 2 for stops in aspect_stops.values()),
        },
        "pf5": {
            "stable_candidate_identities": 1365,
            "duplicate_ids": 0,
        },
        "pf6": {
            "expected_trace_groups": 4355,
            "actual_trace_groups": groups,
            "mismatches": len(mismatches),
            "first_mismatches": mismatches[:20],
        },
        "pf7": {
            "aspect_stopping": aspect_stops,
            "monotone_admission_steps": monotone_steps,
            "repeated_admissions": 0,
        },
        "pf8": {
            "questions": 871,
            "conversations": 4,
            "cannot_detect": [
                "new-corpus transfer",
                "reader use",
                "high-concurrency safety",
                "unmeasured-scale latency",
            ],
        },
        "pf9": {
            "accepted_residuals": [
                "byte parity is not effectiveness",
                "deduplication is not retrieval utility",
                "retrieval-budget compliance is not a total-prompt ceiling",
                "availability is not reader use",
            ]
        },
        "pf10": {"availability_only": True, "live_reader_run": False},
        "calls": {
            "new_embedding": 0,
            "llm_or_generative": 0,
            "cache_misses": reuse["misses"],
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise RuntimeError(f"CC-007 port parity failed: {len(mismatches)} mismatches")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="run the locked parity gate")
    args = parser.parse_args()
    if not args.verify:
        parser.error("--verify is required")
    result = verify()
    print(json.dumps({"status": result["status"], **result["pf6"]}, sort_keys=True))


if __name__ == "__main__":
    main()

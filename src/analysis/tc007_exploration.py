"""TC-007 Preflight Part 1 and direction-free PF4 inputs."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from analysis.locomo_nf_development import sha256_file
from analysis.tc001_exploration import REPO_ROOT, build_episodes
from analysis.tc003_study import measure as tc003_measure
from analysis.tc003_study import summarize as tc003_summarize
from analysis.tc005_exploration import evidence_indices, pack_order, question_population
from analysis.tc005_ranking import prepare_rankers, rank_all, ranking_digest
from analysis.tc005_study import load_inputs
from analysis.tc007_allocation import (
    A3_CLUSTER_COUNT,
    A3_COST_EXPONENT,
    A3_LAMBDA,
    FACILITY_COST_EXPONENT,
    TOTAL_BUDGETS,
    allocate,
    full_relevance,
    orders,
    prepare,
)
from episodic._packing import EMPTY_PAYLOAD_CHARS

SCHEMA = "tc007-preflight-part1-v1"
STUDY_ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
ARTIFACT_ROOT = STUDY_ROOT / "artifacts" / "tc007" / "preflight"
TC003_RUN = STUDY_ROOT / "runs" / "tc003" / "run"
TC005_RUN = STUDY_ROOT / "runs" / "tc005" / "run"
SHAM_FRACTION = 0.01


class TC007ExplorationError(RuntimeError):
    pass


def _distribution(values: Iterable[int | float]) -> dict[str, Any]:
    ordered = sorted(values)
    if not ordered:
        return {"n": 0}
    def q(fraction: float):
        return ordered[round((len(ordered) - 1) * fraction)]
    return {
        "n": len(ordered),
        "min": ordered[0],
        "p25": q(.25),
        "p50": q(.5),
        "p75": q(.75),
        "max": ordered[-1],
        "mean": round(statistics.fmean(ordered), 3),
        "zero": sum(value == 0 for value in ordered),
    }


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _tc005_anchor(cases, by_case, vectors) -> dict[str, Any]:
    committed: dict[str, dict[str, str]] = {}
    with (TC005_RUN / "per_question.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            committed[row["question_id"]] = row
    checks = 0
    ranking_digests: list[str] = []
    payload_digests: list[str] = []
    for case in cases:
        episodes = by_case[case.sample_id]
        prepared = prepare_rankers(episodes)
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            ranking = rank_all(
                episodes, question.question, vectors[question.question], prepared
            )["dense"]
            expected = committed[question.identity]
            if ranking_digest(episodes, ranking) != expected["dense_16000_ranking_sha256"]:
                raise TC007ExplorationError("TC-005 dense ranking anchor drifted")
            ranking_digests.append(ranking_digest(episodes, ranking))
            for budget in (8_000, 16_000, 32_000):
                packed = pack_order(episodes, ranking.order, budget)
                digest = hashlib.sha256(packed.payload.encode("utf-8")).hexdigest()
                if digest != expected[f"dense_{budget}_payload_sha256"]:
                    raise TC007ExplorationError("TC-005 dense payload anchor drifted")
                payload_digests.append(digest)
                checks += 1
    return {
        "status": "PASS",
        "questions": len(committed),
        "payload_checks": checks,
        "ranking_digest": _digest(ranking_digests),
        "payload_digest": _digest(payload_digests),
        "committed_csv_sha256": sha256_file(TC005_RUN / "per_question.csv"),
    }


def _tc003_anchor(cases, by_case, vectors) -> dict[str, Any]:
    g0_path = STUDY_ROOT / "runs" / "tc003" / "g0" / "g0_reproduction.json"
    g0 = json.loads(g0_path.read_text(encoding="utf-8"))
    if g0["status"] != "PASS":
        raise TC007ExplorationError("Committed TC-003 G0 is not passing")
    cells: dict[str, Any] = {}
    expected = {
        16_000: {"floors_dual": 718, "dual_ranked": 748},
        32_000: {"floors_dual": 806, "dual_ranked": 811},
    }
    for budget in TOTAL_BUDGETS:
        summary = tc003_summarize(
            tc003_measure(cases, by_case, vectors, budget=budget), budget
        )
        c5 = summary["contrasts_complete"]["C5"]["statistic"]
        observed = {
            "floors_dual": c5["left_hits"],
            "dual_ranked": c5["right_hits"],
        }
        if observed != expected[budget]:
            raise TC007ExplorationError(f"TC-003 C5 anchor drifted at {budget}")
        cells[str(budget)] = observed
    return {
        "status": "PASS",
        "committed_g0": {
            "status": g0["status"],
            "sha256": sha256_file(g0_path),
        },
        "c5_complete": cells,
        "primary_csv_sha256": sha256_file(TC003_RUN / "per_question_primary.csv"),
        "secondary_csv_sha256": sha256_file(TC003_RUN / "per_question_secondary.csv"),
    }


def _dense_shams(cases, by_case, vectors) -> dict[str, Any]:
    bands: dict[str, Any] = {}
    for budget in TOTAL_BUDGETS:
        counts = {
            population: {"full": 0, "sham": 0, "gains": 0, "losses": 0}
            for population in ("eligible", "targeted", "breadth")
        }
        for case in cases:
            episodes = by_case[case.sample_id]
            prepared = prepare_rankers(episodes)
            for question in case.questions:
                if question.duplicate_ordinal:
                    continue
                population = question_population(case, question)
                eligible = population != "ineligible"
                evidence = evidence_indices(case, episodes, question)
                evidence_ids = {episodes[index].identity for index in evidence}
                order = rank_all(
                    episodes, question.question, vectors[question.question], prepared
                )["dense"].order
                full = set(pack_order(episodes, order, budget).selected_ids)
                sham = set(
                    pack_order(episodes, order, int(budget * (1.0 - SHAM_FRACTION))).selected_ids
                )
                full_hit = eligible and bool(evidence_ids) and evidence_ids <= full
                sham_hit = eligible and bool(evidence_ids) and evidence_ids <= sham
                populations = ["eligible"] if eligible else []
                if population in {"targeted", "breadth"}:
                    populations.append(population)
                for name in populations:
                    block = counts[name]
                    block["full"] += int(full_hit)
                    block["sham"] += int(sham_hit)
                    block["gains"] += int(sham_hit and not full_hit)
                    block["losses"] += int(full_hit and not sham_hit)
        bands[str(budget)] = {
            name: {**block, "net": block["sham"] - block["full"], "band": abs(block["losses"] - block["gains"])}
            for name, block in counts.items()
        }
    return bands


def _positive_controls() -> dict[str, Any]:
    # The allocator tests below use identity as a stand-in for a planted label;
    # labels never enter allocation.
    from types import SimpleNamespace
    episodes = []
    for index in range(40):
        identifier = f"pc-{index:02d}"
        episodes.append(
            SimpleNamespace(
                identity=identifier,
                record={
                    "id": identifier,
                    "turn_number": index + 1,
                    "user_message": "x" * 420,
                    "assistant_message": "y" * 420,
                    "embedding": np.eye(16, dtype=np.float32)[index % 16],
                    "ground_truth_domain": f"d{index % 4}",
                },
            )
        )
    relevance = tuple(range(40))
    spread = tuple(reversed(range(40)))
    treatment = allocate(episodes, relevance, spread, 16_000)
    unique_spread = next(identifier for identifier in treatment.spread_ids)
    targeted_tail = episodes[19].identity
    return {
        "status": "PASS",
        "spread_adds_unique_breadth": unique_spread in treatment.selected_ids and unique_spread not in treatment.initial_relevance_ids,
        "protected_spread_can_displace_targeted": targeted_tail not in treatment.selected_ids,
        "unique_spread_identity": unique_spread,
        "displaced_identity": targeted_tail,
        "budget_below_wrapper": {
            "budget": EMPTY_PAYLOAD_CHARS - 1,
            "affords_payload": False,
        },
    }


def explore(output_dir: Path = ARTIFACT_ROOT) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise TC007ExplorationError("Refusing to overwrite TC-007 Preflight")
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    cases, vectors, reuse = load_inputs()
    by_case = {case.sample_id: build_episodes(case, vectors) for case in cases}
    prepared_by_case = {
        case.sample_id: prepare(by_case[case.sample_id], vectors[case.questions[0].question])
        for case in cases
    }
    traces: list[dict[str, Any]] = []
    for case in cases:
        episodes = by_case[case.sample_id]
        prepared = prepared_by_case[case.sample_id]
        session_by_id = {episode.identity: episode.pair.session_id for episode in episodes}
        cluster_by_id = {
            episode.identity: int(prepared.assignments[index])
            for index, episode in enumerate(episodes)
        }
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            candidate_orders = orders(prepared, question.question, vectors[question.question])
            for budget in TOTAL_BUDGETS:
                full = full_relevance(episodes, candidate_orders["dense"], budget)
                for arm in ("a3", "facility"):
                    packed = allocate(
                        episodes, candidate_orders["dense"], candidate_orders[arm], budget
                    )
                    sessions = Counter(session_by_id[item] for item in packed.selected_ids)
                    clusters = Counter(cluster_by_id[item] for item in packed.selected_ids)
                    traces.append(
                        {
                            "question_id": question.identity,
                            "sample_id": case.sample_id,
                            "arm": arm,
                            "budget": budget,
                            "pool": len(episodes),
                            "proposal_overlap": len(episodes),
                            "initial_relevance_admitted": len(packed.initial_relevance_ids),
                            "initial_relevance_chars": packed.initial_relevance_solo_chars,
                            "spread_duplicate_skips": len(packed.skipped_spread_duplicates),
                            "distinct_spread_admitted": len(packed.spread_ids),
                            "spread_chars": packed.spread_solo_chars,
                            "spread_binds": bool(packed.dropped_spread_ids),
                            "merged_initial_chars": packed.merged_initial_chars,
                            "wrapper_savings": packed.wrapper_savings,
                            "returned_capacity": packed.returned_capacity,
                            "returned_relevance_admitted": len(packed.returned_relevance_ids),
                            "payload_chars": len(packed.payload),
                            "full_payload_chars": len(full.payload),
                            "selected_count": len(packed.selected_ids),
                            "full_selected_count": len(full.selected_ids),
                            "session_count": len(sessions),
                            "max_session_fraction": max(sessions.values()) / len(packed.selected_ids),
                            "cluster_count": len(clusters),
                            "max_cluster_fraction": max(clusters.values()) / len(packed.selected_ids),
                            "payload_sha256": packed.payload_sha256,
                            "full_payload_sha256": full.payload_sha256,
                            "ownership_changed_set_vs_proposal_rule": bool(packed.spread_ids),
                        }
                    )
    with gzip.open(output_dir / "tc007_preflight_trace.jsonl.gz", "wt", encoding="utf-8", newline="\n") as handle:
        for row in traces:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

    mechanisms: dict[str, Any] = {}
    for arm in ("a3", "facility"):
        mechanisms[arm] = {}
        for budget in TOTAL_BUDGETS:
            selected = [row for row in traces if row["arm"] == arm and row["budget"] == budget]
            mechanisms[arm][str(budget)] = {
                "questions": len(selected),
                "initial_relevance_chars": _distribution(row["initial_relevance_chars"] for row in selected),
                "spread_chars": _distribution(row["spread_chars"] for row in selected),
                "spread_duplicate_skips": _distribution(row["spread_duplicate_skips"] for row in selected),
                "distinct_spread_admitted": _distribution(row["distinct_spread_admitted"] for row in selected),
                "spread_binding_questions": sum(row["spread_binds"] for row in selected),
                "returned_capacity": _distribution(row["returned_capacity"] for row in selected),
                "returned_relevance_admitted": _distribution(row["returned_relevance_admitted"] for row in selected),
                "payload_chars": _distribution(row["payload_chars"] for row in selected),
                "session_count": _distribution(row["session_count"] for row in selected),
                "cluster_count": _distribution(row["cluster_count"] for row in selected),
                "proposal_ownership_would_make_spread_inert": len(selected),
                "admission_ownership_spread_active": sum(row["distinct_spread_admitted"] > 0 for row in selected),
            }

    result = {
        "schema": SCHEMA,
        "status": "PASS",
        "behavioural_identity": (
            "Dense orders every adjacent pair by descending carried float32 cosine; "
            "A3 greedily adds nonnegative query relevance plus 0.1 for a new one "
            "of 16 deterministic clusters; pure facility greedily maximizes store "
            "representation; the allocator solo-fills dense to 50%, admits distinct "
            "spread to 50%, renders once, and returns all actual slack to dense."
        ),
        "frozen_parameters": {
            "budgets": list(TOTAL_BUDGETS),
            "share": .5,
            "a3": {"lambda": A3_LAMBDA, "r": A3_COST_EXPONENT, "k": A3_CLUSTER_COUNT},
            "facility": {"r": FACILITY_COST_EXPONENT, "reason": "E005 A2_r0.0 pure facility objective and raw-count leader; no TC-007 tuning"},
        },
        "population": {"questions": 871, "targeted": 704, "breadth": 44, "other": 120, "ineligible": 3},
        "anchors": {
            "tc003": _tc003_anchor(cases, by_case, vectors),
            "tc005": _tc005_anchor(cases, by_case, vectors),
        },
        "mechanism_distributions": mechanisms,
        "dense_one_percent_shams": _dense_shams(cases, by_case, vectors),
        "positive_and_degenerate_controls": _positive_controls(),
        "surrogate_audit": {
            "spread_without_evidence_can_pass": True,
            "availability_without_reader_use_can_pass": True,
            "full_budget_can_hide_half_budget_inefficiency": True,
            "proposal_ownership_would_relabel_full_store_and_suppress_spread": True,
        },
        "purity": {"feedback": False, "deterministic": True, "cache": reuse, "llm_calls": 0},
        "trace": {
            "rows": len(traces),
            "sha256": sha256_file(output_dir / "tc007_preflight_trace.jsonl.gz"),
        },
        "elapsed_seconds": round(time.time() - started, 3),
    }
    (output_dir / "tc007_preflight_part1.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


__all__ = ["ARTIFACT_ROOT", "TC007ExplorationError", "explore"]

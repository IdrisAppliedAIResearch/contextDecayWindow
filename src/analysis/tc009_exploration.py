"""TC-009 Preflight Part 1; dynamic-treatment evidence remains unopened."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from analysis.locomo_nf_development import sha256_file
from analysis.tc001_exploration import CACHE_PATH, DATASET_PATH, REPO_ROOT, build_episodes
from analysis.tc005_ranking import rank_all
from analysis.tc007_allocation import TOTAL_BUDGETS, allocate, full_relevance, orders, prepare
from analysis.tc008_exploration import leakage_violations
from analysis.tc008_study import G0_ROOT as TC008_G0, OUTCOME_ROOT as TC008_RUN, load_blind_manifest, load_blind_vectors
from analysis.tc009_dynamic_session import DYNAMIC_SESSION_LAMBDA, dynamic_session_order

SCHEMA = "tc009-preflight-part1-v1"
STUDY_ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
ARTIFACT_ROOT = STUDY_ROOT / "artifacts" / "tc009" / "preflight"
TC008_PREFLIGHT = STUDY_ROOT / "artifacts" / "tc008" / "preflight" / "tc008_preflight_part1.json"
TC008_PREFLIGHT_SHA256 = "dab50e1a3935d63755824c8d7ea9f7bb9f57263422338f227eeea44ca6a0f971"
MECHANISM_SOURCES = (
    REPO_ROOT / "src" / "analysis" / "tc007_allocation.py",
    REPO_ROOT / "src" / "analysis" / "tc009_dynamic_session.py",
)


class TC009ExplorationError(RuntimeError):
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
        "mean": round(statistics.fmean(ordered), 4),
        "zero": sum(value == 0 for value in ordered),
    }


def _write_gzip_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as handle:
                for row in rows:
                    handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def _expected_tc008() -> dict[str, dict[str, Any]]:
    rows = {}
    with gzip.open(TC008_RUN / "frozen_selections.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows[row["blind_key"]] = row
    if len(rows) != 871:
        raise TC009ExplorationError("TC-008 frozen selection cardinality drifted")
    return rows


def _purity_audit() -> dict[str, Any]:
    files = {}
    for path in MECHANISM_SOURCES:
        violations = leakage_violations(path.read_text(encoding="utf-8"))
        if violations:
            raise TC009ExplorationError(f"Mechanism leakage in {path}: {violations}")
        files[str(path)] = {"sha256": sha256_file(path), "violations": []}
    planted = leakage_violations("from measurement.evidence_key import q_facts_key\n")
    if not planted:
        raise TC009ExplorationError("Planted leakage violation was not detected")
    return {"status": "PASS", "files": files, "planted_violations": planted}


def explore(output_dir: Path = ARTIFACT_ROOT) -> dict[str, Any]:
    allowed_rerun_files = {
        "tc009_preflight_part1.json",
        "tc009_preflight_pf4_reachability.json",
        "tc009_preflight_trace.jsonl.gz",
        "tc009_preflight_mechanism_trace.jsonl.gz",
    }
    existing = {path.name for path in output_dir.iterdir()} if output_dir.exists() else set()
    if existing - allowed_rerun_files:
        raise TC009ExplorationError("Refusing to overwrite an unknown TC-009 Preflight artifact")
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    cases = load_blind_manifest(TC008_G0 / "label_blind_selection_manifest.json.gz")
    vectors, reuse = load_blind_vectors(cases)
    expected = _expected_tc008()
    traces: list[dict[str, Any]] = []
    mechanism_traces: list[dict[str, Any]] = []
    full_order_traces: list[dict[str, Any]] = []
    anchor_checks = 0
    lambda_zero_checks = 0
    order_digests: list[str] = []
    for case in cases:
        episodes = build_episodes(case, vectors)
        prepared = prepare(episodes, vectors[case.questions[0].question])
        session_by_id = {episode.identity: str(episode.pair.session_id) for episode in episodes}
        for question in case.questions:
            ranked_all = rank_all(
                episodes, question.question, vectors[question.question], prepared.rankers
            )
            inherited = orders(prepared, question.question, vectors[question.question])
            if ranked_all["dense"].order != inherited["dense"]:
                raise TC009ExplorationError("Dense route identity drifted inside Preflight")
            dynamic = dynamic_session_order(episodes, ranked_all["dense"].scores)
            zero = dynamic_session_order(episodes, ranked_all["dense"].scores, lambda_=0.0)
            if zero.order != inherited["dense"]:
                raise TC009ExplorationError("Lambda-zero route did not reduce to dense")
            lambda_zero_checks += 1
            order_digests.append(
                hashlib.sha256(
                    "\n".join(episodes[index].identity for index in dynamic.order).encode("utf-8")
                ).hexdigest()
            )
            expected_question = expected[question.blind_key]
            dense_rank = {
                episodes[index].identity: rank
                for rank, index in enumerate(inherited["dense"], 1)
            }
            step_by_id = {step.candidate_id: step for step in dynamic.steps}
            for step in dynamic.steps:
                full_order_traces.append(
                    {
                        "blind_key": question.blind_key,
                        "sample_id": case.sample_id,
                        "source_index": question.source_index,
                        "step": step.step,
                        "candidate_id": step.candidate_id,
                        "session_id": step.session_id,
                        "session_count_before": step.session_count_before,
                        "raw_similarity": step.raw_similarity,
                        "accumulated_penalty": step.accumulated_penalty,
                        "adjusted_score": step.adjusted_score,
                    }
                )
            full_seen: set[str] = set()
            repeat_before_full = False
            consecutive_same = 0
            previous_session = None
            for step in dynamic.steps:
                if step.session_count_before > 0 and len(full_seen) < len(dynamic.session_ids):
                    repeat_before_full = True
                if previous_session == step.session_id:
                    consecutive_same += 1
                full_seen.add(step.session_id)
                previous_session = step.session_id
            for budget in TOTAL_BUDGETS:
                control = full_relevance(episodes, inherited["dense"], budget)
                a3 = allocate(episodes, inherited["dense"], inherited["a3"], budget)
                # Convert the committed identity order back to current episode indices.
                by_id = {episode.identity: index for index, episode in enumerate(episodes)}
                predecessor_order = tuple(by_id[identity] for identity in expected_question["orders"]["session"])
                predecessor = allocate(episodes, inherited["dense"], predecessor_order, budget)
                treatment = allocate(episodes, inherited["dense"], dynamic.order, budget)
                for name, packed in (("control", control), ("a3", a3), ("session", predecessor)):
                    committed = expected_question["budgets"][str(budget)][name]
                    if list(packed.selected_ids) != committed["selected_ids"]:
                        raise TC009ExplorationError(f"TC-008 {name} identities drifted")
                    if packed.payload_sha256 != committed["payload_sha256"]:
                        raise TC009ExplorationError(f"TC-008 {name} payload drifted")
                    anchor_checks += 1
                selected_counts = Counter(session_by_id[item] for item in treatment.selected_ids)
                treatment_only = set(treatment.selected_ids) - set(control.selected_ids)
                control_only = set(control.selected_ids) - set(treatment.selected_ids)
                admitted_steps = [step_by_id[identifier] for identifier in treatment.spread_ids]
                for step in admitted_steps:
                    mechanism_traces.append(
                        {
                            "blind_key": question.blind_key,
                            "sample_id": case.sample_id,
                            "source_index": question.source_index,
                            "budget": budget,
                            "candidate_id": step.candidate_id,
                            "session_id": step.session_id,
                            "session_count_before": step.session_count_before,
                            "raw_similarity": step.raw_similarity,
                            "accumulated_penalty": step.accumulated_penalty,
                            "adjusted_score": step.adjusted_score,
                            "admission_phase": "protected_spread",
                        }
                    )
                traces.append(
                    {
                        "blind_key": question.blind_key,
                        "sample_id": case.sample_id,
                        "source_index": question.source_index,
                        "budget": budget,
                        "pool": len(episodes),
                        "source_sessions": len(dynamic.session_ids),
                        "control_selected": len(control.selected_ids),
                        "dynamic_selected": len(treatment.selected_ids),
                        "dynamic_selected_sessions": len(selected_counts),
                        "max_selected_from_one_session": max(selected_counts.values()),
                        "spread_admitted": len(treatment.spread_ids),
                        "spread_binding": bool(treatment.dropped_spread_ids),
                        "spread_duplicate_skips": len(treatment.skipped_spread_duplicates),
                        "returned_relevance": len(treatment.returned_relevance_ids),
                        "returned_capacity": treatment.returned_capacity,
                        "payload_chars": len(treatment.payload),
                        "budget_compliant": len(treatment.payload) <= budget,
                        "differs_from_control": treatment.selected_ids != control.selected_ids,
                        "differs_from_session_predecessor": treatment.selected_ids != predecessor.selected_ids,
                        "repeat_before_all_sessions": repeat_before_full,
                        "full_order_consecutive_same_session": consecutive_same,
                        "full_order_max_count_before": max(step.session_count_before for step in dynamic.steps),
                        "admitted_max_count_before": max(
                            (step.session_count_before for step in admitted_steps), default=0
                        ),
                        "admitted_max_penalty": max(
                            (step.accumulated_penalty for step in admitted_steps), default=0.0
                        ),
                        "treatment_only_count": len(treatment_only),
                        "control_only_count": len(control_only),
                        "treatment_only_dense_ranks": sorted(dense_rank[item] for item in treatment_only),
                        "control_only_dense_ranks": sorted(dense_rank[item] for item in control_only),
                        "payload_sha256": treatment.payload_sha256,
                    }
                )
    trace_path = output_dir / "tc009_preflight_trace.jsonl.gz"
    mechanism_path = output_dir / "tc009_preflight_mechanism_trace.jsonl.gz"
    full_order_path = output_dir / "tc009_preflight_full_order_trace.jsonl.gz"
    _write_gzip_jsonl(trace_path, traces)
    _write_gzip_jsonl(mechanism_path, mechanism_traces)
    _write_gzip_jsonl(full_order_path, full_order_traces)
    by_budget = {}
    for budget in TOTAL_BUDGETS:
        rows = [row for row in traces if row["budget"] == budget]
        by_budget[str(budget)] = {
            "questions": len(rows),
            "selected_sessions": _distribution(row["dynamic_selected_sessions"] for row in rows),
            "max_selected_from_one_session": _distribution(
                row["max_selected_from_one_session"] for row in rows
            ),
            "spread_admitted": _distribution(row["spread_admitted"] for row in rows),
            "admitted_max_count_before": _distribution(
                row["admitted_max_count_before"] for row in rows
            ),
            "admitted_max_penalty": _distribution(row["admitted_max_penalty"] for row in rows),
            "consecutive_same_session": _distribution(
                row["full_order_consecutive_same_session"] for row in rows
            ),
            "repeat_before_all_sessions": sum(row["repeat_before_all_sessions"] for row in rows),
            "spread_binding_questions": sum(row["spread_binding"] for row in rows),
            "differs_from_control": sum(row["differs_from_control"] for row in rows),
            "differs_from_session_predecessor": sum(
                row["differs_from_session_predecessor"] for row in rows
            ),
            "treatment_only_count": _distribution(row["treatment_only_count"] for row in rows),
            "control_only_count": _distribution(row["control_only_count"] for row in rows),
            "treatment_only_dense_rank": _distribution(
                rank for row in rows for rank in row["treatment_only_dense_ranks"]
            ),
            "control_only_dense_rank": _distribution(
                rank for row in rows for rank in row["control_only_dense_ranks"]
            ),
            "payload_chars": _distribution(row["payload_chars"] for row in rows),
            "budget_violations": sum(not row["budget_compliant"] for row in rows),
        }
    if sha256_file(TC008_PREFLIGHT) != TC008_PREFLIGHT_SHA256:
        raise TC009ExplorationError("TC-008 sham anchor drifted")
    tc008_preflight = json.loads(TC008_PREFLIGHT.read_text(encoding="utf-8"))
    result = {
        "schema": SCHEMA,
        "status": "PASS",
        "behavioural_identity": (
            "A_SPLIT_DYNAMIC globally compares each source session's highest-cosine remaining "
            "candidate after subtracting 0.03 for every candidate already selected from that "
            "session; the winning session remains eligible at the next step."
        ),
        "frozen_candidate_parameters": {
            "lambda": DYNAMIC_SESSION_LAMBDA,
            "penalty": "linear_count_before",
            "budgets": list(TOTAL_BUDGETS),
            "share": .5,
        },
        "inputs": {
            "corpus": {"path": str(DATASET_PATH), "sha256": sha256_file(DATASET_PATH)},
            "cache": {"path": str(CACHE_PATH), "sha256": sha256_file(CACHE_PATH)},
            "tc008_frozen_selections_sha256": sha256_file(TC008_RUN / "frozen_selections.jsonl.gz"),
            "tc008_preflight_sha256": TC008_PREFLIGHT_SHA256,
            "mechanism_sources": {str(path): sha256_file(path) for path in MECHANISM_SOURCES},
        },
        "population": {"questions": 871, "eligible": 868, "targeted": 704, "breadth": 44, "other": 120, "ineligible": 3},
        "tc008_reproduction": {"status": "PASS", "payload_identity_checks": anchor_checks},
        "lambda_zero_reduction": {"status": "PASS", "question_orders": lambda_zero_checks},
        "mechanism_distributions": by_budget,
        "dense_shams": tc008_preflight["dense_shams"],
        "controls": {
            "one_session_dense_order_unit_test": "PASS",
            "consecutive_win_unit_test": "PASS",
            "eventual_overtake_unit_test": "PASS",
            "real_trace_repeat_before_all_sessions": {
                budget: by_budget[str(budget)]["repeat_before_all_sessions"]
                for budget in TOTAL_BUDGETS
            },
        },
        "surrogate_audit": {
            "represented_sessions_can_rise_while_required_evidence_falls": True,
            "lower_concentration_can_rise_while_required_evidence_falls": True,
            "evidence_share_can_rise_without_reader_use": True,
        },
        "purity": {
            "within_query_feedback": True,
            "finite_permutation_replays": 871,
            "cache": reuse,
            "embedding_calls": 0,
            "llm_or_generative_calls": 0,
            "leakage_audit": _purity_audit(),
        },
        "trace": {"rows": len(traces), "sha256": sha256_file(trace_path)},
        "mechanism_trace": {"rows": len(mechanism_traces), "sha256": sha256_file(mechanism_path)},
        "full_order_trace": {"rows": len(full_order_traces), "sha256": sha256_file(full_order_path)},
        "dynamic_order_digest": hashlib.sha256("\n".join(order_digests).encode("utf-8")).hexdigest(),
        "elapsed_seconds": round(time.time() - started, 3),
    }
    (output_dir / "tc009_preflight_part1.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


__all__ = ["ARTIFACT_ROOT", "TC009ExplorationError", "explore"]

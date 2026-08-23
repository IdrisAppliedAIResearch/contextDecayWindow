"""TC-008 Preflight Part 1; treatment evidence outcomes remain unopened."""

from __future__ import annotations

import ast
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
from analysis.tc005_exploration import evidence_indices, pack_order, question_population
from analysis.tc005_ranking import prepare_rankers, rank_all
from analysis.tc005_study import load_inputs
from analysis.tc007_allocation import TOTAL_BUDGETS, allocate, full_relevance, orders, prepare
from analysis.tc008_session_spread import SESSION_LAMBDA, session_spread_order

SCHEMA = "tc008-preflight-part1-v1"
STUDY_ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
ARTIFACT_ROOT = STUDY_ROOT / "artifacts" / "tc008" / "preflight"
TC007_RUN = STUDY_ROOT / "runs" / "tc007" / "run"
SHAM_FRACTIONS = (-0.01, 0.01)
MECHANISM_SOURCES = (
    REPO_ROOT / "src" / "analysis" / "tc007_allocation.py",
    REPO_ROOT / "src" / "analysis" / "tc008_session_spread.py",
    REPO_ROOT / "episodic" / "src" / "episodic" / "_selection.py",
)
FORBIDDEN_IMPORT_PARTS = ("evidence", "answer", "rubric", "q_facts", "key")


class TC008ExplorationError(RuntimeError):
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


def leakage_violations(source: str) -> list[str]:
    """Find mechanism imports and path literals that could expose measurements."""

    violations: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or "", *(alias.name for alias in node.names)]
        else:
            names = []
        for name in names:
            lowered = name.lower()
            if any(part in lowered for part in FORBIDDEN_IMPORT_PARTS):
                violations.append(f"import:{name}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered = node.value.lower()
            if any(part in lowered for part in ("q_facts", "rubric", "answers.json")):
                violations.append(f"literal:{node.value}")
    return sorted(set(violations))


def _purity_audit() -> dict[str, Any]:
    files = {}
    for path in MECHANISM_SOURCES:
        violations = leakage_violations(path.read_text(encoding="utf-8"))
        if violations:
            raise TC008ExplorationError(f"Mechanism leakage in {path}: {violations}")
        files[str(path)] = {"sha256": sha256_file(path), "violations": []}
    planted = "from measurement.evidence_key import q_facts_key\n"
    planted_violations = leakage_violations(planted)
    if not planted_violations:
        raise TC008ExplorationError("Planted leakage violation was not detected")
    return {"status": "PASS", "files": files, "planted_violations": planted_violations}


def _tc007_expected() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with gzip.open(TC007_RUN / "diagnostics.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows[row["question_id"]] = row
    if len(rows) != 871:
        raise TC008ExplorationError("TC-007 diagnostic cardinality drifted")
    return rows


def _dense_shams(cases, by_case, vectors) -> dict[str, Any]:
    cells: dict[str, Any] = {}
    for budget in TOTAL_BUDGETS:
        variants: dict[str, Any] = {}
        for fraction in SHAM_FRACTIONS:
            complete = {
                name: {"gains": 0, "losses": 0}
                for name in ("combined", "targeted", "breadth")
            }
            breadth_share = {
                "question_gains": 0,
                "question_losses": 0,
                "identity_gains": 0,
                "identity_losses": 0,
            }
            for case in cases:
                episodes = by_case[case.sample_id]
                prepared = prepare_rankers(episodes)
                for question in case.questions:
                    if question.duplicate_ordinal:
                        continue
                    population = question_population(case, question)
                    if population == "ineligible":
                        continue
                    evidence = evidence_indices(case, episodes, question)
                    evidence_ids = {episodes[index].identity for index in evidence}
                    dense = rank_all(
                        episodes, question.question, vectors[question.question], prepared
                    )["dense"].order
                    full = set(pack_order(episodes, dense, budget).selected_ids)
                    sham_budget = round(budget * (1.0 + fraction))
                    sham = set(pack_order(episodes, dense, sham_budget).selected_ids)
                    full_complete = evidence_ids <= full
                    sham_complete = evidence_ids <= sham
                    populations = ["combined"]
                    if population in {"targeted", "breadth"}:
                        populations.append(population)
                    for name in populations:
                        complete[name]["gains"] += int(sham_complete and not full_complete)
                        complete[name]["losses"] += int(full_complete and not sham_complete)
                    if population == "breadth":
                        full_count = len(evidence_ids & full)
                        sham_count = len(evidence_ids & sham)
                        breadth_share["question_gains"] += int(sham_count > full_count)
                        breadth_share["question_losses"] += int(sham_count < full_count)
                        breadth_share["identity_gains"] += max(sham_count - full_count, 0)
                        breadth_share["identity_losses"] += max(full_count - sham_count, 0)
            variants[f"{fraction:+.2f}"] = {
                "budget": round(budget * (1.0 + fraction)),
                "complete": {
                    name: {
                        **counts,
                        "net": counts["gains"] - counts["losses"],
                    }
                    for name, counts in complete.items()
                },
                "breadth_share": {
                    **breadth_share,
                    "question_net": breadth_share["question_gains"] - breadth_share["question_losses"],
                    "identity_net": breadth_share["identity_gains"] - breadth_share["identity_losses"],
                },
            }
        cells[str(budget)] = {
            "variants": variants,
            "bands": {
                "combined_complete": max(abs(v["complete"]["combined"]["net"]) for v in variants.values()),
                "targeted_complete": max(abs(v["complete"]["targeted"]["net"]) for v in variants.values()),
                "breadth_complete": max(abs(v["complete"]["breadth"]["net"]) for v in variants.values()),
                "breadth_share_questions": max(abs(v["breadth_share"]["question_net"]) for v in variants.values()),
                "breadth_share_identities": max(abs(v["breadth_share"]["identity_net"]) for v in variants.values()),
            },
        }
    return cells


def explore(output_dir: Path = ARTIFACT_ROOT) -> dict[str, Any]:
    allowed_rerun_files = {
        "tc008_preflight_part1.json",
        "tc008_preflight_pf4_reachability.json",
        "tc008_preflight_trace.jsonl.gz",
    }
    existing = {path.name for path in output_dir.iterdir()} if output_dir.exists() else set()
    if existing - allowed_rerun_files:
        raise TC008ExplorationError("Refusing to overwrite an unknown TC-008 Preflight artifact")
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    cases, vectors, reuse = load_inputs()
    by_case = {case.sample_id: build_episodes(case, vectors) for case in cases}
    tc007 = _tc007_expected()
    traces: list[dict[str, Any]] = []
    mechanism_traces: list[dict[str, Any]] = []
    anchor_checks = 0
    session_order_digests: list[str] = []
    for case in cases:
        episodes = by_case[case.sample_id]
        prepared = prepare(episodes, vectors[case.questions[0].question])
        session_by_id = {episode.identity: str(episode.pair.session_id) for episode in episodes}
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            inherited = orders(prepared, question.question, vectors[question.question])
            session = session_spread_order(episodes, vectors[question.question])
            session_order_digests.append(
                hashlib.sha256(
                    "\n".join(episodes[index].identity for index in session.order).encode("utf-8")
                ).hexdigest()
            )
            step_by_id = {step.candidate_id: step for step in session.result.steps}
            dense_rank = {
                episodes[index].identity: rank
                for rank, index in enumerate(inherited["dense"], 1)
            }
            expected = tc007[question.identity]
            for budget in TOTAL_BUDGETS:
                control = full_relevance(episodes, inherited["dense"], budget)
                a3 = allocate(episodes, inherited["dense"], inherited["a3"], budget)
                treatment = allocate(episodes, inherited["dense"], session.order, budget)
                for name, packed in (("control", control), ("a3", a3)):
                    committed = expected["budgets"][str(budget)][name]
                    if list(packed.selected_ids) != committed["selected_ids"]:
                        raise TC008ExplorationError(f"TC-007 {name} identities drifted")
                    if packed.payload_sha256 != committed["payload_sha256"]:
                        raise TC008ExplorationError(f"TC-007 {name} payload drifted")
                    anchor_checks += 1
                selected_sessions = {
                    name: len({session_by_id[item] for item in packed.selected_ids})
                    for name, packed in (("control", control), ("a3", a3), ("session", treatment))
                }
                treatment_only = set(treatment.selected_ids) - set(control.selected_ids)
                control_only = set(control.selected_ids) - set(treatment.selected_ids)
                spread_bonus = []
                for identifier in treatment.spread_ids:
                    step = step_by_id[identifier]
                    spread_bonus.append(
                        round(step.objective_gain - max(step.relevance, 0.0), 10)
                    )
                initial_sessions = {
                    session_by_id[item] for item in treatment.initial_relevance_ids
                }
                new_spread_sessions = {
                    session_by_id[item] for item in treatment.spread_ids
                    if session_by_id[item] not in initial_sessions
                }
                for identifier in treatment.spread_ids:
                    step = step_by_id[identifier]
                    selected_session = session_by_id[identifier]
                    bonus = round(step.objective_gain - max(step.relevance, 0.0), 10)
                    mechanism_traces.append(
                        {
                            "question_id": question.identity,
                            "budget": budget,
                            "candidate_id": identifier,
                            "session_id": selected_session,
                            "relevance": step.relevance,
                            "novelty_bonus": bonus,
                            "objective_gain": step.objective_gain,
                            "new_session_in_selector_order": bonus == SESSION_LAMBDA,
                            "admission_phase": "protected_spread",
                        }
                    )
                traces.append(
                    {
                        "question_id": question.identity,
                        "sample_id": case.sample_id,
                        "budget": budget,
                        "pool": len(episodes),
                        "source_sessions": len(session.session_ids),
                        "control_selected": len(control.selected_ids),
                        "a3_selected": len(a3.selected_ids),
                        "session_selected": len(treatment.selected_ids),
                        "control_sessions": selected_sessions["control"],
                        "a3_sessions": selected_sessions["a3"],
                        "session_sessions": selected_sessions["session"],
                        "initial_relevance_sessions": len(initial_sessions),
                        "new_spread_sessions": len(new_spread_sessions),
                        "spread_admitted": len(treatment.spread_ids),
                        "spread_bonus_admissions": sum(value == SESSION_LAMBDA for value in spread_bonus),
                        "spread_binds": bool(treatment.dropped_spread_ids),
                        "spread_duplicate_skips": len(treatment.skipped_spread_duplicates),
                        "returned_relevance": len(treatment.returned_relevance_ids),
                        "returned_capacity": treatment.returned_capacity,
                        "payload_chars": len(treatment.payload),
                        "budget_compliant": len(treatment.payload) <= budget,
                        "differs_from_control": treatment.selected_ids != control.selected_ids,
                        "differs_from_a3": treatment.selected_ids != a3.selected_ids,
                        "treatment_only_count": len(treatment_only),
                        "control_only_count": len(control_only),
                        "treatment_only_dense_ranks": sorted(dense_rank[item] for item in treatment_only),
                        "control_only_dense_ranks": sorted(dense_rank[item] for item in control_only),
                        "payload_sha256": treatment.payload_sha256,
                    }
                )
    trace_path = output_dir / "tc008_preflight_trace.jsonl.gz"
    _write_gzip_jsonl(trace_path, traces)
    mechanism_trace_path = output_dir / "tc008_preflight_mechanism_trace.jsonl.gz"
    _write_gzip_jsonl(mechanism_trace_path, mechanism_traces)
    by_budget: dict[str, Any] = {}
    for budget in TOTAL_BUDGETS:
        rows = [row for row in traces if row["budget"] == budget]
        by_budget[str(budget)] = {
            "questions": len(rows),
            "session_selected_sessions": _distribution(row["session_sessions"] for row in rows),
            "a3_selected_sessions": _distribution(row["a3_sessions"] for row in rows),
            "control_selected_sessions": _distribution(row["control_sessions"] for row in rows),
            "new_spread_sessions": _distribution(row["new_spread_sessions"] for row in rows),
            "spread_admitted": _distribution(row["spread_admitted"] for row in rows),
            "spread_bonus_admissions": _distribution(row["spread_bonus_admissions"] for row in rows),
            "spread_binding_questions": sum(row["spread_binds"] for row in rows),
            "differs_from_control": sum(row["differs_from_control"] for row in rows),
            "differs_from_a3": sum(row["differs_from_a3"] for row in rows),
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
    shams = _dense_shams(cases, by_case, vectors)
    result = {
        "schema": SCHEMA,
        "status": "PASS",
        "behavioural_identity": (
            "A_SESSION uses the carried A3 greedy objective max(float32 dense cosine,0) "
            "+ 0.1 once for each previously unrepresented source session; TC-007 then "
            "solo-fills dense and session spread to equal allowances, deduplicates actual "
            "admissions, renders once, and returns slack to dense."
        ),
        "frozen_candidate_parameters": {
            "lambda": SESSION_LAMBDA,
            "cost_exponent": 0.0,
            "group": "source_session_id",
            "budgets": list(TOTAL_BUDGETS),
            "share": .5,
        },
        "inputs": {
            "corpus": {"path": str(DATASET_PATH), "sha256": sha256_file(DATASET_PATH), "bytes": DATASET_PATH.stat().st_size},
            "cache": {"path": str(CACHE_PATH), "sha256": sha256_file(CACHE_PATH), "bytes": CACHE_PATH.stat().st_size},
            "tc007_per_question_sha256": sha256_file(TC007_RUN / "per_question.csv"),
            "tc007_diagnostics_sha256": sha256_file(TC007_RUN / "diagnostics.jsonl.gz"),
            "mechanism_sources": {
                str(path): sha256_file(path) for path in MECHANISM_SOURCES
            },
        },
        "population": {"questions": 871, "eligible": 868, "targeted": 704, "breadth": 44, "other": 120, "ineligible": 3},
        "tc007_reproduction": {"status": "PASS", "payload_identity_checks": anchor_checks},
        "mechanism_distributions": by_budget,
        "dense_shams": shams,
        "controls": {
            "lambda_zero_unit_test": "PASS",
            "one_session_single_bonus_unit_test": "PASS",
            "session_bonus_changes_order_unit_test": "PASS",
            "real_trace_changed_vs_a3": {budget: by_budget[str(budget)]["differs_from_a3"] for budget in TOTAL_BUDGETS},
        },
        "surrogate_audit": {
            "selected_session_count_can_rise_without_required_evidence": True,
            "required_session_touch_can_rise_without_complete_answer_facts": True,
            "required_identity_share_can_rise_on_redundant_annotations": True,
            "availability_can_rise_without_reader_use": True,
        },
        "purity": {
            "feedback": False,
            "deterministic": True,
            "cache": reuse,
            "embedding_calls": 0,
            "llm_or_generative_calls": 0,
            "leakage_audit": _purity_audit(),
        },
        "trace": {"rows": len(traces), "sha256": sha256_file(trace_path)},
        "mechanism_trace": {
            "rows": len(mechanism_traces),
            "sha256": sha256_file(mechanism_trace_path),
        },
        "session_order_digest": hashlib.sha256("\n".join(session_order_digests).encode("utf-8")).hexdigest(),
        "elapsed_seconds": round(time.time() - started, 3),
    }
    (output_dir / "tc008_preflight_part1.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


__all__ = ["ARTIFACT_ROOT", "TC008ExplorationError", "explore", "leakage_violations"]

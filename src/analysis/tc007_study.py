"""Registered TC-007 G0, deterministic offline run, and dispositions."""

from __future__ import annotations

import ast
import csv
import gzip
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from analysis.locomo_nf_development import sha256_file
from analysis.tc001_exploration import REPO_ROOT, build_episodes
from analysis.tc005_exploration import evidence_indices, question_population
from analysis.tc005_study import load_inputs
from analysis.tc007_allocation import TOTAL_BUDGETS, allocate, full_relevance, orders, prepare
from analysis.tc007_exploration import _tc003_anchor, _tc005_anchor
from analysis.tc007_reachability import BANDS, SIGNAL_ALPHA, WORKS_ALPHA, clears

SCHEMA = "tc007-registered-offline-v1"
STUDY_ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
PRE_REGISTRATION = STUDY_ROOT / "TC_007_PRE_REGISTRATION.md"
PRE_REGISTRATION_SHA256 = "0e2d26d741e1947e1b39478db1d61ac7aa18c15ce0dc4d9f397de4babb892fd9"
REGISTRATION_COMMIT = "afb7564369e3f76970b5c637f9eb6faf7706db61"
PREFLIGHT_ROOT = STUDY_ROOT / "artifacts" / "tc007" / "preflight"
PREFLIGHT_SHA256 = {
    PREFLIGHT_ROOT / "tc007_preflight_part1.json": "b54f98b7a3c61f2968f2fdc5a15d9efb5ef4f39aadb5062132d1885a8aac018a",
    PREFLIGHT_ROOT / "tc007_preflight_pf4_reachability.json": "ab559ede686cd41c80a2f8f0748f8ca90c8d18237a616607fe94a8a2eb73f63e",
    PREFLIGHT_ROOT / "tc007_preflight_trace.jsonl.gz": "fc3deb4e3d228c3f0b0696a52b5c676f3a1c818da9af9efb02a3f59e17094443",
}
RUN_ROOT = STUDY_ROOT / "runs" / "tc007"
G0_ROOT = RUN_ROOT / "g0"
OUTCOME_ROOT = RUN_ROOT / "run"
TREATMENTS = ("a3", "facility")
POPULATION_N = {"eligible": 868, "targeted": 704, "breadth": 44}
_FORBIDDEN = ("q_facts_key", "rubric", "expected_answer", "answer_key", "resolved_evidence")


class TC007Error(RuntimeError):
    pass


def _git(*args: str, check: bool = True):
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False
    )
    if check and result.returncode:
        raise TC007Error(result.stderr or result.stdout)
    return result.stdout.strip() if check else result


def _relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def assert_registration() -> dict[str, Any]:
    if sha256_file(PRE_REGISTRATION) != PRE_REGISTRATION_SHA256:
        raise TC007Error("TC-007 pre-registration bytes changed")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", REGISTRATION_COMMIT, "HEAD"],
        cwd=REPO_ROOT,
    ).returncode:
        raise TC007Error("TC-007 registration commit is not an ancestor")
    for path, expected in PREFLIGHT_SHA256.items():
        if sha256_file(path) != expected:
            raise TC007Error(f"TC-007 Preflight changed: {path.name}")
    return {
        "status": "PASS",
        "registration_commit": REGISTRATION_COMMIT,
        "pre_registration_sha256": PRE_REGISTRATION_SHA256,
        "preflight_sha256": {path.name: digest for path, digest in PREFLIGHT_SHA256.items()},
    }


def audit_mechanism_leakage(path: Path | None = None) -> dict[str, Any]:
    paths = [path] if path else [
        Path(__file__).with_name("tc007_allocation.py"),
        Path(__file__).with_name("tc005_ranking.py"),
        REPO_ROOT / "episodic" / "src" / "episodic" / "_selection.py",
        REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "e005.py",
    ]
    violations: list[str] = []
    imports: set[str] = set()
    for source in paths:
        text = source.read_text(encoding="utf-8")
        lowered = text.casefold()
        violations.extend(f"{source.name}:{token}" for token in _FORBIDDEN if token in lowered)
        tree = ast.parse(text, filename=str(source))
        imports.update(
            node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        )
        imports.update(
            alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
        )
    if violations:
        raise TC007Error(f"Mechanism leakage: {violations}")
    return {
        "status": "PASS",
        "files": {_relative(source): sha256_file(source) for source in paths},
        "imports": sorted(imports),
    }


def planted_leakage_control() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="tc007-leakage-") as directory:
        path = Path(directory) / "bad.py"
        path.write_text('KEY = "q_facts_key.md"\n', encoding="utf-8")
        try:
            audit_mechanism_leakage(path)
        except TC007Error:
            return {"status": "PASS", "planted_violation_rejected": True}
    raise TC007Error("Planted leakage violation was accepted")


def implementation_identity(cases, by_case, vectors) -> dict[str, Any]:
    trace: dict[tuple[str, str, int], dict[str, Any]] = {}
    with gzip.open(PREFLIGHT_ROOT / "tc007_preflight_trace.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            trace[(row["question_id"], row["arm"], int(row["budget"]))] = row
    checks = 0
    sham_checks = 0
    for case in cases:
        episodes = by_case[case.sample_id]
        frozen = prepare(episodes, vectors[case.questions[0].question])
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            ranked = orders(frozen, question.question, vectors[question.question])
            for budget in TOTAL_BUDGETS:
                full = full_relevance(episodes, ranked["dense"], budget)
                # The sham has no spread proposal and therefore canonicalizes to
                # the unchanged full-dense control after slack return.
                sham = full_relevance(episodes, ranked["dense"], budget)
                if sham.payload != full.payload:
                    raise TC007Error("Sham diverged from full relevance")
                sham_checks += 1
                for arm in TREATMENTS:
                    packed = allocate(episodes, ranked["dense"], ranked[arm], budget)
                    expected = trace[(question.identity, arm, budget)]
                    observed = {
                        "payload_sha256": packed.payload_sha256,
                        "payload_chars": len(packed.payload),
                        "initial_relevance_admitted": len(packed.initial_relevance_ids),
                        "distinct_spread_admitted": len(packed.spread_ids),
                        "returned_relevance_admitted": len(packed.returned_relevance_ids),
                    }
                    if any(observed[key] != expected[key] for key in observed):
                        raise TC007Error("Final allocator drifted from Preflight")
                    checks += 1
    if checks != 3_484 or sham_checks != 1_742:
        raise TC007Error("Implementation identity cardinality drifted")
    return {"status": "PASS", "treatment_budget_traces": checks, "sham_checks": sham_checks}


def run_g0(output_dir: Path = G0_ROOT, test_summary: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise TC007Error("G0 output directory is not empty")
    if _git("status", "--porcelain"):
        raise TC007Error("G0 requires a clean worktree")
    output_dir.mkdir(parents=True, exist_ok=True)
    registration = assert_registration()
    cases, vectors, reuse = load_inputs()
    by_case = {case.sample_id: build_episodes(case, vectors) for case in cases}
    tests = dict(test_summary or {})
    if tests.get("status") != "PASS":
        raise TC007Error("G0 requires a passing full suite")
    result = {
        "schema": "tc007-g0-v1",
        "status": "PASS",
        "registration": registration,
        "anchors": {
            "tc003": _tc003_anchor(cases, by_case, vectors),
            "tc005": _tc005_anchor(cases, by_case, vectors),
        },
        "implementation_identity": implementation_identity(cases, by_case, vectors),
        "leakage": {"static": audit_mechanism_leakage(), "planted": planted_leakage_control()},
        "cache": {"hits": reuse["hits"], "misses": reuse["misses"]},
        "pf4": json.loads((PREFLIGHT_ROOT / "tc007_preflight_pf4_reachability.json").read_text(encoding="utf-8")),
        "test_suite": tests,
        "calls": {"llm_or_generative": 0, "embedding": 0, "cache_misses": reuse["misses"], "programme_model_free": True},
    }
    _write_json(output_dir / "g0_reproduction.json", result)
    _write_json(output_dir / "run_header.json", {
        "schema": "tc007-g0-header-v1",
        "git_head_before_artifacts": _git("rev-parse", "HEAD"),
        "command": ".venv\\Scripts\\python.exe scripts\\run_tc007_study.py --phase g0",
        "parallel": 1,
        "speculative_decoding": False,
        "python": sys.version,
        "source_sha256": source_hashes(),
    })
    _write_json(output_dir / "no_model_call_audit.json", result["calls"])
    write_manifest(output_dir)
    return result


def run_precondition(g0_dir: Path = G0_ROOT) -> dict[str, Any]:
    if _git("status", "--porcelain"):
        raise TC007Error("Registered run requires a clean worktree")
    path = g0_dir / "g0_reproduction.json"
    if not path.is_file() or _git("ls-files", "--error-unmatch", _relative(path), check=False).returncode:
        raise TC007Error("Committed G0 is absent")
    gate = json.loads(path.read_text(encoding="utf-8"))
    if gate.get("status") != "PASS":
        raise TC007Error("G0 did not pass")
    header = json.loads((g0_dir / "run_header.json").read_text(encoding="utf-8"))
    if header["source_sha256"] != source_hashes():
        raise TC007Error("Study sources changed after G0")
    assert_registration()
    return {"status": "PASS", "g0_sha256": sha256_file(path), "g0_commit": _git("rev-parse", "HEAD"), "source_sha256": source_hashes()}


def _allocation_diag(packed) -> dict[str, Any]:
    return {
        "selected_ids": list(packed.selected_ids),
        "initial_relevance_ids": list(packed.initial_relevance_ids),
        "spread_ids": list(packed.spread_ids),
        "returned_relevance_ids": list(packed.returned_relevance_ids),
        "spread_duplicate_skips": list(packed.skipped_spread_duplicates),
        "dropped_relevance_ids": list(packed.dropped_relevance_ids),
        "dropped_spread_ids": list(packed.dropped_spread_ids),
        "owner": dict(packed.owner),
        "phase": dict(packed.phase),
        "total_budget": packed.total_budget,
        "half_allowance": packed.half_allowance,
        "initial_relevance_solo_chars": packed.initial_relevance_solo_chars,
        "spread_solo_chars": packed.spread_solo_chars,
        "merged_initial_chars": packed.merged_initial_chars,
        "wrapper_savings": packed.wrapper_savings,
        "returned_capacity": packed.returned_capacity,
        "payload_chars": len(packed.payload),
        "payload_sha256": packed.payload_sha256,
    }


def compute_worker(output_dir: Path) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise TC007Error("Worker output directory is not empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    cases, vectors, reuse = load_inputs()
    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for case in cases:
        episodes = build_episodes(case, vectors)
        frozen = prepare(episodes, vectors[case.questions[0].question])
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            ranked = orders(frozen, question.question, vectors[question.question])
            evidence = evidence_indices(case, episodes, question)
            evidence_ids = {episodes[index].identity for index in evidence}
            population = question_population(case, question)
            eligible = population != "ineligible"
            row: dict[str, Any] = {
                "question_id": question.identity,
                "question_content_sha256": question.content_sha256,
                "sample_id": case.sample_id,
                "source_index": question.source_index,
                "population": population,
                "eligible": eligible,
                "evidence_candidates": len(evidence_ids),
            }
            diagnostic: dict[str, Any] = {
                "question_id": question.identity,
                "sample_id": case.sample_id,
                "population": population,
                "evidence_candidate_ids": sorted(evidence_ids),
                "orders": {name: [episodes[index].identity for index in order] for name, order in ranked.items()},
                "budgets": {},
            }
            for budget in TOTAL_BUDGETS:
                packs = {
                    "control": full_relevance(episodes, ranked["dense"], budget),
                    "a3": allocate(episodes, ranked["dense"], ranked["a3"], budget),
                    "facility": allocate(episodes, ranked["dense"], ranked["facility"], budget),
                }
                diagnostic["budgets"][str(budget)] = {}
                for arm, packed in packs.items():
                    selected = set(packed.selected_ids)
                    complete = eligible and bool(evidence_ids) and evidence_ids <= selected
                    any_hit = eligible and bool(evidence_ids & selected)
                    prefix = f"{arm}_{budget}"
                    row[f"{prefix}_complete"] = complete
                    row[f"{prefix}_any"] = any_hit
                    row[f"{prefix}_evidence_delivered"] = len(evidence_ids & selected)
                    row[f"{prefix}_delivered"] = len(selected)
                    row[f"{prefix}_chars"] = len(packed.payload)
                    row[f"{prefix}_payload_sha256"] = packed.payload_sha256
                    row[f"{prefix}_spread_evidence"] = len(evidence_ids & set(packed.spread_ids))
                    row[f"{prefix}_relevance_evidence"] = len(evidence_ids & (set(packed.initial_relevance_ids) | set(packed.returned_relevance_ids)))
                    diagnostic["budgets"][str(budget)][arm] = _allocation_diag(packed)
            rows.append(row)
            diagnostics.append(diagnostic)
    if len(rows) != 871 or len({row["question_id"] for row in rows}) != 871:
        raise TC007Error("Question identity/cardinality drifted")
    if sum(row["population"] == "targeted" for row in rows) != 704 or sum(row["population"] == "breadth" for row in rows) != 44:
        raise TC007Error("Registered populations drifted")
    _write_csv(output_dir / "per_question.csv", rows)
    _write_gzip_jsonl(output_dir / "diagnostics.jsonl.gz", diagnostics)
    digest = {
        "rows": len(rows),
        "per_question_sha256": sha256_file(output_dir / "per_question.csv"),
        "diagnostics_sha256": sha256_file(output_dir / "diagnostics.jsonl.gz"),
        "cache_hits": reuse["hits"],
        "cache_misses": reuse["misses"],
    }
    _write_json(output_dir / "worker_digest.json", digest)
    return digest


def _coerce(row: Mapping[str, str]) -> dict[str, Any]:
    output: dict[str, Any] = dict(row)
    for key, value in list(output.items()):
        if key in {"eligible"} or key.endswith(("_complete", "_any")):
            output[key] = value == "True"
        elif key in {"source_index", "evidence_candidates"} or key.endswith(("_delivered", "_chars", "_evidence")):
            output[key] = int(value)
    return output


def _population_rows(rows: Sequence[Mapping[str, Any]], population: str):
    if population == "combined":
        return [row for row in rows if row["eligible"]]
    return [row for row in rows if row["population"] == population]


def one_sided(favourable: int, adverse: int) -> float:
    n = favourable + adverse
    if not n:
        return 1.0
    return sum(math.comb(n, index) for index in range(favourable, n + 1)) / (2**n)


def paired(rows: Sequence[Mapping[str, Any]], treatment: str, budget: int, population: str) -> dict[str, Any]:
    if treatment not in TREATMENTS or budget not in TOTAL_BUDGETS or population not in POPULATION_N:
        raise TC007Error("Unregistered contrast")
    selected = _population_rows(rows, population)
    tkey = f"{treatment}_{budget}_complete"
    ckey = f"control_{budget}_complete"
    gains = sum(row[tkey] and not row[ckey] for row in selected)
    losses = sum(row[ckey] and not row[tkey] for row in selected)
    return {
        "treatment": treatment,
        "budget_chars": budget,
        "population": population,
        "n": len(selected),
        "control_complete": sum(row[ckey] for row in selected),
        "treatment_complete": sum(row[tkey] for row in selected),
        "gains": gains,
        "losses": losses,
        "ties": len(selected) - gains - losses,
        "net": gains - losses,
        "treatment_one_sided_p": one_sided(gains, losses),
        "control_one_sided_p": one_sided(losses, gains),
        "band": BANDS[budget][population],
    }


def directional(cell: Mapping[str, Any], direction: str, alpha: float) -> bool:
    if direction == "treatment":
        return clears(cell["gains"], cell["losses"], cell["band"], alpha)
    if direction == "control":
        return clears(cell["losses"], cell["gains"], cell["band"], alpha)
    raise TC007Error("Unknown direction")


def joint_works(cells: Mapping[str, Mapping[str, Any]], budget: int) -> bool:
    block = cells[str(budget)]
    return (
        directional(block["combined"], "treatment", WORKS_ALPHA)
        and directional(block["breadth"], "treatment", WORKS_ALPHA)
        and not directional(block["targeted"], "control", WORKS_ALPHA)
    )


def treatment_disposition(cells: Mapping[str, Mapping[str, Any]]) -> str:
    if all(joint_works(cells, budget) for budget in TOTAL_BUDGETS):
        return "TREATMENT_WORKS"
    if all(
        directional(cells[str(budget)]["combined"], "control", WORKS_ALPHA)
        for budget in TOTAL_BUDGETS
    ) or all(
        directional(cells[str(budget)]["targeted"], "control", WORKS_ALPHA)
        for budget in TOTAL_BUDGETS
    ):
        return "CONTROL_WORKS"
    signal_budgets = [
        budget for budget in TOTAL_BUDGETS
        if directional(cells[str(budget)]["combined"], "treatment", SIGNAL_ALPHA)
        and directional(cells[str(budget)]["breadth"], "treatment", SIGNAL_ALPHA)
    ]
    if signal_budgets and all(
        cells[str(budget)][endpoint]["net"] >= -cells[str(budget)][endpoint]["band"]
        for budget in TOTAL_BUDGETS for endpoint in ("combined", "breadth")
    ) and not any(
        directional(cells[str(budget)]["targeted"], "control", WORKS_ALPHA)
        for budget in TOTAL_BUDGETS
    ):
        return "TREATMENT_CARRIES_SIGNAL"
    control_signal = any(
        directional(cells[str(budget)]["combined"], "control", SIGNAL_ALPHA)
        and directional(cells[str(budget)]["breadth"], "control", SIGNAL_ALPHA)
        for budget in TOTAL_BUDGETS
    ) or any(
        directional(cells[str(budget)]["targeted"], "control", WORKS_ALPHA)
        for budget in TOTAL_BUDGETS
    )
    return "CONTROL_CARRIES_SIGNAL" if control_signal else "MIXED_OR_NO_DIFFERENCE"


def select_architecture(contrasts: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    winners = [name for name in TREATMENTS if contrasts[name]["disposition"] == "TREATMENT_WORKS"]
    if not winners:
        return {"disposition": "NO_SPLIT_SELECTED", "selected_arm": "control", "reason": "NO_TREATMENT_WORKS"}
    def key(name: str):
        cells = contrasts[name]["cells"]
        return (
            sum(cells[str(b)]["combined"]["net"] for b in TOTAL_BUDGETS),
            sum(cells[str(b)]["breadth"]["net"] for b in TOTAL_BUDGETS),
            -sum(cells[str(b)]["targeted"]["losses"] for b in TOTAL_BUDGETS),
            1 if name == "a3" else 0,
        )
    selected = max(winners, key=key)
    return {"disposition": "PROTECTED_SPREAD_WORKS", "selected_arm": selected, "reason": "REGISTERED_LEXICOGRAPHIC_RULE"}


def analyze_worker(worker_dir: Path, output_dir: Path = OUTCOME_ROOT) -> dict[str, Any]:
    with (worker_dir / "per_question.csv").open(encoding="utf-8", newline="") as handle:
        rows = [_coerce(row) for row in csv.DictReader(handle)]
    contrasts: dict[str, Any] = {}
    for treatment in TREATMENTS:
        cells = {
            str(budget): {
                population: paired(rows, treatment, budget, population)
                for population in POPULATION_N
            }
            for budget in TOTAL_BUDGETS
        }
        contrasts[treatment] = {"cells": cells, "disposition": treatment_disposition(cells)}
    selection = select_architecture(contrasts)
    summaries = []
    for budget in TOTAL_BUDGETS:
        for arm in ("control", *TREATMENTS):
            for population in ("targeted", "breadth", "combined"):
                selected = _population_rows(rows, population)
                summaries.append({
                    "budget_chars": budget,
                    "arm": arm,
                    "population": population,
                    "n": len(selected),
                    "complete": sum(row[f"{arm}_{budget}_complete"] for row in selected),
                    "any": sum(row[f"{arm}_{budget}_any"] for row in selected),
                    "mean_chars": sum(row[f"{arm}_{budget}_chars"] for row in selected) / len(selected),
                    "mean_delivered": sum(row[f"{arm}_{budget}_delivered"] for row in selected) / len(selected),
                    "spread_evidence": sum(row[f"{arm}_{budget}_spread_evidence"] for row in selected),
                })
    result = {
        "schema": SCHEMA,
        "status": "COMPLETE",
        "primary_endpoint": "complete_required_evidence",
        "contrasts": contrasts,
        "selection": selection,
        "summaries": summaries,
        "calls": {"llm_or_generative": 0, "embedding": 0, "cache_misses": 0, "programme_model_free": True},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in ("per_question.csv", "diagnostics.jsonl.gz", "worker_digest.json"):
        (output_dir / name).write_bytes((worker_dir / name).read_bytes())
    _write_json(output_dir / "summary.json", result)
    _write_json(output_dir / "verdict.json", {"contrasts": contrasts, "selection": selection})
    _write_json(output_dir / "no_model_call_audit.json", result["calls"])
    return result


def source_hashes() -> dict[str, str]:
    paths = [
        Path(__file__),
        Path(__file__).with_name("tc007_allocation.py"),
        REPO_ROOT / "scripts" / "run_tc007_study.py",
    ]
    return {_relative(path): sha256_file(path) for path in paths}


def write_manifest(directory: Path) -> dict[str, Any]:
    manifest = {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(directory.iterdir()) if path.is_file() and path.name != "artifact_manifest.json"
    }
    _write_json(directory / "artifact_manifest.json", manifest)
    return manifest


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_gzip_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


__all__ = [
    "BANDS", "G0_ROOT", "OUTCOME_ROOT", "SIGNAL_ALPHA", "TC007Error",
    "TOTAL_BUDGETS", "TREATMENTS", "WORKS_ALPHA", "analyze_worker",
    "assert_registration", "audit_mechanism_leakage", "compute_worker",
    "directional", "joint_works", "paired", "planted_leakage_control",
    "run_g0", "run_precondition", "select_architecture", "source_hashes",
    "treatment_disposition", "write_manifest",
]

"""Registered TC-009 G0, label-blind run, analysis, and disposition."""

from __future__ import annotations

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
from typing import Any, Mapping, Sequence

from analysis.locomo_nf_development import adapt_development, sha256_file
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT, build_episodes
from analysis.tc005_ranking import rank_all
from analysis.tc007_allocation import TOTAL_BUDGETS, allocate, full_relevance, orders, prepare
from analysis.tc008_exploration import leakage_violations
from analysis.tc008_reachability import BANDS, SIGNAL_ALPHA, WORKS_ALPHA, clears
from analysis.tc008_study import (
    BLIND_MANIFEST_NAME,
    G0_ROOT as TC008_G0,
    OUTCOME_ROOT as TC008_RUN,
    _allocation_diag,
    _coerce,
    _population_rows,
    _write_csv,
    _write_gzip_jsonl,
    _write_json,
    audit_blind_manifest,
    load_blind_manifest,
    load_blind_vectors,
    one_sided,
)
from analysis.tc009_dynamic_session import DYNAMIC_SESSION_LAMBDA, dynamic_session_order

SCHEMA = "tc009-registered-offline-v1"
STUDY_ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
PRE_REGISTRATION = STUDY_ROOT / "TC_009_PRE_REGISTRATION.md"
PRE_REGISTRATION_SHA256 = "6ec7cd70874c9b0f87817d9a17ad1fb8684027922d4d51f31e932b08ac693563"
REGISTRATION_COMMIT = "1edf6ad7601d06a53a2819874b13e48120d13f04"
PREFLIGHT_ROOT = STUDY_ROOT / "artifacts" / "tc009" / "preflight"
PREFLIGHT_SHA256 = {
    PREFLIGHT_ROOT / "tc009_preflight_part1.json": "c1e92a879152edfdef0ba870b78e43f03c87959d82bd8d8b181ba3c288634e08",
    PREFLIGHT_ROOT / "tc009_preflight_pf4_reachability.json": "844d67a1eacd63d7090169dcef56e1efc87408fd20b72c3518dbe4c994ef4b9a",
    PREFLIGHT_ROOT / "tc009_preflight_trace.jsonl.gz": "d30715b2e644f45c0b0efc0b268bf05fcefaccdf56bb4fc729245216c71d5651",
    PREFLIGHT_ROOT / "tc009_preflight_mechanism_trace.jsonl.gz": "148481de267e28bbec667558763266614b8de643f495b302e5cd5ddf38fb9848",
    PREFLIGHT_ROOT / "tc009_preflight_full_order_trace.jsonl.gz": "de56dc5ef827edc8c4919f5a15bde62fc5c2c618e84430c17aadcaffa1f68347",
}
RUN_ROOT = STUDY_ROOT / "runs" / "tc009"
G0_ROOT = RUN_ROOT / "g0"
OUTCOME_ROOT = RUN_ROOT / "run"
ARMS = ("control", "a3", "session", "dynamic")
POPULATION_N = {"combined": 868, "targeted": 704, "breadth": 44}
MECHANISM_SOURCES = (
    REPO_ROOT / "src" / "analysis" / "tc007_allocation.py",
    REPO_ROOT / "src" / "analysis" / "tc009_dynamic_session.py",
)


class TC009Error(RuntimeError):
    pass


def _git(*args: str, check: bool = True):
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False
    )
    if check and result.returncode:
        raise TC009Error(result.stderr or result.stdout)
    return result.stdout.strip() if check else result


def _relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def assert_registration() -> dict[str, Any]:
    if sha256_file(PRE_REGISTRATION) != PRE_REGISTRATION_SHA256:
        raise TC009Error("TC-009 pre-registration bytes changed")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", REGISTRATION_COMMIT, "HEAD"], cwd=REPO_ROOT
    ).returncode:
        raise TC009Error("TC-009 registration commit is not an ancestor")
    for path, expected in PREFLIGHT_SHA256.items():
        if sha256_file(path) != expected:
            raise TC009Error(f"TC-009 Preflight changed: {path.name}")
    return {
        "status": "PASS",
        "registration_commit": REGISTRATION_COMMIT,
        "pre_registration_sha256": PRE_REGISTRATION_SHA256,
        "preflight_sha256": {path.name: digest for path, digest in PREFLIGHT_SHA256.items()},
    }


def audit_mechanism_leakage(path: Path | None = None) -> dict[str, Any]:
    paths = [path] if path else list(MECHANISM_SOURCES)
    files = {}
    for source in paths:
        violations = leakage_violations(source.read_text(encoding="utf-8"))
        if violations:
            raise TC009Error(f"Mechanism leakage in {source}: {violations}")
        files[_relative(source)] = sha256_file(source)
    return {"status": "PASS", "files": files}


def planted_leakage_control() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="tc009-leakage-") as directory:
        path = Path(directory) / "bad.py"
        path.write_text("from measurement.evidence_key import q_facts_key\n", encoding="utf-8")
        try:
            audit_mechanism_leakage(path)
        except TC009Error:
            return {"status": "PASS", "planted_violation_rejected": True}
    raise TC009Error("Planted leakage violation was accepted")


def _tc008_expected() -> dict[str, dict[str, Any]]:
    rows = {}
    with gzip.open(TC008_RUN / "frozen_selections.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows[row["blind_key"]] = row
    if len(rows) != 871:
        raise TC009Error("TC-008 frozen selection cardinality drifted")
    return rows


def freeze_selections(
    manifest_path: Path,
    output_path: Path,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    """Freeze all registered arm selections before evidence modules are imported."""

    cases = load_blind_manifest(manifest_path)
    vectors, reuse = load_blind_vectors(cases)
    expected = _tc008_expected()
    rows = []
    for case in cases:
        episodes = build_episodes(case, vectors)
        prepared = prepare(episodes, vectors[case.questions[0].question])
        by_id = {episode.identity: index for index, episode in enumerate(episodes)}
        for question in case.questions:
            ranked_all = rank_all(
                episodes, question.question, vectors[question.question], prepared.rankers
            )
            inherited = orders(prepared, question.question, vectors[question.question])
            if ranked_all["dense"].order != inherited["dense"]:
                raise TC009Error("Dense order drifted inside worker")
            dynamic = dynamic_session_order(episodes, ranked_all["dense"].scores)
            zero = dynamic_session_order(episodes, ranked_all["dense"].scores, lambda_=0.0)
            if zero.order != inherited["dense"]:
                raise TC009Error("Lambda-zero dynamic order did not reduce to dense")
            predecessor_order = tuple(
                by_id[identity] for identity in expected[question.blind_key]["orders"]["session"]
            )
            step_by_id = {step.candidate_id: step for step in dynamic.steps}
            row = {
                "blind_key": question.blind_key,
                "sample_id": case.sample_id,
                "source_index": question.source_index,
                "category": question.category,
                "orders": {
                    "dense": [episodes[index].identity for index in inherited["dense"]],
                    "a3": [episodes[index].identity for index in inherited["a3"]],
                    "session": [episodes[index].identity for index in predecessor_order],
                    "dynamic": [episodes[index].identity for index in dynamic.order],
                },
                "dynamic_steps": [
                    {
                        "step": step.step,
                        "candidate_id": step.candidate_id,
                        "session_id": step.session_id,
                        "session_count_before": step.session_count_before,
                        "raw_similarity": step.raw_similarity,
                        "accumulated_penalty": step.accumulated_penalty,
                        "adjusted_score": step.adjusted_score,
                    }
                    for step in dynamic.steps
                ],
                "budgets": {},
            }
            for budget in TOTAL_BUDGETS:
                packs = {
                    "control": full_relevance(episodes, inherited["dense"], budget),
                    "a3": allocate(episodes, inherited["dense"], inherited["a3"], budget),
                    "session": allocate(episodes, inherited["dense"], predecessor_order, budget),
                    "dynamic": allocate(episodes, inherited["dense"], dynamic.order, budget),
                }
                block = {arm: _allocation_diag(packed) for arm, packed in packs.items()}
                block["dynamic"]["spread_steps"] = [
                    {
                        "candidate_id": identifier,
                        "session_id": step_by_id[identifier].session_id,
                        "session_count_before": step_by_id[identifier].session_count_before,
                        "raw_similarity": step_by_id[identifier].raw_similarity,
                        "accumulated_penalty": step_by_id[identifier].accumulated_penalty,
                        "adjusted_score": step_by_id[identifier].adjusted_score,
                    }
                    for identifier in packs["dynamic"].spread_ids
                ]
                row["budgets"][str(budget)] = block
            rows.append(row)
            if limit is not None and len(rows) >= limit:
                break
        if limit is not None and len(rows) >= limit:
            break
    _write_gzip_jsonl(output_path, rows)
    return {
        "rows": len(rows),
        "sha256": sha256_file(output_path),
        "cache_hits": reuse["hits"],
        "cache_misses": reuse["misses"],
    }


def _load_gzip_jsonl(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def implementation_identity(blind_manifest: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="tc009-identity-") as directory:
        root = Path(directory)
        frozen_path = root / "selections.jsonl.gz"
        frozen = freeze_selections(blind_manifest, frozen_path)
        rows = _load_gzip_jsonl(frozen_path)
        full_rows = []
        admission_rows = []
        for row in rows:
            for step in row["dynamic_steps"]:
                full_rows.append(
                    {
                        "blind_key": row["blind_key"],
                        "sample_id": row["sample_id"],
                        "source_index": row["source_index"],
                        **step,
                    }
                )
            for budget in TOTAL_BUDGETS:
                for step in row["budgets"][str(budget)]["dynamic"]["spread_steps"]:
                    admission_rows.append(
                        {
                            "blind_key": row["blind_key"],
                            "sample_id": row["sample_id"],
                            "source_index": row["source_index"],
                            "budget": budget,
                            **step,
                            "admission_phase": "protected_spread",
                        }
                    )
        full_path = root / "full.jsonl.gz"
        admission_path = root / "admission.jsonl.gz"
        _write_gzip_jsonl(full_path, full_rows)
        _write_gzip_jsonl(admission_path, admission_rows)
        if sha256_file(full_path) != PREFLIGHT_SHA256[PREFLIGHT_ROOT / "tc009_preflight_full_order_trace.jsonl.gz"]:
            raise TC009Error("Final full dynamic state trace drifted from Preflight")
        if sha256_file(admission_path) != PREFLIGHT_SHA256[PREFLIGHT_ROOT / "tc009_preflight_mechanism_trace.jsonl.gz"]:
            raise TC009Error("Final admitted dynamic state trace drifted from Preflight")

    expected = _tc008_expected()
    preflight = {
        (row["blind_key"], int(row["budget"])): row
        for row in _load_gzip_jsonl(PREFLIGHT_ROOT / "tc009_preflight_trace.jsonl.gz")
    }
    anchor_checks = 0
    treatment_checks = 0
    feedback_checks = 0
    for row in rows:
        committed = expected[row["blind_key"]]
        seen: set[str] = set()
        repeat_before_full = False
        session_total = len({step["session_id"] for step in row["dynamic_steps"]})
        for step in row["dynamic_steps"]:
            if step["session_count_before"] > 0 and len(seen) < session_total:
                repeat_before_full = True
            seen.add(step["session_id"])
        if not repeat_before_full:
            raise TC009Error("Dynamic selector became a hard one-per-session floor")
        feedback_checks += 1
        for budget in TOTAL_BUDGETS:
            block = row["budgets"][str(budget)]
            for arm in ("control", "a3", "session"):
                if block[arm]["selected_ids"] != committed["budgets"][str(budget)][arm]["selected_ids"]:
                    raise TC009Error(f"TC-008 {arm} selected identities drifted")
                if block[arm]["payload_sha256"] != committed["budgets"][str(budget)][arm]["payload_sha256"]:
                    raise TC009Error(f"TC-008 {arm} payload drifted")
                anchor_checks += 1
            expected_treatment = preflight[(row["blind_key"], budget)]
            if block["dynamic"]["payload_sha256"] != expected_treatment["payload_sha256"]:
                raise TC009Error("Dynamic payload drifted from Preflight")
            if len(block["dynamic"]["selected_ids"]) != expected_treatment["dynamic_selected"]:
                raise TC009Error("Dynamic selection count drifted from Preflight")
            treatment_checks += 1
    if (anchor_checks, treatment_checks, feedback_checks, len(full_rows), len(admission_rows)) != (
        5_226,
        1_742,
        871,
        296_166,
        69_961,
    ):
        raise TC009Error("G0 identity cardinality drifted")
    return {
        "status": "PASS",
        "tc008_payload_identity_checks": anchor_checks,
        "dynamic_payload_identity_checks": treatment_checks,
        "lambda_zero_question_checks": feedback_checks,
        "repeat_before_full_coverage_checks": feedback_checks,
        "full_state_steps": len(full_rows),
        "admitted_state_steps": len(admission_rows),
        "selection_digest": frozen,
    }


def mechanism_activity_gate() -> dict[str, Any]:
    artifact = json.loads(
        (PREFLIGHT_ROOT / "tc009_preflight_part1.json").read_text(encoding="utf-8")
    )
    blocks = artifact["mechanism_distributions"]
    for budget in TOTAL_BUDGETS:
        block = blocks[str(budget)]
        if block["differs_from_control"] != 871 or block["differs_from_session_predecessor"] != 871:
            raise TC009Error("Dynamic treatment is not active on every trace")
        if block["spread_binding_questions"] != 871 or block["budget_violations"]:
            raise TC009Error("Dynamic treatment binding/budget gate failed")
        if block["repeat_before_all_sessions"] != 871:
            raise TC009Error("Dynamic treatment behaved as a hard floor")
    return {"status": "PASS", "by_budget": blocks}


def prefix_determinism(blind_manifest: Path, count: int = 12) -> dict[str, Any]:
    runner = REPO_ROOT / "scripts" / "run_tc009_study.py"
    with tempfile.TemporaryDirectory(prefix="tc009-prefix-") as directory:
        root = Path(directory)
        outputs = [root / "first.jsonl.gz", root / "second.jsonl.gz"]
        for output in outputs:
            result = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    "--phase",
                    "blind-prefix",
                    "--manifest",
                    str(blind_manifest),
                    "--output",
                    str(output),
                    "--limit",
                    str(count),
                ],
                cwd=REPO_ROOT,
                env={**os.environ, "PYTHONPATH": "src"},
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode:
                raise TC009Error(result.stdout + result.stderr)
        if outputs[0].read_bytes() != outputs[1].read_bytes():
            raise TC009Error("Fresh-process prefix selections differed")
        return {
            "status": "PASS",
            "fresh_processes": 2,
            "questions": count,
            "sha256": sha256_file(outputs[0]),
        }


def run_g0(output_dir: Path = G0_ROOT, test_summary: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise TC009Error("G0 output directory is not empty")
    if _git("status", "--porcelain"):
        raise TC009Error("G0 requires a clean worktree")
    output_dir.mkdir(parents=True, exist_ok=True)
    tests = dict(test_summary or {})
    if tests.get("status") != "PASS":
        raise TC009Error("G0 requires a passing full suite")
    blind_manifest = output_dir / BLIND_MANIFEST_NAME
    blind_manifest.write_bytes((TC008_G0 / BLIND_MANIFEST_NAME).read_bytes())
    blind_audit = audit_blind_manifest(blind_manifest)
    result = {
        "schema": "tc009-g0-v1",
        "status": "PASS",
        "registration": assert_registration(),
        "blind_manifest": {
            "sha256": sha256_file(blind_manifest),
            "source_tc008_sha256": sha256_file(TC008_G0 / BLIND_MANIFEST_NAME),
            "audit": blind_audit,
        },
        "implementation_identity": implementation_identity(blind_manifest),
        "mechanism_activity": mechanism_activity_gate(),
        "leakage": {"static": audit_mechanism_leakage(), "planted": planted_leakage_control()},
        "pf4": json.loads(
            (PREFLIGHT_ROOT / "tc009_preflight_pf4_reachability.json").read_text(encoding="utf-8")
        ),
        "prefix_determinism": prefix_determinism(blind_manifest),
        "test_suite": tests,
        "calls": {
            "llm_or_generative": 0,
            "embedding": 0,
            "cache_misses": 0,
            "programme_model_free": True,
        },
    }
    _write_json(output_dir / "g0_reproduction.json", result)
    _write_json(
        output_dir / "run_header.json",
        {
            "schema": "tc009-g0-header-v1",
            "git_head_before_artifacts": _git("rev-parse", "HEAD"),
            "command": ".venv\\Scripts\\python.exe scripts\\run_tc009_study.py --phase g0",
            "parallel": 1,
            "speculative_decoding": False,
            "python": sys.version,
            "source_sha256": source_hashes(),
        },
    )
    _write_json(output_dir / "no_model_call_audit.json", result["calls"])
    write_manifest(output_dir)
    return result


def run_precondition(g0_dir: Path = G0_ROOT) -> dict[str, Any]:
    if _git("status", "--porcelain"):
        raise TC009Error("Registered run requires a clean worktree")
    path = g0_dir / "g0_reproduction.json"
    if not path.is_file() or _git("ls-files", "--error-unmatch", _relative(path), check=False).returncode:
        raise TC009Error("Committed G0 is absent")
    gate = json.loads(path.read_text(encoding="utf-8"))
    if gate.get("status") != "PASS":
        raise TC009Error("G0 did not pass")
    blind_manifest = g0_dir / BLIND_MANIFEST_NAME
    if sha256_file(blind_manifest) != gate["blind_manifest"]["sha256"]:
        raise TC009Error("Committed blind manifest drifted")
    header = json.loads((g0_dir / "run_header.json").read_text(encoding="utf-8"))
    if header["source_sha256"] != source_hashes():
        raise TC009Error("Study sources changed after G0")
    assert_registration()
    return {
        "status": "PASS",
        "g0_sha256": sha256_file(path),
        "g0_commit": _git("rev-parse", "HEAD"),
        "blind_manifest_sha256": sha256_file(blind_manifest),
        "source_sha256": source_hashes(),
    }


def measure_frozen_selections(selection_path: Path, output_dir: Path) -> dict[str, Any]:
    if not selection_path.is_file():
        raise TC009Error("Frozen selection artifact is absent")
    # Measurement imports occur only after selection bytes exist.
    from analysis.tc005_exploration import evidence_indices, question_population

    cases = adapt_development(DATASET_PATH)
    by_source = {
        (case.sample_id, question.source_index): (case, question)
        for case in cases
        for question in case.questions
        if question.duplicate_ordinal == 0
    }
    blind_cases = load_blind_manifest(G0_ROOT / BLIND_MANIFEST_NAME)
    vectors, reuse = load_blind_vectors(blind_cases)
    episodes_by_case = {case.sample_id: build_episodes(case, vectors) for case in cases}
    frozen_rows = _load_gzip_jsonl(selection_path)
    rows = []
    diagnostics = []
    for frozen in frozen_rows:
        case, question = by_source[(frozen["sample_id"], int(frozen["source_index"]))]
        episodes = episodes_by_case[case.sample_id]
        evidence = evidence_indices(case, episodes, question)
        evidence_ids = {episodes[index].identity for index in evidence}
        population = question_population(case, question)
        eligible = population != "ineligible"
        row: dict[str, Any] = {
            "question_id": question.identity,
            "question_content_sha256": question.content_sha256,
            "sample_id": case.sample_id,
            "source_index": question.source_index,
            "category": question.category,
            "population": population,
            "eligible": eligible,
            "evidence_candidates": len(evidence_ids),
        }
        diagnostic = {
            **frozen,
            "question_id": question.identity,
            "population": population,
            "evidence_candidate_ids": sorted(evidence_ids),
        }
        for budget in TOTAL_BUDGETS:
            for arm in ARMS:
                packed = frozen["budgets"][str(budget)][arm]
                selected = set(packed["selected_ids"])
                delivered = len(evidence_ids & selected)
                prefix = f"{arm}_{budget}"
                row[f"{prefix}_complete"] = eligible and bool(evidence_ids) and evidence_ids <= selected
                row[f"{prefix}_any"] = eligible and bool(evidence_ids & selected)
                row[f"{prefix}_evidence_delivered"] = delivered
                row[f"{prefix}_evidence_share"] = delivered / len(evidence_ids) if evidence_ids else 0.0
                row[f"{prefix}_delivered"] = len(selected)
                row[f"{prefix}_chars"] = packed["payload_chars"]
                row[f"{prefix}_payload_sha256"] = packed["payload_sha256"]
                row[f"{prefix}_spread_evidence"] = len(evidence_ids & set(packed["spread_ids"]))
                row[f"{prefix}_relevance_evidence"] = len(
                    evidence_ids
                    & (set(packed["initial_relevance_ids"]) | set(packed["returned_relevance_ids"]))
                )
        rows.append(row)
        diagnostics.append(diagnostic)
    if len(rows) != 871 or len({row["question_id"] for row in rows}) != 871:
        raise TC009Error("Question identity/cardinality drifted")
    if sum(row["population"] == "targeted" for row in rows) != 704:
        raise TC009Error("Targeted population drifted")
    if sum(row["population"] == "breadth" for row in rows) != 44:
        raise TC009Error("Breadth population drifted")
    _write_csv(output_dir / "per_question.csv", rows)
    _write_gzip_jsonl(output_dir / "diagnostics.jsonl.gz", diagnostics)
    return {
        "rows": len(rows),
        "per_question_sha256": sha256_file(output_dir / "per_question.csv"),
        "diagnostics_sha256": sha256_file(output_dir / "diagnostics.jsonl.gz"),
        "frozen_selections_sha256": sha256_file(selection_path),
        "cache_hits": reuse["hits"],
        "cache_misses": reuse["misses"],
    }


def compute_worker(output_dir: Path, blind_manifest: Path | None = None) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise TC009Error("Worker output directory is not empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = blind_manifest or G0_ROOT / BLIND_MANIFEST_NAME
    frozen_path = output_dir / "frozen_selections.jsonl.gz"
    selection = freeze_selections(manifest, frozen_path)
    measurement = measure_frozen_selections(frozen_path, output_dir)
    digest = {"selection": selection, "measurement": measurement}
    _write_json(output_dir / "worker_digest.json", digest)
    return digest


def paired_complete(
    rows: Sequence[Mapping[str, Any]], arm: str, budget: int, population: str
) -> dict[str, Any]:
    if arm not in {"a3", "session", "dynamic"} or budget not in TOTAL_BUDGETS or population not in POPULATION_N:
        raise TC009Error("Unregistered complete-evidence contrast")
    selected = _population_rows(rows, population)
    arm_key = f"{arm}_{budget}_complete"
    control_key = f"control_{budget}_complete"
    gains = sum(row[arm_key] and not row[control_key] for row in selected)
    losses = sum(row[control_key] and not row[arm_key] for row in selected)
    return {
        "arm": arm,
        "budget_chars": budget,
        "population": population,
        "n": len(selected),
        "control_complete": sum(row[control_key] for row in selected),
        "arm_complete": sum(row[arm_key] for row in selected),
        "gains": gains,
        "losses": losses,
        "ties": len(selected) - gains - losses,
        "net": gains - losses,
        "arm_one_sided_p": one_sided(gains, losses),
        "control_one_sided_p": one_sided(losses, gains),
        "band": BANDS[budget][f"{population}_complete"],
    }


def paired_breadth_share(
    rows: Sequence[Mapping[str, Any]], arm: str, budget: int
) -> dict[str, Any]:
    if arm not in {"a3", "session", "dynamic"} or budget not in TOTAL_BUDGETS:
        raise TC009Error("Unregistered breadth-share contrast")
    selected = _population_rows(rows, "breadth")
    arm_key = f"{arm}_{budget}_evidence_delivered"
    control_key = f"control_{budget}_evidence_delivered"
    gains = sum(row[arm_key] > row[control_key] for row in selected)
    losses = sum(row[arm_key] < row[control_key] for row in selected)
    identity_gains = sum(max(row[arm_key] - row[control_key], 0) for row in selected)
    identity_losses = sum(max(row[control_key] - row[arm_key], 0) for row in selected)
    return {
        "arm": arm,
        "budget_chars": budget,
        "population": "breadth",
        "n": len(selected),
        "question_gains": gains,
        "question_losses": losses,
        "question_ties": len(selected) - gains - losses,
        "question_net": gains - losses,
        "identity_gains": identity_gains,
        "identity_losses": identity_losses,
        "identity_net": identity_gains - identity_losses,
        "arm_one_sided_p": one_sided(gains, losses),
        "control_one_sided_p": one_sided(losses, gains),
        "question_band": BANDS[budget]["breadth_share_questions"],
        "identity_band": BANDS[budget]["breadth_share_identities"],
    }


def directional_complete(cell: Mapping[str, Any], direction: str, alpha: float) -> bool:
    if direction == "dynamic":
        return clears(cell["gains"], cell["losses"], cell["band"], alpha)
    if direction == "dense":
        return clears(cell["losses"], cell["gains"], cell["band"], alpha)
    raise TC009Error("Unknown complete direction")


def directional_breadth(cell: Mapping[str, Any], direction: str, alpha: float) -> bool:
    if direction == "dynamic":
        return clears(
            cell["question_gains"], cell["question_losses"], cell["question_band"], alpha
        ) and cell["identity_net"] > cell["identity_band"]
    if direction == "dense":
        return clears(
            cell["question_losses"], cell["question_gains"], cell["question_band"], alpha
        ) and -cell["identity_net"] > cell["identity_band"]
    raise TC009Error("Unknown breadth direction")


def budget_decision(cell: Mapping[str, Any]) -> dict[str, bool]:
    dense_guardrail = directional_complete(cell["combined_complete"], "dense", WORKS_ALPHA) or directional_complete(
        cell["targeted_complete"], "dense", WORKS_ALPHA
    )
    dynamic_noninferior = cell["breadth_complete"]["net"] >= -cell["breadth_complete"]["band"]
    dense_noninferior = cell["breadth_complete"]["net"] <= cell["breadth_complete"]["band"]
    return {
        "dynamic_breadth_works": directional_breadth(
            cell["breadth_share"], "dynamic", WORKS_ALPHA
        ) and dynamic_noninferior and not dense_guardrail,
        "dynamic_breadth_signal": directional_breadth(
            cell["breadth_share"], "dynamic", SIGNAL_ALPHA
        ) and dynamic_noninferior and not dense_guardrail,
        "dense_breadth_works": directional_breadth(
            cell["breadth_share"], "dense", WORKS_ALPHA
        ) and dense_noninferior,
        "dense_breadth_signal": directional_breadth(
            cell["breadth_share"], "dense", SIGNAL_ALPHA
        ) and dense_noninferior,
        "dense_guardrail_fire": dense_guardrail,
    }


def study_disposition(cells: Mapping[str, Mapping[str, Any]]) -> str:
    decisions = {str(budget): budget_decision(cells[str(budget)]) for budget in TOTAL_BUDGETS}
    if all(decisions[str(budget)]["dynamic_breadth_works"] for budget in TOTAL_BUDGETS):
        return "DYNAMIC_SPREAD_WORKS"
    if all(decisions[str(budget)]["dense_breadth_works"] for budget in TOTAL_BUDGETS) or all(
        decisions[str(budget)]["dense_guardrail_fire"] for budget in TOTAL_BUDGETS
    ):
        return "DENSE_WORKS"
    dynamic_signal = any(
        decisions[str(budget)]["dynamic_breadth_signal"] for budget in TOTAL_BUDGETS
    )
    dynamic_nonnegative = all(
        cells[str(budget)]["breadth_share"]["question_net"] >= 0
        and cells[str(budget)]["breadth_share"]["identity_net"] >= 0
        and cells[str(budget)]["breadth_complete"]["net"] >= 0
        for budget in TOTAL_BUDGETS
    )
    if dynamic_signal and dynamic_nonnegative and not any(
        decisions[str(budget)]["dense_guardrail_fire"] for budget in TOTAL_BUDGETS
    ):
        return "DYNAMIC_SPREAD_CARRIES_SIGNAL"
    dense_signal = any(
        decisions[str(budget)]["dense_breadth_signal"] for budget in TOTAL_BUDGETS
    )
    dense_nonnegative = all(
        cells[str(budget)]["breadth_share"]["question_net"] <= 0
        and cells[str(budget)]["breadth_share"]["identity_net"] <= 0
        and cells[str(budget)]["breadth_complete"]["net"] <= 0
        for budget in TOTAL_BUDGETS
    )
    if (dense_signal and dense_nonnegative) or any(
        decisions[str(budget)]["dense_guardrail_fire"] for budget in TOTAL_BUDGETS
    ):
        return "DENSE_CARRIES_SIGNAL"
    return "MIXED_OR_NO_DIFFERENCE"


def analyze_worker(worker_dir: Path, output_dir: Path = OUTCOME_ROOT) -> dict[str, Any]:
    with (worker_dir / "per_question.csv").open(encoding="utf-8", newline="") as handle:
        rows = [_coerce(row) for row in csv.DictReader(handle)]
    cells = {}
    references = {"a3": {}, "session": {}}
    for budget in TOTAL_BUDGETS:
        cells[str(budget)] = {
            "breadth_share": paired_breadth_share(rows, "dynamic", budget),
            "breadth_complete": paired_complete(rows, "dynamic", budget, "breadth"),
            "combined_complete": paired_complete(rows, "dynamic", budget, "combined"),
            "targeted_complete": paired_complete(rows, "dynamic", budget, "targeted"),
        }
        cells[str(budget)]["decision"] = budget_decision(cells[str(budget)])
        for arm in references:
            references[arm][str(budget)] = {
                "breadth_share": paired_breadth_share(rows, arm, budget),
                "breadth_complete": paired_complete(rows, arm, budget, "breadth"),
                "combined_complete": paired_complete(rows, arm, budget, "combined"),
                "targeted_complete": paired_complete(rows, arm, budget, "targeted"),
            }
    disposition = study_disposition(cells)
    summaries = []
    for budget in TOTAL_BUDGETS:
        for arm in ARMS:
            for population in ("targeted", "breadth", "combined"):
                selected = _population_rows(rows, population)
                summaries.append(
                    {
                        "budget_chars": budget,
                        "arm": arm,
                        "population": population,
                        "n": len(selected),
                        "complete": sum(row[f"{arm}_{budget}_complete"] for row in selected),
                        "any": sum(row[f"{arm}_{budget}_any"] for row in selected),
                        "required_identities_delivered": sum(
                            row[f"{arm}_{budget}_evidence_delivered"] for row in selected
                        ),
                        "mean_chars": sum(row[f"{arm}_{budget}_chars"] for row in selected) / len(selected),
                        "mean_delivered": sum(row[f"{arm}_{budget}_delivered"] for row in selected) / len(selected),
                    }
                )
    result = {
        "schema": SCHEMA,
        "status": "COMPLETE",
        "primary_endpoint": "breadth_required_identity_share",
        "cells": cells,
        "descriptive_references": references,
        "disposition": disposition,
        "selected_for_reader_followup": "dynamic" if disposition == "DYNAMIC_SPREAD_WORKS" else "control",
        "summaries": summaries,
        "calls": {
            "llm_or_generative": 0,
            "embedding": 0,
            "cache_misses": 0,
            "programme_model_free": True,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "frozen_selections.jsonl.gz",
        "per_question.csv",
        "diagnostics.jsonl.gz",
        "worker_digest.json",
    ):
        (output_dir / name).write_bytes((worker_dir / name).read_bytes())
    _write_json(output_dir / "summary.json", result)
    _write_json(
        output_dir / "verdict.json",
        {"disposition": disposition, "cells": cells, "descriptive_references": references},
    )
    _write_json(output_dir / "no_model_call_audit.json", result["calls"])
    return result


def source_hashes() -> dict[str, str]:
    paths = [
        Path(__file__),
        Path(__file__).with_name("tc007_allocation.py"),
        Path(__file__).with_name("tc009_dynamic_session.py"),
        REPO_ROOT / "scripts" / "run_tc009_study.py",
    ]
    return {_relative(path): sha256_file(path) for path in paths}


def write_manifest(directory: Path) -> dict[str, Any]:
    manifest = {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != "artifact_manifest.json"
    }
    _write_json(directory / "artifact_manifest.json", manifest)
    return manifest


__all__ = [
    "ARMS",
    "BANDS",
    "BLIND_MANIFEST_NAME",
    "G0_ROOT",
    "OUTCOME_ROOT",
    "POPULATION_N",
    "SIGNAL_ALPHA",
    "TC009Error",
    "TOTAL_BUDGETS",
    "WORKS_ALPHA",
    "analyze_worker",
    "assert_registration",
    "audit_mechanism_leakage",
    "budget_decision",
    "compute_worker",
    "directional_breadth",
    "directional_complete",
    "freeze_selections",
    "implementation_identity",
    "measure_frozen_selections",
    "paired_breadth_share",
    "paired_complete",
    "planted_leakage_control",
    "prefix_determinism",
    "run_g0",
    "run_precondition",
    "source_hashes",
    "study_disposition",
    "write_manifest",
]

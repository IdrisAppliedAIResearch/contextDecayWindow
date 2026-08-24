"""Registered TC-008 G0, label-blind selection, measurement, and disposition."""

from __future__ import annotations

import ast
import csv
import gzip
import hashlib
import io
import json
import math
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from analysis.locomo_nf_development import adapt_development, sha256_file
from analysis.tc001_exploration import (
    CACHE_PATH,
    DATASET_PATH,
    REPO_ROOT,
    VECTOR_MANIFEST,
    build_episodes,
)
from analysis.tc007_allocation import TOTAL_BUDGETS, allocate, full_relevance, orders, prepare
from analysis.tc008_reachability import BANDS, SIGNAL_ALPHA, WORKS_ALPHA, clears
from analysis.tc008_session_spread import SESSION_LAMBDA, session_spread_order
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256

SCHEMA = "tc008-registered-offline-v1"
STUDY_ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
PRE_REGISTRATION = STUDY_ROOT / "TC_008_PRE_REGISTRATION.md"
PRE_REGISTRATION_SHA256 = "b40714d4557f7b8510970542856154d920e9f5e1a0f88a4b578c0ee4a9203fbd"
REGISTRATION_COMMIT = "a78bbae30455b1d299547dd96d414c03b9098f53"
PREFLIGHT_ROOT = STUDY_ROOT / "artifacts" / "tc008" / "preflight"
PREFLIGHT_SHA256 = {
    PREFLIGHT_ROOT / "tc008_preflight_part1.json": "dab50e1a3935d63755824c8d7ea9f7bb9f57263422338f227eeea44ca6a0f971",
    PREFLIGHT_ROOT / "tc008_preflight_pf4_reachability.json": "b3de97b6ad905c0a9311f0dae2a03f407003f50139ff5594d0422f0ac7b79711",
    PREFLIGHT_ROOT / "tc008_preflight_trace.jsonl.gz": "d678d873f9a939b0265c4b7ed1875ce81627531b7eadc2e008468af21208d27b",
    PREFLIGHT_ROOT / "tc008_preflight_mechanism_trace.jsonl.gz": "2ac5f84c84284ee75bc1cd3b4d3bf4645947979f623006be6beb75f5db7066dd",
}
TC007_RUN = STUDY_ROOT / "runs" / "tc007" / "run"
RUN_ROOT = STUDY_ROOT / "runs" / "tc008"
G0_ROOT = RUN_ROOT / "g0"
OUTCOME_ROOT = RUN_ROOT / "run"
BLIND_MANIFEST_NAME = "label_blind_selection_manifest.json.gz"
ARMS = ("control", "a3", "session")
POPULATION_N = {"combined": 868, "targeted": 704, "breadth": 44}
_FORBIDDEN = ("q_facts_key", "rubric", "expected_answer", "answer_key", "resolved_evidence")
_BLIND_FORBIDDEN_KEYS = {"answer", "evidence", "resolved_evidence_ids", "evidence_ids", "unresolved_evidence_ids"}


class TC008Error(RuntimeError):
    pass


@dataclass(frozen=True)
class BlindQuestion:
    blind_key: str
    sample_id: str
    source_index: int
    category: str
    question: str


@dataclass(frozen=True)
class BlindCase:
    sample_id: str
    pairs: tuple[Any, ...]
    questions: tuple[BlindQuestion, ...]


def _git(*args: str, check: bool = True):
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False
    )
    if check and result.returncode:
        raise TC008Error(result.stderr or result.stdout)
    return result.stdout.strip() if check else result


def _relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def _blind_key(sample_id: str, source_index: int, category: str, question: str) -> str:
    text = "\0".join((sample_id, str(source_index), category, question))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def assert_registration() -> dict[str, Any]:
    if sha256_file(PRE_REGISTRATION) != PRE_REGISTRATION_SHA256:
        raise TC008Error("TC-008 pre-registration bytes changed")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", REGISTRATION_COMMIT, "HEAD"], cwd=REPO_ROOT
    ).returncode:
        raise TC008Error("TC-008 registration commit is not an ancestor")
    for path, expected in PREFLIGHT_SHA256.items():
        if sha256_file(path) != expected:
            raise TC008Error(f"TC-008 Preflight changed: {path.name}")
    return {
        "status": "PASS",
        "registration_commit": REGISTRATION_COMMIT,
        "pre_registration_sha256": PRE_REGISTRATION_SHA256,
        "preflight_sha256": {path.name: digest for path, digest in PREFLIGHT_SHA256.items()},
    }


def audit_mechanism_leakage(path: Path | None = None) -> dict[str, Any]:
    paths = [path] if path else [
        Path(__file__).with_name("tc007_allocation.py"),
        Path(__file__).with_name("tc008_session_spread.py"),
        REPO_ROOT / "episodic" / "src" / "episodic" / "_selection.py",
    ]
    violations: list[str] = []
    imports: set[str] = set()
    for source in paths:
        text = source.read_text(encoding="utf-8")
        lowered = text.casefold()
        violations.extend(f"{source.name}:{token}" for token in _FORBIDDEN if token in lowered)
        tree = ast.parse(text, filename=str(source))
        imports.update(node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom))
        imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
    if violations:
        raise TC008Error(f"Mechanism leakage: {violations}")
    return {
        "status": "PASS",
        "files": {_relative(source): sha256_file(source) for source in paths},
        "imports": sorted(imports),
    }


def planted_leakage_control() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="tc008-leakage-") as directory:
        path = Path(directory) / "bad.py"
        path.write_text('KEY = "q_facts_key.md"\n', encoding="utf-8")
        try:
            audit_mechanism_leakage(path)
        except TC008Error:
            return {"status": "PASS", "planted_violation_rejected": True}
    raise TC008Error("Planted leakage violation was accepted")


def create_blind_manifest(cases: Sequence[Any], path: Path) -> dict[str, Any]:
    records = []
    question_count = 0
    for case in cases:
        seen: set[tuple[str, str]] = set()
        questions = []
        for question in case.questions:
            label_blind_duplicate_key = (str(question.question), str(question.category))
            if label_blind_duplicate_key in seen:
                continue
            seen.add(label_blind_duplicate_key)
            questions.append({
                "blind_key": _blind_key(case.sample_id, question.source_index, str(question.category), question.question),
                "source_index": int(question.source_index),
                "category": str(question.category),
                "question": str(question.question),
            })
        question_count += len(questions)
        records.append({
            "sample_id": case.sample_id,
            "pairs": [
                {
                    "identity": pair.identity,
                    "session_id": pair.session_id,
                    "session_order": pair.session_order,
                    "pair_order": pair.pair_order,
                    "text": pair.text,
                    "chars": pair.chars,
                    "dialog_ids": list(pair.dialog_ids),
                }
                for pair in case.pairs
            ],
            "questions": questions,
        })
    payload = {
        "schema": "tc008-label-blind-selection-v1",
        "source_sha256": sha256_file(DATASET_PATH),
        "cases": records,
    }
    if question_count != 871:
        raise TC008Error("Label-blind question cardinality drifted")
    _write_gzip_json(path, payload)
    audit_blind_manifest(path)
    return {"cases": len(records), "questions": question_count, "sha256": sha256_file(path)}


def audit_blind_manifest(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    seen_keys: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            seen_keys.update(str(key).casefold() for key in value)
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(payload)
    forbidden = sorted(seen_keys & _BLIND_FORBIDDEN_KEYS)
    if forbidden:
        raise TC008Error(f"Label-blind manifest contains measurement keys: {forbidden}")
    return {"status": "PASS", "forbidden_keys": forbidden, "keys": sorted(seen_keys)}


def load_blind_manifest(path: Path) -> tuple[BlindCase, ...]:
    audit_blind_manifest(path)
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schema") != "tc008-label-blind-selection-v1":
        raise TC008Error("Unknown label-blind manifest schema")
    cases = []
    for row in payload["cases"]:
        pairs = tuple(
            SimpleNamespace(
                identity=pair["identity"],
                sample_id=row["sample_id"],
                session_id=pair["session_id"],
                session_order=int(pair["session_order"]),
                pair_order=int(pair["pair_order"]),
                text=pair["text"],
                chars=int(pair["chars"]),
                dialog_ids=tuple(pair["dialog_ids"]),
            )
            for pair in row["pairs"]
        )
        questions = tuple(
            BlindQuestion(
                blind_key=question["blind_key"],
                sample_id=row["sample_id"],
                source_index=int(question["source_index"]),
                category=str(question["category"]),
                question=question["question"],
            )
            for question in row["questions"]
        )
        cases.append(BlindCase(row["sample_id"], pairs, questions))
    if sum(len(case.questions) for case in cases) != 871:
        raise TC008Error("Blind manifest cardinality drifted")
    return tuple(cases)


def load_blind_vectors(cases: Sequence[BlindCase]) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    with EmbeddingCache(
        CACHE_PATH,
        mode="reuse",
        expected_file_sha256=manifest["cache"]["file_sha256"],
        expected_content_sha256=manifest["cache"]["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDER_SHA256,
    ) as cache:
        vectors = {
            text: np.asarray(cache(text), dtype=np.float32)
            for case in cases
            for text in (
                *(pair.text for pair in case.pairs),
                *(question.question for question in case.questions),
            )
        }
        reuse = cache.record()
    if reuse["misses"]:
        raise TC008Error("Registered LoCoMo cache missed")
    return vectors, reuse


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


def freeze_selections(
    manifest_path: Path,
    output_path: Path,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    """Serialize all arm selections before any evidence module is imported."""

    cases = load_blind_manifest(manifest_path)
    vectors, reuse = load_blind_vectors(cases)
    rows: list[dict[str, Any]] = []
    for case in cases:
        episodes = build_episodes(case, vectors)
        prepared = prepare(episodes, vectors[case.questions[0].question])
        session_by_id = {episode.identity: str(episode.pair.session_id) for episode in episodes}
        for question in case.questions:
            ranked = orders(prepared, question.question, vectors[question.question])
            session = session_spread_order(episodes, vectors[question.question])
            step_by_id = {step.candidate_id: step for step in session.result.steps}
            row = {
                "blind_key": question.blind_key,
                "sample_id": case.sample_id,
                "source_index": question.source_index,
                "category": question.category,
                "orders": {
                    "dense": [episodes[index].identity for index in ranked["dense"]],
                    "a3": [episodes[index].identity for index in ranked["a3"]],
                    "session": [episodes[index].identity for index in session.order],
                },
                "budgets": {},
            }
            for budget in TOTAL_BUDGETS:
                packs = {
                    "control": full_relevance(episodes, ranked["dense"], budget),
                    "a3": allocate(episodes, ranked["dense"], ranked["a3"], budget),
                    "session": allocate(episodes, ranked["dense"], session.order, budget),
                }
                block = {arm: _allocation_diag(packed) for arm, packed in packs.items()}
                block["session"]["selected_sessions"] = sorted(
                    {session_by_id[identifier] for identifier in packs["session"].selected_ids}
                )
                block["session"]["spread_steps"] = [
                    {
                        "candidate_id": identifier,
                        "session_id": session_by_id[identifier],
                        "relevance": step_by_id[identifier].relevance,
                        "novelty_bonus": round(
                            step_by_id[identifier].objective_gain
                            - max(step_by_id[identifier].relevance, 0.0),
                            10,
                        ),
                        "objective_gain": step_by_id[identifier].objective_gain,
                    }
                    for identifier in packs["session"].spread_ids
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


def _load_jsonl_gzip(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def implementation_identity(blind_manifest: Path) -> dict[str, Any]:
    if sha256_file(TC007_RUN / "diagnostics.jsonl.gz") != "660ae5531277030a3c806668135415971a9038c17bb4737cbd7f69b315c626a3":
        raise TC008Error("TC-007 diagnostic anchor drifted")
    with tempfile.TemporaryDirectory(prefix="tc008-identity-") as directory:
        frozen_path = Path(directory) / "selections.jsonl.gz"
        frozen = freeze_selections(blind_manifest, frozen_path)
        rows = _load_jsonl_gzip(frozen_path)

    cases = adapt_development(DATASET_PATH)
    identity_by_source = {
        (case.sample_id, question.source_index): question.identity
        for case in cases
        for question in case.questions
        if question.duplicate_ordinal == 0
    }
    tc007 = {}
    with gzip.open(TC007_RUN / "diagnostics.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            tc007[row["question_id"]] = row
    preflight = {
        (row["question_id"], int(row["budget"])): row
        for row in _load_jsonl_gzip(PREFLIGHT_ROOT / "tc008_preflight_trace.jsonl.gz")
    }
    mechanism = {
        (row["question_id"], int(row["budget"]), row["candidate_id"]): row
        for row in _load_jsonl_gzip(PREFLIGHT_ROOT / "tc008_preflight_mechanism_trace.jsonl.gz")
    }
    anchor_checks = 0
    treatment_checks = 0
    mechanism_checks = 0
    for row in rows:
        question_id = identity_by_source[(row["sample_id"], int(row["source_index"]))]
        expected_tc007 = tc007[question_id]
        for budget in TOTAL_BUDGETS:
            block = row["budgets"][str(budget)]
            for arm in ("control", "a3"):
                expected = expected_tc007["budgets"][str(budget)][arm]
                observed = block[arm]
                if observed["selected_ids"] != expected["selected_ids"]:
                    raise TC008Error(f"TC-007 {arm} selected identities drifted")
                if observed["payload_sha256"] != expected["payload_sha256"]:
                    raise TC008Error(f"TC-007 {arm} payload drifted")
                anchor_checks += 1
            expected_treatment = preflight[(question_id, budget)]
            observed_treatment = block["session"]
            if observed_treatment["payload_sha256"] != expected_treatment["payload_sha256"]:
                raise TC008Error("Session payload drifted from Preflight")
            if len(observed_treatment["selected_ids"]) != expected_treatment["session_selected"]:
                raise TC008Error("Session selection cardinality drifted from Preflight")
            treatment_checks += 1
            for step in observed_treatment["spread_steps"]:
                expected_step = mechanism[(question_id, budget, step["candidate_id"])]
                for key in ("session_id", "relevance", "novelty_bonus", "objective_gain"):
                    if step[key] != expected_step[key]:
                        raise TC008Error(f"Session mechanism trace drifted: {key}")
                mechanism_checks += 1
    if (anchor_checks, treatment_checks, mechanism_checks) != (3_484, 1_742, 70_736):
        raise TC008Error("Implementation identity cardinality drifted")
    return {
        "status": "PASS",
        "tc007_payload_identity_checks": anchor_checks,
        "session_payload_identity_checks": treatment_checks,
        "mechanism_step_checks": mechanism_checks,
        "selection_digest": frozen,
    }


def mechanism_activity_gate() -> dict[str, Any]:
    artifact = json.loads(
        (PREFLIGHT_ROOT / "tc008_preflight_part1.json").read_text(encoding="utf-8")
    )
    budgets = artifact["mechanism_distributions"]
    for budget in TOTAL_BUDGETS:
        block = budgets[str(budget)]
        if block["differs_from_control"] != 871 or block["differs_from_a3"] != 871:
            raise TC008Error("Session treatment was not active on every real trace")
        if block["spread_binding_questions"] != 871 or block["budget_violations"]:
            raise TC008Error("Session treatment activity/budget gate failed")
    return {
        "status": "PASS",
        "by_budget": {
            str(budget): {
                "differs_from_control": budgets[str(budget)]["differs_from_control"],
                "differs_from_a3": budgets[str(budget)]["differs_from_a3"],
                "spread_binding_questions": budgets[str(budget)]["spread_binding_questions"],
                "budget_violations": budgets[str(budget)]["budget_violations"],
            }
            for budget in TOTAL_BUDGETS
        },
    }


def prefix_determinism(blind_manifest: Path, count: int = 12) -> dict[str, Any]:
    runner = REPO_ROOT / "scripts" / "run_tc008_study.py"
    with tempfile.TemporaryDirectory(prefix="tc008-prefix-") as directory:
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
                raise TC008Error(result.stdout + result.stderr)
        if outputs[0].read_bytes() != outputs[1].read_bytes():
            raise TC008Error("Fresh-process prefix selections differed")
        return {
            "status": "PASS",
            "fresh_processes": 2,
            "questions": count,
            "sha256": sha256_file(outputs[0]),
        }


def run_g0(output_dir: Path = G0_ROOT, test_summary: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise TC008Error("G0 output directory is not empty")
    if _git("status", "--porcelain"):
        raise TC008Error("G0 requires a clean worktree")
    output_dir.mkdir(parents=True, exist_ok=True)
    registration = assert_registration()
    tests = dict(test_summary or {})
    if tests.get("status") != "PASS":
        raise TC008Error("G0 requires a passing full suite")
    cases = adapt_development(DATASET_PATH)
    blind_manifest = output_dir / BLIND_MANIFEST_NAME
    blind = create_blind_manifest(cases, blind_manifest)
    result = {
        "schema": "tc008-g0-v1",
        "status": "PASS",
        "registration": registration,
        "blind_manifest": {**blind, "audit": audit_blind_manifest(blind_manifest)},
        "implementation_identity": implementation_identity(blind_manifest),
        "mechanism_activity": mechanism_activity_gate(),
        "leakage": {"static": audit_mechanism_leakage(), "planted": planted_leakage_control()},
        "pf4": json.loads(
            (PREFLIGHT_ROOT / "tc008_preflight_pf4_reachability.json").read_text(encoding="utf-8")
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
            "schema": "tc008-g0-header-v1",
            "git_head_before_artifacts": _git("rev-parse", "HEAD"),
            "command": ".venv\\Scripts\\python.exe scripts\\run_tc008_study.py --phase g0",
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
        raise TC008Error("Registered run requires a clean worktree")
    path = g0_dir / "g0_reproduction.json"
    if not path.is_file() or _git("ls-files", "--error-unmatch", _relative(path), check=False).returncode:
        raise TC008Error("Committed G0 is absent")
    gate = json.loads(path.read_text(encoding="utf-8"))
    if gate.get("status") != "PASS":
        raise TC008Error("G0 did not pass")
    blind_manifest = g0_dir / BLIND_MANIFEST_NAME
    if sha256_file(blind_manifest) != gate["blind_manifest"]["sha256"]:
        raise TC008Error("Committed label-blind manifest drifted")
    header = json.loads((g0_dir / "run_header.json").read_text(encoding="utf-8"))
    if header["source_sha256"] != source_hashes():
        raise TC008Error("Study sources changed after G0")
    assert_registration()
    return {
        "status": "PASS",
        "g0_sha256": sha256_file(path),
        "g0_commit": _git("rev-parse", "HEAD"),
        "blind_manifest_sha256": sha256_file(blind_manifest),
        "source_sha256": source_hashes(),
    }


def measure_frozen_selections(selection_path: Path, output_dir: Path) -> dict[str, Any]:
    """Join evidence only after the label-blind selection file already exists."""

    if not selection_path.is_file():
        raise TC008Error("Frozen selection artifact is absent")
    # Deliberately local: selection has completed and its bytes are frozen.
    from analysis.tc005_exploration import evidence_indices, question_population

    cases = adapt_development(DATASET_PATH)
    by_source = {
        (case.sample_id, question.source_index): (case, question)
        for case in cases
        for question in case.questions
        if question.duplicate_ordinal == 0
    }
    vectors, reuse = load_blind_vectors(load_blind_manifest(G0_ROOT / BLIND_MANIFEST_NAME))
    episodes_by_case = {case.sample_id: build_episodes(case, vectors) for case in cases}
    frozen_rows = _load_jsonl_gzip(selection_path)
    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
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
        raise TC008Error("Question identity/cardinality drifted")
    if sum(row["population"] == "targeted" for row in rows) != 704:
        raise TC008Error("Targeted population drifted")
    if sum(row["population"] == "breadth" for row in rows) != 44:
        raise TC008Error("Breadth population drifted")
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
        raise TC008Error("Worker output directory is not empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = blind_manifest or G0_ROOT / BLIND_MANIFEST_NAME
    frozen_path = output_dir / "frozen_selections.jsonl.gz"
    selection = freeze_selections(manifest, frozen_path)
    measurement = measure_frozen_selections(frozen_path, output_dir)
    digest = {"selection": selection, "measurement": measurement}
    _write_json(output_dir / "worker_digest.json", digest)
    return digest


def _coerce(row: Mapping[str, str]) -> dict[str, Any]:
    output: dict[str, Any] = dict(row)
    for key, value in list(output.items()):
        if key == "eligible" or key.endswith(("_complete", "_any")):
            output[key] = value == "True"
        elif key in {"source_index", "evidence_candidates"} or key.endswith(
            ("_delivered", "_chars", "_evidence")
        ):
            output[key] = int(value)
        elif key.endswith("_evidence_share"):
            output[key] = float(value)
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


def paired_complete(
    rows: Sequence[Mapping[str, Any]], arm: str, budget: int, population: str
) -> dict[str, Any]:
    if arm not in {"a3", "session"} or budget not in TOTAL_BUDGETS or population not in POPULATION_N:
        raise TC008Error("Unregistered complete-evidence contrast")
    selected = _population_rows(rows, population)
    treatment_key = f"{arm}_{budget}_complete"
    control_key = f"control_{budget}_complete"
    gains = sum(row[treatment_key] and not row[control_key] for row in selected)
    losses = sum(row[control_key] and not row[treatment_key] for row in selected)
    return {
        "arm": arm,
        "budget_chars": budget,
        "population": population,
        "n": len(selected),
        "control_complete": sum(row[control_key] for row in selected),
        "arm_complete": sum(row[treatment_key] for row in selected),
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
    if arm not in {"a3", "session"} or budget not in TOTAL_BUDGETS:
        raise TC008Error("Unregistered breadth-share contrast")
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
    if direction == "session":
        return clears(cell["gains"], cell["losses"], cell["band"], alpha)
    if direction == "dense":
        return clears(cell["losses"], cell["gains"], cell["band"], alpha)
    raise TC008Error("Unknown complete-evidence direction")


def directional_breadth(cell: Mapping[str, Any], direction: str, alpha: float) -> bool:
    if direction == "session":
        return clears(
            cell["question_gains"], cell["question_losses"], cell["question_band"], alpha
        ) and cell["identity_net"] > cell["identity_band"]
    if direction == "dense":
        return clears(
            cell["question_losses"], cell["question_gains"], cell["question_band"], alpha
        ) and -cell["identity_net"] > cell["identity_band"]
    raise TC008Error("Unknown breadth direction")


def budget_decision(cell: Mapping[str, Any]) -> dict[str, bool]:
    breadth_share = cell["breadth_share"]
    breadth_complete = cell["breadth_complete"]
    dense_guardrail = directional_complete(cell["combined_complete"], "dense", WORKS_ALPHA) or directional_complete(
        cell["targeted_complete"], "dense", WORKS_ALPHA
    )
    session_noninferior = breadth_complete["net"] >= -breadth_complete["band"]
    dense_noninferior = breadth_complete["net"] <= breadth_complete["band"]
    return {
        "session_breadth_works": directional_breadth(
            breadth_share, "session", WORKS_ALPHA
        ) and session_noninferior and not dense_guardrail,
        "session_breadth_signal": directional_breadth(
            breadth_share, "session", SIGNAL_ALPHA
        ) and session_noninferior and not dense_guardrail,
        "dense_breadth_works": directional_breadth(
            breadth_share, "dense", WORKS_ALPHA
        ) and dense_noninferior,
        "dense_breadth_signal": directional_breadth(
            breadth_share, "dense", SIGNAL_ALPHA
        ) and dense_noninferior,
        "dense_guardrail_fire": dense_guardrail,
    }


def study_disposition(cells: Mapping[str, Mapping[str, Any]]) -> str:
    decisions = {str(budget): budget_decision(cells[str(budget)]) for budget in TOTAL_BUDGETS}
    if all(decisions[str(budget)]["session_breadth_works"] for budget in TOTAL_BUDGETS):
        return "SESSION_SPREAD_WORKS"
    if all(decisions[str(budget)]["dense_breadth_works"] for budget in TOTAL_BUDGETS) or all(
        decisions[str(budget)]["dense_guardrail_fire"] for budget in TOTAL_BUDGETS
    ):
        return "DENSE_WORKS"
    session_signal = any(
        decisions[str(budget)]["session_breadth_signal"] for budget in TOTAL_BUDGETS
    )
    session_other_nonnegative = all(
        cells[str(budget)]["breadth_share"]["question_net"] >= 0
        and cells[str(budget)]["breadth_share"]["identity_net"] >= 0
        and cells[str(budget)]["breadth_complete"]["net"] >= 0
        for budget in TOTAL_BUDGETS
    )
    if session_signal and session_other_nonnegative and not any(
        decisions[str(budget)]["dense_guardrail_fire"] for budget in TOTAL_BUDGETS
    ):
        return "SESSION_SPREAD_CARRIES_SIGNAL"
    dense_signal = any(
        decisions[str(budget)]["dense_breadth_signal"] for budget in TOTAL_BUDGETS
    )
    dense_other_nonnegative = all(
        cells[str(budget)]["breadth_share"]["question_net"] <= 0
        and cells[str(budget)]["breadth_share"]["identity_net"] <= 0
        and cells[str(budget)]["breadth_complete"]["net"] <= 0
        for budget in TOTAL_BUDGETS
    )
    if (dense_signal and dense_other_nonnegative) or any(
        decisions[str(budget)]["dense_guardrail_fire"] for budget in TOTAL_BUDGETS
    ):
        return "DENSE_CARRIES_SIGNAL"
    return "MIXED_OR_NO_DIFFERENCE"


def analyze_worker(worker_dir: Path, output_dir: Path = OUTCOME_ROOT) -> dict[str, Any]:
    with (worker_dir / "per_question.csv").open(encoding="utf-8", newline="") as handle:
        rows = [_coerce(row) for row in csv.DictReader(handle)]
    cells = {}
    a3_reference = {}
    for budget in TOTAL_BUDGETS:
        cells[str(budget)] = {
            "breadth_share": paired_breadth_share(rows, "session", budget),
            "breadth_complete": paired_complete(rows, "session", budget, "breadth"),
            "combined_complete": paired_complete(rows, "session", budget, "combined"),
            "targeted_complete": paired_complete(rows, "session", budget, "targeted"),
        }
        cells[str(budget)]["decision"] = budget_decision(cells[str(budget)])
        a3_reference[str(budget)] = {
            "breadth_share": paired_breadth_share(rows, "a3", budget),
            "breadth_complete": paired_complete(rows, "a3", budget, "breadth"),
            "combined_complete": paired_complete(rows, "a3", budget, "combined"),
            "targeted_complete": paired_complete(rows, "a3", budget, "targeted"),
        }
    disposition = study_disposition(cells)
    summaries = []
    for budget in TOTAL_BUDGETS:
        for arm in ARMS:
            for population in ("targeted", "breadth", "combined"):
                selected = _population_rows(rows, population)
                summaries.append({
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
                })
    result = {
        "schema": SCHEMA,
        "status": "COMPLETE",
        "primary_endpoint": "breadth_required_identity_share",
        "cells": cells,
        "a3_descriptive_reference": a3_reference,
        "disposition": disposition,
        "selected_for_reader_followup": "session" if disposition == "SESSION_SPREAD_WORKS" else "control",
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
        {"disposition": disposition, "cells": cells, "a3_descriptive_reference": a3_reference},
    )
    _write_json(output_dir / "no_model_call_audit.json", result["calls"])
    attribution = _attribution(rows)
    _write_json(output_dir / "attribution.json", attribution)
    return result


def _attribution(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {"schema": "tc008-attribution-v1", "budgets": {}}
    for budget in TOTAL_BUDGETS:
        breadth = _population_rows(rows, "breadth")
        session_gain_ids = [
            row["question_id"]
            for row in breadth
            if row[f"session_{budget}_evidence_delivered"] > row[f"control_{budget}_evidence_delivered"]
        ]
        session_loss_ids = [
            row["question_id"]
            for row in breadth
            if row[f"session_{budget}_evidence_delivered"] < row[f"control_{budget}_evidence_delivered"]
        ]
        unique_vs_a3 = [
            row["question_id"]
            for row in breadth
            if row["question_id"] in session_gain_ids
            and row[f"a3_{budget}_evidence_delivered"] <= row[f"control_{budget}_evidence_delivered"]
        ]
        targeted = _population_rows(rows, "targeted")
        output["budgets"][str(budget)] = {
            "breadth_share_gain_question_ids": session_gain_ids,
            "breadth_share_loss_question_ids": session_loss_ids,
            "session_unique_gain_vs_a3_question_ids": unique_vs_a3,
            "breadth_category_gain_counts": {
                category: sum(row["category"] == category and row["question_id"] in session_gain_ids for row in breadth)
                for category in sorted({row["category"] for row in breadth})
            },
            "targeted_complete_loss_question_ids": [
                row["question_id"]
                for row in targeted
                if row[f"control_{budget}_complete"] and not row[f"session_{budget}_complete"]
            ],
        }
    return output


def source_hashes() -> dict[str, str]:
    paths = [
        Path(__file__),
        Path(__file__).with_name("tc007_allocation.py"),
        Path(__file__).with_name("tc008_session_spread.py"),
        REPO_ROOT / "scripts" / "run_tc008_study.py",
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


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_gzip_json(path: Path, value: Any) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as handle:
                json.dump(value, handle, sort_keys=True, separators=(",", ":"))
                handle.write("\n")


def _write_gzip_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as handle:
                for row in rows:
                    handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


__all__ = [
    "ARMS",
    "BANDS",
    "BLIND_MANIFEST_NAME",
    "G0_ROOT",
    "OUTCOME_ROOT",
    "POPULATION_N",
    "SIGNAL_ALPHA",
    "TC008Error",
    "TOTAL_BUDGETS",
    "WORKS_ALPHA",
    "analyze_worker",
    "assert_registration",
    "audit_blind_manifest",
    "audit_mechanism_leakage",
    "budget_decision",
    "compute_worker",
    "create_blind_manifest",
    "directional_breadth",
    "directional_complete",
    "freeze_selections",
    "measure_frozen_selections",
    "mechanism_activity_gate",
    "one_sided",
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

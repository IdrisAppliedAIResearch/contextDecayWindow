"""Registered TC-005 G0, offline run, and frozen disposition logic."""

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
from pathlib import Path
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
from analysis.tc005_exploration import (
    evidence_indices,
    pack_order,
    question_population,
    reproduce_bakeoff,
    reproduce_tc001_dense,
    surface_class,
)
from analysis.tc005_ranking import (
    ARMS,
    inverse_rank,
    prepare_rankers,
    rank_all,
    ranking_digest,
)
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256

SCHEMA = "tc005-registered-offline-v1"
PRE_REGISTRATION = (
    REPO_ROOT / "experiments" / "components" / "tier_cost" / "TC_005_PRE_REGISTRATION.md"
)
PRE_REGISTRATION_SHA256 = "1b112802cdee5890e6e652039ac1afbf76908425417848f04f6d9ae86e35a170"
REGISTRATION_COMMIT = "024e231f3def3e7c058a2a54ffcf74afde3c3dcc"
PREFLIGHT_PART1 = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "tier_cost"
    / "artifacts"
    / "tc005"
    / "preflight"
    / "tc005_preflight_part1.json"
)
PREFLIGHT_PF4 = PREFLIGHT_PART1.with_name("tc005_preflight_pf4_reachability.json")
PREFLIGHT_SHA256 = {
    PREFLIGHT_PART1: "2687d48812d8862f7c0ff2ebe5abe6bd8011f136deb38efaacf34958296ba584",
    PREFLIGHT_PF4: "c44a96b52ec796f06a9507b31b987d6bb1f9d17976f8134823a485d707c67b4d",
}
RUN_ROOT = (
    REPO_ROOT / "experiments" / "components" / "tier_cost" / "runs" / "tc005"
)
G0_ROOT = RUN_ROOT / "g0"
OUTCOME_ROOT = RUN_ROOT / "run"
BUDGETS = (8_000, 16_000, 32_000)
PRIMARY_BUDGETS = (8_000, 16_000)
FULL_BUDGETS = (16_000, 32_000)
NULL_BAND = {8_000: 1, 16_000: 2, 32_000: 0}
WORKS_ALPHA = 0.01 / 8
SIGNAL_ALPHA = 0.10 / 8
TARGETED_N = 704
ELIGIBLE_N = 868
_FORBIDDEN_MECHANISM_TOKENS = (
    "q_facts_key",
    "rubric",
    "expected_answer",
    "answer_key",
    "resolved_evidence",
)


class TC005Error(RuntimeError):
    pass


def assert_registration() -> dict[str, Any]:
    actual = sha256_file(PRE_REGISTRATION)
    if actual != PRE_REGISTRATION_SHA256:
        raise TC005Error("TC-005 pre-registration bytes changed")
    if not _git_is_ancestor(REGISTRATION_COMMIT, "HEAD"):
        raise TC005Error("TC-005 registration commit is not an ancestor of HEAD")
    for path, expected in PREFLIGHT_SHA256.items():
        if sha256_file(path) != expected:
            raise TC005Error(f"Preflight artifact changed: {path.name}")
    return {
        "status": "PASS",
        "pre_registration_sha256": actual,
        "registration_commit": REGISTRATION_COMMIT,
        "preflight_sha256": {path.name: expected for path, expected in PREFLIGHT_SHA256.items()},
    }


def audit_mechanism_leakage(path: Path | None = None) -> dict[str, Any]:
    mechanism = path or Path(__file__).with_name("tc005_ranking.py")
    audit_paths = [mechanism]
    if path is None:
        audit_paths.extend(
            REPO_ROOT / "src" / "retrieval_bakeoff" / name
            for name in (
                "methods.py",
                "config.py",
                "classifier.py",
                "embedding.py",
                "models.py",
            )
        )
    violations: list[str] = []
    imports: set[str] = set()
    for audit_path in audit_paths:
        text = audit_path.read_text(encoding="utf-8")
        lowered = text.casefold()
        violations.extend(
            f"{audit_path.name}:{token}"
            for token in _FORBIDDEN_MECHANISM_TOKENS
            if token in lowered
        )
        tree = ast.parse(text, filename=str(audit_path))
        imports.update(
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        imports.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
    if violations:
        raise TC005Error(f"Mechanism leakage tokens found: {violations}")
    return {
        "status": "PASS",
        "path": _relative(mechanism),
        "sha256": sha256_file(mechanism),
        "audited_files": {
            _relative(audit_path): sha256_file(audit_path) for audit_path in audit_paths
        },
        "imports": sorted(imports),
        "forbidden_tokens": list(_FORBIDDEN_MECHANISM_TOKENS),
    }


def planted_leakage_control() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="tc005-leakage-") as directory:
        path = Path(directory) / "bad_ranker.py"
        path.write_text('KEY = "q_facts_key.md"\n', encoding="utf-8")
        try:
            audit_mechanism_leakage(path)
        except TC005Error:
            return {"status": "PASS", "planted_violation_rejected": True}
    raise TC005Error("Planted leakage violation did not fail")


def load_inputs() -> tuple[Any, dict[str, np.ndarray], dict[str, Any]]:
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    cases = adapt_development(DATASET_PATH)
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
        raise TC005Error("Registered LoCoMo cache missed")
    return cases, vectors, reuse


def implementation_identity() -> dict[str, Any]:
    """New label-blind module must match committed Preflight orders exactly."""

    from analysis.tc005_exploration import prepare_rankers as old_prepare
    from analysis.tc005_exploration import rank_all as old_rank

    cases, vectors, reuse = load_inputs()
    checks = 0
    digests: list[str] = []
    for case in cases:
        episodes = build_episodes(case, vectors)
        prepared = prepare_rankers(episodes)
        previous = old_prepare(episodes)
        for question in case.questions:
            if question.duplicate_ordinal > 0:
                continue
            new = rank_all(episodes, question.question, vectors[question.question], prepared)
            old = old_rank(episodes, question.question, vectors[question.question], previous)
            for arm in ARMS:
                if new[arm].order != old[arm].order or new[arm].scores != old[arm].scores:
                    raise TC005Error(
                        f"Implementation drifted from Preflight: {question.identity}/{arm}"
                    )
                digests.append(ranking_digest(episodes, new[arm]))
                checks += 1
    return {
        "status": "PASS",
        "question_arm_orders_checked": checks,
        "ranking_digest": _digest(digests),
        "cache_hits": reuse["hits"],
        "cache_misses": reuse["misses"],
    }


def run_g0(output_dir: Path = G0_ROOT, test_summary: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise TC005Error("G0 output directory is not empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    if _git_status():
        raise TC005Error("G0 requires a clean worktree before artifacts are written")
    registration = assert_registration()
    leakage = audit_mechanism_leakage()
    planted = planted_leakage_control()
    identity = implementation_identity()

    cases, vectors, reuse = load_inputs()
    episodes = {case.sample_id: build_episodes(case, vectors) for case in cases}
    tc001 = reproduce_tc001_dense(cases, episodes, vectors)
    bakeoff = reproduce_bakeoff()
    tests = dict(test_summary or {})
    if tests.get("status") != "PASS":
        raise TC005Error("G0 requires a passing full-suite record")

    result = {
        "schema": "tc005-g0-v1",
        "status": "PASS",
        "registration": registration,
        "implementation_identity": identity,
        "tc001_dense_reproduction": tc001,
        "bakeoff_reproduction": bakeoff,
        "leakage": {"static": leakage, "planted": planted},
        "cache": {"hits": reuse["hits"], "misses": reuse["misses"]},
        "test_suite": tests,
        "calls": {
            "llm_or_generative": 0,
            "embedding": bakeoff["embedding_calls"],
            "programme_model_free": True,
        },
    }
    _write_json(output_dir / "g0_reproduction.json", result)
    _write_json(
        output_dir / "run_header.json",
        {
            "schema": "tc005-g0-header-v1",
            "git_head_before_artifacts": _git("rev-parse", "HEAD"),
            "registration_commit": REGISTRATION_COMMIT,
            "command": ".venv\\Scripts\\python.exe scripts\\run_tc005_study.py --phase g0",
            "python": sys.version,
            "threading": _threading(),
            "source_sha256": _source_hashes(),
        },
    )
    _write_json(output_dir / "no_model_call_audit.json", result["calls"])
    write_manifest(output_dir)
    return result


def run_precondition(g0_dir: Path = G0_ROOT) -> dict[str, Any]:
    if _git_status():
        raise TC005Error("Registered run requires a clean worktree")
    path = g0_dir / "g0_reproduction.json"
    if not path.is_file():
        raise TC005Error("Committed G0 artifact is absent")
    if _git("ls-files", "--error-unmatch", _relative(path), check=False).returncode:
        raise TC005Error("G0 artifact is not tracked")
    if _git("cat-file", "-e", f"HEAD:{_relative(path)}", check=False).returncode:
        raise TC005Error("G0 artifact is not committed in HEAD")
    gate = json.loads(path.read_text(encoding="utf-8"))
    if gate.get("status") != "PASS":
        raise TC005Error("G0 did not pass")
    assert_registration()
    current_sources = _source_hashes()
    header = json.loads((g0_dir / "run_header.json").read_text(encoding="utf-8"))
    if current_sources != header["source_sha256"]:
        raise TC005Error("Registered source hashes changed after G0")
    return {
        "status": "PASS",
        "g0_sha256": sha256_file(path),
        "g0_commit": _git("rev-parse", "HEAD"),
        "source_sha256": current_sources,
    }


def compute_worker(output_dir: Path) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise TC005Error("Worker output directory is not empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    cases, vectors, reuse = load_inputs()
    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    for case in cases:
        episodes = build_episodes(case, vectors)
        prepared = prepare_rankers(episodes)
        for question in case.questions:
            if question.duplicate_ordinal > 0:
                continue
            rankings = rank_all(
                episodes, question.question, vectors[question.question], prepared
            )
            evidence = evidence_indices(case, episodes, question)
            evidence_ids = frozenset(episodes[index].identity for index in evidence)
            population = question_population(case, question)
            eligible = population != "ineligible"
            row: dict[str, Any] = {
                "question_id": question.identity,
                "question_content_sha256": question.content_sha256,
                "sample_id": case.sample_id,
                "source_index": question.source_index,
                "category": question.category,
                "population": population,
                "surface_class": surface_class(question.question),
                "eligible": eligible,
                "evidence_candidates": len(evidence_ids),
            }
            diagnostic = {
                "question_id": question.identity,
                "sample_id": case.sample_id,
                "source_index": question.source_index,
                "population": population,
                "surface_class": row["surface_class"],
                "evidence_candidate_ids": sorted(evidence_ids),
                "arms": {},
            }
            for arm in ARMS:
                ranking = rankings[arm]
                inverse = inverse_rank(ranking.order)
                ranks = [inverse[index] for index in evidence]
                arm_diag: dict[str, Any] = {
                    "ranking_sha256": ranking_digest(episodes, ranking),
                    "order": [episodes[index].identity for index in ranking.order],
                    "scores": [ranking.scores[index] for index in ranking.order],
                    "dense_rank_by_order": [ranking.dense_rank[index] for index in ranking.order],
                    "bm25_rank_by_order": [ranking.bm25_rank[index] for index in ranking.order],
                    "budgets": {},
                }
                row[f"{arm}_best_evidence_rank"] = min(ranks) if ranks else ""
                row[f"{arm}_worst_evidence_rank"] = max(ranks) if ranks else ""
                for budget in BUDGETS:
                    packed = pack_order(episodes, ranking.order, budget)
                    selected = frozenset(packed.selected_ids)
                    complete = bool(evidence_ids) and evidence_ids <= selected and eligible
                    any_hit = bool(evidence_ids & selected) and eligible
                    prefix = f"{arm}_{budget}"
                    row[f"{prefix}_complete"] = complete
                    row[f"{prefix}_any"] = any_hit
                    row[f"{prefix}_delivered"] = len(packed.selected_ids)
                    row[f"{prefix}_chars"] = len(packed.payload)
                    row[f"{prefix}_payload_sha256"] = hashlib.sha256(
                        packed.payload.encode("utf-8")
                    ).hexdigest()
                    row[f"{prefix}_ranking_sha256"] = arm_diag["ranking_sha256"]
                    arm_diag["budgets"][str(budget)] = {
                        "selected_ids": list(packed.selected_ids),
                        "skipped_ids": list(packed.skipped_ids),
                        "skip_reason": "overflow",
                        "payload_chars": len(packed.payload),
                        "payload_sha256": row[f"{prefix}_payload_sha256"],
                        "complete": complete,
                        "any": any_hit,
                    }
                    if len(packed.payload) > budget:
                        raise TC005Error("Payload exceeded registered budget")
                diagnostic["arms"][arm] = arm_diag
            rows.append(row)
            diagnostics.append(diagnostic)

    if len(rows) != 871 or len({row["question_id"] for row in rows}) != 871:
        raise TC005Error("Registered question cardinality or identity drifted")
    if sum(row["population"] == "targeted" for row in rows) != TARGETED_N:
        raise TC005Error("Targeted population drifted")
    if sum(bool(row["eligible"]) for row in rows) != ELIGIBLE_N:
        raise TC005Error("Eligible population drifted")

    _write_csv(output_dir / "per_question.csv", rows)
    _write_gzip_jsonl(output_dir / "diagnostics.jsonl.gz", diagnostics)
    digest = {
        "per_question_sha256": sha256_file(output_dir / "per_question.csv"),
        "diagnostics_sha256": sha256_file(output_dir / "diagnostics.jsonl.gz"),
        "rows": len(rows),
        "cache_hits": reuse["hits"],
        "cache_misses": reuse["misses"],
    }
    _write_json(output_dir / "worker_digest.json", digest)
    return digest


def analyze_worker(worker_dir: Path, output_dir: Path = OUTCOME_ROOT) -> dict[str, Any]:
    with (worker_dir / "per_question.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = [_coerce_row(row) for row in csv.DictReader(handle)]
    contrasts: dict[str, Any] = {}
    for treatment in ("bm25", "hybrid"):
        primary = {
            str(budget): paired(rows, treatment, budget, "targeted")
            for budget in PRIMARY_BUDGETS
        }
        guardrails = {
            str(budget): paired(rows, treatment, budget, "eligible")
            for budget in FULL_BUDGETS
        }
        contrasts[treatment] = {
            "primary": primary,
            "guardrails": guardrails,
            "disposition": treatment_disposition(primary, guardrails),
        }
    selection = select_for_tc007(contrasts)
    summaries = summarize(rows)
    result = {
        "schema": SCHEMA,
        "status": "COMPLETE",
        "primary_endpoint": "complete_required_evidence",
        "contrasts": contrasts,
        "selection": selection,
        "summaries": summaries,
        "calls": {
            "llm_or_generative": 0,
            "embedding": 0,
            "cache_misses": 0,
            "programme_model_free": True,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in ("per_question.csv", "diagnostics.jsonl.gz", "worker_digest.json"):
        (output_dir / name).write_bytes((worker_dir / name).read_bytes())
    _write_json(output_dir / "summary.json", result)
    _write_json(output_dir / "verdict.json", {"contrasts": contrasts, "selection": selection})
    _write_json(output_dir / "no_model_call_audit.json", result["calls"])
    return result


def paired(
    rows: Sequence[Mapping[str, Any]], treatment: str, budget: int, population: str
) -> dict[str, Any]:
    if treatment not in {"bm25", "hybrid"} or budget not in BUDGETS:
        raise TC005Error("Unregistered contrast")
    selected = [
        row
        for row in rows
        if (row["population"] == "targeted" if population == "targeted" else row["eligible"])
    ]
    gains = sum(
        bool(row[f"{treatment}_{budget}_complete"])
        and not bool(row[f"dense_{budget}_complete"])
        for row in selected
    )
    losses = sum(
        bool(row[f"dense_{budget}_complete"])
        and not bool(row[f"{treatment}_{budget}_complete"])
        for row in selected
    )
    return {
        "population": population,
        "n": len(selected),
        "budget_chars": budget,
        "treatment": treatment,
        "dense_complete": sum(bool(row[f"dense_{budget}_complete"]) for row in selected),
        "treatment_complete": sum(bool(row[f"{treatment}_{budget}_complete"]) for row in selected),
        "gains": gains,
        "losses": losses,
        "ties": len(selected) - gains - losses,
        "net": gains - losses,
        "treatment_one_sided_p": _one_sided_sign_p(gains, losses),
        "dense_one_sided_p": _one_sided_sign_p(losses, gains),
        "band": NULL_BAND[budget],
    }


def directional_clear(cell: Mapping[str, Any], direction: str, alpha: float) -> bool:
    if direction not in {"treatment", "dense"}:
        raise TC005Error("Unknown direction")
    net = int(cell["net"])
    signed = net if direction == "treatment" else -net
    p = float(cell[f"{direction}_one_sided_p"])
    return signed > int(cell["band"]) and p <= alpha


def _guardrail_fails(cell: Mapping[str, Any]) -> bool:
    return directional_clear(cell, "dense", WORKS_ALPHA)


def treatment_disposition(
    primary: Mapping[str, Mapping[str, Any]],
    guardrails: Mapping[str, Mapping[str, Any]],
) -> str:
    treatment_works = all(
        directional_clear(primary[str(budget)], "treatment", WORKS_ALPHA)
        for budget in PRIMARY_BUDGETS
    )
    guardrail_ok = not any(_guardrail_fails(cell) for cell in guardrails.values())
    if treatment_works and guardrail_ok:
        return "TREATMENT_WORKS"
    if all(
        directional_clear(primary[str(budget)], "dense", WORKS_ALPHA)
        for budget in PRIMARY_BUDGETS
    ):
        return "DENSE_WORKS"
    treatment_signal = any(
        directional_clear(primary[str(budget)], "treatment", SIGNAL_ALPHA)
        for budget in PRIMARY_BUDGETS
    ) and all(
        int(primary[str(budget)]["net"]) >= -NULL_BAND[budget]
        for budget in PRIMARY_BUDGETS
    )
    if treatment_signal and guardrail_ok:
        return "TREATMENT_CARRIES_SIGNAL"
    dense_signal = any(
        directional_clear(primary[str(budget)], "dense", SIGNAL_ALPHA)
        for budget in PRIMARY_BUDGETS
    ) and all(
        -int(primary[str(budget)]["net"]) >= -NULL_BAND[budget]
        for budget in PRIMARY_BUDGETS
    )
    if dense_signal:
        return "DENSE_CARRIES_SIGNAL"
    return "MIXED_OR_NO_DIFFERENCE"


def select_for_tc007(contrasts: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    eligible = [
        treatment
        for treatment in ("bm25", "hybrid")
        if contrasts[treatment]["disposition"] == "TREATMENT_WORKS"
    ]
    if not eligible:
        return {
            "selected_arm": "dense",
            "tc007_name": "A_DENSE",
            "reason": "FROZEN_DENSE_FALLBACK_NO_TREATMENT_WORKS",
        }

    def key(treatment: str) -> tuple[int, int, int, int]:
        cells = contrasts[treatment]["primary"]
        nets = [int(cells[str(budget)]["net"]) for budget in PRIMARY_BUDGETS]
        losses = sum(int(cells[str(budget)]["losses"]) for budget in PRIMARY_BUDGETS)
        return (sum(nets), -losses, min(nets), int(treatment == "hybrid"))

    selected = max(eligible, key=key)
    return {
        "selected_arm": selected,
        "tc007_name": f"A_{selected.upper()}",
        "reason": "REGISTERED_HALF_BUDGET_SELECTION_RULE",
        "selection_key": list(key(selected)),
        "eligible_treatments": eligible,
    }


def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"population_counts": {}}
    for population in ("targeted", "breadth", "other", "ineligible"):
        result["population_counts"][population] = sum(
            row["population"] == population for row in rows
        )
    result["by_budget_arm_population"] = []
    for budget in BUDGETS:
        for arm in ARMS:
            for population in ("targeted", "breadth", "other", "eligible"):
                selected = [
                    row
                    for row in rows
                    if (row["eligible"] if population == "eligible" else row["population"] == population)
                ]
                result["by_budget_arm_population"].append(
                    {
                        "budget_chars": budget,
                        "arm": arm,
                        "population": population,
                        "n": len(selected),
                        "complete": sum(bool(row[f"{arm}_{budget}_complete"]) for row in selected),
                        "any": sum(bool(row[f"{arm}_{budget}_any"]) for row in selected),
                        "mean_chars": (
                            sum(int(row[f"{arm}_{budget}_chars"]) for row in selected) / len(selected)
                            if selected
                            else None
                        ),
                        "mean_delivered": (
                            sum(int(row[f"{arm}_{budget}_delivered"]) for row in selected) / len(selected)
                            if selected
                            else None
                        ),
                    }
                )
    return result


def _one_sided_sign_p(favourable: int, adverse: int) -> float:
    n = favourable + adverse
    if not n or favourable <= adverse:
        return 1.0
    return sum(math.comb(n, k) for k in range(favourable, n + 1)) / (2**n)


def _coerce_row(row: Mapping[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = dict(row)
    for key, value in list(result.items()):
        if key == "eligible" or key.endswith("_complete") or key.endswith("_any"):
            result[key] = value == "True"
        elif key in {"source_index", "evidence_candidates"} or key.endswith(
            ("_delivered", "_chars", "_best_evidence_rank", "_worst_evidence_rank")
        ):
            result[key] = int(value) if value != "" else ""
    return result


def _source_hashes() -> dict[str, str]:
    paths = (
        Path(__file__).resolve(),
        Path(__file__).with_name("tc005_ranking.py"),
        Path(__file__).with_name("tc005_exploration.py"),
        REPO_ROOT / "scripts" / "run_tc005_study.py",
        REPO_ROOT / "src" / "retrieval_bakeoff" / "methods.py",
        REPO_ROOT / "episodic" / "src" / "episodic" / "_packing.py",
        REPO_ROOT / "episodic" / "src" / "episodic" / "_render.py",
    )
    return {_relative(path): sha256_file(path) for path in paths}


def _threading() -> dict[str, str | None]:
    return {
        key: os.environ.get(key)
        for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
    }


def write_manifest(directory: Path) -> dict[str, Any]:
    files = {
        path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != "artifact_manifest.json"
    }
    manifest = {"schema": "tc005-artifact-manifest-v1", "files": files}
    _write_json(directory / "artifact_manifest.json", manifest)
    return manifest


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise TC005Error("Cannot write empty CSV")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_gzip_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as text:
                for row in rows:
                    text.write(json.dumps(row, sort_keys=True, separators=(",", ":")))
                    text.write("\n")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def _git_status() -> str:
    return _git("status", "--porcelain").stdout.strip()


def _git_is_ancestor(ancestor: str, descendant: str) -> bool:
    return _git("merge-base", "--is-ancestor", ancestor, descendant, check=False).returncode == 0


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str] | str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False
    )
    if check and result.returncode:
        raise TC005Error(result.stderr.strip() or result.stdout.strip())
    if args[:2] == ("rev-parse", "HEAD") and check:
        return result.stdout.strip()
    return result


__all__ = [
    "ARMS",
    "BUDGETS",
    "ELIGIBLE_N",
    "NULL_BAND",
    "PRIMARY_BUDGETS",
    "SIGNAL_ALPHA",
    "TARGETED_N",
    "TC005Error",
    "WORKS_ALPHA",
    "analyze_worker",
    "assert_registration",
    "audit_mechanism_leakage",
    "compute_worker",
    "directional_clear",
    "implementation_identity",
    "paired",
    "planted_leakage_control",
    "run_g0",
    "run_precondition",
    "select_for_tc007",
    "summarize",
    "treatment_disposition",
    "write_manifest",
]

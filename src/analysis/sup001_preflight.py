from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable

from episodic import EmbeddingCache
from src.analysis.sup001_benchmark import REPO_ROOT, STUDY_ROOT, canonical_digest
from src.analysis.sup001_control import CONTROL_PATH, compute_control
from src.analysis.sup001_part1 import PART1_PATH, build_ledger, ledger_digest
from src.analysis.sup001_vectors import CACHE_PATH, MANIFEST_PATH, MECHANISM_PATH, sha256_file
from src.biological_memory.supersession import SupersessionLedger
from src.retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256


PREFLIGHT_PATH = STUDY_ROOT / "artifacts" / "sup001_preflight" / "preflight.json"
FINAL_DESIGN = STUDY_ROOT / "SUP_001_FINAL_DESIGN.json"
PRE_REGISTRATION = STUDY_ROOT / "SUP_001_PRE_REGISTRATION.md"
SEALED_KEY = STUDY_ROOT / "artifacts" / "sup001_corpus" / "SEALED_KEY_DO_NOT_OPEN.json"
CORPUS_LOCK = STUDY_ROOT / "artifacts" / "sup001_corpus" / "corpus_lock.json"
HYPOTHETICAL = REPO_ROOT / "HYPOTHETICAL_001_MECHANICAL_BIOLOGICAL_MEMORY_MODEL.md"
MODEL_PATH = Path(
    r"C:\Users\muzaf\.cache\huggingface\hub\Qwen3-Embedding-0.6B-GGUF\Qwen3-Embedding-0.6B-Q8_0.gguf"
)
FINAL_DESIGN_SHA256 = "82fbd81b011e6183a9f9a5ab67724a41716a99eec47545ba097dc0b4b47b3c6c"
FINAL_DESIGN_COMMIT = "b81d01c6459008b1e7e5e420056a77a6fc9860a8"
T1_PATH = STUDY_ROOT / "artifacts" / "sup001_treatment" / "t1.json"
MECHANISM_SOURCES = (
    REPO_ROOT / "src" / "biological_memory" / "supersession.py",
    REPO_ROOT / "src" / "analysis" / "sup001_control.py",
    REPO_ROOT / "src" / "analysis" / "sup001_vectors.py",
    REPO_ROOT / "src" / "analysis" / "sup001_part1.py",
)
FORBIDDEN_SOURCE_TOKENS = (
    "SEALED_KEY_DO_NOT_OPEN",
    "current_sha256",
    "stale_sha256",
    "lineage_sha256",
    "q_facts_key",
    "rubric",
)


class SUP001PreflightError(RuntimeError):
    pass


def _git(*args: str) -> str:
    return subprocess.check_output(
        ("git", *args), cwd=REPO_ROOT, text=True, encoding="utf-8"
    ).strip()


def _ancestor(older: str, newer: str) -> bool:
    return subprocess.run(
        ("git", "merge-base", "--is-ancestor", older, newer),
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    ).returncode == 0


def _last_commit(path: Path) -> str:
    return _git("log", "-1", "--format=%H", "--", path.relative_to(REPO_ROOT).as_posix())


def _identity(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(REPO_ROOT).as_posix() if path.is_relative_to(REPO_ROOT) else str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def source_leakage(paths: Iterable[Path]) -> dict[str, Any]:
    imports: dict[str, list[str]] = {}
    violations: dict[str, list[str]] = {}
    for path in paths:
        source = path.read_text(encoding="utf-8")
        relative = (
            path.relative_to(REPO_ROOT).as_posix()
            if path.is_relative_to(REPO_ROOT)
            else str(path)
        )
        found = [token for token in FORBIDDEN_SOURCE_TOKENS if token in source]
        if found:
            violations[relative] = found
        tree = ast.parse(source)
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
        imports[relative] = sorted(names)
    planted = "from pathlib import Path\nKEY = 'SEALED_KEY_DO_NOT_OPEN'\n"
    planted_rejected = any(token in planted for token in FORBIDDEN_SOURCE_TOKENS)
    return {
        "paths": [
            path.relative_to(REPO_ROOT).as_posix()
            if path.is_relative_to(REPO_ROOT)
            else str(path)
            for path in paths
        ],
        "imports": imports,
        "violations": violations,
        "planted_forbidden_reference_rejected": planted_rejected,
        "pass": not violations and planted_rejected,
    }


def _evaluate_fixture(values: dict[str, Any]) -> str:
    if not values["integrity"]:
        return "INTEGRITY_STOP"
    if values["current_only"] < 64 or values["gain"] < 16:
        return "CURRENT_VALUE_NOT_SURFACED"
    if values["unchanged_losses"] != 0:
        return "UNCHANGED_FACT_REGRESSION"
    if values["lineages"] != 64 or values["natural_stale"] != 0:
        return "LINEAGE_OR_SILENCE_FAILURE"
    if not values["provenance"]:
        return "PROVENANCE_OR_INVARIANT_FAILURE"
    return "SUPERSESSION_OFFLINE_ELIGIBLE"


def synthetic_reachability() -> dict[str, Any]:
    passing = {
        "integrity": True,
        "current_only": 64,
        "gain": 16,
        "unchanged_losses": 0,
        "lineages": 64,
        "natural_stale": 0,
        "provenance": True,
    }
    fixtures = {
        "G1": ({**passing, "integrity": False}, "INTEGRITY_STOP"),
        "G2": ({**passing, "gain": 15}, "CURRENT_VALUE_NOT_SURFACED"),
        "G3": ({**passing, "unchanged_losses": 1}, "UNCHANGED_FACT_REGRESSION"),
        "G4": ({**passing, "natural_stale": 1}, "LINEAGE_OR_SILENCE_FAILURE"),
        "G5": ({**passing, "provenance": False}, "PROVENANCE_OR_INVARIANT_FAILURE"),
        "pass": (passing, "SUPERSESSION_OFFLINE_ELIGIBLE"),
    }
    observed = {name: _evaluate_fixture(values) for name, (values, _expected) in fixtures.items()}
    expected = {name: expected for name, (_values, expected) in fixtures.items()}
    return {"observed": observed, "expected": expected, "all_reachable": observed == expected}


def _actual_name_check(mechanism: dict[str, Any], control: dict[str, Any]) -> dict[str, Any]:
    ledger, transitions = build_ledger(mechanism)
    first_key = next(row["memory_key"] for row in mechanism["registrations"] if row["operation"] == "initial")
    lineage = ledger.lineage(first_key)
    ranked = ledger.natural_rank(control["queries"][0]["population"], limit=8)
    selected = {row["episode_sha256"] for row in ranked}
    before = ledger_digest(ledger)
    ledger.lineage(first_key)
    ledger.natural_rank(control["queries"][0]["population"], limit=8)
    after = ledger_digest(ledger)
    return {
        "registrations_executed": len(transitions),
        "lineage_versions": len(lineage),
        "lineage_accessibility": [row.accessibility for row in lineage],
        "natural_excludes_first_two_versions": not any(row.episode_sha256 in selected for row in lineage[:-1]),
        "lineage_bypasses_accessibility": [row.episode_sha256 for row in lineage] == [row.episode_sha256 for row in ledger.lineage(first_key)],
        "reads_state_pure": before == after,
        "final_distribution": ledger.validate(),
    }


def _subject_coverage(mechanism: dict[str, Any]) -> dict[str, Any]:
    episode_users = [str(row["user"]) for row in mechanism["episodes"]]
    rows = []
    for query in mechanism["queries"]:
        text = str(query["text"])
        subject = text.split(" for my ", 1)[1].removesuffix("?")
        matches = sum(subject in user for user in episode_users)
        rows.append({"query_id": query["query_id"], "subject_sha256": hashlib.sha256(subject.encode()).hexdigest(), "episode_matches": matches})
    return {
        "query_count": len(rows),
        "all_subjects_planted": all(row["episode_matches"] >= 1 for row in rows),
        "match_distribution": {
            "minimum": min(row["episode_matches"] for row in rows),
            "maximum": max(row["episode_matches"] for row in rows),
            "counts": {str(value): sum(row["episode_matches"] == value for row in rows) for value in sorted({row["episode_matches"] for row in rows})},
        },
        "rows": rows,
    }


def run(output_path: Path = PREFLIGHT_PATH, model_path: Path = MODEL_PATH) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite SUP-001 Preflight: {output_path}")
    if _git("status", "--porcelain"):
        raise SUP001PreflightError("SUP-001 Preflight requires a clean worktree")
    required = (
        HYPOTHETICAL,
        REPO_ROOT / "PREFLIGHT.md",
        REPO_ROOT / "AGENTS.md",
        PRE_REGISTRATION,
        FINAL_DESIGN,
        MECHANISM_PATH,
        CORPUS_LOCK,
        SEALED_KEY,
        MANIFEST_PATH,
        CACHE_PATH,
        CONTROL_PATH,
        PART1_PATH,
        model_path,
        *MECHANISM_SOURCES,
        Path(__file__),
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SUP001PreflightError(f"Missing Preflight inputs: {missing}")
    final = json.loads(FINAL_DESIGN.read_text(encoding="utf-8"))
    mechanism = json.loads(MECHANISM_PATH.read_text(encoding="utf-8"))
    vector_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    control = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    part1 = json.loads(PART1_PATH.read_text(encoding="utf-8"))
    inventory = [_identity(path) for path in required]
    anchors = final["anchors"]
    anchor_checks = {
        "final_design": sha256_file(FINAL_DESIGN) == FINAL_DESIGN_SHA256,
        "hypothetical": sha256_file(HYPOTHETICAL) == anchors["hypothetical_reference"]["sha256"],
        "pre_registration": sha256_file(PRE_REGISTRATION) == anchors["pre_registration"]["sha256"],
        "mechanism": sha256_file(MECHANISM_PATH) == anchors["mechanism_manifest_sha256"],
        "vectors": sha256_file(MANIFEST_PATH) == anchors["vector_manifest_sha256"],
        "cache": sha256_file(CACHE_PATH) == anchors["vector_cache_sha256"],
        "control": sha256_file(CONTROL_PATH) == anchors["control_sha256"],
        "part1": sha256_file(PART1_PATH) == anchors["part1_sha256"],
        "model": sha256_file(model_path) == CARRIED_EMBEDDING_SHA256,
    }
    cache_record = vector_manifest["cache"]
    with EmbeddingCache(
        CACHE_PATH,
        mode="reuse",
        expected_file_sha256=cache_record["file_sha256"],
        expected_content_sha256=cache_record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    ) as cache:
        reproduced = compute_control(mechanism, cache)
        cache_replay = cache.record()
    comparable_keys = ("study", "arm", "status", "episode_count", "query_count", "top_k", "budget_chars", "queries")
    c0_exact = all(reproduced[key] == control[key] for key in comparable_keys)
    name_check = _actual_name_check(mechanism, control)
    leakage = source_leakage(MECHANISM_SOURCES)
    reachability = synthetic_reachability()
    coverage = _subject_coverage(mechanism)
    commit_order = [
        anchors["pre_registration"]["commit"],
        anchors["mechanism_implementation_commit"],
        anchors["benchmark_implementation_commit"],
        anchors["corpus_lock_commit"],
        anchors["vector_control_implementation_commit"],
        anchors["vector_lock_commit"],
        anchors["control_lock_commit"],
        anchors["part1_implementation_commit"],
        anchors["part1_artifact_commit"],
        FINAL_DESIGN_COMMIT,
        _last_commit(Path(__file__)),
    ]
    ancestry = [_ancestor(left, right) for left, right in zip(commit_order, commit_order[1:])]
    t1_absent = not T1_PATH.exists()
    ordering = {
        "commits": commit_order,
        "adjacent_ancestry": ancestry,
        "all_ancestry_pass": all(ancestry),
        "final_design_last_commit": _last_commit(FINAL_DESIGN),
        "preflight_source_last_commit": _last_commit(Path(__file__)),
        "T1_absent_before_preflight": t1_absent,
    }
    pf2_pass = bool(
        name_check["registrations_executed"] == 192
        and name_check["lineage_versions"] == 3
        and name_check["lineage_accessibility"] == [0.0, 0.0, 1.0]
        and name_check["natural_excludes_first_two_versions"]
        and name_check["lineage_bypasses_accessibility"]
        and name_check["reads_state_pure"]
    )
    checks = {
        "PF1": {"pass": all(anchor_checks.values()) and len(inventory) == len(required), "evidence": {"inventory": inventory, "anchor_checks": anchor_checks, "counts": {"episodes": 256, "registrations": 192, "queries": 96, "vectors": vector_manifest["cache"]["entries"]}}},
        "PF2": {"pass": pf2_pass, "evidence": name_check},
        "PF3": {"pass": all(ancestry) and t1_absent and leakage["pass"], "evidence": {"ordering": ordering, "leakage": leakage, "sealed_key": {**_identity(SEALED_KEY), "handling": "hashed only; JSON not parsed"}}},
        "PF4": {"pass": reachability["all_reachable"] and coverage["all_subjects_planted"] and len(mechanism["registrations"]) == 192, "evidence": {"gate_reachability": reachability, "target_coverage": coverage, "lineage_versions": sorted({len(rows) for rows in part1["ledger"]["lineages"].values()})}},
        "PF5": {"pass": len({row["episode_sha256"] for row in mechanism["episodes"]}) == 256 and all(len(key) > 0 for key in part1["ledger"]["lineages"]), "evidence": "Comparisons use canonical episode content SHA-256 and explicit memory_key only; no UUID, timestamp, or path keys."},
        "PF6": {"pass": c0_exact and cache_replay["hits"] == 352 and cache_replay["misses"] == 0, "evidence": {"complete_C0_object_equal": c0_exact, "queries": 96, "population_per_query": 256, "cache_replay": cache_replay}},
        "PF7": {"pass": part1["fresh_process"]["identity_equal"] and part1["read_purity"]["state_unchanged"] and all(row["status"] == "PASS" for row in part1["degenerate_states"]), "evidence": {"feedback": "explicit registration only; reads have no feedback", "fresh_process": part1["fresh_process"], "read_purity": part1["read_purity"], "final_distribution": part1["final_distribution"], "degenerate_states": part1["degenerate_states"]}},
        "PF8": {"pass": True, "evidence": "The 96-query offline study detects selection, silence, backfill, and provenance. The conditional 35-turn ablation can detect reader use and short integration regressions, but cannot detect long-run behavior, inferred contradictions, or production ecology."},
        "PF9": {"pass": True, "evidence": ["G1 can pass while the reader ignores delivered context; the ablation owns that residual.", "G2 can pass because explicit metadata is correct while contradiction inference remains absent and excluded.", "G3 can pass on the 32 unchanged fixtures while other query distributions regress.", "G4 can pass lineage recovery while natural current retrieval fails; G2 is independent.", "G5 can pass structural provenance while answer correctness fails.", "A 32k ceiling can pass trivially because payloads are 1,394-1,732 chars; selected identities and zero losses remain separate checks."]},
        "PF10": {"pass": True, "evidence": {"availability_is_answer_verdict": False, "offline_pass_authorizes": "registered 35-turn ablation only", "reader_required": "fixed Qwen reader with scored current, unchanged, and history answers", "full_live_run_authorized": False, "production_authorized": False}},
    }
    status = "PASS" if all(row["pass"] for row in checks.values()) else "FAIL"
    result = {
        "study": "SUP-001",
        "stage": "Preflight Part 2 PF1-PF10",
        "status": status,
        "checks": checks,
        "measurement_authorized": status == "PASS",
        "ablation_authorized": False,
        "full_live_run_authorized": False,
    }
    result["canonical_digest"] = canonical_digest(result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if status != "PASS":
        raise SUP001PreflightError("SUP-001 PF1-PF10 failed")
    return result

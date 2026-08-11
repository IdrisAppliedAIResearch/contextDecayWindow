from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

from src.analysis.sal001_score import validate_manifest
from src.analysis.sal001_shared import (
    DATASET_BYTES,
    DATASET_SHA256,
    DESIGN,
    EXPECTED_COUNTS,
    EXPLORATION,
    MODEL_BYTES,
    MODEL_SHA256,
    REPO_ROOT,
    STUDY_ROOT,
    artifact_identity,
    canonical_digest,
    read_json,
    sha256_file,
    write_json,
)
from src.analysis.sal001_statistics import auc_for_labels, evaluate_gates


FINAL_DESIGN = STUDY_ROOT / "SAL_001_FINAL_DESIGN.json"
SCORE_SOURCE = REPO_ROOT / "src" / "analysis" / "sal001_score.py"
ANALYSIS_SOURCE = REPO_ROOT / "src" / "analysis" / "sal001_analyze.py"
FORBIDDEN_SCORE_IMPORTS = {
    "src.analysis.sal001_seal",
    "src.analysis.sal001_analyze",
    "src.analysis.sal001_preflight",
    "src.analysis.ec001_longmemeval",
}
FORBIDDEN_KEYS = {
    "labels",
    "stratum",
    "question_id",
    "question_type",
    "answer",
    "has_answer",
    "answer_session_ids",
}
SYNTHETIC_PREDICTABLE = 4.6384821217893855
SYNTHETIC_SURPRISING = 11.088347410991723


class SAL001PreflightError(RuntimeError):
    pass


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=REPO_ROOT, text=True, encoding="utf-8"
    ).strip()


def _ancestor(older: str, newer: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
    ).returncode == 0


def _last_commit(path: Path) -> str:
    relative = path.relative_to(REPO_ROOT).as_posix()
    return _git("log", "-1", "--format=%H", "--", relative)


def _unauthorized_keys(value: Any) -> list[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in FORBIDDEN_KEYS:
                found.add(str(key))
            found.update(_unauthorized_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_unauthorized_keys(child))
    return sorted(found)


def _score_imports() -> list[str]:
    tree = ast.parse(SCORE_SOURCE.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return sorted(imports)


def _raw_record(record: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "session_sha256",
        "exchange_index",
        "content_sha256",
        "rendered_token_sha256",
        "content_token_count",
        "preceding_rendered_token_count",
        "mean_nll",
    )
    return {key: record[key] for key in keys}


def _synthetic_reachability() -> dict[str, Any]:
    pass_metrics = {
        "adjusted_symmetric_auc": 0.62,
        "raw_symmetric_auc": 0.61,
        "adjusted_prior_auc": 0.60,
        "adjusted_next_auc": 0.61,
        "permutation_p": 0.005,
        "stratum_auc": {
            name: 0.60 for name in (
                "single-session-user",
                "single-session-assistant",
                "single-session-preference",
                "temporal-reasoning",
                "knowledge-update",
                "multi-session",
            )
        },
    }
    fixtures = {
        "pass": (pass_metrics, "SALIENCE_PROXY_SUPPORTED_OFFLINE"),
        "g2": ({**pass_metrics, "adjusted_symmetric_auc": 0.59}, "NO_INDEPENDENT_PROXIMITY"),
        "g3": ({**pass_metrics, "raw_symmetric_auc": 0.54}, "LENGTH_RARITY_OR_POSITION_CONFOUND"),
        "g4": ({**pass_metrics, "adjusted_prior_auc": 0.54}, "ASYMMETRIC_TEXT_SIGNAL"),
        "g5": (
            {
                **pass_metrics,
                "stratum_auc": {
                    **pass_metrics["stratum_auc"],
                    "multi-session": 0.44,
                },
            },
            "NON_GENERAL_SIGNAL",
        ),
    }
    dispositions = {
        name: evaluate_gates(True, metrics)["status"]
        for name, (metrics, _expected) in fixtures.items()
    }
    expected = {name: expected for name, (_metrics, expected) in fixtures.items()}
    auc_points = {
        "zero": auc_for_labels([1.0, 0.0], [False, True]),
        "half_tie": auc_for_labels([1.0, 1.0], [True, False]),
        "one": auc_for_labels([1.0, 0.0], [True, False]),
    }
    return {
        "dispositions": dispositions,
        "expected_dispositions": expected,
        "dispositions_match": dispositions == expected,
        "auc_points": auc_points,
        "auc_range_reached": auc_points == {"zero": 0.0, "half_tie": 0.5, "one": 1.0},
        "permutation_resolution": 1 / 100_001,
        "permutation_bar_resolvable": 1 / 100_001 <= 0.01,
    }


def run(
    dataset_path: Path,
    model_path: Path,
    seal_dir: Path,
    score_path: Path,
    repeat_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite Preflight: {output_path}")
    if not FINAL_DESIGN.is_file():
        raise SAL001PreflightError("Final design lock is absent")
    final_design = read_json(FINAL_DESIGN)
    anchors = final_design["commit_anchors"]
    expected_artifacts = final_design["artifact_sha256"]
    manifest_path = seal_dir / "scorer_manifest.json"
    labels_path = seal_dir / "SEALED_LABELS_DO_NOT_OPEN.json"
    selection_path = seal_dir / "selection_manifest.json"
    seal_report_path = seal_dir / "seal_report.json"
    paths = {
        "design": DESIGN,
        "exploration": EXPLORATION,
        "dataset": dataset_path,
        "model": model_path,
        "scorer_manifest": manifest_path,
        "sealed_labels": labels_path,
        "selection_manifest": selection_path,
        "seal_report": seal_report_path,
        "scores": score_path,
        "repeat_scores": repeat_path,
        "final_design": FINAL_DESIGN,
        "score_source": SCORE_SOURCE,
        "analysis_source": ANALYSIS_SOURCE,
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise SAL001PreflightError(f"Preflight inputs absent: {missing}")

    manifest = read_json(manifest_path)
    validate_manifest(manifest)
    seal_report = read_json(seal_report_path)
    scores = read_json(score_path)
    repeat = read_json(repeat_path)
    selection = read_json(selection_path)
    exploration = read_json(EXPLORATION)
    reachability = _synthetic_reachability()

    input_identities = {name: artifact_identity(path) for name, path in paths.items()}
    required_artifact_names = {
        "design",
        "exploration",
        "scorer_manifest",
        "sealed_labels",
        "selection_manifest",
        "seal_report",
        "scores",
        "repeat_scores",
        "score_source",
        "analysis_source",
    }
    expected_identity_pass = bool(
        set(expected_artifacts) == required_artifact_names
        and all(
        sha256_file(paths[name]) == expected_sha
        for name, expected_sha in expected_artifacts.items()
        )
    )
    fixed_external = {
        "dataset_bytes": dataset_path.stat().st_size == DATASET_BYTES,
        "dataset_sha256": sha256_file(dataset_path) == DATASET_SHA256,
        "model_bytes": model_path.stat().st_size == MODEL_BYTES,
        "model_sha256": sha256_file(model_path) == MODEL_SHA256,
    }

    imports = _score_imports()
    unauthorized_imports = sorted(set(imports) & FORBIDDEN_SCORE_IMPORTS)
    scorer_unauthorized_keys = _unauthorized_keys(manifest)
    score_unauthorized_keys = _unauthorized_keys(scores)
    rendered_lengths = [int(row["rendered_token_count"]) for row in scores["sessions"]]
    population = {
        "sessions": len(scores["sessions"]),
        "records": len(scores["records"]),
        "rendered_tokens": sum(rendered_lengths),
        "maximum_rendered_tokens": max(rendered_lengths),
    }
    population_pass = population == {
        "sessions": EXPECTED_COUNTS["eligible_sessions"],
        "records": EXPECTED_COUNTS["eligible_exchanges"],
        "rendered_tokens": 286_152,
        "maximum_rendered_tokens": 5_499,
    }

    first_hashes = [row["session_sha256"] for row in scores["sessions"][:3]]
    repeat_hashes = [row["session_sha256"] for row in repeat["sessions"]]
    full_prefix = [
        _raw_record(row)
        for row in scores["records"]
        if row["session_sha256"] in set(first_hashes)
    ]
    repeat_rows = [_raw_record(row) for row in repeat["records"]]
    repeat_pass = bool(
        repeat.get("session_limit") == 3
        and first_hashes == repeat_hashes
        and full_prefix == repeat_rows
        and scores["synthetic_probe"]["predictable_mean_nll"]
        == repeat["synthetic_probe"]["predictable_mean_nll"]
    )
    synthetic = scores["synthetic_probe"]
    synthetic_pass = bool(
        synthetic["predictable_mean_nll"] == SYNTHETIC_PREDICTABLE
        and synthetic["predictable_repeat_mean_nll"] == SYNTHETIC_PREDICTABLE
        and synthetic["surprising_mean_nll"] == SYNTHETIC_SURPRISING
        and synthetic["repeat_exact"]
        and synthetic["surprising_higher"]
    )

    commit_order = [
        anchors["design_commit"],
        anchors["implementation_commit"],
        anchors["seal_artifact_commit"],
        anchors["score_artifact_commit"],
        _last_commit(FINAL_DESIGN),
    ]
    ancestry = [
        _ancestor(older, newer)
        for older, newer in zip(commit_order, commit_order[1:])
    ]
    order_pass = all(ancestry) and anchors["design_commit"].startswith("15b718e3")

    stable_keys_pass = all(
        len(str(row["session_sha256"])) == 64
        and len(str(row["content_sha256"])) == 64
        and isinstance(row["exchange_index"], int)
        for row in scores["records"]
    )
    selection_pass = bool(
        all(selection["selection"]["ec001_first_twenty_reproduced"].values())
        and selection["selection"]["ordered_question_id_sha256"]
        == exploration["selection"]["ordered_question_id_digest"]
        and seal_report["counts"] == EXPECTED_COUNTS
    )
    adjustment = scores["adjustment"]
    identity_pass = bool(
        population_pass
        and scores["model"]["n_ctx"] == 6144
        and scores["model"]["vocabulary_size"] == 248_320
        and adjustment["rank"] == 5
        and all(
            abs(float(value)) < 1e-10
            for value in adjustment["residual_feature_correlations"].values()
        )
        and len({row["mean_nll"] for row in scores["records"]}) > 1
        and adjustment["residual_std"] > 0
        and synthetic_pass
    )

    checks = {
        "PF1": {
            "pass": bool(all(fixed_external.values()) and expected_identity_pass and selection_pass),
            "evidence": {
                "inputs": input_identities,
                "fixed_external": fixed_external,
                "final_design_artifact_hashes": expected_identity_pass,
                "selection": selection_pass,
            },
        },
        "PF2": {
            "pass": identity_pass,
            "evidence": {
                "behavioral_identity": exploration["behavioral_identity"],
                "population": population,
                "adjustment": adjustment,
                "synthetic_probe": synthetic,
            },
        },
        "PF3": {
            "pass": bool(order_pass and not unauthorized_imports and not scorer_unauthorized_keys and not score_unauthorized_keys),
            "evidence": {
                "commit_order": commit_order,
                "adjacent_ancestry": ancestry,
                "scorer_imports": imports,
                "unauthorized_imports": unauthorized_imports,
                "manifest_unauthorized_keys": scorer_unauthorized_keys,
                "score_unauthorized_keys": score_unauthorized_keys,
                "labels_hashed_not_parsed": artifact_identity(labels_path),
            },
        },
        "PF4": {
            "pass": bool(
                reachability["dispositions_match"]
                and reachability["auc_range_reached"]
                and reachability["permutation_bar_resolvable"]
                and EXPECTED_COUNTS["evidence_with_prior"] > 0
                and EXPECTED_COUNTS["evidence_with_next"] > 0
            ),
            "evidence": reachability,
        },
        "PF5": {
            "pass": stable_keys_pass,
            "evidence": "Session-content SHA-256, exchange index, content SHA-256, rendered-token SHA-256; no path or generated ID compares records.",
        },
        "PF6": {
            "pass": bool(selection_pass and synthetic_pass and repeat_pass),
            "evidence": {
                "ec001_first_twenty_reproduced": selection["selection"]["ec001_first_twenty_reproduced"],
                "synthetic_probe": synthetic,
                "prefix_sessions": first_hashes,
                "prefix_rows_byte_equal": repeat_pass,
            },
        },
        "PF7": {
            "pass": bool(
                repeat_pass
                and len({row["mean_nll"] for row in scores["records"]}) > 1
                and adjustment["residual_std"] > 0
            ),
            "evidence": {
                "feedback": False,
                "fresh_process_prefix_equal": repeat_pass,
                "constant_score": len({row["mean_nll"] for row in scores["records"]}) == 1,
                "adjusted_zero_variance": adjustment["residual_std"] == 0,
            },
        },
        "PF8": {
            "pass": True,
            "evidence": "Sixty histories and 92 AUC sessions test immediate within-session adjacency. They cannot test longer tag windows, retrieval, a 35-turn integration, endurance, or live answer correctness.",
        },
        "PF9": {
            "pass": True,
            "evidence": [
                "Surprisal can pass without biological reward equivalence.",
                "Markers can pass without complete relevance labels.",
                "Within-session AUC can pass without natural conversation ecology.",
                "Adjustment removes only four registered observed covariates.",
                "F2 can pass while tags, capture, accessibility, replay, and retrieval fail.",
            ],
        },
        "PF10": {
            "pass": True,
            "evidence": {
                "diagnostic_only": True,
                "delivery_evaluated": False,
                "answer_correctness_evaluated": False,
                "later_accessibility_requires_new_registration": True,
                "later_delivery_requires_35_turn_ablation_and_live_decision": True,
            },
        },
    }
    status = "PASS" if all(check["pass"] for check in checks.values()) else "FAIL"
    result = {
        "study": "SAL-001",
        "status": status,
        "checks": checks,
        "measurement_authorized": status == "PASS",
        "ablation_authorized": False,
        "live_run_authorized": False,
    }
    result["canonical_digest"] = canonical_digest(result)
    write_json(output_path, result)
    if status != "PASS":
        raise SAL001PreflightError("SAL-001 Preflight failed")
    return result

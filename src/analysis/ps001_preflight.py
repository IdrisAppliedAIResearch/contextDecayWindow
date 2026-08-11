from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from src.analysis.ps001_exploration import (
    AMENDMENT_006,
    AMENDMENT_006_AUTHORIZATION,
    AMENDMENT_007,
    AMENDMENT_007_AUTHORIZATION,
    AMENDMENT_008,
    AMENDMENT_008_AUTHORIZATION,
    AUTHORIZATION,
    DESIGN,
    EXPECTED_EPISODES,
    EXPECTED_NORMALIZED_VECTOR_SHA256,
    GRID,
    LIVE_ARRAY_CEILING,
    MECHANISM_SOURCE,
    REPO_ROOT,
    REV4_COMMIT,
    REV4_RESULT_SHA256,
    StageResult,
    apply_selection_rule,
    execute_ordered_gates,
    load_episode_population,
    load_historical_gate,
    payload_sha256,
    sha256_file,
    synthetic_reachability,
)
from src.retrieval_mechanism_ledger.ps001 import (
    SparseEngramAutoassociator,
    degrade_sparse_code,
    rademacher_projection,
)


COMPONENT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
)
FINAL_DESIGN = COMPONENT_ROOT / "PS_001_FINAL_DESIGN_REVISION.md"
FINAL_AUTHORIZATION = COMPONENT_ROOT / "PS_001_FINAL_DESIGN_AUTHORIZATION.md"
PART1_ROOT = COMPONENT_ROOT / "artifacts" / "ps001_exploration" / "part1_process_1"
EXPLORATION = PART1_ROOT / "exploration.json"
MANIFEST = PART1_ROOT / "artifact_manifest.json"
SELECTED_CELL = PART1_ROOT / "cells" / "d4096_k41" / "cell_result.json"
DETERMINISM = COMPONENT_ROOT / "artifacts" / "ps001_exploration" / "two_process_determinism.json"
HISTORICAL_GATE = COMPONENT_ROOT / "artifacts" / "ps001_exploration" / "rev4_reproduction.json"
EXPLORATION_SOURCE = REPO_ROOT / "src" / "analysis" / "ps001_exploration.py"
PREFLIGHT_SOURCE = Path(__file__).resolve()
COMPONENT_TEST = REPO_ROOT / "tests" / "test_ps001_component.py"
EXPLORATION_TEST = REPO_ROOT / "tests" / "test_ps001_exploration.py"
PREFLIGHT_TEST = REPO_ROOT / "tests" / "test_ps001_preflight.py"

EXPECTED_FINAL_DESIGN_SHA256 = "22404732fb2fc39ccf1cc84c2b5d24c16ee1bba6f8bcdef314a2d30c20f7c430"
EXPECTED_FINAL_AUTHORIZATION_SHA256 = "f3c382417e2307f89df8383d1d43d840d4c790254f336676f5157266ca64d66d"
EXPECTED_EXPLORATION_SHA256 = "b1645ecb4991ed7b3bd84729779ccaeb7306b39a035dfc196e901f54e52b154d"
EXPECTED_MANIFEST_SHA256 = "c1a83758b6956a861d9fbedcc1a6bc64eac35ee3f165cb08195f086f1ff95e18"
EXPECTED_SELECTED_CELL_SHA256 = "b7bcbea8e9c628d114cabb1a49dc962d41019800eacd89308e0314ff1c77c760"
EXPECTED_DETERMINISM_SHA256 = "f4be4cf316d93793334b135a91b716585521409ab5ccb515a3d278dad2d5ce8a"
EXPECTED_MECHANISM_DIGEST = "0d45ddd45980dbf3989a543136bad52d4f743f650f3c0af76e370f049b6c80cc"
SELECTED_CONFIGURATION = (4096, 41)
REQUIRED_TRACE_FIELDS = frozenset(
    {
        "cue_level",
        "swap_count",
        "source_content_sha256",
        "source_code_sha256",
        "deactivated_indices",
        "activated_indices",
        "initial_state_sha256",
        "state_sha256_trace",
        "changed_units_per_sweep",
        "active_count_per_state",
        "quadratic_score_trace",
        "field_margin_trace",
        "fixed_point",
        "cycle",
        "runtime_guard",
        "converged",
        "sweeps",
        "repeated_state_witness",
        "terminal_state_sha256",
        "terminal_stored_content_sha256",
        "terminal_status",
        "exact_source_recovery",
        "terminal_hamming_distance",
    }
)


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=REPO_ROOT, text=True, encoding="utf-8"
    ).strip()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _artifact(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def verify_manifest(root: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    listed = {str(row["path"]): row for row in manifest["files"]}
    actual = {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and path != manifest_path
    }
    missing = sorted(set(listed) - set(actual))
    unexpected = sorted(set(actual) - set(listed))
    mismatches = []
    for relative in sorted(set(listed) & set(actual)):
        row = listed[relative]
        path = actual[relative]
        if int(row["bytes"]) != path.stat().st_size or str(row["sha256"]) != sha256_file(path):
            mismatches.append(relative)
    passed = not missing and not unexpected and not mismatches
    return {
        "status": "PASS" if passed else "FAIL",
        "listed_file_count": len(listed),
        "actual_file_count": len(actual),
        "missing": missing,
        "unexpected": unexpected,
        "identity_mismatches": mismatches,
        "file_sequence_sha256": manifest["file_sequence_sha256"],
    }


def _ancestor(older: str, newer: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        cwd=REPO_ROOT,
        check=False,
    ).returncode == 0


def _planted_ordering() -> dict[str, Any]:
    names = ("G1", "G2", "G3", "G4", "G5")
    outcomes = []
    for failure_index in range(4):
        calls: list[str] = []

        def make_stage(index: int):
            def stage() -> StageResult:
                calls.append(names[index])
                status = "FAIL" if index == failure_index else "PASS"
                return StageResult(status, {"status": status})

            return stage

        results = execute_ordered_gates(
            [(name, make_stage(index)) for index, name in enumerate(names)]
        )
        expected = list(names[: failure_index + 1])
        passed = calls == expected and all(
            results[name] == "NOT_REACHED"
            for name in names[failure_index + 1 :]
        )
        outcomes.append(
            {
                "planted_failure": names[failure_index],
                "executed": calls,
                "later_stages_unreachable": passed,
            }
        )
    return {
        "status": "PASS" if all(row["later_stages_unreachable"] for row in outcomes) else "FAIL",
        "outcomes": outcomes,
    }


def _disposition_reachability() -> dict[str, Any]:
    def cell(g2: str, g3: str, g4: str | None = None, g5: str | None = None):
        gates: dict[str, Any] = {
            "G2": {"status": g2},
            "G3": {"status": g3},
            "G4": "NOT_REACHED" if g4 is None else {"status": g4},
            "G5": "NOT_REACHED",
        }
        if g5 is not None:
            gates["G5"] = {
                "status": g5,
                "basin_levels": {"10_percent": {"exact_recovery_count": 119}},
            }
        return {"code_dimension": 4096, "active_count": 41, "gates": gates}

    observed = {
        "NO_VALID_IMPLEMENTATION": apply_selection_rule([cell("FAIL", "FAIL")])[1],
        "NO_STORED_SPARSE_CODE": apply_selection_rule([cell("PASS", "FAIL")])[1],
        "NO_VIABLE_SPARSE_CODE": apply_selection_rule([cell("PASS", "PASS", "FAIL")])[1],
        "SPARSE_ENGRAM_CANDIDATE_CHARACTERIZED": apply_selection_rule(
            [cell("PASS", "PASS", "PASS", "PASS")]
        )[1],
    }
    return {
        "status": "PASS" if all(key == value for key, value in observed.items()) else "FAIL",
        "observed": observed,
        "synthetic_g3_g4": synthetic_reachability(),
    }


def _trace_inventory() -> dict[str, Any]:
    trace_root = PART1_ROOT / "traces" / "d4096_k41"
    expected = {
        "uncorrupted": 119,
        "one_swap": 119,
        "10_percent": 119,
        "30_percent": 119,
        "50_percent": 119,
        "degenerate": 7,
    }
    levels: dict[str, Any] = {}
    all_rows: list[dict[str, Any]] = []
    schema_failures: list[str] = []
    for level, count in expected.items():
        path = trace_root / f"{level}.jsonl"
        rows = _read_jsonl(path)
        all_rows.extend(rows)
        for index, row in enumerate(rows):
            missing = REQUIRED_TRACE_FIELDS - set(row)
            if missing:
                schema_failures.append(f"{level}:{index}:{sorted(missing)}")
        levels[level] = {
            "artifact": _artifact(path),
            "row_count": len(rows),
            "expected_count": count,
            "fixed_points": sum(bool(row["fixed_point"]) for row in rows),
            "exact_recoveries": sum(bool(row["exact_source_recovery"]) for row in rows),
            "wrong_stored_attractors": sum(row["terminal_status"] == "stored" and not row["exact_source_recovery"] for row in rows),
            "spurious_terminals": sum(row["terminal_status"] == "spurious" for row in rows),
            "cycles": sum(bool(row["cycle"]) for row in rows),
            "runtime_guards": sum(bool(row["runtime_guard"]) for row in rows),
        }
    content_ids = [
        str(row["source_content_sha256"])
        for row in _read_jsonl(trace_root / "uncorrupted.jsonl")
    ]
    code_ids = [
        str(row["source_code_sha256"])
        for row in _read_jsonl(trace_root / "uncorrupted.jsonl")
    ]
    state_ids = [
        str(state)
        for row in all_rows
        for state in row["state_sha256_trace"]
    ]
    stable_hashes = all(
        len(value) == 64 and all(character in "0123456789abcdef" for character in value)
        for value in content_ids + code_ids + state_ids
    )
    counts_pass = all(levels[level]["row_count"] == count for level, count in expected.items())
    terminated = all(
        bool(row["fixed_point"]) or bool(row["cycle"]) or bool(row["runtime_guard"])
        for row in all_rows
    )
    return {
        "status": "PASS" if counts_pass and not schema_failures and stable_hashes and terminated else "FAIL",
        "levels": levels,
        "total_trace_count": len(all_rows),
        "expected_total_trace_count": 602,
        "schema_failures": schema_failures,
        "stable_content_code_state_hashes": stable_hashes,
        "content_identity_sequence_sha256": hashlib.sha256("\n".join(content_ids).encode("ascii")).hexdigest(),
        "code_identity_sequence_sha256": hashlib.sha256("\n".join(code_ids).encode("ascii")).hexdigest(),
        "state_identity_sequence_sha256": hashlib.sha256("\n".join(state_ids).encode("ascii")).hexdigest(),
        "all_traces_reach_fixed_cycle_or_guard": terminated,
    }


def build_preflight() -> dict[str, Any]:
    anchors = {
        "design": _artifact(DESIGN),
        "authorization": _artifact(AUTHORIZATION),
        "amendment_006": _artifact(AMENDMENT_006),
        "amendment_006_authorization": _artifact(AMENDMENT_006_AUTHORIZATION),
        "amendment_007": _artifact(AMENDMENT_007),
        "amendment_007_authorization": _artifact(AMENDMENT_007_AUTHORIZATION),
        "amendment_008": _artifact(AMENDMENT_008),
        "amendment_008_authorization": _artifact(AMENDMENT_008_AUTHORIZATION),
        "final_design": _artifact(FINAL_DESIGN),
        "final_authorization": _artifact(FINAL_AUTHORIZATION),
        "mechanism_source": _artifact(MECHANISM_SOURCE),
        "exploration_source": _artifact(EXPLORATION_SOURCE),
        "preflight_source": _artifact(PREFLIGHT_SOURCE),
        "component_test": _artifact(COMPONENT_TEST),
        "exploration_test": _artifact(EXPLORATION_TEST),
        "preflight_test": _artifact(PREFLIGHT_TEST),
    }
    fixed_hashes = {
        "final_design": anchors["final_design"]["sha256"] == EXPECTED_FINAL_DESIGN_SHA256,
        "final_authorization": anchors["final_authorization"]["sha256"] == EXPECTED_FINAL_AUTHORIZATION_SHA256,
        "exploration": sha256_file(EXPLORATION) == EXPECTED_EXPLORATION_SHA256,
        "manifest": sha256_file(MANIFEST) == EXPECTED_MANIFEST_SHA256,
        "selected_cell": sha256_file(SELECTED_CELL) == EXPECTED_SELECTED_CELL_SHA256,
        "determinism": sha256_file(DETERMINISM) == EXPECTED_DETERMINISM_SHA256,
    }
    exploration = _read_json(EXPLORATION)
    selected = _read_json(SELECTED_CELL)
    determinism = _read_json(DETERMINISM)
    manifest = verify_manifest(PART1_ROOT, MANIFEST)
    population = load_episode_population()
    projection_fixture = rademacher_projection(bytes(32), 5, 3).tolist()
    corruption_source = [1, 1, 0, 0, 1, 0, 0, 0]
    degraded, deactivated, activated = degrade_sparse_code(
        np.asarray(corruption_source, dtype=np.uint8), f"{1:064x}", 2
    )
    trace_inventory = _trace_inventory()
    historical = load_historical_gate(HISTORICAL_GATE)
    ordering = _planted_ordering()
    reachability = _disposition_reachability()
    selected_gates = selected["gates"]

    pf1_pass = bool(
        all(fixed_hashes.values())
        and manifest["status"] == "PASS"
        and population.inventory["episode_count"] == EXPECTED_EPISODES
        and population.inventory["normalized_float64_sha256"] == EXPECTED_NORMALIZED_VECTOR_SHA256
        and projection_fixture == [[-1, -1, 1], [-1, 1, 1], [-1, -1, -1], [-1, 1, 1], [-1, 1, -1]]
        and deactivated == (4, 1)
        and activated == (2, 7)
        and int(degraded.sum()) == 3
        and trace_inventory["status"] == "PASS"
    )
    pf1 = {
        "status": "PASS" if pf1_pass else "FAIL",
        "anchors": anchors,
        "fixed_hashes": fixed_hashes,
        "population": population.inventory,
        "manifest": manifest,
        "projection_fixture": projection_fixture,
        "corruption_fixture": {
            "deactivated": list(deactivated),
            "activated": list(activated),
            "active_count": int(degraded.sum()),
        },
        "trace_schema": {
            "required_fields": sorted(REQUIRED_TRACE_FIELDS),
            "status": trace_inventory["status"],
        },
    }

    selected_checks = selected["name_checks"]
    pf2_pass = bool(
        len(selected_checks) == 10
        and all(bool(row["demonstrated"]) for row in selected_checks)
        and selected["formation_distribution"]["sha256"]
        and selected["operator_audit"]["sha256"]
    )
    pf2 = {
        "status": "PASS" if pf2_pass else "FAIL",
        "behavioral_identity": selected["behavioral_identity"],
        "name_checks": selected_checks,
        "pairwise_distribution": selected["formation_distribution"],
        "unique_codes_not_sufficient_alone": True,
        "nearest_code_decoding_not_used": True,
    }

    commit_order = (
        "e20d0c0",
        "90e88f86",
        "9712a5b4",
        "ea6a9a20",
        "2c755034",
        "04ff100",
        "56442f70",
        "df4718f1",
    )
    ancestry = [
        _ancestor(older, newer)
        for older, newer in zip(commit_order, commit_order[1:])
    ]
    pf3_pass = all(ancestry) and ordering["status"] == "PASS"
    pf3 = {
        "status": "PASS" if pf3_pass else "FAIL",
        "commit_order": list(commit_order),
        "adjacent_ancestry": ancestry,
        "executed_gate_order": ["historical_reproduction", "leakage", "G1", "G2", "G3", "G4", "G5", "interpretation"],
        "planted_short_circuits": ordering,
        "q11_import_stage": "ABSENT",
    }

    pf4_pass = reachability["status"] == "PASS" and selected_gates["G5"]["status"] == "PASS"
    pf4 = {
        "status": "PASS" if pf4_pass else "FAIL",
        "reachability": reachability,
        "selected_real_configuration_already_passed_exploration": True,
        "selected_configuration": {"code_dimension": 4096, "active_count": 41},
        "later_reporting_is_characterization_not_confirmation": True,
    }

    fit_parameters = tuple(inspect.signature(SparseEngramAutoassociator.fit).parameters)
    pf5_pass = trace_inventory["stable_content_code_state_hashes"] and fit_parameters == (
        "vectors",
        "code_dimension",
        "active_count",
        "projection_seed",
    )
    pf5 = {
        "status": "PASS" if pf5_pass else "FAIL",
        "fit_parameters": list(fit_parameters),
        "trace_identities": {key: value for key, value in trace_inventory.items() if key.endswith("sha256") or key.startswith("stable_")},
        "generated_ids_timestamps_paths_as_comparison_keys": False,
    }

    pf6_pass = bool(
        historical["status"] == "PASS"
        and historical["control_commit"] == REV4_COMMIT
        and historical["generated_result_sha256"] == REV4_RESULT_SHA256
        and historical["exact_reproduction"]["converged_count"] == 119
        and historical["exact_reproduction"]["basin_sizes"] == [5, 13, 15, 20, 29, 37]
    )
    pf6 = {
        "status": "PASS" if pf6_pass else "FAIL",
        "historical_gate": _artifact(HISTORICAL_GATE),
        "exact_reproduction": historical["exact_reproduction"],
        "result_sha256": historical["generated_result_sha256"],
    }

    resources_pass = all(
        cell["runtime"]["wall_seconds"] <= 600
        and cell["live_array_bytes"]["estimated_with_largest_audit_chunk"] < LIVE_ARRAY_CEILING
        for cell in exploration["cells"]
    )
    pf7_pass = trace_inventory["status"] == "PASS" and resources_pass
    pf7 = {
        "status": "PASS" if pf7_pass else "FAIL",
        "trace_inventory": trace_inventory,
        "intended_stored_attractors": trace_inventory["levels"]["uncorrupted"]["fixed_points"],
        "wrong_stored_attractors": sum(level["wrong_stored_attractors"] for level in trace_inventory["levels"].values()),
        "spurious_terminals": sum(level["spurious_terminals"] for level in trace_inventory["levels"].values()),
        "cycles": sum(level["cycles"] for level in trace_inventory["levels"].values()),
        "runtime_guards": sum(level["runtime_guards"] for level in trace_inventory["levels"].values()),
        "resource_ceilings_pass": resources_pass,
    }

    pf8 = {
        "status": "PASS",
        "detects": "failures on this fixed 119-episode store and registered corruption set",
        "cannot_detect": [
            "capacity at 1,000 episodes",
            "natural-language cue robustness",
            "new-episode generalization",
            "biological realism",
            "live answer use",
        ],
        "35_turn_live_ablation": "NOT_APPLICABLE_NO_INFERENCE_AUTHORIZED",
    }

    surrogate_rows = exploration["surrogate_audit"]
    required_residual = any(
        "tie" in str(row["observation"]).lower()
        or "field" in str(row["control_or_residual"]).lower()
        for row in surrogate_rows
    )
    pf9_pass = len(surrogate_rows) >= 13 and required_residual
    pf9 = {
        "status": "PASS" if pf9_pass else "FAIL",
        "surrogate_audit": surrogate_rows,
        "accepted_residuals": [
            "same-store grid selection can overfit",
            "bit swaps need not transfer to natural-language cues",
            "untested cues can cycle or reach spurious attractors",
            "one deterministic seed does not generalize",
            "exact tie behavior need not be perturbation robust",
            "offline completion need not improve retrieval or answers",
        ],
    }

    pf10_pass = bool(
        exploration["zero_embedding_requests"] == 0
        and exploration["zero_model_generation_calls"] == 0
        and determinism["status"] == "PASS"
        and determinism["first_mechanism_digest"] == EXPECTED_MECHANISM_DIGEST
    )
    pf10 = {
        "status": "PASS" if pf10_pass else "FAIL",
        "offline_formation_and_recovery_are_answer_verdicts": False,
        "natural_language_cue_study_required": True,
        "separate_live_evaluation_required": True,
        "either_authorized_here": False,
        "zero_embedding_requests": exploration["zero_embedding_requests"],
        "zero_model_generation_calls": exploration["zero_model_generation_calls"],
    }

    checks = {
        "PF1": pf1,
        "PF2": pf2,
        "PF3": pf3,
        "PF4": pf4,
        "PF5": pf5,
        "PF6": pf6,
        "PF7": pf7,
        "PF8": pf8,
        "PF9": pf9,
        "PF10": pf10,
    }
    status = "PASS" if all(check["status"] == "PASS" for check in checks.values()) else "FAIL"
    return {
        "study": "PS-001",
        "stage": "Preflight Part 2 PF1-PF10",
        "status": status,
        "selected_configuration": {"code_dimension": 4096, "active_count": 41},
        "outcome_ceiling": "CHARACTERIZED",
        "checks": checks,
        "check_order": list(checks),
        "part1_mechanism_digest": exploration["determinism"]["mechanism_digest"],
        "part1_disposition": exploration["disposition"],
        "additional_real_mechanism_run": False,
        "zero_embedding_requests": 0,
        "zero_model_generation_calls": 0,
        "preflight_payload_sha256": payload_sha256(checks),
    }


def write_preflight(output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite PS-001 Preflight: {output}")
    if _git("status", "--porcelain"):
        raise RuntimeError("PS-001 Preflight requires a clean committed worktree")
    result = build_preflight()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if result["status"] != "PASS":
        raise RuntimeError("PS-001 Preflight Part 2 failed")
    return result


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify PS-001 PF1-PF10")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    result = write_preflight(args.output)
    print(json.dumps({"status": result["status"], "stage": result["stage"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

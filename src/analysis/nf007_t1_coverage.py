"""Outcome-blind sealed-T1 cluster-coverage control for NF-007."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

from analysis.nf006_cache import canonical_bytes, load_vectors
from analysis.nf006_inputs import Q11_TURN, eligible_parents, load_parents
from analysis.nf006_mechanism import (
    build_statement_candidates,
    expanded_cluster_assignments,
)
from analysis.nf007_exploration import (
    CLUSTER_COUNT,
    REPO_ROOT,
    assignment_digest,
    cluster_parents,
    distribution,
    sha256_file,
    verify_inputs,
)


NF006_ROOT = REPO_ROOT / "experiments/components/biological_memory/nf_006"
NF007_ROOT = REPO_ROOT / "experiments/components/biological_memory/nf_007"
SELECTION_SEAL = NF006_ROOT / "artifacts/g6_g7_selection_seal.json"
VECTOR_CACHE = NF006_ROOT / "artifacts/nf006_vectors.sqlite"
PART1_ARTIFACT = NF007_ROOT / "artifacts/part1_cluster_reachability.json"
DEFAULT_OUTPUT = NF007_ROOT / "artifacts/t1_cluster_coverage_control.json"

REGISTRATION_COMMIT = "9360eb9556a04009407e71a07b57dae0913a4851"
SELECTION_SEAL_COMMIT = "ef074cda8753b594cd970dd4e4c83f0b7b8e04c1"
SELECTION_SEAL_SHA256 = (
    "3dc22122d4cae27af29d642cee68918e4f683ecdac6885691b44a0bf39786686"
)
PART1_SHA256 = "bc51b33796c45b5d9db2b804ba9989f2b7cafce689b761bd2f07be3b3fb5f71d"
PARENT_ASSIGNMENT_SHA256 = (
    "29c026e653ab7f65b032b0b3104a6b24194d951d0fe740c913c5406b0756f9ca"
)
STATEMENT_ASSIGNMENT_SHA256 = (
    "be4fc93ed80e5ff582074177729a1d60dcfb3897f758cb8cfdae4d99889ade14"
)
ARM = "T1_OWN_STATEMENT"
PROBE_TURN = 120
EXPECTED_SELECTED = 80


def select_sealed_record(payload: Mapping[str, object]) -> Mapping[str, object]:
    records = payload.get("records")
    if not isinstance(records, list):
        raise AssertionError("NF-006 selection seal has no records list")
    matches = [
        row
        for row in records
        if isinstance(row, dict)
        and row.get("arm") == ARM
        and int(row.get("probe_turn", -1)) == PROBE_TURN
    ]
    if len(matches) != 1:
        raise AssertionError("Expected exactly one sealed T1 record at turn 120")
    return matches[0]


def coverage_summary(
    selected_ids: Sequence[str],
    statement_ids: Sequence[str],
    assignments: Sequence[int],
) -> dict[str, object]:
    if len(selected_ids) != EXPECTED_SELECTED or len(set(selected_ids)) != EXPECTED_SELECTED:
        raise AssertionError("Sealed T1 selection must contain 80 unique identities")
    assignment_by_id = dict(zip(statement_ids, assignments, strict=True))
    unknown = sorted(set(selected_ids) - assignment_by_id.keys())
    if unknown:
        raise AssertionError(f"Sealed T1 identities missing from assignments: {unknown}")

    counts = Counter(int(assignment_by_id[identity]) for identity in selected_ids)
    touched = sorted(counts)
    missing = sorted(set(range(CLUSTER_COUNT)) - counts.keys())
    return {
        "status": "FLOOR_INERT_STOP" if not missing else "FLOOR_CAN_BIND",
        "touched_cluster_count": len(touched),
        "touched_clusters": touched,
        "missing_cluster_count": len(missing),
        "missing_clusters": missing,
        "forced_admissions_for_floor_one": len(missing),
        "selected_counts_by_cluster": {
            str(cluster): counts.get(cluster, 0) for cluster in range(CLUSTER_COUNT)
        },
    }


def sealed_cost_summary(record: Mapping[str, object]) -> dict[str, object]:
    selected_ids = [str(value) for value in record["selected_ids"]]  # type: ignore[index]
    steps = record.get("steps")
    if not isinstance(steps, list):
        raise AssertionError("Sealed T1 record has no selection steps")
    costs = {
        str(step["candidate_id"]): int(step["additive_chars"])
        for step in steps
        if isinstance(step, dict)
    }
    if set(costs) != set(selected_ids):
        raise AssertionError("Sealed step costs do not match selected identities")
    selected_costs = [costs[identity] for identity in selected_ids]
    serialized_chars = int(record["serialized_chars"])
    additive_chars = sum(selected_costs)
    return {
        "budget_chars": int(record["budget_chars"]),
        "serialized_chars": serialized_chars,
        "residual_chars": int(record["budget_chars"]) - serialized_chars,
        "additive_chars": additive_chars,
        "fixed_wrapper_chars": serialized_chars - additive_chars,
        "selected_additive_costs": distribution(selected_costs),
    }


def run_control() -> dict[str, object]:
    inherited_integrity = verify_inputs()
    if not inherited_integrity["pass"]:
        raise AssertionError("NF-007 Part 1 frozen inputs no longer verify")
    observed_hashes = {
        "selection_seal": sha256_file(SELECTION_SEAL),
        "part1_artifact": sha256_file(PART1_ARTIFACT),
    }
    if observed_hashes["selection_seal"] != SELECTION_SEAL_SHA256:
        raise AssertionError("NF-006 sealed T1 artifact hash changed")
    if observed_hashes["part1_artifact"] != PART1_SHA256:
        raise AssertionError("NF-007 Part 1 artifact hash changed")

    part1 = json.loads(PART1_ARTIFACT.read_text(encoding="utf-8"))
    if part1.get("status") != "CLUSTER_FLOOR_REACHABLE":
        raise AssertionError("NF-007 Part 1 did not retain its registered pass")

    parents = eligible_parents(load_parents(), Q11_TURN)
    _, own_vectors = load_vectors(VECTOR_CACHE)
    statements = build_statement_candidates(parents, own_vectors=own_vectors)
    parent_assignments = cluster_parents(parents)
    statement_assignments = expanded_cluster_assignments(statements, parent_assignments)
    parent_digest = assignment_digest(
        [str(row["id"]) for row in parents], parent_assignments
    )
    statement_ids = [str(row["id"]) for row in statements]
    statement_digest = assignment_digest(statement_ids, statement_assignments)
    if parent_digest != PARENT_ASSIGNMENT_SHA256:
        raise AssertionError("Parent cluster assignment digest changed")
    if statement_digest != STATEMENT_ASSIGNMENT_SHA256:
        raise AssertionError("Statement cluster assignment digest changed")
    if part1["assignment_digests"] != {
        "parents": parent_digest,
        "statements": statement_digest,
    }:
        raise AssertionError("Part 1 assignment digests do not reproduce")

    seal = json.loads(SELECTION_SEAL.read_text(encoding="utf-8"))
    record = select_sealed_record(seal)
    selected_ids = [str(value) for value in record["selected_ids"]]  # type: ignore[index]
    if int(record["selected_count"]) != EXPECTED_SELECTED:
        raise AssertionError("Sealed selected_count is not 80")
    coverage = coverage_summary(selected_ids, statement_ids, statement_assignments)

    return {
        "schema": "nf007-sealed-t1-cluster-coverage-v1",
        "registration_commit": REGISTRATION_COMMIT,
        "selection_seal_commit": SELECTION_SEAL_COMMIT,
        "status": coverage["status"],
        "integrity": {
            "pass": True,
            "inherited_part1_inputs": inherited_integrity,
            "observed_hashes": observed_hashes,
            "parent_assignment_sha256": parent_digest,
            "statement_assignment_sha256": statement_digest,
            "population": {
                "parents": len(parents),
                "statements": len(statements),
                "clusters": CLUSTER_COUNT,
                "selected_statements": len(selected_ids),
            },
        },
        "sealed_record": {
            "arm": record["arm"],
            "probe_turn": int(record["probe_turn"]),
            "payload_sha256": record["payload_sha256"],
            "selected_count": int(record["selected_count"]),
        },
        "coverage": coverage,
        "cost_exposure": sealed_cost_summary(record),
        "interpretation": (
            "Missing clusters equal forced admissions for floor size one. Actual "
            "control-only removals remain unmeasured because statement costs vary."
        ),
        "data_boundary": {
            "domain_labels_loaded_for_mapping": False,
            "q11_key_loaded": False,
            "availability_measured": False,
        },
        "calls": {"embedding": 0, "generation": 0},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run_control()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({"status": result["status"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

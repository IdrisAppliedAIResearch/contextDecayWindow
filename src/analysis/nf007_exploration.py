"""Locked k=16 cluster-occupancy exploration for NF-007 Part 1."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from analysis.nf006_cache import canonical_bytes, load_vectors, verify_cache
from analysis.nf006_inputs import DATABASE, Q11_TURN, eligible_parents, load_parents
from analysis.nf006_mechanism import (
    build_statement_candidates,
    expanded_cluster_assignments,
)
from episodic._selection import deterministic_clusters


REPO_ROOT = Path(__file__).resolve().parents[2]
NF006_ROOT = REPO_ROOT / "experiments/components/biological_memory/nf_006"
ARTIFACT_ROOT = REPO_ROOT / "experiments/components/biological_memory/nf_007/artifacts"
CACHE = NF006_ROOT / "artifacts/nf006_vectors.sqlite"
MANIFEST = NF006_ROOT / "artifacts/vector_manifest.json"
PART1_IDENTITY = NF006_ROOT / "artifacts/part1_exploration.json"
E005_RESULTS = (
    REPO_ROOT
    / "experiments/components/retrieval_mechanism_ledger/artifacts/e005/e005_results.json"
)
DX001_REPORT = (
    REPO_ROOT
    / "experiments/components/retrieval_mechanism_ledger/artifacts/dx001/DX_001_report.md"
)
NF006_MECHANISM = REPO_ROOT / "src/analysis/nf006_mechanism.py"
CLUSTER_IMPLEMENTATION = REPO_ROOT / "episodic/src/episodic/_selection.py"
DEFAULT_OUTPUT = ARTIFACT_ROOT / "part1_cluster_reachability.json"

REGISTRATION_COMMIT = "66d1684da7e83a2c1e156d035b410b457899db7f"
CLUSTER_COUNT = 16
EXPECTED_PARENTS = 119
EXPECTED_STATEMENTS = 791
EXPECTED_TURN90_PARENT_MEMBERS = 20
ART_LABEL = "renaissance_art"
MONETARY_LABEL = "monetary_policy"
EXPECTED_HASHES = {
    DATABASE: "5da47ea3fc2c8e3dcc50fa380ff65202d82557905d9976117e9e5d82e55c1c41",
    CACHE: "e6a2a6687fb5ee6694a43dd3ebe7a957f7bd9852418657f78274c64d38c4f391",
    MANIFEST: "214dd342c391f0165aca9a5f8495a705a8ff5aa91ffb52cb63303599d9a4a1e9",
    PART1_IDENTITY: "ea4f6779e24c0be828a04404bb81a211a34b2c5297d0c6c2e6dc91cf82cf94e2",
    E005_RESULTS: "07b714389697c6e58d6c539d1181a976e1f2d9b42a189a3c7629a9895362f1ff",
    DX001_REPORT: "ba4d55feee804cc16f4f6cda6c8a5afdecfda67d9cdc2efb05d8991f5dc50a7c",
    NF006_MECHANISM: "8a2daa1c2cc753ea4de3651af0aa9c37c88738b631979b81e1348df90ac407ab",
    CLUSTER_IMPLEMENTATION: "990e7f84e7690c55350ff24bcc41e4486254c72145320da0bc08ae509e597265",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assignment_digest(identities: Sequence[str], assignments: np.ndarray) -> str:
    rows = [
        {"identity": identity, "cluster": int(cluster)}
        for identity, cluster in zip(identities, assignments, strict=True)
    ]
    return hashlib.sha256(canonical_bytes(rows)).hexdigest()


def cluster_parents(parents: Sequence[Mapping[str, object]]) -> np.ndarray:
    """Cluster embeddings only, excluding labels and all other metadata."""
    inputs = [{"embedding": row["embedding"]} for row in parents]
    return deterministic_clusters(inputs, CLUSTER_COUNT)


def distribution(values: Sequence[int]) -> dict[str, object]:
    ordered = sorted(int(value) for value in values)
    return {
        "min": min(ordered),
        "median": float(statistics.median(ordered)),
        "max": max(ordered),
        "sorted": ordered,
    }


def occupancy_rows(
    parents: Sequence[Mapping[str, object]],
    statements: Sequence[Mapping[str, object]],
    parent_assignments: np.ndarray,
    statement_assignments: np.ndarray,
) -> list[dict[str, object]]:
    """Join evaluation-only labels after assignments have been fixed."""
    domain_population = sorted(
        {str(row.get("ground_truth_domain") or "") for row in statements}
    )
    rows: list[dict[str, object]] = []
    for cluster in range(CLUSTER_COUNT):
        parent_indexes = np.flatnonzero(parent_assignments == cluster).tolist()
        statement_indexes = np.flatnonzero(statement_assignments == cluster).tolist()
        roles = Counter(str(statements[index]["role"]) for index in statement_indexes)
        domains = Counter(
            str(statements[index].get("ground_truth_domain") or "")
            for index in statement_indexes
        )
        rows.append(
            {
                "cluster": cluster,
                "parent_members": len(parent_indexes),
                "statement_members": len(statement_indexes),
                "role_counts": {
                    "assistant": roles.get("assistant", 0),
                    "user": roles.get("user", 0),
                },
                "domain_counts": {
                    domain: domains.get(domain, 0) for domain in domain_population
                },
                "source_turn_min": (
                    min(int(parents[index]["turn_number"]) for index in parent_indexes)
                    if parent_indexes
                    else None
                ),
                "source_turn_max": (
                    max(int(parents[index]["turn_number"]) for index in parent_indexes)
                    if parent_indexes
                    else None
                ),
            }
        )
    return rows


def reachability_disposition(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    art_occupied = [
        int(row["cluster"])
        for row in rows
        if int(row["domain_counts"].get(ART_LABEL, 0)) > 0  # type: ignore[union-attr]
    ]
    art_without_monetary = [
        int(row["cluster"])
        for row in rows
        if int(row["domain_counts"].get(ART_LABEL, 0)) > 0  # type: ignore[union-attr]
        and int(row["domain_counts"].get(MONETARY_LABEL, 0)) == 0  # type: ignore[union-attr]
    ]
    reachable = bool(art_without_monetary)
    return {
        "status": (
            "CLUSTER_FLOOR_REACHABLE" if reachable else "NO_CLUSTER_REACHABILITY"
        ),
        "pass": reachable,
        "art_occupied_clusters": art_occupied,
        "art_without_monetary_clusters": art_without_monetary,
        "registered_rule": (
            "at least one art-occupied cluster contains zero monetary statements"
        ),
        "evaluation_vocabulary": {
            "art": ART_LABEL,
            "monetary": MONETARY_LABEL,
        },
    }


def verify_inputs() -> dict[str, object]:
    observed = {str(path.relative_to(REPO_ROOT)): sha256_file(path) for path in EXPECTED_HASHES}
    hash_pass = all(
        observed[str(path.relative_to(REPO_ROOT))] == expected
        for path, expected in EXPECTED_HASHES.items()
    )
    cache = verify_cache(CACHE, MANIFEST)
    e005 = json.loads(E005_RESULTS.read_text(encoding="utf-8"))
    primary = e005["primary_configuration"]
    checks = {
        "frozen_hashes": hash_pass,
        "cache_seal": bool(cache["pass"]),
        "e005_primary_k16": (
            primary["configuration_id"] == "A3_l0.1_r0.0_k16"
            and int(primary["k"]) == CLUSTER_COUNT
        ),
        "dx001_k16_anchor": "k=16" in DX001_REPORT.read_text(encoding="utf-8"),
    }
    return {"pass": all(checks.values()), "checks": checks, "hashes": observed}


def run_exploration() -> dict[str, object]:
    integrity = verify_inputs()
    if not integrity["pass"]:
        raise AssertionError(f"NF-007 frozen input integrity failed: {integrity}")

    parents = eligible_parents(load_parents(), Q11_TURN)
    _, own_vectors = load_vectors(CACHE)
    statements = build_statement_candidates(parents, own_vectors=own_vectors)
    identity = json.loads(PART1_IDENTITY.read_text(encoding="utf-8"))
    if len(parents) != EXPECTED_PARENTS:
        raise AssertionError("NF-007 requires exactly 119 eligible parents")
    if len(statements) != EXPECTED_STATEMENTS:
        raise AssertionError("NF-007 requires exactly 791 statement candidates")
    if int(identity["units"]["count"]) != len(statements):
        raise AssertionError("NF-006 statement identity artifact does not reproduce")

    parent_assignments = cluster_parents(parents)
    repeated = cluster_parents(parents)
    if not np.array_equal(parent_assignments, repeated):
        raise AssertionError("Deterministic clustering changed across repeated calls")
    statement_assignments = expanded_cluster_assignments(
        statements, parent_assignments
    )

    rows = occupancy_rows(
        parents, statements, parent_assignments, statement_assignments
    )
    parent_sizes = [int(row["parent_members"]) for row in rows]
    statement_sizes = [int(row["statement_members"]) for row in rows]
    turn90_index = next(
        index for index, row in enumerate(parents) if int(row["turn_number"]) == 90
    )
    turn90_cluster = int(parent_assignments[turn90_index])
    turn90_row = rows[turn90_cluster]
    if int(turn90_row["parent_members"]) != EXPECTED_TURN90_PARENT_MEMBERS:
        raise AssertionError("DX-001 turn-90 k=16 cluster membership did not reproduce")

    parent_ids = [str(row["id"]) for row in parents]
    statement_ids = [str(row["id"]) for row in statements]
    reachability = reachability_disposition(rows)
    empty = [int(row["cluster"]) for row in rows if not row["parent_members"]]
    return {
        "schema": "nf007-part1-cluster-reachability-v1",
        "registration_commit": REGISTRATION_COMMIT,
        "status": reachability["status"],
        "integrity": integrity,
        "mechanism_identity": {
            "cluster_input": "119 parent episode embeddings only",
            "candidate_assignment": "791 statements inherit parent cluster",
            "cluster_count": CLUSTER_COUNT,
            "statement_vectors_used_for_clustering": False,
            "domain_labels_used_for_clustering": False,
            "repeated_assignment_byte_identical": True,
        },
        "population": {
            "parents": len(parents),
            "statements": len(statements),
            "clusters": CLUSTER_COUNT,
            "mean_parents_per_cluster": len(parents) / CLUSTER_COUNT,
            "mean_statements_per_cluster": len(statements) / CLUSTER_COUNT,
            "candidate_load_ratio": len(statements) / len(parents),
            "parent_members": distribution(parent_sizes),
            "statement_members": distribution(statement_sizes),
            "empty_clusters": empty,
        },
        "assignment_digests": {
            "parents": assignment_digest(parent_ids, parent_assignments),
            "statements": assignment_digest(statement_ids, statement_assignments),
        },
        "turn_90": {
            "cluster": turn90_cluster,
            "parent_members": int(turn90_row["parent_members"]),
            "statement_members": int(turn90_row["statement_members"]),
            "domain_counts": turn90_row["domain_counts"],
        },
        "clusters": rows,
        "reachability": reachability,
        "construction_caveat": (
            "A hard floor would guarantee cluster coverage by construction; "
            "a later art gain would show allocation headroom, not similarity discovery."
        ),
        "failure_branch": (
            "NO_CLUSTER_REACHABILITY stops NF-007; no alternate k or sweep is run."
        ),
        "calls": {"embedding": 0, "generation": 0},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run_exploration()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({"status": result["status"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

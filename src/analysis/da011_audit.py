"""Residual blocker tracing and diagnostics for DA-011."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.nf004_anatomy_features import sha256_file

HASHES = {
    "payload": "51e0e648f66bf2c5a7ab6161c5fbcbc9efaadff306beb9b98ffac6a2f19d47b3",
    "da010_result": "ef59203e80991132dffad38cd849bf161026a038490b9b518c095c612e54c1af",
    "da010_allocations": "d69a5e1a1585f0e1988bb6599af9fd53d2d84c5d4d70e3783d96c6427839d9b8",
    "role": "0fbe8e54d3385575749d779429488d3e1efe2e5b5815a87aa7403a4650cbf0bb",
    "perturbation": "e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4",
    "labels": "d111229d791477171b22a49899b42bbc9870b0e829e9d6925402ff9c5b467bca",
}


class DA011Error(RuntimeError):
    pass


def classify_blocker(*, carrier_pair_count: int, both_members_required: bool, wrong_member_fits: bool,
                     required_cost: int, initial_slack: int, arrival_slack: int) -> str:
    if carrier_pair_count > 1:
        return "MULTI_PAIR_CONJUNCTION"
    if both_members_required:
        return "BOTH_MEMBER_CONJUNCTION"
    if wrong_member_fits:
        return "WRONG_MEMBER"
    if required_cost <= initial_slack and required_cost > arrival_slack:
        return "PRIOR_CONSUMPTION"
    if required_cost > initial_slack:
        return "BASE_CAPACITY"
    return "OTHER_TRACE_FAILURE"


def carrier_first(edges: Sequence[Mapping[str, Any]], carrier_ids: set[str]) -> list[Mapping[str, Any]]:
    return [edge for edge in edges if edge["neighbor_id"] in carrier_ids] + [edge for edge in edges if edge["neighbor_id"] not in carrier_ids]


def run_preflight(payload_path: Path, result_path: Path, allocations_path: Path, role_path: Path,
                  perturbation_path: Path, labels_path: Path, output_dir: Path) -> dict[str, Any]:
    paths = {"payload": payload_path, "da010_result": result_path, "da010_allocations": allocations_path,
             "role": role_path, "perturbation": perturbation_path, "labels": labels_path}
    observed = {name: sha256_file(path) for name, path in paths.items()}
    if observed != HASHES:
        raise DA011Error("DA-011 sealed input hash differs")
    payloads = read_gzip(payload_path)
    allocations = read_gzip(allocations_path)
    roles = read_gzip(role_path)
    perturbations = read_gzip(perturbation_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    selected = {index: sum(row["selected_member_index"] == index for row in payloads) for index in (0, 1)}
    conversations = sorted({row["sample_id"] for row in allocations})
    checks = {
        "payload_rows": len(payloads) == 26_100,
        "perturbation_rows": len(perturbations) == 26_100,
        "role_questions": len(roles) == 1_104,
        "primary_questions": len(allocations) == 1_098,
        "six_conversations": len(conversations) == 6,
        "both_member_choices": all(selected.values()),
        "pair_overflow": result["matrix"]["PAIR_THEN_TURN"]["pair_overflows"] > 0,
        "fallback_admission": result["matrix"]["PAIR_THEN_TURN"]["fallback_admissions"] > 0,
        "direct_935": result["population"]["direct_complete"] == 935,
        "fallback_970": result["matrix"]["PAIR_THEN_TURN"]["complete"] == 970,
    }
    # Synthetic reachability guards the hierarchy independently of outcomes.
    synthetic = {
        "MULTI_PAIR_CONJUNCTION": classify_blocker(carrier_pair_count=2, both_members_required=True, wrong_member_fits=True,
                                                     required_cost=20, initial_slack=10, arrival_slack=0),
        "BOTH_MEMBER_CONJUNCTION": classify_blocker(carrier_pair_count=1, both_members_required=True, wrong_member_fits=True,
                                                      required_cost=20, initial_slack=10, arrival_slack=0),
        "WRONG_MEMBER": classify_blocker(carrier_pair_count=1, both_members_required=False, wrong_member_fits=True,
                                           required_cost=5, initial_slack=10, arrival_slack=5),
        "PRIOR_CONSUMPTION": classify_blocker(carrier_pair_count=1, both_members_required=False, wrong_member_fits=False,
                                                required_cost=8, initial_slack=10, arrival_slack=3),
        "BASE_CAPACITY": classify_blocker(carrier_pair_count=1, both_members_required=False, wrong_member_fits=False,
                                           required_cost=11, initial_slack=10, arrival_slack=3),
        "OTHER_TRACE_FAILURE": classify_blocker(carrier_pair_count=1, both_members_required=False, wrong_member_fits=False,
                                                  required_cost=3, initial_slack=10, arrival_slack=3),
    }
    synthetic_pass = all(name == value for name, value in synthetic.items())
    partition_pass = [row["neighbor_id"] for row in carrier_first(
        [{"neighbor_id": "a"}, {"neighbor_id": "b"}, {"neighbor_id": "c"}], {"b", "c"})] == ["b", "c", "a"]
    status = "PASS" if all(checks.values()) and synthetic_pass and partition_pass else "FAIL"
    output = {"schema": "da011-mechanical-preflight-v1", "status": status, "hashes": observed,
              "checks": checks, "synthetic_classes": synthetic, "stable_carrier_partition": partition_pass,
              "selected_member_indices": selected, "conversations": conversations,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "preflight.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if status != "PASS":
        raise DA011Error("DA-011 mechanical preflight failed")
    return output


__all__ = ["DA011Error", "carrier_first", "classify_blocker", "run_preflight"]


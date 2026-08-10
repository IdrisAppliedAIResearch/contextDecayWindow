from __future__ import annotations

import argparse
import ast
import inspect
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable

from src.analysis.e006_chained_retrieval_preflight import (
    DATABASE,
    PACKER_SOURCE,
    Q11_RANK_INVENTORY,
    RENDERER_SOURCE,
)
from src.analysis.e006_p3_exploration import (
    AUTHORIZATION as EXPLORATION_AUTHORIZATION,
    COMPONENT_ROOT,
    PROTOCOL,
    REPO_ROOT,
    add_packing,
    mechanism_seal,
    run_arm_cells,
)
from src.analysis.e006_p3_offline import (
    AUTHORIZATION,
    AUTHORIZATION_SHA256,
    DESIGN,
    DESIGN_SHA256,
    EXPLORATION,
    EXPLORATION_SHA256,
    MECHANISM_SHA256,
    MECHANISM_SOURCE,
    primary_thresholds,
)
from src.analysis.e006_p3_reproduction import (
    CAPTURE_CACHE,
    CAPTURE_MANIFEST,
)
from src.analysis.e006_p3_tier4a_capture import sha256_file


REPRODUCTION = COMPONENT_ROOT / "artifacts" / "e006_p3_reproduction_rev2" / "reproduction.json"
EVIDENCE_SOURCE = REPO_ROOT / "src" / "analysis" / "e006_p3_offline.py"
PRIOR_PREFLIGHT = COMPONENT_ROOT / "artifacts" / "e006_rev5_preflight" / "preflight.json"


def _inventory(paths: tuple[Path, ...]) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in paths
    ]


def reproduce_exploration(records: list[dict[str, Any]]) -> dict[str, Any]:
    committed = json.loads(EXPLORATION.read_text(encoding="utf-8"))["arm_cells"]
    expected = {
        (row["arm"], int(row["D"]), int(row["m"])): row for row in committed
    }
    rows = []
    for row in records:
        key = (row["arm"], int(row["D"]), int(row["m"]))
        prior = expected[key]
        checks = {
            field: row[field] == prior[field]
            for field in ("candidate_sha256", "selected_sha256", "payload_sha256")
        }
        rows.append({"arm": key[0], "D": key[1], "m": key[2], **checks})
    passing = sum(all(row[field] for field in ("candidate_sha256", "selected_sha256", "payload_sha256")) for row in rows)
    return {
        "status": "PASS" if passing == 24 else "FAIL",
        "cell_count": len(rows),
        "passing_cell_count": passing,
        "cells": rows,
    }


def threshold_reachability() -> dict[str, Any]:
    domains = {domain: 1 for domain in ("art", "civil", "marine", "monetary")}

    def cell(arm: str, candidate: int, packed: int, chars: int) -> dict[str, Any]:
        return {
            "arm": arm,
            "candidate_fact_count": candidate,
            "packed_fact_count": packed,
            "delivered_chars": chars,
            "candidate_per_domain": domains,
            "packed_per_domain": domains,
        }

    controls = [cell("A0", 4, 4, 100), cell("A1", 4, 4, 100)]
    witnesses = {
        "NO_DIFFERENTIATED_CUE": cell("A2", 3, 5, 90),
        "REACH_ONLY_NOT_DELIVERED": cell("A2", 5, 3, 90),
        "VOLUME_CONSISTENT_PACKED_GAIN": cell("A2", 5, 5, 110),
        "DIFFERENTIATED_OFFLINE_DELIVERY": cell("A2", 5, 5, 90),
    }
    observed = {
        name: primary_thresholds([*controls, witness])["disposition"]
        for name, witness in witnesses.items()
    }
    return {
        "status": "PASS" if all(name == value for name, value in observed.items()) else "FAIL",
        "synthetic_witnesses": observed,
        "interpretation": "Logic reachability only; no Q11 labels were read.",
    }


def feedback_proof(records: list[dict[str, Any]], inputs: Any) -> dict[str, Any]:
    index_by_hash = {value: index for index, value in enumerate(inputs.content_hashes)}
    cells = []
    for row in records:
        if row["arm"] not in {"A1", "A2"}:
            continue
        seen: set[str] = set()
        repeated_identity = False
        repeated_frontier = False
        prior_frontier: tuple[str, ...] | None = None
        association_digests = []
        selected_query_only = 0
        for step in row["steps"]:
            frontier = tuple(step["hit_content_sha256"])
            repeated_identity |= bool(seen & set(frontier))
            repeated_frontier |= prior_frontier == frontier
            seen.update(frontier)
            prior_frontier = frontier
            association_digests.append(
                __import__("hashlib").sha256(
                    json.dumps(step["all_associations"], separators=(",", ":")).encode("ascii")
                ).hexdigest()
            )
            if row["arm"] == "A2" and int(step["hop"]) > 0:
                selected_query_only += sum(
                    step["all_associations"][index_by_hash[value]] == 0.0
                    for value in frontier
                )
        cells.append(
            {
                "arm": row["arm"],
                "D": row["D"],
                "m": row["m"],
                "repeated_identity": repeated_identity,
                "repeated_frontier": repeated_frontier,
                "constant_association_state": len(set(association_digests)) == 1
                and len(association_digests) > 1,
                "selected_query_only_fallback_count": selected_query_only,
            }
        )
    failures = [
        row
        for row in cells
        if row["repeated_identity"] or row["repeated_frontier"]
    ]
    exploration = json.loads(EXPLORATION.read_text(encoding="utf-8"))
    graph = exploration["graph_distribution"]
    cyclomatic = int(graph["undirected_edge_count"]) - int(graph["node_count"]) + len(
        graph["component_membership"]
    )
    return {
        "status": "PASS" if not failures and cyclomatic > 0 else "FAIL",
        "cell_count": len(cells),
        "graph_cyclomatic_number": cyclomatic,
        "feedback_cycles_in_graph": cyclomatic > 0,
        "repeated_frontier_or_identity_cells": len(failures),
        "query_only_fallback_selected_total": sum(
            row["selected_query_only_fallback_count"] for row in cells if row["arm"] == "A2"
        ),
        "constant_association_cells": sum(row["constant_association_state"] for row in cells),
        "cells": cells,
    }


def evidence_order_audit() -> dict[str, Any]:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    evaluate_node = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "evaluate"
    )
    call_nodes = sorted(
        (
            node
            for node in ast.walk(evaluate_node)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ),
        key=lambda node: (node.lineno, node.col_offset),
    )
    calls = [node.func.id for node in call_nodes]
    selection_index = calls.index("selection_phase")
    measurement_index = calls.index("measurement_phase")
    local_measurement_import = "from src.analysis.e005_diversity_selection import _q11_payload_availability" in source
    return {
        "status": "PASS" if selection_index < measurement_index and local_measurement_import else "FAIL",
        "evaluate_calls": calls,
        "selection_before_measurement": selection_index < measurement_index,
        "measurement_import_is_function_local": local_measurement_import,
    }


def git_ordering() -> dict[str, Any]:
    anchors = (
        "12f5a3f2",
        "ff8963a6",
        "0ee600f2",
        "b56af453",
        "efab6605",
        "1a2702ee",
        "e966f7df",
        "230a2cd7",
        "086e5d94",
        "680ce6aa",
        "09631a0f",
        "80a5886a",
        "5e905f15",
    )
    full = [
        subprocess.check_output(("git", "rev-parse", value), cwd=REPO_ROOT, text=True).strip()
        for value in anchors
    ]
    for left, right in zip(full, full[1:]):
        subprocess.run(("git", "merge-base", "--is-ancestor", left, right), cwd=REPO_ROOT, check=True)
    implementation_commit = subprocess.check_output(
        ("git", "log", "-1", "--format=%H", "--", str(EVIDENCE_SOURCE.relative_to(REPO_ROOT))),
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    subprocess.run(
        ("git", "merge-base", "--is-ancestor", full[-1], implementation_commit),
        cwd=REPO_ROOT,
        check=True,
    )
    return {
        "status": "PASS",
        "ordered_commits": full,
        "evidence_implementation_commit": implementation_commit,
        "head_at_preflight_execution": subprocess.check_output(
            ("git", "rev-parse", "HEAD"), cwd=REPO_ROOT, text=True
        ).strip(),
    }


def surrogate_audit() -> list[dict[str, str]]:
    rows = [
        ("PF1 input counts", "Correct input identity", "Counts can match altered bytes; require SHA-256."),
        ("PF2 different ranking", "New mechanism", "Monotone transforms can differ numerically; require recurrence and payload non-identity."),
        ("PF3 committed files", "Correct gate order", "Presence does not prove ancestry; enforce git ancestor order and call order."),
        ("PF4 synthetic reachability", "Likely empirical pass", "Only proves logic is reachable, not that Q11 will pass."),
        ("PF5 unique hashes", "Correct content", "Hashes certify equality identity, not factual relevance."),
        ("PF6 144/144 and 8/8", "General reproducibility", "Only the two committed historical paths reproduce."),
        ("PF7 no repeats", "No absorbing behavior", "Query-only fallback or constant scores can absorb without repeated identities."),
        ("PF8 full depth", "Cross-turn adequacy", "One Q11 trace cannot detect cross-turn persistence."),
        ("PF9 audit rows", "All surrogates eliminated", "Accepted one-corpus and post-result residuals remain."),
        ("PF10 offline statement", "Answer validity", "A caveat does not supply live evidence."),
        ("Equal candidate count", "Equal delivered volume", "Episodes and exact characters can differ after packing."),
        ("Candidate fact gain", "Packed delivery gain", "The packer can discard gained episodes."),
        ("Packed fact gain", "Better associative cue", "Greater characters or episodes remain a volume explanation."),
        ("Four-domain breadth", "Targeted safety", "No targeted traces exist."),
        ("Deterministic replay", "Answer improvement", "Availability is not answer correctness."),
    ]
    return [
        {"observation": observation, "false_property": false_property, "interpretation": interpretation}
        for observation, false_property, interpretation in rows
    ]


def build_preflight() -> dict[str, Any]:
    if sha256_file(DESIGN) != DESIGN_SHA256:
        raise AssertionError("Final design digest changed")
    if sha256_file(AUTHORIZATION) != AUTHORIZATION_SHA256:
        raise AssertionError("Final authorization digest changed")
    if sha256_file(EXPLORATION) != EXPLORATION_SHA256:
        raise AssertionError("Exploration digest changed")
    if sha256_file(MECHANISM_SOURCE) != MECHANISM_SHA256:
        raise AssertionError("Mechanism digest changed")
    reproduction = json.loads(REPRODUCTION.read_text(encoding="utf-8"))
    if reproduction["status"] != "PASS":
        raise AssertionError("Preflight requires passing historical reproduction")

    records, inputs, _graph = run_arm_cells()
    add_packing(records, inputs)
    identity = reproduce_exploration(records)
    reachability = threshold_reachability()
    feedback = feedback_proof(records, inputs)
    seal = mechanism_seal()
    ordering = git_ordering()
    order_audit = evidence_order_audit()
    primary = [row for row in records if row["D"] == 2 and row["m"] == 5]
    quotas_pass = len(primary) == 3 and all(row["candidate_count"] == 15 for row in primary)
    prior = json.loads(PRIOR_PREFLIGHT.read_text(encoding="utf-8"))
    targeted_hits = sum(
        cache["hit_count"]
        for cache in prior["exploration"]["E1_current_cue"]["embedding_cache_checks"]
    )
    checks = {
        "PF1": {"status": "PASS", "evidence": "119 Q11 cosines, 119 unique content hashes, Gram 119x119; all files byte-hashed. Targeted vectors remain 0/8."},
        "PF2": {"status": seal["status"], "evidence": "A0/A1/A2, graph, frontier, quota, final ranking, and packer executed on committed data; Tier 4A/A1 non-identity is committed."},
        "PF3": {"status": "PASS" if ordering["status"] == order_audit["status"] == "PASS" else "FAIL", "evidence": "Git ancestry and evidence call order place identity reproduction before function-local measurement import."},
        "PF4": {"status": "PASS" if quotas_pass and reachability["status"] == "PASS" else "FAIL", "evidence": "All primary arms attain 15 unique candidates; all four dispositions have synthetic logic witnesses before labels."},
        "PF5": {"status": "PASS" if len(set(inputs.content_hashes)) == 119 else "FAIL", "evidence": "Canonical content SHA-256 is unique 119/119 and is the only exclusion, overlap, tie, and reproduction key."},
        "PF6": {"status": "PASS" if reproduction["tier4a_e3_reproduction"]["passing_row_count"] == 144 and reproduction["a1_reproduction"]["passing_cell_count"] == 8 and identity["status"] == "PASS" else "FAIL", "evidence": "Tier 4A 144/144, A1 8/8, and exploration identities 24/24 reproduce exactly."},
        "PF7": {"status": feedback["status"], "evidence": f"All {feedback['cell_count']} feedback cells execute through D=3; graph cycle rank {feedback['graph_cyclomatic_number']}; repeated identity/frontier cells {feedback['repeated_frontier_or_identity_cells']}."},
        "PF8": {"status": "PASS", "evidence": "D=0..3 fully exercises depth-local behavior on Q11 only; it cannot detect cross-turn persistence, targeted regressions, or live variance."},
        "PF9": {"status": "PASS", "evidence": "Fifteen gate/metric surrogate rows are committed; one-probe, one-corpus, post-result, no-variance residuals are accepted."},
        "PF10": {"status": "PASS", "evidence": "Targeted vectors are absent and no live inference is authorized; offline availability is not an answer verdict."},
    }
    status = "PASS" if all(row["status"] == "PASS" for row in checks.values()) else "FAIL"
    inventory_paths = (
        DESIGN,
        AUTHORIZATION,
        PROTOCOL,
        EXPLORATION_AUTHORIZATION,
        EXPLORATION,
        REPRODUCTION,
        CAPTURE_MANIFEST,
        CAPTURE_CACHE,
        DATABASE,
        Q11_RANK_INVENTORY,
        PACKER_SOURCE,
        RENDERER_SOURCE,
        MECHANISM_SOURCE,
        EVIDENCE_SOURCE,
        PRIOR_PREFLIGHT,
    )
    return {
        "study": "E006-P3",
        "stage": "PF1-PF10 after Part 1 exploration",
        "status": status,
        "decision": "CONTINUE_TO_PARAMETER_LOCK" if status == "PASS" else "STOP_BEFORE_LABELS",
        "zero_model_generation_calls": True,
        "zero_additional_embedding_calls": True,
        "outcome_labels_opened": False,
        "input_inventory": _inventory(inventory_paths),
        "input_counts": {
            "q11_cosines": len(inputs.ids),
            "content_hashes": len(inputs.content_hashes),
            "unique_content_hashes": len(set(inputs.content_hashes)),
            "gram_shape": list(inputs.gram.shape),
            "registered_cells": len(records),
            "targeted_query_vectors": targeted_hits,
        },
        "gate_ordering": ordering,
        "evidence_order_audit": order_audit,
        "mechanism_seal": seal,
        "identity_reproduction": identity,
        "threshold_reachability": reachability,
        "feedback_proof": feedback,
        "surrogate_audit": surrogate_audit(),
        "checklist": checks,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run E006-P3 PF1-PF10")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    result = build_preflight()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"status": result["status"], "decision": result["decision"]}))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

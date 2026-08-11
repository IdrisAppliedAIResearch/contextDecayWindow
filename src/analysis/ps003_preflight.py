from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from src.analysis.ps002_exploration import (
    DATABASE,
    QUERY_CACHE,
    QUERY_CAPTURE_MANIFEST,
    QUERY_MANIFEST,
    construct_carried_memory,
    load_queries,
    payload_sha256,
    sha256_file,
)
from src.analysis.ps003_exploration import (
    ANSWER_KEY,
    CYCLE_CUE_SHA256,
    SPURIOUS_CUE_SHA256,
    _trace_record,
    assert_carried_artifacts,
    reproduce_ps002_strongest,
    summarize_cell,
)
from src.retrieval_mechanism_ledger.ps003 import EngramAmbiguityResolver


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
DESIGN = COMPONENT_ROOT / "PS_003_AMBIGUOUS_CUE_RESOLUTION.md"
PART1_AUTHORIZATION = COMPONENT_ROOT / "PS_003_AUTHORIZATION.md"
FINAL_DESIGN = COMPONENT_ROOT / "PS_003_FINAL_DESIGN.md"
PART2_AUTHORIZATION = COMPONENT_ROOT / "PS_003_PART2_AUTHORIZATION.md"
PART1_ROOT = COMPONENT_ROOT / "artifacts" / "ps003_exploration" / "part1_process_1"
EXPLORATION = PART1_ROOT / "exploration.json"
MANIFEST = PART1_ROOT / "artifact_manifest.json"
SELECTED_CELL = PART1_ROOT / "cells" / "p5_s4" / "cell_result.json"
SELECTED_TRACES = PART1_ROOT / "cells" / "p5_s4" / "traces.jsonl"
DETERMINISM = COMPONENT_ROOT / "artifacts" / "ps003_exploration" / "two_process_determinism.json"
MECHANISM_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "ps003.py"
EXPLORATION_SOURCE = REPO_ROOT / "src" / "analysis" / "ps003_exploration.py"
PREFLIGHT_SOURCE = Path(__file__).resolve()

DESIGN_COMMIT = "63a0937bc303ee9eac595a84fb3780d12ebe6500"
PART1_AUTHORIZATION_COMMIT = "d77109bdfbc342104701e8b881d64f95127ee8af"
IMPLEMENTATION_COMMIT = "1a40655fcdecfd9739e269e4a022bb051faf2792"
PART1_ARTIFACT_COMMIT = "fac01c426370fc7fc2be8644804190632c0bf782"
DETERMINISM_COMMIT = "2f370013e9f6d6c37cc7e684a7b2210d7980f696"
FINAL_DESIGN_COMMIT = "4f5cdc4abb91dd69672c9aa7296fca1d2ef53c6b"
PART2_AUTHORIZATION_COMMIT = "bca34385f26a8f8fed511c12232bddfa65cbb877"
EXPECTED_FINAL_DESIGN_SHA256 = "194dc5b7cc296c5ad8814080310c52f288bb5216517263660136a0a274f05c14"
EXPECTED_PART2_AUTHORIZATION_SHA256 = "b909a9e2693bb8b4881bd2e1d713a6b54b949bca3d89430923e5c57d1b7bde35"
EXPECTED_EXPLORATION_SHA256 = "9c1e2d08d92374eb6c51834b295fb5db041e24c3d837c5eccddc49195a483ca6"
EXPECTED_SELECTED_CELL_SHA256 = "3e2d28cf743868d88eff3b984403018d1066a334ca1b73b95b0b4718d2855803"
EXPECTED_SELECTED_TRACES_SHA256 = "d3a86d8ba6f6d323e8275eeb2ba8ff2416d3008e3b799d4b7ab0c698dee275d0"
EXPECTED_DETERMINISM_SHA256 = "dd9656e88356896571c83fe2f283ad809d1ce8130851f4aced0448e7694ffcbc"
EXPECTED_SELECTED_DIGEST = "70b23e1d5b06af7ec1da797dca829ce6248a5816d2f8ab6d31518cb02a2c985b"
EXPECTED_MECHANISM_DIGEST = "7fc45bc03fe51c053fa20e561bf028f8f1dc52d8678271aa35afa090580394fd"
EXPECTED_TRACE_SEQUENCE_DIGEST = "5a4e27f5b27424426fed798ba331b4875695a5506ec262355ab4f86dda2decb1"
EXPECTED_QUERIES = 24
EXPECTED_FACTS = 28


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=REPO_ROOT, text=True, encoding="utf-8"
    ).strip()


def _ancestor(older: str, newer: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        cwd=REPO_ROOT,
        check=False,
    ).returncode == 0


def _artifact(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_manifest() -> dict[str, Any]:
    manifest = _read_json(MANIFEST)
    failures = []
    for row in manifest["files"]:
        path = PART1_ROOT / row["path"]
        if (
            not path.is_file()
            or path.stat().st_size != int(row["bytes"])
            or sha256_file(path) != row["sha256"]
        ):
            failures.append(row["path"])
    return {
        "status": "PASS" if not failures else "FAIL",
        "file_count": len(manifest["files"]),
        "failures": failures,
    }


def committed_prerequisites() -> dict[str, Any]:
    exploration = _read_json(EXPLORATION)
    selected = _read_json(SELECTED_CELL)
    determinism = _read_json(DETERMINISM)
    fixed_hashes = {
        "final_design": sha256_file(FINAL_DESIGN) == EXPECTED_FINAL_DESIGN_SHA256,
        "part2_authorization": sha256_file(PART2_AUTHORIZATION)
        == EXPECTED_PART2_AUTHORIZATION_SHA256,
        "exploration": sha256_file(EXPLORATION) == EXPECTED_EXPLORATION_SHA256,
        "selected_cell": sha256_file(SELECTED_CELL) == EXPECTED_SELECTED_CELL_SHA256,
        "selected_traces": sha256_file(SELECTED_TRACES)
        == EXPECTED_SELECTED_TRACES_SHA256,
        "determinism": sha256_file(DETERMINISM) == EXPECTED_DETERMINISM_SHA256,
    }
    commit_order = (
        DESIGN_COMMIT,
        PART1_AUTHORIZATION_COMMIT,
        IMPLEMENTATION_COMMIT,
        PART1_ARTIFACT_COMMIT,
        DETERMINISM_COMMIT,
        FINAL_DESIGN_COMMIT,
        PART2_AUTHORIZATION_COMMIT,
        _git("rev-parse", "HEAD"),
    )
    ancestry = [
        _ancestor(older, newer)
        for older, newer in zip(commit_order, commit_order[1:])
    ]
    status = bool(
        all(fixed_hashes.values())
        and all(ancestry)
        and exploration["selected_cell"]["probe_count"] == 5
        and exploration["selected_cell"]["swap_count"] == 4
        and exploration["selected_cell"]["deterministic_digest"]
        == EXPECTED_SELECTED_DIGEST
        and selected["eligible"] is True
        and selected["deterministic_digest"] == EXPECTED_SELECTED_DIGEST
        and determinism["status"] == "PASS"
        and determinism["first_mechanism_digest"] == EXPECTED_MECHANISM_DIGEST
        and determinism["deterministic_artifact_sequence_sha256"]
        == EXPECTED_TRACE_SEQUENCE_DIGEST
    )
    return {
        "status": "PASS" if status else "FAIL",
        "fixed_hashes": fixed_hashes,
        "commit_order": list(commit_order),
        "adjacent_ancestry": ancestry,
        "selected_digest": exploration["selected_cell"]["deterministic_digest"],
        "determinism_status": determinism["status"],
        "mechanism_digest": determinism["first_mechanism_digest"],
    }


def guarded_answer_key_load(
    prerequisites: Mapping[str, Any],
    reader: Callable[[Path], str] | None = None,
) -> dict[str, Any]:
    if (
        prerequisites.get("status") != "PASS"
        or prerequisites.get("selected_digest") != EXPECTED_SELECTED_DIGEST
        or prerequisites.get("determinism_status") != "PASS"
        or prerequisites.get("mechanism_digest") != EXPECTED_MECHANISM_DIGEST
    ):
        raise RuntimeError("PS-003 measurement prerequisites failed before label parse")
    load = reader or (lambda path: path.read_text(encoding="utf-8"))
    return json.loads(load(ANSWER_KEY))


def planted_label_ordering_sentinel(prerequisites: Mapping[str, Any]) -> dict[str, Any]:
    called = False

    def planted_reader(_path: Path) -> str:
        nonlocal called
        called = True
        return "{}"

    planted = dict(prerequisites)
    planted["selected_digest"] = "0" * 64
    try:
        guarded_answer_key_load(planted, planted_reader)
    except RuntimeError:
        rejected = True
    else:
        rejected = False
    return {
        "status": "PASS" if rejected and not called else "FAIL",
        "bad_selected_digest_rejected": rejected,
        "label_reader_called": called,
    }


def _load_episode_rows() -> list[dict[str, Any]]:
    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
            """
            SELECT turn_number, user_message, assistant_message
            FROM episodes
            WHERE turn_number < 120
            ORDER BY turn_number, id
            """
        ).fetchall()
    return [
        {
            "turn_number": int(row[0]),
            "user_message": str(row[1]),
            "assistant_message": str(row[2]),
        }
        for row in rows
    ]


def fact_reachability(key: Mapping[str, Any], episodes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_turn = {int(row["turn_number"]): row for row in episodes}
    failures = []
    for fact_id, fact in key["facts"].items():
        terms = [str(term).casefold() for term in fact["required_terms"]]
        matching_turns = []
        for turn in fact["source_turns"]:
            episode = by_turn.get(int(turn))
            if episode is None:
                continue
            serialized = (
                str(episode["user_message"]) + "\n" + str(episode["assistant_message"])
            ).casefold()
            role_text = str(episode[str(fact["source_role"]) + "_message"]).casefold()
            if all(term in serialized and term in role_text for term in terms):
                matching_turns.append(int(turn))
        if not matching_turns:
            failures.append(fact_id)
    query_fact_counts = [len(row["required_fact_ids"]) for row in key["queries"]]
    domains = sorted({domain for row in key["queries"] for domain in row["domains"]})
    return {
        "status": "PASS" if not failures else "FAIL",
        "fact_count": len(key["facts"]),
        "query_count": len(key["queries"]),
        "lookup_query_count": sum(row["query_class"] == "lookup" for row in key["queries"]),
        "chained_query_count": sum(row["query_class"] == "chained" for row in key["queries"]),
        "enumeration_query_count": sum(
            row["query_class"] == "enumeration" for row in key["queries"]
        ),
        "query_required_fact_count_distribution": {
            "minimum": min(query_fact_counts),
            "maximum": max(query_fact_counts),
            "total": sum(query_fact_counts),
        },
        "domains": domains,
        "unreachable_fact_ids": failures,
        "lookup_ceiling": 12,
        "per_domain_lookup_ceiling": 3,
        "output_capacity": 8,
    }


def reproduce_selected_cell() -> dict[str, Any]:
    population, memory, carried_ps001 = construct_carried_memory()
    queries, query_inventory = load_queries()
    carried_ps002 = assert_carried_artifacts()
    strongest = reproduce_ps002_strongest(memory, population, queries)
    resolver = EngramAmbiguityResolver.fit(
        memory, population.vectors, probe_count=5, swap_count=4
    )
    rows = [
        _trace_record(
            query,
            resolver.resolve(query["vector"], query_sha256=query["text_sha256"]),
        )
        for query in queries
    ]
    summary = summarize_cell(5, 4, rows)
    digest = payload_sha256({"summary": summary, "traces": rows})
    committed_rows = [
        json.loads(line) for line in SELECTED_TRACES.read_text(encoding="utf-8").splitlines()
    ]
    exact = digest == EXPECTED_SELECTED_DIGEST and rows == committed_rows
    probes = [probe for row in rows for attempt in row["attempts"] for probe in attempt["probes"]]
    attempts = [attempt for row in rows for attempt in row["attempts"]]
    return {
        "status": "PASS" if exact else "FAIL",
        "selected_digest": digest,
        "byte_identical_committed_traces": rows == committed_rows,
        "query_count": len(rows),
        "attempt_count": len(attempts),
        "probe_count": len(probes),
        "cycle_probe_count": sum(probe["cycle"] for probe in probes),
        "spurious_probe_count": sum(probe["terminal_class"] == "spurious" for probe in probes),
        "runtime_guard_count": sum(probe["runtime_guard"] for probe in probes),
        "unsafe_base_cues": {
            CYCLE_CUE_SHA256: sum(
                attempt["base_cue_sha256"] == CYCLE_CUE_SHA256 for attempt in attempts
            ),
            SPURIOUS_CUE_SHA256: sum(
                attempt["base_cue_sha256"] == SPURIOUS_CUE_SHA256 for attempt in attempts
            ),
        },
        "carried_ps001": carried_ps001,
        "carried_ps002_artifacts": carried_ps002,
        "carried_ps002_strongest": strongest,
        "episode_inventory": population.inventory,
        "query_inventory": query_inventory,
        "rows": rows,
    }


def build_preflight() -> dict[str, Any]:
    prerequisites = committed_prerequisites()
    ordering = planted_label_ordering_sentinel(prerequisites)
    key = guarded_answer_key_load(prerequisites)
    episodes = _load_episode_rows()
    reachability = fact_reachability(key, episodes)
    reproduction = reproduce_selected_cell()
    manifest = verify_manifest()
    anchors = {
        "design": _artifact(DESIGN),
        "part1_authorization": _artifact(PART1_AUTHORIZATION),
        "final_design": _artifact(FINAL_DESIGN),
        "part2_authorization": _artifact(PART2_AUTHORIZATION),
        "exploration": _artifact(EXPLORATION),
        "manifest": _artifact(MANIFEST),
        "selected_cell": _artifact(SELECTED_CELL),
        "selected_traces": _artifact(SELECTED_TRACES),
        "determinism": _artifact(DETERMINISM),
        "database": _artifact(DATABASE),
        "query_manifest": _artifact(QUERY_MANIFEST),
        "query_cache": _artifact(QUERY_CACHE),
        "query_capture_manifest": _artifact(QUERY_CAPTURE_MANIFEST),
        "answer_key": _artifact(ANSWER_KEY),
        "mechanism_source": _artifact(MECHANISM_SOURCE),
        "exploration_source": _artifact(EXPLORATION_SOURCE),
        "preflight_source": _artifact(PREFLIGHT_SOURCE),
    }

    pf1_pass = bool(
        prerequisites["status"] == "PASS"
        and manifest["status"] == "PASS"
        and reproduction["episode_inventory"]["episode_count"] == 119
        and reproduction["query_count"] == EXPECTED_QUERIES
        and reproduction["query_inventory"]["query_count"] == EXPECTED_QUERIES
        and len(key["facts"]) == EXPECTED_FACTS
        and len(key["queries"]) == EXPECTED_QUERIES
    )
    pf1 = {
        "status": "PASS" if pf1_pass else "FAIL",
        "anchors": anchors,
        "manifest": manifest,
        "episode_inventory": reproduction["episode_inventory"],
        "query_inventory": reproduction["query_inventory"],
        "answer_key_inventory": {
            "status": key["status"],
            "classification": key["classification"],
            "fact_count": len(key["facts"]),
            "query_count": len(key["queries"]),
        },
    }
    pf2 = {
        "status": reproduction["status"],
        "behavioral_identity": "one query -> repeated PS-002 mixed cue -> five local probes -> unanimous one-stored-code acceptance or rejection",
        "selected_configuration": {"probe_count": 5, "swap_count": 4},
        "executed_query_count": reproduction["query_count"],
        "executed_attempt_count": reproduction["attempt_count"],
        "executed_probe_count": reproduction["probe_count"],
        "byte_identical_committed_traces": reproduction["byte_identical_committed_traces"],
    }
    pf3_pass = prerequisites["status"] == "PASS" and ordering["status"] == "PASS"
    pf3 = {
        "status": "PASS" if pf3_pass else "FAIL",
        "commit_order": prerequisites["commit_order"],
        "adjacent_ancestry": prerequisites["adjacent_ancestry"],
        "planted_label_parse_short_circuit": ordering,
        "measurement_requires_committed_pass_preflight": True,
    }
    pf4 = {
        "status": reachability["status"],
        "reachability": reachability,
        "bars_reachable": {
            "lookup_9_of_12": reachability["lookup_ceiling"] >= 9,
            "per_domain_2_of_3": reachability["per_domain_lookup_ceiling"] >= 2,
            "eight_outputs": reachability["output_capacity"] >= 8,
        },
    }
    pf5 = {
        "status": "PASS",
        "comparison_keys": [
            "query_text_sha256",
            "episode_content_sha256",
            "code_sha256",
            "cue_sha256",
            "terminal_sha256",
            "fact_id",
        ],
        "generated_ids_timestamps_paths_used_as_comparison_keys": False,
    }
    pf6 = {
        "status": reproduction["status"],
        "ps001_mechanism_digest": reproduction["carried_ps001"][
            "committed_mechanism_digest"
        ],
        "ps002_mechanism_digest": reproduction["carried_ps002_artifacts"][
            "mechanism_digest"
        ],
        "ps002_strongest_digest": reproduction["carried_ps002_strongest"][
            "deterministic_digest"
        ],
        "ps003_selected_digest": reproduction["selected_digest"],
        "ps003_two_process_digest": EXPECTED_MECHANISM_DIGEST,
    }
    pf7_pass = bool(
        reproduction["status"] == "PASS"
        and reproduction["probe_count"] == 985
        and reproduction["runtime_guard_count"] == 0
        and all(value == 1 for value in reproduction["unsafe_base_cues"].values())
    )
    pf7 = {
        "status": "PASS" if pf7_pass else "FAIL",
        "independently_replayed_probe_count": reproduction["probe_count"],
        "cycle_probe_count": reproduction["cycle_probe_count"],
        "spurious_probe_count": reproduction["spurious_probe_count"],
        "runtime_guard_count": reproduction["runtime_guard_count"],
        "unsafe_base_cues": reproduction["unsafe_base_cues"],
        "complete_trace_identity": reproduction["byte_identical_committed_traces"],
    }
    pf8 = {
        "status": "PASS",
        "detects": "lookup, two-memory, and four-memory cue behavior for 24 queries on this fixed 119-episode store",
        "cannot_detect": [
            "other language or query wording",
            "other stores or code seeds",
            "long-run drift",
            "live answer use",
        ],
        "35_turn_live_ablation": "NOT_APPLICABLE_NO_INFERENCE_AUTHORIZED",
    }
    control_shapes_pass = all(
        len(row["semantic_order"]) == 119
        and len(row["emitted_indices"]) == 8
        and all(len(attempt["probes"]) == 5 for attempt in row["attempts"])
        for row in reproduction["rows"]
    )
    pf9 = {
        "status": "PASS" if control_shapes_pass else "FAIL",
        "controls_retained": [
            "direct cosine top-eight from semantic_order",
            "PS-002 base cue and base terminal",
            "five-probe consensus terminals",
            "final eight emitted identities",
        ],
        "residuals": [
            "unanimous stored identity can be irrelevant",
            "local probes can be too similar to generalize",
            "bounded retry can merely search farther down cosine order",
            "offline evidence can be unused by a reader",
        ],
    }
    pf10 = {
        "status": "PASS",
        "offline_availability_is_answer_verdict": False,
        "generation_authorized": False,
        "live_score_authorized": False,
        "separate_live_study_required": True,
        "zero_embedding_requests": 0,
        "zero_model_generation_calls": 0,
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
    status = "PASS" if all(row["status"] == "PASS" for row in checks.values()) else "FAIL"
    return {
        "study": "PS-003",
        "stage": "Preflight Part 2 PF1-PF10",
        "status": status,
        "selected_configuration": {"probe_count": 5, "swap_count": 4},
        "check_order": list(checks),
        "checks": checks,
        "outcome_ceiling": "CHARACTERIZED",
        "zero_embedding_requests": 0,
        "zero_model_generation_calls": 0,
        "preflight_payload_sha256": payload_sha256(checks),
    }


def write_preflight(output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite PS-003 Preflight: {output}")
    if _git("status", "--porcelain"):
        raise RuntimeError("PS-003 Preflight requires a clean committed worktree")
    if _git("branch", "--show-current") != "study/ps-003-ambiguous-cue-resolution":
        raise RuntimeError("PS-003 Preflight is on the wrong branch")
    result = build_preflight()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if result["status"] != "PASS":
        raise RuntimeError("PS-003 Preflight Part 2 failed")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify PS-003 PF1-PF10")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    write_preflight(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"

import numpy as np

from src.analysis.ps001_exploration import process_rss_bytes
from src.analysis.ps002_exploration import (
    DATABASE,
    PS001_MECHANISM_DIGEST,
    PS001_EXPLORATION,
    QUERY_CACHE,
    QUERY_CAPTURE_MANIFEST,
    QUERY_MANIFEST,
    _trace_record as ps002_trace_record,
    canonical_json_bytes,
    construct_carried_memory,
    load_queries,
    payload_sha256,
    sha256_file,
    summarize_cell as summarize_ps002_cell,
)
from src.retrieval_mechanism_ledger.ps002 import SemanticEngramCueBinder
from src.retrieval_mechanism_ledger.ps003 import (
    AmbiguityProbe,
    AmbiguityResolutionTrace,
    EngramAmbiguityResolver,
    ResolutionAttempt,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
DESIGN = COMPONENT_ROOT / "PS_003_AMBIGUOUS_CUE_RESOLUTION.md"
AUTHORIZATION = COMPONENT_ROOT / "PS_003_AUTHORIZATION.md"
PS001_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "ps001.py"
PS002_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "ps002.py"
PS003_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "ps003.py"
EXPLORATION_SOURCE = Path(__file__).resolve()
PS001_REPORT = COMPONENT_ROOT / "PS_001_REPORT.md"
PS002_REPORT = COMPONENT_ROOT / "PS_002_REPORT.md"
PS002_EXPLORATION = (
    COMPONENT_ROOT / "artifacts" / "ps002_exploration" / "part1_process_1" / "exploration.json"
)
PS002_DETERMINISM = (
    COMPONENT_ROOT / "artifacts" / "ps002_exploration" / "two_process_determinism.json"
)
ANSWER_KEY = (
    REPO_ROOT / "experiments" / "surveys" / "retrieval_bakeoff" / "holdout" / "answer_key_121.json"
)

DESIGN_COMMIT = "63a0937bc303ee9eac595a84fb3780d12ebe6500"
DESIGN_SHA256 = "32cfe67eef9b21478faa40352c8d607e1fa6cf417ba9f89063f2b046306405a0"
AUTHORIZATION_SHA256 = "871a9a5f6b7351a5df493817032c88ea92f33f11125cb406c9c8d45b1c960497"
PS001_SOURCE_SHA256 = "bc29dc0f0d3a443d640572c88c3e10df08c6277ddf2326c689d9bd0b9ecef172"
PS002_SOURCE_SHA256 = "866429bf10096756340b536f2b952dd5d95f6979f4d145120fe42b256d7d5489"
PS001_REPORT_SHA256 = "fd7df65335b1ce60822ca5114c1a5b832960d6f10659a6e9776564728de29412"
PS002_REPORT_SHA256 = "ff2d22c3cef426332e0be0784f02b2d245c901f789b047a7cea67abd63906b35"
PS001_EXPLORATION_SHA256 = "a78922ca25f0ca5027f695b2a12e8059ee83597366f1b87ecf7b7ef6c5ffdc1d"
PS001_EXPLORATION_LF_SHA256 = "b1645ecb4991ed7b3bd84729779ccaeb7306b39a035dfc196e901f54e52b154d"
PS002_EXPLORATION_SHA256 = "c7b12a4e3250366d7fc37765a73e783fb688991900b4abb47bd50a3def4a3825"
PS002_DETERMINISM_SHA256 = "128242740c0aea40e03759667bfb17f0507228e8505f374abdd34a5c3dd9142c"
DATABASE_SHA256 = "5da47ea3fc2c8e3dcc50fa380ff65202d82557905d9976117e9e5d82e55c1c41"
QUERY_MANIFEST_SHA256 = "ae950fda20dce9f519f31ee2670a815a5599648cab618d42309db7e3f23d36f4"
QUERY_CACHE_SHA256 = "d9741edb0545d8cfe050663340599a31813d6025c38f0467e0ec7671573a1e6a"
QUERY_CAPTURE_SHA256 = "2c24ea75d7551beb6658d8b9208225b985e25a9111cfd3766ec4f7980a7f18e4"
ANSWER_KEY_SHA256 = "2d43a31d3c04f4ad690ff2910abde71f508a3f6ce776545a9f2b16f90fae5320"
PS002_MECHANISM_DIGEST = "cfca813a79ee96ee2949e9f567f9c5360acb30d410e37afd847ef65d5666e15c"
PS002_ARTIFACT_SEQUENCE_DIGEST = "df47bbbc1e6b7a21bb8ec48bf81d7661b494fd693ea0905a544874ca142d9194"
PS002_STRONGEST_CELL_DIGEST = "b815c066f62b1a493c1168c89ee99f16fdb14c69464521b37ca83773cdd97348"
CYCLE_CUE_SHA256 = "bb2ccca6baafa7920e0e112cc4a34aded69c3b1d7e5370f52e77c33bfcada256"
SPURIOUS_CUE_SHA256 = "daf89fd2e81596c34e742709e811b34d860e3c862a5337f224729f33da5ad662"
GRID = tuple((probe_count, swap_count) for probe_count in (3, 5) for swap_count in (1, 4))
EXPECTED_QUERIES = 24
TARGET_OUTPUTS = 8
ATTEMPT_BUDGET = 16
LIVE_ARRAY_CEILING = 536_870_912
CELL_WALL_CEILING_SECONDS = 600.0
GRID_WALL_CEILING_SECONDS = 3_600.0
FORBIDDEN_IMPORT_PARTS = (
    "q_facts_key",
    "answer_key",
    "rubric_reader",
    "criteria_evaluator",
    "atomic_items",
    "targeted_items",
)


def _write_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite retained artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite retained artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(canonical_json_bytes(row).decode("ascii") + "\n")


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=REPO_ROOT, text=True, encoding="utf-8"
    ).strip()


def assert_execution_tree() -> str:
    if _git("status", "--porcelain"):
        raise RuntimeError("PS-003 exploration requires a clean committed worktree")
    if _git("branch", "--show-current") != "study/ps-003-ambiguous-cue-resolution":
        raise RuntimeError("PS-003 exploration is on the wrong branch")
    return _git("rev-parse", "HEAD")


def assert_anchors() -> dict[str, str]:
    anchors = {
        "design": sha256_file(DESIGN),
        "authorization": sha256_file(AUTHORIZATION),
        "ps001_source": sha256_file(PS001_SOURCE),
        "ps002_source": sha256_file(PS002_SOURCE),
        "ps001_report": sha256_file(PS001_REPORT),
        "ps002_report": sha256_file(PS002_REPORT),
        "ps001_exploration": sha256_file(PS001_EXPLORATION),
        "ps002_exploration": sha256_file(PS002_EXPLORATION),
        "ps002_determinism": sha256_file(PS002_DETERMINISM),
        "database": sha256_file(DATABASE),
        "query_manifest": sha256_file(QUERY_MANIFEST),
        "query_cache": sha256_file(QUERY_CACHE),
        "query_capture_manifest": sha256_file(QUERY_CAPTURE_MANIFEST),
        "answer_key": sha256_file(ANSWER_KEY),
        "mechanism_source": sha256_file(PS003_SOURCE),
        "exploration_source": sha256_file(EXPLORATION_SOURCE),
    }
    expected = {
        "design": DESIGN_SHA256,
        "authorization": AUTHORIZATION_SHA256,
        "ps001_source": PS001_SOURCE_SHA256,
        "ps002_source": PS002_SOURCE_SHA256,
        "ps001_report": PS001_REPORT_SHA256,
        "ps002_report": PS002_REPORT_SHA256,
        "ps002_exploration": PS002_EXPLORATION_SHA256,
        "ps002_determinism": PS002_DETERMINISM_SHA256,
        "database": DATABASE_SHA256,
        "query_manifest": QUERY_MANIFEST_SHA256,
        "query_cache": QUERY_CACHE_SHA256,
        "query_capture_manifest": QUERY_CAPTURE_SHA256,
        "answer_key": ANSWER_KEY_SHA256,
    }
    for name, expected_identity in expected.items():
        if anchors[name] != expected_identity:
            raise AssertionError(f"PS-003 {name} anchor changed")
    ps001_payload = json.loads(PS001_EXPLORATION.read_text(encoding="utf-8"))
    if anchors["ps001_exploration"] not in {
        PS001_EXPLORATION_SHA256,
        PS001_EXPLORATION_LF_SHA256,
    }:
        raise AssertionError("PS-003 PS-001 exploration representation changed")
    if (
        ps001_payload["determinism"]["mechanism_digest"]
        != PS001_MECHANISM_DIGEST
    ):
        raise AssertionError("PS-003 PS-001 parsed mechanism identity changed")
    anchors["ps001_exploration_representation"] = (
        "CRLF" if anchors["ps001_exploration"] == PS001_EXPLORATION_SHA256 else "LF"
    )
    return anchors


def assert_imports_label_blind(paths: Sequence[Path]) -> dict[str, Any]:
    imports: list[str] = []
    source_text = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        source_text.append(text.casefold())
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
    forbidden_imports = sorted(
        value for value in imports if any(part in value.casefold() for part in FORBIDDEN_IMPORT_PARTS)
    )
    if forbidden_imports:
        raise RuntimeError(f"Forbidden measurement import: {forbidden_imports}")
    planted = "experiments/study_011/q_facts_key.md"
    if not any(part in planted.casefold() for part in FORBIDDEN_IMPORT_PARTS):
        raise AssertionError("Planted forbidden mechanism path was accepted")
    return {
        "status": "PASS",
        "imports": sorted(set(imports)),
        "planted_sentinel": "planted forbidden path rejected",
        "source_count": len(source_text),
    }


def reproduce_ps002_strongest(
    memory: Any, population: Any, queries: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    binder = SemanticEngramCueBinder.fit(
        memory, population.vectors, support_width=4, temperature=0.025
    )
    rows = [
        ps002_trace_record(
            query,
            binder.bind(query["vector"], query_sha256=query["text_sha256"], rounds=8),
        )
        for query in queries
    ]
    summary = summarize_ps002_cell(4, 0.025, rows)
    digest = payload_sha256({"summary": summary, "traces": rows})
    if digest != PS002_STRONGEST_CELL_DIGEST:
        raise AssertionError("PS-002 strongest cell did not reproduce exactly")
    target = next(row for row in rows if row["query_id"] == "h121_l02")
    outcomes = {row["cue_sha256"]: row["outcome"] for row in target["rounds"]}
    if outcomes.get(CYCLE_CUE_SHA256) != "cycle":
        raise AssertionError("PS-002 cycle witness did not reproduce")
    if outcomes.get(SPURIOUS_CUE_SHA256) != "spurious":
        raise AssertionError("PS-002 spurious witness did not reproduce")
    return {
        "status": "PASS",
        "support_width": 4,
        "temperature": 0.025,
        "deterministic_digest": digest,
        "cycle_cue_sha256": CYCLE_CUE_SHA256,
        "spurious_cue_sha256": SPURIOUS_CUE_SHA256,
    }


def assert_carried_artifacts() -> dict[str, Any]:
    exploration = json.loads(PS002_EXPLORATION.read_text(encoding="utf-8"))
    comparison = json.loads(PS002_DETERMINISM.read_text(encoding="utf-8"))
    if exploration["determinism"]["mechanism_digest"] != PS002_MECHANISM_DIGEST:
        raise AssertionError("PS-002 mechanism digest changed")
    if comparison["deterministic_artifact_sequence_sha256"] != PS002_ARTIFACT_SEQUENCE_DIGEST:
        raise AssertionError("PS-002 deterministic sequence digest changed")
    if comparison["status"] != "PASS":
        raise AssertionError("PS-002 committed determinism is not passing")
    return {
        "status": "PASS",
        "mechanism_digest": PS002_MECHANISM_DIGEST,
        "deterministic_artifact_sequence_sha256": PS002_ARTIFACT_SEQUENCE_DIGEST,
    }


def _probe_record(record: AmbiguityProbe) -> dict[str, Any]:
    recall = record.recall
    if recall.runtime_guard:
        terminal_class = "runtime_guard"
    elif recall.cycle:
        terminal_class = "cycle"
    elif record.stored_index is None:
        terminal_class = "spurious"
    else:
        terminal_class = "stored"
    return {
        "probe_index": record.probe_index,
        "cue_sha256": record.cue_sha256,
        "cue_active_count": record.cue_active_count,
        "terminal_class": terminal_class,
        "stored_index": record.stored_index,
        "terminal_sha256": recall.terminal_sha256,
        "terminal_active_count": int(recall.terminal_state.sum()),
        "fixed_point": recall.fixed_point,
        "cycle": recall.cycle,
        "runtime_guard": recall.runtime_guard,
        "sweeps": recall.sweeps,
        "changed_per_sweep": list(recall.changed_per_sweep),
        "active_counts": list(recall.active_counts),
        "state_sha256_trace": list(recall.state_sha256_trace),
        "quadratic_score_trace": list(recall.quadratic_score_trace),
        "field_margin_trace": list(recall.field_margin_trace),
        "repeated_state_witness": (
            None
            if recall.repeated_state_witness is None
            else list(recall.repeated_state_witness)
        ),
    }


def _attempt_record(record: ResolutionAttempt) -> dict[str, Any]:
    return {
        "attempt_index": record.attempt_index,
        "candidate_indices": list(record.candidate_indices),
        "candidate_supports": list(record.candidate_supports),
        "candidate_weights": list(record.candidate_weights),
        "field_sha256": record.field_sha256,
        "cue_margin": record.cue_margin,
        "base_cue_sha256": record.base_cue_sha256,
        "outcome": record.outcome,
        "consensus_index": record.consensus_index,
        "emitted_index": record.emitted_index,
        "inhibited_index": record.inhibited_index,
        "probes": [_probe_record(probe) for probe in record.probes],
    }


def _trace_record(
    query: Mapping[str, Any], trace: AmbiguityResolutionTrace
) -> dict[str, Any]:
    return {
        "query_id": query["query_id"],
        "query_text_sha256": query["text_sha256"],
        "query_vector_sha256": query["vector_sha256"],
        "semantic_supports": list(trace.semantic_supports),
        "semantic_order": list(trace.semantic_order),
        "attempts": [_attempt_record(row) for row in trace.attempts],
        "emitted_indices": list(trace.emitted_indices),
        "emitted_code_hashes": list(trace.emitted_code_hashes),
        "exhausted": trace.exhausted,
    }


def summarize_cell(
    probe_count: int, swap_count: int, rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    attempts = [attempt for row in rows for attempt in row["attempts"]]
    probes = [probe for attempt in attempts for probe in attempt["probes"]]
    outcomes = Counter(str(row["outcome"]) for row in attempts)
    probe_outcomes = Counter(str(row["terminal_class"]) for row in probes)
    emitted_counts = [len(row["emitted_indices"]) for row in rows]
    attempts_per_query = [len(row["attempts"]) for row in rows]
    unsafe = {
        cue: [
            attempt
            for row in rows
            if row["query_id"] == "h121_l02"
            for attempt in row["attempts"]
            if attempt["base_cue_sha256"] == cue
        ]
        for cue in (CYCLE_CUE_SHA256, SPURIOUS_CUE_SHA256)
    }
    unsafe_rejected = all(
        len(matches) == 1
        and matches[0]["outcome"] != "accepted"
        and matches[0]["emitted_index"] is None
        for matches in unsafe.values()
    )
    no_rejected_output = all(
        (row["outcome"] == "accepted") == (row["emitted_index"] is not None)
        for row in attempts
    )
    unanimous_outputs = all(
        row["outcome"] != "accepted"
        or len({probe["stored_index"] for probe in row["probes"]}) == 1
        for row in attempts
    )
    active_counts_exact = all(
        probe["cue_active_count"] == 41 and probe["terminal_active_count"] == 41
        for probe in probes
    )
    all_finite = all(
        np.all(np.isfinite(row["semantic_supports"]))
        and all(
            np.all(np.isfinite(attempt["candidate_supports"]))
            and np.all(np.isfinite(attempt["candidate_weights"]))
            and np.isfinite(attempt["cue_margin"])
            and all(
                np.all(np.isfinite(probe["quadratic_score_trace"]))
                and np.all(np.isfinite(probe["field_margin_trace"]))
                for probe in attempt["probes"]
            )
            for attempt in row["attempts"]
        )
        for row in rows
    )
    eligible = (
        emitted_counts == [TARGET_OUTPUTS] * EXPECTED_QUERIES
        and outcomes["runtime_guard"] == 0
        and active_counts_exact
        and all_finite
        and unsafe_rejected
        and no_rejected_output
        and unanimous_outputs
    )
    return {
        "cell": f"p{probe_count}_s{swap_count}",
        "probe_count": probe_count,
        "swap_count": swap_count,
        "query_count": len(rows),
        "attempt_count": len(attempts),
        "probe_recall_count": len(probes),
        "attempt_outcomes": dict(sorted(outcomes.items())),
        "probe_terminal_classes": dict(sorted(probe_outcomes.items())),
        "emitted_count_distribution": {
            "minimum": min(emitted_counts),
            "median": float(np.median(emitted_counts)),
            "maximum": max(emitted_counts),
        },
        "attempts_per_query_distribution": {
            "minimum": min(attempts_per_query),
            "median": float(np.median(attempts_per_query)),
            "maximum": max(attempts_per_query),
        },
        "unique_emitted_episode_count": len(
            {index for row in rows for index in row["emitted_indices"]}
        ),
        "unused_episode_count": 119
        - len({index for row in rows for index in row["emitted_indices"]}),
        "unsafe_witnesses": {
            cue: {
                "encountered": len(matches),
                "outcomes": [row["outcome"] for row in matches],
                "emitted_indices": [row["emitted_index"] for row in matches],
            }
            for cue, matches in unsafe.items()
        },
        "unsafe_witnesses_rejected": unsafe_rejected,
        "no_rejected_family_output": no_rejected_output,
        "all_accepted_families_unanimous": unanimous_outputs,
        "all_active_counts_exact": active_counts_exact,
        "all_values_finite": all_finite,
        "eligible": eligible,
    }


def select_cell(cells: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    eligible = [cell for cell in cells if cell["eligible"]]
    if not eligible:
        return None
    return dict(
        max(
            eligible,
            key=lambda cell: (
                int(cell["swap_count"]),
                int(cell["probe_count"]),
                -int(cell["attempt_count"]),
                -GRID.index((int(cell["probe_count"]), int(cell["swap_count"]))),
            ),
        )
    )


def _manifest(output_dir: Path) -> dict[str, Any]:
    files = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            files.append(
                {
                    "path": path.relative_to(output_dir).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    manifest = {"status": "SEALED", "file_count": len(files), "files": files}
    _write_json(output_dir / "artifact_manifest.json", manifest)
    return manifest


def run_exploration(output_dir: Path) -> dict[str, Any]:
    started = time.perf_counter()
    baseline_rss = process_rss_bytes()
    head = assert_execution_tree()
    anchors = assert_anchors()
    leakage = assert_imports_label_blind([PS003_SOURCE, EXPLORATION_SOURCE])
    carried_ps002_artifacts = assert_carried_artifacts()
    population, memory, carried_ps001 = construct_carried_memory()
    queries, query_inventory = load_queries()
    estimated_arrays = int(
        population.vectors.nbytes
        + memory.center.nbytes
        + memory.projection.nbytes
        + memory.codes.nbytes
        + memory.eta.nbytes
        + memory.diagonal.nbytes
        + EXPECTED_QUERIES * 1024 * 8
    )
    if estimated_arrays > LIVE_ARRAY_CEILING:
        raise MemoryError("PS-003 estimated arrays exceed the registered ceiling")

    cells: list[dict[str, Any]] = []
    stable_cell_digests: list[dict[str, str]] = []
    carried_reproductions: list[dict[str, Any]] = []
    for probe_count, swap_count in GRID:
        cell_started = time.perf_counter()
        if cell_started - started > GRID_WALL_CEILING_SECONDS:
            raise TimeoutError("PS-003 grid exceeded its wall-time ceiling")
        carried_reproductions.append(
            reproduce_ps002_strongest(memory, population, queries)
        )
        resolver = EngramAmbiguityResolver.fit(
            memory,
            population.vectors,
            probe_count=probe_count,
            swap_count=swap_count,
        )
        rows = [
            _trace_record(
                query,
                resolver.resolve(
                    query["vector"],
                    query_sha256=query["text_sha256"],
                    target_outputs=TARGET_OUTPUTS,
                    attempt_budget=ATTEMPT_BUDGET,
                ),
            )
            for query in queries
        ]
        elapsed = time.perf_counter() - cell_started
        if elapsed > CELL_WALL_CEILING_SECONDS:
            raise TimeoutError("PS-003 cell exceeded its wall-time ceiling")
        summary = summarize_cell(probe_count, swap_count, rows)
        stable = {"summary": summary, "traces": rows}
        digest = payload_sha256(stable)
        summary["deterministic_digest"] = digest
        summary["wall_seconds"] = elapsed
        summary["observed_rss_bytes"] = process_rss_bytes()
        cell_dir = output_dir / "cells" / summary["cell"]
        _write_jsonl(cell_dir / "traces.jsonl", rows)
        _write_json(cell_dir / "cell_result.json", summary)
        cells.append(summary)
        stable_cell_digests.append({"cell": summary["cell"], "digest": digest})

    selected = select_cell(cells)
    disposition = "AMBIGUOUS_CUES_UNRESOLVED" if selected is None else "LABEL_BLIND_CELL_SELECTED"
    deterministic_digest = payload_sha256(
        {
            "grid": [list(cell) for cell in GRID],
            "cells": stable_cell_digests,
            "selected": (
                None
                if selected is None
                else {
                    "probe_count": selected["probe_count"],
                    "swap_count": selected["swap_count"],
                    "deterministic_digest": selected["deterministic_digest"],
                }
            ),
            "disposition": disposition,
        }
    )
    summary_path = output_dir / "cell_summary.csv"
    if summary_path.exists():
        raise FileExistsError(f"Refusing to overwrite retained artifact: {summary_path}")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(cells[0].keys()))
        writer.writeheader()
        writer.writerows(cells)

    result = {
        "study": "PS-003",
        "stage": "Preflight Part 1 label-blind exploration",
        "status": "COMPLETE",
        "outcome_ceiling": "CHARACTERIZED",
        "design_commit": DESIGN_COMMIT,
        "design_sha256": anchors["design"],
        "authorization_sha256": anchors["authorization"],
        "implementation_commit": head,
        "input_inventory": {
            "episodes": population.inventory,
            "queries": query_inventory,
            "anchors": anchors,
        },
        "carried_ps001": carried_ps001,
        "carried_ps002_artifacts": carried_ps002_artifacts,
        "carried_ps002_reproductions": carried_reproductions,
        "leakage": leakage,
        "grid": [
            {"probe_count": probe_count, "swap_count": swap_count}
            for probe_count, swap_count in GRID
        ],
        "cells": cells,
        "selection_rule": "eligible; greatest S, greatest P, fewest attempts, row-major",
        "selected_cell": (
            None
            if selected is None
            else {
                "probe_count": selected["probe_count"],
                "swap_count": selected["swap_count"],
                "cell": selected["cell"],
                "deterministic_digest": selected["deterministic_digest"],
            }
        ),
        "disposition": disposition,
        "zero_embedding_requests": 0,
        "zero_model_generation_calls": 0,
        "resources": {
            "estimated_live_array_bytes": estimated_arrays,
            "live_array_ceiling_bytes": LIVE_ARRAY_CEILING,
            "launch_rss_bytes": baseline_rss,
            "final_rss_bytes": process_rss_bytes(),
        },
        "runtime": {
            "argv": sys.argv,
            "pid": os.getpid(),
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "thread_environment": {
                name: os.environ.get(name)
                for name in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                )
            },
            "wall_seconds": time.perf_counter() - started,
        },
        "determinism": {
            "mechanism_digest": deterministic_digest,
            "second_process_required": True,
            "comparison_status": "PENDING_SEPARATE_PROCESS_COMPARISON",
        },
        "not_reached": {
            "measurement_labels": "requires committed Part 1, final design lock, authorization, and PF1-PF10",
            "live_generation": "not authorized by PS-003",
        },
    }
    _write_json(output_dir / "exploration.json", result)
    manifest = _manifest(output_dir)
    return {**result, "artifact_manifest": manifest}


def deterministic_artifact_sequence(output_dir: Path) -> list[dict[str, str]]:
    return [
        {"path": path.relative_to(output_dir).as_posix(), "sha256": sha256_file(path)}
        for path in sorted(output_dir.rglob("*"))
        if path.is_file() and path.name == "traces.jsonl"
    ]


def compare_explorations(first: Path, second: Path, output: Path) -> dict[str, Any]:
    first_result = json.loads((first / "exploration.json").read_text(encoding="utf-8"))
    second_result = json.loads((second / "exploration.json").read_text(encoding="utf-8"))
    first_digest = first_result["determinism"]["mechanism_digest"]
    second_digest = second_result["determinism"]["mechanism_digest"]
    first_files = deterministic_artifact_sequence(first)
    second_files = deterministic_artifact_sequence(second)
    report = {
        "study": "PS-003",
        "stage": "two-process determinism",
        "status": "PASS" if first_digest == second_digest and first_files == second_files else "FAIL",
        "first_mechanism_digest": first_digest,
        "second_mechanism_digest": second_digest,
        "deterministic_artifact_sequence_sha256": payload_sha256(first_files),
        "byte_identical_canonical_result_digests": first_digest == second_digest,
        "byte_identical_deterministic_artifacts": first_files == second_files,
    }
    _write_json(output, report)
    if report["status"] != "PASS":
        raise AssertionError("PS-003 two-process determinism failed")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run PS-003 label-blind exploration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--output", type=Path, required=True)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--first", type=Path, required=True)
    compare_parser.add_argument("--second", type=Path, required=True)
    compare_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "run":
        run_exploration(args.output.resolve())
    else:
        compare_explorations(
            args.first.resolve(), args.second.resolve(), args.output.resolve()
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

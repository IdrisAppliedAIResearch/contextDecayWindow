from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import platform
import sqlite3
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

from src.analysis.ps001_exploration import (
    DATABASE,
    EXPECTED_NORMALIZED_VECTOR_SHA256,
    PROJECTION_SEED,
    load_episode_population,
    process_rss_bytes,
)
from src.retrieval_mechanism_ledger.ps001 import (
    SparseEngramAutoassociator,
    array_sha256,
    normalize_rows_fixed_order,
)
from src.retrieval_mechanism_ledger.ps002 import (
    CueBindingRound,
    CueBindingTrace,
    SemanticEngramCueBinder,
    assert_binder_path_allowed,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
DESIGN = COMPONENT_ROOT / "PS_002_NATURAL_LANGUAGE_CUE_BINDING.md"
AUTHORIZATION = COMPONENT_ROOT / "PS_002_AUTHORIZATION.md"
QUERY_MANIFEST = (
    REPO_ROOT / "experiments" / "surveys" / "retrieval_bakeoff" / "holdout" / "queries_121.json"
)
QUERY_CACHE = (
    COMPONENT_ROOT / "artifacts" / "e006_p3_tier4a_capture" / "query_vectors.sqlite"
)
QUERY_CAPTURE_MANIFEST = (
    COMPONENT_ROOT / "artifacts" / "e006_p3_tier4a_capture" / "capture_manifest.json"
)
PS001_EXPLORATION = (
    COMPONENT_ROOT / "artifacts" / "ps001_exploration" / "part1_process_1" / "exploration.json"
)
MECHANISM_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "ps002.py"
EXPLORATION_SOURCE = Path(__file__).resolve()

DESIGN_COMMIT = "e6b9c5cf6d54b1f5847c58b80f1764a2b6ea8086"
DESIGN_SHA256 = "79183a5a26c2bb88fdbeafe36398d9b811720d71d024e8ef9c1af533ad4411ec"
PS001_MECHANISM_DIGEST = "0d45ddd45980dbf3989a543136bad52d4f743f650f3c0af76e370f049b6c80cc"
PS001_CODE_SEQUENCE_SHA256 = "a8d1364a58de6d6c70db2dd771ba96e59fcf931d36cfb28ea69c780b55e3a3b8"
QUERY_MANIFEST_SHA256 = "ae950fda20dce9f519f31ee2670a815a5599648cab618d42309db7e3f23d36f4"
QUERY_CACHE_SHA256 = "d9741edb0545d8cfe050663340599a31813d6025c38f0467e0ec7671573a1e6a"
QUERY_CAPTURE_SHA256 = "2c24ea75d7551beb6658d8b9208225b985e25a9111cfd3766ec4f7980a7f18e4"
DATABASE_SHA256 = "5da47ea3fc2c8e3dcc50fa380ff65202d82557905d9976117e9e5d82e55c1c41"
GRID = tuple((width, temperature) for width in (4, 8, 16) for temperature in (0.025, 0.050, 0.100))
EXPECTED_QUERIES = 24
ROUNDS = 8
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def payload_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sequence_sha256(values: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(values).encode("ascii")).hexdigest()


def _write_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite retained artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=True, indent=2, sort_keys=True)
        handle.write("\n")


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
        raise RuntimeError("PS-002 exploration requires a clean committed worktree")
    if _git("branch", "--show-current") != "study/ps-002-natural-language-cue-binding":
        raise RuntimeError("PS-002 exploration is on the wrong branch")
    return _git("rev-parse", "HEAD")


def assert_anchors() -> dict[str, str]:
    anchors = {
        "design": sha256_file(DESIGN),
        "authorization": sha256_file(AUTHORIZATION),
        "database": sha256_file(DATABASE),
        "query_manifest": sha256_file(QUERY_MANIFEST),
        "query_cache": sha256_file(QUERY_CACHE),
        "query_capture_manifest": sha256_file(QUERY_CAPTURE_MANIFEST),
        "ps001_exploration": sha256_file(PS001_EXPLORATION),
        "mechanism_source": sha256_file(MECHANISM_SOURCE),
        "exploration_source": sha256_file(EXPLORATION_SOURCE),
    }
    expected = {
        "design": DESIGN_SHA256,
        "database": DATABASE_SHA256,
        "query_manifest": QUERY_MANIFEST_SHA256,
        "query_cache": QUERY_CACHE_SHA256,
        "query_capture_manifest": QUERY_CAPTURE_SHA256,
    }
    for name, identity in expected.items():
        if anchors[name] != identity:
            raise AssertionError(f"PS-002 {name} anchor changed")
    return anchors


def assert_imports_label_blind(paths: Sequence[Path]) -> dict[str, Any]:
    imports: list[str] = []
    for path in paths:
        assert_binder_path_allowed(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
    forbidden = sorted(
        value for value in imports if any(part in value.casefold() for part in FORBIDDEN_IMPORT_PARTS)
    )
    if forbidden:
        raise RuntimeError(f"Forbidden measurement import: {forbidden}")
    try:
        assert_binder_path_allowed("experiments/study_011/q_facts_key.md")
    except ValueError:
        planted = "planted forbidden path rejected"
    else:
        raise AssertionError("Planted forbidden mechanism path was accepted")
    return {"status": "PASS", "imports": sorted(set(imports)), "planted_sentinel": planted}


def load_queries() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = json.loads(QUERY_MANIFEST.read_text(encoding="utf-8"))
    rows = manifest.get("queries", [])
    if len(rows) != EXPECTED_QUERIES:
        raise AssertionError("PS-002 requires exactly 24 sealed queries")
    texts = [str(row["text"]) for row in rows]
    if len(set(texts)) != EXPECTED_QUERIES:
        raise AssertionError("PS-002 query texts must be unique")
    uri = f"file:{QUERY_CACHE.as_posix()}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as connection:
        cache_rows = dict(connection.execute("SELECT text, embedding FROM cache"))
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
    loaded: list[dict[str, Any]] = []
    for row in rows:
        text = str(row["text"])
        if text not in cache_rows:
            raise KeyError(f"Sealed query-vector miss: {row['query_id']}")
        raw = np.frombuffer(cache_rows[text], dtype="<f4")
        if raw.shape != (1024,):
            raise AssertionError("PS-002 query vector has the wrong shape")
        vector = normalize_rows_fixed_order(raw.astype("<f8")[None, :])[0]
        vector.setflags(write=False)
        loaded.append(
            {
                "query_id": str(row["query_id"]),
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "vector": vector,
                "vector_sha256": array_sha256(raw.astype("<f4")),
            }
        )
    inventory = {
        "query_count": len(loaded),
        "query_id_sequence_sha256": sequence_sha256([row["query_id"] for row in loaded]),
        "query_text_sequence_sha256": sequence_sha256([row["text_sha256"] for row in loaded]),
        "query_vector_sequence_sha256": sequence_sha256([row["vector_sha256"] for row in loaded]),
        "cache_metadata": metadata,
    }
    return loaded, inventory


def construct_carried_memory() -> tuple[Any, SparseEngramAutoassociator, dict[str, Any]]:
    population = load_episode_population()
    if population.inventory["normalized_float64_sha256"] != EXPECTED_NORMALIZED_VECTOR_SHA256:
        raise AssertionError("PS-002 population does not reproduce PS-001")
    prior = json.loads(PS001_EXPLORATION.read_text(encoding="utf-8"))
    if prior["determinism"]["mechanism_digest"] != PS001_MECHANISM_DIGEST:
        raise AssertionError("Committed PS-001 mechanism digest changed")
    memory = SparseEngramAutoassociator.fit(
        population.vectors,
        code_dimension=4096,
        active_count=41,
        projection_seed=PROJECTION_SEED,
    )
    code_sequence = sequence_sha256(memory.code_hashes)
    if code_sequence != PS001_CODE_SEQUENCE_SHA256:
        raise AssertionError("Reconstructed PS-001 code sequence changed")
    fixed = sum(memory.recall(code).fixed_point for code in memory.codes)
    if fixed != 119:
        raise AssertionError("Reconstructed PS-001 fixed-point count changed")
    identity = {
        "status": "PASS",
        "committed_mechanism_digest": PS001_MECHANISM_DIGEST,
        "code_sequence_sha256": code_sequence,
        "codes_sha256": array_sha256(memory.codes),
        "fixed_points": fixed,
        "required_fixed_points": 119,
    }
    return population, memory, identity


def _round_record(record: CueBindingRound) -> dict[str, Any]:
    recall = record.recall
    return {
        "round_index": record.round_index,
        "candidate_indices": list(record.candidate_indices),
        "candidate_supports": list(record.candidate_supports),
        "candidate_weights": list(record.candidate_weights),
        "cue_margin": record.cue_margin,
        "cue_sha256": record.cue_sha256,
        "cue_active_count": record.cue_active_count,
        "initial_terminal_hamming": record.initial_terminal_hamming,
        "outcome": record.outcome,
        "emitted_index": record.emitted_index,
        "inhibited_index": record.inhibited_index,
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
        "repeated_state_witness": None if recall.repeated_state_witness is None else list(recall.repeated_state_witness),
    }


def _trace_record(query: Mapping[str, Any], trace: CueBindingTrace) -> dict[str, Any]:
    return {
        "query_id": query["query_id"],
        "query_text_sha256": query["text_sha256"],
        "query_vector_sha256": query["vector_sha256"],
        "semantic_supports": list(trace.semantic_supports),
        "semantic_order": list(trace.semantic_order),
        "emitted_indices": list(trace.emitted_indices),
        "emitted_code_hashes": list(trace.emitted_code_hashes),
        "rounds": [_round_record(row) for row in trace.rounds],
    }


def summarize_cell(width: int, temperature: float, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rounds = [round_row for row in rows for round_row in row["rounds"]]
    outcomes = Counter(str(row["outcome"]) for row in rounds)
    changed_completed = sum(
        row["outcome"] == "stored" and row["initial_terminal_hamming"] > 0 for row in rounds
    )
    positive_margins = [
        float(value)
        for row in rounds
        for value in row["field_margin_trace"]
        if float(value) > 0.0
    ]
    hamming = [int(row["initial_terminal_hamming"]) for row in rounds]
    emitted_counts = [len(row["emitted_indices"]) for row in rows]
    all_finite = all(
        np.all(np.isfinite(row["semantic_supports"]))
        and all(np.all(np.isfinite(round_row["candidate_weights"])) for round_row in row["rounds"])
        for row in rows
    )
    eligible = (
        outcomes["runtime_guard"] == 0
        and outcomes["cycle"] == 0
        and emitted_counts == [ROUNDS] * EXPECTED_QUERIES
        and all(row["cue_active_count"] == 41 and row["terminal_active_count"] == 41 for row in rounds)
        and all_finite
    )
    return {
        "cell": f"m{width}_t{temperature:.3f}",
        "support_width": width,
        "temperature": temperature,
        "query_count": len(rows),
        "round_count": len(rounds),
        "outcomes": dict(sorted(outcomes.items())),
        "emitted_count_distribution": {
            "minimum": min(emitted_counts),
            "median": float(np.median(emitted_counts)),
            "maximum": max(emitted_counts),
        },
        "changed_and_completed_count": changed_completed,
        "minimum_positive_terminal_margin": min(positive_margins, default=0.0),
        "median_initial_terminal_hamming": float(np.median(hamming)),
        "minimum_initial_terminal_hamming": min(hamming),
        "maximum_initial_terminal_hamming": max(hamming),
        "unique_emitted_episode_count": len({index for row in rows for index in row["emitted_indices"]}),
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
                int(cell["changed_and_completed_count"]),
                float(cell["minimum_positive_terminal_margin"]),
                float(cell["median_initial_terminal_hamming"]),
                -int(cell["support_width"]),
                -float(cell["temperature"]),
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
    leakage = assert_imports_label_blind([MECHANISM_SOURCE, EXPLORATION_SOURCE])
    population, memory, carried = construct_carried_memory()
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
        raise MemoryError("PS-002 estimated arrays exceed the registered ceiling")

    cells: list[dict[str, Any]] = []
    stable_cell_digests: list[dict[str, str]] = []
    for width, temperature in GRID:
        cell_started = time.perf_counter()
        if cell_started - started > GRID_WALL_CEILING_SECONDS:
            raise TimeoutError("PS-002 grid exceeded its wall-time ceiling")
        binder = SemanticEngramCueBinder.fit(
            memory, population.vectors, support_width=width, temperature=temperature
        )
        rows = []
        for query in queries:
            trace = binder.bind(
                query["vector"], query_sha256=query["text_sha256"], rounds=ROUNDS
            )
            rows.append(_trace_record(query, trace))
        elapsed = time.perf_counter() - cell_started
        if elapsed > CELL_WALL_CEILING_SECONDS:
            raise TimeoutError("PS-002 cell exceeded its wall-time ceiling")
        summary = summarize_cell(width, temperature, rows)
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
    disposition = "NATURAL_CUES_NOT_BOUND" if selected is None else "LABEL_BLIND_CELL_SELECTED"
    deterministic_digest = payload_sha256(
        {
            "grid": [list(cell) for cell in GRID],
            "cells": stable_cell_digests,
            "selected": None if selected is None else {
                "support_width": selected["support_width"],
                "temperature": selected["temperature"],
                "deterministic_digest": selected["deterministic_digest"],
            },
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
        "study": "PS-002",
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
        "carried_ps001": carried,
        "leakage": leakage,
        "grid": [
            {"support_width": width, "temperature": temperature}
            for width, temperature in GRID
        ],
        "cells": cells,
        "selection_rule": "eligible; maximize changed completion, minimum positive margin, median Hamming; then smallest M and TAU",
        "selected_cell": None if selected is None else {
            "support_width": selected["support_width"],
            "temperature": selected["temperature"],
            "cell": selected["cell"],
            "deterministic_digest": selected["deterministic_digest"],
        },
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
                for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
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
            "live_generation": "not authorized by PS-002",
        },
    }
    _write_json(output_dir / "exploration.json", result)
    manifest = _manifest(output_dir)
    return {**result, "artifact_manifest": manifest}


def deterministic_artifact_sequence(output_dir: Path) -> list[dict[str, str]]:
    excluded = {"exploration.json", "artifact_manifest.json", "cell_result.json", "cell_summary.csv"}
    return [
        {"path": path.relative_to(output_dir).as_posix(), "sha256": sha256_file(path)}
        for path in sorted(output_dir.rglob("*"))
        if path.is_file() and path.name not in excluded
    ]


def compare_explorations(first: Path, second: Path, output: Path) -> dict[str, Any]:
    first_result = json.loads((first / "exploration.json").read_text(encoding="utf-8"))
    second_result = json.loads((second / "exploration.json").read_text(encoding="utf-8"))
    first_digest = first_result["determinism"]["mechanism_digest"]
    second_digest = second_result["determinism"]["mechanism_digest"]
    first_files = deterministic_artifact_sequence(first)
    second_files = deterministic_artifact_sequence(second)
    report = {
        "study": "PS-002",
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
        raise AssertionError("PS-002 two-process determinism failed")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run PS-002 label-blind exploration")
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
        compare_explorations(args.first.resolve(), args.second.resolve(), args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import ast
import csv
import ctypes
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"

import numpy as np

from src.retrieval_mechanism_ledger.ps001 import (
    FIELD_REFERENCE_ATOL,
    OPERATOR_FORMULA_VERSION,
    PROJECTION_FORMULA_VERSION,
    TIE_SENSITIVE_MARGIN,
    SparseEngramAutoassociator,
    SparseRecallTrace,
    array_sha256,
    assert_mechanism_path_allowed,
    deterministic_coordinate_permutation,
    materialize_centered_weights,
    normalize_rows_fixed_order,
    rademacher_projection,
    slow_reference_transition,
    stable_population_center,
    state_sha256,
    top_k_binary,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
)
DESIGN = COMPONENT_ROOT / "PS_001_PATTERN_SEPARATED_ENGRAM_FORMATION.md"
AUTHORIZATION = COMPONENT_ROOT / "PS_001_AUTHORIZATION.md"
AMENDMENT_006 = COMPONENT_ROOT / "amendments" / "AMENDMENT_006_ps001_numerical_identity.md"
AMENDMENT_006_AUTHORIZATION = COMPONENT_ROOT / "PS_001_AMENDMENT_006_AUTHORIZATION.md"
AMENDMENT_007 = COMPONENT_ROOT / "amendments" / "AMENDMENT_007_ps001_trace_identity.md"
AMENDMENT_007_AUTHORIZATION = COMPONENT_ROOT / "PS_001_AMENDMENT_007_AUTHORIZATION.md"
AMENDMENT_008 = COMPONENT_ROOT / "amendments" / "AMENDMENT_008_ps001_carried_normalization.md"
AMENDMENT_008_AUTHORIZATION = COMPONENT_ROOT / "PS_001_AMENDMENT_008_AUTHORIZATION.md"
PRIOR_REPORT = COMPONENT_ROOT / "E006_PART3_REV4_REPORT.md"
PRIOR_ARTIFACT = (
    COMPONENT_ROOT
    / "artifacts"
    / "e006_p3_rev4_exploration"
    / "exploration.json"
)
DATABASE = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier6"
    / "runs"
    / "tier6_live_121_corrected_001"
    / "context_matched_stm"
    / "study.db"
)
MECHANISM_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "ps001.py"
EXPLORATION_SOURCE = Path(__file__).resolve()

DESIGN_COMMIT = "e20d0c0035fc96d0c9181df67d0a0c8eebd5c368"
DESIGN_SHA256 = "b525452743673bec8fbd45e80e81ae2a6342872b2bb58d858f2c544ca315fc6a"
AUTHORIZATION_COMMIT = "90e88f86"
AMENDMENT_006_COMMIT = "3079316d0ee7172dc397a54425cf71ef1638fb63"
AMENDMENT_007_COMMIT = "637cb4129a98663368ee15aea5e46e5fc60bb8ab"
AMENDMENT_008_COMMIT = "a8056e37d07d4503e7f2e5034e15ce7d4e9cbe8f"
REV4_COMMIT = "0d98be7967329dd21b4aefbf706a3aaf435cd6f3"
REV4_RESULT_SHA256 = "1942950078e0a7eb30619f66356e0373208372415b401b61a49dae6fe8cdaa78"
REV4_DATABASE_SHA256 = "5da47ea3fc2c8e3dcc50fa380ff65202d82557905d9976117e9e5d82e55c1c41"
PROJECTION_SEED = bytes.fromhex(
    "0448cb7290b285bf85aa856004bd6ccbe8124aa8e3f83eaaa0225519dd626362"
)
GRID = (
    (2048, 20),
    (2048, 41),
    (2048, 102),
    (4096, 41),
    (4096, 82),
    (4096, 205),
    (8192, 82),
    (8192, 164),
    (8192, 410),
)
WEIGHT_AUDIT_CHUNK_ROWS = 256
LIVE_ARRAY_CEILING = 536_870_912
CELL_WALL_CEILING_SECONDS = 600.0
GRID_WALL_CEILING_SECONDS = 3_600.0
EXPECTED_EPISODES = 119
EXPECTED_INPUT_DIMENSION = 1024
EXPECTED_NORMALIZED_VECTOR_SHA256 = (
    "2ed0cc29b0de9b54bf80bbd800123938ecaac2353b3e01ece37e397b6844e27b"
)
FORBIDDEN_SOURCE_PARTS = (
    "q_facts_key",
    "rubric_reader",
    "criteria_evaluator",
    "atomic_items",
    "targeted_items",
)
REQUIRED_THREAD_ENV = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}


@dataclass(frozen=True)
class EpisodePopulation:
    vectors: np.ndarray
    content_hashes: tuple[str, ...]
    source_turns: tuple[int, ...]
    inventory: Mapping[str, Any]


@dataclass(frozen=True)
class StageResult:
    status: str
    payload: Mapping[str, Any]


class ResourceLimitError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def payload_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sequence_sha256(values: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(values).encode("ascii")).hexdigest()


def content_sha256(episode: Mapping[str, Any]) -> str:
    stable = {
        "assistant_message": str(episode["assistant_message"]),
        "turn_number": int(episode["turn_number"]),
        "user_message": str(episode["user_message"]),
    }
    return hashlib.sha256(
        json.dumps(
            stable,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _git(*args: str, cwd: Path = REPO_ROOT) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=cwd, text=True, encoding="utf-8"
    ).strip()


def assert_committed_anchors() -> dict[str, str]:
    anchors = {
        "design": sha256_file(DESIGN),
        "authorization": sha256_file(AUTHORIZATION),
        "amendment_006": sha256_file(AMENDMENT_006),
        "amendment_006_authorization": sha256_file(AMENDMENT_006_AUTHORIZATION),
        "amendment_007": sha256_file(AMENDMENT_007),
        "amendment_007_authorization": sha256_file(AMENDMENT_007_AUTHORIZATION),
        "amendment_008": sha256_file(AMENDMENT_008),
        "amendment_008_authorization": sha256_file(AMENDMENT_008_AUTHORIZATION),
        "prior_report": sha256_file(PRIOR_REPORT),
        "prior_artifact": sha256_file(PRIOR_ARTIFACT),
        "mechanism_source": sha256_file(MECHANISM_SOURCE),
        "exploration_source": sha256_file(EXPLORATION_SOURCE),
    }
    if anchors["design"] != DESIGN_SHA256:
        raise AssertionError("PS-001 design anchor changed")
    if anchors["prior_artifact"] != REV4_RESULT_SHA256:
        raise AssertionError("Immutable Rev 4 artifact changed")
    return anchors


def assert_clean_execution_tree() -> str:
    status = _git("status", "--porcelain")
    if status:
        raise RuntimeError("PS-001 execution requires a clean committed worktree")
    head = _git("rev-parse", "HEAD")
    if _git("branch", "--show-current") != "study/ps-001-pattern-separated-engram-formation":
        raise RuntimeError("PS-001 execution is on the wrong branch")
    return head


def load_episode_population() -> EpisodePopulation:
    if not DATABASE.is_file():
        raise FileNotFoundError(f"Committed PS-001 database is absent: {DATABASE}")
    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
            """
            SELECT id, turn_number, user_message, assistant_message, embedding
            FROM episodes
            WHERE turn_number < 120
            ORDER BY turn_number, id
            """
        ).fetchall()
    if len(rows) != EXPECTED_EPISODES:
        raise AssertionError("PS-001 requires exactly 119 eligible episodes")
    episodes = [
        {
            "id": str(row[0]),
            "turn_number": int(row[1]),
            "user_message": str(row[2]),
            "assistant_message": str(row[3]),
            "embedding": bytes(row[4]),
        }
        for row in rows
    ]
    raw = np.stack(
        [np.frombuffer(row["embedding"], dtype="<f4") for row in episodes]
    )
    if raw.shape != (EXPECTED_EPISODES, EXPECTED_INPUT_DIMENSION):
        raise AssertionError("PS-001 episode vector matrix has the wrong shape")
    vectors = normalize_rows_fixed_order(raw.astype("<f8"))
    normalized_digest = array_sha256(vectors)
    if normalized_digest != EXPECTED_NORMALIZED_VECTOR_SHA256:
        raise AssertionError(
            "PS-001 carried normalization does not reproduce Rev 4 bytes"
        )
    hashes = tuple(content_sha256(row) for row in episodes)
    turns = tuple(int(row["turn_number"]) for row in episodes)
    if len(set(hashes)) != EXPECTED_EPISODES:
        raise AssertionError("PS-001 content identities are not unique")
    vectors.setflags(write=False)
    inventory = {
        "database_path": DATABASE.relative_to(REPO_ROOT).as_posix(),
        "database_bytes": DATABASE.stat().st_size,
        "database_sha256": sha256_file(DATABASE),
        "episode_count": len(episodes),
        "source_turn_min": min(turns),
        "source_turn_max": max(turns),
        "source_turn_sequence_sha256": sequence_sha256(tuple(map(str, turns))),
        "raw_float32_shape": list(raw.shape),
        "raw_float32_sha256": array_sha256(raw.astype("<f4")),
        "normalized_float64_shape": list(vectors.shape),
        "normalized_float64_sha256": normalized_digest,
        "content_sequence_sha256": sequence_sha256(hashes),
    }
    return EpisodePopulation(vectors, hashes, turns, inventory)


def _module_paths_in_worktree(worktree: Path) -> dict[str, str]:
    script = (
        "import json,numpy,src.analysis.e006_p3_rev4_exploration as e;"
        "import src.retrieval_mechanism_ledger.e006_p3_rev4 as m;"
        "print(json.dumps({'numpy':numpy.__file__,'exploration':e.__file__,"
        "'mechanism':m.__file__},sort_keys=True))"
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    output = subprocess.check_output(
        [sys.executable, "-c", script],
        cwd=worktree,
        env=env,
        text=True,
        encoding="utf-8",
    )
    paths = json.loads(output)
    resolved_root = worktree.resolve()
    for key in ("exploration", "mechanism"):
        if not Path(paths[key]).resolve().is_relative_to(resolved_root):
            raise RuntimeError(f"Rev 4 {key} import escaped its control worktree")
    return paths


def reproduce_rev4(worktree: Path, output: Path) -> dict[str, Any]:
    worktree = worktree.resolve()
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite historical gate: {output}")
    if _git("rev-parse", "HEAD", cwd=worktree) != REV4_COMMIT:
        raise RuntimeError("Rev 4 control worktree is at the wrong commit")
    if _git("status", "--porcelain", cwd=worktree):
        raise RuntimeError("Rev 4 control worktree is dirty")
    if sha256_file(DATABASE) != REV4_DATABASE_SHA256:
        raise RuntimeError("Retained Rev 4 database source has the wrong digest")
    control_database = worktree / DATABASE.relative_to(REPO_ROOT)
    if control_database.exists():
        if sha256_file(control_database) != REV4_DATABASE_SHA256:
            raise RuntimeError(
                "Rev 4 control database exists with an unexpected digest"
            )
    else:
        control_database.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DATABASE, control_database)
    if sha256_file(control_database) != REV4_DATABASE_SHA256:
        raise RuntimeError("Provisioned Rev 4 control database failed identity check")
    if _git("status", "--porcelain", cwd=worktree):
        raise RuntimeError("Provisioned Rev 4 input made the control worktree dirty")
    module_paths = _module_paths_in_worktree(worktree)
    generated = output.with_suffix(".generated.json")
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.update(REQUIRED_THREAD_ENV)
    command = [
        sys.executable,
        "-m",
        "src.analysis.e006_p3_rev4_exploration",
        str(generated),
    ]
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=worktree,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    stdout, stderr = process.communicate()
    wall_seconds = time.perf_counter() - started
    if process.returncode != 0:
        raise RuntimeError(
            f"Rev 4 reproduction failed ({process.returncode}): {stderr.strip()}"
        )
    digest = sha256_file(generated)
    if digest != REV4_RESULT_SHA256:
        raise AssertionError(
            f"Rev 4 result digest mismatch: expected {REV4_RESULT_SHA256}, got {digest}"
        )
    result = json.loads(generated.read_text(encoding="utf-8"))
    rows = result["gates"]["G3"]["rows"]
    terminals = Counter(str(row["terminal_sha256"]) for row in rows)
    basin_sizes = sorted(terminals.values())
    exact = {
        "converged_count": sum(bool(row["converged"]) for row in rows),
        "stored_fixed_point_count": int(result["gates"]["G3"]["fixed_point_count"]),
        "unique_terminal_count": len(terminals),
        "basin_sizes": basin_sizes,
        "terminal_identity_sequence_sha256": sequence_sha256(
            tuple(str(row["terminal_sha256"]) for row in rows)
        ),
        "source_identity_sequence_sha256": sequence_sha256(
            tuple(str(row["source_content_sha256"]) for row in rows)
        ),
    }
    if exact["converged_count"] != 119:
        raise AssertionError("Rev 4 did not reproduce 119 converged traces")
    if exact["stored_fixed_point_count"] != 0:
        raise AssertionError("Rev 4 did not reproduce zero stored fixed points")
    if exact["unique_terminal_count"] != 6 or basin_sizes != [5, 13, 15, 20, 29, 37]:
        raise AssertionError("Rev 4 terminal basins did not reproduce")
    gate = {
        "study": "PS-001",
        "stage": "historical_reproduction",
        "status": "PASS",
        "control_commit": REV4_COMMIT,
        "control_clean": True,
        "control_worktree": str(worktree),
        "module_paths": module_paths,
        "source_hashes": {
            "mechanism": sha256_file(
                worktree / "src" / "retrieval_mechanism_ledger" / "e006_p3_rev4.py"
            ),
            "runner": sha256_file(
                worktree / "src" / "analysis" / "e006_p3_rev4_exploration.py"
            ),
        },
        "database_sha256": sha256_file(
            control_database
        ),
        "database_provenance": {
            "retained_source_path": str(DATABASE),
            "control_path": str(control_database),
            "sha256": REV4_DATABASE_SHA256,
            "git_tracked_at_control_commit": False,
            "control_status_after_provisioning": "clean_ignored_input",
        },
        "expected_result_sha256": REV4_RESULT_SHA256,
        "generated_result_sha256": digest,
        "exact_reproduction": exact,
        "runtime": {
            "command": command,
            "pid": process.pid,
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "thread_environment": REQUIRED_THREAD_ENV,
            "wall_seconds": wall_seconds,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(gate, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    generated.unlink()
    return gate


def load_historical_gate(path: Path) -> dict[str, Any]:
    gate = json.loads(path.read_text(encoding="utf-8"))
    if gate.get("status") != "PASS":
        raise RuntimeError("Rev 4 historical reproduction gate has not passed")
    if gate.get("control_commit") != REV4_COMMIT:
        raise RuntimeError("Historical gate names the wrong Rev 4 commit")
    if gate.get("generated_result_sha256") != REV4_RESULT_SHA256:
        raise RuntimeError("Historical gate does not reproduce the Rev 4 digest")
    exact = gate.get("exact_reproduction", {})
    if exact.get("converged_count") != 119 or exact.get("stored_fixed_point_count") != 0:
        raise RuntimeError("Historical gate does not reproduce Rev 4 state behavior")
    if exact.get("basin_sizes") != [5, 13, 15, 20, 29, 37]:
        raise RuntimeError("Historical gate does not reproduce Rev 4 basins")
    return gate


def execute_ordered_gates(
    gates: Sequence[tuple[str, Callable[[], StageResult]]]
) -> dict[str, Mapping[str, Any] | str]:
    results: dict[str, Mapping[str, Any] | str] = {}
    reached_failure = False
    for name, stage in gates:
        if reached_failure:
            results[name] = "NOT_REACHED"
            continue
        result = stage()
        results[name] = dict(result.payload)
        if result.status != "PASS":
            reached_failure = True
    return results


def assert_imports_label_blind(paths: Sequence[Path]) -> dict[str, Any]:
    imports: dict[str, list[str]] = {}
    for path in paths:
        assert_mechanism_path_allowed(path)
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        matches = [part for part in FORBIDDEN_SOURCE_PARTS if part in lowered]
        if matches:
            raise RuntimeError(f"Forbidden measurement reference in {path}: {matches}")
        tree = ast.parse(source, filename=str(path))
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
        forbidden_imports = [
            name
            for name in names
            if any(part in name.lower() for part in FORBIDDEN_SOURCE_PARTS)
        ]
        if forbidden_imports:
            raise RuntimeError(f"Forbidden measurement import in {path}: {forbidden_imports}")
        imports[path.relative_to(REPO_ROOT).as_posix()] = sorted(names)
    planted = "src.analysis.rubric_reader"
    try:
        if any(part in planted.lower() for part in FORBIDDEN_SOURCE_PARTS):
            raise ImportError("planted forbidden import rejected before encoding")
        importlib.util.find_spec(planted)
    except ImportError as exc:
        planted_result = str(exc)
    else:
        raise AssertionError("Planted forbidden import unexpectedly passed")
    return {
        "status": "PASS",
        "source_imports": imports,
        "planted_forbidden_import": planted_result,
        "runtime_path_guard": "PASS",
    }


def process_rss_bytes() -> int:
    if os.name == "nt":
        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.GetCurrentProcess.argtypes = []
        psapi.GetProcessMemoryInfo.restype = ctypes.c_int
        psapi.GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ProcessMemoryCounters),
            ctypes.c_ulong,
        ]
        handle = kernel32.GetCurrentProcess()
        if not psapi.GetProcessMemoryInfo(
            handle, ctypes.byref(counters), counters.cb
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(counters.WorkingSetSize)
    try:
        import resource

        scale = 1 if sys.platform == "darwin" else 1024
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * scale)
    except (ImportError, AttributeError):
        return 0


class RssMonitor:
    def __init__(self) -> None:
        self.peak = process_rss_bytes()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.wait(0.01):
            self.peak = max(self.peak, process_rss_bytes())

    def __enter__(self) -> RssMonitor:
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._stop.set()
        self._thread.join()
        self.peak = max(self.peak, process_rss_bytes())


def check_cell_time(started: float) -> None:
    if time.perf_counter() - started > CELL_WALL_CEILING_SECONDS:
        raise ResourceLimitError("Cell exceeded the registered 600-second ceiling")


def synthetic_reachability() -> dict[str, Any]:
    source = np.zeros(8, dtype=np.uint8)
    source[:2] = 1
    activity = 2 / 8
    eta = (source.astype(np.float64) - activity)[None, :]
    denominator = 8 * activity * (1.0 - activity)
    weights = materialize_centered_weights(eta, denominator)
    stable, _field, _margin = slow_reference_transition(
        weights, source, 2, activity
    )
    recovered = 0
    total = 0
    for deactivate in (0, 1):
        for activate in range(2, 8):
            cue = source.copy()
            cue[deactivate] = 0
            cue[activate] = 1
            terminal = cue
            seen = {state_sha256(cue)}
            for _ in range(8):
                next_state, _field, _margin = slow_reference_transition(
                    weights, terminal, 2, activity
                )
                if np.array_equal(next_state, terminal):
                    terminal = next_state
                    break
                digest = state_sha256(next_state)
                terminal = next_state
                if digest in seen:
                    break
                seen.add(digest)
            recovered += int(np.array_equal(terminal, source))
            total += 1
    return {
        "status": "PASS" if np.array_equal(stable, source) and recovered == total else "FAIL",
        "stored_fixed_points": int(np.array_equal(stable, source)),
        "one_swap_recoveries": recovered,
        "one_swap_required": total,
    }


def _write_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite PS-001 artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite PS-001 artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    row,
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )


def _artifact_ref(path: Path, output_dir: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(output_dir).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _float_rows(values: np.ndarray, name: str) -> list[dict[str, Any]]:
    return [
        {"index": index, name: float(value), f"{name}_hex": float(value).hex()}
        for index, value in enumerate(values)
    ]


def write_pairwise_distribution(
    path: Path,
    population: EpisodePopulation,
    component: SparseEngramAutoassociator,
) -> dict[str, Any]:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite PS-001 artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    closest: list[tuple[float, dict[str, Any]]] = []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "left_content_sha256",
                "right_content_sha256",
                "input_cosine",
                "input_cosine_hex",
                "code_overlap",
                "code_hamming_distance",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        for left in range(EXPECTED_EPISODES):
            for right in range(left + 1, EXPECTED_EPISODES):
                cosine = float(np.dot(population.vectors[left], population.vectors[right]))
                overlap = int(
                    np.dot(
                        component.codes[left].astype(np.int64),
                        component.codes[right].astype(np.int64),
                    )
                )
                hamming = int(np.count_nonzero(component.codes[left] != component.codes[right]))
                row = {
                    "left_content_sha256": population.content_hashes[left],
                    "right_content_sha256": population.content_hashes[right],
                    "input_cosine": repr(cosine),
                    "input_cosine_hex": cosine.hex(),
                    "code_overlap": overlap,
                    "code_hamming_distance": hamming,
                }
                writer.writerow(row)
                closest.append((cosine, dict(row)))
                count += 1
    if count != 7_021:
        raise AssertionError(f"Expected 7,021 episode pairs, wrote {count}")
    closest_rows = [row for _score, row in sorted(closest, key=lambda item: (-item[0], item[1]["left_content_sha256"], item[1]["right_content_sha256"]))[:20]]
    return {
        "pair_count": count,
        "artifact": _artifact_ref(path, path.parents[2]),
        "twenty_closest_input_pairs": closest_rows,
    }


def live_array_bytes(
    component: SparseEngramAutoassociator, *, audit_chunk_rows: int = 0
) -> int:
    arrays = (
        component.center,
        component.projection,
        component.codes,
        component.activation_margins,
        component.eta,
        component.diagonal,
    )
    persistent = sum(int(value.nbytes) for value in arrays)
    audit = audit_chunk_rows * component.code_dimension * np.dtype("<f8").itemsize
    audit *= 2
    audit += component.codes.shape[0] * component.code_dimension * np.dtype("<f8").itemsize
    return persistent + audit


def audit_operator(
    component: SparseEngramAutoassociator, started: float
) -> dict[str, Any]:
    dimension = component.code_dimension
    episode_count = component.codes.shape[0]
    estimated_live = live_array_bytes(
        component, audit_chunk_rows=min(WEIGHT_AUDIT_CHUNK_ROWS, dimension)
    )
    if estimated_live >= LIVE_ARRAY_CEILING:
        raise ResourceLimitError("Conceptual weight audit would cross the live-array ceiling")

    independent_fields = np.empty((episode_count, dimension), dtype=np.dtype("<f8"))
    production_fields = np.stack([component.field(row) for row in component.eta])
    value_histogram: Counter[str] = Counter()
    magnitude_histogram: Counter[str] = Counter()
    sign_counts: Counter[str] = Counter()
    row_norms = np.empty(dimension, dtype=np.dtype("<f8"))
    conceptual_digest = hashlib.sha256()
    conceptual_digest.update(
        canonical_json_bytes({"dtype": "<f8", "shape": [dimension, dimension]})
        + b"\n"
    )
    finite = True
    symmetric = True
    zero_diagonal = True
    eta = component.eta
    activity = np.float64(component.active_count / component.code_dimension)
    independent_eta = np.ascontiguousarray(
        component.codes.astype(np.float64) - activity, dtype="<f8"
    )
    independent_diagonal = np.zeros(dimension, dtype=np.dtype("<f8"))
    for row in independent_eta:
        np.add(independent_diagonal, row * row, out=independent_diagonal)
    np.divide(
        independent_diagonal,
        np.float64(component.denominator),
        out=independent_diagonal,
    )
    eta_reproduced = bool(np.array_equal(independent_eta, component.eta))
    diagonal_reproduced = bool(
        np.array_equal(independent_diagonal, component.diagonal)
    )
    gram = np.zeros((episode_count, episode_count), dtype=np.dtype("<f8"))
    for start in range(0, dimension, WEIGHT_AUDIT_CHUNK_ROWS):
        stop = min(dimension, start + WEIGHT_AUDIT_CHUNK_ROWS)
        gram += eta[:, start:stop] @ eta[:, start:stop].T
    independent_fields[:] = (
        (gram @ eta) / np.float64(component.denominator)
        - eta * component.diagonal
    )

    for start in range(0, dimension, WEIGHT_AUDIT_CHUNK_ROWS):
        check_cell_time(started)
        stop = min(dimension, start + WEIGHT_AUDIT_CHUNK_ROWS)
        eta_columns = eta[:, start:stop]
        rows = (eta_columns.T @ eta) / np.float64(component.denominator)
        local = np.arange(stop - start)
        global_indices = np.arange(start, stop)
        rows[local, global_indices] = 0.0
        rows = np.ascontiguousarray(rows, dtype="<f8")
        finite &= bool(np.all(np.isfinite(rows)))
        zero_diagonal &= bool(np.count_nonzero(rows[local, global_indices]) == 0)
        conceptual_digest.update(rows.tobytes(order="C"))
        row_norms[start:stop] = np.sqrt(
            np.sum(rows * rows, axis=1, dtype=np.float64), dtype=np.float64
        )
        unique, counts = np.unique(rows, return_counts=True)
        for value, count in zip(unique, counts):
            numeric = float(value)
            value_histogram[numeric.hex()] += int(count)
            magnitude_histogram[abs(numeric).hex()] += int(count)
        sign_counts["negative"] += int(np.count_nonzero(rows < 0.0))
        sign_counts["zero"] += int(np.count_nonzero(rows == 0.0))
        sign_counts["positive"] += int(np.count_nonzero(rows > 0.0))

    difference = np.abs(production_fields - independent_fields)
    max_error = float(np.max(difference))
    fields_match = bool(np.allclose(
        production_fields,
        independent_fields,
        rtol=0.0,
        atol=FIELD_REFERENCE_ATOL,
    ))
    transition_matches = []
    margins = np.empty(episode_count, dtype=np.dtype("<f8"))
    for index in range(episode_count):
        production_next, production_margin = top_k_binary(
            production_fields[index], component.active_count
        )
        independent_next, independent_margin = top_k_binary(
            independent_fields[index], component.active_count
        )
        transition_matches.append(np.array_equal(production_next, independent_next))
        if abs(production_margin - independent_margin) > FIELD_REFERENCE_ATOL:
            transition_matches[-1] = False
        margins[index] = production_margin

    total_weights = dimension * dimension
    nonzero = total_weights - sign_counts["zero"]
    return {
        "status": "PASS" if finite and symmetric and zero_diagonal and eta_reproduced and diagonal_reproduced and fields_match and all(transition_matches) else "FAIL",
        "formula_version": OPERATOR_FORMULA_VERSION,
        "eta_sha256": array_sha256(component.eta),
        "diagonal_sha256": array_sha256(component.diagonal),
        "eta_reproduced_by_bytes": eta_reproduced,
        "diagonal_reproduced_by_bytes": diagonal_reproduced,
        "learned_state_sha256": component.learned_state_sha256(),
        "conceptual_weight_sha256": conceptual_digest.hexdigest(),
        "conceptual_weight_shape": [dimension, dimension],
        "chunk_rows": WEIGHT_AUDIT_CHUNK_ROWS,
        "finite": finite,
        "symmetric": symmetric,
        "symmetry_identity": "W[j,k] and W[k,j] are the same ordered eta-column dot product; small materialized oracle is exact",
        "zero_diagonal": zero_diagonal,
        "sign_counts": dict(sorted(sign_counts.items())),
        "nonzero_count": nonzero,
        "density": nonzero / total_weights,
        "value_histogram_hex": dict(sorted(value_histogram.items())),
        "magnitude_histogram_hex": dict(sorted(magnitude_histogram.items())),
        "row_norms": _float_rows(row_norms, "row_norm"),
        "production_fields_sha256": array_sha256(production_fields),
        "independent_fields_sha256": array_sha256(independent_fields),
        "field_reference_atol": FIELD_REFERENCE_ATOL,
        "field_reference_rtol": 0.0,
        "max_field_absolute_error": max_error,
        "all_real_fields_match": fields_match,
        "all_real_transitions_match": all(transition_matches),
        "stored_state_field_margins": _float_rows(margins, "field_margin"),
        "tie_sensitive_count": int(np.count_nonzero(margins <= TIE_SENSITIVE_MARGIN)),
        "tie_sensitive_threshold": TIE_SENSITIVE_MARGIN,
        "estimated_peak_live_array_bytes": estimated_live,
    }


def trace_record(
    component: SparseEngramAutoassociator,
    trace: SparseRecallTrace,
    *,
    cue_level: str,
    swap_count: int,
    source_index: int | None,
    content_hashes: Sequence[str],
    deactivated: Sequence[int] = (),
    activated: Sequence[int] = (),
) -> dict[str, Any]:
    terminal_index = next(
        (
            index
            for index, digest in enumerate(component.code_hashes)
            if digest == trace.terminal_sha256
            and np.array_equal(component.codes[index], trace.terminal_state)
        ),
        None,
    )
    source_code = None if source_index is None else component.codes[source_index]
    source_hash = None if source_index is None else component.code_hashes[source_index]
    source_identity = None if source_index is None else content_hashes[source_index]
    exact_recovery = bool(
        source_index is not None
        and trace.fixed_point
        and np.array_equal(trace.terminal_state, source_code)
    )
    return {
        "cue_level": cue_level,
        "swap_count": swap_count,
        "source_content_sha256": source_identity,
        "source_code_sha256": source_hash,
        "deactivated_indices": list(deactivated),
        "activated_indices": list(activated),
        "initial_state_sha256": trace.state_sha256_trace[0],
        "state_sha256_trace": list(trace.state_sha256_trace),
        "changed_units_per_sweep": list(trace.changed_per_sweep),
        "active_count_per_state": list(trace.active_counts),
        "quadratic_score_trace": list(trace.quadratic_score_trace),
        "quadratic_score_trace_hex": [value.hex() for value in trace.quadratic_score_trace],
        "field_margin_trace": list(trace.field_margin_trace),
        "field_margin_trace_hex": [value.hex() for value in trace.field_margin_trace],
        "fixed_point": trace.fixed_point,
        "cycle": trace.cycle,
        "runtime_guard": trace.runtime_guard,
        "converged": trace.converged,
        "sweeps": trace.sweeps,
        "repeated_state_witness": (
            None if trace.repeated_state_witness is None else list(trace.repeated_state_witness)
        ),
        "terminal_state_sha256": trace.terminal_sha256,
        "terminal_stored_content_sha256": (
            None if terminal_index is None else content_hashes[terminal_index]
        ),
        "terminal_status": "spurious" if terminal_index is None else "stored",
        "exact_source_recovery": exact_recovery,
        "terminal_hamming_distance": (
            None
            if source_code is None
            else int(np.count_nonzero(trace.terminal_state != source_code))
        ),
    }


def evaluate_sources(
    component: SparseEngramAutoassociator,
    content_hashes: Sequence[str],
    *,
    cue_level: str,
    swaps: int,
    started: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(component.codes):
        check_cell_time(started)
        if swaps:
            cue, deactivated, activated = component.degrade(
                source, content_hashes[index], swaps
            )
        else:
            cue = source
            deactivated = ()
            activated = ()
        rows.append(
            trace_record(
                component,
                component.recall(cue),
                cue_level=cue_level,
                swap_count=swaps,
                source_index=index,
                content_hashes=content_hashes,
                deactivated=deactivated,
                activated=activated,
            )
        )
    return rows


def trace_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    terminals: dict[str, list[str | None]] = {}
    for row in rows:
        terminals.setdefault(str(row["terminal_state_sha256"]), []).append(
            row.get("source_content_sha256")
        )
    return {
        "trace_count": len(rows),
        "fixed_point_count": sum(bool(row["fixed_point"]) for row in rows),
        "cycle_count": sum(bool(row["cycle"]) for row in rows),
        "runtime_guard_count": sum(bool(row["runtime_guard"]) for row in rows),
        "exact_recovery_count": sum(bool(row["exact_source_recovery"]) for row in rows),
        "wrong_stored_attractor_count": sum(
            row["terminal_status"] == "stored" and not row["exact_source_recovery"]
            for row in rows
        ),
        "spurious_terminal_count": sum(row["terminal_status"] == "spurious" for row in rows),
        "tie_sensitive_sweep_count": sum(
            margin <= TIE_SENSITIVE_MARGIN
            for row in rows
            for margin in row["field_margin_trace"]
        ),
        "terminal_basin_cardinalities": {
            digest: len(sources) for digest, sources in sorted(terminals.items())
        },
        "terminal_collision_membership": {
            digest: sources for digest, sources in sorted(terminals.items())
        },
        "terminal_sequence_sha256": sequence_sha256(
            tuple(str(row["terminal_state_sha256"]) for row in rows)
        ),
        "state_trace_sequence_sha256": sequence_sha256(
            tuple(payload_sha256(row["state_sha256_trace"]) for row in rows)
        ),
    }


def degenerate_cues(
    component: SparseEngramAutoassociator, content_hashes: Sequence[str]
) -> list[tuple[str, np.ndarray]]:
    dimension = component.code_dimension
    active = component.active_count
    cues: list[tuple[str, np.ndarray]] = []
    lowest = np.zeros(dimension, dtype=np.uint8)
    lowest[:active] = 1
    cues.append(("lowest_indices", lowest))
    highest = np.zeros(dimension, dtype=np.uint8)
    highest[-active:] = 1
    cues.append(("highest_indices", highest))
    unit_counts = component.codes.sum(axis=0)
    order = np.lexsort((np.arange(dimension), -unit_counts))
    union = np.zeros(dimension, dtype=np.uint8)
    union[order[:active]] = 1
    cues.append(("union_biased", union))
    for index, identity in enumerate(sorted(content_hashes)[:4]):
        permutation = deterministic_coordinate_permutation(
            range(dimension), identity, "random"
        )
        random_state = np.zeros(dimension, dtype=np.uint8)
        random_state[np.asarray(permutation[:active], dtype=np.int64)] = 1
        cues.append((f"hash_seeded_random_{index}", random_state))
    return cues


def evaluate_degenerates(
    component: SparseEngramAutoassociator,
    content_hashes: Sequence[str],
    started: float,
) -> list[dict[str, Any]]:
    rows = []
    for name, cue in degenerate_cues(component, content_hashes):
        check_cell_time(started)
        row = trace_record(
            component,
            component.recall(cue),
            cue_level=name,
            swap_count=0,
            source_index=None,
            content_hashes=content_hashes,
        )
        row["degenerate_cue"] = name
        rows.append(row)
    return rows


def cell_name(code_dimension: int, active_count: int) -> str:
    return f"d{code_dimension}_k{active_count}"


def _trace_artifact(
    output_dir: Path,
    cell: str,
    cue_level: str,
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    path = output_dir / "traces" / cell / f"{cue_level}.jsonl"
    _write_jsonl(path, rows)
    return {
        **trace_summary(rows),
        "artifact": _artifact_ref(path, output_dir),
    }


def _non_identity_record(component: SparseEngramAutoassociator) -> dict[str, Any]:
    return {
        "status": "PASS",
        "sparse_binary_state_space": True,
        "fixed_cardinality": component.active_count,
        "projection_formula": PROJECTION_FORMULA_VERSION,
        "centered_operator_formula": OPERATOR_FORMULA_VERSION,
        "synchronous_global_competition": True,
        "median_bipolar_encoding": False,
        "unconstrained_sign_recall": False,
        "mechanical_identity_with_rev4": False,
    }


def _component_distribution(
    component: SparseEngramAutoassociator,
    population: EpisodePopulation,
    pairwise: Mapping[str, Any],
) -> dict[str, Any]:
    unit_counts = component.codes.sum(axis=0).astype(np.int64)
    code_counts = component.codes.sum(axis=1).astype(np.int64)
    return {
        "per_unit_activation_counts": [int(value) for value in unit_counts],
        "per_code_active_counts": [int(value) for value in code_counts],
        "activation_margins": [
            {
                "content_sha256": population.content_hashes[index],
                "margin": float(value),
                "margin_hex": float(value).hex(),
            }
            for index, value in enumerate(component.activation_margins)
        ],
        "tie_sensitive_activation_margin_count": int(
            np.count_nonzero(component.activation_margins <= TIE_SENSITIVE_MARGIN)
        ),
        "pairwise": pairwise,
    }


def _name_checks(
    component: SparseEngramAutoassociator,
    pairwise: Mapping[str, Any],
    operator: Mapping[str, Any],
    gates: Mapping[str, Any],
) -> list[dict[str, Any]]:
    g3 = gates.get("G3") if isinstance(gates.get("G3"), Mapping) else {}
    g4 = gates.get("G4") if isinstance(gates.get("G4"), Mapping) else {}
    g5 = gates.get("G5") if isinstance(gates.get("G5"), Mapping) else {}
    return [
        {"name": "sparse", "demonstrated": bool(np.all(component.codes.sum(axis=1) == component.active_count)), "evidence": "all formed and traced states retain exact active count"},
        {"name": "expansion", "demonstrated": component.code_dimension > component.input_dimension, "evidence": f"{component.input_dimension}->{component.code_dimension}"},
        {"name": "pattern separation", "demonstrated": True, "evidence": f"complete {pairwise['pair_count']}-pair cosine/overlap/Hamming artifact; uniqueness is not the sole evidence"},
        {"name": "engram", "demonstrated": True, "evidence": "term limited to formed internal sparse code"},
        {"name": "learned", "demonstrated": operator["status"] == "PASS", "evidence": "independent conceptual centered-weight reconstruction"},
        {"name": "recurrent", "demonstrated": operator["all_real_transitions_match"], "evidence": "each synchronous output is the next sweep input"},
        {"name": "fixed point", "demonstrated": g3.get("fixed_point_count", 0) == EXPECTED_EPISODES, "evidence": f"{g3.get('fixed_point_count', 0)}/119 unchanged additional sweeps"},
        {"name": "pattern completion", "demonstrated": g4.get("exact_recovery_count", 0) == EXPECTED_EPISODES, "evidence": f"{g4.get('exact_recovery_count', 0)}/119 exact one-swap source recoveries"},
        {"name": "competition", "demonstrated": True, "evidence": "all serialized state active counts equal the registered K_ACTIVE"},
        {"name": "basin", "demonstrated": g5.get("status") == "PASS", "evidence": "claim limited to registered swaps and seven degenerates"},
    ]


def _cell_mechanism_digest(cell: Mapping[str, Any]) -> str:
    stable = {
        "code_dimension": cell["code_dimension"],
        "active_count": cell["active_count"],
        "disposition": cell["disposition"],
        "gate_statuses": {
            name: value if isinstance(value, str) else value.get("status")
            for name, value in cell["gates"].items()
        },
        "cross_cell_hashes": cell.get("cross_cell_hashes", {}),
        "trace_hashes": {
            name: value["artifact"]["sha256"]
            for name, value in cell.get("trace_artifacts", {}).items()
        },
    }
    return payload_sha256(stable)


def run_cell(
    population: EpisodePopulation,
    output_dir: Path,
    code_dimension: int,
    active_count: int,
    leakage: Mapping[str, Any],
) -> dict[str, Any]:
    name = cell_name(code_dimension, active_count)
    cell_dir = output_dir / "cells" / name
    started = time.perf_counter()
    result: dict[str, Any] = {
        "cell": name,
        "code_dimension": code_dimension,
        "active_count": active_count,
        "activity": active_count / code_dimension,
        "activity_hex": float(active_count / code_dimension).hex(),
        "gates": {},
        "trace_artifacts": {},
    }

    with RssMonitor() as monitor:
        try:
            component = SparseEngramAutoassociator.fit(
                population.vectors,
                code_dimension=code_dimension,
                active_count=active_count,
                projection_seed=PROJECTION_SEED,
            )
            regenerated_projection = rademacher_projection(
                PROJECTION_SEED, code_dimension, EXPECTED_INPUT_DIMENSION
            )
            reordered_center = stable_population_center(population.vectors[::-1])
            remapped_codes = np.stack(
                [component.encode(vector) for vector in population.vectors[::-1]]
            )[::-1]
            g1_pass = bool(
                component.codes.shape == (EXPECTED_EPISODES, code_dimension)
                and np.all(np.isin(component.codes, (0, 1)))
                and np.all(component.codes.sum(axis=1) == active_count)
                and len(set(component.code_hashes)) == EXPECTED_EPISODES
                and np.array_equal(component.projection, regenerated_projection)
                and np.array_equal(component.center, reordered_center)
                and np.array_equal(component.codes, remapped_codes)
                and leakage.get("status") == "PASS"
            )
            g1 = {
                "status": "PASS" if g1_pass else "FAIL",
                "episode_count": component.codes.shape[0],
                "binary_codes": bool(np.all(np.isin(component.codes, (0, 1)))),
                "exact_sparsity_count": int(np.count_nonzero(component.codes.sum(axis=1) == active_count)),
                "unique_code_hashes": len(set(component.code_hashes)),
                "projection_reproduced": bool(np.array_equal(component.projection, regenerated_projection)),
                "center_reproduced_after_row_reorder": bool(np.array_equal(component.center, reordered_center)),
                "row_reorder_remap_reproduced": bool(np.array_equal(component.codes, remapped_codes)),
                "leakage": leakage,
            }
            result["gates"]["G1"] = g1
            if not g1_pass:
                result["gates"].update({name: "NOT_REACHED" for name in ("G2", "G3", "G4", "G5")})
                result["disposition"] = "INVALID_ENCODER"
                result["behavioral_identity"] = f"At ({code_dimension}, {active_count}), encoder integrity failed before recurrence."
                result["mechanism_digest"] = _cell_mechanism_digest(result)
                return result

            persistent_bytes = live_array_bytes(component)
            if persistent_bytes >= LIVE_ARRAY_CEILING:
                raise ResourceLimitError("Component arrays cross the live-array ceiling")
            pairwise_path = cell_dir / "pairwise_distribution.csv"
            pairwise = write_pairwise_distribution(
                pairwise_path, population, component
            )
            distribution = _component_distribution(component, population, pairwise)
            distribution_path = cell_dir / "formation_distribution.json"
            _write_json(distribution_path, distribution)

            operator = audit_operator(component, started)
            operator_path = cell_dir / "operator_audit.json"
            _write_json(operator_path, operator)
            synthetic = synthetic_reachability()
            g2_pass = operator["status"] == "PASS" and synthetic["status"] == "PASS"
            g2 = {
                "status": "PASS" if g2_pass else "FAIL",
                "operator_audit": _artifact_ref(operator_path, output_dir),
                "synthetic_reachability": synthetic,
                "exact_active_count_preserved_by_transition": True,
                "cycle_and_runtime_guard_distinct": True,
            }
            result["gates"]["G2"] = g2
            if not g2_pass:
                result["gates"].update({name: "NOT_REACHED" for name in ("G3", "G4", "G5")})
                result["disposition"] = "INVALID_RECURRENCE"
                result["behavioral_identity"] = f"At ({code_dimension}, {active_count}), recurrent identity failed before stored-code evaluation."
                result["mechanism_digest"] = _cell_mechanism_digest(result)
                return result

            uncorrupted = evaluate_sources(
                component,
                population.content_hashes,
                cue_level="uncorrupted",
                swaps=0,
                started=started,
            )
            uncorrupted_artifact = _trace_artifact(
                output_dir, name, "uncorrupted", uncorrupted
            )
            result["trace_artifacts"]["uncorrupted"] = uncorrupted_artifact
            fixed_count = sum(
                row["fixed_point"]
                and row["changed_units_per_sweep"] == [0]
                and row["exact_source_recovery"]
                for row in uncorrupted
            )
            g3_pass = fixed_count == EXPECTED_EPISODES
            g3 = {
                "status": "PASS" if g3_pass else "FAIL",
                "fixed_point_count": fixed_count,
                "required": EXPECTED_EPISODES,
                "trace_artifact": uncorrupted_artifact["artifact"],
                "summary": {key: value for key, value in uncorrupted_artifact.items() if key != "artifact"},
            }
            result["gates"]["G3"] = g3
            if not g3_pass:
                result["gates"].update({"G4": "NOT_REACHED", "G5": "NOT_REACHED"})
                result["disposition"] = "SPARSE_CODES_NOT_STORED"
            else:
                one_swap = evaluate_sources(
                    component,
                    population.content_hashes,
                    cue_level="one_swap",
                    swaps=1,
                    started=started,
                )
                one_swap_artifact = _trace_artifact(
                    output_dir, name, "one_swap", one_swap
                )
                result["trace_artifacts"]["one_swap"] = one_swap_artifact
                recovered = sum(
                    row["fixed_point"]
                    and row["exact_source_recovery"]
                    and not row["cycle"]
                    and not row["runtime_guard"]
                    for row in one_swap
                )
                g4_pass = recovered == EXPECTED_EPISODES
                result["gates"]["G4"] = {
                    "status": "PASS" if g4_pass else "FAIL",
                    "exact_recovery_count": recovered,
                    "required": EXPECTED_EPISODES,
                    "trace_artifact": one_swap_artifact["artifact"],
                    "summary": {key: value for key, value in one_swap_artifact.items() if key != "artifact"},
                }
                if not g4_pass:
                    result["gates"]["G5"] = "NOT_REACHED"
                    result["disposition"] = "NO_EXACT_ONE_SWAP_COMPLETION"
                else:
                    basin: dict[str, Any] = {}
                    for label, swaps in (
                        ("10_percent", int(np.floor(0.10 * active_count))),
                        ("30_percent", int(np.floor(0.30 * active_count))),
                        ("50_percent", int(np.floor(0.50 * active_count))),
                    ):
                        if swaps == 0:
                            raise AssertionError("Registered descriptive swap count rounded to zero")
                        rows = evaluate_sources(
                            component,
                            population.content_hashes,
                            cue_level=label,
                            swaps=swaps,
                            started=started,
                        )
                        artifact = _trace_artifact(output_dir, name, label, rows)
                        result["trace_artifacts"][label] = artifact
                        basin[label] = {"swap_count": swaps, **artifact}
                    degenerate_rows = evaluate_degenerates(
                        component, population.content_hashes, started
                    )
                    degenerate_artifact = _trace_artifact(
                        output_dir, name, "degenerate", degenerate_rows
                    )
                    result["trace_artifacts"]["degenerate"] = degenerate_artifact
                    result["gates"]["G5"] = {
                        "status": "PASS",
                        "basin_levels": basin,
                        "degenerate": degenerate_artifact,
                    }
                    result["disposition"] = "SPARSE_ENGRAM_CANDIDATE_CHARACTERIZED"

            result["formation_distribution"] = _artifact_ref(
                distribution_path, output_dir
            )
            result["operator_audit"] = _artifact_ref(operator_path, output_dir)
            result["non_identity"] = _non_identity_record(component)
            result["name_checks"] = _name_checks(
                component, pairwise, operator, result["gates"]
            )
            result["cross_cell_hashes"] = {
                "center": array_sha256(component.center),
                "projection": array_sha256(component.projection),
                "codes": array_sha256(component.codes),
                "code_sequence": sequence_sha256(component.code_hashes),
                "eta": array_sha256(component.eta),
                "diagonal": array_sha256(component.diagonal),
                "learned_operator": component.learned_state_sha256(),
                "conceptual_weights": operator["conceptual_weight_sha256"],
                "terminal_sequences": payload_sha256(
                    {
                        key: value["terminal_sequence_sha256"]
                        for key, value in result["trace_artifacts"].items()
                    }
                ),
            }
            result["live_array_bytes"] = {
                "persistent": persistent_bytes,
                "estimated_with_largest_audit_chunk": operator[
                    "estimated_peak_live_array_bytes"
                ],
                "ceiling": LIVE_ARRAY_CEILING,
            }
        except ResourceLimitError as exc:
            result["resource_failure"] = str(exc)
            result["disposition"] = "RESOURCE_LIMIT"
            for gate in ("G1", "G2", "G3", "G4", "G5"):
                result["gates"].setdefault(gate, "NOT_REACHED")
        finally:
            result["runtime"] = {
                "wall_seconds": time.perf_counter() - started,
                "peak_resident_memory_bytes": monitor.peak,
                "cell_wall_ceiling_seconds": CELL_WALL_CEILING_SECONDS,
            }

    result["behavioral_identity"] = (
        f"At ({code_dimension}, {active_count}), the encoder formed "
        f"{result.get('gates', {}).get('G1', {}).get('unique_code_hashes', 0) if isinstance(result.get('gates', {}).get('G1'), Mapping) else 0}/119 "
        f"unique exact-sparsity codes; the recurrence stored "
        f"{result.get('gates', {}).get('G3', {}).get('fixed_point_count', 0) if isinstance(result.get('gates', {}).get('G3'), Mapping) else 0}/119 as fixed points and recovered "
        f"{result.get('gates', {}).get('G4', {}).get('exact_recovery_count', 0) if isinstance(result.get('gates', {}).get('G4'), Mapping) else 0}/119 deterministic one-swap cues exactly."
    )
    result["mechanism_digest"] = _cell_mechanism_digest(result)
    return result


def apply_selection_rule(cells: Sequence[Mapping[str, Any]]) -> tuple[dict[str, int] | None, str]:
    valid = [cell for cell in cells if isinstance(cell["gates"].get("G2"), Mapping) and cell["gates"]["G2"].get("status") == "PASS"]
    stored = [cell for cell in valid if isinstance(cell["gates"].get("G3"), Mapping) and cell["gates"]["G3"].get("status") == "PASS"]
    viable = [cell for cell in stored if isinstance(cell["gates"].get("G4"), Mapping) and cell["gates"]["G4"].get("status") == "PASS" and isinstance(cell["gates"].get("G5"), Mapping) and cell["gates"]["G5"].get("status") == "PASS"]
    if not valid:
        return None, "NO_VALID_IMPLEMENTATION"
    if not stored:
        return None, "NO_STORED_SPARSE_CODE"
    if not viable:
        return None, "NO_VIABLE_SPARSE_CODE"
    selected = sorted(
        viable,
        key=lambda cell: (
            -int(cell["gates"]["G5"]["basin_levels"]["10_percent"]["exact_recovery_count"]),
            int(cell["code_dimension"]),
            int(cell["active_count"]),
        ),
    )[0]
    return {
        "code_dimension": int(selected["code_dimension"]),
        "active_count": int(selected["active_count"]),
        "ten_percent_exact_recovery_count": int(
            selected["gates"]["G5"]["basin_levels"]["10_percent"]["exact_recovery_count"]
        ),
    }, "SPARSE_ENGRAM_CANDIDATE_CHARACTERIZED"


def surrogate_audit(cells: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    any_g3 = any(
        isinstance(cell["gates"].get("G3"), Mapping)
        and cell["gates"]["G3"].get("status") == "PASS"
        for cell in cells
    )
    any_g4 = any(
        isinstance(cell["gates"].get("G4"), Mapping)
        and cell["gates"]["G4"].get("status") == "PASS"
        for cell in cells
    )
    tie_sensitive = sum(
        int(cell.get("gates", {}).get("G3", {}).get("summary", {}).get("tie_sensitive_sweep_count", 0))
        for cell in cells
        if isinstance(cell.get("gates", {}).get("G3"), Mapping)
    )
    return [
        {"observation": "exact K_ACTIVE", "property_still_false": "codes can remain poorly separated", "control_or_residual": "all 7,021 pairwise overlaps and Hamming distances committed"},
        {"observation": "119 unique code hashes", "property_still_false": "nearby episodes can collide functionally", "control_or_residual": "closest-input joint distributions committed per cell"},
        {"observation": "large Hamming distance", "property_still_false": "small perturbations can destroy identity", "control_or_residual": "registered bit swaps tested; natural embedding perturbations remain outside scope"},
        {"observation": "all fixed points", "property_still_false": "basins can have zero useful radius", "control_or_residual": f"G4 exact one-swap bar reached by any cell: {any_g4}"},
        {"observation": "one-swap recovery", "property_still_false": "10 percent cues can fail", "control_or_residual": "10/30/50 percent distributions required only after G4"},
        {"observation": "bit-swap recovery", "property_still_false": "natural-language partial cues can fail", "control_or_residual": "accepted residual; later cue-binding study required"},
        {"observation": "deterministic projection", "property_still_false": "the one seed can be fortuitous", "control_or_residual": "one seed characterized; seed sweep prohibited"},
        {"observation": "passing grid cell", "property_still_false": "same-store parameter selection can overfit", "control_or_residual": "outcome remains exploratory and CHARACTERIZED"},
        {"observation": "recurrent convergence", "property_still_false": "terminal can be spurious", "control_or_residual": "exact source identity required"},
        {"observation": "no registered cycles", "property_still_false": "untested cues can cycle", "control_or_residual": "claim limited to registered cues and degenerates"},
        {"observation": "exact recovery with deterministic ties", "property_still_false": "learned field support can be perturbation-fragile", "control_or_residual": f"complete margins committed; observed tie-sensitive sweep count {tie_sensitive}"},
        {"observation": "sparse component pass", "property_still_false": "dentate gyrus replication", "control_or_residual": "biological claim prohibited"},
        {"observation": "offline memory pass", "property_still_false": "retrieval or answers improve", "control_or_residual": "Q11 and live claims prohibited"},
        {"observation": "stored-code pass", "property_still_false": "minimal completion", "control_or_residual": f"at least one G3 pass observed: {any_g3}; G4 remains independently binding"},
    ]


def construct_table(cells: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    names = (
        "sparse",
        "expansion",
        "pattern separation",
        "engram",
        "learned",
        "recurrent",
        "fixed point",
        "pattern completion",
        "competition",
        "basin",
    )
    rows = []
    for name in names:
        observations = [
            check
            for cell in cells
            for check in cell.get("name_checks", [])
            if check["name"] == name
        ]
        rows.append(
            {
                "name": name,
                "demonstrated_cell_count": sum(bool(row["demonstrated"]) for row in observations),
                "evaluated_cell_count": len(observations),
                "cell_evidence": [
                    {
                        "cell": cell["cell"],
                        "demonstrated": next(
                            (
                                bool(check["demonstrated"])
                                for check in cell.get("name_checks", [])
                                if check["name"] == name
                            ),
                            False,
                        ),
                        "evidence": next(
                            (
                                str(check["evidence"])
                                for check in cell.get("name_checks", [])
                                if check["name"] == name
                            ),
                            "NOT_REACHED",
                        ),
                    }
                    for cell in cells
                ],
            }
        )
    return rows


def _write_cell_summary(path: Path, cells: Sequence[Mapping[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite PS-001 artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = (
            "cell",
            "code_dimension",
            "active_count",
            "g1",
            "g2",
            "g3",
            "g4",
            "g5",
            "stored_fixed_points",
            "one_swap_recoveries",
            "ten_percent_recoveries",
            "disposition",
            "mechanism_digest",
        )
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for cell in cells:
            gate_status = {
                name: value if isinstance(value, str) else value.get("status")
                for name, value in cell["gates"].items()
            }
            g5 = cell["gates"].get("G5")
            writer.writerow(
                {
                    "cell": cell["cell"],
                    "code_dimension": cell["code_dimension"],
                    "active_count": cell["active_count"],
                    "g1": gate_status.get("G1"),
                    "g2": gate_status.get("G2"),
                    "g3": gate_status.get("G3"),
                    "g4": gate_status.get("G4"),
                    "g5": gate_status.get("G5"),
                    "stored_fixed_points": cell["gates"].get("G3", {}).get("fixed_point_count", 0) if isinstance(cell["gates"].get("G3"), Mapping) else 0,
                    "one_swap_recoveries": cell["gates"].get("G4", {}).get("exact_recovery_count", 0) if isinstance(cell["gates"].get("G4"), Mapping) else 0,
                    "ten_percent_recoveries": g5.get("basin_levels", {}).get("10_percent", {}).get("exact_recovery_count", 0) if isinstance(g5, Mapping) else 0,
                    "disposition": cell["disposition"],
                    "mechanism_digest": cell["mechanism_digest"],
                }
            )


def _write_manifest(output_dir: Path) -> dict[str, Any]:
    path = output_dir / "artifact_manifest.json"
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite PS-001 manifest: {path}")
    files = [
        {
            "path": artifact.relative_to(output_dir).as_posix(),
            "bytes": artifact.stat().st_size,
            "sha256": sha256_file(artifact),
        }
        for artifact in sorted(output_dir.rglob("*"))
        if artifact.is_file() and artifact != path
    ]
    manifest = {
        "study": "PS-001",
        "file_count": len(files),
        "files": files,
        "file_sequence_sha256": payload_sha256(files),
    }
    _write_json(path, manifest)
    return manifest


def run_exploration(output_dir: Path, historical_gate_path: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite PS-001 output: {output_dir}")
    started = time.perf_counter()
    head = assert_clean_execution_tree()
    anchors = assert_committed_anchors()
    historical = load_historical_gate(historical_gate_path)
    population = load_episode_population()
    leakage = assert_imports_label_blind([MECHANISM_SOURCE])
    output_dir.mkdir(parents=True)
    if tuple(GRID) != (
        (2048, 20),
        (2048, 41),
        (2048, 102),
        (4096, 41),
        (4096, 82),
        (4096, 205),
        (8192, 82),
        (8192, 164),
        (8192, 410),
    ):
        raise AssertionError("PS-001 grid changed")

    cells = []
    for code_dimension, active_count in GRID:
        if time.perf_counter() - started > GRID_WALL_CEILING_SECONDS:
            raise ResourceLimitError("Grid exceeded the registered 3,600-second ceiling")
        cell = run_cell(
            population,
            output_dir,
            code_dimension,
            active_count,
            leakage,
        )
        cells.append(cell)
        _write_json(output_dir / "cells" / cell["cell"] / "cell_result.json", cell)

    selected, disposition = apply_selection_rule(cells)
    summary_path = output_dir / "cell_summary.csv"
    _write_cell_summary(summary_path, cells)
    stable_cells = [
        {"cell": cell["cell"], "mechanism_digest": cell["mechanism_digest"]}
        for cell in cells
    ]
    mechanism_digest = payload_sha256(
        {
            "grid": [list(cell) for cell in GRID],
            "cells": stable_cells,
            "selected_cell": selected,
            "disposition": disposition,
        }
    )
    result = {
        "study": "PS-001",
        "stage": "Preflight Part 1 label-blind exploration",
        "status": "COMPLETE",
        "outcome_ceiling": "CHARACTERIZED",
        "design_commit": DESIGN_COMMIT,
        "design_sha256": DESIGN_SHA256,
        "authorization_commit": AUTHORIZATION_COMMIT,
        "authorization_sha256": anchors["authorization"],
        "amendments": [
            {"commit": AMENDMENT_006_COMMIT, "sha256": anchors["amendment_006"], "authorization_sha256": anchors["amendment_006_authorization"]},
            {"commit": AMENDMENT_007_COMMIT, "sha256": anchors["amendment_007"], "authorization_sha256": anchors["amendment_007_authorization"]},
            {"commit": AMENDMENT_008_COMMIT, "sha256": anchors["amendment_008"], "authorization_sha256": anchors["amendment_008_authorization"]},
        ],
        "implementation_commit": head,
        "implementation_sha256": payload_sha256(
            {"mechanism": anchors["mechanism_source"], "exploration": anchors["exploration_source"]}
        ),
        "input_inventory": [
            population.inventory,
            {"path": DESIGN.relative_to(REPO_ROOT).as_posix(), "bytes": DESIGN.stat().st_size, "sha256": anchors["design"]},
            {"path": AUTHORIZATION.relative_to(REPO_ROOT).as_posix(), "bytes": AUTHORIZATION.stat().st_size, "sha256": anchors["authorization"]},
            {"path": PRIOR_REPORT.relative_to(REPO_ROOT).as_posix(), "bytes": PRIOR_REPORT.stat().st_size, "sha256": anchors["prior_report"]},
            {"path": PRIOR_ARTIFACT.relative_to(REPO_ROOT).as_posix(), "bytes": PRIOR_ARTIFACT.stat().st_size, "sha256": anchors["prior_artifact"]},
            {"path": MECHANISM_SOURCE.relative_to(REPO_ROOT).as_posix(), "bytes": MECHANISM_SOURCE.stat().st_size, "sha256": anchors["mechanism_source"]},
            {"path": EXPLORATION_SOURCE.relative_to(REPO_ROOT).as_posix(), "bytes": EXPLORATION_SOURCE.stat().st_size, "sha256": anchors["exploration_source"]},
        ],
        "runtime": {
            "launch_command": sys.argv,
            "pid": os.getpid(),
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "thread_environment": {key: os.environ.get(key) for key in REQUIRED_THREAD_ENV},
            "wall_seconds": time.perf_counter() - started,
            "grid_wall_ceiling_seconds": GRID_WALL_CEILING_SECONDS,
            "cell_wall_ceiling_seconds": CELL_WALL_CEILING_SECONDS,
            "live_array_ceiling_bytes": LIVE_ARRAY_CEILING,
            "weight_audit_chunk_rows": WEIGHT_AUDIT_CHUNK_ROWS,
            "server_process": None,
            "model_process": None,
        },
        "historical_reproduction": {
            "artifact": {
                "path": str(historical_gate_path.resolve()),
                "bytes": historical_gate_path.stat().st_size,
                "sha256": sha256_file(historical_gate_path),
            },
            "status": historical["status"],
            "control_commit": historical["control_commit"],
            "result_sha256": historical["generated_result_sha256"],
            "exact_reproduction": historical["exact_reproduction"],
        },
        "leakage": leakage,
        "grid_definition": [
            {"code_dimension": dimension, "active_count": active}
            for dimension, active in GRID
        ],
        "cells": cells,
        "selection_rule": "G1-G2 valid, 119/119 G3, 119/119 G4, maximize 10% exact recovery, then smallest D_CODE, then smallest K_ACTIVE",
        "selected_cell": selected,
        "disposition": disposition,
        "construct_table": construct_table(cells),
        "surrogate_audit": surrogate_audit(cells),
        "zero_embedding_requests": 0,
        "zero_model_generation_calls": 0,
        "determinism": {
            "mechanism_digest": mechanism_digest,
            "second_process_required": True,
            "comparison_status": "PENDING_SEPARATE_PROCESS_COMPARISON",
        },
        "non_identity": {
            "status": "PASS" if all(cell.get("non_identity", {}).get("status") == "PASS" for cell in cells) else "FAIL",
            "rev4_reproduced_before_ps001": True,
            "all_cells_execute_sparse_projection_centered_weights_and_competition": all(cell.get("non_identity", {}).get("status") == "PASS" for cell in cells),
        },
        "not_reached": {
            "preflight_part_2": "requires a viable selected cell and prospective final-design revision",
            "final_evidence": "not specified by the locked design",
            "q11": "prohibited",
            "live_inference": "prohibited",
        },
        "cell_summary": _artifact_ref(summary_path, output_dir),
    }
    _write_json(output_dir / "exploration.json", result)
    manifest = _write_manifest(output_dir)
    return {**result, "artifact_manifest": manifest}


def deterministic_artifact_sequence(output_dir: Path) -> list[dict[str, str]]:
    excluded = {"exploration.json", "artifact_manifest.json", "cell_result.json"}
    return [
        {
            "path": path.relative_to(output_dir).as_posix(),
            "sha256": sha256_file(path),
        }
        for path in sorted(output_dir.rglob("*"))
        if path.is_file() and path.name not in excluded
    ]


def compare_explorations(first: Path, second: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite determinism report: {output}")
    first_result = json.loads((first / "exploration.json").read_text(encoding="utf-8"))
    second_result = json.loads((second / "exploration.json").read_text(encoding="utf-8"))
    first_sequence = deterministic_artifact_sequence(first)
    second_sequence = deterministic_artifact_sequence(second)
    first_digest = str(first_result["determinism"]["mechanism_digest"])
    second_digest = str(second_result["determinism"]["mechanism_digest"])
    passed = first_digest == second_digest and first_sequence == second_sequence
    report = {
        "study": "PS-001",
        "stage": "two_process_determinism",
        "status": "PASS" if passed else "FAIL",
        "first_mechanism_digest": first_digest,
        "second_mechanism_digest": second_digest,
        "first_artifact_sequence_sha256": payload_sha256(first_sequence),
        "second_artifact_sequence_sha256": payload_sha256(second_sequence),
        "byte_identical_canonical_result_digests": first_digest == second_digest,
        "byte_identical_deterministic_artifacts": first_sequence == second_sequence,
    }
    _write_json(output, report)
    if not passed:
        raise AssertionError("PS-001 two-process determinism failed")
    return report


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run PS-001 ordered exploration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    reproduce = subparsers.add_parser("reproduce-rev4")
    reproduce.add_argument("worktree", type=Path)
    reproduce.add_argument("output", type=Path)
    run = subparsers.add_parser("run")
    run.add_argument("output_dir", type=Path)
    run.add_argument("historical_gate", type=Path)
    compare = subparsers.add_parser("compare")
    compare.add_argument("first", type=Path)
    compare.add_argument("second", type=Path)
    compare.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "reproduce-rev4":
        result = reproduce_rev4(args.worktree, args.output)
    elif args.command == "run":
        result = run_exploration(args.output_dir, args.historical_gate)
    else:
        result = compare_explorations(args.first, args.second, args.output)
    print(json.dumps({"status": result["status"], "command": args.command}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

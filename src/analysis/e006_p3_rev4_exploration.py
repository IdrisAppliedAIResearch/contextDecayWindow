from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from src.analysis.e006_chained_retrieval_preflight import content_sha256
from src.retrieval_mechanism_ledger.e006_p3 import build_union_knn_graph
from src.retrieval_mechanism_ledger.e006_p3_rev4 import (
    EpisodeAutoassociativeMemory,
    RecallTrace,
    degrade_pattern,
    pattern_sha256,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
)
DESIGN = COMPONENT_ROOT / "E006_PART3_REV4_NEUROSCIENCE_CONSTRUCT_REPAIR.md"
AUTHORIZATION = COMPONENT_ROOT / "E006_PART3_REV4_AUTHORIZATION.md"
AMENDMENT = (
    COMPONENT_ROOT / "amendments" / "AMENDMENT_005_rev4_query_vector_absence.md"
)
PRIOR_REPORT = COMPONENT_ROOT / "E006_PART3_REPORT.md"
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
MECHANISM_SOURCE = (
    REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "e006_p3_rev4.py"
)
EXPLORATION_SOURCE = Path(__file__).resolve()
EXPECTED_DESIGN_SHA256 = (
    "e0f9e188c1992ef662a3fe9db5864d3bc308dc7b31e123bb6c6c862fa4c6db33"
)
EXPECTED_DESIGN_COMMIT = "a4f952f6"
EXPECTED_AUTHORIZATION_COMMIT = "27313b66"
EXPECTED_AMENDMENT_COMMIT = "8c2c0a16"
EXPECTED_IMPLEMENTATION_COMMIT = "942cde4e"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sequence_sha256(values: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(values).encode("ascii")).hexdigest()


def array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    header = json.dumps(
        {"dtype": str(array.dtype), "shape": list(array.shape)},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(header + b"\n" + array.tobytes(order="C")).hexdigest()


def load_episode_vectors() -> tuple[np.ndarray, tuple[str, ...], tuple[int, ...]]:
    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
            """
            SELECT id, turn_number, user_message, assistant_message, embedding
            FROM episodes
            WHERE turn_number < 120
            ORDER BY turn_number, id
            """
        ).fetchall()
    if len(rows) != 119:
        raise AssertionError("Rev 4 requires exactly 119 eligible store episodes")
    episodes = [
        {
            "id": str(row[0]),
            "turn_number": int(row[1]),
            "user_message": str(row[2]),
            "assistant_message": str(row[3]),
            "embedding": row[4],
        }
        for row in rows
    ]
    vectors = np.stack(
        [
            np.frombuffer(row["embedding"], dtype=np.float32).astype(np.float64)
            for row in episodes
        ]
    )
    if vectors.shape[0] != 119 or not np.all(np.isfinite(vectors)):
        raise AssertionError("Eligible episode matrix is malformed")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if np.any(norms == 0.0):
        raise AssertionError("Eligible store contains a zero episode vector")
    vectors /= norms
    hashes = tuple(content_sha256(row) for row in episodes)
    if len(set(hashes)) != 119:
        raise AssertionError("Eligible episode content hashes are not unique")
    turns = tuple(int(row["turn_number"]) for row in episodes)
    return vectors, hashes, turns


def load_memory() -> tuple[EpisodeAutoassociativeMemory, tuple[int, ...], dict[str, Any]]:
    vectors, hashes, turns = load_episode_vectors()
    memory = EpisodeAutoassociativeMemory.from_vectors(vectors, hashes)
    inventory = {
        "episode_count": len(hashes),
        "turn_min": min(turns),
        "turn_max": max(turns),
        "vector_shape": list(vectors.shape),
        "normalized_vector_sha256": array_sha256(vectors),
        "content_sequence_sha256": sequence_sha256(hashes),
        "pattern_matrix_sha256": array_sha256(memory.patterns),
        "pattern_sequence_sha256": sequence_sha256(memory.pattern_hashes),
        "center_sha256": array_sha256(memory.center),
        "weight_matrix_sha256": array_sha256(memory.weights),
    }
    return memory, turns, inventory


def slow_reference_recall(
    weights: np.ndarray, cue: np.ndarray, max_sweeps: int
) -> tuple[np.ndarray, tuple[float, ...], tuple[int, ...]]:
    state = np.asarray(cue, dtype=np.int8).copy()
    energies = [float(-0.5 * state @ weights @ state)]
    changes_by_sweep = []
    for _sweep in range(max_sweeps):
        changes = 0
        for coordinate in range(len(state)):
            field = float(np.dot(weights[coordinate], state))
            old_value = int(state[coordinate])
            state[coordinate] = (
                1 if field > 0.0 else -1 if field < 0.0 else old_value
            )
            changes += int(state[coordinate]) != old_value
        changes_by_sweep.append(changes)
        energies.append(float(-0.5 * state @ weights @ state))
        if changes == 0:
            break
    return state, tuple(energies), tuple(changes_by_sweep)


def synthetic_reachability() -> dict[str, Any]:
    patterns = np.array(
        [
            [1, 1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, -1, -1, -1, -1],
        ],
        dtype=np.int8,
    )
    hashes = (f"{1:064x}", f"{2:064x}")
    memory = EpisodeAutoassociativeMemory.from_patterns(patterns, hashes)
    rows = []
    for pattern_index, pattern in enumerate(memory.patterns):
        stable = memory.recall(pattern)
        recoveries = []
        for coordinate in range(memory.dimension):
            cue = pattern.copy()
            cue[coordinate] *= -1
            trace = memory.recall(cue)
            expected_state, expected_energy, expected_changes = slow_reference_recall(
                memory.weights, cue, memory.dimension
            )
            recoveries.append(
                {
                    "coordinate": coordinate,
                    "exact_source_recovery": bool(
                        trace.matched_pattern_index == pattern_index
                    ),
                    "reference_state_equal": bool(
                        np.array_equal(trace.terminal_state, expected_state)
                    ),
                    "reference_energy_equal": bool(
                        np.array_equal(trace.energy_trace, expected_energy)
                    ),
                    "reference_changes_equal": (
                        trace.changed_per_sweep == expected_changes
                    ),
                }
            )
        rows.append(
            {
                "pattern_index": pattern_index,
                "fixed_point": stable.changed_per_sweep == (0,),
                "recoveries": recoveries,
            }
        )
    passed = all(
        row["fixed_point"]
        and all(
            recovery["exact_source_recovery"]
            and recovery["reference_state_equal"]
            and recovery["reference_energy_equal"]
            and recovery["reference_changes_equal"]
            for recovery in row["recoveries"]
        )
        for row in rows
    )
    return {"status": "PASS" if passed else "FAIL", "rows": rows}


def pattern_distribution(
    memory: EpisodeAutoassociativeMemory, turns: Sequence[int]
) -> dict[str, Any]:
    positive = np.count_nonzero(memory.patterns == 1, axis=1)
    coordinate_positive = np.count_nonzero(memory.patterns == 1, axis=0)
    overlaps = memory.patterns.astype(np.float64) @ memory.patterns.astype(np.float64).T
    overlaps /= memory.dimension
    pairwise = [
        {
            "left_content_sha256": memory.content_hashes[left],
            "right_content_sha256": memory.content_hashes[right],
            "normalized_overlap": float(overlaps[left, right]),
            "hamming_distance": int(
                np.count_nonzero(memory.patterns[left] != memory.patterns[right])
            ),
        }
        for left in range(len(memory.patterns))
        for right in range(left + 1, len(memory.patterns))
    ]
    return {
        "per_pattern": [
            {
                "content_sha256": memory.content_hashes[index],
                "source_turn": int(turns[index]),
                "pattern_sha256": memory.pattern_hashes[index],
                "positive_count": int(positive[index]),
                "positive_fraction": float(positive[index] / memory.dimension),
            }
            for index in range(len(memory.patterns))
        ],
        "per_coordinate_positive_count": [int(value) for value in coordinate_positive],
        "pairwise": pairwise,
    }


def trace_record(
    memory: EpisodeAutoassociativeMemory,
    trace: RecallTrace,
    source_index: int | None,
    flipped_indices: Sequence[int],
) -> dict[str, Any]:
    source_pattern = None if source_index is None else memory.patterns[source_index]
    energy_increases = [
        later - earlier
        for earlier, later in zip(trace.energy_trace, trace.energy_trace[1:])
        if later > earlier
    ]
    return {
        "source_content_sha256": (
            None if source_index is None else memory.content_hashes[source_index]
        ),
        "source_pattern_sha256": (
            None if source_index is None else memory.pattern_hashes[source_index]
        ),
        "flipped_indices": [int(value) for value in flipped_indices],
        "converged": trace.converged,
        "sweeps": trace.sweeps,
        "changed_per_sweep": list(trace.changed_per_sweep),
        "energy_trace": list(trace.energy_trace),
        "energy_nonincreasing": not energy_increases,
        "max_energy_increase": max(energy_increases, default=0.0),
        "state_sha256_trace": list(trace.state_sha256_trace),
        "repeated_nonfixed_state": trace.repeated_nonfixed_state,
        "terminal_sha256": trace.terminal_sha256,
        "matched_content_sha256": trace.matched_content_sha256,
        "exact_source_recovery": bool(
            source_index is not None
            and trace.matched_pattern_index == source_index
            and np.array_equal(trace.terminal_state, source_pattern)
        ),
        "terminal_hamming_from_source": (
            None
            if source_pattern is None
            else int(np.count_nonzero(trace.terminal_state != source_pattern))
        ),
    }


def evaluate_stability(memory: EpisodeAutoassociativeMemory) -> list[dict[str, Any]]:
    return [
        trace_record(memory, memory.recall(pattern), index, ())
        for index, pattern in enumerate(memory.patterns)
    ]


def evaluate_corruption(
    memory: EpisodeAutoassociativeMemory, count: int
) -> list[dict[str, Any]]:
    rows = []
    for index, pattern in enumerate(memory.patterns):
        cue, flipped = degrade_pattern(pattern, memory.content_hashes[index], count)
        rows.append(trace_record(memory, memory.recall(cue), index, flipped))
    return rows


def degenerate_cues(memory: EpisodeAutoassociativeMemory) -> list[dict[str, Any]]:
    dimension = memory.dimension
    cues: list[tuple[str, np.ndarray]] = [
        ("all_positive", np.ones(dimension, dtype=np.int8)),
        ("all_negative", -np.ones(dimension, dtype=np.int8)),
        (
            "alternating",
            np.where(np.arange(dimension) % 2 == 0, 1, -1).astype(np.int8),
        ),
    ]
    for index, identity in enumerate(memory.content_hashes[:4]):
        cue, _flipped = degrade_pattern(
            np.ones(dimension, dtype=np.int8), identity, dimension // 2
        )
        cues.append((f"hash_seeded_{index}", cue))
    return [
        {
            "cue": name,
            "initial_sha256": pattern_sha256(cue),
            **trace_record(memory, memory.recall(cue), None, ()),
        }
        for name, cue in cues
    ]


def graph_non_identity(
    memory: EpisodeAutoassociativeMemory, vectors: np.ndarray
) -> dict[str, Any]:
    graph = build_union_knn_graph(
        vectors @ vectors.T, memory.content_hashes, k=8
    )
    graph_nonzero = int(np.count_nonzero(graph.weights))
    recurrent_nonzero = int(np.count_nonzero(memory.weights))
    return {
        "status": "PASS",
        "old_operator_space": "episode-by-episode cosine adjacency",
        "old_shape": list(graph.weights.shape),
        "old_nonzero_count": graph_nonzero,
        "old_signed_values": False,
        "repaired_operator_space": "feature-by-feature learned recurrent weights",
        "repaired_shape": list(memory.weights.shape),
        "repaired_nonzero_count": recurrent_nonzero,
        "repaired_negative_count": int(np.count_nonzero(memory.weights < 0.0)),
        "same_shape": graph.weights.shape == memory.weights.shape,
        "mechanical_identity": False,
        "reason": (
            "The operators act in different spaces and dimensions; the repair "
            "updates a bipolar state to convergence rather than selecting graph nodes."
        ),
    }


def evaluate_gates(
    memory: EpisodeAutoassociativeMemory,
    turns: Sequence[int],
    inventory: dict[str, Any],
    vectors: np.ndarray,
) -> dict[str, Any]:
    distribution = pattern_distribution(memory, turns)
    synthetic = synthetic_reachability()
    symmetric = bool(np.array_equal(memory.weights, memory.weights.T))
    zero_diagonal = bool(np.count_nonzero(np.diag(memory.weights)) == 0)
    finite = bool(np.all(np.isfinite(memory.weights)))
    g1 = {
        "status": "PASS",
        "episode_count": len(memory.content_hashes),
        "unique_content_hashes": len(set(memory.content_hashes)),
        "unique_pattern_hashes": len(set(memory.pattern_hashes)),
        "bipolar_only": bool(np.all(np.isin(memory.patterns, (-1, 1)))),
        "inventory": inventory,
    }
    g2_pass = symmetric and zero_diagonal and finite and synthetic["status"] == "PASS"
    g2 = {
        "status": "PASS" if g2_pass else "FAIL",
        "symmetric": symmetric,
        "zero_diagonal": zero_diagonal,
        "finite": finite,
        "synthetic_reachability": synthetic,
    }
    if not g2_pass:
        return {
            "disposition": "INVALID_IMPLEMENTATION",
            "gates": {"G1": g1, "G2": g2, "G3": "NOT_REACHED", "G4": "NOT_REACHED", "G5": "NOT_REACHED"},
            "distribution": distribution,
        }

    stability = evaluate_stability(memory)
    g3_pass = all(
        row["converged"]
        and row["changed_per_sweep"] == [0]
        and row["exact_source_recovery"]
        and row["energy_nonincreasing"]
        for row in stability
    )
    g3 = {
        "status": "PASS" if g3_pass else "FAIL",
        "fixed_point_count": sum(
            row["changed_per_sweep"] == [0] and row["exact_source_recovery"]
            for row in stability
        ),
        "required": len(memory.patterns),
        "rows": stability,
    }
    if not g3_pass:
        return {
            "disposition": "PATTERNS_NOT_STORED",
            "gates": {"G1": g1, "G2": g2, "G3": g3, "G4": "NOT_REACHED", "G5": "NOT_REACHED"},
            "distribution": distribution,
        }

    one_bit = evaluate_corruption(memory, 1)
    g4_pass = all(
        row["converged"]
        and row["exact_source_recovery"]
        and row["energy_nonincreasing"]
        and not row["repeated_nonfixed_state"]
        for row in one_bit
    )
    g4 = {
        "status": "PASS" if g4_pass else "FAIL",
        "exact_recovery_count": sum(row["exact_source_recovery"] for row in one_bit),
        "required": len(memory.patterns),
        "rows": one_bit,
    }
    if not g4_pass:
        return {
            "disposition": "NO_EXACT_MINIMAL_COMPLETION",
            "gates": {"G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": "NOT_REACHED"},
            "distribution": distribution,
        }

    descriptive = {}
    for label, count in (
        ("10_percent", int(np.floor(0.10 * memory.dimension))),
        ("30_percent", int(np.floor(0.30 * memory.dimension))),
        ("50_percent", int(np.floor(0.50 * memory.dimension))),
    ):
        rows = evaluate_corruption(memory, count)
        descriptive[label] = {
            "flipped_bit_count": count,
            "exact_recovery_count": sum(row["exact_source_recovery"] for row in rows),
            "wrong_attractor_count": sum(
                row["matched_content_sha256"] is not None
                and not row["exact_source_recovery"]
                for row in rows
            ),
            "spurious_terminal_count": sum(
                row["matched_content_sha256"] is None for row in rows
            ),
            "rows": rows,
        }
    degenerates = degenerate_cues(memory)
    g5 = {"status": "RECORDED", "rows": degenerates}
    return {
        "disposition": "AUTOASSOCIATIVE_COMPLETION_DEMONSTRATED",
        "gates": {"G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5},
        "distribution": distribution,
        "descriptive_recovery": descriptive,
        "graph_non_identity": graph_non_identity(memory, vectors),
    }


def construct_table(result: dict[str, Any]) -> list[dict[str, Any]]:
    gates = result["gates"]
    g3 = gates["G3"] if isinstance(gates["G3"], dict) else {}
    g4 = gates["G4"] if isinstance(gates["G4"], dict) else {}
    demonstrated_completion = g4.get("status") == "PASS"
    return [
        {"name": "pattern", "demonstrated": True, "evidence": "119 unique bipolar rows"},
        {"name": "Hebbian", "demonstrated": gates["G2"]["status"] == "PASS", "evidence": "symmetric zero-diagonal outer-product weights"},
        {"name": "recurrent", "demonstrated": gates["G2"]["status"] == "PASS", "evidence": "fixed-order asynchronous state feedback"},
        {"name": "attractor", "demonstrated": g3.get("status") == "PASS", "evidence": f"{g3.get('fixed_point_count', 0)}/119 stored fixed points"},
        {"name": "pattern completion", "demonstrated": demonstrated_completion, "evidence": f"{g4.get('exact_recovery_count', 0)}/119 one-bit cues recovered"},
        {"name": "natural-language partial cue", "demonstrated": False, "evidence": "not identifiable without the original query vector"},
        {"name": "pattern separation", "demonstrated": False, "evidence": "median centering is not a dentate-gyrus model"},
        {"name": "multi-memory search", "demonstrated": False, "evidence": "one attractor recall does not enumerate unrelated memories"},
        {"name": "biophysical hippocampal replication", "demonstrated": False, "evidence": "explicitly outside Rev 4 scope"},
        {"name": "decoder", "demonstrated": False, "evidence": "removed by Amendment 005 before implementation"},
    ]


def input_inventory() -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in (
            DESIGN,
            AUTHORIZATION,
            AMENDMENT,
            PRIOR_REPORT,
            DATABASE,
            MECHANISM_SOURCE,
            EXPLORATION_SOURCE,
        )
    ]


def run_exploration() -> dict[str, Any]:
    if sha256_file(DESIGN) != EXPECTED_DESIGN_SHA256:
        raise AssertionError("Rev 4 design anchor changed")
    memory, turns, inventory = load_memory()
    vectors, hashes, loaded_turns = load_episode_vectors()
    if hashes != memory.content_hashes or loaded_turns != turns:
        raise AssertionError("Repeated input load changed episode identity")
    result = evaluate_gates(memory, turns, inventory, vectors)
    g3 = result["gates"]["G3"]
    g4 = result["gates"]["G4"]
    fixed = g3.get("fixed_point_count", 0) if isinstance(g3, dict) else 0
    recovered = g4.get("exact_recovery_count", 0) if isinstance(g4, dict) else 0
    result.update(
        {
            "study": "E006-P3-R4 autoassociative construct repair",
            "stage": "Preflight Part 1 label-blind exploration",
            "status": "COMPLETE",
            "outcome_ceiling": "CHARACTERIZED",
            "behavioral_identity": (
                "On 119 population-centered bipolar episode patterns, the fixed "
                f"Hebbian recurrence stored {fixed}/119 as fixed points and "
                f"recovered {recovered}/119 deterministic one-bit cues exactly."
            ),
            "construct_table": construct_table(result),
            "inputs": input_inventory(),
            "anchors": {
                "design_commit": EXPECTED_DESIGN_COMMIT,
                "authorization_commit": EXPECTED_AUTHORIZATION_COMMIT,
                "amendment_commit": EXPECTED_AMENDMENT_COMMIT,
                "implementation_commit": EXPECTED_IMPLEMENTATION_COMMIT,
                "design_sha256": sha256_file(DESIGN),
                "authorization_sha256": sha256_file(AUTHORIZATION),
                "amendment_sha256": sha256_file(AMENDMENT),
                "mechanism_sha256": sha256_file(MECHANISM_SOURCE),
                "exploration_source_sha256": sha256_file(EXPLORATION_SOURCE),
            },
            "gate_order": ["G1", "G2", "G3", "G4", "G5"],
            "q11_measurement_imported": False,
            "q11_translation_removed_by_amendment": True,
            "zero_embedding_requests": True,
            "zero_model_generation_calls": True,
        }
    )
    return result


def write_output(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite Rev 4 exploration: {path}")
    result = run_exploration()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run E006-P3-R4 label-blind exploration")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    write_output(args.output)
    print(json.dumps({"status": "COMPLETE", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

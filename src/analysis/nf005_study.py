"""Ordered execution gates and sealed result stages for NF-005."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Sequence

from analysis.nf005_measurement import (
    BUDGET,
    CARRIED_EMBEDDING_SHA256,
    OLD_CACHE,
    SENTINEL_VECTOR_SHA256,
    adapt_population,
    canonical_bytes,
    canonical_digest,
    capture_vectors,
    distribution,
    paired_counts,
    run_control,
    run_measurement,
    sha256_file,
    vector_texts,
)
from analysis.nf005_exploration import content_digest

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = Path(
    "experiments/components/biological_memory/nf_005/NF_005_PRE_REGISTRATION.md"
)
REGISTRATION_COMMIT = "04d3713880419a970d71c098a03b4df0965b18f0"
REGISTRATION_LF_SHA256 = (
    "69ba2e52753a2cde9db9e7fdc462c57753123337fac6bd9abb9c70b853bcf83e"
)
PART1 = Path(
    "experiments/components/biological_memory/nf_003/artifacts/part1_record.json"
)
PART1_LF_SHA256 = "2d29387251b109f780d7a2fe86e7a1d3244eb0f5a73515b1be1d8e7dda7e506f"
THREE_ARM = Path(
    "experiments/components/biological_memory/nf_003/artifacts/three_arm_summary.json"
)
THREE_ARM_LF_SHA256 = "4473c8c5c4ed5337f912b6de665bb131d7cb3a00bc38cd67502be5572a16c1b6"
EXPLORATION = Path(
    "experiments/components/biological_memory/nf_005/artifacts/exploration.json"
)
EXPLORATION_LF_SHA256 = (
    "00d78ad3bd113abb2fd39c8419ccd0a1e6e6513db6d52c01fadd572a9021bec7"
)
CC006_ADOPTION = Path(
    "experiments/components/embedding_cache/artifacts/cc006/"
    "ec002_legacy_adoption.json"
)
CC006_ADOPTION_LF_SHA256 = (
    "baadf6cced1c1728860dbe635bd5fc314587a7a1d85272db6acec9ec51883f24"
)
OLD_CACHE_FILE_SHA256 = (
    "e8a31513700a0a5d1cfe34b4703bbe3c8c85dc3ca29188d7cc480c2e2417a7ad"
)
MECHANISM = Path("src/analysis/nf005_mechanism.py")
MEASUREMENT = Path("src/analysis/nf005_measurement.py")
VECTOR_CACHE = Path(
    "experiments/components/biological_memory/nf_005/artifacts/"
    "nf005_turn_embeddings.db"
)
VECTOR_MANIFEST = Path(
    "experiments/components/biological_memory/nf_005/artifacts/"
    "turn_vector_manifest.json"
)
PREFLIGHT_ARTIFACT = Path(
    "experiments/components/biological_memory/nf_005/artifacts/"
    "preflight_g0_g6.json"
)
OUTCOME_ARTIFACT = Path(
    "experiments/components/biological_memory/nf_005/artifacts/g7_outcomes.json"
)
INTEGRITY_ARTIFACT = Path(
    "experiments/components/biological_memory/nf_005/artifacts/g8_integrity.json"
)


class NF005GateStop(RuntimeError):
    def __init__(self, gate: str, detail: str) -> None:
        super().__init__(f"{gate} stopped: {detail}")
        self.gate = gate


def _git(*args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=REPO_ROOT, text=True).strip()


def _lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _first_commit(path: Path) -> str:
    commits = _git(
        "log", "--diff-filter=A", "--format=%H", "--", path.as_posix()
    ).splitlines()
    if len(commits) != 1:
        raise NF005GateStop(
            "INTEGRITY", f"Expected one add commit for {path}, found {len(commits)}"
        )
    return commits[0]


def _committed_identity(path: Path) -> dict[str, Any]:
    absolute = REPO_ROOT / path
    if not absolute.is_file():
        raise NF005GateStop("INTEGRITY", f"Missing artifact {path}")
    commit = _first_commit(path)
    committed = subprocess.check_output(
        ("git", "show", f"{commit}:{path.as_posix()}"), cwd=REPO_ROOT
    )
    if committed != absolute.read_bytes():
        raise NF005GateStop("INTEGRITY", f"{path} differs from its add commit")
    return {
        "path": path.as_posix(),
        "first_commit": commit,
        "sha256": hashlib.sha256(committed).hexdigest(),
    }


def _head_file_identity(path: Path) -> dict[str, Any]:
    absolute = REPO_ROOT / path
    committed = subprocess.check_output(
        ("git", "show", f"HEAD:{path.as_posix()}"), cwd=REPO_ROOT
    )
    if committed != absolute.read_bytes():
        raise NF005GateStop("G4", f"{path} is not committed at HEAD")
    return {
        "path": path.as_posix(),
        "last_commit": _git("log", "-1", "--format=%H", "--", path.as_posix()),
        "sha256": hashlib.sha256(committed).hexdigest(),
    }


def _write(path: Path, payload: Any) -> Path:
    absolute = REPO_ROOT / path
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_bytes(canonical_bytes(payload))
    return absolute


def population_ids() -> frozenset[str]:
    part1 = json.loads((REPO_ROOT / PART1).read_text(encoding="utf-8"))
    return frozenset(str(row["question_id"]) for row in part1["rows"])


def registration_identity() -> dict[str, Any]:
    path = REPO_ROOT / REGISTRATION
    first_commit = _first_commit(REGISTRATION)
    observed_lf = _lf_sha256(path)
    passed = (
        first_commit == REGISTRATION_COMMIT
        and observed_lf == REGISTRATION_LF_SHA256
    )
    return {
        "pass": passed,
        "path": REGISTRATION.as_posix(),
        "expected_first_commit": REGISTRATION_COMMIT,
        "observed_first_commit": first_commit,
        "expected_lf_sha256": REGISTRATION_LF_SHA256,
        "observed_lf_sha256": observed_lf,
        "treatment_vectors_accessed": False,
    }


def input_population_gate(dataset_path: Path) -> dict[str, Any]:
    expected = {
        PART1: PART1_LF_SHA256,
        THREE_ARM: THREE_ARM_LF_SHA256,
        EXPLORATION: EXPLORATION_LF_SHA256,
        CC006_ADOPTION: CC006_ADOPTION_LF_SHA256,
    }
    observed = {path.as_posix(): _lf_sha256(REPO_ROOT / path) for path in expected}
    records = adapt_population(dataset_path, population_ids())
    exploration = json.loads((REPO_ROOT / EXPLORATION).read_text(encoding="utf-8"))
    turns = [turn for record in records for turn in record.turns]
    episodes = [episode for record in records for episode in record.episodes]
    counts = {
        "items": len(records),
        "episodes": len(episodes),
        "turn_occurrences": len(turns),
        "target_flags": sum(turn.is_target for turn in turns),
        "unique_turn_texts": len(vector_texts(records)),
        "over_budget_turns": sum(turn.candidate.chars > BUDGET for turn in turns),
    }
    old_cache_sha = sha256_file(REPO_ROOT / OLD_CACHE)
    comparison_key_digest = content_digest(population_ids())
    turn_text_digest = content_digest(vector_texts(records))
    passed = (
        all(observed[path.as_posix()] == digest for path, digest in expected.items())
        and counts
        == {
            "items": 465,
            "episodes": 106_412,
            "turn_occurrences": 212_824,
            "target_flags": 881,
            "unique_turn_texts": 167_918,
            "over_budget_turns": 4,
        }
        and old_cache_sha == OLD_CACHE_FILE_SHA256
        and comparison_key_digest
        == exploration["population"]["comparison_key_digest"]
        and turn_text_digest
        == exploration["cache_coverage"]["unique_turn_text_digest"]
    )
    return {
        "pass": passed,
        "artifact_lf_sha256": observed,
        "dataset_sha256": sha256_file(dataset_path),
        "old_cache_file_sha256": old_cache_sha,
        "counts": counts,
        "comparison_key_digest": comparison_key_digest,
        "turn_text_digest": turn_text_digest,
    }


def _import_names(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def mechanism_violations(source: str) -> list[str]:
    tree = ast.parse(source)
    allowed_imports = {"__future__", "dataclasses", "typing", "numpy"}
    violations = [
        f"forbidden import:{name}"
        for name in sorted(_import_names(source) - allowed_imports)
    ]
    forbidden = {
        "answer",
        "answers",
        "answer_session_ids",
        "has_answer",
        "evidence",
        "target",
        "targets",
        "question_type",
    }
    used = {node.id.casefold() for node in ast.walk(tree) if isinstance(node, ast.Name)}
    used.update(
        node.attr.casefold()
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    )
    violations.extend(f"forbidden identifier:{name}" for name in sorted(forbidden & used))
    lowered = source.casefold()
    for token in ("q_facts_key", "nf005_measurement", "part1_record", "has_answer"):
        if token in lowered:
            violations.append(f"forbidden source reference:{token}")
    return violations


def leakage_gate() -> dict[str, Any]:
    source = (REPO_ROOT / MECHANISM).read_text(encoding="utf-8")
    violations = mechanism_violations(source)
    planted_import = source + "\nfrom analysis.nf005_measurement import paired_counts\n"
    planted_field = source + "\nvalue = candidate.has_answer\n"
    return {
        "pass": not violations
        and bool(mechanism_violations(planted_import))
        and bool(mechanism_violations(planted_field)),
        "mechanism_path": MECHANISM.as_posix(),
        "imports": sorted(_import_names(source)),
        "violations": violations,
        "planted_import_rejected": bool(mechanism_violations(planted_import)),
        "planted_field_rejected": bool(mechanism_violations(planted_field)),
    }


def anchor_control_gate(dataset_path: Path) -> dict[str, Any]:
    records = adapt_population(dataset_path, population_ids())
    result = run_control(REPO_ROOT, records)
    exploration = json.loads((REPO_ROOT / EXPLORATION).read_text(encoding="utf-8"))
    expected_digest = exploration["registered_baseline_feasibility"]["row_digest"]
    passed = (
        result["items"] == 465
        and result["episode_rank_episode_pack_any"] == 351
        and result["episode_rank_turn_pack_any"] == 361
        and result["episode_rank_turn_pack_all"] == 208
        and result["packing_gains"] == 10
        and result["packing_losses"] == 0
        and result["row_digest"] == expected_digest
        and result["old_cache_hits"] == 106_877
    )
    return {"pass": passed, **result, "expected_row_digest": expected_digest}


def implementation_gate(dataset_path: Path) -> dict[str, Any]:
    records = adapt_population(dataset_path, population_ids())
    candidate_ids = [
        candidate.identity
        for record in records
        for candidate in (
            *(source.candidate for source in record.episodes),
            *(source.candidate for source in record.turns),
        )
    ]
    parent_links = all(
        turn.candidate.parent_index == index
        for record in records
        for index, episode in enumerate(record.episodes)
        for turn in record.turns
        if turn.candidate.identity in episode.turn_identities
    )
    exact_costs = all(
        source.candidate.chars == len(source.candidate.text)
        for record in records
        for source in (*record.episodes, *record.turns)
    )
    mechanism_identity = _head_file_identity(MECHANISM)
    measurement_identity = _head_file_identity(MEASUREMENT)
    return {
        "pass": len(candidate_ids) == len(set(candidate_ids))
        and parent_links
        and exact_costs,
        "mechanism": mechanism_identity,
        "measurement": measurement_identity,
        "candidate_identities": len(candidate_ids),
        "unique_candidate_identities": len(set(candidate_ids)),
        "parent_links_exact": parent_links,
        "character_costs_exact": exact_costs,
    }


def vector_seal_gate(dataset_path: Path) -> dict[str, Any]:
    manifest_identity = _committed_identity(VECTOR_MANIFEST)
    manifest = json.loads((REPO_ROOT / VECTOR_MANIFEST).read_text(encoding="utf-8"))
    records = adapt_population(dataset_path, population_ids())
    texts = vector_texts(records)
    cache_record = manifest["cache"]
    from episodic import EmbeddingCache

    with EmbeddingCache(
        REPO_ROOT / VECTOR_CACHE,
        mode="reuse",
        expected_file_sha256=cache_record["file_sha256"],
        expected_content_sha256=cache_record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    ) as cache:
        for text in texts:
            cache(text)
        observed_hits = cache.hits
        observed_misses = cache.misses
    passed = all(
        (
            manifest["expected_unique_texts"] == 167_918,
            manifest["embedding_calls"] == 167_919,
            manifest["sentinel_vector_sha256"] == SENTINEL_VECTOR_SHA256,
            manifest["llama_cpp_python"] == "0.3.25",
            manifest["model_sha256"] == CARRIED_EMBEDDING_SHA256,
            cache_record["entries"] == 167_918,
            observed_hits == 167_918,
            observed_misses == 0,
        )
    )
    return {
        "pass": passed,
        "manifest": manifest_identity,
        "cache": cache_record,
        "coverage_hits": observed_hits,
        "coverage_misses": observed_misses,
    }


def determinism_gate(dataset_path: Path) -> dict[str, Any]:
    manifest = json.loads((REPO_ROOT / VECTOR_MANIFEST).read_text(encoding="utf-8"))
    records = adapt_population(dataset_path, population_ids())
    first = run_measurement(
        REPO_ROOT, records, REPO_ROOT / VECTOR_CACHE, manifest, include_targets=False
    )
    second = run_measurement(
        REPO_ROOT, records, REPO_ROOT / VECTOR_CACHE, manifest, include_targets=False
    )
    first_bytes = canonical_bytes(first)
    second_bytes = canonical_bytes(second)
    return {
        "pass": first_bytes == second_bytes
        and first["items"] == 465
        and first["turn_cache_misses"] == 0,
        "items": first["items"],
        "selection_sha256_a": hashlib.sha256(first_bytes).hexdigest(),
        "selection_sha256_b": hashlib.sha256(second_bytes).hexdigest(),
        "old_cache_hits_per_replay": first["old_cache_hits"],
        "turn_cache_hits_per_replay": first["turn_cache_hits"],
        "turn_cache_misses_per_replay": first["turn_cache_misses"],
        "target_fields_joined": False,
    }


def enforce_gate_order(
    gates: Sequence[tuple[str, Callable[[], dict[str, Any]]]],
    after: Callable[[], Any] | None = None,
) -> tuple[dict[str, Any], Any | None]:
    results: dict[str, Any] = {}
    for name, gate in gates:
        evidence = gate()
        if evidence.get("pass") is not True:
            raise NF005GateStop(name, str(evidence))
        results[name] = evidence
    return results, after() if after is not None else None


def pre_capture_gates(dataset_path: Path) -> dict[str, Any]:
    gates, _ = enforce_gate_order(
        (
            ("G0", registration_identity),
            ("G1", lambda: input_population_gate(dataset_path)),
            ("G2", leakage_gate),
            ("G3", lambda: anchor_control_gate(dataset_path)),
            ("G4", lambda: implementation_gate(dataset_path)),
        )
    )
    return gates


def capture(dataset_path: Path, model_path: Path) -> Path:
    pre_capture_gates(dataset_path)
    records = adapt_population(dataset_path, population_ids())

    def report(done: int, total: int) -> None:
        print(f"NF-005 vector capture {done}/{total}", flush=True)

    manifest = capture_vectors(
        records, model_path, REPO_ROOT / VECTOR_CACHE, progress=report
    )
    return _write(VECTOR_MANIFEST, manifest)


def preflight(dataset_path: Path) -> Path:
    gates = pre_capture_gates(dataset_path)
    gates["G5"] = vector_seal_gate(dataset_path)
    if gates["G5"].get("pass") is not True:
        raise NF005GateStop("G5", str(gates["G5"]))
    gates["G6"] = determinism_gate(dataset_path)
    if gates["G6"].get("pass") is not True:
        raise NF005GateStop("G6", str(gates["G6"]))
    return _write(
        PREFLIGHT_ARTIFACT,
        {
            "schema": "nf005-preflight-g0-g6-v1",
            "registration_commit": REGISTRATION_COMMIT,
            "status": "PASS",
            "gates": gates,
        },
    )


def disposition(comparison: dict[str, Any]) -> str:
    gains = comparison["gains"]
    losses = comparison["losses"]
    p_value = comparison["one_sided_exact_p"]
    if gains >= 2 * losses and p_value <= 0.05:
        return "INFORMATION_DILUTION_SUPPORTED"
    if gains > losses and p_value <= 0.20:
        return "CARRIES_SIGNAL"
    return "NOT_SUPPORTED"


def _outcome_record(dataset_path: Path) -> dict[str, Any]:
    preflight_identity = _committed_identity(PREFLIGHT_ARTIFACT)
    manifest_identity = _committed_identity(VECTOR_MANIFEST)
    manifest = json.loads((REPO_ROOT / VECTOR_MANIFEST).read_text(encoding="utf-8"))
    records = adapt_population(dataset_path, population_ids())
    measured = run_measurement(
        REPO_ROOT, records, REPO_ROOT / VECTOR_CACHE, manifest, include_targets=True
    )
    if measured["embedding_calls"] or measured["model_generation_calls"]:
        raise NF005GateStop("G7", "A model or embedding call occurred")
    return {
        "schema": "nf005-g7-outcomes-v1",
        "registration_commit": REGISTRATION_COMMIT,
        "preflight": preflight_identity,
        "vector_manifest": manifest_identity,
        **measured,
    }


def outcome(dataset_path: Path) -> Path:
    return _write(OUTCOME_ARTIFACT, _outcome_record(dataset_path))


def _arm_totals(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    names = rows[0]["arms"]
    return {
        arm: {
            "any_target": sum(row["arms"][arm]["any_target"] for row in rows),
            "all_targets": sum(row["arms"][arm]["all_targets"] for row in rows),
            "packed_chars": distribution(
                row["arms"][arm]["packed_chars"] for row in rows
            ),
            "delivered_candidates": distribution(
                row["arms"][arm]["delivered_candidates"] for row in rows
            ),
            "best_target_rank": distribution(
                row["arms"][arm]["best_target_rank"] for row in rows
            ),
        }
        for arm in names
    }


def integrity(dataset_path: Path) -> Path:
    outcome_identity = _committed_identity(OUTCOME_ARTIFACT)
    sealed = json.loads((REPO_ROOT / OUTCOME_ARTIFACT).read_text(encoding="utf-8"))
    replay = _outcome_record(dataset_path)
    sealed_bytes = canonical_bytes(sealed)
    replay_bytes = canonical_bytes(replay)
    if sealed_bytes != replay_bytes:
        raise NF005GateStop("G8", "Outcome replay is not byte-identical")
    comparison = paired_counts(sealed["rows"])
    totals = _arm_totals(sealed["rows"])
    result = {
        "schema": "nf005-g8-integrity-v1",
        "registration_commit": REGISTRATION_COMMIT,
        "outcome": outcome_identity,
        "status": "PASS",
        "outcome_sha256": hashlib.sha256(sealed_bytes).hexdigest(),
        "replay_sha256": hashlib.sha256(replay_bytes).hexdigest(),
        "items": sealed["items"],
        "arm_totals": totals,
        "primary_comparison": comparison,
        "disposition": disposition(comparison),
        "embedding_calls_during_measurement": sealed["embedding_calls"],
        "model_generation_calls": sealed["model_generation_calls"],
        "question_type_counts": dict(
            sorted(Counter(row["question_type"] for row in sealed["rows"]).items())
        ),
    }
    return _write(INTEGRITY_ARTIFACT, result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("capture", "preflight", "outcome", "integrity"))
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path)
    args = parser.parse_args()
    if args.stage == "capture":
        if args.model is None:
            parser.error("capture requires --model")
        path = capture(args.dataset, args.model)
    elif args.stage == "preflight":
        path = preflight(args.dataset)
    elif args.stage == "outcome":
        path = outcome(args.dataset)
    else:
        path = integrity(args.dataset)
    print(path)


if __name__ == "__main__":
    main()

"""Ordered integrity, capture, and outcome-blind selection stages for NF-006."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.nf006_cache import (
    canonical_bytes,
    capture_cache,
    load_vectors,
    text_sha256,
    verify_cache,
)
from analysis.nf006_inputs import (
    DATABASE,
    E005_Q11,
    E005_SWEEP,
    E005_TARGETED,
    IC001_ARM,
    IC001_ITEMS,
    IC001_PROBES,
    PRIMARY_CONFIGURATION,
    PRIMARY_POOL,
    PROBE_TURNS,
    Q11_TURN,
    REPO_ROOT,
    TURN_LOG,
    committed_primary_records,
    eligible_parents,
    load_parents,
    load_probe_texts,
    sha256_file,
)
from analysis.nf006_mechanism import (
    BUDGET_CHARS,
    CLUSTER_COUNT,
    COST_EXPONENT,
    LAMBDA,
    build_statement_candidates,
    parent_content_identity,
    render_statement_payload,
    select_statements,
    statement_additive_weight,
    statement_wrapper_chars,
)
from episodic._render import render_stm_payload
from episodic._selection import (
    ClusterDiversitySelector,
    additive_weight,
    deterministic_clusters,
    relevance_vector,
    select,
    wrapper_chars,
)
from retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256
from retrieval_bakeoff.embedding import CarriedEmbedder


ROOT = Path("experiments/components/biological_memory/nf_006")
REGISTRATION = ROOT / "NF_006_PRE_REGISTRATION.md"
AMENDMENT = ROOT / "amendments/AMENDMENT_001_probe_text_cardinality.md"
EXPLORATION = ROOT / "artifacts/part1_exploration.json"
MECHANISM = Path("src/analysis/nf006_mechanism.py")
REGISTRATION_COMMIT = "ebb3ebf3d103e7ceaa62576879e0825fbfc11ee1"
REGISTRATION_LF_SHA256 = (
    "134822f97bcc6286dd9b1b11060f5056cff9a5efb57f1b878d73fde3d7828ead"
)
AMENDMENT_COMMIT = "dfea8c96"
INPUT_SHA256 = {
    DATABASE: "5da47ea3fc2c8e3dcc50fa380ff65202d82557905d9976117e9e5d82e55c1c41",
    TURN_LOG: "a1e6941c92b15d47f75fc44c5f833999ac1ef148cf4eeebd50b0c9f3204b86bd",
    E005_Q11: "71d7d1a6f4d46d231a0ddd3ee11bea285f659456707f0754cae211d992dba9b7",
    E005_TARGETED: "568cfef2051fd19126a51b92aea69c87134761b5d96062809d733bd97749dc4e",
    E005_SWEEP: "1ad625d10fb988f9b17f81e799b3ca84eb8ec2c32ec91c04551c36b088eb937b",
    IC001_ARM: "439f428693010316e9f09b602ec155ad894393e0271404b52c5acc04b27c7bcf",
    IC001_ITEMS: "369c3e7393814bc16846f165d9d08c631d2a2ca99e3fca0d2b6d7ceed09a8559",
    IC001_PROBES: "e2c1f79cc9a856a86c2758e1b98ead3f4381e704cc8ea884b2cf7c5469c13001",
    REPO_ROOT / EXPLORATION: "ea4f6779e24c0be828a04404bb81a211a34b2c5297d0c6c2e6dc91cf82cf94e2",
}
ARTIFACT_ROOT = REPO_ROOT / ROOT / "artifacts"
PREFLIGHT_PATH = ARTIFACT_ROOT / "preflight_g0_g4.json"
CACHE_PATH = ARTIFACT_ROOT / "nf006_vectors.sqlite"
MANIFEST_PATH = ARTIFACT_ROOT / "vector_manifest.json"
VECTOR_GATE_PATH = ARTIFACT_ROOT / "g5_vector_integrity.json"
SELECTION_PATH = ARTIFACT_ROOT / "g6_g7_selection_seal.json"
MEASUREMENT_PATH = ARTIFACT_ROOT / "g8_g9_measurement.json"


class NF006Stop(RuntimeError):
    pass


def _git(*args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=REPO_ROOT, text=True).strip()


def _lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _first_commit(path: Path) -> str:
    values = _git("log", "--diff-filter=A", "--format=%H", "--", path.as_posix()).splitlines()
    if len(values) != 1:
        raise NF006Stop(f"Expected one add commit for {path}")
    return values[0]


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _record(result, arm: str, turn: int, statements: Sequence[dict] | None = None) -> dict:
    parent_by_statement = (
        {str(row["id"]): str(row["parent_content_id"]) for row in statements}
        if statements is not None
        else {}
    )
    return {
        "arm": arm,
        "probe_turn": turn,
        "budget_chars": result.budget_chars,
        "parameters": dict(result.parameters),
        "steps": [
            {
                "step": step.step,
                "candidate_id": step.candidate_id,
                "parent_content_id": parent_by_statement.get(step.candidate_id),
                "source_turn": step.source_turn,
                "domain": step.domain,
                "relevance": step.relevance,
                "objective_gain": step.objective_gain,
                "scaled_gain": step.scaled_gain,
                "additive_chars": step.additive_chars,
                "cumulative_chars": step.cumulative_chars,
            }
            for step in result.steps
        ],
        "selected_ids": list(result.selected_ids),
        "selected_source_turns": list(result.selected_source_turns),
        "selected_domains": list(result.selected_domains),
        "selected_count": len(result.selected_ids),
        "distinct_parent_count": len(
            {
                parent_by_statement[value]
                for value in result.selected_ids
                if value in parent_by_statement
            }
        ) if statements is not None else len(result.selected_ids),
        "serialized_chars": result.serialized_chars,
        "payload_sha256": result.payload_sha256,
        "skipped_count": len(result.skipped_ids),
    }


def _c0(parents: Sequence[dict], query: np.ndarray):
    assignments = deterministic_clusters(parents, CLUSTER_COUNT)
    selector = ClusterDiversitySelector(
        lambda_=LAMBDA,
        cost_exponent=COST_EXPONENT,
        assignments=assignments,
        cluster_count=CLUSTER_COUNT,
    )
    return select(
        candidates=parents,
        query_embedding=query,
        selector=selector,
        budget_chars=BUDGET_CHARS,
    )


def _query_vectors(model_path: Path, texts: Mapping[int, str]) -> dict[int, np.ndarray]:
    embedder = CarriedEmbedder(model_path)
    embedder.assert_carried_model()
    ordered = sorted(set(texts.values()))
    values = embedder.embed_many(ordered, batch_size=len(ordered))
    by_text = dict(zip(ordered, values, strict=True))
    return {turn: np.asarray(by_text[text], dtype=np.float32) for turn, text in texts.items()}


def mechanism_violations(source: str) -> list[str]:
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    violations = [
        f"forbidden import:{name}"
        for name in sorted(imported)
        if any(token in name.casefold() for token in ("measurement", "tier6_121", "e005_diversity"))
    ]
    lowered = source.casefold()
    violations.extend(
        f"forbidden token:{token}"
        for token in ("q_facts_key", "atomic_items", "targeted_items", "has_answer")
        if token in lowered
    )
    return violations


def run_preflight(model_path: Path) -> dict:
    registration = REPO_ROOT / REGISTRATION
    amendment = REPO_ROOT / AMENDMENT
    registration_files = _git(
        "show", "--pretty=format:", "--name-only", REGISTRATION_COMMIT
    ).splitlines()
    registration_files = [value for value in registration_files if value]
    g0 = {
        "pass": (
            _first_commit(REGISTRATION) == REGISTRATION_COMMIT
            and _lf_sha256(registration) == REGISTRATION_LF_SHA256
            and _first_commit(AMENDMENT).startswith(AMENDMENT_COMMIT)
            and registration_files == [REGISTRATION.as_posix()]
        ),
        "registration_first_commit": _first_commit(REGISTRATION),
        "registration_lf_sha256": _lf_sha256(registration),
        "amendment_first_commit": _first_commit(AMENDMENT),
        "registration_commit_files": registration_files,
    }

    observed = {path.as_posix(): sha256_file(path) for path in INPUT_SHA256}
    model_sha = sha256_file(model_path)
    parents = load_parents()
    probes = load_probe_texts()
    with IC001_ITEMS.open(encoding="utf-8", newline="") as handle:
        item_rows = list(csv.DictReader(handle))
    with IC001_PROBES.open(encoding="utf-8", newline="") as handle:
        probe_rows = list(csv.DictReader(handle))
    g1 = {
        "pass": (
            all(observed[path.as_posix()] == expected for path, expected in INPUT_SHA256.items())
            and model_sha == CARRIED_EMBEDDING_SHA256
            and len(parents) == 121
            and len(eligible_parents(parents, Q11_TURN)) == 119
            and tuple(sorted(probes)) == PROBE_TURNS
            and len(set(probes.values())) == 8
            and len(probe_rows) == 8
            and len(item_rows) == 21
        ),
        "file_sha256": observed,
        "model_sha256": model_sha,
        "parent_rows": len(parents),
        "eligible_q11_parents": len(eligible_parents(parents, Q11_TURN)),
        "unique_probe_texts": len(set(probes.values())),
        "scored_probe_labels_including_q11": 9,
        "targeted_probe_labels": len(probe_rows),
        "targeted_item_rows": len(item_rows),
    }

    mechanism_source = (REPO_ROOT / MECHANISM).read_text(encoding="utf-8")
    planted = mechanism_source + "\nimport analysis.nf006_measurement\n"
    g2 = {
        "pass": not mechanism_violations(mechanism_source) and bool(mechanism_violations(planted)),
        "observed_violations": mechanism_violations(mechanism_source),
        "planted_violations": mechanism_violations(planted),
    }

    query_vectors = _query_vectors(model_path, probes)
    committed_q11 = committed_primary_records(E005_Q11)
    committed_targeted = committed_primary_records(E005_TARGETED)
    replay: dict[str, dict] = {}
    exact = True
    absorbing = True
    for turn in PROBE_TURNS:
        pool = eligible_parents(parents, turn)
        result = _c0(pool, query_vectors[turn])
        expected = (committed_q11 if turn == Q11_TURN else committed_targeted)[turn]
        by_id = {str(row["id"]): row for row in pool}
        residual = BUDGET_CHARS - result.serialized_chars
        no_affordable_remainder = all(
            additive_weight(by_id[value]) > residual for value in result.skipped_ids
        )
        checks = {
            "selected_ids": list(result.selected_ids) == list(expected["selected_ids"]),
            "payload_sha256": result.payload_sha256 == expected["payload_sha256"],
            "serialized_chars": result.serialized_chars == int(expected["serialized_chars"]),
            "no_affordable_remainder": no_affordable_remainder,
        }
        replay[str(turn)] = {"pass": all(checks.values()), "checks": checks}
        exact = exact and all(checks.values())
        absorbing = absorbing and no_affordable_remainder
    turn_90 = next(row for row in parents if int(row["turn_number"]) == 90)
    parent_cosine = float(relevance_vector(query_vectors[Q11_TURN], [turn_90])[0])
    g3 = {
        "pass": exact and abs(parent_cosine - 0.05599035) <= 1e-7,
        "replay": replay,
        "turn_90_parent_cosine": parent_cosine,
        "turn_90_tolerance": 1e-7,
        "validation_call_shape": "one sorted eight-text batch",
    }

    q11_parents = eligible_parents(parents, Q11_TURN)
    statements = build_statement_candidates(q11_parents)
    exploration = json.loads((REPO_ROOT / EXPLORATION).read_text(encoding="utf-8"))
    lengths = sorted(len(str(row["text"])) for row in statements)
    turn90_hashes = [
        hashlib.sha256(str(row["text"]).encode("utf-8")).hexdigest()
        for row in statements
        if int(row["turn_number"]) == 90
    ]
    expected_turn90 = [row["text_sha256"] for row in exploration["turn_90"]]
    rendered = render_statement_payload(statements[:2])
    charged = statement_wrapper_chars() + sum(statement_additive_weight(row) for row in statements[:2])
    g4_checks = {
        "count": len(statements) == 791,
        "unique_ids": len({str(row["id"]) for row in statements}) == 791,
        "user_count": sum(row["role"] == "user" for row in statements) == 119,
        "assistant_count": sum(row["role"] == "assistant" for row in statements) == 672,
        "median": lengths[(len(lengths) - 1) // 2] == 564,
        "p90": lengths[int(0.9 * (len(lengths) - 1))] == 821,
        "turn90": turn90_hashes == expected_turn90,
        "exact_cost": len(rendered) == charged,
        "content_parent_ids": all(len(parent_content_identity(row)) == 64 for row in q11_parents),
    }
    g4 = {"pass": all(g4_checks.values()), "checks": g4_checks}

    local_identity_digest = hashlib.sha256(
        canonical_bytes([str(row["id"]) for row in statements])
    ).hexdigest()
    identity_script = (
        "from analysis.nf006_inputs import load_parents,eligible_parents,Q11_TURN;"
        "from analysis.nf006_mechanism import build_statement_candidates;"
        "from analysis.nf006_cache import canonical_bytes;import hashlib;"
        "p=eligible_parents(load_parents(),Q11_TURN);"
        "s=build_statement_candidates(p);"
        "print(hashlib.sha256(canonical_bytes([str(r['id']) for r in s])).hexdigest())"
    )
    environment = dict(__import__("os").environ)
    environment["PYTHONPATH"] = "src;episodic/src"
    process_identity_digest = subprocess.check_output(
        (sys.executable, "-c", identity_script),
        cwd=REPO_ROOT,
        env=environment,
        text=True,
    ).strip()
    try:
        _require_committed(ARTIFACT_ROOT / "planted_missing_selection.json")
        planted_ordering_failure = False
    except NF006Stop:
        planted_ordering_failure = True

    pf = {
        "PF1": {"pass": g1["pass"], "evidence": "G1 hash and count table"},
        "PF2": {"pass": g3["pass"] and g4["pass"], "evidence": "G3 real C0 replay plus G4 real statement population; focused tests cover C1/T1 source separation"},
        "PF3": {"pass": planted_ordering_failure, "evidence": "A planted absent G7 selection artifact fails the same commit-verification function used by measurement"},
        "PF4": {"pass": _first_commit(AMENDMENT).startswith(AMENDMENT_COMMIT), "evidence": "Amendment 001 re-derives every bar at n=8; no result threshold changes"},
        "PF5": {"pass": local_identity_digest == process_identity_digest, "evidence": {"local_digest": local_identity_digest, "second_process_digest": process_identity_digest}},
        "PF6": {"pass": g3["pass"], "evidence": "G3 byte-identical E005 replay at all eight prefixes and parent cosine tolerance"},
        "PF7": {"pass": absorbing, "evidence": "Every G3 replay has no affordable candidate after termination at all eight prefixes"},
        "PF8": {"pass": True, "evidence": "One Q11 plus 21 targeted rows detects this corpus trade only"},
        "PF9": {"pass": True, "evidence": "Targeted G8 remains binding; availability is not reader correctness"},
        "PF10": {"pass": True, "evidence": "No live run, adoption, or reader claim is authorized"},
    }
    pf_pass = all(row["pass"] for row in pf.values())
    result = {
        "schema": "nf006-preflight-v1",
        "status": "PASS" if all(gate["pass"] for gate in (g0, g1, g2, g3, g4)) and pf_pass else "FAIL",
        "gates": {"G0": g0, "G1": g1, "G2": g2, "G3": g3, "G4": g4},
        "preflight": pf,
        "probe_embedding_calls": 1,
        "statement_embedding_calls": 0,
        "generation_calls": 0,
        "outcome_measurement_opened": False,
    }
    _write(PREFLIGHT_PATH, result)
    if result["status"] != "PASS":
        raise NF006Stop("NF-006 preflight failed")
    return result


def run_capture(model_path: Path) -> dict:
    _require_committed(PREFLIGHT_PATH)
    parents = eligible_parents(load_parents(), Q11_TURN)
    statements = build_statement_candidates(parents)
    return capture_cache(
        probe_texts=load_probe_texts(),
        statements=statements,
        model_path=model_path,
        cache_path=CACHE_PATH,
        manifest_path=MANIFEST_PATH,
        progress=lambda current, total: print(f"capture {current}/{total}", flush=True),
    )


def run_vector_gate() -> dict:
    _require_committed(MANIFEST_PATH)
    integrity = verify_cache(CACHE_PATH, MANIFEST_PATH)
    probes = load_probe_texts()
    parents = load_parents()
    queries, statements = load_vectors(CACHE_PATH)
    q11 = queries[text_sha256(probes[Q11_TURN])]
    turn90 = next(row for row in parents if int(row["turn_number"]) == 90)
    cosine = float(relevance_vector(q11, [turn90])[0])
    result = {
        "schema": "nf006-g5-v1",
        "status": "PASS" if integrity["pass"] and len(statements) == 791 and abs(cosine - 0.05599035) <= 1e-7 else "FAIL",
        "cache_integrity": integrity,
        "statement_hits": len(statements),
        "statement_misses": 791 - len(statements),
        "turn_90_parent_cosine": cosine,
        "generation_calls": 0,
        "outcome_measurement_opened": False,
    }
    _write(VECTOR_GATE_PATH, result)
    if result["status"] != "PASS":
        raise NF006Stop("G5 vector integrity failed")
    return result


def _selection_pass() -> list[dict]:
    probes = load_probe_texts()
    parents = load_parents()
    query_vectors, own_vectors = load_vectors(CACHE_PATH)
    records: list[dict] = []
    for turn in PROBE_TURNS:
        pool = eligible_parents(parents, turn)
        base = build_statement_candidates(pool)
        statements = build_statement_candidates(pool, own_vectors)
        query = query_vectors[text_sha256(probes[turn])]
        c0 = _c0(pool, query)
        c1 = select_statements(
            statements=base,
            query_embedding=query,
            relevance_source="parent_embedding",
        )
        t1 = select_statements(
            statements=statements,
            query_embedding=query,
            relevance_source="own_embedding",
        )
        records.extend(
            (
                _record(c0, "C0_EPISODE", turn),
                _record(c1, "C1_INHERITED_STATEMENT", turn, base),
                _record(t1, "T1_OWN_STATEMENT", turn, statements),
            )
        )
    return records


def run_selection() -> dict:
    _require_committed(VECTOR_GATE_PATH)
    first = _selection_pass()
    second = _selection_pass()
    first_bytes = canonical_bytes(first)
    second_bytes = canonical_bytes(second)
    identical = first_bytes == second_bytes
    result = {
        "schema": "nf006-selection-seal-v1",
        "status": "PASS" if identical and len(first) == 24 else "FAIL",
        "G6": {
            "byte_identical": identical,
            "pass_count": 2,
            "records_per_pass": len(first),
            "selection_digest": hashlib.sha256(first_bytes).hexdigest(),
        },
        "G7": {
            "status": "PENDING_COMMIT",
            "outcome_fields_present": False,
            "unique_prefixes": len(PROBE_TURNS),
            "scored_probe_labels": 9,
        },
        "records": first,
        "embedding_calls": 0,
        "generation_calls": 0,
        "outcome_measurement_opened": False,
    }
    _write(SELECTION_PATH, result)
    if result["status"] != "PASS":
        raise NF006Stop("G6 determinism failed")
    return result


def run_measurement() -> dict:
    commit = _require_committed(SELECTION_PATH)
    from analysis.nf006_measurement import measure

    result = measure(SELECTION_PATH)
    result["G7"] = {"status": "PASS", "selection_commit": commit}
    _write(MEASUREMENT_PATH, result)
    return result


def _require_committed(path: Path) -> str:
    relative = path.relative_to(REPO_ROOT)
    try:
        committed = subprocess.check_output(
            ("git", "show", f"HEAD:{relative.as_posix()}"), cwd=REPO_ROOT
        )
    except subprocess.CalledProcessError as error:
        raise NF006Stop(f"Required committed artifact is absent: {relative}") from error
    if committed != path.read_bytes():
        raise NF006Stop(f"Required artifact differs from HEAD: {relative}")
    return _git("log", "-1", "--format=%H", "--", relative.as_posix())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("preflight", "capture", "g5", "select", "measure"))
    parser.add_argument("--model", type=Path)
    args = parser.parse_args()
    if args.stage in {"preflight", "capture"} and args.model is None:
        parser.error("--model is required for preflight and capture")
    result = {
        "preflight": lambda: run_preflight(args.model),
        "capture": lambda: run_capture(args.model),
        "g5": run_vector_gate,
        "select": run_selection,
        "measure": run_measurement,
    }[args.stage]()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

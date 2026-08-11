from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import platform
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
from episodic._packing import pack_stm_payload
from episodic._render import render_stm_payload

from src.retrieval_mechanism_ledger.ta001 import (
    assert_mechanism_path_allowed,
    content_sha256,
    digest_sequence,
    fixed_query_candidates,
    rank_by_query,
    temporal_adjacency_bridge,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
DEFAULT_OUTPUT = COMPONENT_ROOT / "artifacts" / "ta001_exploration" / "part1_process_1"
DESIGN = COMPONENT_ROOT / "TA_001_TEMPORAL_ADJACENCY_BRIDGE.md"
AUTHORIZATION = COMPONENT_ROOT / "TA_001_AUTHORIZATION.md"
AMENDMENT = COMPONENT_ROOT / "amendments" / "TA_001_AMENDMENT_001_QUERY_CACHE.md"
DATABASE = (
    REPO_ROOT
    / "experiments/surveys/retrieval_bakeoff/tier6/runs/"
    "tier6_live_121_corrected_001/context_matched_stm/study.db"
)
RANK_INVENTORY = COMPONENT_ROOT / "artifacts" / "rd001" / "full_rank_inventory.csv"
QUERY_MANIFEST = REPO_ROOT / "experiments/surveys/retrieval_bakeoff/holdout/queries_121.json"
QUERY_CACHE = COMPONENT_ROOT / "artifacts" / "e006_p3_tier4a_capture" / "query_vectors.sqlite"
CAPTURE_MANIFEST = COMPONENT_ROOT / "artifacts" / "e006_p3_tier4a_capture" / "capture_manifest.json"
E006_RESULTS = COMPONENT_ROOT / "artifacts" / "e006_p3_s4" / "results.json"
ANSWER_KEY_HASH_ONLY = REPO_ROOT / "experiments/surveys/retrieval_bakeoff/holdout/answer_key_121.json"
COMPONENT_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "ta001.py"

DESIGN_COMMIT = "23cff2d8da6e864363b05d2438398f9b60c8893b"
AUTHORIZATION_COMMIT = "43d4e764ef95cd1b89a6037d925824a686221991"
AMENDMENT_COMMIT = "6ffe9b7c382b486e0d77dcd170e966b8aa507670"
CANDIDATE_QUOTA = 15
TEMPORAL_RADIUS = 1
BUDGET_CHARS = 32_000

FROZEN_INPUTS = {
    "HYPOTHETICAL_001_MECHANICAL_BIOLOGICAL_MEMORY_MODEL.md": (17505, "dbc6a1c4134df37877d6f5a77acdf61db4ce8361a1f7b2a2810b6182a6d6f926"),
    "experiments/components/retrieval_mechanism_ledger/BA_001_REPORT.md": (6861, "efaa03b10a90da68c7f284bb092a80d1edbbb724a84d871cb89a5e4a4a18d14c"),
    "experiments/components/retrieval_mechanism_ledger/artifacts/ba001/results.json": (41619, "1c0d6fb6ef01e991fd7f14ebba2900d0770325c564b64648b9d716a84e1630f1"),
    "experiments/components/retrieval_mechanism_ledger/artifacts/e006_p3_s4/results.json": (741804, "5a6b8a6731b813e0bf63071838d1b14ceaf41362d6548c0bced9777e2bbe49ef"),
    "src/retrieval_mechanism_ledger/e006_p3.py": (7858, "8bb02f16dd6d07cda0d050289dab6ab939e9cf7048d14564b8e71dfbd3347030"),
    "experiments/components/retrieval_mechanism_ledger/artifacts/rd001/full_rank_inventory.csv": (10642, "8d6f9eee6ebe232608981aac0c0d4816eaec4710ae551db028ae0b323253ac03"),
    "experiments/surveys/retrieval_bakeoff/tier6/runs/tier6_live_121_corrected_001/context_matched_stm/study.db": (1978368, "5da47ea3fc2c8e3dcc50fa380ff65202d82557905d9976117e9e5d82e55c1c41"),
    "experiments/surveys/retrieval_bakeoff/holdout/queries_121.json": (4231, "ae950fda20dce9f519f31ee2670a815a5599648cab618d42309db7e3f23d36f4"),
    "experiments/surveys/retrieval_bakeoff/cache/c121_l_span_embeddings.sqlite": (13164544, "a58ee1163d3c2417962b1fcc4ab84dc4edc313c8254a967376a59558ee28a45d"),
    "experiments/components/retrieval_mechanism_ledger/artifacts/e006_p3_tier4a_capture/query_vectors.sqlite": (249856, "d9741edb0545d8cfe050663340599a31813d6025c38f0467e0ec7671573a1e6a"),
    "experiments/components/retrieval_mechanism_ledger/artifacts/e006_p3_tier4a_capture/capture_manifest.json": (17131, "2c24ea75d7551beb6658d8b9208225b985e25a9111cfd3766ec4f7980a7f18e4"),
    "experiments/surveys/retrieval_bakeoff/holdout/answer_key_121.json": (9832, "2d43a31d3c04f4ad690ff2910abde71f508a3f6ce776545a9f2b16f90fae5320"),
    "episodic/src/episodic/_packing.py": (5164, "c5011dada056fa0106544925c75d849c3d5b4857b6c5010ed4b604f9c3d2af04"),
    "episodic/src/episodic/_render.py": (2022, "d0bdc051695fe98064bad9ecc52afe0178bba1ba8a3edf7e3a1960d5f261cf6f"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(data.encode("ascii")).hexdigest()


def verify_inputs() -> list[dict[str, Any]]:
    rows = []
    for relative, (size, digest) in FROZEN_INPUTS.items():
        path = REPO_ROOT / relative
        if not path.is_file() or path.stat().st_size != size or sha256_file(path) != digest:
            raise AssertionError(f"Frozen input mismatch: {relative}")
        rows.append({"path": relative, "bytes": size, "sha256": digest})
    return rows


def load_episodes(max_turn: int) -> list[dict[str, Any]]:
    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
            """
            SELECT id, turn_number, user_message, assistant_message, embedding,
                   ground_truth_domain
            FROM episodes WHERE turn_number <= ? ORDER BY turn_number, id
            """,
            (max_turn,),
        ).fetchall()
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
    if len(episodes) != max_turn:
        raise AssertionError(f"Expected one episode per turn through {max_turn}")
    return episodes


def load_q11_ranking(episodes: Sequence[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    by_id = {episode["id"]: episode for episode in episodes}
    with RANK_INVENTORY.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ranked = tuple(by_id[str(row["episode_id"])] for row in rows)
    if len(ranked) != 119 or len({content_sha256(row) for row in ranked}) != 119:
        raise AssertionError("Q11 rank inventory does not bind 119 unique episodes")
    return ranked


def load_holdout_queries() -> list[dict[str, str]]:
    payload = json.loads(QUERY_MANIFEST.read_text(encoding="utf-8"))
    rows = [{"query_id": str(row["query_id"]), "text": str(row["text"])} for row in payload["queries"]]
    if len(rows) != 24:
        raise AssertionError("TA-001 requires 24 sealed holdout queries")
    return rows


def load_query_vectors(queries: Sequence[dict[str, str]]) -> dict[str, np.ndarray]:
    with sqlite3.connect(QUERY_CACHE) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        expected = {
            "cache_version": "episodic-embedding-cache-v1",
            "model_sha256": "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439",
            "call_shape": "solo",
            "dtype": "float32",
            "dimension": "1024",
        }
        if metadata != expected:
            raise AssertionError("Query cache metadata changed")
        vectors = {}
        for query in queries:
            row = connection.execute(
                "SELECT embedding FROM cache WHERE text = ?", (query["text"],)
            ).fetchone()
            if row is None:
                raise AssertionError(f"Missing query cache hit: {query['query_id']}")
            vector = np.frombuffer(row[0], dtype=np.float32).copy()
            if vector.shape != (1024,):
                raise AssertionError("Query cache vector has wrong dimension")
            vectors[query["query_id"]] = vector
    return vectors


def pack_record(candidates: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_id = {episode["id"]: episode for episode in candidates}
    packed = pack_stm_payload([], list(candidates), BUDGET_CHARS)
    selected = [content_sha256(by_id[value]) for value in packed.selected_ids]
    skipped = [content_sha256(by_id[value]) for value in packed.skipped_k_ids]
    return {
        "candidate_serialized_chars": len(render_stm_payload([], list(candidates))),
        "selected_content_sha256": selected,
        "selected_count": len(selected),
        "selected_sha256": digest_sequence(selected),
        "skipped_content_sha256": skipped,
        "delivered_chars": packed.serialized_chars,
        "payload_sha256": hashlib.sha256(packed.payload.encode("utf-8")).hexdigest(),
    }


def query_record(
    query_id: str,
    ranked: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    rank_by_hash = {content_sha256(episode): rank for rank, episode in enumerate(ranked, 1)}
    control = fixed_query_candidates(ranked, quota=CANDIDATE_QUOTA)
    bridge = temporal_adjacency_bridge(
        ranked, quota=CANDIDATE_QUOTA, radius=TEMPORAL_RADIUS
    )
    control_hashes = [content_sha256(episode) for episode in control]
    treatment_hashes = [content_sha256(episode) for episode in bridge.candidates]
    treatment_seed_ranks = [
        admission.parent_seed_rank for admission in bridge.admissions if admission.role == "seed"
    ]
    return {
        "query_id": query_id,
        "direct_rank_content_sha256": [content_sha256(episode) for episode in ranked],
        "direct_rank_source_turns": [int(episode["turn_number"]) for episode in ranked],
        "C0": {
            "candidate_content_sha256": control_hashes,
            "candidate_source_turns": [int(episode["turn_number"]) for episode in control],
            "candidate_sha256": digest_sequence(control_hashes),
            **pack_record(control),
        },
        "T1": {
            "candidate_content_sha256": treatment_hashes,
            "candidate_source_turns": [int(episode["turn_number"]) for episode in bridge.candidates],
            "candidate_sha256": digest_sequence(treatment_hashes),
            "admissions": [admission.__dict__ for admission in bridge.admissions],
            "skipped_duplicates": list(bridge.skipped_duplicates),
            "seed_count": sum(admission.role == "seed" for admission in bridge.admissions),
            "neighbor_count": sum(admission.role != "seed" for admission in bridge.admissions),
            "admitted_direct_ranks": [rank_by_hash[value] for value in treatment_hashes],
            "seed_ranks": treatment_seed_ranks,
            **pack_record(bridge.candidates),
        },
        "candidate_overlap_count": len(set(control_hashes) & set(treatment_hashes)),
        "displaced_control_content_sha256": sorted(set(control_hashes) - set(treatment_hashes)),
    }


def verify_q11_reproduction(record: dict[str, Any]) -> dict[str, Any]:
    committed = json.loads(E006_RESULTS.read_text(encoding="utf-8"))
    a0 = next(row for row in committed["primary_cells"] if row["arm"] == "A0")
    checks = {
        "candidate_sha256": record["C0"]["candidate_sha256"] == a0["candidate_sha256"],
        "selected_sha256": record["C0"]["selected_sha256"] == a0["selected_sha256"],
        "payload_sha256": record["C0"]["payload_sha256"] == a0["payload_sha256"],
        "delivered_chars": record["C0"]["delivered_chars"] == a0["delivered_chars"],
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def source_audit() -> dict[str, Any]:
    component_tree = ast.parse(COMPONENT_SOURCE.read_text(encoding="utf-8"))
    imports = [
        node.module or ""
        for node in ast.walk(component_tree)
        if isinstance(node, (ast.ImportFrom,))
    ]
    forbidden_imports = [
        value for value in imports if any(part in value.lower() for part in ("answer", "rubric", "scoring", "fact"))
    ]
    planted_stopped = False
    try:
        assert_mechanism_path_allowed("fixtures/answer_key_planted.json")
    except ValueError:
        planted_stopped = True
    return {
        "forbidden_imports": forbidden_imports,
        "planted_forbidden_path_stopped": planted_stopped,
        "answer_key_access": "hash_only_in_input_verifier",
        "status": "PASS" if not forbidden_imports and planted_stopped else "FAIL",
    }


def characterize(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    neighbor_ranks = [
        rank
        for record in records
        for rank, admission in zip(
            record["T1"]["admitted_direct_ranks"], record["T1"]["admissions"], strict=True
        )
        if admission["role"] != "seed"
    ]
    roles = Counter(
        admission["role"] for record in records for admission in record["T1"]["admissions"]
    )
    candidate_sequences = [record["T1"]["candidate_sha256"] for record in records]
    return {
        "query_count": len(records),
        "role_counts": dict(sorted(roles.items())),
        "neighbor_direct_rank_distribution": sorted(neighbor_ranks),
        "candidate_overlap_distribution": sorted(record["candidate_overlap_count"] for record in records),
        "treatment_seed_count_distribution": sorted(record["T1"]["seed_count"] for record in records),
        "treatment_neighbor_count_distribution": sorted(record["T1"]["neighbor_count"] for record in records),
        "control_selected_count_distribution": sorted(record["C0"]["selected_count"] for record in records),
        "treatment_selected_count_distribution": sorted(record["T1"]["selected_count"] for record in records),
        "control_delivered_chars_distribution": sorted(record["C0"]["delivered_chars"] for record in records),
        "treatment_delivered_chars_distribution": sorted(record["T1"]["delivered_chars"] for record in records),
        "unique_treatment_candidate_sequences": len(set(candidate_sequences)),
        "constant_output": len(set(candidate_sequences)) == 1,
        "boundary_admissions": [
            {"query_id": record["query_id"], **admission}
            for record in records
            for admission in record["T1"]["admissions"]
            if admission["source_turn"] in (1, 111, 119)
        ],
        "duplicate_skip_count": sum(len(record["T1"]["skipped_duplicates"]) for record in records),
        "quota_truncation_count": len(records),
    }


def eligibility(records: Sequence[dict[str, Any]], reproduction: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "exact_unique_quota": all(
            len(record[arm]["candidate_content_sha256"]) == CANDIDATE_QUOTA
            and len(set(record[arm]["candidate_content_sha256"])) == CANDIDATE_QUOTA
            for record in records for arm in ("C0", "T1")
        ),
        "neighbors_radius_one": all(
            admission["temporal_distance"] == 1
            for record in records for admission in record["T1"]["admissions"]
            if admission["role"] != "seed"
        ),
        "seed_order_preserved": all(
            record["T1"]["seed_ranks"] == sorted(record["T1"]["seed_ranks"])
            for record in records
        ),
        "payload_budget": all(
            record[arm]["delivered_chars"] <= BUDGET_CHARS
            for record in records for arm in ("C0", "T1")
        ),
        "q11_reproduction": reproduction["status"] == "PASS",
        "source_audit": audit["status"] == "PASS",
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def run(output_dir: Path, process_tag: str) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite exploration output: {output_dir}")
    started = time.perf_counter()
    inventory = verify_inputs()
    episodes_119 = load_episodes(119)
    episodes_111 = episodes_119[:111]
    queries = load_holdout_queries()
    vectors = load_query_vectors(queries)
    records = [query_record("q11", load_q11_ranking(episodes_119))]
    records.extend(
        query_record(query["query_id"], rank_by_query(episodes_111, vectors[query["query_id"]]))
        for query in queries
    )
    reproduction = verify_q11_reproduction(records[0])
    audit = source_audit()
    distribution = characterize(records)
    gate = eligibility(records, reproduction, audit)
    core = {
        "study": "TA-001 temporal-adjacency bridge",
        "part": "label-blind exploration",
        "parameters": {"candidate_quota": CANDIDATE_QUOTA, "temporal_radius": TEMPORAL_RADIUS, "budget_chars": BUDGET_CHARS},
        "calls": {"embedding": 0, "model_generation": 0},
        "input_inventory": inventory,
        "query_cache_hits": len(vectors),
        "records": records,
        "distribution": distribution,
        "q11_reproduction": reproduction,
        "source_audit": audit,
        "eligibility": gate,
    }
    deterministic_digest = canonical_digest(core)
    result = {
        **core,
        "deterministic_digest": deterministic_digest,
        "process": {
            "tag": process_tag,
            "pid": os.getpid(),
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "elapsed_seconds": time.perf_counter() - started,
            "thread_environment": {name: os.environ.get(name) for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
        },
    }
    output_dir.mkdir(parents=True)
    write_json(output_dir / "exploration.json", result)
    with (output_dir / "query_traces.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n")
    manifest_rows = []
    for path in sorted(output_dir.iterdir()):
        manifest_rows.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    write_json(output_dir / "artifact_manifest.json", {"files": manifest_rows, "deterministic_digest": deterministic_digest})
    return result


def compare(first: Path, second: Path, output: Path) -> dict[str, Any]:
    left = json.loads((first / "exploration.json").read_text(encoding="utf-8"))
    right = json.loads((second / "exploration.json").read_text(encoding="utf-8"))
    def display_path(path: Path) -> str:
        try:
            return path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return path.as_posix()

    result = {
        "status": "PASS" if left["deterministic_digest"] == right["deterministic_digest"] else "FAIL",
        "first_digest": left["deterministic_digest"],
        "second_digest": right["deterministic_digest"],
        "first_path": display_path(first),
        "second_path": display_path(second),
    }
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite comparison: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    if result["status"] != "PASS":
        raise AssertionError("TA-001 fresh-process determinism failed")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--process-tag", default="process_1")
    parser.add_argument("--compare", nargs=2, type=Path)
    parser.add_argument("--comparison-output", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.compare:
        if args.comparison_output is None:
            raise SystemExit("--comparison-output is required with --compare")
        compared = compare(args.compare[0], args.compare[1], args.comparison_output)
        print(json.dumps(compared, sort_keys=True))
    else:
        result = run(args.output, args.process_tag)
        print(json.dumps({"status": result["eligibility"]["status"], "deterministic_digest": result["deterministic_digest"]}, sort_keys=True))

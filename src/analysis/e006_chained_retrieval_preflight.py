from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sqlite3
import subprocess
import sys
import types
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
)
RUN_ROOT = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier6"
    / "runs"
    / "tier6_live_121_corrected_001"
    / "context_matched_stm"
)
ANALYSIS_ROOT = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier6"
    / "analysis_corrected_121"
)

DESIGN = COMPONENT_ROOT / "E006_PART2_chained_retrieval.md"
AUTHORIZATION = COMPONENT_ROOT / "E006_PART2_AUTHORIZATION.md"
S1_REPORT = COMPONENT_ROOT / "E006_PART2_S1_PRIOR_ART_SCAN.md"
PREFLIGHT_RULE = REPO_ROOT / "PREFLIGHT.md"
LEDGER = COMPONENT_ROOT / "RETRIEVAL_MECHANISM_LEDGER.md"
CONTEXT_LOG = RUN_ROOT / "logs" / "context_match.jsonl"
TURN_LOG = RUN_ROOT / "logs" / "turns.jsonl"
DATABASE = RUN_ROOT / "study.db"
TARGETED_MEASUREMENT = ANALYSIS_ROOT / "targeted_fact_delivery.csv"
Q11_RANK_INVENTORY = COMPONENT_ROOT / "artifacts" / "rd001" / "full_rank_inventory.csv"
COMMITTED_X0 = COMPONENT_ROOT / "artifacts" / "e005" / "a0_baseline.json"
PACKER_SOURCE = REPO_ROOT / "episodic" / "src" / "episodic" / "_packing.py"
RENDERER_SOURCE = REPO_ROOT / "episodic" / "src" / "episodic" / "_render.py"
RETRIEVAL_SOURCE = REPO_ROOT / "src" / "memory" / "context_matched_stm.py"
RUNNER_SOURCE = REPO_ROOT / "src" / "study" / "retrieval_bakeoff_tier6_runner.py"

NAMED_COMPANIONS = (
    COMPONENT_ROOT / "NEUROSCIENCE_LANDSCAPE.md",
    REPO_ROOT / "STANDING_RULE_preflight.md",
)
DISCOVERED_NEAR_MATCHES = (
    COMPONENT_ROOT / "LITERATURE_LANDSCAPE.md",
    PREFLIGHT_RULE,
)
EMBEDDING_CACHES = (
    REPO_ROOT
    / "experiments"
    / "external"
    / "longmemeval"
    / "runs"
    / "ec002_k_first"
    / "ec002_exact_solo_embeddings.db",
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "cache"
    / "c1000_l_span_embeddings.sqlite",
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "cache"
    / "c1000_s_span_embeddings.sqlite",
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "cache"
    / "c121_l_span_embeddings.sqlite",
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "cache"
    / "c121_s_span_embeddings.sqlite",
)

DESIGN_SHA256 = "84a5eb5b29a01f4027b4e18411f8d0d99d41c7eea3206e4ed329063d13b35dc1"
DESIGN_COMMIT = "7fa09c62"
S1_COMMIT = "1ef754a3"
BUDGET_CHARS = 32_000
PROBE_TURNS = (112, 113, 115, 116, 117, 118, 119, 120)
DEPTHS = (1, 2, 3)
PER_STEP_COUNTS = (3, 5)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_sha256(episode: dict[str, Any]) -> str:
    stable = {
        "assistant_message": str(episode["assistant_message"]),
        "turn_number": int(episode["turn_number"]),
        "user_message": str(episode["user_message"]),
    }
    encoded = json.dumps(
        stable,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_episodes() -> list[dict[str, Any]]:
    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
            """
            SELECT id, user_message, assistant_message, embedding,
                   turn_number, text
            FROM episodes
            ORDER BY turn_number, id
            """
        ).fetchall()
    return [
        {
            "id": row[0],
            "user_message": row[1],
            "assistant_message": row[2],
            "embedding": row[3],
            "turn_number": row[4],
            "text": row[5],
        }
        for row in rows
    ]


def load_probe_queries() -> dict[int, str]:
    rows = read_jsonl(TURN_LOG)
    queries = {
        int(row["turn_number"]): str(row["user_message"])
        for row in rows
        if int(row["turn_number"]) in PROBE_TURNS
    }
    if tuple(sorted(queries)) != PROBE_TURNS:
        raise AssertionError("The committed turn log lacks a registered probe")
    return queries


def load_authoritative_packer():
    package_name = "_e006_episodic_contract"
    package = types.ModuleType(package_name)
    package.__path__ = []  # type: ignore[attr-defined]
    sys.modules[package_name] = package

    render_name = f"{package_name}._render"
    render_spec = importlib.util.spec_from_file_location(render_name, RENDERER_SOURCE)
    if render_spec is None or render_spec.loader is None:
        raise RuntimeError("Could not load the authoritative renderer")
    render_module = importlib.util.module_from_spec(render_spec)
    sys.modules[render_name] = render_module
    render_spec.loader.exec_module(render_module)

    packing_name = f"{package_name}._packing"
    packing_spec = importlib.util.spec_from_file_location(packing_name, PACKER_SOURCE)
    if packing_spec is None or packing_spec.loader is None:
        raise RuntimeError("Could not load the authoritative packer")
    packing_module = importlib.util.module_from_spec(packing_spec)
    sys.modules[packing_name] = packing_module
    packing_spec.loader.exec_module(packing_module)
    return packing_module.pack_stm_payload


def input_inventory() -> list[dict[str, Any]]:
    paths = (
        DESIGN,
        AUTHORIZATION,
        S1_REPORT,
        PREFLIGHT_RULE,
        LEDGER,
        CONTEXT_LOG,
        TURN_LOG,
        DATABASE,
        TARGETED_MEASUREMENT,
        Q11_RANK_INVENTORY,
        COMMITTED_X0,
        PACKER_SOURCE,
        RENDERER_SOURCE,
        RETRIEVAL_SOURCE,
        RUNNER_SOURCE,
        *EMBEDDING_CACHES,
    )
    return [
        {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in paths
    ]


def inspect_store(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    vector_lengths = Counter(len(episode["embedding"]) for episode in episodes)
    pair_text_matches = sum(
        episode["text"]
        == (
            f"User: {episode['user_message']}\n"
            f"Assistant: {episode['assistant_message']}"
        )
        for episode in episodes
    )
    return {
        "episode_count": len(episodes),
        "turn_min": min(int(episode["turn_number"]) for episode in episodes),
        "turn_max": max(int(episode["turn_number"]) for episode in episodes),
        "embedding_blob_bytes": {
            str(length): count for length, count in sorted(vector_lengths.items())
        },
        "embedding_dimension_float32": sorted(
            {length // 4 for length in vector_lengths}
        ),
        "pair_text_binding_matches": pair_text_matches,
        "pair_text_binding_total": len(episodes),
        "interpretation": (
            "The store vectors are episode-pair vectors. They are not raw "
            "probe-query vectors and cannot substitute for q0."
        ),
    }


def cache_probe_hits(queries: dict[int, str]) -> list[dict[str, Any]]:
    results = []
    for path in EMBEDDING_CACHES:
        hits: dict[str, bool] = {}
        with sqlite3.connect(path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            if "cache" in tables:
                for turn, query in queries.items():
                    row = connection.execute(
                        "SELECT 1 FROM cache WHERE text = ?", (query,)
                    ).fetchone()
                    hits[str(turn)] = row is not None
                key_mode = "exact_text"
            elif "embeddings" in tables:
                for turn, query in queries.items():
                    text_digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
                    row = connection.execute(
                        "SELECT 1 FROM embeddings WHERE text_sha256 = ?",
                        (text_digest,),
                    ).fetchone()
                    hits[str(turn)] = row is not None
                key_mode = "sha256_utf8_text"
            else:
                raise AssertionError(f"Unknown embedding cache schema: {path}")
        results.append(
            {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_file(path),
                "key_mode": key_mode,
                "probe_hits": hits,
                "hit_count": sum(hits.values()),
            }
        )
    return results


def retrieval_distribution() -> dict[str, Any]:
    rows = read_jsonl(CONTEXT_LOG)
    histogram = Counter(int(row["k_candidate_count"]) for row in rows)
    probe_rows = {
        str(row["turn_number"]): {
            "k_candidate_count": int(row["k_candidate_count"]),
            "k_delivered_count": int(row["k_delivered_count"]),
            "n_candidate_count": int(row["n_candidate_count"]),
            "n_delivered_count": int(row["n_delivered_count"]),
        }
        for row in rows
        if int(row["turn_number"]) in PROBE_TURNS
    }
    return {
        "turn_count": len(rows),
        "k_candidate_count_histogram": {
            str(count): frequency for count, frequency in sorted(histogram.items())
        },
        "probe_turns": probe_rows,
    }


def reproduce_x0(
    episodes: list[dict[str, Any]],
    pack_stm_payload,
) -> dict[str, Any]:
    by_id = {str(episode["id"]): episode for episode in episodes}
    context = next(
        row
        for row in read_jsonl(CONTEXT_LOG)
        if int(row["turn_number"]) == 120
    )
    n_candidates = [by_id[str(value)] for value in context["n_candidate_ids"]]
    n_ids = {str(value) for value in context["n_candidate_ids"]}
    k_candidates = [
        by_id[str(value)]
        for value in context["k_candidate_ids"]
        if str(value) not in n_ids
    ]
    packed = pack_stm_payload(n_candidates, k_candidates, BUDGET_CHARS)
    committed = json.loads(COMMITTED_X0.read_text(encoding="utf-8"))
    selected_hashes = [
        content_sha256(by_id[episode_id]) for episode_id in packed.selected_ids
    ]
    committed_hashes = [
        content_sha256(by_id[episode_id])
        for episode_id in committed["selected_ids"]
    ]
    payload_sha256 = hashlib.sha256(packed.payload.encode("utf-8")).hexdigest()
    checks = {
        "content_hash_sequence_equal": selected_hashes == committed_hashes,
        "payload_sha256_equal": payload_sha256 == committed["payload_sha256"],
        "serialized_chars_equal": packed.serialized_chars
        == committed["serialized_chars"],
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "comparison_key": "episode_content_sha256",
        "checks": checks,
        "selected_content_sha256": selected_hashes,
        "selected_source_turns": [
            int(episode["turn_number"])
            for episode in (*packed.recent_episodes, *packed.stm_episodes)
        ],
        "selected_episode_count": len(packed.selected_ids),
        "serialized_chars": packed.serialized_chars,
        "payload_sha256": payload_sha256,
        "committed_payload_sha256": committed["payload_sha256"],
    }


def disabled_chain_control(
    episodes: list[dict[str, Any]],
    pack_stm_payload,
) -> dict[str, Any]:
    by_id = {str(episode["id"]): episode for episode in episodes}
    with Q11_RANK_INVENTORY.open(encoding="utf-8", newline="") as handle:
        ranks = list(csv.DictReader(handle))
    ranked = [by_id[str(row["episode_id"])] for row in ranks]
    top_four_fact_counts = [int(row["fact_count"]) for row in ranks[:4]]
    cells = []
    for per_step in PER_STEP_COUNTS:
        single = pack_stm_payload([], ranked[:per_step], BUDGET_CHARS)
        single_digest = hashlib.sha256(single.payload.encode("utf-8")).hexdigest()
        single_hashes = [content_sha256(by_id[value]) for value in single.selected_ids]
        for depth in DEPTHS:
            # With BETA=0, c remains q0. exclude=seen therefore takes the next
            # m episodes on each of the D+1 inclusive loop iterations.
            considered = per_step * (depth + 1)
            chained = pack_stm_payload([], ranked[:considered], BUDGET_CHARS)
            chained_digest = hashlib.sha256(
                chained.payload.encode("utf-8")
            ).hexdigest()
            chained_hashes = [
                content_sha256(by_id[value]) for value in chained.selected_ids
            ]
            cells.append(
                {
                    "D": depth,
                    "m": per_step,
                    "loop_iterations": depth + 1,
                    "single_shot_episode_count": len(single.selected_ids),
                    "disabled_chain_episode_count": len(chained.selected_ids),
                    "single_shot_payload_sha256": single_digest,
                    "disabled_chain_payload_sha256": chained_digest,
                    "content_hash_sequence_equal": single_hashes == chained_hashes,
                    "payload_sha256_equal": single_digest == chained_digest,
                }
            )
    all_equal = all(cell["payload_sha256_equal"] for cell in cells)
    return {
        "status": "PASS" if all_equal else "FAIL",
        "registered_assertion": "X1 equals X0 across all probes by payload digest",
        "mechanical_result": (
            "BETA=0 fixes the cue at q0, but exclude=seen and the inclusive "
            "0..D loop accumulate m*(D+1) candidates instead of m."
        ),
        "comparison_key": "episode_content_sha256",
        "q11_top_four_fact_counts": top_four_fact_counts,
        "cells": cells,
    }


def git_ordering() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.check_output(
            ("git", *args), cwd=REPO_ROOT, text=True
        ).strip()

    design_full = run("rev-parse", DESIGN_COMMIT)
    s1_full = run("rev-parse", S1_COMMIT)
    subprocess.check_call(
        ("git", "merge-base", "--is-ancestor", design_full, s1_full),
        cwd=REPO_ROOT,
    )
    subprocess.check_call(
        ("git", "merge-base", "--is-ancestor", s1_full, "HEAD"),
        cwd=REPO_ROOT,
    )
    return {
        "status": "PASS",
        "design_commit": design_full,
        "s1_commit": s1_full,
        "head_at_preflight_execution": run("rev-parse", "HEAD"),
        "assertion": (
            "design_commit is ancestor of s1_commit, which is ancestor of HEAD"
        ),
    }


def checklist(
    *,
    cache_hits: list[dict[str, Any]],
    companions: dict[str, Any],
    x0: dict[str, Any],
    x1: dict[str, Any],
    ordering: dict[str, Any],
) -> dict[str, dict[str, str]]:
    query_vectors_found = sum(item["hit_count"] for item in cache_hits)
    return {
        "PF1": {
            "status": "FAIL",
            "evidence": (
                f"Store and candidate identities exist, but {query_vectors_found}/"
                f"{len(PROBE_TURNS)} probe q0 vectors were found in all committed "
                "caches; candidate identities cannot compute chained cue updates. "
                f"Named companion resolution is {companions['status']}."
            ),
        },
        "PF2": {
            "status": "FAIL",
            "evidence": (
                "Existing components are behaviorally identified, but deployed X0 "
                "uses thresholded K plus rotating N-first packing while the proposed "
                "chain uses top_m; they are not one named retrieval operation."
            ),
        },
        "PF3": {
            "status": ordering["status"],
            "evidence": ordering["assertion"],
        },
        "PF4": {
            "status": "FAIL",
            "evidence": (
                "The 32,000-character capacity precedent is available, but maximum "
                "seed reachability by depth cannot be computed without q0 vectors."
            ),
        },
        "PF5": {
            "status": "PASS",
            "evidence": (
                "All new identity comparisons use SHA-256 over canonical episode "
                "content; source UUIDs are used only to dereference committed rows."
            ),
        },
        "PF6": {
            "status": "FAIL",
            "evidence": (
                f"X0 reproduction is {x0['status']}, but the mandatory X1=X0 "
                f"control is {x1['status']} for every registered (D,m) cell."
            ),
        },
        "PF7": {
            "status": "FAIL",
            "evidence": (
                "A real chained trace, context-vector trace, cycle sweep, and "
                "per-step novelty calculation cannot run without q0 vectors."
            ),
        },
        "PF8": {
            "status": "PASS",
            "evidence": (
                "Depth is fully exercised within one probe; a 35-turn ablation can "
                "detect depth-local cycles and drift but cannot estimate live answer "
                "variance or long-horizon cross-turn state."
            ),
        },
        "PF9": {
            "status": "PASS",
            "evidence": (
                "Availability can rise without answer quality; no-cycle can miss "
                "near-degeneracy; targeted aggregates can hide per-probe loss. The "
                "registered mitigations and one-corpus residual remain explicit."
            ),
        },
        "PF10": {
            "status": "PASS",
            "evidence": (
                "S4 is delivery characterization only. S5 requires a separate "
                "registration and authorization and was not run."
            ),
        },
    }


def build_preflight() -> dict[str, Any]:
    if sha256_file(DESIGN) != DESIGN_SHA256:
        raise AssertionError("E006 Part 2 design anchor digest changed")
    episodes = load_episodes()
    queries = load_probe_queries()
    pack_stm_payload = load_authoritative_packer()
    cache_hits = cache_probe_hits(queries)
    companions = {
        "status": "PASS" if all(path.exists() for path in NAMED_COMPANIONS) else "FAIL",
        "named": [
            {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "exists": path.exists(),
            }
            for path in NAMED_COMPANIONS
        ],
        "near_matches_not_substituted": [
            {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "exists": path.exists(),
            }
            for path in DISCOVERED_NEAR_MATCHES
        ],
    }
    x0 = reproduce_x0(episodes, pack_stm_payload)
    x1 = disabled_chain_control(episodes, pack_stm_payload)
    ordering = git_ordering()
    checks = checklist(
        cache_hits=cache_hits,
        companions=companions,
        x0=x0,
        x1=x1,
        ordering=ordering,
    )
    return {
        "study": "E006 Part 2 chained retrieval",
        "stage": "S2 Preflight",
        "status": "PASS"
        if all(item["status"] == "PASS" for item in checks.values())
        else "FAIL",
        "decision": "STOP_BEFORE_S3",
        "design_sha256": DESIGN_SHA256,
        "zero_model_calls": True,
        "zero_embedding_calls": True,
        "input_inventory": input_inventory(),
        "companion_resolution": companions,
        "exploration": {
            "E1_current_cue": {
                "status": "FAIL_INCOMPLETE",
                "probe_turns": list(PROBE_TURNS),
                "probe_query_sha256": {
                    str(turn): hashlib.sha256(query.encode("utf-8")).hexdigest()
                    for turn, query in queries.items()
                },
                "embedding_cache_checks": cache_hits,
                "q11_rank_inventory_available": True,
                "all_probe_cosines_available": False,
                "all_probe_fact_rank_distributions_available": False,
                "q11_top_four_fact_counts": x1["q11_top_four_fact_counts"],
            },
            "E2_component_identity": {
                "seeding_path": (
                    "The live runner embeds the raw current user message for K; "
                    "stored vectors embed the full User/Assistant episode pair."
                ),
                "K_threshold": (
                    "K scans every eligible episode in store order and returns each "
                    "cosine >= 0.48; it is not top_m."
                ),
                "packer": (
                    "The packer considers N before K, charges exact compact XML "
                    "serialization, skips an overflow candidate, and continues."
                ),
                "renderer": (
                    "The renderer emits compact recent_context and retrieved_stm "
                    "XML blocks with escaped turn, user, and assistant content."
                ),
                "proposed_chain": (
                    "The spec retrieves top_m unseen episodes per inclusive 0..D "
                    "step and blends their mean episode vector into the next cue."
                ),
            },
            "E3_feedback_inventory": {
                "state": ("seen", "c"),
                "updates": (
                    "seen grows monotonically by retrieved identities; c is a "
                    "normalized blend of prior c and mean(hit embeddings)."
                ),
                "absorbing_candidates": (
                    "seen cannot decay; BETA=0 fixes c at q0; missing q0 prevents "
                    "the required real-trace cycle and near-degeneracy sweep."
                ),
            },
            "E4_return_distribution": retrieval_distribution(),
            "store": inspect_store(episodes),
            "x0_reproduction": x0,
            "x1_disabled_chain": x1,
        },
        "gate_ordering": ordering,
        "checklist": checks,
        "binding_failures": [
            (
                "No committed raw probe-query vectors exist for the eight probes; "
                "candidate identities reproduce X0 but cannot execute E-1 or the "
                "chained update."
            ),
            (
                "The registered X1 control is structurally unequal to single-shot "
                "retrieval because exclude=seen accumulates m new episodes on each "
                "of D+1 iterations even when BETA=0."
            ),
            (
                "The spec names two companion files that do not exist; near-matching "
                "files were not silently substituted."
            ),
        ],
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run E006 Part 2 S2 Preflight")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    result = build_preflight()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    print(json.dumps({"status": result["status"], "output": str(output)}))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

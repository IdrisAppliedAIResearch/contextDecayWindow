from __future__ import annotations

import argparse
import ast
import html
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from src.analysis.ps002_exploration import DATABASE, canonical_json_bytes, sha256_file
from src.analysis.ps003_preflight import (
    ANSWER_KEY,
    EXPECTED_MECHANISM_DIGEST,
    EXPECTED_SELECTED_DIGEST,
    guarded_answer_key_load,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
PREFLIGHT = COMPONENT_ROOT / "artifacts" / "ps003_preflight" / "preflight.json"
SELECTED_TRACES = (
    COMPONENT_ROOT
    / "artifacts"
    / "ps003_exploration"
    / "part1_process_1"
    / "cells"
    / "p5_s4"
    / "traces.jsonl"
)
PS002_TRACES = (
    COMPONENT_ROOT
    / "artifacts"
    / "ps002_exploration"
    / "part1_process_1"
    / "cells"
    / "m4_t0.025"
    / "traces.jsonl"
)
PS003_MECHANISM_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "ps003.py"
MEASUREMENT_SOURCE = Path(__file__).resolve()

PREFLIGHT_COMMIT = "7e26e44362ff82402beba3eb94e0164c14d9e5cc"
EXPECTED_PREFLIGHT_SHA256 = "d70e2a20466d74830213c9f034aff93ecca422181c20b3a7d12c2441b6751ad7"
EXPECTED_SELECTED_TRACES_SHA256 = "d3a86d8ba6f6d323e8275eeb2ba8ff2416d3008e3b799d4b7ab0c698dee275d0"
EXPECTED_PS002_TRACES_SHA256 = "c2504d3d77112bcb1cfdf422fbdc2e633df5e6a878f68f49800da0d7a2b4950d"
GATE_ORDER = ("G1", "G2", "G3", "G4", "G5")


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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def measurement_prerequisites(preflight_path: Path = PREFLIGHT) -> dict[str, Any]:
    if not preflight_path.is_file():
        raise RuntimeError("Committed passing PS-003 Preflight is required")
    if preflight_path == PREFLIGHT and sha256_file(preflight_path) != EXPECTED_PREFLIGHT_SHA256:
        raise RuntimeError("PS-003 Preflight identity changed")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS":
        raise RuntimeError("PS-003 Preflight is not passing")
    if preflight.get("selected_configuration") != {"probe_count": 5, "swap_count": 4}:
        raise RuntimeError("PS-003 Preflight selected configuration changed")
    if preflight_path == PREFLIGHT and not _ancestor(PREFLIGHT_COMMIT, _git("rev-parse", "HEAD")):
        raise RuntimeError("PS-003 Preflight is not committed before measurement")
    if sha256_file(SELECTED_TRACES) != EXPECTED_SELECTED_TRACES_SHA256:
        raise RuntimeError("PS-003 selected traces changed")
    if sha256_file(PS002_TRACES) != EXPECTED_PS002_TRACES_SHA256:
        raise RuntimeError("PS-002 control traces changed")
    return {
        "status": "PASS",
        "preflight_sha256": sha256_file(preflight_path),
        "preflight_payload_sha256": preflight["preflight_payload_sha256"],
        "selected_digest": preflight["checks"]["PF6"]["ps003_selected_digest"],
        "determinism_status": "PASS",
        "mechanism_digest": preflight["checks"]["PF6"]["ps003_two_process_digest"],
        "preflight": preflight,
    }


def load_measurement_key(prerequisites: Mapping[str, Any]) -> dict[str, Any]:
    if prerequisites.get("selected_digest") != EXPECTED_SELECTED_DIGEST:
        raise RuntimeError("Selected digest failed before measurement key parse")
    if prerequisites.get("mechanism_digest") != EXPECTED_MECHANISM_DIGEST:
        raise RuntimeError("Mechanism digest failed before measurement key parse")
    return guarded_answer_key_load(prerequisites)


def mechanism_import_audit() -> dict[str, Any]:
    tree = ast.parse(
        PS003_MECHANISM_SOURCE.read_text(encoding="utf-8"),
        filename=str(PS003_MECHANISM_SOURCE),
    )
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    forbidden = sorted(value for value in imports if "measurement" in value.casefold())
    return {
        "status": "PASS" if not forbidden else "FAIL",
        "mechanism_imports_measurement": forbidden,
    }


def load_episodes() -> list[dict[str, Any]]:
    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
            """
            SELECT turn_number, user_message, assistant_message
            FROM episodes
            WHERE turn_number < 120
            ORDER BY turn_number, id
            """
        ).fetchall()
    if len(rows) != 119:
        raise AssertionError("PS-003 measurement requires 119 episodes")
    from src.analysis.ps001_exploration import load_episode_population

    population = load_episode_population()
    return [
        {
            "index": index,
            "turn_number": int(row[0]),
            "user_message": str(row[1]),
            "assistant_message": str(row[2]),
            "content_sha256": population.hashes[index],
        }
        for index, row in enumerate(rows)
    ]


def episode_matches_fact(episode: Mapping[str, Any], fact: Mapping[str, Any]) -> bool:
    terms = [str(term).casefold() for term in fact["required_terms"]]
    serialized = html.unescape(
        str(episode["user_message"]) + "\n" + str(episode["assistant_message"])
    ).casefold()
    role_text = html.unescape(
        str(episode[str(fact["source_role"]) + "_message"])
    ).casefold()
    return bool(
        int(episode["turn_number"]) in {int(turn) for turn in fact["source_turns"]}
        and all(term in serialized for term in terms)
        and all(term in role_text for term in terms)
    )


def evaluate_identity_list(
    indices: Sequence[int],
    query: Mapping[str, Any],
    facts: Mapping[str, Mapping[str, Any]],
    episodes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    matched = []
    for fact_id in query["required_fact_ids"]:
        ranks = [
            rank
            for rank, episode_index in enumerate(indices, start=1)
            if episode_matches_fact(episodes[int(episode_index)], facts[fact_id])
        ]
        if ranks:
            rank = ranks[0]
            episode = episodes[int(indices[rank - 1])]
            matched.append(
                {
                    "fact_id": fact_id,
                    "rank": rank,
                    "reciprocal_rank": 1.0 / rank,
                    "episode_content_sha256": episode["content_sha256"],
                    "source_turn": episode["turn_number"],
                }
            )
    return {
        "ordered_episode_indices": list(indices),
        "ordered_source_turns": [episodes[int(index)]["turn_number"] for index in indices],
        "ordered_content_sha256": [episodes[int(index)]["content_sha256"] for index in indices],
        "facts_required": len(query["required_fact_ids"]),
        "facts_available": len(matched),
        "query_complete": len(matched) == len(query["required_fact_ids"]),
        "matched_facts": matched,
        "first_match_reciprocal_rank": max(
            (row["reciprocal_rank"] for row in matched), default=0.0
        ),
    }


def execute_ordered_gates(
    stages: Sequence[tuple[str, Callable[[], dict[str, Any]]]]
) -> dict[str, dict[str, Any] | str]:
    results: dict[str, dict[str, Any] | str] = {}
    stopped = False
    for name, stage in stages:
        if stopped:
            results[name] = "NOT_REACHED"
            continue
        result = stage()
        results[name] = result
        if result["status"] != "PASS":
            stopped = True
    return results


def _lookup_summary(rows: Sequence[Mapping[str, Any]], arm: str) -> dict[str, Any]:
    domains = ("structural", "art", "monetary", "marine")
    return {
        "facts_available": sum(row[arm]["facts_available"] for row in rows),
        "queries_complete": sum(row[arm]["query_complete"] for row in rows),
        "per_domain_facts_available": {
            domain: sum(
                row[arm]["facts_available"] for row in rows if domain in row["domains"]
            )
            for domain in domains
        },
    }


def build_measurement() -> dict[str, Any]:
    prerequisites = measurement_prerequisites()
    key = load_measurement_key(prerequisites)
    audit = mechanism_import_audit()
    episodes = load_episodes()
    selected_rows = {row["query_id"]: row for row in _read_jsonl(SELECTED_TRACES)}
    ps002_rows = {row["query_id"]: row for row in _read_jsonl(PS002_TRACES)}
    lookup_results = []
    for query in key["queries"]:
        if query["query_class"] != "lookup":
            continue
        query_id = query["query_id"]
        selected = selected_rows[query_id]
        ps002 = ps002_rows[query_id]
        direct_indices = selected["semantic_order"][:8]
        lookup_results.append(
            {
                "query_id": query_id,
                "query_class": query["query_class"],
                "domains": list(query["domains"]),
                "required_fact_ids": list(query["required_fact_ids"]),
                "direct_cosine_top8": evaluate_identity_list(
                    direct_indices, query, key["facts"], episodes
                ),
                "ps002_strongest": evaluate_identity_list(
                    ps002["emitted_indices"], query, key["facts"], episodes
                ),
                "ps003_resolver": evaluate_identity_list(
                    selected["emitted_indices"], query, key["facts"], episodes
                ),
                "ps003_base_attempts": [
                    {
                        "attempt_index": attempt["attempt_index"],
                        "base_cue_sha256": attempt["base_cue_sha256"],
                        "base_terminal_sha256": attempt["probes"][0]["terminal_sha256"],
                        "base_stored_index": attempt["probes"][0]["stored_index"],
                        "attempt_outcome": attempt["outcome"],
                    }
                    for attempt in selected["attempts"]
                ],
            }
        )

    resolver_summary = _lookup_summary(lookup_results, "ps003_resolver")
    cosine_summary = _lookup_summary(lookup_results, "direct_cosine_top8")
    ps002_summary = _lookup_summary(lookup_results, "ps002_strongest")

    def g1() -> dict[str, Any]:
        passed = bool(
            prerequisites["preflight"]["checks"]["PF6"]["status"] == "PASS"
            and audit["status"] == "PASS"
        )
        return {
            "status": "PASS" if passed else "FAIL",
            "failure_disposition": "CARRIED_MECHANISM_IDENTITY_FAILED",
            "preflight_pf6": prerequisites["preflight"]["checks"]["PF6"],
            "mechanism_import_audit": audit,
        }

    def g2() -> dict[str, Any]:
        preflight = prerequisites["preflight"]["checks"]
        passed = preflight["PF2"]["status"] == "PASS" and preflight["PF7"]["status"] == "PASS"
        return {
            "status": "PASS" if passed else "FAIL",
            "failure_disposition": "AMBIGUOUS_CUES_UNRESOLVED",
            "selected_digest": prerequisites["selected_digest"],
            "pf2_status": preflight["PF2"]["status"],
            "pf7_status": preflight["PF7"]["status"],
        }

    def g3() -> dict[str, Any]:
        domains_pass = all(
            count >= 2 for count in resolver_summary["per_domain_facts_available"].values()
        )
        passed = resolver_summary["facts_available"] >= 9 and domains_pass
        return {
            "status": "PASS" if passed else "FAIL",
            "failure_disposition": "LOOKUP_BINDING_INSUFFICIENT",
            "required_total": 9,
            "required_per_domain": 2,
            "observed": resolver_summary,
        }

    def g4() -> dict[str, Any]:
        total_gain = resolver_summary["facts_available"] - cosine_summary["facts_available"]
        no_domain_loss = all(
            resolver_summary["per_domain_facts_available"][domain]
            >= cosine_summary["per_domain_facts_available"][domain]
            for domain in resolver_summary["per_domain_facts_available"]
        )
        passed = total_gain >= 2 and no_domain_loss
        return {
            "status": "PASS" if passed else "FAIL",
            "failure_disposition": "NO_BINDING_GAIN",
            "required_gain": 2,
            "observed_gain": total_gain,
            "no_domain_loss": no_domain_loss,
            "resolver": resolver_summary,
            "direct_cosine_top8": cosine_summary,
        }

    def g5() -> dict[str, Any]:
        bounded = all(
            len(row["emitted_indices"]) == 8
            and len(set(row["emitted_indices"])) == 8
            for row in selected_rows.values()
        )
        return {
            "status": "PASS" if bounded else "FAIL",
            "failure_disposition": "OUTPUT_BOUND_FAILED",
            "query_count": len(selected_rows),
            "all_queries_eight_unique": bounded,
            "label_dependent_retries": 0,
        }

    gates = execute_ordered_gates(
        [("G1", g1), ("G2", g2), ("G3", g3), ("G4", g4), ("G5", g5)]
    )
    failed_gate = next(
        (
            name
            for name in GATE_ORDER
            if isinstance(gates[name], dict) and gates[name]["status"] == "FAIL"
        ),
        None,
    )
    if failed_gate is None:
        disposition = "AMBIGUOUS_CUE_RESOLUTION_CANDIDATE_CHARACTERIZED"
        stress_results = []
        for query in key["queries"]:
            if query["query_class"] == "lookup":
                continue
            selected = selected_rows[query["query_id"]]
            stress_results.append(
                {
                    "query_id": query["query_id"],
                    "query_class": query["query_class"],
                    "domains": list(query["domains"]),
                    "required_fact_ids": list(query["required_fact_ids"]),
                    "direct_cosine_top8": evaluate_identity_list(
                        selected["semantic_order"][:8], query, key["facts"], episodes
                    ),
                    "ps003_resolver": evaluate_identity_list(
                        selected["emitted_indices"], query, key["facts"], episodes
                    ),
                }
            )
        stress_status = "COMPLETE_NON_GATING"
    else:
        disposition = str(gates[failed_gate]["failure_disposition"])
        stress_results = []
        stress_status = f"NOT_REACHED_AFTER_{failed_gate}"

    return {
        "study": "PS-003",
        "stage": "ordered offline relevance measurement",
        "status": "COMPLETE",
        "outcome_ceiling": "CHARACTERIZED",
        "preflight_commit": PREFLIGHT_COMMIT,
        "preflight_sha256": prerequisites["preflight_sha256"],
        "selected_configuration": {"probe_count": 5, "swap_count": 4},
        "lookup_results": lookup_results,
        "lookup_summaries": {
            "direct_cosine_top8": cosine_summary,
            "ps002_strongest": ps002_summary,
            "ps003_resolver": resolver_summary,
        },
        "gates": gates,
        "gate_order": list(GATE_ORDER),
        "failed_gate": failed_gate,
        "disposition": disposition,
        "stress_status": stress_status,
        "stress_results": stress_results,
        "zero_embedding_requests": 0,
        "zero_model_generation_calls": 0,
        "not_authorized": [
            "answer_generation",
            "scoring",
            "35-turn ablation",
            "120-turn live run",
            "promotion",
            "adoption",
        ],
    }


def write_measurement(output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite PS-003 measurement: {output_dir}")
    if _git("status", "--porcelain"):
        raise RuntimeError("PS-003 measurement requires a clean committed worktree")
    if _git("branch", "--show-current") != "study/ps-003-ambiguous-cue-resolution":
        raise RuntimeError("PS-003 measurement is on the wrong branch")
    result = build_measurement()
    output_dir.mkdir(parents=True)
    result_path = output_dir / "measurement.json"
    result_path.write_bytes(canonical_json_bytes(result) + b"\n")
    manifest = {
        "status": "SEALED",
        "files": [
            {
                "path": "measurement.json",
                "bytes": result_path.stat().st_size,
                "sha256": sha256_file(result_path),
            }
        ],
    }
    (output_dir / "artifact_manifest.json").write_bytes(
        canonical_json_bytes(manifest) + b"\n"
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run PS-003 ordered measurement")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    write_measurement(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

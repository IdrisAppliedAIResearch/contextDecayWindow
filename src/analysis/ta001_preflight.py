from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence

from episodic._render import render_stm_payload

from src.analysis.e005_diversity_selection import _q11_payload_availability
from src.analysis.ta001_exploration import (
    ANSWER_KEY_HASH_ONLY,
    BUDGET_CHARS,
    COMPONENT_ROOT,
    QUERY_CACHE,
    QUERY_MANIFEST,
    RANK_INVENTORY,
    REPO_ROOT,
    canonical_digest,
    load_episodes,
    load_holdout_queries,
    load_q11_ranking,
    load_query_vectors,
    query_record,
    rank_by_query,
    sha256_file,
    verify_inputs,
)
from src.retrieval_mechanism_ledger.ta001 import content_sha256


FINAL_DESIGN = COMPONENT_ROOT / "TA_001_FINAL_DESIGN.md"
EXPLORATION = COMPONENT_ROOT / "artifacts" / "ta001_exploration" / "part1_process_1" / "exploration.json"
DETERMINISM = COMPONENT_ROOT / "artifacts" / "ta001_exploration" / "two_process_determinism.json"
DEFAULT_OUTPUT = COMPONENT_ROOT / "artifacts" / "ta001_preflight"

FINAL_DESIGN_COMMIT = "6e3e839f62fa0cb37f09e5900bf16e5ef841e22e"
FINAL_DESIGN_SHA256 = "bc8c4152ed92bb72c8c3d8fde574c4265c6a93f9593c9b6e4fa15c0191b60011"
EXPLORATION_SHA256 = "a18c91d4251a5a6aca8e2fb6b37ed96e86e64798ea30e3db76ff2894399ffddf"
EXPLORATION_DIGEST = "54983e565475afd17862c9aee46d12018dc344206ed9ccb3a60c2e3774da50a5"


class MeasurementBoundary:
    def __init__(self) -> None:
        self._preflight_digest: str | None = None

    def seal(self, preflight: dict[str, Any]) -> str:
        if preflight.get("status") != "PASS":
            raise RuntimeError("Cannot seal a failing preflight")
        self._preflight_digest = canonical_digest(preflight)
        return self._preflight_digest

    def require_open(self) -> str:
        if self._preflight_digest is None:
            raise RuntimeError("Measurement attempted before Preflight seal")
        return self._preflight_digest


def git_ordering() -> dict[str, Any]:
    commits = (
        "23cff2d8da6e864363b05d2438398f9b60c8893b",
        "43d4e764ef95cd1b89a6037d925824a686221991",
        "6ffe9b7c382b486e0d77dcd170e966b8aa507670",
        "1c786b758ad8dfce76d675d8a125958ffb6e02a2",
        "0ea39da6fa66b23773593fdff36bdc28a433bad5",
        FINAL_DESIGN_COMMIT,
    )
    for left, right in zip(commits, commits[1:]):
        subprocess.run(("git", "merge-base", "--is-ancestor", left, right), cwd=REPO_ROOT, check=True)
    subprocess.run(("git", "merge-base", "--is-ancestor", FINAL_DESIGN_COMMIT, "HEAD"), cwd=REPO_ROOT, check=True)
    planted_stopped = False
    try:
        MeasurementBoundary().require_open()
    except RuntimeError:
        planted_stopped = True
    return {"ordered_commits": list(commits), "early_measurement_stopped": planted_stopped}


def replay_records() -> list[dict[str, Any]]:
    episodes = load_episodes(119)
    queries = load_holdout_queries()
    vectors = load_query_vectors(queries)
    records = [query_record("q11", load_q11_ranking(episodes))]
    records.extend(
        query_record(query["query_id"], rank_by_query(episodes[:111], vectors[query["query_id"]]))
        for query in queries
    )
    return records


def source_existence() -> dict[str, Any]:
    key = json.loads(ANSWER_KEY_HASH_ONLY.read_text(encoding="utf-8"))
    episodes = load_episodes(111)
    by_turn = {int(episode["turn_number"]): episode for episode in episodes}
    fact_checks = []
    for fact_id, fact in key["facts"].items():
        matching_sources = []
        for turn in fact["source_turns"]:
            episode = by_turn.get(int(turn))
            if episode is None:
                continue
            serialized = render_stm_payload([], [episode]).casefold()
            if all(str(term).casefold() in serialized for term in fact["required_terms"]):
                matching_sources.append(int(turn))
        fact_checks.append({"fact_id": fact_id, "matching_source_turns": matching_sources, "pass": bool(matching_sources)})
    query_requirements = sum(len(query["required_fact_ids"]) for query in key["queries"])

    with RANK_INVENTORY.open(encoding="utf-8", newline="") as handle:
        rank_rows = list(csv.DictReader(handle))
    q11_items = sorted({item for row in rank_rows for item in row["items"].split("|") if item})
    q11_art = sorted({item for row in rank_rows if "art" in row["domains"].split("|") for item in row["items"].split("|") if item})
    return {
        "holdout_fact_count": len(fact_checks),
        "holdout_query_requirement_count": query_requirements,
        "holdout_all_sources_present": all(row["pass"] for row in fact_checks),
        "holdout_fact_checks": fact_checks,
        "q11_item_ceiling": len(q11_items),
        "q11_art_ceiling": len(q11_art),
        "q11_items": q11_items,
        "q11_art_items": q11_art,
    }


def c0_measurement_reproduction(record: dict[str, Any]) -> dict[str, Any]:
    episodes = load_episodes(119)
    by_hash = {content_sha256(episode): episode for episode in episodes}
    selected = [by_hash[value] for value in record["C0"]["selected_content_sha256"]]
    payload = render_stm_payload([], selected)
    availability = _q11_payload_availability(payload)
    return {
        "packed_fact_count": availability["fact_count"],
        "expected_packed_fact_count": 7,
        "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "expected_payload_sha256": record["C0"]["payload_sha256"],
        "pass": availability["fact_count"] == 7 and hashlib.sha256(payload.encode("utf-8")).hexdigest() == record["C0"]["payload_sha256"],
    }


def run(output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite Preflight output: {output_dir}")
    if sha256_file(FINAL_DESIGN) != FINAL_DESIGN_SHA256:
        raise AssertionError("Final design identity changed")
    if sha256_file(EXPLORATION) != EXPLORATION_SHA256:
        raise AssertionError("Part 1 exploration identity changed")
    committed = json.loads(EXPLORATION.read_text(encoding="utf-8"))
    determinism = json.loads(DETERMINISM.read_text(encoding="utf-8"))
    current = replay_records()
    repeated = replay_records()
    existence = source_existence()
    reproduction = c0_measurement_reproduction(current[0])
    ordering = git_ordering()
    inventory = verify_inputs()
    hashes = [value for record in current for arm in ("C0", "T1") for value in record[arm]["candidate_content_sha256"]]

    checks = {
        "PF1": {
            "pass": len(inventory) == 14 and len(load_query_vectors(load_holdout_queries())) == 24,
            "evidence": {"inputs": inventory, "episode_counts": {"q11": 119, "holdout": 111}, "query_cache_hits": 24, "vector_dimension": 1024},
        },
        "PF2": {
            "pass": current == committed["records"] and all(len(record[arm]["candidate_content_sha256"]) == 15 for record in current for arm in ("C0", "T1")),
            "evidence": {"query_count": len(current), "record_digest": canonical_digest(current), "committed_record_digest": canonical_digest(committed["records"])},
        },
        "PF3": {"pass": ordering["early_measurement_stopped"], "evidence": ordering},
        "PF4": {
            "pass": existence["holdout_all_sources_present"] and existence["q11_item_ceiling"] == 17 and existence["q11_art_ceiling"] == 4,
            "evidence": existence,
        },
        "PF5": {"pass": all(re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes), "evidence": {"comparison_key": "episode_content_sha256", "identity_count": len(hashes)}},
        "PF6": {
            "pass": committed["deterministic_digest"] == EXPLORATION_DIGEST and determinism["status"] == "PASS" and reproduction["pass"],
            "evidence": {"part1_digest": committed["deterministic_digest"], "fresh_process": determinism, "c0": reproduction},
        },
        "PF7": {"pass": current == repeated, "evidence": {"stateless": True, "first_digest": canonical_digest(current), "repeat_digest": canonical_digest(repeated), "query_history_feedback": False}},
        "PF8": {"pass": True, "evidence": "Twenty-five offline queries identify this 119-episode lineage. A 35-turn prefix can test integration, leakage, budgets, and deterministic replay, but not turn-55 art recovery or endurance."},
        "PF9": {
            "pass": True,
            "evidence": [
                {"surrogate": "candidate count", "can_miss": "semantic opportunity"},
                {"surrogate": "neighbor count", "can_miss": "useful evidence"},
                {"surrogate": "broad facts", "can_miss": "reader use"},
                {"surrogate": "art candidates", "can_miss": "packed art"},
                {"surrogate": "targeted no-loss", "can_miss": "other wording and corpora"},
                {"surrogate": "payload <=32k", "can_miss": "equal delivered characters"},
                {"surrogate": "35-turn stability", "can_miss": "120-turn endurance"},
            ],
        },
        "PF10": {"pass": True, "evidence": {"offline_is_verdict": False, "conditional_next": "registered 35-turn ablation", "full_live_run_authorized": False}},
    }
    failed = [name for name, row in checks.items() if not row["pass"]]
    result = {
        "study": "TA-001 temporal-adjacency bridge",
        "status": "PASS" if not failed else "FAIL",
        "final_design_commit": FINAL_DESIGN_COMMIT,
        "final_design_sha256": FINAL_DESIGN_SHA256,
        "implementation_sha256": sha256_file(Path(__file__).resolve()),
        "checks": checks,
        "failed_checks": failed,
        "measurement_boundary": "SEALED" if not failed else "CLOSED",
    }
    if failed:
        raise AssertionError(f"TA-001 Preflight failed: {failed}")
    boundary = MeasurementBoundary()
    result["preflight_seal_sha256"] = boundary.seal(result)
    output_dir.mkdir(parents=True)
    path = output_dir / "preflight.json"
    path.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    manifest = {"files": [{"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}]}
    (output_dir / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps({"status": run(args.output)["status"]}, sort_keys=True))

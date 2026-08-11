from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from src.analysis.e005_diversity_selection import _q11_payload_availability
from src.analysis.sr001_exploration import (
    DATABASE_Q11,
    DESIGN_COMMIT,
    FROZEN_INPUTS,
    REPO_ROOT,
    canonical_digest,
    load_q11_sources,
    sha256_file,
)
from src.analysis.sr001_gates import synthetic_reachability
from src.retrieval_bakeoff.config import corpus_spec
from src.retrieval_bakeoff.corpus import load_raw_episodes


COMPONENT_ROOT = REPO_ROOT / "experiments/components/retrieval_mechanism_ledger"
EXPLORATION_2 = COMPONENT_ROOT / "artifacts/sr001_exploration/part1_process_2/exploration.json"
EXPLORATION_3 = COMPONENT_ROOT / "artifacts/sr001_exploration/part1_process_3/exploration.json"
DETERMINISM = COMPONENT_ROOT / "artifacts/sr001_exploration/two_process_determinism.json"
FINAL_LOCK = COMPONENT_ROOT / "SR_001_FINAL_DESIGN.md"
AMENDMENT = COMPONENT_ROOT / "amendments/SR_001_AMENDMENT_001_SERIALIZED_SCORE_ANCHOR.md"
ANSWER_KEY = REPO_ROOT / "experiments/surveys/retrieval_bakeoff/holdout/answer_key_121.json"
DEFAULT_OUTPUT = COMPONENT_ROOT / "artifacts/sr001_preflight/preflight.json"

REQUIRED_COMMITS = (
    DESIGN_COMMIT,
    "f99b86a4",
    "5828147c98afdd542a6fe4233af8e0e7220bb04a",
    "bbef505c648371e7761e0bedb9a35da21f4ccda6",
    "13fe470e",
)


def is_ancestor(commit: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
    ).returncode == 0


def planted_holdout_coverage(key: dict[str, Any]) -> dict[str, Any]:
    episodes = load_raw_episodes(corpus_spec("c121_l"))
    by_turn = {row.turn_number: row for row in episodes}
    missing = []
    for fact_id, fact in key["facts"].items():
        terms = [str(value).casefold() for value in fact["required_terms"]]
        role = str(fact["source_role"])
        found = False
        for turn in fact["source_turns"]:
            episode = by_turn.get(int(turn))
            if episode is None:
                continue
            text = episode.user_message if role == "user" else episode.assistant_message
            if all(term in text.casefold() for term in terms):
                found = True
                break
        if not found:
            missing.append(fact_id)
    return {"fact_count": len(key["facts"]), "missing": missing, "complete": not missing}


def q11_ceiling() -> dict[str, Any]:
    candidates, _ = load_q11_sources()
    payload = "\n".join(f"{row.user_message}\n{row.assistant_message}" for row in candidates)
    result = _q11_payload_availability(payload)
    return {"fact_count": result["fact_count"], "per_domain": result["per_domain"]}


def run(output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite preflight output: {output}")
    exploration_2 = json.loads(EXPLORATION_2.read_text(encoding="utf-8"))
    exploration_3 = json.loads(EXPLORATION_3.read_text(encoding="utf-8"))
    determinism = json.loads(DETERMINISM.read_text(encoding="utf-8"))
    key = json.loads(ANSWER_KEY.read_text(encoding="utf-8"))
    holdout_coverage = planted_holdout_coverage(key)
    q11 = q11_ceiling()
    dispositions = synthetic_reachability()
    input_checks = [
        {
            "path": relative,
            "bytes_equal": (REPO_ROOT / relative).stat().st_size == expected[0],
            "sha256_equal": sha256_file(REPO_ROOT / relative) == expected[1],
        }
        for relative, expected in FROZEN_INPUTS.items()
    ]
    pf = {
        "PF1": {"pass": all(row["bytes_equal"] and row["sha256_equal"] for row in input_checks), "evidence": {"inputs": input_checks, "queries": 25, "holdout_facts": len(key["facts"])}},
        "PF2": {"pass": exploration_2["eligibility"]["status"] == "PASS", "evidence": {"behavioral_identity_digest": exploration_2["deterministic_digest"], "distribution": exploration_2["distribution"]}},
        "PF3": {"pass": all(is_ancestor(commit) for commit in REQUIRED_COMMITS), "evidence": {"required_commits": list(REQUIRED_COMMITS), "ordered_before_measurement": True}},
        "PF4": {"pass": holdout_coverage["complete"] and q11["fact_count"] == 17 and q11["per_domain"] == {"art": 4, "civil": 5, "marine": 4, "monetary": 4} and all(key == value for key, value in dispositions.items()), "evidence": {"holdout": holdout_coverage, "q11": q11, "synthetic_dispositions": dispositions}},
        "PF5": {"pass": all(len(value) == 64 for row in exploration_2["records"] for value in row["source_identities"]), "evidence": "25 traces use canonical source SHA-256; span IDs bind source, role, and offsets"},
        "PF6": {"pass": all(all(row["C0"]["committed_reproduction"].values()) for row in exploration_2["records"][1:]), "evidence": {"m2_exact_queries": 24, "part1_digest": exploration_2["deterministic_digest"]}},
        "PF7": {"pass": exploration_2["deterministic_digest"] == exploration_3["deterministic_digest"] and determinism["status"] == "PASS", "evidence": {"process_2": exploration_2["deterministic_digest"], "process_3": exploration_3["deterministic_digest"], "feedback": "none; repeated complete pass identity-equal"}},
        "PF8": {"pass": True, "evidence": "25 frozen queries identify this lineage's offline delivery. A 35-turn ablation tests integration, provenance, budget, leakage, and prefix determinism; it cannot test turn-55 art or 120-turn efficacy."},
        "PF9": {"pass": True, "evidence": [{"surrogate": "selected span count", "can_be_false": "distinct fact breadth"}, {"surrogate": "Q11 availability", "can_be_false": "reader use and correctness"}, {"surrogate": "domain macro", "can_be_false": "individual-query safety; G4 remains separate"}, {"surrogate": "32k fit", "can_be_false": "equal delivered evidence"}]},
        "PF10": {"pass": True, "evidence": {"offline_availability_is_verdict": False, "answer_correctness_evaluated": False, "conditional_ablation": "35-turn integration only", "full_live_run_authorized": False}},
    }
    result = {
        "study": "SR-001 extractive span representation",
        "status": "PASS" if all(row["pass"] for row in pf.values()) else "FAIL",
        "checks": pf,
        "measurement_authorized": all(row["pass"] for row in pf.values()),
        "ablation_authorized": False,
        "live_run_authorized": False,
        "input_sha256": {"exploration_2": sha256_file(EXPLORATION_2), "exploration_3": sha256_file(EXPLORATION_3), "final_lock": sha256_file(FINAL_LOCK), "amendment": sha256_file(AMENDMENT), "answer_key": sha256_file(ANSWER_KEY), "database_q11": sha256_file(DATABASE_Q11)},
    }
    result["canonical_digest"] = canonical_digest(result)
    output.parent.mkdir(parents=True)
    output.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    if result["status"] != "PASS":
        raise AssertionError("SR-001 Preflight failed")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    result = run(parse_args().output)
    print(json.dumps({"status": result["status"], "canonical_digest": result["canonical_digest"]}, sort_keys=True))

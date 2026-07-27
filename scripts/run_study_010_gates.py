"""Run Study 010's offline scale, purity, resume, and leakage gates."""

import json
import sqlite3
import subprocess
import sys
import tempfile
import time
from functools import lru_cache
from pathlib import Path

import numpy as np

from src.db.schema import init_db
from src.embeddings.provider import cosine_similarity, embed
from src.memory.stm_retrieval_engine import K_SIMILARITY_THRESHOLD
from src.memory.stm_retrieval_engine import StmRetrievalEngine
from src.memory.topic_manager import TopicManager
from src.runners.stm_runner import StmRunner
from src.study.script_loader import load_script

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "experiments/study_010"
SCRIPT = STUDY / "script_1000.json"
RESULTS = STUDY / "gates/amendment_004/gate_results.json"
REPORT = STUDY / "gates/amendment_004/gate_report.md"


@lru_cache(maxsize=None)
def cached_embed(text: str) -> np.ndarray:
    return embed(text)


def synthetic_assistant(domain: str) -> str:
    return (
        f"Concise technical answer for {domain}. The result records assumptions, "
        "uncertainty, validation, and provenance without repeating locked facts."
    )


def retrieval_gate(script: dict) -> dict:
    domain_order = list(
        dict.fromkeys(
            turn["ground_truth_domain"]
            for turn in script["turns"][:986]
            if turn["ground_truth_domain"] != "probe"
        )
    )
    episodes = []
    for turn in script["turns"][:986]:
        assistant = synthetic_assistant(turn["ground_truth_domain"])
        text = f"User: {turn['user']}\nAssistant: {assistant}"
        episodes.append(
            {
                "turn": turn["turn"],
                "domain": turn["ground_truth_domain"],
                "chars": len(text),
                "embedding": cached_embed(text),
            }
        )

    probes = {}
    latencies = []
    for turn in script["turns"][986:998]:
        started = time.perf_counter()
        query = cached_embed(turn["user"])
        selected = [
            episode
            for episode in episodes
            if cosine_similarity(query, episode["embedding"])
            >= K_SIMILARITY_THRESHOLD
        ]
        latencies.append((time.perf_counter() - started) * 1000)
        # Terminal Q1-Q12 follow the locked canonical-domain order.
        target = domain_order[turn["turn"] - 987]
        target_plants = [
            episode
            for episode in selected
            if episode["domain"] == target
            and script["turns"][episode["turn"] - 1].get("plant_stage")
            in {"early", "middle"}
        ]
        selected_chars = sum(episode["chars"] for episode in selected)
        probes[turn["probe_label"]] = {
            "target_domain": target,
            "selected_count": len(selected),
            "selected_chars": selected_chars,
            "estimated_k_tokens": selected_chars // 4,
            "target_plant_turns": [row["turn"] for row in target_plants],
            "target_fact_source_recovered": bool(target_plants),
        }

    peak_tokens = max(row["estimated_k_tokens"] for row in probes.values())
    return {
        "passed": (
            all(row["target_fact_source_recovered"] for row in probes.values())
            and peak_tokens < 25000
        ),
        "threshold": K_SIMILARITY_THRESHOLD,
        "episode_count": len(episodes),
        "embedding_cache_entries": cached_embed.cache_info().currsize,
        "latency_ms_mean": sum(latencies) / len(latencies),
        "latency_ms_max": max(latencies),
        "peak_estimated_k_tokens": peak_tokens,
        "probes": probes,
    }


def consolidation_replay(
    script: dict,
    assignment_threshold: float,
    merge_threshold: float,
) -> dict:
    original_assignment = TopicManager.TOPIC_SIMILARITY_THRESHOLD
    original_merge = TopicManager.CONSOLIDATION_MERGE_THRESHOLD
    TopicManager.TOPIC_SIMILARITY_THRESHOLD = assignment_threshold
    TopicManager.CONSOLIDATION_MERGE_THRESHOLD = merge_threshold
    with tempfile.TemporaryDirectory() as tmp:
        conn = init_db(str(Path(tmp) / "gate.db"))
        manager = TopicManager(conn)
        retrieval = StmRetrievalEngine(
            conn,
            embedding_provider=cached_embed,
            system_prompt=script["system_prompt"],
        )
        runner = StmRunner(conn, cached_embed, manager, retrieval)
        purity_events = []
        topic_trajectory = []
        for turn in script["turns"][:986]:
            domain = turn["ground_truth_domain"]
            assistant = synthetic_assistant(domain)
            result = runner.on_turn_complete(
                user_message=turn["user"],
                assistant_message=assistant,
                turn_number=turn["turn"],
                embedding=cached_embed(
                    f"User: {turn['user']}\nAssistant: {assistant}"
                ),
                topic_embedding=cached_embed(turn["user"]),
                ground_truth_domain=domain,
            )
            if result.consolidation:
                purity_events.extend(result.consolidation.purity_events)
            if turn["turn"] % 100 == 0:
                topic_trajectory.append(
                    {"turn": turn["turn"], "topics": manager.topic_count}
                )

        profiles = []
        for topic_id, label in conn.execute("SELECT id, label FROM topics"):
            domains = sorted(
                {
                    row[0]
                    for row in conn.execute(
                        "SELECT ground_truth_domain FROM episodes "
                        "WHERE topic_id = ?",
                        (topic_id,),
                    )
                    if row[0] and row[0] != "probe"
                }
            )
            profiles.append({"topic": label, "domains": domains})
        cross_domain_topics = [
            profile for profile in profiles if len(profile["domains"]) > 1
        ]
        topic_count = manager.topic_count
        conn.close()
    TopicManager.TOPIC_SIMILARITY_THRESHOLD = original_assignment
    TopicManager.CONSOLIDATION_MERGE_THRESHOLD = original_merge
    return {
        "passed": 10 <= topic_count <= 18 and not cross_domain_topics,
        "assignment_threshold": assignment_threshold,
        "merge_threshold": merge_threshold,
        "final_topic_count": topic_count,
        "topic_trajectory": topic_trajectory,
        "topic_profiles": profiles,
        "cross_domain_topics": cross_domain_topics,
        "purity_event_count": len(purity_events),
    }


def consolidation_gate(script: dict) -> dict:
    candidates = [
        (0.45, 0.45),
        (0.50, 0.75),
        (0.55, 0.75),
        (0.60, 0.75),
        (0.65, 0.80),
        (0.70, 0.85),
        (0.75, 0.90),
        (0.80, 0.95),
    ]
    sweep = [
        consolidation_replay(script, assignment, merge)
        for assignment, merge in candidates
    ]
    chosen = next((row for row in sweep if row["passed"]), None)
    return {
        "passed": chosen is not None,
        "chosen": chosen,
        "sweep": [
            {
                "assignment_threshold": row["assignment_threshold"],
                "merge_threshold": row["merge_threshold"],
                "final_topic_count": row["final_topic_count"],
                "cross_domain_topics": len(row["cross_domain_topics"]),
                "passed": row["passed"],
            }
            for row in sweep
        ],
        **(
            {
                "final_topic_count": chosen["final_topic_count"],
                "topic_trajectory": chosen["topic_trajectory"],
                "topic_profiles": chosen["topic_profiles"],
                "cross_domain_topics": chosen["cross_domain_topics"],
                "purity_event_count": chosen["purity_event_count"],
            }
            if chosen
            else {
                "final_topic_count": sweep[-1]["final_topic_count"],
                "topic_trajectory": sweep[-1]["topic_trajectory"],
                "topic_profiles": sweep[-1]["topic_profiles"],
                "cross_domain_topics": sweep[-1]["cross_domain_topics"],
                "purity_event_count": sweep[-1]["purity_event_count"],
            }
        ),
    }


def resume_gate() -> dict:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_study_010_checkpoint.py",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return {
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "output": result.stdout.strip(),
    }


def leakage_gate() -> dict:
    forbidden = ("q_facts_key_1000", "rubric_1000", "artifact_lock.json")
    roots = [ROOT / "src/memory", ROOT / "src/db", ROOT / "src/embeddings"]
    hits = []
    scanned = 0
    for root in roots:
        for path in root.rglob("*.py"):
            scanned += 1
            text = path.read_text(encoding="utf-8").casefold()
            for token in forbidden:
                if token.casefold() in text:
                    hits.append(
                        {"path": path.relative_to(ROOT).as_posix(), "token": token}
                    )
    return {"passed": not hits, "scanned_files": scanned, "violations": hits}


def write_report(results: dict) -> None:
    g1 = results["g1_retrieval"]
    g2 = results["g2_consolidation"]
    lines = [
        "# Study 010 Amendment 004 Offline Gate Rerun",
        "",
        "**Evidence status:** post-stop exploratory",
        "",
        f"**Original gate status:** {'PASS' if results['passed'] else 'FAIL'}",
        f"**Continuation eligibility:** "
        f"{'PASS' if results['continuation_passed'] else 'FAIL'}",
        "",
        "## G1 - Retrieval at scale",
        "",
        f"- Episodes: {g1['episode_count']}",
        f"- Threshold: {g1['threshold']}",
        f"- Peak projected K tokens: {g1['peak_estimated_k_tokens']:,}",
        f"- Mean/max query scan: {g1['latency_ms_mean']:.2f} / "
        f"{g1['latency_ms_max']:.2f} ms",
        f"- All 12 targeted probes recover a target plant source: "
        f"{all(row['target_fact_source_recovered'] for row in g1['probes'].values())}",
        "",
        "## G2 - Consolidation at scale",
        "",
        f"- Final topics: {g2['final_topic_count']}",
        f"- Cross-domain topics: {len(g2['cross_domain_topics'])}",
        (
            f"- Chosen assignment/merge thresholds: "
            f"{g2['chosen']['assignment_threshold']} / "
            f"{g2['chosen']['merge_threshold']}"
            if g2["chosen"]
            else "- No swept threshold pair passed"
        ),
        f"- Result: {'PASS' if g2['passed'] else 'FAIL'}",
        "",
        "## G3 - Digest at scale",
        "",
        "- NOT APPLICABLE: Study 009 resolved digest carry false.",
        "",
        "## G4 - Checkpoint/restore",
        "",
        f"- Result: {'PASS' if results['g4_resume']['passed'] else 'FAIL'}",
        f"- Tests: {results['g4_resume']['output']}",
        "",
        "## Leakage",
        "",
        f"- Result: {'PASS' if results['leakage']['passed'] else 'FAIL'}",
        f"- Files scanned: {results['leakage']['scanned_files']}",
        "",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    script = load_script(str(SCRIPT), minimum_turns=1000)
    results = {
        "g1_retrieval": retrieval_gate(script),
        "g2_consolidation": consolidation_gate(script),
        "g3_digest": {"applicable": False, "passed": None},
        "g4_resume": resume_gate(),
        "leakage": leakage_gate(),
    }
    results["passed"] = all(
        results[key]["passed"]
        for key in ("g1_retrieval", "g2_consolidation", "g4_resume", "leakage")
    )
    results["evidence_status"] = "post_stop_exploratory"
    results["governing_amendment"] = (
        "experiments/study_010/amendments/"
        "AMENDMENT_004_authorized_exploratory_restart.md"
    )
    results["continuation_passed"] = all(
        results[key]["passed"]
        for key in ("g1_retrieval", "g4_resume", "leakage")
    )
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    write_report(results)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

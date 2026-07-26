"""Run Study 009's three registered offline gates."""

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np

from src.analysis.study_007_replay import PROBE_TURNS, hash_tree, score
from src.analysis.study_008_replay import (
    actual_probe_block,
    arm_configs,
    load_candidates,
    load_fact_rows,
    match_facts,
    replay_arm_probe,
    scored_probes,
)
from src.embeddings.provider import embed
from src.memory.topic_digest import TopicDigest


ROOT = Path(__file__).resolve().parents[1]
STUDY_DIR = ROOT / "experiments/study_009"
RUN_DIR = ROOT / "experiments/study_007/runs/study_007_full_001/condition_c"
DB_PATH = RUN_DIR / "study.db"
FACT_KEY = STUDY_DIR / "q_facts_key.md"
RESULTS_PATH = STUDY_DIR / "gates/gate_results.json"
REPORT_PATH = STUDY_DIR / "gates/gate_report.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_gate() -> dict:
    before = sha256(DB_PATH)
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    preserved = load_candidates()
    cache = {
        row["span_text"]: np.frombuffer(row["embedding"], dtype=np.float32)
        for row in preserved
        if row.get("span_text") and row.get("embedding") is not None
    }
    fallback_count = 0

    def cached_embed(text: str):
        nonlocal fallback_count
        if text not in cache:
            cache[text] = embed(text)
            fallback_count += 1
        return cache[text]

    try:
        fact_rows = load_fact_rows(FACT_KEY)
        settings = []
        chosen = None
        builder = TopicDigest(
            conn,
            embedding_provider=cached_embed,
            spans_per_topic=50,
            budget=100000,
        )
        full = builder.rebuild(111, through_turn=111)
        all_by_topic = {
            topic_id: [
                span
                for span in full.spans
                if span.topic_id == topic_id
            ]
            for topic_id in {span.topic_id for span in full.spans}
        }
        for d in range(1, 51):

            by_topic = {
                topic_id: spans[:d]
                for topic_id, spans in all_by_topic.items()
            }

            def evaluate_budget(budget: int):
                builder.budget = budget
                try:
                    selected = builder._fit_budget(by_topic)
                except ValueError:
                    return None
                text = __import__(
                    "src.memory.topic_digest",
                    fromlist=["render_topic_digest"],
                ).render_topic_digest(selected)
                matched = match_facts(text, fact_rows)
                domains = sorted(
                    domain for domain, facts in matched.items() if facts
                )
                return {
                    "d": d,
                    "budget": budget,
                    "serialized_chars": len(text),
                    "span_count": len(selected),
                    "domains": domains,
                    "matched_facts": matched,
                    "spans": [
                        builder._span_dict(span) for span in selected
                    ],
                }

            upper_row = evaluate_budget(50000)
            if upper_row is None or len(upper_row["domains"]) < 4:
                continue
            low = len("<topic_digest/>")
            high = 50000
            while low < high:
                middle = (low + high) // 2
                row = evaluate_budget(middle)
                if row is not None and len(row["domains"]) == 4:
                    high = middle
                else:
                    low = middle + 1
            row = evaluate_budget(low)
            settings.append(row)
            chosen = row
            break
            if chosen is not None:
                break
        registered_builder = TopicDigest(
            conn,
            embedding_provider=cached_embed,
            spans_per_topic=2,
            budget=2500,
        )
        registered_frame = __import__(
            "src.memory.topic_digest",
            fromlist=["DigestFrame"],
        ).DigestFrame(
            spans=registered_builder._fit_budget({
                topic_id: spans[:2]
                for topic_id, spans in all_by_topic.items()
            }),
            budget=2500,
            built_at_turn=111,
        )
        registered_builder.frame = registered_frame
        registered_render = registered_builder.render()
        registered_matches = match_facts(registered_render.text, fact_rows)
        registered_domains = sorted(
            domain
            for domain, facts in registered_matches.items()
            if facts
        )
    finally:
        conn.close()
    after = sha256(DB_PATH)
    return {
        "passed": chosen is not None,
        "read_only_store_unchanged": before == after,
        "store_sha256": before,
        "plant_key_sha256": sha256(FACT_KEY),
        "smallest_sufficient": chosen,
        "registered": {
            "d": 2,
            "budget": 2500,
            "serialized_chars": registered_render.chars,
            "span_count": registered_render.span_count,
            "domains": registered_domains,
            "matched_facts": registered_matches,
            "passed": len(registered_domains) == 4,
            "spans": [
                registered_builder._span_dict(span)
                for span in registered_frame.spans
            ],
        },
        "embedding_cache_entries": len(cache),
        "live_embedding_fallbacks": fallback_count,
    }


def ltm_fidelity_gate() -> dict:
    candidates = load_candidates()
    fact_rows = load_fact_rows(FACT_KEY)
    scored = scored_probes(candidates)
    config = arm_configs(2)["A"]
    probes = {}
    for turn in PROBE_TURNS:
        predicted = replay_arm_probe(
            turn,
            scored[turn],
            config=config,
            fact_rows=fact_rows,
        ).rendered_block
        actual = actual_probe_block(turn)
        probes[str(turn)] = {
            "equal": predicted == actual,
            "predicted_sha256": hashlib.sha256(
                predicted.encode("utf-8")
            ).hexdigest(),
            "actual_sha256": hashlib.sha256(
                actual.encode("utf-8")
            ).hexdigest(),
        }
    return {
        "passed": all(row["equal"] for row in probes.values()),
        "probes": probes,
    }


def stm_gate() -> dict:
    code = (
        "import sys; import src.study.study_009_runner; "
        "print('\\n'.join(sorted(name for name in sys.modules "
        "if name.startswith('src.'))))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    forbidden = [
        name
        for name in result.stdout.splitlines()
        if any(token in name for token in ("ltm", "digest", "dream", "promotion"))
    ]
    tests = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_study_009_stm.py",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return {
        "passed": not forbidden and tests.returncode == 0,
        "forbidden_modules": forbidden,
        "fixture_test_exit_code": tests.returncode,
        "fixture_test_output": tests.stdout.strip(),
    }


def write_report(results: dict) -> None:
    g1 = results["g1_digest"]
    g2 = results["g2_ltm_fidelity"]
    g3 = results["g3_stm_sanity"]
    chosen = g1["smallest_sufficient"]
    lines = [
        "# Study 009 Offline Gate Report",
        "",
        (
            "**Overall:** PASS WITH PRE-REGISTERED DIGEST CONTINGENCY"
            if results["passed"] and results["digest_contingency_invoked"]
            else f"**Overall:** {'PASS' if results['passed'] else 'FAIL'}"
        ),
        "",
        "## G1 - Digest replay",
        "",
        f"- Result: {'PASS' if g1['passed'] else 'FAIL'}",
        f"- Preserved store unchanged: {g1['read_only_store_unchanged']}",
        (
            f"- Smallest sufficient: d={chosen['d']}, "
            f"B_digest={chosen['budget']} chars"
            if chosen
            else "- No sufficient setting found through d=50, B_digest=50,000"
        ),
        (
        f"- Registered d=2, B_digest=2,500: "
            f"{'PASS' if g1['registered']['passed'] else 'FAIL'} "
            f"({g1['registered']['serialized_chars']} chars)"
        ),
        (
            "- Consequence: S+D is dropped; Study 009 proceeds as the "
            "S-versus-L null test."
            if results["digest_contingency_invoked"]
            else "- Consequence: S+D remains enabled."
        ),
        "",
        "## G2 - Arm L fidelity",
        "",
        f"- Result: {'PASS' if g2['passed'] else 'FAIL'}",
        *[
            f"- Turn {turn}: {'byte-identical' if row['equal'] else 'DIFF'}"
            for turn, row in g2["probes"].items()
        ],
        "",
        "## G3 - Arm S sanity",
        "",
        f"- Result: {'PASS' if g3['passed'] else 'FAIL'}",
        f"- Forbidden imported modules: {g3['forbidden_modules']}",
        f"- Fixture tests: {g3['fixture_test_output']}",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    STUDY_DIR.joinpath("gates").mkdir(parents=True, exist_ok=True)
    before = hash_tree(RUN_DIR)
    results = {
        "g1_digest": digest_gate(),
        "g2_ltm_fidelity": ltm_fidelity_gate(),
        "g3_stm_sanity": stm_gate(),
    }
    after = hash_tree(RUN_DIR)
    results["study_007_tree_unchanged"] = before == after
    results["digest_contingency_invoked"] = not results["g1_digest"]["passed"]
    results["s_plus_digest_enabled"] = results["g1_digest"]["passed"]
    results["passed"] = (
        results["g1_digest"]["read_only_store_unchanged"]
        and results["g2_ltm_fidelity"]["passed"]
        and results["g3_stm_sanity"]["passed"]
        and results["study_007_tree_unchanged"]
    )
    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    write_report(results)
    print(json.dumps({
        "passed": results["passed"],
        "g1": results["g1_digest"]["passed"],
        "g2": results["g2_ltm_fidelity"]["passed"],
        "g3": results["g3_stm_sanity"]["passed"],
        "registered_digest": results["g1_digest"]["registered"]["passed"],
        "smallest_sufficient": results["g1_digest"]["smallest_sufficient"],
    }, indent=2))


if __name__ == "__main__":
    main()

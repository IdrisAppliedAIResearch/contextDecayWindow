"""S8-T-005: fact-aware re-derivation of Study 007's replay sweep."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.analysis.study_008_replay import (  # noqa: E402
    PLANT_KEY,
    PROBE_TURNS,
    STUDY_007_RUN,
    hash_tree,
    load_candidates,
    load_fact_rows,
    replay_episode_probe,
    scored_probes,
    sha256_file,
)


B_SWEEP = (16000, 20000, 24000, 28000, 32000, 36000, 40000, 48000, 64000)
K_SWEEP = (0, 1, 2, 3, 4)
OUT_DIR = REPO / "experiments/study_008/replay"


def main() -> int:
    before = hash_tree(STUDY_007_RUN)
    fact_rows = load_fact_rows()
    if len(fact_rows) != 14:
        raise AssertionError(f"Expected 14 locked fact rows, got {len(fact_rows)}")
    candidates = load_candidates()
    scored = scored_probes(candidates)

    frontier = []
    for b_ltm in B_SWEEP:
        for k_min in K_SWEEP:
            probes = {
                turn: replay_episode_probe(
                    turn,
                    scored[turn],
                    b_ltm=b_ltm,
                    k_min=k_min,
                    fact_rows=fact_rows,
                )
                for turn in PROBE_TURNS
            }
            frontier.append(
                {
                    "b_ltm": b_ltm,
                    "k_min": k_min,
                    "four_domain_both": all(
                        probe.four_domain for probe in probes.values()
                    ),
                    "probes": {
                        str(turn): {
                            "domains": probe.domains_covered,
                            "matched_facts": probe.matched_facts,
                            "source_turns": probe.source_turns,
                            "chars": probe.selection.chars_used,
                            "records": len(probe.selection.selected),
                            "floor_per_topic": probe.selection.floor_per_topic,
                            "fill_selected": probe.selection.fill_selected,
                            "containment_drops": probe.containment_drops,
                        }
                        for turn, probe in probes.items()
                    },
                }
            )

    at_locked_budget = [
        row for row in frontier if row["b_ltm"] == 32000
    ]
    viable_locked = [
        row["k_min"] for row in at_locked_budget if row["four_domain_both"]
    ]
    p1_confirmed = not viable_locked
    amendment_002_floor_inert = any(
        row["k_min"] == 0 and row["four_domain_both"]
        for row in at_locked_budget
    )
    passing = [row for row in frontier if row["four_domain_both"]]

    after = hash_tree(STUDY_007_RUN)
    unchanged = before == after
    result = {
        "study_007_artifacts_hashed": len(before),
        "study_007_artifacts_unchanged": unchanged,
        "plant_key_sha256": sha256_file(PLANT_KEY),
        "candidate_count": len(candidates),
        "fact_rows": len(fact_rows),
        "p1_confirmed": p1_confirmed,
        "locked_budget_viable_k_min": viable_locked,
        "amendment_002_floor_inertness_survives": amendment_002_floor_inert,
        "frontier": frontier,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "gate1_rederivation.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Study 008 — Gate 1 Corrected Re-Derivation",
        "",
        "**Task:** S8-T-005",
        "**Input:** Study 007 accepted treatment store, read-only",
        f"**Plant-key SHA-256:** `{result['plant_key_sha256']}`",
        f"**Verdict:** {'P1 CONFIRMED' if p1_confirmed else 'P1 REFUTED'}",
        "",
        "## Locked-budget verdict",
        "",
    ]
    if viable_locked:
        lines.append(
            "At `B_ltm = 32,000`, genuine fact-aware four-domain coverage at "
            f"both probes is reached by `k_min = {viable_locked}`."
        )
    else:
        lines.append(
            "At `B_ltm = 32,000`, no swept `k_min` from 0 through 4 reaches "
            "genuine fact-aware four-domain coverage at both probes."
        )
    lines.extend(
        [
            "",
            "## Amendment 002 §6 retro-verdict",
            "",
            (
                "The floor-inertness claim survives the corrected criterion."
                if amendment_002_floor_inert
                else "The floor-inertness claim is VOID under the corrected criterion: "
                "`k_min = 0` does not reach fact-aware four-domain coverage at "
                "both probes at 32,000 characters."
            ),
            "",
            "## Corrected frontier",
            "",
            "| B_ltm | k_min | Q11 domains | Q14 domains | Four-domain both |",
            "|---:|---:|---|---|---|",
        ]
    )
    for row in frontier:
        q11 = ", ".join(row["probes"]["120"]["domains"]) or "none"
        q14 = ", ".join(row["probes"]["121"]["domains"]) or "none"
        lines.append(
            f"| {row['b_ltm']} | {row['k_min']} | {q11} | {q14} | "
            f"{'PASS' if row['four_domain_both'] else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "## Integrity",
            "",
            f"- Candidates replayed: {len(candidates)}",
            f"- Locked fact rows: {len(fact_rows)}",
            f"- Study 007 files hashed before and after: {len(before)}",
            f"- Study 007 artifacts unchanged: **{unchanged}**",
            "",
            "Full matched-fact and source-turn details are in",
            "`gate1_rederivation.json`.",
            "",
        ]
    )
    (OUT_DIR / "gate1_rederivation_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print(
        f"Gate 1: {'P1 CONFIRMED' if p1_confirmed else 'P1 REFUTED'}; "
        f"Study 007 artifacts unchanged={unchanged}"
    )
    if passing:
        first = min(passing, key=lambda row: (row["b_ltm"], row["k_min"]))
        print(
            "First swept fact-aware 4/4 point: "
            f"B_ltm={first['b_ltm']} k_min={first['k_min']}"
        )
    else:
        print("No swept episode-rendering point reached fact-aware 4/4.")
    return 0 if unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())

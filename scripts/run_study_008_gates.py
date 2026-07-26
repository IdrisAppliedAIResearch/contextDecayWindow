"""S8-T-011 through S8-T-014: targeted fixture and four-arm replay."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.analysis.study_007_replay import score  # noqa: E402
from src.analysis.study_008_replay import (  # noqa: E402
    PROBE_TURNS,
    STUDY_007_RUN,
    actual_probe_block,
    arm_configs,
    configure_candidates,
    hash_tree,
    load_candidates,
    load_fact_rows,
    match_facts,
    rendered_selection_text,
    replay_arm_probe,
    scored_probes,
)
from src.memory.arbitration import arbitrate_budgeted  # noqa: E402
from src.memory.retrieval_budget import (  # noqa: E402
    FLOOR_DENSITY,
    FLOOR_SIMILARITY,
    RENDER_EPISODE,
    collapse_by_rendered_unit,
    rendered_cost,
    selection_key,
    select_within_budget,
    topic_key,
)
from src.study.domain_labels import ground_truth_domain_for_turn  # noqa: E402


B_LTM = 32000
K_MIN = 1
C_FILL_SWEEP = (1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 40, 50)
FIXTURE = REPO / "experiments/study_008/tests/targeted_retrieval_fixture.json"
OUT_DIR = REPO / "experiments/study_008/replay"
TEST_DIR = REPO / "experiments/study_008/tests"

DOMAIN_NORMALIZATION = {
    "civil_engineering": "civil",
    "renaissance_art": "art",
    "monetary_policy": "monetary",
    "marine_biology": "marine",
}


def topic_domain_map(candidates: list[dict]) -> dict[str, str]:
    votes: dict[str, Counter] = {}
    for candidate in candidates:
        domain = DOMAIN_NORMALIZATION.get(
            ground_truth_domain_for_turn(int(candidate["turn_number"]))
        )
        if domain:
            votes.setdefault(topic_key(candidate), Counter())[domain] += 1
    return {
        topic: counts.most_common(1)[0][0]
        for topic, counts in votes.items()
    }


def own_chars(selection, domain: str, mapping: dict[str, str]) -> int:
    return sum(
        rendered_cost(candidate, selection.render_mode)
        for candidate in selection.selected
        if mapping.get(topic_key(candidate)) == domain
    )


def top_own_key(
    candidates: list[dict],
    domain: str,
    mapping: dict[str, str],
    *,
    floor_ranking: str,
    render_mode: str,
) -> str | None:
    pool, _ = collapse_by_rendered_unit(candidates, render_mode)
    own = [
        candidate
        for candidate in pool
        if mapping.get(topic_key(candidate)) == domain
    ]
    if not own:
        return None
    if floor_ranking == FLOOR_DENSITY:
        own.sort(
            key=lambda candidate: (
                -float(candidate.get("rendered_density") or 0.0),
                -float(candidate["similarity"]),
                selection_key(candidate, render_mode),
            )
        )
    else:
        own.sort(
            key=lambda candidate: (
                -float(candidate["similarity"]),
                selection_key(candidate, render_mode),
            )
        )
    return selection_key(own[0], render_mode)


def targeted_result(
    scored_candidates: list[dict],
    *,
    config,
    domain: str,
    mapping: dict[str, str],
    fact_rows,
) -> dict:
    candidates = configure_candidates(scored_candidates, config)
    selection = select_within_budget(
        candidates,
        budget=B_LTM,
        k_min=K_MIN,
        floor_ranking=config.floor_ranking,
        fill_cap=config.fill_cap,
        render_mode=config.render_mode,
    )
    baseline_config = type(config)(
        arm=f"{config.arm}-baseline",
        floor_ranking=FLOOR_SIMILARITY,
        fill_cap=None,
        render_mode=config.render_mode,
    )
    baseline_candidates = configure_candidates(
        scored_candidates,
        baseline_config,
    )
    baseline = select_within_budget(
        baseline_candidates,
        budget=B_LTM,
        k_min=0,
        floor_ranking=FLOOR_SIMILARITY,
        fill_cap=None,
        render_mode=config.render_mode,
    )

    delivered_own = own_chars(selection, domain, mapping)
    baseline_own = own_chars(baseline, domain, mapping)
    total = selection.chars_used
    non_own = total - delivered_own
    own_loss = max(0, baseline_own - delivered_own)
    slack = max(
        (
            rendered_cost(candidate, config.render_mode)
            for candidate in candidates
        ),
        default=0,
    )
    best_key = top_own_key(
        candidates,
        domain,
        mapping,
        floor_ranking=config.floor_ranking,
        render_mode=config.render_mode,
    )
    selected_keys = {
        selection_key(candidate, config.render_mode)
        for candidate in selection.selected
    }
    matched = match_facts(
        rendered_selection_text(selection.selected, config.render_mode),
        fact_rows,
    )
    return {
        "own_chars": delivered_own,
        "total_chars": total,
        "own_share": round(delivered_own / total if total else 0.0, 6),
        "majority_own_domain": total > 0 and delivered_own / total > 0.5,
        "top_item_key": best_key,
        "top_item_present": best_key in selected_keys,
        "baseline_own_chars": baseline_own,
        "own_chars_lost": own_loss,
        "other_domain_chars": non_own,
        "packing_slack": slack,
        "loss_bound": non_own + slack,
        "bounded_cost": own_loss <= non_own + slack,
        "matched_own_domain_facts": matched.get(domain, []),
        "records": len(selection.selected),
        "fill_per_topic": selection.fill_per_topic,
        "cap_skips": selection.cap_skips,
    }


def run_targeted_fixture(
    fixture: dict,
    targeted_scored: dict[str, list[dict]],
    mapping: dict[str, str],
    fact_rows,
    c_fill: int,
) -> dict:
    configs = arm_configs(c_fill)
    results = {}
    for entry in fixture["queries"]:
        scored = targeted_scored[entry["id"]]
        results[entry["id"]] = {
            arm: targeted_result(
                scored,
                config=config,
                domain=entry["domain"],
                mapping=mapping,
                fact_rows=fact_rows,
            )
            for arm, config in configs.items()
        }
    per_arm = {}
    for arm in configs:
        rows = [result[arm] for result in results.values()]
        per_arm[arm] = {
            "all_majority": all(row["majority_own_domain"] for row in rows),
            "all_top_present": all(row["top_item_present"] for row in rows),
            "all_bounded": all(row["bounded_cost"] for row in rows),
            "min_own_share": min(row["own_share"] for row in rows),
        }
        per_arm[arm]["passed"] = all(
            (
                per_arm[arm]["all_majority"],
                per_arm[arm]["all_top_present"],
                per_arm[arm]["all_bounded"],
            )
        )
    return {
        "c_fill": c_fill,
        "per_arm": per_arm,
        "queries": results,
        "passed": all(row["passed"] for row in per_arm.values()),
    }


def fill_capture_prevented(probes: dict[str, dict]) -> bool:
    for arm in ("B", "D"):
        for probe in probes[arm].values():
            counts = probe.selection.fill_per_topic
            total = probe.selection.fill_selected
            if total >= 2 and (len(counts) < 2 or max(counts.values()) == total):
                return False
    return True


def replay_for_c_fill(scored, fact_rows, c_fill: int) -> dict:
    configs = arm_configs(c_fill)
    probes = {
        arm: {
            turn: replay_arm_probe(
                turn,
                scored[turn],
                config=config,
                fact_rows=fact_rows,
            )
            for turn in PROBE_TURNS
        }
        for arm, config in configs.items()
    }
    return {
        "probes": probes,
        "per_arm_four_domain_both": {
            arm: all(probe.four_domain for probe in arm_probes.values())
            for arm, arm_probes in probes.items()
        },
        "fill_capture_prevented": fill_capture_prevented(probes),
    }


def serializable_replay(replay: dict) -> dict:
    return {
        "per_arm_four_domain_both": replay["per_arm_four_domain_both"],
        "fill_capture_prevented": replay["fill_capture_prevented"],
        "probes": {
            arm: {
                str(turn): {
                    "domains": probe.domains_covered,
                    "matched_facts": probe.matched_facts,
                    "source_turns": probe.source_turns,
                    "chars": probe.selection.chars_used,
                    "records": len(probe.selection.selected),
                    "floor_per_topic": probe.selection.floor_per_topic,
                    "fill_per_topic": probe.selection.fill_per_topic,
                    "cap_skips": probe.selection.cap_skips,
                    "containment_drops": probe.containment_drops,
                }
                for turn, probe in arm_probes.items()
            }
            for arm, arm_probes in replay["probes"].items()
        },
    }


def write_reports(
    sweep: list[dict],
    chosen: dict | None,
    fidelity: dict,
    unchanged: bool,
) -> None:
    gate3_lines = [
        "# Study 008 — Gate 3 Targeted Fixture",
        "",
        "**Task:** S8-T-011",
        "**Criterion:** fact-aware, rendered-character-costed",
        f"**Verdict:** {'PASS' if chosen else 'FAIL'}",
        "",
        "| c_fill | Arm A | Arm B | Arm C | Arm D | Minimum own share |",
        "|---:|---|---|---|---|---:|",
    ]
    for row in sweep:
        targeted = row["targeted"]
        gate3_lines.append(
            f"| {row['c_fill']} | "
            + " | ".join(
                "PASS" if targeted["per_arm"][arm]["passed"] else "FAIL"
                for arm in ("A", "B", "C", "D")
            )
            + " | "
            + f"{min(v['min_own_share'] for v in targeted['per_arm'].values()):.3f} |"
        )
    if chosen:
        gate3_lines.extend(
            [
                "",
                f"Locked jointly at `c_fill = {chosen['c_fill']}`.",
            ]
        )
    else:
        gate3_lines.extend(
            [
                "",
                "No swept `c_fill` passes the registered targeted criterion in "
                "all four arms. The study may not proceed to ablation.",
            ]
        )
    gate3_lines.extend(
        [
            "",
            "Per-query character splits, fact matches, top-item checks, and cost",
            "bounds are recorded in `joint_gate_results.json`.",
            "",
        ]
    )
    (TEST_DIR / "targeted_fixture_report.md").write_text(
        "\n".join(gate3_lines),
        encoding="utf-8",
    )

    gate2_lines = [
        "# Study 008 — Gate 2 Four-Arm Replay",
        "",
        "**Tasks:** S8-T-012 through S8-T-014",
        f"**Arm A byte fidelity:** {'PASS' if fidelity['passed'] else 'FAIL'}",
        f"**Proceed verdict:** {'PASS' if chosen else 'STOP'}",
        "",
        "## Arm A fidelity",
        "",
        "| Probe | Predicted SHA-256 | Actual SHA-256 | Equal |",
        "|---:|---|---|---|",
    ]
    for turn, row in fidelity["probes"].items():
        gate2_lines.append(
            f"| {turn} | `{row['predicted_sha256']}` | "
            f"`{row['actual_sha256']}` | {row['equal']} |"
        )
    gate2_lines.extend(
        [
            "",
            "## Calibration sweep",
            "",
            "| c_fill | A 4/4 | B 4/4 | C 4/4 | D 4/4 | Capture prevented | Gate 3 |",
            "|---:|---|---|---|---|---|---|",
        ]
    )
    for row in sweep:
        four = row["replay"]["per_arm_four_domain_both"]
        gate2_lines.append(
            f"| {row['c_fill']} | "
            + " | ".join("PASS" if four[arm] else "FAIL" for arm in "ABCD")
            + f" | {row['replay']['fill_capture_prevented']} | "
            + f"{'PASS' if row['targeted']['passed'] else 'FAIL'} |"
        )
    if chosen:
        gate2_lines.extend(
            [
                "",
                f"`c_fill = {chosen['c_fill']}` is the smallest jointly passing value.",
                "At least one arm reaches fact-aware four-domain coverage at both probes.",
            ]
        )
    else:
        gate2_lines.extend(
            [
                "",
                "No jointly admissible value exists in the sweep. Per the locked",
                "proceed condition, do not run.",
            ]
        )
    gate2_lines.extend(
        [
            "",
            "## Integrity",
            "",
            f"- Study 007 artifacts unchanged: **{unchanged}**",
            "",
        ]
    )
    (OUT_DIR / "gate2_report.md").write_text(
        "\n".join(gate2_lines),
        encoding="utf-8",
    )


def main() -> int:
    before = hash_tree(STUDY_007_RUN)
    candidates = load_candidates()
    fact_rows = load_fact_rows()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    mapping = topic_domain_map(candidates)
    scored = scored_probes(candidates)
    targeted_scored = {
        entry["id"]: score(candidates, entry["query"])
        for entry in fixture["queries"]
    }

    arm_a = arm_configs(2)["A"]
    fidelity_probes = {}
    for turn in PROBE_TURNS:
        predicted = replay_arm_probe(
            turn,
            scored[turn],
            config=arm_a,
            fact_rows=fact_rows,
        ).rendered_block
        actual = actual_probe_block(turn)
        import hashlib

        fidelity_probes[str(turn)] = {
            "predicted_sha256": hashlib.sha256(
                predicted.encode("utf-8")
            ).hexdigest(),
            "actual_sha256": hashlib.sha256(
                actual.encode("utf-8")
            ).hexdigest(),
            "equal": predicted == actual,
        }
    fidelity = {
        "probes": fidelity_probes,
        "passed": all(row["equal"] for row in fidelity_probes.values()),
    }

    sweep = []
    for c_fill in C_FILL_SWEEP:
        replay = replay_for_c_fill(scored, fact_rows, c_fill)
        targeted = run_targeted_fixture(
            fixture,
            targeted_scored,
            mapping,
            fact_rows,
            c_fill,
        )
        proceed = (
            fidelity["passed"]
            and any(replay["per_arm_four_domain_both"].values())
            and replay["fill_capture_prevented"]
            and targeted["passed"]
        )
        sweep.append(
            {
                "c_fill": c_fill,
                "replay_runtime": replay,
                "replay": serializable_replay(replay),
                "targeted": targeted,
                "proceed": proceed,
            }
        )

    chosen = next((row for row in sweep if row["proceed"]), None)
    after = hash_tree(STUDY_007_RUN)
    unchanged = before == after

    serializable = [
        {
            key: value
            for key, value in row.items()
            if key != "replay_runtime"
        }
        for row in sweep
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "joint_gate_results.json").write_text(
        json.dumps(
            {
                "b_ltm": B_LTM,
                "k_min": K_MIN,
                "topic_domain_map": mapping,
                "fidelity": fidelity,
                "sweep": serializable,
                "chosen_c_fill": chosen["c_fill"] if chosen else None,
                "proceed": chosen is not None,
                "study_007_artifacts_unchanged": unchanged,
                "study_007_artifacts_hashed": len(before),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_reports(sweep, chosen, fidelity, unchanged)

    print(f"Arm A byte fidelity: {fidelity['passed']}")
    print(
        "Joint Gate 2/Gate 3: "
        + (
            f"PASS; c_fill={chosen['c_fill']}"
            if chosen
            else "STOP; no jointly passing c_fill"
        )
    )
    print(f"Study 007 artifacts unchanged: {unchanged}")
    return 0 if chosen and unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())

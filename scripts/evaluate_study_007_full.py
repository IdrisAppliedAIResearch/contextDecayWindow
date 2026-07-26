"""S7-T-024/025/026 — formation checks, bars, and mechanism analysis.

Runs only after `evaluation/rubric_scores.json` is committed. Git order is the
audit trail for that, per Correction 2.
"""

import json
import sqlite3
from pathlib import Path

from src.analysis.study_007_evaluation import (
    PROBE_TURNS,
    block_coverage,
    budget_log,
    delivered_information,
    evaluate_bars,
)

TREATMENT = Path("experiments/study_007/runs/study_007_full_001/condition_c")
CONTROL = Path(
    "experiments/study_007/controls/count_budget_seeded/run_001/condition_c"
)
FACT_KEY = Path("experiments/study_007/q_facts_key.md")
SCORES = Path("experiments/study_007/evaluation/rubric_scores.json")
OUT = Path("experiments/study_007/evaluation/bar_results.json")

Q1_Q13 = [f"Q{i}" for i in range(1, 14)]


def load_scores() -> dict:
    raw = json.loads(SCORES.read_text(encoding="utf-8"))
    mapping = json.loads(
        Path("experiments/study_007/evaluation/sealed_mapping.json")
        .read_text(encoding="utf-8")
    )["mapping"]
    arm_for = {v: k for k, v in mapping.items()}
    out = {}
    for arm, key in (
        ("treatment", "treatment_v7"),
        ("control", "control_count_budget"),
    ):
        block = raw[arm_for[key]]
        out[arm] = {
            "primary": {q: block[q]["primary"] for q in Q1_Q13 + ["Q14"]},
            "strict": {q: block[q]["strict"] for q in Q1_Q13 + ["Q14"]},
        }
    return out


def main() -> None:
    scores = load_scores()
    results = evaluate_bars(TREATMENT, CONTROL, FACT_KEY, scores)

    print("=" * 68)
    print("BAR 3 — Formation non-regression (evaluated first: Bar 1's precondition)")
    b3 = results["bar3_formation"]
    print(f"  domains formed        : {b3['domains_formed']}/4")
    print(f"  content records       : {b3['records_content']}")
    print(f"  non-content records   : {b3['records_non_content']}")
    print(f"  unfaithful at offsets : {b3['unfaithful']}")
    print(f"  inference calls       : {b3['inference_calls']}")
    print(f"  VERDICT               : {'PASS' if b3['pass'] else 'FAIL'}")

    print()
    print("BAR 1 — Breadth recovery")
    b1 = results["bar1_breadth"]
    print(f"  evaluable             : {b1['evaluable']}")
    print(f"  Q11 / Q14 / sum       : {b1['q11']} / {b1['q14']} / {b1['sum']}")
    print(f"  four-domain in block  : {b1['four_domain_in_block']}")
    for turn in PROBE_TURNS:
        per = b1["per_probe"][turn]
        print(
            f"    turn {turn}: treatment={sorted(per['treatment_domains'])} "
            f"control={sorted(per['control_domains'])}"
        )
    print(f"  attribution           : {b1['attribution']}")
    print(f"  VERDICT               : {'PASS' if b1['pass'] else 'FAIL'}")

    print()
    print("BAR 2 — Targeted recall non-regression")
    b2 = results["bar2_targeted"]["primary"]
    print(
        f"  Q1-Q13 treatment/control : "
        f"{b2['treatment_q1_13']} / {b2['control_q1_13']}"
    )
    for cat, vals in b2["categories"].items():
        print(
            f"    {cat}: treatment={vals['treatment']} "
            f"control={vals['control']} ok={vals['treatment'] >= vals['control']}"
        )
    print(f"  VERDICT               : {'PASS' if b2['pass'] else 'FAIL'}")

    print()
    print("=" * 68)
    print("OBSERVATIONAL — delivered LTM information")
    info = delivered_information(TREATMENT)
    for key, value in info.items():
        print(f"  {key}: {value}")

    print()
    print("Probe-turn budget rows")
    rows = {int(r["turn"]): r for r in budget_log(TREATMENT)}
    for turn in PROBE_TURNS:
        r = rows.get(turn)
        if not r:
            continue
        print(
            f"  turn {turn}: topics={r['topic_count']} "
            f"floor={r['floor_selected']} fill={r['fill_selected']} "
            f"drops={r['containment_drops']} chars={r['ltm_chars_used']} "
            f"util={r['budget_utilization']} records={r['ltm_records_used']}"
        )

    verdicts = [b1["pass"], b2["pass"], b3["pass"]]
    overall = results["verdict"]
    print()
    print(f"OVERALL: {overall}")

    results["overall"] = overall
    results["delivered_information"] = info
    OUT.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()

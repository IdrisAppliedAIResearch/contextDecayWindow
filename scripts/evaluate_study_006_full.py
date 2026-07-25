"""S6-T-018/019/020 — score both Study 006 arms against the three bars.

Rubric scores are **not** computed here. They are read from
`experiments/study_006/evaluation/rubric_scores.json`, which the rater fills in
from each arm's `rubric/responses.md` before any dreaming, retrieval or
arbitration log is opened. This script computes everything mechanical:
formation, faithfulness at recorded offsets, non-content counts, and the
observational measures.
"""

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.analysis.study_006_evaluation import (  # noqa: E402
    evaluate_bars,
    evaluate_formation,
    observations,
)

TREATMENT = REPO / "experiments/study_006/runs/study_006_full_001/condition_c"
CONTROL = (
    REPO / "experiments/study_006/controls/whole_turn_seeded/run_001/condition_c"
)
FACT_KEY = REPO / "experiments/study_006/q_facts_key.md"
SCORES = REPO / "experiments/study_006/evaluation/rubric_scores.json"
OUTPUT = REPO / "experiments/study_006/evaluation/study_006_results.json"


def main() -> None:
    if not SCORES.exists():
        raise SystemExit(
            f"Rubric scores not found at {SCORES}.\n"
            "Score both arms' rubric/responses.md first; Bar 2 and Bar 3 "
            "cannot be computed without them."
        )
    scores = json.loads(SCORES.read_text(encoding="utf-8"))

    treatment_conn = sqlite3.connect(TREATMENT / "study.db")
    control_conn = sqlite3.connect(CONTROL / "study.db")
    try:
        treatment_formation = evaluate_formation(
            treatment_conn, FACT_KEY, span_level=True
        )
        control_formation = evaluate_formation(
            control_conn, FACT_KEY, span_level=False
        )
        treatment_obs = observations(treatment_conn)
        control_obs = observations(control_conn)
    finally:
        treatment_conn.close()
        control_conn.close()

    bars = evaluate_bars(
        treatment_formation,
        scores["treatment"],
        scores["control"],
    )

    payload = {
        "rater": scores.get("rater"),
        "scored_at": scores.get("scored_at"),
        "scoring_note": scores.get("note"),
        "treatment": {
            "formation": treatment_formation,
            "observations": treatment_obs,
            "scores": scores["treatment"],
        },
        "control": {
            "formation": control_formation,
            "observations": control_obs,
            "scores": scores["control"],
        },
        "bars": bars,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("=== BAR 1 — Formation ===")
    b1 = bars["bar1"]
    for domain, value in treatment_formation["domains"].items():
        print(
            f"  {domain:20} formed={value['formed']}  "
            f"facts {value['facts_present']}/{value['facts_total']}"
        )
    print(
        f"  domains {b1['domains_formed']}/4  unfaithful={b1['unfaithful']}  "
        f"non-content={b1['non_content']}  -> {'PASS' if b1['pass'] else 'FAIL'}"
    )

    print("\n=== BAR 2 — Breadth ===")
    b2 = bars["bar2"]
    print(
        f"  Q11={b2['Q11']}  Q14={b2['Q14']}  sum={b2['sum']}  "
        f"evaluable={b2['evaluable']}  -> {'PASS' if b2['pass'] else 'FAIL'}"
    )

    print("\n=== BAR 3 — Non-regression (Q1-Q13) ===")
    b3 = bars["bar3"]
    print(
        f"  treatment={b3['treatment_total']}  control={b3['control_total']}  "
        f"delta={b3['delta']:+.1f}  -> {'PASS' if b3['pass'] else 'FAIL'}"
    )
    if b3["regressions"]:
        print(f"  regressions: {', '.join(b3['regressions'])}")
        for q in b3["regressions"]:
            v = b3["per_question"][q]
            print(f"    {q}: treatment {v['treatment']} vs control {v['control']}")

    print(f"\n=== VERDICT: {bars['verdict']} ===")

    print("\n=== Observational ===")
    for label, obs in (("treatment", treatment_obs), ("control", control_obs)):
        print(
            f"  {label:10} records={obs['records']:4} "
            f"compression={obs['compression_pct']:.2f}%  "
            f"roles={obs['records_by_role']}  "
            f"inference_calls={obs['inference_calls_total']}"
        )
    print(f"\nWritten: {OUTPUT}")


if __name__ == "__main__":
    main()

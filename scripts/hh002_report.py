"""Render HH-002's results.

Every number printed here is read from a committed artifact under
``experiments/comparisons/hh_002/artifacts/``. Nothing is retyped, and the
gate is evaluated before the leaderboard is printed so a reader cannot see the
component's row without first seeing whether the rig reproduced the rows it is
standing beside.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analysis.hh002_analysis import (  # noqa: E402
    HH002AnalysisError,
    cost_summary,
    depth_strata,
    gctrl,
    judge_variance,
    leaderboard,
    load_judged,
    paired,
)
from analysis.hh002_run import ARTIFACTS, INHERITED, PUBLISHED, score  # noqa: E402

ALL_ARMS = ["A_FULL", "A_CDW", "A_CDW_NOTS", "A_RAG", "A_NONE"]


def _available(base: Path) -> list[str]:
    out = []
    for arm in ALL_ARMS:
        if (base / arm / "judged_r1.json").exists():
            out.append(arm)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render HH-002 results")
    parser.add_argument("--base", type=Path, default=ARTIFACTS)
    parser.add_argument("--tolerance", type=float, default=3.0)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    base = args.base
    arms = _available(base)
    if not arms:
        print("No judged arms yet.")
        return 1

    lines: list[str] = []
    w = lines.append

    w("# HH-002 results\n")
    w(f"Arms scored: {', '.join(arms)}\n")

    # -- judge variance, which sets the tolerance ------------------------
    tolerance = args.tolerance
    variance = None
    for arm in arms:
        if (base / arm / "judged_r2.json").exists():
            try:
                variance = judge_variance(arm, base)
            except HH002AnalysisError:
                continue
            break
    w("## Judge run-to-run variance\n")
    if variance is None:
        w("Not measured. Tolerance falls back to the registered "
          f"±{tolerance:.1f} points.\n")
    else:
        w(f"Same {variance['n']} sealed answers from `{variance['arm']}`, "
          f"judged twice.\n")
        w(f"- Rates: {variance['rate_points']}")
        w(f"- Spread: **{variance['spread_points']:.2f} points**")
        w(f"- Items that flipped: {variance['item_flips']} "
          f"({variance['item_flip_rate']*100:.2f}%)\n")
        tolerance = max(args.tolerance, variance["spread_points"])
        w(f"Registered rule: ±3.0 points or the measured spread, whichever is "
          f"wider. **Tolerance = ±{tolerance:.2f} points.**\n")

    # -- G-CTRL ----------------------------------------------------------
    gate = gctrl(tolerance, base)
    w("## G-CTRL: did this rig reproduce the published rows?\n")
    w("| Arm | Published | Measured | Delta | Within tolerance |")
    w("|---|---:|---:|---:|:--:|")
    for check in gate["checks"]:
        if check.get("status") == "NOT RUN":
            w(f"| `{check['arm']}` | {check['target']:.2f}% | — | — | not run |")
            continue
        w(f"| `{check['arm']}` | {check['target_points']:.2f}% | "
          f"**{check['measured_points']:.2f}%** | "
          f"{check['delta_points']:+.2f} | "
          f"{'yes' if check['within_tolerance'] else '**NO**'} |")
    w("")
    w(f"**G-CTRL {'PASSED' if gate['passed'] else 'FAILED'}.**\n")

    # -- floor -----------------------------------------------------------
    if "A_NONE" in arms:
        floor = score(list(load_judged("A_NONE", base=base).values()))
        w("## G-FLOOR: contamination\n")
        w(f"`A_NONE` scored **{floor['llm_score']*100:.2f}%** "
          f"on {floor['n']} questions with no memory block at all. "
          f"Bar is below 5%. "
          f"{'Passed.' if floor['llm_score'] < 0.05 else '**FAILED.**'}\n")

    # -- leaderboard -----------------------------------------------------
    w("## The table\n")
    w("| System | LLM-as-a-Judge | n | Source |")
    w("|---|---:|---:|---|")
    for row in leaderboard(arms, base):
        marker = "**" if row["system"].startswith("A_CDW") else ""
        w(f"| {marker}{row['system']}{marker} | "
          f"{marker}{row['llm_score_points']:.2f}%{marker} | {row['n']} | "
          f"{row['source']} |")
    w("")
    w("Five rows are the Mem0 authors' reproductions of other people's "
      "systems, not those systems' own reports.\n")

    # -- paired contrasts -------------------------------------------------
    w("## Paired contrasts\n")
    w("Item-level, against arms this run produced. No paired test is possible "
      "against an inherited row: their per-item answers were never "
      "published.\n")
    w("| Contrast | Endpoint | Delta | Gains | Losses | p (one-sided) |")
    w("|---|---|---:|---:|---:|---:|")
    pairs = [("A_CDW", "A_RAG"), ("A_CDW", "A_NONE"), ("A_FULL", "A_CDW"),
             ("A_CDW", "A_CDW_NOTS")]
    for treatment, control in pairs:
        if treatment not in arms or control not in arms:
            continue
        for endpoint in ("llm_score", "f1"):
            try:
                contrast = paired(treatment, control, endpoint, base)
            except HH002AnalysisError:
                continue
            w(f"| {treatment} vs {control} | {endpoint} | "
              f"{contrast.delta*100:+.2f} | {contrast.gains} | "
              f"{contrast.losses} | {contrast.p_one_sided:.3g} |")
    w("")

    # -- cost -------------------------------------------------------------
    w("## What each arm spent to answer\n")
    w("| Arm | Mean prompt tokens | Mean context chars | Units delivered | "
      "Median retrieval ms |")
    w("|---|---:|---:|---:|---:|")
    for arm, row in cost_summary(arms, base).items():
        w(f"| {arm} | {row['mean_prompt_tokens']:,.0f} | "
          f"{row['mean_context_chars']:,.0f} | "
          f"{row['mean_units_delivered']:,.2f} | "
          f"{row['median_search_ms']:.2f} |")
    w("")

    # -- per category -----------------------------------------------------
    w("## By question category\n")
    w("LoCoMo category 2 is temporal, 5 is adversarial and never scored.\n")
    cats = sorted({
        c for arm in arms
        for c in score(list(load_judged(arm, base=base).values()))["per_category"]
    })
    w("| Arm | " + " | ".join(f"cat {c}" for c in cats) + " |")
    w("|---" * (len(cats) + 1) + "|")
    for arm in arms:
        result = score(list(load_judged(arm, base=base).values()))
        cells = []
        for c in cats:
            entry = result["per_category"].get(c)
            cells.append(f"{entry['llm_score']*100:.1f}%" if entry else "—")
        w(f"| {arm} | " + " | ".join(cells) + " |")
    w("")

    # -- depth ------------------------------------------------------------
    if "A_CDW" in arms and "A_RAG" in arms:
        w("## Where the evidence sits\n")
        rows = depth_strata("A_CDW", "A_RAG", base)
        if rows:
            w("| Quartile | Depth | n | A_CDW | A_RAG | Delta |")
            w("|---|---|---:|---:|---:|---:|")
            for row in rows:
                w(f"| {row['quartile']} | {row['depth_range']} | {row['n']} | "
                  f"{row['A_CDW_points']:.2f}% | {row['A_RAG_points']:.2f}% | "
                  f"{row['delta_points']:+.2f} |")
            w("")

    text = "\n".join(lines)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8", newline="\n")
        print(f"\nwritten to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

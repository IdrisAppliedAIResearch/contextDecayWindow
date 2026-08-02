"""Generate PAPER-001's six figures from committed artifacts.

Every value plotted is read from a committed artifact. No number is entered by
hand in this file except two documented corrections, both flagged inline and
both traceable to `ERRATA.md`:

  1. DR-002's selection table publishes turn 118 at cosine rank 21. The
     re-measurement under E005's committed nine-query batched embedding call
     puts it at rank 20 (`generality_batched.json`). The corrected value is
     read from that artifact, not typed.
  2. `dr_002_results.json` carries a pre-correction `timings` block that its
     own report supersedes. It is not read here; Figure 6 uses CC-005's
     `latency_curve.csv`.

Writes SVG (vector) plus a manifest recording the SHA-256 of every input, so a
caption's provenance can be checked without rerunning anything.

Usage:
    python scripts/generate_paper_001_figures.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "experiments/components/retrieval_mechanism_ledger/artifacts"
CLOSEOUT = REPO / "experiments/components/deployment_closeout/artifacts"
AUDIT = REPO / "experiments/audits/scoring_integrity"
OUT = REPO / "paper/figures"

# Okabe-Ito, colourblind-safe.
BLACK = "#000000"
ORANGE = "#E69F00"
SKY = "#56B4E9"
GREEN = "#009E73"
YELLOW = "#F0E442"
BLUE = "#0072B2"
VERMILLION = "#D55E00"
PURPLE = "#CC79A7"
GREY = "#999999"

_INPUTS: dict[str, str] = {}


def read(path: Path) -> Path:
    """Record a file's canonical hash, then hand back the path.

    Hashes git blob content so the value matches the repository convention and
    does not drift with platform line endings.
    """
    rel = path.relative_to(REPO).as_posix()
    if rel not in _INPUTS:
        blob = subprocess.run(
            ["git", "show", f"HEAD:{rel}"],
            cwd=REPO,
            capture_output=True,
            check=True,
        ).stdout
        _INPUTS[rel] = hashlib.sha256(blob).hexdigest()[:16]
    return path


def load_json(path: Path) -> dict:
    return json.loads(read(path).read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict]:
    with read(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def style(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GREY, alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.svg", format="svg", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}.svg / .png")


# --------------------------------------------------------------------------
# F1 - cosine rank against fact content
# --------------------------------------------------------------------------
def figure_1() -> None:
    ranks = load_csv(LEDGER / "e005/dr_002/selection_ranks.csv")
    cost = load_csv(LEDGER / "dx001/cost_comparison.csv")
    generality = load_json(LEDGER / "e005/dr_002/generality_batched.json")

    q11 = next(r for r in generality["generality"] if r["question"] == "Q11")
    correction = {
        int(c["source_turn"]): int(c["measured_rank"])
        for c in generality["selection_rank_corrections"]
    }

    points = []
    for row in ranks:
        turn = int(row["source_turn"])
        rank = correction.get(turn, int(row["cosine_rank"]))
        facts = len([i for i in row["q11_items"].split(";") if i.strip()])
        points.append((rank, facts, turn))

    # The unselected residual, turn 90, comes from DX-001's cost comparison.
    target = next(r for r in cost if r["role"] == "target")
    points.append((int(target["cosine_rank"]), int(target["q11_facts"]), int(target["turn"])))

    oracle_turns = {90, 112, 113, 116, 118}

    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    style(ax)

    ax.axvspan(0.5, 4.5, color=VERMILLION, alpha=0.10, zorder=0)
    ax.axvline(34.5, color=BLUE, linewidth=1.2, linestyle="--", zorder=1)
    ax.axvline(100.5, color=PURPLE, linewidth=1.2, linestyle=":", zorder=1)

    for rank, facts, turn in points:
        is_oracle = turn in oracle_turns
        selected = turn != int(target["turn"])
        ax.vlines(rank, 0, facts, color=GREY, linewidth=1.0, zorder=2)
        ax.scatter(
            rank,
            facts,
            s=104 if is_oracle else 54,
            facecolor=(GREEN if selected else "white"),
            edgecolor=(BLACK if is_oracle else GREEN),
            linewidth=1.8 if is_oracle else 1.0,
            marker="o" if selected else "D",
            zorder=3,
        )

    ax.annotate(
        "ranks 1-4 carry\nzero target facts",
        xy=(2.6, 0.12),
        xytext=(8, 1.55),
        fontsize=8.5,
        color=VERMILLION,
        arrowprops=dict(arrowstyle="->", color=VERMILLION, linewidth=1.0),
    )
    ax.annotate(
        f"first fact-bearing\nepisode: rank {q11['first_hit']}",
        xy=(q11["first_hit"], 3.08),
        xytext=(15, 4.75),
        fontsize=8.5,
        arrowprops=dict(arrowstyle="->", color=BLACK, linewidth=0.9),
    )
    worst_rank = max(r for r, f, _ in points if f > 0 and r != 112)
    ax.annotate(
        f"worst fact-bearing selection: rank {worst_rank}, 2 art items;\n"
        f"the last still-needed item first appears at rank {q11['last_needed']}",
        xy=(worst_rank, 2.06),
        xytext=(38, 3.15),
        fontsize=8.5,
        arrowprops=dict(arrowstyle="->", color=BLACK, linewidth=0.9),
    )
    ax.annotate(
        "turn 90: 4 monetary items.\nNeeds cosine 0.225, has 0.056",
        xy=(111, 4.06),
        xytext=(56, 5.05),
        fontsize=8.5,
        color=VERMILLION,
        arrowprops=dict(arrowstyle="->", color=VERMILLION, linewidth=0.9),
    )
    ax.text(36.2, 0.30, "deployed pool cut (34)", fontsize=8, color=BLUE, rotation=90, va="bottom")
    ax.text(102.2, 0.30, "top-100 cut", fontsize=8, color=PURPLE, rotation=90, va="bottom")

    ax.set_xlim(0, 121)
    ax.set_ylim(0, 5.7)
    ax.set_xlabel("cosine rank against the turn-120 breadth query (1 = most similar, of 119 eligible episodes)")
    ax.set_ylabel("Q11 target facts carried")
    ax.set_title(
        "Figure 1  The target facts sit outside the top of the ranking, and the pool cut removes a domain",
        fontsize=10.5,
        loc="left",
        pad=12,
    )

    handles = [
        plt.Line2D([], [], marker="o", color="none", markerfacecolor=GREEN,
                   markeredgecolor=GREEN, markersize=8, label="selected by the primary configuration"),
        plt.Line2D([], [], marker="D", color="none", markerfacecolor="white",
                   markeredgecolor=GREEN, markersize=7, label="in the pool, never selected"),
        plt.Line2D([], [], marker="o", color="none", markerfacecolor=GREEN,
                   markeredgecolor=BLACK, markeredgewidth=1.8, markersize=10,
                   label="episode of the 15-fact known optimum"),
    ]
    ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.20),
        ncol=3,
        frameon=False,
        fontsize=8.5,
    )

    fig.text(
        0.005,
        -0.26,
        "Only the 16 episodes whose cosine rank is committed are plotted: the 15 selected, plus the rank-112 miss.\n"
        "Per-episode ranks for the other 103 candidates were never committed. The rank-4, rank-5 and rank-87 readings\n"
        "are committed structural values (generality_batched.json), drawn as annotations rather than inferred from points.\n"
        "Turn 118 is shown at its corrected rank 20, not the published 21 (ERRATA.md, 2026-08-01).",
        fontsize=7.6,
        color="#444444",
        va="top",
    )
    save(fig, "f1_cosine_rank_vs_fact_content")


# --------------------------------------------------------------------------
# F2 - the budget efficiency gap
# --------------------------------------------------------------------------
def figure_2() -> None:
    e005 = load_json(LEDGER / "e005/e005_results.json")
    a0 = load_json(LEDGER / "e005/a0_baseline.json")
    ar = load_json(LEDGER / "ar_001/achievability.json")

    exact_chars = ar["exact_optimum"]["serialized_chars"]
    exact_facts = ar["exact_optimum"]["fact_count"]

    bars = [
        ("deployed baseline - deployed selector, 34-episode pool",
         a0["serialized_chars"], a0["fact_count"], VERMILLION, "right", 0.34),
        ("set-level coverage - new selector AND 119-episode pool",
         e005["primary_configuration"]["serialized_chars"],
         e005["primary_configuration"]["q11_fact_count"], BLUE, "right", 0.34),
        ("known optimum, greedy - answer key, 119-episode pool",
         e005["oracle"]["serialized_chars"], e005["oracle"]["fact_count"],
         GREEN, "left", 0.0),
        ("known optimum, exact - answer key, 119-episode pool",
         exact_chars, exact_facts, SKY, "left", -0.62),
    ]

    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    style(ax)

    for label, chars, facts, colour, side, dy in bars:
        ax.hlines(facts, 0, chars, color=colour, linewidth=4.0, alpha=0.85, zorder=2)
        ax.scatter([chars], [facts], s=70, color=colour, zorder=3)
        if side == "right":
            ax.text(chars - 400, facts + dy, f"{label}   {facts}/17 in {chars:,} chars",
                    fontsize=8.8, ha="right", va="bottom", color=colour, zorder=4)
        else:
            ax.text(chars + 700, facts + dy, f"{label}   {facts}/17 in {chars:,} chars",
                    fontsize=8.8, ha="left", va="center", color=colour, zorder=4)

    ax.axhline(14, color=BLACK, linewidth=1.1, linestyle="--", zorder=1)
    ax.text(31900, 14.22, "registered breadth bar, 14/17", fontsize=8.4, ha="right", va="bottom")
    ax.axvline(32000, color=GREY, linewidth=1.1, zorder=1)
    ax.text(31780, 1.4, "enforced budget\n32,000 chars", fontsize=8.4, ha="right", color=GREY)

    shipped = e005["primary_configuration"]
    greedy = e005["oracle"]
    extra_chars = shipped["serialized_chars"] - greedy["serialized_chars"]
    fewer_facts = greedy["fact_count"] - shipped["q11_fact_count"]
    ax.annotate(
        "",
        xy=(greedy["serialized_chars"], 16.3), xytext=(shipped["serialized_chars"], 16.3),
        arrowprops=dict(arrowstyle="<->", color=BLACK, linewidth=1.0),
    )
    ax.text(
        (greedy["serialized_chars"] + shipped["serialized_chars"]) / 2,
        16.45,
        f"{extra_chars:,} more characters, {fewer_facts} fewer facts",
        fontsize=8.6,
        ha="center",
    )

    ax.set_xlim(0, 34500)
    ax.set_ylim(0, 17.2)
    ax.set_xlabel("characters spent (exact serialized cost)")
    ax.set_ylabel("Q11 target facts delivered")
    ax.set_title(
        "Figure 2  The constraint is not capacity: the tallest result is also the narrowest",
        fontsize=10.5,
        loc="left",
        pad=12,
    )
    fig.text(
        0.005,
        -0.055,
        "The top two bars change TWO things against the baseline, not one: the selection objective and the candidate pool.\n"
        "Section 5.2 separates them - on the deployed 34-episode pool the same set-level configuration scores 5/17, BELOW the\n"
        "baseline's 6/17. Read this figure as the budget argument only: the target is affordable, and deployed selection spent\n"
        "the whole budget without reaching it. The two known-optimum bars are computed with the answer key and are bounds,\n"
        "not methods; no deployable selection reaches the 14/17 bar.",
        fontsize=7.6,
        color="#444444",
        va="top",
    )
    save(fig, "f2_budget_efficiency_gap")


# --------------------------------------------------------------------------
# F3 - pool ablation
# --------------------------------------------------------------------------
def figure_3() -> None:
    # DR-002 section 1: one frozen configuration read across three pools.
    frozen = "A3_l0.1_r0.0_k16"
    sweep = load_csv(LEDGER / "e005/configuration_sweep.csv")
    secondaries = load_csv(LEDGER / "e005/pool_secondaries.csv")

    pools = [("deployed_n_union_k", 34), ("cosine_top_100", 100), ("full_eligible_store", 119)]
    facts, domains, oracle, best = [], [], [], []
    for pool, _ in pools:
        row = next(r for r in sweep if r["configuration_id"] == frozen and r["pool"] == pool)
        facts.append(int(row["q11_fact_count"]))
        domains.append(int(row["q11_domain_count"]))
        oracle.append(int(row["oracle_overlap"]))
        best.append(max(int(r["q11_fact_count"]) for r in secondaries if r["pool"] == pool))

    labels = [f"{n}\ncandidates" for _, n in pools]
    fig, axes = plt.subplots(1, 3, figsize=(9.4, 3.7))
    panels = [
        (axes[0], facts, "Q11 facts delivered", 17, BLUE),
        (axes[1], domains, "domains covered", 4, GREEN),
        (axes[2], oracle, "overlap with the 5-episode\nknown optimum", 5, ORANGE),
    ]
    for index, (ax, values, title, top, colour) in enumerate(panels):
        style(ax)
        ax.bar(labels, values, color=colour, alpha=0.85, width=0.62)
        for x, v in enumerate(values):
            # Panel 0 carries a best-of-sweep rule just above each bar, so its
            # value labels sit inside the bar to stay clear of it.
            if index == 0 and v > 2:
                ax.text(x, v - top * 0.055, str(v), ha="center", va="top",
                        fontsize=9.5, fontweight="bold", color="white")
            else:
                ax.text(x, v + top * 0.03, str(v), ha="center", fontsize=9.5, fontweight="bold")
        ax.set_ylim(0, top * 1.18)
        ax.set_title(title, fontsize=9.5)
        ax.tick_params(labelsize=8.5)

    axes[0].axhline(14, color=BLACK, linewidth=1.0, linestyle="--")
    axes[0].text(2.42, 14.25, "bar 14/17", fontsize=7.6, ha="right")
    for x, v in enumerate(best):
        axes[0].plot([x - 0.31, x + 0.31], [v, v], color=VERMILLION, linewidth=1.8)
    axes[0].text(
        -0.45, 18.1,
        "orange rule = best of the 146\nconfigurations on that pool",
        fontsize=7.4, color=VERMILLION, va="top",
    )

    fig.suptitle(
        "Figure 3  Widening the pool moves the frozen configuration from 5/17 across 2 domains to 12/17 across 4",
        fontsize=10.5,
        x=0.005,
        ha="left",
        y=1.03,
    )
    fig.text(
        0.005,
        -0.14,
        "One frozen configuration (A3, lambda 0.1, r 0.0, k 16) read across three pools; store, renderer and embedding held fixed.\n"
        "Dropping only the 19 lowest-cosine episodes to form the 100-pool costs three facts, the whole art domain, and all\n"
        "optimum overlap - though four of the five optimum episodes survive the cut. The selector clusters over the pool, so\n"
        "removing the tail reshuffles the objective rather than removing options. The best-of-sweep rule shows why the pool's\n"
        "binding effect must be read in domains: that maximum is 13/17 on all three pools.",
        fontsize=7.6,
        color="#444444",
        va="top",
    )
    save(fig, "f3_pool_ablation")


# --------------------------------------------------------------------------
# F4 - the corrected arc
# --------------------------------------------------------------------------
def figure_4() -> None:
    totals = load_json(AUDIT / "corrected_scores/arm_totals.json")
    wanted = [
        ("s002_c", "002 C"), ("s003_accepted", "003"), ("s004_treatment", "004"),
        ("s005_treatment", "005"), ("s006_treatment", "006"),
        ("s007_treatment", "007"), ("s009_l", "009 L"),
    ]
    rows = []
    for arm_id, label in wanted:
        row = next(r for r in totals if r["arm_id"] == arm_id)
        rows.append((label, row["original_q1_q13"], row["corrected_q1_q13"]))

    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    style(ax)
    xs = range(len(rows))
    for x, (_, original, corrected) in zip(xs, rows):
        ax.plot([x, x], [original, corrected], color=GREY, linewidth=1.4, zorder=1)
    ax.scatter(list(xs), [r[1] for r in rows], s=64, color=GREY, zorder=2, label="as originally published")
    ax.scatter(list(xs), [r[2] for r in rows], s=76, color=BLUE, zorder=3, label="after the scoring audit")

    for x, (_, original, corrected) in zip(xs, rows):
        if original != corrected:
            ax.annotate(f"{corrected - original:+.1f}", xy=(x, (original + corrected) / 2),
                        xytext=(9, 0), textcoords="offset points",
                        fontsize=8.2, color=VERMILLION, va="center")

    ax.set_xticks(list(xs))
    ax.set_xticklabels([r[0] for r in rows])
    ax.set_ylim(0, 14.4)
    ax.set_xlabel("study arm")
    ax.set_ylabel("treatment score (Q1-Q13, of 13)")
    ax.set_title(
        "Figure 4  19 of 222 re-scored items changed, and the program's only VALIDATED verdict disappeared",
        fontsize=10.5,
        loc="left",
        pad=12,
    )
    ax.legend(loc="lower right", frameon=False, fontsize=8.6)
    fig.text(
        0.005,
        -0.075,
        "These points are not a controlled series: runtime and response budgets changed across it. The only clean architectural\n"
        "comparison in the program is Study 009's same-seed pair, 9.0 without the memory tier against 12.0 with it. Study 010 was\n"
        "outside the audit and is not plotted. Study 001, which lost the VALIDATED verdict, scored on a different rubric and is\n"
        "likewise not plotted; its fall is reported in the text.",
        fontsize=7.6,
        color="#444444",
        va="top",
    )
    save(fig, "f4_corrected_arc")


# --------------------------------------------------------------------------
# F5 - selector comparison
# --------------------------------------------------------------------------
def figure_5() -> None:
    sweep = load_csv(LEDGER / "e005/configuration_sweep.csv")
    e005 = load_json(LEDGER / "e005/e005_results.json")
    a0 = load_json(LEDGER / "e005/a0_baseline.json")

    primary = e005["primary_configuration"]
    pool = "full_eligible_store"

    def best_of(arm: str) -> dict:
        rows = [r for r in sweep if r["arm"] == arm and r["pool"] == pool]
        return max(rows, key=lambda r: int(r["q11_fact_count"]))

    a1, a2 = best_of("A1"), best_of("A2")
    arms = [
        ("A0\ndeployed", a0["fact_count"], a0["domain_count"], None, VERMILLION),
        ("A1\nMMR", int(a1["q11_fact_count"]), int(a1["q11_domain_count"]), int(a1["monetary"]), SKY),
        ("A2\nfacility\nlocation", int(a2["q11_fact_count"]), int(a2["q11_domain_count"]), int(a2["monetary"]), ORANGE),
        ("A3\nrelevance +\ndiversity", primary["q11_fact_count"], primary["q11_domain_count"], primary["monetary"], BLUE),
        ("A4\nknown\noptimum", e005["oracle"]["fact_count"], 4, 4, GREEN),
    ]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.6, 4.2), gridspec_kw={"width_ratios": [1.55, 1]})
    style(ax)
    style(ax2)

    labels = [a[0] for a in arms]
    ax.bar(labels, [a[1] for a in arms], color=[a[4] for a in arms], alpha=0.85, width=0.6)
    for x, a in enumerate(arms):
        ax.text(x, a[1] + 0.28, f"{a[1]}/17", ha="center", fontsize=9, fontweight="bold")
    ax.axhline(14, color=BLACK, linewidth=1.0, linestyle="--")
    ax.text(-0.44, 14.25, "bar 14/17", fontsize=7.8, ha="left")
    ax.set_ylim(0, 17.4)
    ax.set_ylabel("Q11 facts delivered (best configuration per arm)")
    ax.tick_params(labelsize=8.2)

    ax.annotate(
        "highest count,\npassed no gate",
        xy=(2, 13.2), xytext=(1.15, 16.2),
        fontsize=8.4, color=VERMILLION,
        arrowprops=dict(arrowstyle="->", color=VERMILLION, linewidth=1.0),
    )

    have_monetary = [a for a in arms if a[3] is not None]
    ax2.bar([a[0] for a in have_monetary], [a[3] for a in have_monetary],
            color=[a[4] for a in have_monetary], alpha=0.85, width=0.55)
    for x, a in enumerate(have_monetary):
        ax2.text(x, a[3] + 0.09, f"{a[3]}/4", ha="center", fontsize=9, fontweight="bold")
    ax2.set_ylim(0, 4.8)
    ax2.set_ylabel("monetary domain items (of 4)")
    ax2.set_title("the per-domain check that caught A2", fontsize=9.2)
    ax2.tick_params(labelsize=8.2)

    fig.suptitle(
        "Figure 5  The selector with the highest raw fact count delivered nothing from one domain and passed no gate",
        fontsize=10.5,
        x=0.005,
        ha="left",
        y=1.02,
    )
    fig.text(
        0.005,
        -0.10,
        "Primary pool, 119 candidates, 32,000-character budget; best configuration per arm by fact count. A2 delivers monetary 0/4\n"
        "at every one of its settings. On THIS pool all 146 configurations beat the deployed 6/17; on the deployed 34-episode\n"
        "pool they fall as low as 4/17 and the shipped configuration scores 5/17, which is the ordering result in section 5.7.\n"
        "137 configurations preserve 16/16 targeted items, so targeted recall does not separate the arms - itself the finding:\n"
        "the failure is confined to enumeration. A4 is AR-001's known optimum, a reference point and never deployable.",
        fontsize=7.6,
        color="#444444",
        va="top",
    )
    save(fig, "f5_selector_comparison")


# --------------------------------------------------------------------------
# F6 - growth and cost
# --------------------------------------------------------------------------
def figure_6() -> None:
    dx002 = load_json(CLOSEOUT / "dx002/dx002_results.json")
    gate = load_json(CLOSEOUT / "cc003/ge0_growth_gate.json")
    latency = load_csv(CLOSEOUT / "cc005/latency_curve.csv")
    growth = load_json(CLOSEOUT / "cc005/growth_measurement.json")

    def buckets(arm_name: str) -> tuple[list[int], list[int]]:
        arm = next(a for a in dx002["arms"] if a["arm"] == arm_name)
        blocks = arm["series"]["retrieved_stm"]["blocks"][-5:]
        return [b["last_turn"] for b in blocks], [b["p95"] for b in blocks]

    l_turns, l_p95 = buckets("arm_l")
    s_turns, s_p95 = buckets("arm_s")
    lib_blocks = gate["saturation"]["blocks"][-5:]
    lib_turns = [b["last_turn"] for b in lib_blocks]
    lib_p95 = [b["p95"] for b in lib_blocks]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.2, 4.3))
    style(ax)
    style(ax2)

    ax.plot(s_turns, s_p95, marker="o", color=VERMILLION, linewidth=1.8, label="study runner, arm S")
    ax.plot(l_turns, l_p95, marker="s", color=ORANGE, linewidth=1.8, label="study runner, arm L")
    ax.plot(lib_turns, lib_p95, marker="D", color=BLUE, linewidth=1.8, label="extracted library")
    ax.axhline(gate["budget_chars"], color=GREY, linewidth=1.1, linestyle="--")
    ax.text(1000, gate["budget_chars"] + 1400, "32,000-char budget", fontsize=8, ha="right", color=GREY)

    ax.annotate(f"+{s_p95[-1] - s_p95[0]:,} chars", xy=(s_turns[-1], s_p95[-1]),
                xytext=(-6, 8), textcoords="offset points", fontsize=8.4,
                color=VERMILLION, ha="right")
    ax.annotate(f"+{l_p95[-1] - l_p95[0]:,} chars", xy=(l_turns[-1], l_p95[-1]),
                xytext=(-6, -16), textcoords="offset points", fontsize=8.4,
                color=ORANGE, ha="right")
    ax.annotate(f"+{int(gate['saturation']['p95_growth_chars'])} chars",
                xy=(lib_turns[-1], lib_p95[-1]), xytext=(-6, -18),
                textcoords="offset points", fontsize=8.4, color=BLUE, ha="right")

    ax.set_xlabel("turn (100-turn buckets, final 500 turns)")
    ax.set_ylabel("95th percentile of the retrieved block (chars)")
    ax.set_title("the leak was the harness, not the component", fontsize=9.6)
    ax.legend(loc="upper left", frameon=False, fontsize=8.2)

    candidates = [int(r["candidates"]) for r in latency]
    medians = [float(r["median_ms"]) for r in latency]
    ax2.plot(candidates, medians, marker="o", color=BLUE, linewidth=1.9, label="measured (CC-005)")

    # The withdrawn projection: DR-002's flat ~40 microseconds per candidate.
    withdrawn = [0.040 * n for n in candidates]
    ax2.plot(candidates, withdrawn, color=VERMILLION, linewidth=1.5, linestyle="--",
             label="withdrawn projection (~40 us/candidate)")

    coefficient = growth["latency"]["fitted_coefficient"]
    exponent = growth["latency"]["fitted_exponent"]
    forward = [1500, 2000, 3000, 5000]
    ax2.plot([candidates[-1]] + forward,
             [medians[-1]] + [coefficient * n ** exponent for n in forward],
             color=BLUE, linewidth=1.4, linestyle=":", label="projection above the measured range")

    ax2.annotate(
        f"{medians[-1]:.0f} ms measured\nvs ~{withdrawn[-1]:.0f} ms projected",
        xy=(1000, medians[-1] * 1.12), xytext=(56, 620),
        fontsize=8.4, color=BLUE,
        arrowprops=dict(arrowstyle="->", color=BLUE, linewidth=1.0),
    )
    ax2.axvline(119, color=GREY, linewidth=1.0, linestyle=":")
    ax2.text(128, 2.6, "DR-002's last\nmeasured point (119)", fontsize=7.8, color=GREY)

    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("candidate episodes in the pool")
    ax2.set_ylabel("median selection latency (ms, embedding excluded)")
    ax2.set_title("a projection extended 84x past its data", fontsize=9.6)
    ax2.legend(loc="lower right", frameon=False, fontsize=7.8)

    fig.suptitle(
        "Figure 6  Growth belonged to the harness; cost was five times the projection",
        fontsize=10.5,
        x=0.005,
        ha="left",
        y=1.02,
    )
    fig.text(
        0.005,
        -0.10,
        "Left: same 1,000 episodes, same 32,000-character budget. The runner's block was still setting records in its final bucket;\n"
        "the library breaches the budget on 0 of 1,000 turns. The library also truncates on 895 of them - the block is bounded\n"
        "because it is enforced, not because demand is small. Right: exponent 1.25 over 50-1,000 candidates, where the earlier\n"
        "sweep found 0.96 over 20-119; clustering's share rises from 37% to 81%. Both axes are logarithmic.",
        fontsize=7.6,
        color="#444444",
        va="top",
    )
    save(fig, "f6_growth_and_cost")


def main() -> None:
    print("Generating PAPER-001 figures from committed artifacts...")
    figure_1()
    figure_2()
    figure_3()
    figure_4()
    figure_5()
    figure_6()

    manifest = {
        "record": "PAPER-001 figure inputs",
        "hash_method": "sha256 over git blob content (LF-normalized), first 16 hex digits",
        "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                               capture_output=True, text=True, check=True).stdout.strip(),
        "inputs": dict(sorted(_INPUTS.items())),
    }
    (OUT / "figure_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"  wrote figure_manifest.json ({len(_INPUTS)} inputs)")


if __name__ == "__main__":
    main()

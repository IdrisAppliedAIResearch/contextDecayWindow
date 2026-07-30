"""Generate reproducible, publication-ready Study 010 figures."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "experiments" / "study_010"
EVAL = STUDY / "evaluation"
FIGURES = STUDY / "figures"
RENDERING_PRE_FIX = (
    ROOT
    / "experiments"
    / "components"
    / "rendering_expansion"
    / "artifacts"
    / "pre_fix"
    / "summary.json"
)

BLUE = "#0072B2"
ORANGE = "#D55E00"
GREEN = "#009E73"
RED = "#C43C39"
INK = "#17212B"
MID = "#596773"
GRID = "#D7DEE4"
PALE = "#E5E9ED"
GOLD = "#E6AB02"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def configure() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 15,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.edgecolor": MID,
            "axes.labelcolor": INK,
            "xtick.color": MID,
            "ytick.color": MID,
            "text.color": INK,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.7,
            "grid.alpha": 0.8,
            "savefig.bbox": "tight",
            "savefig.facecolor": "white",
            "svg.fonttype": "none",
            "svg.hashsalt": "study-010",
        }
    )


def save(fig: plt.Figure, stem: str) -> list[str]:
    FIGURES.mkdir(parents=True, exist_ok=True)
    names = [f"{stem}.svg", f"{stem}.png"]
    fig.savefig(
        FIGURES / names[0],
        metadata={"Creator": "generate_study_010_figures.py", "Date": None},
    )
    fig.savefig(FIGURES / names[1], dpi=300, metadata={"Software": "Matplotlib"})
    plt.close(fig)
    return names


def title(fig: plt.Figure, heading: str, subtitle: str) -> None:
    fig.text(0.08, 0.975, heading, ha="left", va="top", fontsize=12, fontweight="bold")
    fig.text(0.08, 0.91, subtitle, ha="left", va="top", color=MID, fontsize=8.5)


def figure_1() -> list[str]:
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    fig.subplots_adjust(left=0.22, right=0.91, top=0.75, bottom=0.23)
    title(
        fig,
        "Terminal advantage is entirely cross-domain breadth",
        "Post-stop exploratory scores; the confirmatory study remains STOPPED AT G2",
    )
    arms = ["Arm L - LTM", "Arm S - STM"]
    targeted = np.array([12, 12])
    breadth = np.array([2, 0])
    y = np.arange(2)
    ax.barh(y, targeted, color=BLUE, height=0.46, label="Targeted recall")
    ax.barh(y, breadth, left=targeted, color=GREEN, height=0.46, label="Breadth")
    for i, (t, b) in enumerate(zip(targeted, breadth)):
        ax.text(t / 2, i, f"Targeted {t}/12", ha="center", va="center", color="white", weight="bold")
        if b:
            ax.text(t + b / 2, i, f"{b}/2", ha="center", va="center", color="white", weight="bold")
        else:
            ax.text(t + 1, i, "0/2", ha="center", va="center", color=ORANGE, weight="bold", fontsize=8)
        ax.text(14.25, i, f"{t + b}/14", ha="left", va="center", weight="bold")
    ax.set_yticks(y, arms)
    ax.invert_yaxis()
    ax.set_xlim(0, 15.5)
    ax.set_xticks(np.arange(0, 15, 2))
    ax.set_xlabel("Terminal score (maximum 14)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.36), ncol=2, frameon=False)
    fig.text(
        0.08,
        0.855,
        "CONFIRMATORY STATUS: STOPPED AT G2    |    EXPLORATORY BAR 1: RETAIN LTM",
        color=RED,
        weight="bold",
        fontsize=9.5,
    )
    fig.text(0.91, 0.035, "Source: evaluation/rubric_scores.json", ha="right", color=MID, fontsize=7.5)
    return save(fig, "figure_01_terminal_score_decomposition")


def figure_2() -> list[str]:
    scores = read_json(EVAL / "rubric_scores.json")
    mapping = read_json(EVAL / "sealed_mapping.json")["mapping"]
    anonymous_for = {arm: anonymous for anonymous, arm in mapping.items()}
    labels = [f"I{i}" for i in range(1, 10)] + [f"Q{i}" for i in range(1, 15)]
    matrix = np.array(
        [
            [scores["arms"][anonymous_for[arm]]["items"][label]["primary"] for label in labels]
            for arm in ("arm_l", "arm_s")
        ]
    )
    fig, ax = plt.subplots(figsize=(11.2, 3.9))
    fig.subplots_adjust(left=0.12, right=0.98, top=0.69, bottom=0.25)
    title(
        fig,
        "Probe-level scores expose invalid interim items and terminal breadth separation",
        "Red outlines mark probes whose required facts were planted after the probe turn",
    )
    cmap = ListedColormap([PALE, GOLD, GREEN])
    ax.imshow(matrix, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(labels)), labels)
    ax.set_yticks([0, 1], ["Arm L - LTM", "Arm S - STM"])
    ax.tick_params(axis="both", length=0)
    ax.grid(False)
    for row in range(2):
        for col in range(len(labels)):
            value = matrix[row, col]
            ax.text(col, row, f"{value:g}", ha="center", va="center", color="white" if value == 1 else INK, weight="bold")
    for label in ("I2", "I5", "I8"):
        col = labels.index(label)
        ax.add_patch(Rectangle((col - 0.48, -0.48), 0.96, 1.96, fill=False, edgecolor=RED, linewidth=2.2))
    ax.axvline(8.5, color=MID, linewidth=1.3)
    ax.text(4, -0.88, "INTERIM", ha="center", va="center", weight="bold", fontsize=8)
    ax.text(15.5, -0.88, "TERMINAL", ha="center", va="center", weight="bold", fontsize=8)
    fig.text(
        0.12,
        0.065,
        "Bar 3: NOT EVALUABLE. I2, I5, and I8 were capped at 0.5 because required facts were unavailable.",
        color=RED,
        weight="bold",
        fontsize=8.5,
    )
    fig.text(
        0.98,
        0.02,
        "Sources: evaluation/rubric_scores.json; evaluation/probe_fact_order_audit.json",
        ha="right",
        color=MID,
        fontsize=7.5,
    )
    return save(fig, "figure_02_probe_score_matrix")


def figure_3() -> list[str]:
    rows = read_csv(EVAL / "context_performance_curve.csv")
    fig, ax = plt.subplots(figsize=(10, 5.2))
    fig.subplots_adjust(left=0.1, right=0.95, top=0.78, bottom=0.17)
    title(
        fig,
        "Prompt context remained below the 40,000-token monitor over 1,000 turns",
        "Estimated serialized prompt tokens by arm; lines show every recorded turn",
    )
    for arm, color, label in (("L", BLUE, "Arm L - LTM"), ("S", ORANGE, "Arm S - STM")):
        data = [(int(r["turn"]), int(r["estimated_tokens"])) for r in rows if r["arm"] == arm]
        turns, tokens = zip(*data)
        ax.plot(turns, tokens, color=color, linewidth=1.25, label=label)
        peak_turn, peak = max(data, key=lambda item: item[1])
        ax.scatter([peak_turn], [peak], color=color, edgecolor="white", linewidth=0.8, zorder=3)
        ax.annotate(
            f"{label} peak: {peak:,}\nturn {peak_turn}",
            (peak_turn, peak),
            xytext=(-12, 15 if arm == "L" else -42),
            textcoords="offset points",
            ha="right",
            color=color,
            fontsize=8,
            weight="bold",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 1.5},
        )
    ax.axhline(40000, color=RED, linestyle="--", linewidth=1.3, label="40,000-token monitor")
    ax.set_xlim(1, 1000)
    ax.set_ylim(0, 42000)
    ax.set_xticks(np.arange(0, 1001, 100))
    ax.set_yticks(np.arange(0, 40001, 5000), [f"{v // 1000}k" for v in np.arange(0, 40001, 5000)])
    ax.set_xlabel("Conversation turn")
    ax.set_ylabel("Estimated prompt tokens")
    ax.legend(loc="upper left", frameon=False, ncol=3, fontsize=8)
    fig.text(0.95, 0.035, "Source: evaluation/context_performance_curve.csv", ha="right", color=MID, fontsize=7.5)
    return save(fig, "figure_03_context_trajectory")


def figure_4() -> list[str]:
    matrix = read_csv(EVAL / "fact_delivery_matrix.csv")
    delivery = {
        (arm, question): sum(
            r["in_prompt"].lower() == "true"
            for r in matrix
            if r["arm"] == arm and r["question"] == question
        )
        for arm in ("L", "S")
        for question in ("Q13", "Q14")
    }
    replay = read_json(RENDERING_PRE_FIX)
    blocks = {block["block"]: block for block in replay["blocks"]}
    q13 = int(blocks["study_010_q13"]["actual_serialized_chars"])
    q14 = int(blocks["study_010_q14"]["actual_serialized_chars"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.8, 5.2), gridspec_kw={"width_ratios": [0.85, 1.25]})
    fig.subplots_adjust(left=0.08, right=0.97, top=0.75, bottom=0.23, wspace=0.3)
    title(
        fig,
        "Breadth came from LTM blocks that violated the fixed character budget",
        "Delivery is descriptive; no inference was run on exact-cost 32k selections",
    )
    x = np.arange(2)
    width = 0.32
    l_vals = [delivery[("L", q)] for q in ("Q13", "Q14")]
    s_vals = [delivery[("S", q)] for q in ("Q13", "Q14")]
    ax1.bar(x - width / 2, l_vals, width, color=BLUE, label="Arm L - LTM")
    ax1.bar(x + width / 2, s_vals, width, color=ORANGE, label="Arm S - STM")
    for xpos, value, color in [
        (x[0] - width / 2, l_vals[0], BLUE),
        (x[1] - width / 2, l_vals[1], BLUE),
        (x[0] + width / 2, s_vals[0], ORANGE),
        (x[1] + width / 2, s_vals[1], ORANGE),
    ]:
        ax1.text(xpos, value + 0.35, f"{value}/12", ha="center", color=color, weight="bold", fontsize=8)
    ax1.set_title("A  Required breadth pairs in prompt", loc="left", fontsize=10)
    ax1.set_xticks(x, ["Q13", "Q14"])
    ax1.set_ylim(0, 13.5)
    ax1.set_ylabel("Required fact pairs delivered")
    ax1.legend(frameon=False, fontsize=8, loc="upper center")

    names = ["Q13 actual\nserialized LTM", "Q14 actual\nserialized LTM"]
    values = [q13, q14]
    colors = [BLUE, BLUE]
    bars = ax2.bar(np.arange(2), values, color=colors, width=0.58)
    ax2.axhline(32000, color=RED, linestyle="--", linewidth=1.3)
    ax2.set_ylim(0, 60000)
    ax2.set_xticks(np.arange(2), names)
    ax2.set_ylabel("Serialized characters")
    ax2.set_title("B  Actual LTM budget violation", loc="left", fontsize=10)
    ax2.text(
        -0.32,
        32750,
        "Registered LTM budget: 32,000",
        color=RED,
        fontsize=8,
        weight="bold",
    )
    for bar, value in zip(bars, values):
        overage = value - 32000
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            value + 1200,
            f"{value:,}\n+{overage:,}",
            ha="center",
            fontsize=8,
            weight="bold",
        )
    fig.text(
        0.54,
        0.075,
        "The historical 31,991/31,847 values undercharged serialized output; the compact-store projection is withdrawn.",
        color=RED,
        weight="bold",
        fontsize=7.8,
    )
    fig.text(
        0.97,
        0.02,
        "Sources: fact_delivery_matrix.csv; DR-001 pre-fix replay; ERRATA.md",
        ha="right",
        color=MID,
        fontsize=7.5,
    )
    return save(fig, "figure_04_breadth_delivery_and_budget")


def main() -> None:
    configure()
    outputs = figure_1() + figure_2() + figure_3() + figure_4()
    source_paths = [
        EVAL / "rubric_scores.json",
        EVAL / "sealed_mapping.json",
        EVAL / "probe_fact_order_audit.json",
        EVAL / "context_performance_curve.csv",
        EVAL / "fact_delivery_matrix.csv",
        RENDERING_PRE_FIX,
        EVAL / "bakeoff_t1_2_requirement.md",
    ]
    manifest = {
        "generator": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"),
        "formats": ["SVG", "PNG (300 dpi)"],
        "outputs": outputs,
        "sources": [
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in source_paths
        ],
    }
    (FIGURES / "figure_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

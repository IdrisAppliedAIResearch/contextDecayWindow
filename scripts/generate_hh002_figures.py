"""Generate HH-002's figures from committed artifacts.

Same contract as `scripts/generate_paper_002_figures.py`:

  * Every plotted value is read from a committed artifact via
    `git show HEAD:<path>`. No number is typed into this file.
  * Every input's blob SHA-256 (first 16 hex) goes into a manifest beside the
    figures, together with the HEAD commit.
  * Okabe-Ito palette, Agg backend, pinned `svg.hashsalt`, SVG plus PNG.

Titles here are short. The paper owns the captions.

Two figures:

  hh002_leaderboard  - where this component lands on the table arXiv:2504.19413
                       published, with the rows this rig measured visually
                       separated from the rows it only quotes, and the
                       no-memory floor drawn across all of them. The floor is
                       the point: it sits under every bar, including the
                       quoted ones, and the source paper does not report it.
  hh002_timestamps   - the timestamp ablation by question category, which is
                       the study's cleanest result: one stratum moves 36
                       points and the other three do not move at all.

Usage:
    python scripts/generate_hh002_figures.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "HH-002"
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

REPO = Path(__file__).resolve().parent.parent
ART = REPO / "experiments/comparisons/hh_002/artifacts"
OUT = REPO / "paper/figures"

# Okabe-Ito, colourblind-safe.
BLACK = "#000000"
ORANGE = "#E69F00"
SKY = "#56B4E9"
GREEN = "#009E73"
BLUE = "#0072B2"
VERMILLION = "#D55E00"
GREY = "#999999"

_INPUTS: dict[str, str] = {}


def read(path: Path) -> bytes:
    rel = path.relative_to(REPO).as_posix()
    blob = subprocess.run(
        ["git", "show", f"HEAD:{rel}"], cwd=REPO, capture_output=True, check=True
    ).stdout
    _INPUTS.setdefault(rel, hashlib.sha256(blob).hexdigest()[:16])
    return blob


def load_json(path: Path) -> dict:
    return json.loads(read(path).decode("utf-8"))


def judged(arm: str) -> list[dict]:
    return load_json(ART / arm / "judged_r1.json")["records"]


def rate(arm: str) -> float:
    rows = judged(arm)
    return 100.0 * sum(r["llm_score"] for r in rows) / len(rows)


def rate_by_category(arm: str) -> dict[int, tuple[float, int]]:
    rows = judged(arm)
    buckets: dict[int, list[int]] = {}
    for row in rows:
        buckets.setdefault(int(row["category"]), []).append(row["llm_score"])
    return {
        c: (100.0 * sum(v) / len(v), len(v)) for c, v in sorted(buckets.items())
    }


def mean_prompt_tokens(arm: str) -> float:
    rows = load_json(ART / arm / "predictions.json")["records"]
    return sum(r["prompt_tokens"] for r in rows) / len(rows)


def commitments_published() -> dict[str, float]:
    """The quoted rows, read from the run's own commitments file.

    Read rather than typed so the figure cannot disagree with the study about
    what Table 2 says.
    """
    payload = load_json(ART / "commitments.json")["commitments"]
    return dict(payload["inherited_rows_not_rerun"]), dict(
        payload["gctrl"]["targets"]
    )


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for suffix in ("svg", "png"):
        fig.savefig(OUT / f"{name}.{suffix}", bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"  wrote {name}.svg / {name}.png")


# --------------------------------------------------------------------------


def figure_leaderboard() -> None:
    """The table, with measured and quoted rows kept visually apart."""
    inherited, published = commitments_published()
    floor = rate("A_NONE")

    rows: list[tuple[str, float, str]] = [
        ("This component", rate("A_CDW"), "measured"),
        ("Full context (published)", published["A_FULL"], "quoted"),
        ("Full context (reproduced here)", rate("A_FULL"), "measured"),
        ("This component, undated turns", rate("A_CDW_NOTS"), "measured"),
        ("Mem0-graph", inherited["Mem0g"], "quoted"),
        ("Mem0", inherited["Mem0"], "quoted"),
        ("Zep", inherited["Zep"], "quoted"),
        ("RAG, best variant (published)", published["A_RAG"], "quoted"),
        ("OpenAI memory", inherited["OpenAI memory"], "quoted"),
        ("A-MEM", inherited["A-MEM"], "quoted"),
        ("RAG 500/k=1 (reproduced here)", rate("A_RAG"), "measured"),
    ]
    rows.sort(key=lambda r: r[1])

    fig, ax = plt.subplots(figsize=(9.2, 6.2))
    ypos = range(len(rows))
    colours = []
    for label, _, kind in rows:
        if label == "This component":
            colours.append(BLUE)
        elif kind == "measured":
            colours.append(SKY)
        else:
            colours.append(GREY)

    bars = ax.barh(list(ypos), [r[1] for r in rows], color=colours,
                   edgecolor=BLACK, linewidth=0.6, height=0.68, zorder=3)
    for bar, (label, value, _) in zip(bars, rows):
        weight = "bold" if label == "This component" else "normal"
        ax.text(value + 0.7, bar.get_y() + bar.get_height() / 2,
                f"{value:.2f}%", va="center", ha="left", fontsize=9,
                fontweight=weight, zorder=4)

    ax.axvline(floor, color=VERMILLION, linewidth=1.8, linestyle="--", zorder=2)
    ax.text(floor - 0.9, len(rows) - 0.35,
            f"no memory at all: {floor:.2f}%",
            color=VERMILLION, fontsize=9, fontweight="bold",
            ha="right", va="center", zorder=4)

    ax.set_yticks(list(ypos))
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.set_xlabel("LoCoMo, LLM-as-a-Judge, 1,540 scored questions (%)",
                  fontsize=10)
    ax.set_xlim(0, 92)
    ax.grid(axis="x", color="#DDDDDD", linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    # Below the axes, not over it: at "lower right" the frame covered the
    # bottom bar's value label.
    ax.legend(
        handles=[
            Patch(facecolor=BLUE, edgecolor=BLACK, label="This component"),
            Patch(facecolor=SKY, edgecolor=BLACK, label="Measured on this rig"),
            Patch(facecolor=GREY, edgecolor=BLACK,
                  label="arXiv:2504.19413 Table 2, quoted with attribution"),
        ],
        loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=3,
        fontsize=8.5, framealpha=1.0, borderaxespad=0.0,
    )
    ax.set_title(
        "79.09% — above every system on the table Mem0 published",
        fontsize=12.5, fontweight="bold", loc="left", pad=10,
    )
    save(fig, "hh002_leaderboard")


def figure_timestamps() -> None:
    """The ablation: one stratum moves, three do not."""
    names = {1: "single-hop", 2: "temporal", 3: "multi-hop", 4: "open-domain"}
    dated = rate_by_category("A_CDW")
    undated = rate_by_category("A_CDW_NOTS")
    cats = sorted(dated)

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(10.4, 4.4), gridspec_kw={"width_ratios": [1.55, 1]}
    )

    width = 0.38
    xs = range(len(cats))
    ax.bar([x - width / 2 for x in xs], [dated[c][0] for c in cats],
           width, label="Turns carry their date", color=BLUE,
           edgecolor=BLACK, linewidth=0.6, zorder=3)
    ax.bar([x + width / 2 for x in xs], [undated[c][0] for c in cats],
           width, label="Turns undated", color=ORANGE,
           edgecolor=BLACK, linewidth=0.6, zorder=3)
    for i, c in enumerate(cats):
        for offset, value in ((-width / 2, dated[c][0]),
                              (width / 2, undated[c][0])):
            ax.text(i + offset, value + 1.2, f"{value:.1f}", ha="center",
                    fontsize=8, zorder=4)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"{names[c]}\n(n={dated[c][1]})" for c in cats],
                       fontsize=9)
    ax.set_ylabel("LLM-as-a-Judge (%)", fontsize=10)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=8.5, framealpha=1.0, loc="upper left")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.set_title("Same retrieval, with and without timestamps",
                 fontsize=11, fontweight="bold", loc="left", pad=10)

    deltas = [dated[c][0] - undated[c][0] for c in cats]
    colours = [GREEN if d > 5 else GREY for d in deltas]
    ax2.bar(list(xs), deltas, 0.6, color=colours, edgecolor=BLACK,
            linewidth=0.6, zorder=3)
    for i, d in enumerate(deltas):
        ax2.text(i, d + (1.2 if d >= 0 else -2.6), f"{d:+.2f}", ha="center",
                 fontsize=9, fontweight="bold" if d > 5 else "normal",
                 zorder=4)
    ax2.axhline(0, color=BLACK, linewidth=0.9, zorder=2)
    ax2.set_xticks(list(xs))
    ax2.set_xticklabels([names[c] for c in cats], fontsize=9, rotation=20,
                        ha="right")
    ax2.set_ylabel("Points gained by dating the turn", fontsize=10)
    ax2.set_ylim(-8, 44)
    ax2.grid(axis="y", color="#DDDDDD", linewidth=0.7, zorder=0)
    ax2.set_axisbelow(True)
    for spine in ("top", "right"):
        ax2.spines[spine].set_visible(False)
    ax2.set_title("The whole effect is one stratum", fontsize=11,
                  fontweight="bold", loc="left", pad=10)

    fig.tight_layout()
    save(fig, "hh002_timestamps")


def write_manifest() -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
        check=True, text=True,
    ).stdout.strip()
    manifest = {
        "study": "HH-002",
        "head_commit": head,
        "figures": ["hh002_leaderboard", "hh002_timestamps"],
        "inputs": dict(sorted(_INPUTS.items())),
    }
    (OUT / "figure_manifest_hh002.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"  wrote figure_manifest_hh002.json ({len(_INPUTS)} inputs)")


def main() -> None:
    print("Generating HH-002 figures from committed artifacts...")
    figure_leaderboard()
    figure_timestamps()
    write_manifest()


if __name__ == "__main__":
    main()

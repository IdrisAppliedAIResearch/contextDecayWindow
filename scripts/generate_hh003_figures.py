"""Generate HH-003 figures from committed artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

os.environ.setdefault("SOURCE_DATE_EPOCH", "0")

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "HH-003"
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

REPO = Path(__file__).resolve().parent.parent
ART = REPO / "experiments/comparisons/hh_003/artifacts/run"
OUT = REPO / "paper/figures"

BLACK = "#000000"
ORANGE = "#E69F00"
SKY = "#56B4E9"
BLUE = "#0072B2"
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
    return 100.0 * sum(row["llm_score"] for row in rows) / len(rows)


def rate_by_category(arm: str) -> dict[int, tuple[float, int]]:
    buckets: dict[int, list[int]] = {}
    for row in judged(arm):
        buckets.setdefault(int(row["category"]), []).append(row["llm_score"])
    return {
        category: (100.0 * sum(values) / len(values), len(values))
        for category, values in sorted(buckets.items())
    }


def quoted_rows() -> dict[str, float]:
    text = read(REPO / "paper/notes/COMPETITIVE_LANDSCAPE.md").decode("utf-8")
    wanted = {
        "Mem0": r"\| Mem0 \| LoCoMo, LLM-as-a-Judge \(J\) \| \*\*([\d.]+)%\*\*",
        "Mem0-graph": r"\| Mem0ᵍ \(graph\) \| LoCoMo, J \| \*\*([\d.]+)%\*\*",
        "Zep": r"\| Zep \| LoCoMo, J \| \*\*([\d.]+)%\*\*",
        "RAG, 512/k=1": r"\| RAG \(512 tokens, k=1\) \| LoCoMo, J \| \*\*([\d.]+)%\*\*",
        "Full context": r"full-context ceiling of ([\d.]+)%",
    }
    result: dict[str, float] = {}
    for label, pattern in wanted.items():
        match = re.search(pattern, text)
        if match is None:
            raise SystemExit(f"citation record no longer matches {label!r}")
        result[label] = float(match.group(1))
    return result


def save(fig, name: str) -> None:
    for suffix in ("svg", "png"):
        path = OUT / f"{name}.{suffix}"
        fig.savefig(path, bbox_inches="tight", dpi=200)
        if suffix == "svg":
            text = path.read_text(encoding="utf-8")
            path.write_text(
                "\n".join(line.rstrip() for line in text.splitlines()) + "\n",
                encoding="utf-8", newline="\n",
            )
    plt.close(fig)


def figure_leaderboard() -> None:
    quoted = quoted_rows()
    rows = [
        ("Episodic-chat + ASPECT", rate("A_EPISODIC_ASPECT"), "current_aspect"),
        ("Episodic-chat", rate("A_EPISODIC"), "current_default"),
        ("Full context", quoted["Full context"], "quoted"),
        ("Mem0-graph", quoted["Mem0-graph"], "quoted"),
        ("Mem0", quoted["Mem0"], "quoted"),
        ("Zep", quoted["Zep"], "quoted"),
        ("RAG, 512/k=1", quoted["RAG, 512/k=1"], "quoted"),
    ]
    rows.sort(key=lambda row: row[1])
    colours = {
        "current_aspect": ORANGE, "current_default": BLUE, "quoted": GREY
    }

    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    bars = ax.barh(
        range(len(rows)), [row[1] for row in rows],
        color=[colours[row[2]] for row in rows], edgecolor=BLACK,
        linewidth=0.6, height=0.68, zorder=3,
    )
    for bar, (label, value, kind) in zip(bars, rows):
        ax.text(
            value + 0.6, bar.get_y() + bar.get_height() / 2, f"{value:.2f}%",
            va="center", fontsize=9, fontweight="bold" if kind != "quoted" else "normal",
        )
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([row[0] for row in rows], fontsize=9)
    ax.set_xlim(45, 84)
    ax.set_xlabel("LoCoMo, LLM-as-a-Judge, 1,540 scored questions (%)")
    ax.grid(axis="x", color="#DDDDDD", linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(
        handles=[
            Patch(facecolor=BLUE, edgecolor=BLACK, label="Episodic-chat"),
            Patch(facecolor=ORANGE, edgecolor=BLACK, label="Episodic-chat + ASPECT"),
            Patch(facecolor=GREY, edgecolor=BLACK, label="Published row, quoted"),
        ],
        loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, fontsize=8.5,
    )
    ax.set_title(
        "Deployed episodic-chat on the published LoCoMo axis",
        fontsize=12.5, fontweight="bold", loc="left", pad=10,
    )
    save(fig, "hh003_leaderboard")


def figure_categories() -> None:
    names = {1: "single-hop", 2: "temporal", 3: "multi-hop", 4: "open-domain"}
    default = rate_by_category("A_EPISODIC")
    aspect = rate_by_category("A_EPISODIC_ASPECT")
    categories = sorted(default)
    width = 0.36

    fig, (ax, delta_ax) = plt.subplots(
        1, 2, figsize=(10.4, 4.4), gridspec_kw={"width_ratios": [1.65, 1]}
    )
    xs = list(range(len(categories)))
    ax.bar([x - width / 2 for x in xs], [default[c][0] for c in categories],
           width, label="Episodic-chat", color=BLUE, edgecolor=BLACK, linewidth=0.6)
    ax.bar([x + width / 2 for x in xs], [aspect[c][0] for c in categories],
           width, label="Episodic-chat + ASPECT", color=ORANGE, edgecolor=BLACK, linewidth=0.6)
    for x, category in zip(xs, categories):
        for offset, value in ((-width / 2, default[category][0]), (width / 2, aspect[category][0])):
            ax.text(x + offset, value + 1.2, f"{value:.1f}", ha="center", fontsize=8)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{names[c]}\n(n={default[c][1]})" for c in categories], fontsize=9)
    ax.set_ylabel("LLM-as-a-Judge (%)")
    ax.set_ylim(0, 100)
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.7)
    ax.legend(fontsize=8.5, loc="upper left")
    ax.set_title("Episodic-chat and Episodic-chat + ASPECT by question category", fontsize=11, fontweight="bold", loc="left")

    deltas = [aspect[c][0] - default[c][0] for c in categories]
    delta_ax.bar(xs, deltas, 0.6, color=[ORANGE if value > 0 else GREY for value in deltas], edgecolor=BLACK, linewidth=0.6)
    for x, value in zip(xs, deltas):
        delta_ax.text(x, value + (0.35 if value >= 0 else -0.65), f"{value:+.2f}", ha="center", fontsize=9)
    delta_ax.axhline(0, color=BLACK, linewidth=0.9)
    delta_ax.set_xticks(xs)
    delta_ax.set_xticklabels([names[c] for c in categories], rotation=20, ha="right", fontsize=9)
    delta_ax.set_ylabel("ASPECT minus default (points)")
    delta_ax.set_ylim(-2, 8)
    delta_ax.grid(axis="y", color="#DDDDDD", linewidth=0.7)
    delta_ax.set_title("Primary-score difference", fontsize=11, fontweight="bold", loc="left")
    for axis in (ax, delta_ax):
        axis.set_axisbelow(True)
        for spine in ("top", "right"):
            axis.spines[spine].set_visible(False)
    fig.tight_layout()
    save(fig, "hh003_aspect_categories")


def write_manifest() -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
        check=True, text=True,
    ).stdout.strip()
    manifest = {
        "study": "HH-003", "head_commit": head,
        "figures": ["hh003_leaderboard", "hh003_aspect_categories"],
        "inputs": dict(sorted(_INPUTS.items())),
    }
    (OUT / "figure_manifest_hh003.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> None:
    figure_leaderboard()
    figure_categories()
    write_manifest()


if __name__ == "__main__":
    main()

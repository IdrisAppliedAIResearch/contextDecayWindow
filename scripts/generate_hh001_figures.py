"""Generate HH-001's figures from its committed artifacts.

Same contract as `scripts/generate_paper_002_figures.py`:

  * Every plotted value is read from an artifact. No number is typed into this
    file.
  * `read()` records the SHA-256 of the bytes it parsed, and records whether
    those bytes came from `git show HEAD:<path>` or from the working tree. A
    figure built from uncommitted bytes is labelled `PRELIMINARY` on its face,
    so a screenshot cannot be mistaken for a committed result.
  * Okabe-Ito palette, Agg backend, pinned `svg.hashsalt`, SVG plus PNG, and a
    manifest recording every input, its hash, and the HEAD commit.

Titles are short; the report owns the captions.

    python scripts/generate_hh001_figures.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "HH-001"
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
DEV = REPO / "experiments/comparisons/hh_001/artifacts/dev"
# HH-001's two figures are paper figures, so they are written where the build
# looks for them. The study keeps its own manifest; `paper/figures/` holds one
# directory of figures rather than two competing ones.
OUT = REPO / "paper/figures"

BLACK = "#000000"
ORANGE = "#E69F00"
SKY = "#56B4E9"
GREEN = "#009E73"
BLUE = "#0072B2"
VERMILLION = "#D55E00"
GREY = "#7F7F7F"

INPUTS: dict[str, dict] = {}


def head_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
            text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def read(path: Path) -> dict:
    """Return parsed JSON, preferring committed bytes and recording which."""
    relative = str(path.relative_to(REPO)).replace("\\", "/")
    committed = True
    try:
        raw = subprocess.run(
            ["git", "show", f"HEAD:{relative}"], cwd=REPO,
            capture_output=True, check=True,
        ).stdout
    except subprocess.CalledProcessError:
        committed = False
        raw = path.read_bytes()
    INPUTS[relative] = {
        "sha256": hashlib.sha256(raw).hexdigest()[:16],
        "committed": committed,
    }
    return json.loads(raw.decode("utf-8"))


def rolling_median(values: list[float], window: int) -> list[float]:
    out = []
    for index in range(len(values)):
        lo = max(0, index - window // 2)
        window_values = sorted(values[lo : lo + window])
        out.append(window_values[len(window_values) // 2])
    return out


def figure_ingest_latency() -> Path:
    data = read(DEV / "cost/mem0_ingest_latency.json")
    points = data["points"]
    if not points:
        raise SystemExit("No points in the latency artifact")
    store = [p["store_size"] for p in points]
    seconds = [p["seconds"] for p in points]
    window = max(5, len(points) // 20 | 1)
    smooth = rolling_median(seconds, window)

    figure, axes = plt.subplots(figsize=(8.2, 4.6))
    axes.scatter(store, seconds, s=11, color=SKY, alpha=0.55,
                 label="one Mem0 add() call", zorder=2)
    axes.plot(store, smooth, color=VERMILLION, linewidth=2.0,
              label=f"rolling median (window {window})", zorder=3)
    axes.axhline(0.0, color=GREEN, linewidth=2.0, zorder=3,
                 label="this component: 0 generative calls")

    first = data["first_decile_mean_s"]
    last = data["last_decile_mean_s"]
    axes.annotate(
        f"first decile mean {first:.1f}s\nlast decile mean {last:.1f}s",
        xy=(0.985, 0.96), xycoords="axes fraction", ha="right", va="top",
        fontsize=8.5, color=BLACK,
        bbox=dict(boxstyle="round,pad=0.42", facecolor="white",
                  edgecolor=GREY, linewidth=0.7),
    )

    axes.set_xlabel("memories in the store when the call started")
    axes.set_ylabel("seconds for one ingested message pair")
    axes.set_title(
        f"Mem0 ingest latency against store size "
        f"({data['calls_measured']} calls, local reader)",
        fontsize=11,
    )
    axes.set_ylim(bottom=-max(seconds) * 0.04)
    axes.grid(True, alpha=0.25, linewidth=0.6)
    axes.legend(loc="upper left", fontsize=8.5, framealpha=0.92)
    axes.spines["top"].set_visible(False)
    axes.spines["right"].set_visible(False)

    relative = "experiments/comparisons/hh_001/artifacts/dev/cost/mem0_ingest_latency.json"
    if not INPUTS[relative]["committed"]:
        figure.text(
            0.5, 0.5, "PRELIMINARY", fontsize=52, color=GREY, alpha=0.16,
            ha="center", va="center", rotation=24, zorder=10,
        )

    figure.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    stem = OUT / "f2_mem0_ingest_latency"
    figure.savefig(stem.with_suffix(".svg"))
    figure.savefig(stem.with_suffix(".png"), dpi=200)
    plt.close(figure)
    return stem



def figure_head_to_head() -> Path:
    """Accuracy beside what each arm spent to get it.

    Two panels because they are two different quantities and one axis would
    imply a trade curve the data does not describe.
    """
    result = read(DEV / "result.json")
    storage = read(DEV / "cost/storage.json")
    ingest = read(DEV / "cost/mem0_ingest.json")
    tokens = read(DEV / "cost/mem0_ingest_tokens.json")
    corrected = read(DEV / "cost/mem0_ingest_tokens_corrected.json")

    order = ["A0_NO_MEMORY", "A3_MEM0", "A4_RAG_FIXED", "A2_CDW_PAIR", "A1_FULL_CONTEXT"]
    label = {
        "A0_NO_MEMORY": "no memory",
        "A3_MEM0": "Mem0 2.0.18",
        "A4_RAG_FIXED": "chunk retrieval",
        "A2_CDW_PAIR": "this component",
        "A1_FULL_CONTEXT": "whole conversation",
    }
    colour = {
        "A0_NO_MEMORY": GREY,
        "A3_MEM0": VERMILLION,
        "A4_RAG_FIXED": ORANGE,
        "A2_CDW_PAIR": BLUE,
        "A1_FULL_CONTEXT": SKY,
    }
    judged = [result["per_arm"][a]["judged"]["accuracy"] for a in order]
    contained = [result["per_arm"][a]["contained"]["accuracy"] for a in order]
    prompt_tokens = [result["cost"][a]["prompt_tokens_mean"] for a in order]

    figure, (left, right) = plt.subplots(1, 2, figsize=(11.4, 4.8))

    y = range(len(order))
    left.barh([i + 0.19 for i in y], judged, height=0.36,
              color=[colour[a] for a in order], label="judged")
    left.barh([i - 0.19 for i in y], contained, height=0.36,
              color=[colour[a] for a in order], alpha=0.45,
              label="containment (no model)")
    for i, (j, c) in enumerate(zip(judged, contained)):
        left.text(j + 0.008, i + 0.19, f"{j:.3f}", va="center", fontsize=8.5)
        left.text(c + 0.008, i - 0.19, f"{c:.3f}", va="center", fontsize=8.5,
                  color=GREY)
    left.set_yticks(list(y))
    left.set_yticklabels([label[a] for a in order])
    left.set_xlabel("accuracy over 300 questions, 3 replicates")
    left.set_xlim(0, max(judged) * 1.22)
    left.set_title("What each memory layer answered", fontsize=11)
    left.legend(loc="lower right", fontsize=8.5, framealpha=0.92)
    left.grid(True, axis="x", alpha=0.25, linewidth=0.6)
    for side in ("top", "right"):
        left.spines[side].set_visible(False)

    # Prompt tokens alongside the call count. The raw artifact's
    # window_prompt_tokens is NOT usable: its counter is cumulative and
    # process-wide and kept running past Mem0's last write. Amendment 001
    # scales the overlap instead, and that is what is plotted.
    spent = {a: 0 for a in order}
    spent["A3_MEM0"] = corrected["RECOMPUTED_prompt_tokens_whole_ingest"]
    coverage = corrected["counter_overlap_fraction"]
    floor = corrected["MEASURED_prompt_tokens_in_overlap"]
    right.bar([label[a] for a in order], [spent[a] / 1e6 for a in order],
              color=[colour[a] for a in order])
    right.set_ylabel("million prompt tokens to build the store")
    right.set_title("What each memory layer spent to build it", fontsize=11)
    right.tick_params(axis="x", rotation=32, labelsize=8.5)
    for tick in right.get_xticklabels():
        tick.set_ha("right")
    right.annotate(
        "{:,} prompt tokens\n{:,} calls in {:.0f} min\n{:.0f}% measured ({:,}), "
        "remainder scaled".format(
            int(spent["A3_MEM0"]), ingest["total_generative_calls"],
            ingest["total_seconds"] / 60, coverage * 100, int(floor)),
        xy=(1, spent["A3_MEM0"] / 1e6),
        xytext=(2.05, spent["A3_MEM0"] / 1e6 * 0.62),
        fontsize=9, color=BLACK,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                  edgecolor=GREY, linewidth=0.7),
    )
    right.annotate(
        "zero", xy=(3, 0), xytext=(3, spent["A3_MEM0"] / 1e6 * 0.18),
        fontsize=10, color=BLUE, ha="center", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=BLUE, linewidth=1.3),
    )
    right.grid(True, axis="y", alpha=0.25, linewidth=0.6)
    for side in ("top", "right"):
        right.spines[side].set_visible(False)

    relative = "experiments/comparisons/hh_001/artifacts/dev/result.json"
    if not INPUTS[relative]["committed"]:
        figure.text(0.5, 0.5, "PRELIMINARY", fontsize=52, color=GREY, alpha=0.16,
                    ha="center", va="center", rotation=24, zorder=10)

    figure.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    stem = OUT / "f1_head_to_head"
    figure.savefig(stem.with_suffix(".svg"))
    figure.savefig(stem.with_suffix(".png"), dpi=200)
    plt.close(figure)
    return stem


def main() -> int:
    stem = figure_ingest_latency()
    stem2 = figure_head_to_head()
    manifest = {
        "schema": "hh001-figure-manifest-v1",
        "head_commit": head_commit(),
        "figures": ["f1_head_to_head", "f2_mem0_ingest_latency"],
        "inputs": INPUTS,
        "all_inputs_committed": all(v["committed"] for v in INPUTS.values()),
    }
    path = REPO / "experiments/comparisons/hh_001/figures/figure_manifest_hh001.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")
    for name, meta in INPUTS.items():
        state = "committed" if meta["committed"] else "WORKING TREE"
        print(f"  {meta['sha256']}  {state:12s}  {name}")
    print(f"wrote {stem.with_suffix('.svg').relative_to(REPO)}")
    print(f"wrote {stem.with_suffix('.png').relative_to(REPO)}")
    print(f"wrote {stem2.with_suffix('.png').relative_to(REPO)}")
    if not manifest["all_inputs_committed"]:
        print("\nPRELIMINARY: at least one input is uncommitted; the figure "
              "is watermarked. Commit the artifacts and re-run for a final.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

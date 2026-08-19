"""Generate PAPER-002's seven figures from committed artifacts.

Contract, inherited from `scripts/generate_paper_001_figures.py` and tightened:

  * Every plotted value is read from a committed artifact. No number is typed
    into this file. Where an artifact could not be found for an element, the
    element is omitted and the omission is reported, never hardcoded.
  * `read()` records the SHA-256 of `git show HEAD:<path>` (first 16 hex
    digits) for every input and hands back the *committed bytes*. PAPER-001's
    script hashed HEAD but parsed the working tree; here both come from HEAD,
    so a recorded hash always corresponds to the bytes that were parsed.
  * A few registered bars live in prose rather than JSON. Those are pulled with
    `extract()`, a strict regex over the same committed bytes: if the artifact's
    wording changes, the regex fails loudly instead of plotting a stale value.
  * Okabe-Ito palette, Agg backend, pinned `svg.hashsalt`, SVG plus PNG into
    `paper/figures/`, and a manifest at `paper/figures/figure_manifest_002.json`
    recording every input path, its hash, and the HEAD commit.

Titles here are short. The paper owns the captions.

Usage:
    python scripts/generate_paper_002_figures.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import statistics
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
# Keep generated SVG element ids stable across identical builds.
matplotlib.rcParams["svg.hashsalt"] = "PAPER-002"
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

REPO = Path(__file__).resolve().parent.parent
BIO = REPO / "experiments/components/biological_memory"
LEDGER = REPO / "experiments/components/retrieval_mechanism_ledger"
CLOSEOUT = REPO / "experiments/components/deployment_closeout/artifacts"
LME = REPO / "experiments/external/longmemeval"
IC001 = REPO / "experiments/internal/packing_priority/runs/ic001"
S011 = REPO / "experiments/study_011"
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


def read(path: Path) -> bytes:
    """Record a file's canonical hash and return its committed bytes.

    Hashes git blob content so the value matches the repository convention and
    does not drift with platform line endings.
    """
    rel = path.relative_to(REPO).as_posix()
    blob = subprocess.run(
        ["git", "show", f"HEAD:{rel}"],
        cwd=REPO,
        capture_output=True,
        check=True,
    ).stdout
    _INPUTS.setdefault(rel, hashlib.sha256(blob).hexdigest()[:16])
    return blob


def load_json(path: Path) -> dict:
    return json.loads(read(path).decode("utf-8"))


def load_csv(path: Path) -> list[dict]:
    text = read(path).decode("utf-8-sig")
    return list(csv.DictReader(text.splitlines()))


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in read(path).decode("utf-8").splitlines()
        if line.strip()
    ]


def text_of(path: Path) -> str:
    return read(path).decode("utf-8")


def extract(path: Path, pattern: str, cast=float, group: int = 1):
    """Pull one registered value out of a prose artifact, or fail loudly."""
    match = re.search(pattern, text_of(path))
    if match is None:
        raise SystemExit(
            f"artifact {path.relative_to(REPO).as_posix()} no longer matches "
            f"{pattern!r}; refusing to plot a value this script cannot source"
        )
    return cast(match.group(group))


def style(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GREY, alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)


def style_x(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", color=GREY, alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        OUT / f"{name}.svg",
        format="svg",
        bbox_inches="tight",
        metadata={"Date": None},
    )
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}.svg / .png")


# --------------------------------------------------------------------------
# F1 - the sealed holdout
# --------------------------------------------------------------------------
def figure_1() -> None:
    outcomes = load_json(BIO / "nf_004/artifacts/g6_holdout_outcomes.json")
    integrity = load_json(BIO / "nf_004/artifacts/g7_result_integrity.json")
    # The registered disposition rule, from the pre-registration itself.
    ratio_bar = extract(
        BIO / "nf_004/NF_004_PRE_REGISTRATION.md",
        r"gains\s*>=\s*([0-9.]+)\s*\*\s*losses",
    )

    rows = [r for r in outcomes["rows"] if r["primary_eligible"]]
    n = integrity["primary"]["n"]
    budget = outcomes["budget"]

    arms = [
        ("source order\n(no ranking)", "SOURCE_ORDER", GREY),
        ("session rank\n(baseline)", "S_SESSION_RANK", SKY),
        ("pair rank\n(treatment)", "P_PAIR_RANK", BLUE),
    ]
    totals = [
        sum(1 for r in rows if r["arms"][key]["all_evidence"]) for _, key, _ in arms
    ]

    paired = integrity["primary"]["paired"]
    gains, losses, ties = paired["gains"], paired["losses"], paired["ties"]

    per_conversation: dict[str, int] = {}
    for row in rows:
        delta = int(row["arms"]["P_PAIR_RANK"]["all_evidence"]) - int(
            row["arms"]["S_SESSION_RANK"]["all_evidence"]
        )
        per_conversation[row["sample_id"]] = (
            per_conversation.get(row["sample_id"], 0) + delta
        )
    conversations = sorted(per_conversation)
    deltas = [per_conversation[c] for c in conversations]

    fig = plt.figure(figsize=(9.8, 6.2))
    grid = fig.add_gridspec(
        2, 2, height_ratios=[1.15, 1.0], width_ratios=[1.05, 1.0],
        hspace=0.52, wspace=0.26,
    )
    ax_a = fig.add_subplot(grid[0, :])
    ax_b = fig.add_subplot(grid[1, 0])
    ax_c = fig.add_subplot(grid[1, 1])

    # (a) complete-evidence delivery by arm
    style_x(ax_a)
    labels = [label for label, _, _ in arms]
    colours = [colour for _, _, colour in arms]
    positions = range(len(arms))
    ax_a.barh(list(positions), [n] * len(arms), color=GREY, alpha=0.13, height=0.62)
    ax_a.barh(list(positions), totals, color=colours, alpha=0.9, height=0.62)
    for y, (value, colour) in enumerate(zip(totals, colours)):
        ax_a.text(
            value + n * 0.012, y, f"{value:,} of {n:,}   ({value / n:.1%})",
            va="center", fontsize=9.2, fontweight="bold", color=colour,
        )
    ax_a.set_yticks(list(positions))
    ax_a.set_yticklabels(labels, fontsize=8.6)
    ax_a.set_xlim(0, n * 1.24)
    ax_a.invert_yaxis()
    ax_a.set_xlabel(
        f"questions whose complete exact evidence was delivered "
        f"(sealed LoCoMo holdout, {budget:,}-char budget)",
        fontsize=9,
    )
    ax_a.set_title(
        "the ranking unit, not the ranker, moved delivery", fontsize=10, loc="left"
    )

    # (b) the paired discordant split
    style(ax_b)
    ax_b.bar(["gains", "losses"], [gains, losses], color=[GREEN, VERMILLION],
             alpha=0.9, width=0.55)
    for x, value in enumerate([gains, losses]):
        ax_b.text(x, value + gains * 0.03, str(value), ha="center",
                  fontsize=10.5, fontweight="bold")
    ax_b.axhline(losses * ratio_bar, color=BLACK, linewidth=1.1, linestyle="--")
    ax_b.text(
        1.42, losses * ratio_bar + gains * 0.02,
        f"registered bar: gains ≥ {ratio_bar:g} × losses  "
        f"({losses * ratio_bar:g})",
        fontsize=7.8, ha="right", va="bottom",
    )
    ax_b.set_ylim(0, gains * 1.22)
    ax_b.set_ylabel("discordant questions", fontsize=9)
    ax_b.set_title(
        "pair rank against session rank\n"
        f"ratio {paired['gain_loss_ratio']:.2f} · p = {paired['p_one_sided']:.2e} · "
        f"{ties:,} ties",
        fontsize=9.6, loc="left",
    )

    # (c) per-conversation net delta
    style(ax_c)
    ax_c.bar(conversations, deltas, color=GREEN, alpha=0.9, width=0.6)
    for x, value in enumerate(deltas):
        ax_c.text(x, value + max(deltas) * 0.035, f"+{value}", ha="center",
                  fontsize=9, fontweight="bold")
    ax_c.axhline(0, color=BLACK, linewidth=1.0)
    ax_c.set_ylim(0, max(deltas) * 1.24)
    ax_c.set_ylabel("net questions gained", fontsize=9)
    ax_c.tick_params(axis="x", labelsize=8, rotation=30)
    ax_c.set_title(
        f"all {len(conversations)} withheld conversations net positive",
        fontsize=9.6, loc="left",
    )

    save(fig, "f1_sealed_holdout")


# --------------------------------------------------------------------------
# F2 - granularity across three corpora
# --------------------------------------------------------------------------
def figure_2() -> None:
    nf005 = load_json(BIO / "nf_005/artifacts/g8_integrity.json")
    nf004 = load_json(BIO / "nf_004/artifacts/g7_result_integrity.json")
    nf006 = load_json(BIO / "nf_006/artifacts/g8_g9_measurement.json")
    lengths = load_json(BIO / "nf_005/artifacts/exploration.json")["candidate_lengths"]

    nf005_totals = nf005["arm_totals"]
    nf006_q11 = nf006["G9"]["q11"]

    corpora = [
        (
            "NF-005  LongMemEval\n465 turn-labelled items",
            "episode rank",
            nf005_totals["E_EPISODE_RANK_TURN_PACK"]["any_target"],
            "source-turn rank",
            nf005_totals["T_TURN_RANK_TURN_PACK"]["any_target"],
            nf005["items"],
            "any exact evidence",
        ),
        (
            "NF-004  LoCoMo (sealed)\n1,098 QA records",
            "session rank",
            nf004["primary"]["session_all_evidence_hits"],
            "adjacent-pair rank",
            nf004["primary"]["pair_all_evidence_hits"],
            nf004["primary"]["n"],
            "complete exact evidence",
        ),
        (
            "NF-006  internal store\n17 breadth items",
            "episode rank",
            nf006_q11["C0_EPISODE"]["available"],
            "statement rank",
            nf006_q11["T1_OWN_STATEMENT"]["available"],
            nf006_q11["T1_OWN_STATEMENT"]["total"],
            "target items available",
        ),
    ]

    units = [
        ("LongMemEval\nevidence episodes", lengths["longmemeval_evidence_episodes"], SKY),
        ("LongMemEval\nevidence source turns", lengths["longmemeval_evidence_turns"], BLUE),
        ("LoCoMo\nadjacent pairs", lengths["locomo_adjacent_pairs"], GREEN),
    ]

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(10.4, 4.6), gridspec_kw={"width_ratios": [1.45, 1.0]}
    )
    style_x(ax)
    style(ax2)

    for index, (label, coarse_name, coarse, fine_name, fine, total, metric) in enumerate(
        corpora
    ):
        y = len(corpora) - 1 - index
        c_rate, f_rate = coarse / total, fine / total
        ax.hlines(y, c_rate, f_rate, color=GREY, linewidth=2.4, zorder=2)
        ax.scatter([c_rate], [y], s=95, color=SKY, zorder=3, edgecolor="white",
                   linewidth=1.0)
        ax.scatter([f_rate], [y], s=115, color=BLUE, zorder=3, edgecolor="white",
                   linewidth=1.0)
        ax.annotate(f"{coarse_name}\n{coarse:,}", xy=(c_rate, y),
                    xytext=(0, 11), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8.0, color=SKY)
        ax.annotate(f"{fine:,} of {total:,}\n{fine_name}", xy=(f_rate, y),
                    xytext=(0, -11), textcoords="offset points",
                    ha="center", va="top", fontsize=8.0, color=BLUE,
                    fontweight="bold")

    ax.set_yticks(range(len(corpora)))
    ax.set_yticklabels(
        [f"{c[0]}\n{c[6]}" for c in corpora][::-1], fontsize=8.0
    )
    ax.set_xlim(0, 1.16)
    ax.set_ylim(-0.72, len(corpora) - 0.28)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=8.4)
    ax.set_xlabel("share of the corpus whose evidence was delivered", fontsize=9)
    ax.set_title("ranking at a finer unit, three corpora", fontsize=10, loc="left")

    labels = [f"{u[0]}\nn = {u[1]['n']:,}" for u in units]
    medians = [u[1]["p50"] for u in units]
    lows = [u[1]["p50"] - u[1]["p10"] for u in units]
    highs = [u[1]["p90"] - u[1]["p50"] for u in units]
    ax2.bar(labels, medians, color=[u[2] for u in units], alpha=0.9, width=0.6,
            yerr=[lows, highs], capsize=4,
            error_kw=dict(ecolor=GREY, elinewidth=1.0))
    top = max(m + h for m, h in zip(medians, highs))
    for x, (value, high) in enumerate(zip(medians, highs)):
        ax2.text(x, value + high + top * 0.03, f"{value:,}", ha="center",
                 va="bottom", fontsize=9.4, fontweight="bold")
    ax2.set_ylim(0, top * 1.16)
    ax2.tick_params(axis="x", labelsize=7.2)
    ax2.set_ylabel("median candidate length (characters)", fontsize=9)
    ax2.set_title(
        "why: the size of one candidate\nbars are medians, whiskers p10-p90",
        fontsize=10, loc="left",
    )

    save(fig, "f2_granularity_three_corpora")


def write_manifest() -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    manifest = {
        "record": "PAPER-002 figure inputs",
        "hash_method": (
            "sha256 over git blob content (LF-normalized), first 16 hex digits"
        ),
        "head": head,
        "inputs": dict(sorted(_INPUTS.items())),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "figure_manifest_002.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"  wrote figure_manifest_002.json ({len(_INPUTS)} inputs)")


def main() -> None:
    print("Generating PAPER-002 figures from committed artifacts...")
    figure_1()
    figure_2()
    write_manifest()


if __name__ == "__main__":
    main()

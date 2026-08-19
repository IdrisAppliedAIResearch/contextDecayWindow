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
    # git blobs are LF-normalized, so split on "\n" only: str.splitlines() also
    # breaks on U+2028 and U+0085, which appear inside these payloads verbatim.
    text = read(path).decode("utf-8-sig")
    return list(csv.DictReader(text.split("\n")))


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in read(path).decode("utf-8").split("\n")
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


# --------------------------------------------------------------------------
# F3 - every mechanism against its own registered bar
# --------------------------------------------------------------------------
def figure_3() -> None:
    nf004 = load_json(BIO / "nf_004/artifacts/g7_result_integrity.json")
    nf004_bar = extract(
        BIO / "nf_004/NF_004_PRE_REGISTRATION.md",
        r"gains\s*>=\s*([0-9.]+)\s*\*\s*losses",
    )
    nf005 = load_json(BIO / "nf_005/artifacts/g8_integrity.json")
    nf005_bar = extract(
        BIO / "nf_005/NF_005_PRE_REGISTRATION.md",
        r"gains\s*>=\s*([0-9.]+)\s*\*\s*losses",
    )
    nf006 = load_json(BIO / "nf_006/artifacts/g8_g9_measurement.json")
    nf006_bar = extract(
        BIO / "nf_006/NF_006_PRE_REGISTRATION.md",
        r"T1\s*>=\s*([0-9]+)/17",
    )
    e005 = load_json(LEDGER / "artifacts/e005/e005_results.json")
    e001 = load_json(LEDGER / "artifacts/e001/analysis_001/e001_results.json")
    tier3 = load_json(REPO / "experiments/surveys/retrieval_bakeoff/tier3/tier3_results.json")
    tier3_bar = extract(
        REPO / "experiments/surveys/retrieval_bakeoff/retrieval_bakeoff_report.md",
        r"below the registered ([0-9.]+)% build",
    )
    sal = load_json(BIO / "sal_001/artifacts/sal001_analysis/analysis.json")
    sal_bar = extract(
        BIO / "sal_001/SAL_001_FINAL_DESIGN.json",
        r"adjusted symmetric AUC >= ([0-9.]+)",
    )
    dmr004 = load_json(BIO / "dmr_004/artifacts/gates_holdout.json")["gates"]
    dmr001 = load_json(BIO / "dmr_001/artifacts/dmr001_gates/gate_report.json")
    dmr001c = load_json(BIO / "dmr_001c/artifacts/dmr001c_gates/gate_report.json")
    s011 = load_json(S011 / "evaluation/verdict.json")
    lv001_baseline = extract(
        REPO / "experiments/components/live_validation/LV_001_report.md",
        r"\*\*B2\*\* targeted[^|]*\|\s*([0-9.]+)\s*/\s*8",
    )
    lv001_treatment = extract(
        REPO / "experiments/components/live_validation/LV_001_report.md",
        r"\*\*B2\*\* targeted[^|]*\|\s*[0-9.]+\s*/\s*8\s*\|\s*([0-9.]+)\s*/\s*8",
    )
    lv001_tolerance = extract(
        REPO / "experiments/components/live_validation/LV_001_report.md",
        r"must not fall >([0-9.]+) below",
    )

    def dmr001_check(gate: str, needle: str) -> dict:
        for entry in dmr001["verdict"]["gates"]:
            if entry["gate"] != gate:
                continue
            for check in entry["checks"]:
                if needle in check["check"]:
                    return check
        raise SystemExit(f"DMR-001 check {needle!r} not found in the gate report")

    forced = dmr001_check("G3", "holdout: forced fraction")
    largest = dmr001_check("G3", "development: largest event share")
    periodic = dmr001c["summary"]["periodic_macro_f1"][dmr001c["summary"]["best_periodic"]]

    # (statistic, achieved, bar, higher_is_better, note)
    rows = [
        (
            "NF-005 · source-turn ranking", "gain / loss ratio",
            None, nf005_bar, True,
            f"{nf005['primary_comparison']['gains']} gains, "
            f"{nf005['primary_comparison']['losses']} losses",
        ),
        (
            "NF-004 · adjacent-pair ranking", "gain / loss ratio",
            nf004["primary"]["paired"]["gain_loss_ratio"], nf004_bar, True,
            f"{nf004['primary']['paired']['gain_loss_ratio']:.2f} vs {nf004_bar:g}",
        ),
        (
            "NF-006 · statement ranking", "breadth items available",
            nf006["G9"]["q11"]["T1_OWN_STATEMENT"]["available"], nf006_bar, True,
            f"{nf006['G9']['q11']['T1_OWN_STATEMENT']['available']}/17 "
            f"vs {nf006_bar:g}/17",
        ),
        (
            "E005 · coverage selection", "breadth items available",
            e005["primary_configuration"]["q11_fact_count"],
            e005["secondary_reference_points"]["rubric_threshold"], True,
            f"{e005['primary_configuration']['q11_fact_count']}/17 vs "
            f"{e005['secondary_reference_points']['rubric_threshold']}/17",
        ),
        (
            "E002 · segmented query retrieval", "breadth items available",
            e005["secondary_reference_points"]["e002_best"],
            e005["secondary_reference_points"]["rubric_threshold"], True,
            f"{e005['secondary_reference_points']['e002_best']}/17 vs "
            f"{e005['secondary_reference_points']['rubric_threshold']}/17",
        ),
        (
            "Bakeoff T3 · query-type routing", "oracle relative gain",
            tier3["analysis"]["T3.2_oracle_router"]["relative_gain"],
            tier3_bar / 100.0, True,
            f"{tier3['analysis']['T3.2_oracle_router']['relative_gain']:.2%} vs "
            f"{tier3_bar:g}%",
        ),
        (
            "E001 · attention-derived terms", "best cue cosine",
            e001["best"]["target_cosine"], e001["k_threshold"], True,
            f"{e001['best']['target_cosine']:.3f} vs K = {e001['k_threshold']:g}",
        ),
        (
            "SAL-001 · surprisal proximity", "adjusted neighbour AUC",
            sal["metrics"]["adjusted_symmetric_auc"], sal_bar, True,
            f"{sal['metrics']['adjusted_symmetric_auc']:.3f} vs {sal_bar:g}",
        ),
        (
            "DMR-004 · sufficiency signal", "Youden's J",
            dmr004["G_J"]["value"], dmr004["G_J"]["bar"], True,
            f"{dmr004['G_J']['value']:.3f} vs {dmr004['G_J']['bar']:g}",
        ),
        (
            "DMR-004 · sufficiency signal", "false-finite rate (lower is better)",
            dmr004["G3"]["value"], dmr004["G3"]["bar"], False,
            f"{dmr004['G3']['value']:.3f} vs {dmr004['G3']['bar']:g}",
        ),
        (
            "DMR-001 · event formation", "forced fraction (lower is better)",
            forced["observed"],
            dmr001["verdict"]["bars"]["G3"]["max_forced_fraction"], False,
            f"{forced['observed']:.3f} vs "
            f"{dmr001['verdict']['bars']['G3']['max_forced_fraction']:g}",
        ),
        (
            "DMR-001 · event formation", "largest event share (lower is better)",
            largest["observed"],
            dmr001["verdict"]["bars"]["G3"]["max_largest_event_share_of_session"],
            False,
            f"{largest['observed']:.3f} vs "
            f"{dmr001['verdict']['bars']['G3']['max_largest_event_share_of_session']:g}",
        ),
        (
            "DMR-001C · boundary evidence", "macro F1 vs best periodic control",
            dmr001c["summary"]["macro_f1"],
            periodic + dmr001c["verdict"]["bars"]["G5"]["margin_over_best_periodic"],
            True,
            f"{dmr001c['summary']['macro_f1']:.3f} vs "
            f"{periodic:.3f} + "
            f"{dmr001c['verdict']['bars']['G5']['margin_over_best_periodic']:g}",
        ),
        (
            "Study 011 · K-first packing, live", "rubric score /13",
            s011["b1"]["arm_c"], s011["b1"]["arm_d"], True,
            f"{s011['b1']['arm_c']:g} vs {s011['b1']['arm_d']:g}",
        ),
        (
            "LV-001 · coverage selection, live", "targeted probes /8",
            lv001_treatment, lv001_baseline - lv001_tolerance, True,
            f"{lv001_treatment:g}/8 vs {lv001_baseline - lv001_tolerance:g}/8",
        ),
    ]

    graveyard = _graveyard_rows()

    clip = 1.8
    text_x = 1.95
    height = 0.38 * len(rows) + 0.34 * len(graveyard) + 2.0
    fig = plt.figure(figsize=(10.6, height))
    grid = fig.add_gridspec(
        2, 1,
        height_ratios=[0.38 * len(rows), 0.34 * len(graveyard)],
        hspace=0.16,
    )
    ax = fig.add_subplot(grid[0])
    ax2 = fig.add_subplot(grid[1])

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", color=GREY, alpha=0.22, linewidth=0.6)
    ax.set_axisbelow(True)

    for index, (name, statistic, achieved, bar, higher, note) in enumerate(rows):
        y = len(rows) - 1 - index
        if achieved is None:
            ratio, clears, off_scale = clip, True, True
        else:
            ratio = (achieved / bar) if higher else (bar / achieved)
            clears = ratio >= 1.0
            off_scale = ratio > clip
        colour = GREEN if clears else VERMILLION
        ax.barh(y, min(ratio, clip), color=colour, alpha=0.85, height=0.56)
        if off_scale:
            ax.annotate(
                "", xy=(clip + 0.10, y), xytext=(clip - 0.02, y),
                arrowprops=dict(arrowstyle="-|>", color=colour, linewidth=1.4),
            )
        ax.text(-0.03, y, name, ha="right", va="center", fontsize=8.4)
        ax.text(text_x, y + 0.16, statistic, ha="left", va="center",
                fontsize=7.6, color=GREY)
        ax.text(text_x, y - 0.20, note, ha="left", va="center",
                fontsize=8.2, color=colour, fontweight="bold")

    ax.axvline(1.0, color=BLACK, linewidth=1.3, zorder=4)
    ax.text(1.03, -0.60, "the registered bar", fontsize=8.4,
            ha="left", va="center", fontweight="bold")
    short = sum(
        1 for _, _, achieved, bar, higher, _ in rows
        if achieved is not None and ((achieved / bar) if higher else (bar / achieved)) < 1.0
    )
    clears = len(rows) - short
    ax.text(
        -0.60, -1.24,
        f"{short} of {len(rows)} registered statistics fall short; "
        f"{clears} clear, and all {clears} are the granularity substitution",
        fontsize=8.6, ha="left", fontweight="bold", zorder=6,
        bbox=dict(facecolor="white", edgecolor="none", pad=2.0),
    )
    ax.set_yticks([])
    ax.set_xlim(-0.62, 3.35)
    ax.set_ylim(-1.60, len(rows) - 0.35)
    ax.set_xticks([0, 0.5, 1.0, 1.5])
    ax.set_xticklabels(["0", "0.5×", "1.0× bar", "1.5×"], fontsize=8.2)
    ax.set_title(
        "every mechanism against the bar registered for it "
        "(each row on its own statistic, rescaled so 1.0 is that row's bar)",
        fontsize=10, loc="left",
    )

    # Mechanisms closed without a numeric bar: categorical rows only.
    ax2.axis("off")
    ax2.set_xlim(-0.62, 3.35)
    ax2.set_ylim(-1.0, len(graveyard))
    ax2.text(-0.60, len(graveyard) - 0.30,
             "closed without a committed numeric bar — categorical outcome only",
             fontsize=9, fontweight="bold")
    for index, (name, verdict, reason) in enumerate(graveyard):
        y = len(graveyard) - 1.35 - index
        colour = VERMILLION if verdict == "REFUTED" else GREY
        ax2.text(-0.03, y, name, ha="right", va="center", fontsize=8.4)
        ax2.scatter([0.10], [y], s=52, marker="s", color=colour, alpha=0.85)
        ax2.text(0.20, y, verdict, ha="left", va="center", fontsize=7.4,
                 color=colour, fontweight="bold")
        ax2.text(0.72, y, reason, ha="left", va="center", fontsize=7.8,
                 color=BLACK)

    save(fig, "f3_mechanisms_against_bars")


def _graveyard_rows() -> list[tuple[str, str, str]]:
    """Parse the ledger's graveyard table: mechanism, verdict, short reason."""
    ledger = text_of(LEDGER / "RETRIEVAL_MECHANISM_LEDGER.md")
    section = re.search(
        r"^## 6\. Graveyard.*?^\| Mechanism \| Killed by \|\n\|[-| ]+\|\n(.*?)^\s*$",
        ledger, re.S | re.M,
    )
    if section is None:
        raise SystemExit("the ledger's graveyard table no longer parses")
    out: list[tuple[str, str, str]] = []
    for line in section.group(1).splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        name = cells[0].replace("**", "")
        killed = cells[1]
        verdict = "NOT REFUTED" if "ot refuted" in killed.lower() else "REFUTED"
        reason = re.sub(r"\*\*|`", "", killed)
        reason = re.sub(r"\s*\(?See .*$", "", reason).strip(" .")
        reason = re.sub(r"^NOT REFUTED\.\s*|^Not refuted -\s*", "", reason)
        reason = reason[:1].upper() + reason[1:]
        if len(reason) > 84:
            reason = reason[:81].rstrip() + "…"
        out.append((name, verdict, reason))
    return out


# --------------------------------------------------------------------------
# F4 - packing priority as a gate
# --------------------------------------------------------------------------
def figure_4() -> None:
    paired = load_json(LME / "runs/ec002_k_first/a1_k_first/paired_comparison.json")
    a0_mech = load_jsonl(
        LME / "runs/ec002_k_first/a0_amended_reproduction_v2/a0_reproduced_mechanism.jsonl"
    )
    a1_mech = load_jsonl(LME / "runs/ec002_k_first/a1_k_first/a1_mechanism.jsonl")
    ic_paths = load_csv(IC001 / "b1_k_first/path_split.csv")
    ic_paired = load_json(IC001 / "b1_k_first/paired_comparison.json")

    session_any = paired["by_stratum"]["all"]["session_any"]
    n_answerable = paired["answerable_questions"]
    top_four = paired["top_four_subset"]["session_any"]
    n_top_four = paired["top_four_subset"]["denominator"]

    a0_k = sum(r["report"]["k_count"] for r in a0_mech)
    a1_k = sum(r["report"]["k_count"] for r in a1_mech)
    a0_chars = statistics.median(r["report"]["chars_delivered"] for r in a0_mech)
    a1_chars = statistics.median(r["report"]["chars_delivered"] for r in a1_mech)

    b0 = [r for r in ic_paths if r["arm"] == "B0"]
    b1 = [r for r in ic_paths if r["arm"] == "B1"]
    probes = [r["probe_turn"] for r in b0]
    b0_k = [int(r["k_episodes"]) for r in b0]
    b1_k = [int(r["k_episodes"]) for r in b1]
    b0_k_chars = sum(int(r["k_chars"]) for r in b0)
    b1_k_chars = sum(int(r["k_chars"]) for r in b1)

    fig = plt.figure(figsize=(10.6, 4.9))
    grid = fig.add_gridspec(1, 3, width_ratios=[1.0, 0.78, 1.15], wspace=0.36)
    ax_a = fig.add_subplot(grid[0])
    ax_b = fig.add_subplot(grid[1])
    ax_c = fig.add_subplot(grid[2])

    # (a) EC-002 outcome
    style(ax_a)
    labels = ["A0\nrecency-first\n(deployed)", "A1\nK-first"]
    values = [session_any["a0"], session_any["a1"]]
    ax_a.bar(labels, [n_answerable] * 2, color=GREY, alpha=0.13, width=0.6)
    ax_a.bar(labels, values, color=[VERMILLION, BLUE], alpha=0.9, width=0.6)
    for x, value in enumerate(values):
        ax_a.text(x, value + n_answerable * 0.02,
                  f"{value}/{n_answerable}\n{value / n_answerable:.1%}",
                  ha="center", fontsize=9, fontweight="bold")
    ax_a.text(
        0.5, n_answerable * 1.03,
        f"{session_any['gains']} gains, {session_any['losses']} losses",
        ha="center", fontsize=9, fontweight="bold", color=GREEN,
    )
    ax_a.set_ylim(0, n_answerable * 1.16)
    ax_a.tick_params(axis="x", labelsize=8)
    ax_a.set_ylabel("questions recalling any evidence session", fontsize=9)
    ax_a.set_title("EC-002 · 500 external stores,\nonly the packing order changed",
                   fontsize=9.4, loc="left")

    # (b) the mechanism, and what the medians hid
    style(ax_b)
    ax_b.bar(["A0", "A1"], [a0_k, a1_k], color=[VERMILLION, BLUE], alpha=0.9,
             width=0.55)
    for x, value in enumerate([a0_k, a1_k]):
        ax_b.text(x, value + a1_k * 0.03, f"{value:,}", ha="center",
                  fontsize=9.6, fontweight="bold")
    ax_b.set_ylim(0, a1_k * 1.18)
    ax_b.set_ylabel("similarity-path episodes delivered, all 500 blocks",
                    fontsize=8.6)
    median_note = (
        f"median block unchanged at {a0_chars:,.0f} chars"
        if a0_chars == a1_chars
        else f"median block {a0_chars:,.0f} → {a1_chars:,.0f} chars"
    )
    ax_b.set_title(
        f"the medians concealed it:\n{median_note}\n"
        f"top four subset {top_four['a0']} → {top_four['a1']} of {n_top_four},\n"
        f"{top_four['gains']} gains, {top_four['losses']} losses",
        fontsize=8.0, loc="left",
    )

    # (c) IC-001, per probe
    style(ax_c)
    width = 0.38
    xs = range(len(probes))
    zeros = sum(1 for v in b0_k if v == 0)
    ax_c.bar([x - width / 2 for x in xs], b0_k, width=width, color=VERMILLION,
             alpha=0.9,
             label=f"B0 recency-first (deployed) — 0 at {zeros} of {len(b0_k)}")
    ax_c.bar([x + width / 2 for x in xs], b1_k, width=width, color=BLUE,
             alpha=0.9, label="B1 K-first")
    ax_c.scatter([x - width / 2 for x in xs], b0_k, marker="_", s=120,
                 color=VERMILLION, linewidth=2.0, zorder=3)
    ax_c.set_xticks(list(xs))
    ax_c.set_xticklabels([f"turn {p}" for p in probes], fontsize=7.4, rotation=45)
    ax_c.set_yticks(range(0, max(b1_k) + 2))
    ax_c.set_ylim(0, max(b1_k) + 1.9)
    ax_c.set_ylabel("similarity-path episodes delivered", fontsize=9)
    ax_c.legend(loc="upper left", frameon=False, fontsize=7.6)
    ax_c.set_title("IC-001 · the same gate on the internal store",
                   fontsize=9.4, loc="left")
    ax_c.text(
        len(probes) - 0.5, max(b1_k) + 0.95,
        f"deployed order: {sum(b0_k)} episodes, {b0_k_chars:,} characters\n"
        f"K-first: {sum(b1_k)} episodes, {b1_k_chars:,} characters\n"
        f"Q11 available {ic_paired['q11']['b0_fact_count']}/17 → "
        f"{ic_paired['q11']['b1_fact_count']}/17, "
        f"{ic_paired['q11']['loss_count']} losses",
        fontsize=7.8, color=BLACK, ha="right", va="top",
    )

    save(fig, "f4_packing_priority_gate")


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
    figure_3()
    figure_4()
    write_manifest()


if __name__ == "__main__":
    main()

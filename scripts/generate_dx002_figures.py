"""Generate the DX-002 context-growth figures.

Two panels per arm. The stacked panel is the diagnostic named in section
0.3.2: it shows which part of the prompt owns the total, so a climbing
total can be attributed rather than guessed at. The terminal panel zooms
to the fitted window and draws the fit, because the whole question is
whether that line has a slope.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = (
    ROOT
    / "experiments"
    / "components"
    / "deployment_closeout"
    / "artifacts"
    / "dx002"
)

BLUE = "#0072B2"
ORANGE = "#D55E00"
GREEN = "#009E73"
PURPLE = "#7B4FA8"
GREY = "#8A97A3"
INK = "#17212B"
MID = "#596773"
GRID = "#D7DEE4"
RED = "#C43C39"

TERMINAL_WINDOW = 300
LTM_BUDGET = 32_000

STACK = [
    ("retrieved_ltm", "retrieved_ltm", BLUE),
    ("retrieved_stm", "retrieved_stm", ORANGE),
    ("recent_context", "recent_context", GREEN),
    ("current_turn", "current_turn", PURPLE),
    ("preamble", "preamble + rules + separators", GREY),
]


def configure() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.edgecolor": MID,
            "axes.labelcolor": INK,
            "text.color": INK,
            "xtick.color": MID,
            "ytick.color": MID,
            "grid.color": GRID,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def read_rows() -> dict[str, list[dict]]:
    with (ARTIFACTS / "decomposition.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    by_arm: dict[str, list[dict]] = {}
    for row in rows:
        by_arm.setdefault(row["arm"], []).append(row)
    for arm_rows in by_arm.values():
        arm_rows.sort(key=lambda item: int(item["turn"]))
    return by_arm


def build(by_arm: dict[str, list[dict]], results: dict) -> None:
    arms = sorted(by_arm)
    figure, axes = plt.subplots(
        len(arms), 2, figsize=(13.5, 4.1 * len(arms)), constrained_layout=True
    )
    if len(arms) == 1:
        axes = np.array([axes])

    for index, arm in enumerate(arms):
        rows = by_arm[arm]
        _stacked_panel(axes[index][0], arm, rows)
        _terminal_panel(axes[index][1], arm, rows, results)

    figure.suptitle(
        "DX-002 — where Study 010's context went, and whether it was "
        "still climbing",
        fontsize=15,
        fontweight="bold",
    )
    for suffix in ("svg", "png"):
        figure.savefig(
            ARTIFACTS / f"dx002_context_growth.{suffix}",
            dpi=300 if suffix == "png" else None,
        )
    plt.close(figure)


def _stacked_panel(axis, arm: str, rows: list[dict]) -> None:
    turns = [int(row["turn"]) for row in rows]
    series = []
    labels = []
    colors = []
    for key, label, color in STACK:
        if key == "preamble":
            values = [
                int(row["preamble"])
                + int(row["pinned_rules"])
                + int(row["separators"])
                + int(row["assistant_cue"])
                for row in rows
            ]
        else:
            values = [int(row[key]) for row in rows]
        if not any(values):
            continue
        series.append(values)
        labels.append(label)
        colors.append(color)

    axis.stackplot(turns, *series, labels=labels, colors=colors, linewidth=0)
    axis.set_title(f"{arm} — prompt composition, all 1,000 turns")
    axis.set_xlabel("turn")
    axis.set_ylabel("serialized characters")
    axis.grid(True, alpha=0.35, linewidth=0.6)
    axis.set_axisbelow(True)
    axis.legend(loc="upper left", fontsize=8, framealpha=0.92)
    axis.margins(x=0)


def _terminal_panel(axis, arm: str, rows: list[dict], results: dict) -> None:
    tail = rows[-TERMINAL_WINDOW:]
    turns = np.array([int(row["turn"]) for row in tail], dtype=float)
    totals = np.array([int(row["total"]) for row in tail], dtype=float)

    window = _window(results, arm, "total")
    slope = window["slope_chars_per_turn"]
    intercept = window["intercept_chars"]
    low, high = window["ci95_low"], window["ci95_high"]

    axis.scatter(turns, totals, s=9, color=BLUE, alpha=0.55, linewidths=0)
    axis.plot(
        turns,
        intercept + slope * turns,
        color=RED,
        linewidth=2.0,
        label=f"OLS {slope:+.2f} chars/turn",
    )
    centre = totals.mean()
    mid_turn = turns.mean()
    for bound, style in ((low, "--"), (high, "--")):
        axis.plot(
            turns,
            centre + bound * (turns - mid_turn),
            color=MID,
            linewidth=1.1,
            linestyle=style,
        )
    axis.plot([], [], color=MID, linestyle="--", label=f"95% CI [{low:+.1f}, {high:+.1f}]")

    verdict = "flat" if window["includes_zero"] else "NOT flat"
    axis.set_title(f"{arm} — terminal {TERMINAL_WINDOW} turns ({verdict})")
    axis.set_xlabel("turn")
    axis.set_ylabel("total serialized characters")
    axis.grid(True, alpha=0.35, linewidth=0.6)
    axis.set_axisbelow(True)
    axis.legend(loc="upper left", fontsize=8, framealpha=0.92)


def _window(results: dict, arm: str, series: str) -> dict:
    for entry in results["arms"]:
        if entry["arm"] == arm:
            return entry["series"][series]["terminal_window"]
    raise KeyError(arm)


def write_manifest() -> None:
    outputs = ["dx002_context_growth.svg", "dx002_context_growth.png"]
    sources = ["decomposition.csv", "dx002_results.json"]
    manifest = {
        "generator": "scripts/generate_dx002_figures.py",
        "formats": ["SVG", "PNG (300 dpi)"],
        "outputs": outputs,
        "sources": [
            {
                "path": (ARTIFACTS / name).relative_to(ROOT).as_posix(),
                "sha256": _sha256(ARTIFACTS / name),
            }
            for name in sources
        ],
    }
    (ARTIFACTS / "figure_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()


def main() -> None:
    configure()
    results = json.loads(
        (ARTIFACTS / "dx002_results.json").read_text(encoding="utf-8")
    )
    build(read_rows(), results)
    write_manifest()
    print(f"wrote figures to {ARTIFACTS}")


if __name__ == "__main__":
    main()

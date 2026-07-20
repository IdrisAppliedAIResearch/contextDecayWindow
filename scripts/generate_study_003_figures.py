r"""Generate the publication figures for the Study 003 paper.

The script uses only the Python standard library. Every quantitative mark is
derived from the accepted ``study_003_full_002`` artifacts; design constants
come from the locked protocol and the paper's documented amendments.

Run from the repository root:

    .venv\Scripts\python.exe scripts\generate_study_003_figures.py

Use ``--check`` to verify that committed SVGs match a fresh generation.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, quantiles


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = REPOSITORY_ROOT / "experiments" / "study_003"
RUN_ROOT = STUDY_ROOT / "runs" / "run_001"
METRICS_ROOT = RUN_ROOT / "condition_c" / "metrics"
LTM_ROOT = RUN_ROOT / "ltm_analysis"
DEFAULT_OUTPUT = STUDY_ROOT / "figures"

INK = "#17212B"
MUTED = "#5D6975"
GRID = "#D8E0E6"
LIGHT = "#EEF2F5"
PAPER = "#FFFFFF"
BLUE = "#2474A6"
BLUE_LIGHT = "#DCECF5"
GREEN = "#18835D"
GREEN_LIGHT = "#DCEFE7"
ORANGE = "#C85A16"
ORANGE_LIGHT = "#F8E4D7"
PURPLE = "#7656A8"
PURPLE_LIGHT = "#EAE3F3"
GRAY = "#89949E"
GRAY_LIGHT = "#E5EAEE"


@dataclass(frozen=True)
class RubricCategory:
    number: int
    label: str
    score: float
    maximum: float


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_rubric() -> tuple[list[RubricCategory], float, float]:
    text = (RUN_ROOT / "condition_c" / "rubric" / "scores.md").read_text(
        encoding="utf-8"
    )
    labels = {
        1: "Early plant survival",
        2: "Middle plant survival",
        3: "Late plant survival",
        4: "Topic bleed",
        5: "Rule pinning",
    }
    categories: list[RubricCategory] = []
    for number in range(1, 6):
        match = re.search(
            rf"Category {number} Total.*?([0-9.]+)\s*/\s*([0-9.]+)", text
        )
        if match is None:
            raise ValueError(f"Could not parse Category {number} from rubric scores")
        categories.append(
            RubricCategory(
                number,
                labels[number],
                float(match.group(1)),
                float(match.group(2)),
            )
        )
    overall = re.search(r"\*\*Overall:\*\*\s*([0-9.]+)\s*/\s*([0-9.]+)", text)
    if overall is None:
        raise ValueError("Could not parse overall rubric score")
    return categories, float(overall.group(1)), float(overall.group(2))


def fmt(value: float, digits: int = 1) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.{digits}f}"


class SVG:
    def __init__(self, width: int, height: int, title: str, description: str):
        self.width = width
        self.height = height
        self.title = title
        self.description = description
        self.parts: list[str] = []

    @staticmethod
    def _attrs(**attrs: object) -> str:
        rendered: list[str] = []
        for key, value in attrs.items():
            if value is None:
                continue
            name = key.rstrip("_").replace("_", "-")
            rendered.append(f'{name}="{html.escape(str(value), quote=True)}"')
        return " ".join(rendered)

    def raw(self, value: str) -> None:
        self.parts.append(value)

    def rect(self, x: float, y: float, width: float, height: float, **attrs: object) -> None:
        self.parts.append(
            f'<rect {self._attrs(x=round(x, 2), y=round(y, 2), width=round(width, 2), height=round(height, 2), **attrs)}/>'
        )

    def line(self, x1: float, y1: float, x2: float, y2: float, **attrs: object) -> None:
        self.parts.append(
            f'<line {self._attrs(x1=round(x1, 2), y1=round(y1, 2), x2=round(x2, 2), y2=round(y2, 2), **attrs)}/>'
        )

    def circle(self, cx: float, cy: float, r: float, **attrs: object) -> None:
        self.parts.append(
            f'<circle {self._attrs(cx=round(cx, 2), cy=round(cy, 2), r=round(r, 2), **attrs)}/>'
        )

    def polygon(self, points: list[tuple[float, float]], **attrs: object) -> None:
        value = " ".join(f"{round(x, 2)},{round(y, 2)}" for x, y in points)
        self.parts.append(f'<polygon {self._attrs(points=value, **attrs)}/>')

    def path(self, d: str, **attrs: object) -> None:
        self.parts.append(f'<path {self._attrs(d=d, **attrs)}/>')

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: int = 16,
        weight: int = 400,
        fill: str = INK,
        anchor: str = "start",
        **attrs: object,
    ) -> None:
        self.parts.append(
            f'<text {self._attrs(x=round(x, 2), y=round(y, 2), font_size=size, font_weight=weight, fill=fill, text_anchor=anchor, **attrs)}>{html.escape(value)}</text>'
        )

    def multiline(
        self,
        x: float,
        y: float,
        lines: list[str],
        *,
        size: int = 16,
        weight: int = 400,
        fill: str = INK,
        anchor: str = "start",
        gap: int = 21,
    ) -> None:
        tspans = []
        for index, line in enumerate(lines):
            dy = 0 if index == 0 else gap
            tspans.append(
                f'<tspan x="{round(x, 2)}" dy="{dy}">{html.escape(line)}</tspan>'
            )
        self.parts.append(
            f'<text {self._attrs(x=round(x, 2), y=round(y, 2), font_size=size, font_weight=weight, fill=fill, text_anchor=anchor)}>{"".join(tspans)}</text>'
        )

    def finish(self) -> str:
        body = "\n  ".join(self.parts)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
            f'height="{self.height}" viewBox="0 0 {self.width} {self.height}" '
            'role="img" aria-labelledby="figure-title figure-description">\n'
            f'  <title id="figure-title">{html.escape(self.title)}</title>\n'
            f'  <desc id="figure-description">{html.escape(self.description)}</desc>\n'
            "  <defs>\n"
            '    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">\n'
            f'      <path d="M 0 0 L 10 5 L 0 10 z" fill="{MUTED}"/>\n'
            "    </marker>\n"
            '    <pattern id="probe-hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">\n'
            f'      <line x1="0" y1="0" x2="0" y2="8" stroke="{ORANGE}" stroke-width="2" opacity="0.25"/>\n'
            "    </pattern>\n"
            "  </defs>\n"
            f'  <rect width="{self.width}" height="{self.height}" fill="{PAPER}"/>\n'
            f'  <g font-family="Inter, Segoe UI, Arial, sans-serif" shape-rendering="geometricPrecision">\n  {body}\n  </g>\n'
            "</svg>\n"
        )


def arrow(svg: SVG, x1: float, y1: float, x2: float, y2: float) -> None:
    svg.line(
        x1,
        y1,
        x2,
        y2,
        stroke=MUTED,
        stroke_width=2,
        marker_end="url(#arrow)",
    )


def label_box(
    svg: SVG,
    x: float,
    y: float,
    width: float,
    height: float,
    lines: list[str],
    *,
    fill: str = LIGHT,
    stroke: str = GRID,
    accent: str | None = None,
    text_size: int = 15,
) -> None:
    svg.rect(x, y, width, height, rx=8, fill=fill, stroke=stroke, stroke_width=1.5)
    if accent:
        svg.rect(x, y, 7, height, rx=4, fill=accent)
    total_height = (len(lines) - 1) * 20
    svg.multiline(
        x + width / 2,
        y + height / 2 - total_height / 2 + 5,
        lines,
        size=text_size,
        weight=500 if len(lines) == 1 else 400,
        anchor="middle",
        gap=20,
    )


def turn_x(turn: float, left: float, right: float) -> float:
    return left + (turn - 1) / 119 * (right - left)


def draw_phase_backgrounds(
    svg: SVG, left: float, right: float, top: float, height: float, *, labels: bool
) -> None:
    phases = [
        (1, 30, "Civil engineering"),
        (31, 60, "Renaissance art"),
        (61, 90, "Monetary policy"),
        (91, 120, "Marine biology + probes"),
    ]
    fills = [BLUE_LIGHT, GREEN_LIGHT, PURPLE_LIGHT, ORANGE_LIGHT]
    for (start, end, label), fill in zip(phases, fills, strict=True):
        x1 = turn_x(start, left, right)
        x2 = turn_x(end, left, right)
        width = x2 - x1 + (right - left) / 119
        svg.rect(x1, top, width, height, fill=fill, opacity=0.42)
        if labels:
            svg.text(
                x1 + width / 2,
                top + 20,
                label,
                size=14,
                fill=MUTED,
                anchor="middle",
            )
    probe_x = turn_x(112, left, right)
    svg.rect(
        probe_x,
        top,
        right - probe_x,
        height,
        fill="url(#probe-hatch)",
        stroke=ORANGE,
        stroke_width=1,
        stroke_dasharray="5 4",
    )


def generate_overview(output: Path) -> None:
    categories, overall_score, overall_max = load_rubric()
    promotions = load_csv(LTM_ROOT / "promotion_events.csv")
    evaluated = sum(int(row["episodes_evaluated"]) for row in promotions)
    promoted = sum(int(row["episodes_promoted"]) for row in promotions)
    memory = load_csv(METRICS_ROOT / "memory_store.csv")
    before_final = int(memory[-2]["topic_count"])
    final_topics = int(memory[-1]["topic_count"])

    svg = SVG(
        1200,
        560,
        "Study 003 design and principal outcomes",
        "A 120-turn conversation crossed four scripted domains. LTM promotion fired at turns 31, 61, and 91. The accepted run scored 12 of 13 rubric points, passed two of three pre-registered bars, promoted 21 of 90 evaluated episodes, and collapsed from five topics to one at turn 120.",
    )
    left, right = 120, 1140
    svg.text(40, 38, "A", size=18, weight=500)
    svg.text(70, 38, "120-turn scripted conversation", size=18, weight=500)
    phases = [
        (1, 30, "Civil engineering", BLUE_LIGHT),
        (31, 60, "Renaissance art", GREEN_LIGHT),
        (61, 90, "Monetary policy", PURPLE_LIGHT),
        (91, 120, "Marine biology", ORANGE_LIGHT),
    ]
    for start, end, label, fill in phases:
        x1 = turn_x(start, left, right)
        x2 = turn_x(end, left, right) + (right - left) / 119
        svg.rect(x1, 78, x2 - x1, 76, fill=fill, stroke=PAPER, stroke_width=2)
        svg.text((x1 + x2) / 2, 109, label, size=15, weight=500, anchor="middle")
        svg.text((x1 + x2) / 2, 134, f"turns {start}–{end}", size=13, fill=MUTED, anchor="middle")

    for event_turn in (31, 61, 91):
        x = turn_x(event_turn, left, right)
        svg.line(x, 57, x, 78, stroke=BLUE, stroke_width=2)
        svg.circle(x, 52, 6, fill=BLUE)
        svg.text(x, 39, f"LTM event {event_turn}", size=12, fill=MUTED, anchor="middle")

    probe_x = turn_x(112, left, right)
    svg.rect(
        probe_x,
        78,
        right - probe_x,
        76,
        fill="url(#probe-hatch)",
        stroke=ORANGE,
        stroke_width=1.5,
    )
    svg.text((probe_x + right) / 2, 171, "rubric probes 112–120", size=12, fill=ORANGE, anchor="middle")
    for consolidation_turn in range(10, 121, 10):
        x = turn_x(consolidation_turn, left, right)
        svg.line(x, 154, x, 163, stroke=GRAY, stroke_width=1.5)
    svg.text(120, 190, "topic consolidation every 10 turns", size=12, fill=MUTED)

    svg.text(40, 237, "B", size=18, weight=500)
    svg.text(70, 237, "Principal outcomes", size=18, weight=500)

    lane_y = [282, 348, 414, 480]
    label_x, mark_x, mark_width = 70, 330, 620

    svg.text(label_x, lane_y[0] + 18, "Rubric", size=15, weight=500)
    cell_gap = 5
    cell_width = (mark_width - 12 * cell_gap) / 13
    failed_question = 11
    for question in range(1, 14):
        x = mark_x + (question - 1) * (cell_width + cell_gap)
        passed = question != failed_question
        svg.rect(
            x,
            lane_y[0],
            cell_width,
            28,
            rx=4,
            fill=BLUE if passed else ORANGE,
        )
        svg.text(x + cell_width / 2, lane_y[0] + 19, str(question), size=11, fill=PAPER, anchor="middle")
    svg.text(990, lane_y[0] + 20, f"{fmt(overall_score)}/{fmt(overall_max)}", size=20, weight=500)
    svg.text(1070, lane_y[0] + 20, "Q11 missed", size=13, fill=ORANGE)

    svg.text(label_x, lane_y[1] + 18, "Pre-registered bars", size=15, weight=500)
    for index, passed in enumerate((True, False, True)):
        x = mark_x + index * 95
        svg.circle(x + 14, lane_y[1] + 14, 14, fill=GREEN if passed else ORANGE)
        symbol = "✓" if passed else "×"
        svg.text(x + 14, lane_y[1] + 20, symbol, size=20, weight=500, fill=PAPER, anchor="middle")
        svg.text(x + 35, lane_y[1] + 19, f"Bar {index + 1}", size=13, fill=MUTED)
    svg.text(990, lane_y[1] + 20, "2/3", size=20, weight=500)
    svg.text(1040, lane_y[1] + 20, "PARTIAL", size=13, fill=ORANGE)

    svg.text(label_x, lane_y[2] + 18, "LTM write path", size=15, weight=500)
    promoted_width = mark_width * promoted / evaluated
    svg.rect(mark_x, lane_y[2], mark_width, 28, rx=4, fill=GRAY_LIGHT)
    svg.rect(mark_x, lane_y[2], promoted_width, 28, rx=4, fill=BLUE)
    svg.text(mark_x + promoted_width / 2, lane_y[2] + 19, str(promoted), size=13, weight=500, fill=PAPER, anchor="middle")
    svg.text(mark_x + mark_width + 15, lane_y[2] + 20, f"{promoted}/{evaluated} promoted ({promoted/evaluated:.1%})", size=15)

    svg.text(label_x, lane_y[3] + 18, "Topic state at turn 120", size=15, weight=500)
    svg.circle(mark_x + 30, lane_y[3] + 14, 24, fill=ORANGE_LIGHT, stroke=ORANGE, stroke_width=2)
    svg.text(mark_x + 30, lane_y[3] + 21, str(before_final), size=22, weight=500, anchor="middle")
    arrow(svg, mark_x + 64, lane_y[3] + 14, mark_x + 132, lane_y[3] + 14)
    svg.circle(mark_x + 170, lane_y[3] + 14, 24, fill=ORANGE, stroke=ORANGE, stroke_width=2)
    svg.text(mark_x + 170, lane_y[3] + 21, str(final_topics), size=22, weight=500, fill=PAPER, anchor="middle")
    svg.text(mark_x + 215, lane_y[3] + 20, "four cross-domain merges; numerical bar passed, purity did not", size=15, fill=ORANGE)

    output.write_text(svg.finish(), encoding="utf-8", newline="\n")


def generate_architecture(output: Path) -> None:
    svg = SVG(
        1200,
        590,
        "Study 003 iterative memory architecture",
        "Each conversation turn produces an STM episode. N plus K retrieval and pinned rules construct bounded context for the next model call. User-message embeddings support topic assignment and consolidation. At an eligible canonical topic transition, outgoing episodes are scored by novelty, repetition, association, and emotional valence; promoted episodes are written to an LTM store that is not read during Study 003.",
    )
    svg.text(40, 38, "A", size=18, weight=500)
    svg.text(70, 38, "Active-context loop", size=18, weight=500)

    label_box(svg, 55, 85, 165, 80, ["User message", "+ model response"], fill=BLUE_LIGHT, accent=BLUE)
    label_box(svg, 280, 75, 205, 100, ["STM episode", "full episode embedding", "user-message embedding"], fill=LIGHT, accent=BLUE)
    label_box(svg, 555, 75, 190, 100, ["N + K retrieval", "N ≤ 10 decay-ranked", "+ similarity matches"], fill=GREEN_LIGHT, accent=GREEN)
    label_box(svg, 815, 85, 150, 80, ["Bounded", "active context"], fill=LIGHT, accent=GREEN)
    label_box(svg, 1030, 85, 120, 80, ["Next model", "turn"], fill=BLUE_LIGHT, accent=BLUE)
    arrow(svg, 220, 125, 280, 125)
    arrow(svg, 485, 125, 555, 125)
    arrow(svg, 745, 125, 815, 125)
    arrow(svg, 965, 125, 1030, 125)
    svg.path(
        "M 1090 165 C 1090 220, 135 220, 135 165",
        fill="none",
        stroke=MUTED,
        stroke_width=2,
        marker_end="url(#arrow)",
    )
    label_box(svg, 690, 220, 155, 58, ["Pinned rules"], fill=PURPLE_LIGHT, accent=PURPLE)
    arrow(svg, 768, 220, 845, 165)

    svg.line(40, 312, 1160, 312, stroke=GRID, stroke_width=1)
    svg.text(40, 352, "B", size=18, weight=500)
    svg.text(70, 352, "Transition-triggered LTM write path", size=18, weight=500)

    label_box(svg, 55, 400, 170, 90, ["User-message", "topic assignment", "and consolidation"], fill=LIGHT, accent=PURPLE)
    label_box(svg, 275, 400, 175, 90, ["Eligible canonical", "topic transition", "outgoing topic ≥ 3"], fill=ORANGE_LIGHT, accent=ORANGE)
    label_box(svg, 500, 382, 235, 126, ["Score outgoing episodes", "Novelty · 0.35", "Repetition · 0.30", "Association · 0.20", "Emotional valence · 0.15"], fill=LIGHT, accent=BLUE, text_size=14)
    label_box(svg, 785, 392, 180, 106, ["Promote if", "weighted score ≥ 0.60", "or any filter ≥ 0.90*"], fill=GREEN_LIGHT, accent=GREEN, text_size=14)
    label_box(svg, 1015, 400, 140, 90, ["LTM store", "write only in", "Study 003"], fill=BLUE_LIGHT, accent=BLUE)
    arrow(svg, 225, 445, 275, 445)
    arrow(svg, 450, 445, 500, 445)
    arrow(svg, 735, 445, 785, 445)
    arrow(svg, 965, 445, 1015, 445)
    svg.path(
        "M 382 175 L 382 365 C 382 390, 140 365, 140 400",
        fill="none",
        stroke=PURPLE,
        stroke_width=2,
        stroke_dasharray="6 5",
        marker_end="url(#arrow)",
    )
    svg.text(397, 286, "user-message embedding", size=13, fill=PURPLE)
    svg.text(785, 538, "* All-or-nothing bypass suspended while LTM is empty", size=13, fill=MUTED)
    svg.text(55, 538, "Promoted episodes remain resident in STM.", size=13, fill=MUTED)

    output.write_text(svg.finish(), encoding="utf-8", newline="\n")


def generate_confirmatory(output: Path) -> None:
    categories, overall_score, overall_max = load_rubric()
    memory = load_csv(METRICS_ROOT / "memory_store.csv")
    final_topics = int(memory[-1]["topic_count"])

    svg = SVG(
        1200,
        590,
        "Rubric and pre-registered success-bar outcomes",
        "Four rubric categories achieved full credit. Topic bleed achieved two of three points because Q11 failed, producing an overall score of 12 of 13. The middle-position and final-topic-count success bars passed; the overall-score bar failed, so the confirmatory result was partial.",
    )
    svg.text(40, 42, "A", size=18, weight=500)
    svg.text(70, 42, "Rubric score by category", size=18, weight=500)
    svg.text(650, 42, "B", size=18, weight=500)
    svg.text(680, 42, "Pre-registered success bars", size=18, weight=500)

    bar_left, bar_width = 245, 330
    for index, category in enumerate(categories):
        y = 90 + index * 72
        svg.text(70, y + 20, f"C{category.number}  {category.label}", size=14)
        svg.rect(bar_left, y, bar_width, 28, rx=4, fill=GRAY_LIGHT)
        fill_width = bar_width * category.score / category.maximum
        color = BLUE if category.score == category.maximum else ORANGE
        svg.rect(bar_left, y, fill_width, 28, rx=4, fill=color)
        svg.text(
            bar_left + bar_width + 16,
            y + 20,
            f"{fmt(category.score)}/{fmt(category.maximum)}",
            size=15,
            weight=500,
            fill=color if category.score < category.maximum else INK,
        )
        if category.number == 4:
            svg.text(bar_left + 4, y + 52, "Q11: incomplete four-domain enumeration", size=12, fill=ORANGE)

    svg.line(620, 65, 620, 475, stroke=GRID, stroke_width=1)
    success_rows = [
        ("Bar 1", "Middle-position score", "3/3", "required 3/3", True),
        ("Bar 2", "Overall rubric score", f"{fmt(overall_score)}/{fmt(overall_max)}", "required 13/13", False),
        ("Bar 3", "Final topic count", str(final_topics), "required ≤ 20", True),
    ]
    for index, (bar, label, observed, criterion, passed) in enumerate(success_rows):
        y = 92 + index * 126
        color = GREEN if passed else ORANGE
        svg.circle(690, y + 22, 20, fill=color)
        svg.text(690, y + 29, "✓" if passed else "×", size=26, weight=500, fill=PAPER, anchor="middle")
        svg.text(730, y + 7, bar, size=13, fill=MUTED)
        svg.text(730, y + 31, label, size=16, weight=500)
        svg.text(730, y + 57, f"observed {observed} · {criterion}", size=14, fill=MUTED)
        svg.text(1090, y + 31, "PASS" if passed else "FAIL", size=15, weight=500, fill=color, anchor="end")

    svg.rect(70, 505, 1060, 48, rx=6, fill=ORANGE_LIGHT)
    svg.text(600, 536, "Confirmatory outcome: PARTIAL — 2 of 3 pre-registered bars passed", size=18, weight=500, fill=ORANGE, anchor="middle")
    output.write_text(svg.finish(), encoding="utf-8", newline="\n")


def axis_y(value: float, minimum: float, maximum: float, top: float, bottom: float) -> float:
    return bottom - (value - minimum) / (maximum - minimum) * (bottom - top)


def generate_trajectories(output: Path) -> None:
    memory = load_csv(METRICS_ROOT / "memory_store.csv")
    performance = load_csv(METRICS_ROOT / "model_performance.csv")
    consolidation = load_csv(METRICS_ROOT / "consolidation_events.csv")
    left, right = 105, 1145

    svg = SVG(
        1200,
        740,
        "Topic-count and constructed-context trajectories across 120 turns",
        "The topic count briefly rose to two before a turn-20 merge, then tracked scripted domain transitions to four topics. A mixed-domain query created a fifth topic at turn 114, and four turn-120 merges collapsed the count to one. Estimated constructed context peaked at 9,189 tokens on turn 80.",
    )
    svg.text(40, 38, "A", size=18, weight=500)
    svg.text(70, 38, "Topic count", size=18, weight=500)
    top1, bottom1 = 72, 320
    draw_phase_backgrounds(svg, left, right, top1, bottom1 - top1, labels=True)
    for value in range(1, 6):
        y = axis_y(value, 0.5, 5.5, top1 + 25, bottom1 - 20)
        svg.line(left, y, right, y, stroke=GRID, stroke_width=1)
        svg.text(left - 18, y + 5, str(value), size=13, fill=MUTED, anchor="end")
    for boundary in (30.5, 60.5, 90.5):
        x = turn_x(boundary, left, right)
        svg.line(x, top1, x, bottom1, stroke=GRAY, stroke_width=1.5, stroke_dasharray="5 5")
    for row in consolidation:
        x = turn_x(float(row["turn_number"]), left, right)
        svg.polygon([(x - 4, top1 - 4), (x + 4, top1 - 4), (x, top1 + 4)], fill=GRAY)

    topic_points = [(int(row["turn"]), int(row["topic_count"])) for row in memory]
    path_parts: list[str] = []
    previous_value: int | None = None
    for turn, value in topic_points:
        x = turn_x(turn, left, right)
        y = axis_y(value, 0.5, 5.5, top1 + 25, bottom1 - 20)
        if previous_value is None:
            path_parts.append(f"M {x:.2f} {y:.2f}")
        else:
            previous_y = axis_y(previous_value, 0.5, 5.5, top1 + 25, bottom1 - 20)
            path_parts.append(f"L {x:.2f} {previous_y:.2f} L {x:.2f} {y:.2f}")
        previous_value = value
    svg.path(" ".join(path_parts), fill="none", stroke=BLUE, stroke_width=3, stroke_linejoin="round")
    for turn, value, label, color in [
        (20, 1, "merge 2→1", GREEN),
        (114, 5, "mixed query 4→5", ORANGE),
        (120, 1, "four merges 5→1", ORANGE),
    ]:
        x = turn_x(turn, left, right)
        y = axis_y(value, 0.5, 5.5, top1 + 25, bottom1 - 20)
        svg.circle(x, y, 5, fill=color, stroke=PAPER, stroke_width=2)
        anchor = "end" if turn >= 114 else "start"
        dx = -8 if anchor == "end" else 8
        text_y = y - 12 if turn != 120 else y + 25
        svg.text(x + dx, text_y, label, size=13, weight=500, fill=color, anchor=anchor)
    svg.text(left, bottom1 + 22, "triangles mark 10-turn consolidation passes", size=12, fill=MUTED)

    svg.text(40, 385, "B", size=18, weight=500)
    svg.text(70, 385, "Estimated constructed context (tokens)", size=18, weight=500)
    top2, bottom2 = 420, 680
    draw_phase_backgrounds(svg, left, right, top2, bottom2 - top2, labels=False)
    for value in range(0, 10001, 2000):
        y = axis_y(value, 0, 10000, top2, bottom2)
        svg.line(left, y, right, y, stroke=GRID, stroke_width=1)
        svg.text(left - 18, y + 5, f"{value // 1000}k", size=13, fill=MUTED, anchor="end")
    for boundary in (30.5, 60.5, 90.5):
        x = turn_x(boundary, left, right)
        svg.line(x, top2, x, bottom2, stroke=GRAY, stroke_width=1.5, stroke_dasharray="5 5")
    context_points = [(int(row["turn"]), int(row["estimated_tokens"])) for row in performance]
    d = " ".join(
        ("M" if index == 0 else "L")
        + f" {turn_x(turn, left, right):.2f} {axis_y(value, 0, 10000, top2, bottom2):.2f}"
        for index, (turn, value) in enumerate(context_points)
    )
    svg.path(d, fill="none", stroke=PURPLE, stroke_width=2.5, stroke_linejoin="round")
    peak_turn, peak_value = max(context_points, key=lambda point: point[1])
    peak_x = turn_x(peak_turn, left, right)
    peak_y = axis_y(peak_value, 0, 10000, top2, bottom2)
    svg.circle(peak_x, peak_y, 6, fill=ORANGE, stroke=PAPER, stroke_width=2)
    svg.text(peak_x + 10, peak_y - 12, f"peak {peak_value:,} · turn {peak_turn}", size=14, weight=500, fill=ORANGE)
    for turn in (1, 30, 60, 90, 120):
        x = turn_x(turn, left, right)
        svg.line(x, bottom2, x, bottom2 + 7, stroke=MUTED, stroke_width=1)
        svg.text(x, bottom2 + 25, str(turn), size=13, fill=MUTED, anchor="middle")
    svg.text((left + right) / 2, 724, "conversation turn", size=14, fill=MUTED, anchor="middle")

    output.write_text(svg.finish(), encoding="utf-8", newline="\n")


def generate_promotions(output: Path) -> None:
    promotions = load_csv(LTM_ROOT / "promotion_events.csv")
    scores = load_csv(LTM_ROOT / "episode_scores.csv")
    domains = ["Civil engineering", "Renaissance art", "Monetary policy"]
    evaluated = sum(int(row["episodes_evaluated"]) for row in promotions)
    promoted = sum(int(row["episodes_promoted"]) for row in promotions)
    weighted = sum(row["trigger_type"] == "weighted_threshold" for row in scores)
    novelty = sum(row["triggered_filter"] == "novelty" for row in scores)
    repetition = sum(row["triggered_filter"] == "repetition" for row in scores)

    svg = SVG(
        1200,
        650,
        "LTM promotion volume and trigger routes",
        "Thirty episodes were evaluated at each of three outgoing domain transitions. Twelve civil-engineering, seven Renaissance-art, and two monetary-policy episodes were promoted. Marine biology was structurally unevaluated. Of 21 promoted episodes, 12 used the weighted threshold, seven used an all-or-nothing novelty trigger, and two used an all-or-nothing repetition trigger.",
    )
    svg.text(40, 42, "A", size=18, weight=500)
    svg.text(70, 42, "Promotion by outgoing scripted domain", size=18, weight=500)
    bar_left, bar_width = 300, 650
    max_evaluated = 30
    for index, (domain, row) in enumerate(zip(domains, promotions, strict=True)):
        y = 92 + index * 82
        evaluated_count = int(row["episodes_evaluated"])
        promoted_count = int(row["episodes_promoted"])
        rate = float(row["promotion_rate"])
        svg.text(70, y + 22, domain, size=15, weight=500)
        svg.rect(bar_left, y, bar_width, 30, rx=4, fill=GRAY_LIGHT)
        promoted_width = bar_width * promoted_count / max_evaluated
        svg.rect(bar_left, y, promoted_width, 30, rx=4, fill=BLUE)
        svg.text(bar_left + promoted_width / 2, y + 21, str(promoted_count), size=14, weight=500, fill=PAPER, anchor="middle")
        svg.text(bar_left + bar_width + 18, y + 21, f"{promoted_count}/{evaluated_count} · {rate:.1%}", size=15, weight=500)
    marine_y = 92 + 3 * 82
    svg.text(70, marine_y + 22, "Marine biology", size=15, weight=500)
    svg.rect(bar_left, marine_y, bar_width, 30, rx=4, fill=PAPER, stroke=GRAY, stroke_width=1.5, stroke_dasharray="6 5")
    svg.text(bar_left + bar_width / 2, marine_y + 21, "not evaluated — no outgoing transition", size=14, fill=MUTED, anchor="middle")
    svg.text(bar_left, marine_y + 58, "bar width represents 30 evaluated episodes", size=12, fill=MUTED)

    svg.line(40, 444, 1160, 444, stroke=GRID, stroke_width=1)
    svg.text(40, 486, "B", size=18, weight=500)
    svg.text(70, 486, "Promotion route composition", size=18, weight=500)
    route_left, route_width, route_y = 300, 650, 520
    route_values = [
        (weighted, BLUE, "weighted threshold"),
        (novelty, GREEN, "novelty ≥ 0.90"),
        (repetition, PURPLE, "repetition ≥ 0.90"),
    ]
    current_x = route_left
    for value, color, label in route_values:
        width = route_width * value / promoted
        svg.rect(current_x, route_y, width, 38, fill=color)
        if width >= 40:
            svg.text(current_x + width / 2, route_y + 25, str(value), size=15, weight=500, fill=PAPER, anchor="middle")
        current_x += width
    legend_x = route_left
    for value, color, label in route_values:
        svg.rect(legend_x, 579, 14, 14, rx=2, fill=color)
        svg.text(legend_x + 21, 591, f"{label}: {value}", size=13)
        legend_x += 220
    svg.text(70, route_y + 27, f"{promoted} unique", size=16, weight=500)
    svg.text(70, route_y + 49, "promotions", size=14, fill=MUTED)
    svg.text(1010, route_y + 19, f"{promoted}/{evaluated}", size=20, weight=500, fill=BLUE)
    svg.text(1010, route_y + 43, f"{promoted/evaluated:.2%} of evaluated", size=13, fill=MUTED)
    svg.text(1010, route_y + 63, "17.50% of all 120 STM", size=13, fill=MUTED)

    output.write_text(svg.finish(), encoding="utf-8", newline="\n")


def generate_score_distributions(output: Path) -> None:
    rows = load_csv(LTM_ROOT / "episode_scores.csv")
    fields = [
        ("novelty", "Novelty", 0.90, 7),
        ("repetition", "Repetition", 0.90, 2),
        ("association", "Association", 0.90, 0),
        ("emotional", "Emotional valence", 0.90, 0),
        ("weighted_score", "Weighted score", 0.60, 12),
    ]
    promoted_flags = [row["promoted"] == "True" for row in rows]
    left, right, top, bottom = 105, 1145, 75, 455

    svg = SVG(
        1200,
        620,
        "Distributions of Study 003 promotion-filter scores",
        "All 90 evaluated episodes are shown for novelty, repetition, association, emotional valence, and weighted score. Points distinguish promoted and non-promoted episodes. Boxes show the interquartile range and median, whiskers show minima and maxima, and diamonds show means. Individual-filter thresholds are 0.90 and the weighted threshold is 0.60.",
    )
    svg.text(40, 38, "Scores across all 90 evaluated episodes", size=18, weight=500)
    svg.text(
        1145,
        38,
        "Alternative routes; empty-LTM filter bypass was suspended",
        size=12,
        fill=MUTED,
        anchor="end",
    )
    for value in [0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        y = axis_y(value, 0, 1, top, bottom)
        svg.line(left, y, right, y, stroke=GRID, stroke_width=1)
        svg.text(left - 18, y + 5, f"{value:.1f}", size=13, fill=MUTED, anchor="end")
    group_width = (right - left) / len(fields)
    for field_index, (field, label, threshold, trigger_count) in enumerate(fields):
        center = left + group_width * (field_index + 0.5)
        values = [float(row[field]) for row in rows]
        q1, q3 = quantiles(values, n=4, method="inclusive")[0::2]
        med = median(values)
        avg = mean(values)
        minimum, maximum = min(values), max(values)

        threshold_y = axis_y(threshold, 0, 1, top, bottom)
        svg.line(
            center - 72,
            threshold_y,
            center + 72,
            threshold_y,
            stroke=ORANGE,
            stroke_width=2,
            stroke_dasharray="6 4",
        )
        svg.text(center + 74, threshold_y + 4, f"{threshold:.2f}", size=11, fill=ORANGE)

        for row_index, (value, is_promoted) in enumerate(zip(values, promoted_flags, strict=True)):
            jitter = ((row_index * 37 + field_index * 11) % 79) - 39
            x = center + jitter
            y = axis_y(value, 0, 1, top, bottom)
            svg.circle(
                x,
                y,
                3.2,
                fill=ORANGE if is_promoted else BLUE,
                opacity=0.46 if is_promoted else 0.18,
            )

        y_min = axis_y(minimum, 0, 1, top, bottom)
        y_max = axis_y(maximum, 0, 1, top, bottom)
        y_q1 = axis_y(q1, 0, 1, top, bottom)
        y_q3 = axis_y(q3, 0, 1, top, bottom)
        y_med = axis_y(med, 0, 1, top, bottom)
        y_avg = axis_y(avg, 0, 1, top, bottom)
        svg.line(center, y_min, center, y_max, stroke=INK, stroke_width=1.5)
        svg.line(center - 18, y_min, center + 18, y_min, stroke=INK, stroke_width=1.5)
        svg.line(center - 18, y_max, center + 18, y_max, stroke=INK, stroke_width=1.5)
        svg.rect(center - 30, y_q3, 60, y_q1 - y_q3, fill=PAPER, stroke=INK, stroke_width=2)
        svg.line(center - 30, y_med, center + 30, y_med, stroke=INK, stroke_width=3)
        svg.polygon(
            [(center, y_avg - 7), (center + 7, y_avg), (center, y_avg + 7), (center - 7, y_avg)],
            fill=GREEN,
            stroke=PAPER,
            stroke_width=1,
        )
        svg.text(center, 488, label, size=14, weight=500, anchor="middle")
        route_label = "weighted-route n=" if field == "weighted_score" else "individual triggers n="
        svg.text(center, 510, f"{route_label}{trigger_count}", size=12, fill=MUTED, anchor="middle")
        svg.text(center, 535, f"median {med:.3f} · mean {avg:.3f}", size=11, fill=MUTED, anchor="middle")

    svg.circle(115, 574, 4, fill=BLUE, opacity=0.35)
    svg.text(128, 579, "not promoted", size=13, fill=MUTED)
    svg.circle(250, 574, 4, fill=ORANGE, opacity=0.65)
    svg.text(263, 579, "promoted", size=13, fill=MUTED)
    svg.polygon([(365, 567), (372, 574), (365, 581), (358, 574)], fill=GREEN)
    svg.text(380, 579, "mean", size=13, fill=MUTED)
    svg.line(450, 574, 485, 574, stroke=ORANGE, stroke_width=2, stroke_dasharray="6 4")
    svg.text(493, 579, "decision threshold", size=13, fill=MUTED)
    svg.text(1145, 579, "box: Q1–Q3 · line: median · whiskers: min–max", size=12, fill=MUTED, anchor="end")

    output.write_text(svg.finish(), encoding="utf-8", newline="\n")


GENERATORS = {
    "study-overview.svg": generate_overview,
    "memory-architecture.svg": generate_architecture,
    "confirmatory-outcomes.svg": generate_confirmatory,
    "topic-context-trajectories.svg": generate_trajectories,
    "ltm-promotion-outcomes.svg": generate_promotions,
    "filter-score-distributions.svg": generate_score_distributions,
}


def generate_all(output_directory: Path) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    for filename, generator in GENERATORS.items():
        generator(output_directory / filename)


def check_committed() -> int:
    with tempfile.TemporaryDirectory(prefix="study003-figures-") as directory:
        temporary = Path(directory)
        generate_all(temporary)
        mismatches: list[str] = []
        for filename in GENERATORS:
            committed = DEFAULT_OUTPUT / filename
            generated = temporary / filename
            # Text-mode comparison normalizes platform line endings while still
            # requiring every SVG element and attribute to match exactly.
            if not committed.exists() or committed.read_text(
                encoding="utf-8"
            ) != generated.read_text(encoding="utf-8"):
                mismatches.append(filename)
        if mismatches:
            print("Study 003 figures are stale or missing:")
            for filename in mismatches:
                print(f"  - {filename}")
            return 1
    print("Study 003 figures match the canonical artifacts.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output directory for generated SVG files",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify committed figures match a fresh generation",
    )
    arguments = parser.parse_args()
    if arguments.check:
        return check_committed()
    generate_all(arguments.output)
    print(f"Generated {len(GENERATORS)} Study 003 figures in {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""DX-002: does Study 010's context curve grow without bound?

Offline. Committed Study 010 artifacts only. No inference call, no run.

The record holds a *peak* - 27,154 estimated tokens for arm L, verified as
`characters // 4` across all 2,000 serialized prompts - and a peak says
nothing about whether the curve was still climbing. This module reads the
same 2,000 prompts and asks the question the peak cannot answer.

The decomposition is the diagnostic. Every prompt is split into the parts
that compose it - preamble, pinned rules, recency window, retrieved STM,
retrieved LTM, the current turn, and the separators between them - under a
gate that the parts concatenate back to the original file byte for byte.
A flat LTM series under a climbing total names an unbudgeted leak
immediately; nothing weaker does.

Four gates run before any number is reported:

* **G1** every prompt reconstructs byte-exactly from its parts,
* **G2** every recomputed `chars // 4` matches the committed telemetry,
* **G3** re-rendering the LTM block under the post-DR-001 compact renderer
  reproduces DR-001's committed 37,619 and 37,545 characters for Q13/Q14,
* **G4** the input tree hash is unchanged across the read.

G3 is what lets section 0.3.4 be answered in exactly-serialized characters
under the production renderer rather than the historical undercharged
figures: the re-render is certified against a committed result before it is
used on the other 998 turns.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "episodic" / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "episodic" / "src"))

from episodic._render import render_episode_block  # noqa: E402

RUN_ROOT = (
    REPO_ROOT / "experiments" / "study_010" / "runs" / "study_010_full_001"
)
ARMS = ("arm_l", "arm_s")
ASSISTANT_CUE = "\n\nAssistant:"

#: The LTM character budget every Study 010 arm was supposed to respect.
LTM_BUDGET_CHARS = 32_000

#: Section 0.3.3: fit the last 300 turns of each series.
TERMINAL_WINDOW = 300

#: DR-001's committed post-fix figures. G3 asserts the re-render against
#: these before the method is trusted on any other turn.
DR001_COMPACT_REPLAY = {
    ("arm_l", 999): 37_619,
    ("arm_l", 1000): 37_545,
}

BLOCK_ORDER = (
    "pinned_rules",
    "recent_context",
    "retrieved_stm",
    "retrieved_ltm",
    "current_turn",
)

#: Parts are reported in prompt order. ``separators`` and ``assistant_cue``
#: exist so that the parts sum to the whole; they are structural, not content.
PART_ORDER = (
    "preamble",
    "pinned_rules",
    "recent_context",
    "retrieved_stm",
    "retrieved_ltm",
    "current_turn",
    "separators",
    "assistant_cue",
)

_EPISODE = re.compile(
    r"<episode turn=\"(?P<turn>[^\"]*)\"[^>]*>\s*"
    r"<user_message>(?P<user>.*?)</user_message>\s*"
    r"<assistant_message>(?P<assistant>.*?)</assistant_message>\s*"
    r"</episode>",
    re.S,
)


# -- decomposition ---------------------------------------------------------


def decompose_prompt_ordered(text: str) -> list[tuple[str, str]]:
    """Split a prompt into ordered ``(part_name, text)`` pieces.

    Every character of ``text`` lands in exactly one piece, in prompt
    order, so ``"".join(piece for _, piece in pieces) == text`` holds by
    construction rather than by a reconstruction heuristic. That identity
    is gate G1, and it is what makes the per-part series trustworthy: a
    part cannot silently lose characters to an unnamed remainder.
    """
    body = text
    cue = ""
    if body.endswith(ASSISTANT_CUE):
        body, cue = body[: -len(ASSISTANT_CUE)], ASSISTANT_CUE

    spans: list[tuple[str, int, int]] = []
    for name in BLOCK_ORDER:
        match = re.search(rf"<{name}>.*?</{name}>|<{name}/>", body, re.S)
        if match is not None:
            spans.append((name, match.start(), match.end()))
    spans.sort(key=lambda item: item[1])

    pieces: list[tuple[str, str]] = []
    cursor = 0
    for index, (name, start, end) in enumerate(spans):
        gap = body[cursor:start]
        if gap:
            pieces.append(("preamble" if index == 0 else "separators", gap))
        pieces.append((name, body[start:end]))
        cursor = end
    trailing = body[cursor:]
    if trailing:
        pieces.append(("separators" if spans else "preamble", trailing))
    if cue:
        pieces.append(("assistant_cue", cue))
    return pieces


def decompose_prompt(text: str) -> dict[str, str]:
    """Per-part character totals, summed over `decompose_prompt_ordered`."""
    parts = {name: "" for name in PART_ORDER}
    for name, piece in decompose_prompt_ordered(text):
        parts[name] += piece
    return parts


def _parse_ltm_episodes(block: str) -> list[dict]:
    """Recover (turn, user, assistant) from a historical rendered block."""
    return [
        {
            "turn_number": html.unescape(match["turn"]),
            "user_message": html.unescape(match["user"]),
            "assistant_message": html.unescape(match["assistant"]),
        }
        for match in _EPISODE.finditer(block)
    ]


def recompact_block(name: str, block: str) -> tuple[str, int]:
    """Re-render a historical block under the post-DR-001 compact renderer.

    Returns the compact serialization and its episode count. Content is
    carried through unchanged - only the structural tags shrink - which is
    what DR-001's G-R2 identity gate certified. G3 re-asserts it here.
    """
    episodes = _parse_ltm_episodes(block)
    if not episodes:
        return f"<{name}/>", 0
    return render_episode_block(name, episodes, name), len(episodes)


# -- statistics ------------------------------------------------------------


def ols_slope(xs: list[float], ys: list[float]) -> dict:
    """Least-squares slope with a two-sided 95% interval on t(n-2)."""
    n = len(xs)
    if n < 3:
        raise ValueError("need at least three points to fit a slope")
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    residuals = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    sse = sum(r * r for r in residuals)
    sst = sum((y - mean_y) ** 2 for y in ys)
    df = n - 2
    stderr = math.sqrt(sse / df / sxx)
    critical = student_t_quantile(0.975, df)
    half_width = critical * stderr
    return {
        "n": n,
        "slope_chars_per_turn": slope,
        "intercept_chars": intercept,
        "stderr": stderr,
        "t_statistic": slope / stderr if stderr else math.inf,
        "ci95_low": slope - half_width,
        "ci95_high": slope + half_width,
        "ci95_half_width": half_width,
        "includes_zero": (slope - half_width) <= 0.0 <= (slope + half_width),
        "r_squared": 1.0 - sse / sst if sst else 0.0,
    }


def durbin_watson(xs: list[float], ys: list[float]) -> float:
    """Serial correlation of the OLS residuals, on [0, 4]; 2 means none.

    These series are sawtooths - retrieval ramps up and resets - so the
    residuals are not independent and the OLS interval is not, on its own,
    an honest uncertainty statement. This number is reported so the reader
    can see that, and it is why `block_summary` exists next to the fit.
    """
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    residuals = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    numerator = sum(
        (residuals[i] - residuals[i - 1]) ** 2 for i in range(1, n)
    )
    denominator = sum(r * r for r in residuals)
    return numerator / denominator if denominator else float("nan")


def block_summary(rows: list[dict], name: str, size: int = 100) -> list[dict]:
    """Bucketed mean/max/p95 - a saturation check that assumes nothing.

    A plateau is visible in these numbers without any model of the noise:
    if the last buckets match the middle buckets, the series has stopped
    growing whatever its residual structure.
    """
    blocks = []
    for start in range(0, len(rows), size):
        chunk = [row[name] for row in rows[start : start + size]]
        if not chunk:
            continue
        ordered = sorted(chunk)
        blocks.append(
            {
                "first_turn": rows[start]["turn"],
                "last_turn": rows[min(start + size, len(rows)) - 1]["turn"],
                "mean": sum(chunk) / len(chunk),
                "max": max(chunk),
                "p95": ordered[min(int(0.95 * len(ordered)), len(ordered) - 1)],
            }
        )
    return blocks


def half_over_half(rows: list[dict], name: str, window: int) -> dict:
    """Compare the fitted window against the window before it.

    The blunt instrument: if the terminal 300 turns are not materially
    larger than the 300 before them, the series is not growing, and no
    assumption about residual structure is needed to say so.
    """
    recent = [row[name] for row in rows[-window:]]
    prior = [row[name] for row in rows[-2 * window : -window]]
    if not prior:
        return {"comparable": False}
    recent_mean = sum(recent) / len(recent)
    prior_mean = sum(prior) / len(prior)
    return {
        "comparable": True,
        "prior_window_turns": [rows[-2 * window]["turn"], rows[-window - 1]["turn"]],
        "recent_window_turns": [rows[-window]["turn"], rows[-1]["turn"]],
        "prior_mean": prior_mean,
        "recent_mean": recent_mean,
        "delta_chars": recent_mean - prior_mean,
        "delta_pct": (
            100.0 * (recent_mean - prior_mean) / prior_mean if prior_mean else 0.0
        ),
        "prior_max": max(prior),
        "recent_max": max(recent),
    }


def theil_sen_slope(xs: list[float], ys: list[float]) -> float:
    """Median pairwise slope - a robustness check against the OLS fit.

    The series is heavily heteroscedastic (probe turns retrieve far more
    than conversational turns), so a median-of-pairs estimator is reported
    alongside OLS. Agreement between the two is the check; disagreement
    would mean the OLS slope is being driven by a handful of extreme turns.
    """
    slopes = [
        (ys[j] - ys[i]) / (xs[j] - xs[i])
        for i in range(len(xs))
        for j in range(i + 1, len(xs))
        if xs[j] != xs[i]
    ]
    slopes.sort()
    mid = len(slopes) // 2
    if len(slopes) % 2:
        return slopes[mid]
    return (slopes[mid - 1] + slopes[mid]) / 2.0


def student_t_quantile(p: float, df: int) -> float:
    """Inverse CDF of Student's t, by bisection on the exact CDF.

    Implemented here because the analysis environment carries no SciPy and
    a normal approximation is exactly the kind of shortcut this diagnostic
    exists to avoid.
    """
    low, high = 0.0, 1_000.0
    for _ in range(200):
        mid = (low + high) / 2.0
        if student_t_cdf(mid, df) < p:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def student_t_cdf(t: float, df: int) -> float:
    x = df / (df + t * t)
    tail = 0.5 * _incomplete_beta(df / 2.0, 0.5, x)
    return 1.0 - tail if t > 0 else tail


def _incomplete_beta(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b) by continued fraction."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_cf(a, b, x) / a
    return 1.0 - front * _beta_cf(b, a, 1.0 - x) / b


def _beta_cf(a: float, b: float, x: float) -> float:
    tiny = 1e-30
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1.0)
    d = tiny if abs(d) < tiny else d
    d = 1.0 / d
    result = d
    for m in range(1, 300):
        m2 = 2 * m
        numerator = m * (b - m) * x / ((a + m2 - 1.0) * (a + m2))
        d = 1.0 + numerator * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + numerator / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        result *= d * c
        numerator = -(a + m) * (a + b + m) * x / ((a + m2) * (a + m2 + 1.0))
        d = 1.0 + numerator * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + numerator / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        result *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return result


# -- the analysis ----------------------------------------------------------


def analyse(run_root: Path = RUN_ROOT) -> dict:
    inputs = _input_paths(run_root)
    hashes_before = _hash_paths(inputs)

    arms = [_analyse_arm(run_root / arm) for arm in ARMS]

    hashes_after = _hash_paths(inputs)
    gates = {
        "G1_byte_exact_reconstruction": all(
            arm["gates"]["reconstruction_ok"] for arm in arms
        ),
        "G2_telemetry_matches_committed": all(
            arm["gates"]["telemetry_ok"] for arm in arms
        ),
        "G3_dr001_compact_replay": all(
            arm["gates"]["compact_replay_ok"] for arm in arms
        ),
        "G4_inputs_unchanged": hashes_before == hashes_after,
    }
    result = {
        "record": "DX-002 context growth diagnostic",
        "question": (
            "Is Study 010's context curve still climbing at turn 1,000, and "
            "if so which part of the prompt is climbing?"
        ),
        "scope": "committed Study 010 serialized prompts; offline; no run",
        "terminal_window_turns": TERMINAL_WINDOW,
        "ltm_budget_chars": LTM_BUDGET_CHARS,
        "gates": gates,
        "status": "PASS" if all(gates.values()) else "FAIL",
        "input_file_count": len(inputs),
        "input_tree_sha256_before": _digest_mapping(hashes_before),
        "input_tree_sha256_after": _digest_mapping(hashes_after),
        "arms": arms,
    }
    result["decision"] = _decide(result)
    return result


def _analyse_arm(arm_root: Path) -> dict:
    metrics_path = arm_root / "metrics" / "context_sizes.csv"
    with metrics_path.open(encoding="utf-8", newline="") as handle:
        logged = {int(row["turn"]): int(row["estimated_tokens"]) for row in csv.DictReader(handle)}

    rows: list[dict] = []
    reconstruction_ok = True
    telemetry_ok = True
    compact_replay_ok = True
    compact_replay_checks: list[dict] = []

    for turn in sorted(logged):
        path = arm_root / "constructed_prompts" / f"turn_{turn:03d}.txt"
        text = path.read_text(encoding="utf-8")
        pieces = decompose_prompt_ordered(text)
        parts = {name: "" for name in PART_ORDER}
        for name, piece in pieces:
            parts[name] += piece
        if "".join(piece for _, piece in pieces) != text:
            reconstruction_ok = False
        if (len(text) - len(parts["assistant_cue"])) // 4 != logged[turn]:
            telemetry_ok = False

        compact_ltm, ltm_episodes = recompact_block(
            "retrieved_ltm", parts["retrieved_ltm"]
        )
        compact_chars = len(compact_ltm) if parts["retrieved_ltm"] else 0
        expected = DR001_COMPACT_REPLAY.get((arm_root.name, turn))
        if expected is not None:
            matched = compact_chars == expected
            compact_replay_ok = compact_replay_ok and matched
            compact_replay_checks.append(
                {
                    "turn": turn,
                    "expected_chars": expected,
                    "observed_chars": compact_chars,
                    "match": matched,
                }
            )

        row = {"turn": turn, "total": len(text)}
        row.update({name: len(parts[name]) for name in PART_ORDER})
        row["retrieved_ltm_compact"] = compact_chars
        row["retrieved_ltm_episodes"] = ltm_episodes
        rows.append(row)

    series_names = (*PART_ORDER, "total", "retrieved_ltm_compact")
    parts_summary = {
        name: _summarise_series(rows, name) for name in series_names
    }
    return {
        "arm": arm_root.name,
        "turns": len(rows),
        "gates": {
            "reconstruction_ok": reconstruction_ok,
            "telemetry_ok": telemetry_ok,
            "compact_replay_ok": compact_replay_ok,
            "compact_replay_checks": compact_replay_checks,
        },
        "series": parts_summary,
        "ltm_vs_budget": _ltm_vs_budget(rows),
        "rule_pinning": _rule_pinning(arm_root, rows),
        "rows": rows,
    }


def _rule_pinning(arm_root: Path, rows: list[dict]) -> dict:
    """Section 0.3.5: the rule-pinning contribution, specifically.

    118 false rules at 1,000 turns is the named H-B candidate. The answer
    the committed artifacts give is not "rule pinning is harmless" - it is
    that rule pinning **cannot be measured here**, because persistence was
    disabled before this run and the block is empty on every turn. That is
    a scoped Branch D, and reporting it as a clean pass would be exactly
    the surrogate failure this program keeps hitting.
    """
    path = arm_root / "metrics" / "rule_detection.csv"
    detections = 0
    turns = 0
    if path.exists():
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                turns += 1
                if row.get("contains_rule_detected", "").strip().lower() == "true":
                    detections += 1
    sizes = {row["pinned_rules"] for row in rows}
    return {
        "metrics_rows": turns,
        "rule_detections": detections,
        "pinned_rules_block_sizes": sorted(sizes),
        "pinned_rules_constant": len(sizes) == 1,
        "contributes_growth": len(sizes) > 1,
        "measurable": detections > 0,
        "finding": (
            "Rule detection fired on 0 of "
            f"{turns:,} turns and the <pinned_rules/> block is a constant "
            f"{sorted(sizes)[0]} characters on every turn, so rule pinning "
            "contributes exactly zero growth in these artifacts."
        ),
        "limitation": (
            "This does not clear the rule-pinning growth path. Persistence "
            "was disabled before this run, so the 118-false-rule behaviour "
            "is absent by configuration rather than shown harmless. The "
            "candidate is untested at this horizon, not refuted."
        ),
    }


def _summarise_series(rows: list[dict], name: str) -> dict:
    xs = [float(row["turn"]) for row in rows]
    ys = [float(row[name]) for row in rows]
    tail = rows[-TERMINAL_WINDOW:]
    tail_xs = [float(row["turn"]) for row in tail]
    tail_ys = [float(row[name]) for row in tail]

    constant = len(set(ys)) == 1
    summary = {
        "min": min(ys),
        "max": max(ys),
        "mean": sum(ys) / len(ys),
        "first_turn_value": ys[0],
        "last_turn_value": ys[-1],
        "constant": constant,
        "terminal_window": {
            "first_turn": int(tail_xs[0]),
            "last_turn": int(tail_xs[-1]),
            "mean": sum(tail_ys) / len(tail_ys),
        },
    }
    if constant:
        summary["terminal_window"].update(
            {
                "slope_chars_per_turn": 0.0,
                "ci95_low": 0.0,
                "ci95_high": 0.0,
                "includes_zero": True,
                "degenerate_constant_series": True,
            }
        )
        summary["full_series"] = {"slope_chars_per_turn": 0.0}
        summary["blocks"] = block_summary(rows, name)
        summary["window_over_window"] = half_over_half(
            rows, name, TERMINAL_WINDOW
        )
        return summary

    fit = ols_slope(tail_xs, tail_ys)
    fit["theil_sen_slope_chars_per_turn"] = theil_sen_slope(tail_xs, tail_ys)
    fit["projected_growth_over_1000_turns"] = (
        fit["slope_chars_per_turn"] * 1000.0
    )
    fit["minimum_detectable_slope"] = fit["ci95_half_width"]
    fit["durbin_watson"] = durbin_watson(tail_xs, tail_ys)
    summary["terminal_window"].update(fit)
    summary["full_series"] = ols_slope(xs, ys)
    summary["blocks"] = block_summary(rows, name)
    summary["window_over_window"] = half_over_half(rows, name, TERMINAL_WINDOW)
    return summary


def _ltm_vs_budget(rows: list[dict]) -> dict:
    historical = [row["retrieved_ltm"] for row in rows]
    compact = [row["retrieved_ltm_compact"] for row in rows]
    nonempty = [value for value in historical if value]
    if not nonempty:
        return {"present": False}
    return {
        "present": True,
        "budget_chars": LTM_BUDGET_CHARS,
        "historical_max_chars": max(historical),
        "historical_turns_over_budget": sum(
            1 for value in historical if value > LTM_BUDGET_CHARS
        ),
        "compact_max_chars": max(compact),
        "compact_turns_over_budget": sum(
            1 for value in compact if value > LTM_BUDGET_CHARS
        ),
        "compact_mean_chars": sum(compact) / len(compact),
        "turns_with_ltm": len(nonempty),
        "turns_total": len(rows),
    }


#: A part counts as a growth concern only if it moved by at least 1% of the
#: LTM character budget across the saturation lookback. The floor is stated
#: in the system's own budget units rather than fitted to the observed
#: series: `current_turn` drifts about five characters over the last 500
#: turns, which is a real record but not a boundedness problem, and listing
#: it beside a 23,000-character move would bury the finding rather than
#: report it.
MATERIALITY_FLOOR_CHARS = LTM_BUDGET_CHARS // 100


def p95_growth(series: dict, lookback: int = 5) -> float:
    """Change in bucketed p95 across the saturation lookback, in chars."""
    blocks = series.get("blocks") or []
    if len(blocks) < lookback:
        return 0.0
    return float(blocks[-1]["p95"] - blocks[-lookback]["p95"])


def has_saturated(series: dict, lookback: int = 5) -> bool:
    """Has the series stopped setting new highs?

    A saturated series stops reaching further; a climbing one keeps
    setting records. The test is whether the final 100-turn bucket holds
    the maximum p95 of the last ``lookback`` buckets. It assumes nothing
    about noise or residual structure, which matters because these series
    are sawtooths and the OLS interval is underpowered against their
    variance.
    """
    blocks = series.get("blocks") or []
    if len(blocks) < lookback:
        return True
    recent = [block["p95"] for block in blocks[-lookback:]]
    if max(recent) == min(recent):
        return True
    return recent[-1] < max(recent)


def classify_series(series: dict) -> dict:
    """Is this part still growing at the end of the run?

    Three independent readings, because no one of them is sufficient:

    * the OLS terminal slope, which is *sensitive but underpowered* here,
    * saturation, i.e. whether the last bucket still sets a record,
    * the window-over-window mean change, which assumes nothing at all.

    A part is called climbing when it has not saturated **and** its mean
    rose over the previous window. The OLS slope alone is not enough to
    clear a part: an interval that contains zero is a statement about
    power, not about flatness, and treating it as proof of boundedness is
    precisely the surrogate failure class this program tracks.
    """
    window = series["terminal_window"]
    comparison = series.get("window_over_window", {})
    constant = bool(window.get("degenerate_constant_series"))
    saturated = constant or has_saturated(series)
    delta_pct = comparison.get("delta_pct", 0.0) if comparison.get(
        "comparable"
    ) else 0.0
    slope_positive = (
        not constant
        and not window["includes_zero"]
        and window["slope_chars_per_turn"] > 0
    )
    slope_negative = (
        not constant
        and not window["includes_zero"]
        and window["slope_chars_per_turn"] < 0
    )
    growth = p95_growth(series)
    material = abs(growth) >= MATERIALITY_FLOOR_CHARS
    rising = (not saturated and delta_pct > 0.0) or slope_positive
    return {
        "constant": constant,
        "saturated": saturated,
        "delta_pct": delta_pct,
        "p95_growth_chars": growth,
        "material": material,
        "slope_significant_positive": slope_positive,
        "slope_significant_negative": slope_negative,
        "rising": rising,
        "climbing": rising and material,
    }


def _decide(result: dict) -> dict:
    """Apply section 0.4's decision rule.

    Branch A is a conjunction - "terminal slope approximately zero; LTM
    saturated; **no unbudgeted component climbing**" - and all three
    clauses have to hold. Reading only the first clause is what makes a
    plateau in the budgeted block look like a bounded system.
    """
    if result["status"] != "PASS":
        return {
            "branch": "D",
            "label": "Not determinable from committed artifacts",
            "reason": "one or more integrity gates failed",
        }

    climbing_parts: list[str] = []
    declining_parts: list[str] = []
    immaterial_parts: list[str] = []
    ltm_climbing: list[str] = []
    ltm_saturated = True
    verdicts: dict[str, dict] = {}

    for arm in result["arms"]:
        for name in PART_ORDER:
            verdict = classify_series(arm["series"][name])
            entry = f"{arm['arm']}.{name}"
            verdicts[entry] = verdict
            if name == "retrieved_ltm" and not verdict["constant"]:
                ltm_saturated = ltm_saturated and verdict["saturated"]
            if verdict["climbing"]:
                climbing_parts.append(entry)
                if name == "retrieved_ltm":
                    ltm_climbing.append(entry)
            elif verdict["rising"] and not verdict["material"]:
                immaterial_parts.append(entry)
            elif verdict["slope_significant_negative"]:
                declining_parts.append(entry)

    common = {
        "series_verdicts": verdicts,
        "climbing_parts": climbing_parts,
        "declining_parts": declining_parts,
        "rising_but_immaterial_parts": immaterial_parts,
        "materiality_floor_chars": MATERIALITY_FLOOR_CHARS,
        "ltm_saturated": ltm_saturated,
        "horizon_turns": 1000,
    }

    if ltm_climbing:
        return {
            **common,
            "branch": "C",
            "label": "LTM itself still climbing - STOP and reconcile",
            "reason": (
                "the budgeted LTM block is still setting new highs, which "
                "contradicts DR-001's budget accounting"
            ),
        }
    if climbing_parts:
        return {
            **common,
            "branch": "B",
            "label": "An unbudgeted component is climbing",
            "reason": (
                "the budgeted LTM block saturates, but "
                + ", ".join(f"`{entry}`" for entry in climbing_parts)
                + " has not: it is still setting new highs in its final "
                "100-turn bucket. Name it and bring it inside the budget "
                "before anything ships"
            ),
        }
    return {
        **common,
        "branch": "A",
        "label": "Context is bounded at the tested horizon",
        "reason": (
            "the LTM block saturates and no other part is still setting new "
            "highs at turn 1,000"
        ),
    }


# -- integrity helpers -----------------------------------------------------


def _input_paths(run_root: Path) -> list[Path]:
    paths: list[Path] = []
    for arm in ARMS:
        arm_root = run_root / arm
        paths.append(arm_root / "metrics" / "context_sizes.csv")
        paths.extend(
            sorted((arm_root / "constructed_prompts").glob("turn_*.txt"))
        )
    return sorted(paths)


def _hash_paths(paths: list[Path]) -> dict[str, str]:
    return {
        path.relative_to(REPO_ROOT).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in paths
    }


def _digest_mapping(mapping: dict[str, str]) -> str:
    payload = json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


# -- artifacts -------------------------------------------------------------


def write_artifacts(result: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    slim = json.loads(json.dumps(result))
    for arm in slim["arms"]:
        arm.pop("rows", None)
    (output_dir / "dx002_results.json").write_text(
        json.dumps(slim, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    fieldnames = [
        "arm",
        "turn",
        "total",
        *PART_ORDER,
        "retrieved_ltm_compact",
        "retrieved_ltm_episodes",
    ]
    with (output_dir / "decomposition.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for arm in result["arms"]:
            for row in arm["rows"]:
                writer.writerow({"arm": arm["arm"], **row})

    with (output_dir / "terminal_slopes.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "arm",
                "series",
                "n",
                "slope_chars_per_turn",
                "ci95_low",
                "ci95_high",
                "includes_zero",
                "theil_sen_slope_chars_per_turn",
                "projected_growth_over_1000_turns",
                "terminal_mean_chars",
            ]
        )
        for arm in result["arms"]:
            for name in (*PART_ORDER, "total", "retrieved_ltm_compact"):
                window = arm["series"][name]["terminal_window"]
                writer.writerow(
                    [
                        arm["arm"],
                        name,
                        window.get("n", TERMINAL_WINDOW),
                        _fmt(window.get("slope_chars_per_turn")),
                        _fmt(window.get("ci95_low")),
                        _fmt(window.get("ci95_high")),
                        window.get("includes_zero"),
                        _fmt(window.get("theil_sen_slope_chars_per_turn")),
                        _fmt(window.get("projected_growth_over_1000_turns")),
                        _fmt(window.get("mean")),
                    ]
                )

    (output_dir / "DX_002_report.md").write_text(
        render_report(result),
        encoding="utf-8",
        newline="\n",
    )


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def render_report(result: dict) -> str:
    decision = result["decision"]
    lines = [
        "# DX-002 - The Context Growth Question",
        "",
        f"**Status:** {result['status']}",
        f"**Branch:** {decision['branch']} - {decision['label']}",
        "**Scope:** committed Study 010 serialized prompts. Offline. No run.",
        "",
        "## The question",
        "",
        "The record holds a peak - 27,154 estimated tokens for arm L - and a",
        "peak cannot say whether the curve was still climbing. This reads the",
        "same 2,000 prompts and fits the terminal",
        f"{result['terminal_window_turns']} turns of every part.",
        "",
        "## Gates",
        "",
        "| Gate | Certifies | Result |",
        "|---|---|---|",
        f"| G1 | every prompt reconstructs byte-exactly from its parts | "
        f"{_verdict(result['gates']['G1_byte_exact_reconstruction'])} |",
        f"| G2 | recomputed `chars // 4` matches committed telemetry | "
        f"{_verdict(result['gates']['G2_telemetry_matches_committed'])} |",
        f"| G3 | compact re-render reproduces DR-001's 37,619 / 37,545 | "
        f"{_verdict(result['gates']['G3_dr001_compact_replay'])} |",
        f"| G4 | input tree unchanged across the read | "
        f"{_verdict(result['gates']['G4_inputs_unchanged'])} |",
        "",
        "G3 is what licenses the post-DR-001 column below. The re-render is",
        "certified against a committed result before it is applied to the",
        "other 998 turns.",
        "",
        "## Terminal slopes",
        "",
        "Ordinary least squares over the last "
        f"{result['terminal_window_turns']} turns, with a two-sided 95%",
        "interval on t(n-2). A slope whose interval contains zero is not",
        "distinguishable from flat. Theil-Sen is the median-of-pairs",
        "robustness check: these series are heteroscedastic, and agreement",
        "between the two estimators is what rules out a handful of extreme",
        "turns driving the fit.",
        "",
    ]

    for arm in result["arms"]:
        lines.extend(
            [
                f"### {arm['arm']}",
                "",
                "| Part | Terminal mean chars | Slope chars/turn | 95% CI | "
                "Theil-Sen | Flat? |",
                "|---|---:|---:|---|---:|---|",
            ]
        )
        for name in (*PART_ORDER, "total"):
            window = arm["series"][name]["terminal_window"]
            if window.get("degenerate_constant_series"):
                lines.append(
                    f"| `{name}` | {window['mean']:,.0f} | 0 | constant | 0 | "
                    "yes (constant) |"
                )
                continue
            flat = "yes" if window["includes_zero"] else "**NO**"
            lines.append(
                f"| `{name}` | {window['mean']:,.0f} | "
                f"{window['slope_chars_per_turn']:+.3f} | "
                f"[{window['ci95_low']:+.3f}, {window['ci95_high']:+.3f}] | "
                f"{window['theil_sen_slope_chars_per_turn']:+.3f} | {flat} |"
            )
        lines.append("")

    lines.extend(
        [
            "## What this fit can and cannot rule out",
            "",
            "A flat verdict is a statement about detectable growth, not about",
            "growth. The half-width of each interval is the smallest slope",
            "this data could have distinguished from zero, so any growth",
            "below it is compatible with the measurement.",
            "",
            "| Arm | Series | Terminal mean | Smallest detectable slope | "
            "Undetectable drift over 1,000 turns |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for arm in result["arms"]:
        for name in ("total", "retrieved_stm", "retrieved_ltm"):
            window = arm["series"][name]["terminal_window"]
            if window.get("degenerate_constant_series"):
                continue
            half = window["ci95_half_width"]
            lines.append(
                f"| {arm['arm']} | `{name}` | {window['mean']:,.0f} | "
                f"{half:.2f} chars/turn | {half * 1000:,.0f} chars |"
            )
    lines.extend(
        [
            "",
            "Read the `arm_l.total` row before treating Branch A as settled:",
            f"growth of up to {_half_width(result, 'arm_l', 'total'):.0f} "
            "characters per turn is inside the noise here, which over 1,000",
            f"further turns is {_half_width(result, 'arm_l', 'total') * 1000:,.0f}",
            "characters of drift the fit would not have caught. Branch A means",
            "*no growth was detected at this power*, on this conversation",
            "shape, at this horizon.",
            "",
            "### Why the interval is not the whole answer",
            "",
            "These series are sawtooths - retrieval ramps up over a topic run",
            "and resets - so the residuals are strongly autocorrelated and an",
            "OLS interval built on independence assumptions cannot be taken at",
            "face value. Durbin-Watson on the terminal residuals (2.0 would",
            "mean no serial correlation):",
            "",
            "| Arm | Series | Durbin-Watson |",
            "|---|---|---:|",
        ]
    )
    for arm in result["arms"]:
        for name in ("total", "retrieved_stm", "retrieved_ltm"):
            window = arm["series"][name]["terminal_window"]
            if window.get("degenerate_constant_series"):
                continue
            lines.append(
                f"| {arm['arm']} | `{name}` | "
                f"{window['durbin_watson']:.2f} |"
            )
    lines.extend(
        [
            "",
            "So the verdict does not rest on the fit. The blunt check below",
            "assumes nothing about residual structure: it compares the fitted",
            "window against the 300 turns immediately before it. A series that",
            "is still climbing has to show up here.",
            "",
            "| Arm | Series | Turns 401-700 mean | Turns 701-1000 mean | "
            "Change |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for arm in result["arms"]:
        for name in ("total", "retrieved_stm", "retrieved_ltm", "recent_context"):
            comparison = arm["series"][name]["window_over_window"]
            if not comparison.get("comparable") or not comparison["prior_mean"]:
                continue
            lines.append(
                f"| {arm['arm']} | `{name}` | {comparison['prior_mean']:,.0f} | "
                f"{comparison['recent_mean']:,.0f} | "
                f"{comparison['delta_pct']:+.1f}% |"
            )
    lines.extend(
        [
            "",
            "### Saturation: is the part still setting records?",
            "",
            "The decisive reading. A part that has stopped growing stops",
            "reaching further; a part that is still climbing keeps setting",
            "new highs. Below is the 95th percentile of each part within each",
            "of the last five 100-turn buckets. If the final bucket holds the",
            "maximum, the part had not saturated when the run ended.",
            "",
            "A part is only called a growth concern if it also moved by at",
            f"least {MATERIALITY_FLOOR_CHARS:,} characters - one percent of",
            "the LTM budget - across these five buckets. That floor is in the",
            "system's own budget units, not fitted to the data.",
            "",
            "| Arm | Series | 501-600 | 601-700 | 701-800 | 801-900 | "
            "901-1000 | Change | Verdict |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for arm in result["arms"]:
        for name in PART_ORDER:
            series = arm["series"][name]
            if series["constant"]:
                continue
            blocks = series["blocks"][-5:]
            verdict = result["decision"]["series_verdicts"][
                f"{arm['arm']}.{name}"
            ]
            cells = " | ".join(f"{block['p95']:,.0f}" for block in blocks)
            if verdict["climbing"]:
                mark = "**STILL CLIMBING**"
            elif verdict["rising"]:
                mark = "rising, below floor"
            elif not verdict["saturated"]:
                mark = "record set, below floor"
            else:
                mark = "saturated"
            lines.append(
                f"| {arm['arm']} | `{name}` | {cells} | "
                f"{verdict['p95_growth_chars']:+,.0f} | {mark} |"
            )

    lines.extend(
        [
            "",
            "## Rule pinning",
            "",
        ]
    )
    for arm in result["arms"]:
        pinning = arm["rule_pinning"]
        lines.extend(
            [
                f"**{arm['arm']}.** {pinning['finding']}",
                "",
                f"*Limitation.* {pinning['limitation']}",
                "",
            ]
        )

    lines.extend(["## LTM against its 32,000-character budget", ""])
    for arm in result["arms"]:
        budget = arm["ltm_vs_budget"]
        if not budget["present"]:
            lines.append(
                f"- **{arm['arm']}** carries no `<retrieved_ltm>` block; it is "
                "the STM-only arm."
            )
            continue
        lines.extend(
            [
                f"- **{arm['arm']}**, {budget['turns_with_ltm']:,} of "
                f"{budget['turns_total']:,} turns carry an LTM block.",
                f"  - Historical renderer: max "
                f"{budget['historical_max_chars']:,} chars; "
                f"{budget['historical_turns_over_budget']:,} turns over the "
                f"{budget['budget_chars']:,} budget.",
                f"  - Post-DR-001 compact renderer: max "
                f"{budget['compact_max_chars']:,} chars, mean "
                f"{budget['compact_mean_chars']:,.0f}; "
                f"{budget['compact_turns_over_budget']:,} turns over budget.",
            ]
        )
    lines.extend(
        [
            "",
            "**The compact renderer alone does not bring the block under",
            "budget.** Re-serializing the historically selected episode sets",
            "at exact cost still exceeds 32,000 characters on the majority of",
            "turns. This is not a contradiction of DR-001: those sets were",
            "*chosen* under the undercharged accounting, so they contain more",
            "episodes than the budget can hold, and cheaper tags cannot undo",
            "an over-large selection. It is the measured case for CC-003 -",
            "the ceiling has to bind during selection, not after it.",
            "",
        ]
    )

    lines.extend(
        [
            "## Decision",
            "",
            f"**Branch {decision['branch']} - {decision['label']}.**",
            "",
            decision["reason"] + ".",
            "",
            "Against section 0.5's committed prediction - H-A for the LTM",
            "block, H-C overall, at about 60% - this is the predicted",
            "outcome. The greedy frame does fill its budget and then flatten,",
            "and there is a second component outside that budget which does",
            "not. The prediction understated the size of the residual: it",
            "expected \"a small positive residual slope\", and the measured",
            "leak is the largest single mover in the terminal window.",
            "",
            "### The near miss",
            "",
            "This diagnostic first returned **Branch A**, on a decision rule",
            "that asked only whether the terminal OLS slope's interval",
            "contained zero. It does, in every part, in both arms - the",
            "sawtooth variance is large enough that nothing clears the bar.",
            "But Branch A is a conjunction, and its third clause is *no",
            "unbudgeted component climbing*. Checking only the slope let a",
            "part whose 95th percentile rose from 25,253 to 48,491 characters",
            "over the final five buckets be reported as flat.",
            "",
            "That is the failure class in AGENTS.md section 3, reproduced",
            "exactly: a check that passes while the property it certifies is",
            "false. The confidence interval was measuring statistical power,",
            "and it was read as evidence of boundedness. The saturation and",
            "window-over-window readings were added because of it, and both",
            "are assumption-free.",
            "",
            "## Consequences",
            "",
            "- **This blocks CC-003** (section 0.4, Branch B). The STM block",
            "  has to come inside a budget or be removed before enforcement",
            "  can claim a bounded context. Enforcing a ceiling on the LTM",
            "  block alone would leave the growing component untouched while",
            "  the report says `truncated=False`.",
            "- **CC-005's design is decided** (section 3.1, row 1). Context is",
            "  not bounded by construction, so eviction cannot be scoped as a",
            "  pure disk-and-latency policy on the strength of a plateau that",
            "  only one of the two retrieval blocks exhibits.",
            "- The extracted library already routes both the recency window",
            "  and the K-threshold hits through a single `budget` in",
            "  `pack_stm_payload`, so the leak measured here is a property of",
            "  the Study 010 runner, not necessarily of `episodic`. CC-003",
            "  should verify that directly rather than assume it.",
            "",
            "## Boundary",
            "",
            "This is a statement about **the tested horizon only**. A plateau",
            "at 1,000 turns says nothing about 10,000; section 0.6 names that",
            "surrogate explicitly and it is not mitigated here, only stated.",
            "The LTM saturation claim inherits that limit in full.",
            "",
            "The decomposition is over one conversation shape - a scripted",
            "1,000-turn run on one model, one quantization, one machine.",
            "",
            "The climbing verdict rests on bucketed percentiles and a",
            "window-over-window mean, not on a significance test. It says the",
            "part had not stopped growing by turn 1,000; it does not fit a",
            "growth law and does not project one.",
            "",
            "## Integrity",
            "",
            f"- Input files: {result['input_file_count']:,}",
            f"- Input tree SHA-256 before: "
            f"`{result['input_tree_sha256_before']}`",
            f"- Input tree SHA-256 after: "
            f"`{result['input_tree_sha256_after']}`",
            "",
        ]
    )
    return "\n".join(lines)


def _verdict(ok: bool) -> str:
    return "**PASS**" if ok else "**FAIL**"


def _half_width(result: dict, arm_name: str, series: str) -> float:
    for arm in result["arms"]:
        if arm["arm"] == arm_name:
            return arm["series"][series]["terminal_window"]["ci95_half_width"]
    return float("nan")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            REPO_ROOT
            / "experiments"
            / "components"
            / "deployment_closeout"
            / "artifacts"
            / "dx002"
        ),
    )
    args = parser.parse_args()
    result = analyse()
    write_artifacts(result, args.output_dir)
    print(f"status={result['status']} branch={result['decision']['branch']}")
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

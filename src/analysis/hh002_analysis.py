"""HH-002 analysis: the leaderboard, the paired contrasts, the gate.

Three things are computed here and kept apart on purpose.

1. **The reproduced rows.**  What this rig scored for full context and RAG,
   against what arXiv:2504.19413 Table 2 published for them.  This is G-CTRL,
   and until it passes nothing else in the file means anything.
2. **The component's row.**  A number on the same axis as every published row,
   because it came out of the same questions, prompt, model, judge and metric.
3. **Paired contrasts.**  Item-level gains and losses against the arms this
   run actually produced.  A paired test against an inherited row is not
   possible and is not attempted: their per-item answers were never published.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from analysis.hh001_stats import (
    exact_sign_test,
    exact_sign_test_two_sided,
    reachability,
)
from analysis.hh002_run import ARTIFACTS, INHERITED, PUBLISHED, score


class HH002AnalysisError(RuntimeError):
    pass


@dataclass(frozen=True)
class Contrast:
    treatment: str
    control: str
    endpoint: str
    n: int
    gains: int
    losses: int
    ties: int
    treatment_rate: float
    control_rate: float

    @property
    def delta(self) -> float:
        return self.treatment_rate - self.control_rate

    @property
    def p_one_sided(self) -> float:
        return exact_sign_test(self.gains, self.losses)

    @property
    def p_two_sided(self) -> float:
        return exact_sign_test_two_sided(self.gains, self.losses)

    def as_dict(self) -> dict[str, Any]:
        return {
            "treatment": self.treatment,
            "control": self.control,
            "endpoint": self.endpoint,
            "n": self.n,
            "gains": self.gains,
            "losses": self.losses,
            "ties": self.ties,
            "treatment_rate": round(self.treatment_rate, 6),
            "control_rate": round(self.control_rate, 6),
            "delta_points": round(self.delta * 100, 4),
            "p_one_sided": self.p_one_sided,
            "p_two_sided": self.p_two_sided,
        }


def load_judged(
    arm: str, replicate: int = 1, base: Path | None = None
) -> dict[str, dict[str, Any]]:
    base = base or ARTIFACTS
    path = base / arm / f"judged_r{replicate}.json"
    if not path.exists():
        raise HH002AnalysisError(f"no judgements for {arm} r{replicate}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {row["key"]: row for row in payload["records"]}


def load_predictions(
    arm: str, base: Path | None = None
) -> dict[str, dict[str, Any]]:
    base = base or ARTIFACTS
    path = base / arm / "predictions.json"
    if not path.exists():
        raise HH002AnalysisError(f"no predictions for {arm}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {row["key"]: row for row in payload["records"]}


def paired(
    treatment: str,
    control: str,
    endpoint: str = "llm_score",
    base: Path | None = None,
    threshold: float = 0.5,
) -> Contrast:
    """Pair by item key, never by position.

    ``f1`` is continuous, so it is thresholded before pairing; the threshold
    is declared rather than tuned.  ``llm_score`` is already 0/1.
    """
    left = load_judged(treatment, base=base)
    right = load_judged(control, base=base)
    keys = sorted(set(left) & set(right))
    if not keys:
        raise HH002AnalysisError(f"{treatment} and {control} share no items")
    if len(keys) != len(left) or len(keys) != len(right):
        raise HH002AnalysisError(
            f"{treatment} has {len(left)} items, {control} has {len(right)}, "
            f"{len(keys)} shared - refusing to compare unequal populations"
        )

    def value(row: dict[str, Any]) -> bool:
        raw = float(row[endpoint])
        return raw >= threshold if endpoint != "llm_score" else raw >= 1.0

    gains = losses = ties = 0
    t_total = c_total = 0
    for key in keys:
        t, c = value(left[key]), value(right[key])
        t_total += int(t)
        c_total += int(c)
        if t and not c:
            gains += 1
        elif c and not t:
            losses += 1
        else:
            ties += 1
    n = len(keys)
    return Contrast(
        treatment=treatment,
        control=control,
        endpoint=endpoint,
        n=n,
        gains=gains,
        losses=losses,
        ties=ties,
        treatment_rate=t_total / n,
        control_rate=c_total / n,
    )


def judge_variance(
    arm: str, base: Path | None = None, replicates: Sequence[int] = (1, 2)
) -> dict[str, Any]:
    """How much the judge moves when the same answers are scored twice.

    G-CTRL's tolerance comes from this rather than from a round number.  The
    answers are byte-identical between replicates, so every disagreement here
    is the judge's own variance and nothing else.
    """
    loaded = {r: load_judged(arm, r, base) for r in replicates}
    keys = sorted(set.intersection(*(set(v) for v in loaded.values())))
    if not keys:
        raise HH002AnalysisError(f"{arm} has no shared items across replicates")
    rates = {
        r: sum(loaded[r][k]["llm_score"] for k in keys) / len(keys)
        for r in replicates
    }
    flips = sum(
        1
        for k in keys
        if len({loaded[r][k]["llm_score"] for r in replicates}) > 1
    )
    values = list(rates.values())
    return {
        "arm": arm,
        "n": len(keys),
        "replicates": replicates,
        "rates": {str(r): round(v, 6) for r, v in rates.items()},
        "rate_points": {str(r): round(v * 100, 4) for r, v in rates.items()},
        "spread_points": round((max(values) - min(values)) * 100, 4),
        "item_flips": flips,
        "item_flip_rate": round(flips / len(keys), 6),
    }


def leaderboard(
    arms: Sequence[str], base: Path | None = None
) -> list[dict[str, Any]]:
    """Every row this study can put on one axis, measured or inherited."""
    rows: list[dict[str, Any]] = []
    for arm in arms:
        try:
            judged = list(load_judged(arm, base=base).values())
        except HH002AnalysisError:
            continue
        result = score(judged)
        rows.append(
            {
                "system": arm,
                "source": "measured here",
                "llm_score_points": round(result["llm_score"] * 100, 2),
                "f1": round(result["f1"], 4),
                "n": result["n"],
                "published_points": PUBLISHED.get(arm),
                "per_category": {
                    k: round(v["llm_score"] * 100, 2)
                    for k, v in result["per_category"].items()
                },
            }
        )
    for system, value in INHERITED.items():
        rows.append(
            {
                "system": system,
                "source": "arXiv:2504.19413 Table 2, not re-run here",
                "llm_score_points": value,
                "f1": None,
                "n": 1540,
                "published_points": value,
                "per_category": None,
            }
        )
    rows.sort(key=lambda r: -r["llm_score_points"])
    return rows


def gctrl(
    tolerance_points: float, base: Path | None = None
) -> dict[str, Any]:
    """Did this rig reproduce the two rows it must reproduce?"""
    checks = []
    for arm, target in PUBLISHED.items():
        try:
            judged = list(load_judged(arm, base=base).values())
        except HH002AnalysisError:
            checks.append({"arm": arm, "status": "NOT RUN", "target": target})
            continue
        measured = score(judged)["llm_score"] * 100
        delta = measured - target
        checks.append(
            {
                "arm": arm,
                "target_points": target,
                "measured_points": round(measured, 2),
                "delta_points": round(delta, 2),
                "within_tolerance": abs(delta) <= tolerance_points,
                "n": len(judged),
            }
        )
    passed = all(c.get("within_tolerance") for c in checks) and len(checks) == len(
        PUBLISHED
    )
    return {
        "tolerance_points": tolerance_points,
        "checks": checks,
        "passed": passed,
    }


def cost_summary(arms: Sequence[str], base: Path | None = None) -> dict[str, Any]:
    """Read cost per arm, from the usage the run recorded per item."""
    base = base or ARTIFACTS
    out: dict[str, Any] = {}
    for arm in arms:
        try:
            rows = list(load_predictions(arm, base).values())
        except HH002AnalysisError:
            continue
        if not rows:
            continue
        n = len(rows)
        out[arm] = {
            "n": n,
            # Whole tokens: these are means of integer counts, and a tenth
            # of a token is precision the quantity does not have.
            "mean_prompt_tokens": round(
                sum(r["prompt_tokens"] for r in rows) / n
            ),
            "total_prompt_tokens": sum(r["prompt_tokens"] for r in rows),
            "mean_context_chars": round(
                sum(r["context_chars"] for r in rows) / n
            ),
            "median_search_ms": round(
                sorted(r["search_time"] for r in rows)[n // 2] * 1000, 2
            ),
            "median_response_ms": round(
                sorted(r["response_time"] for r in rows)[n // 2] * 1000, 2
            ),
            "mean_units_delivered": round(
                sum(r["units_delivered"] for r in rows) / n, 2
            ),
        }
    return out


def depth_strata(
    arm: str, control: str, base: Path | None = None, bins: int = 4
) -> list[dict[str, Any]]:
    """Accuracy split by where in the conversation the evidence sits.

    The long-horizon axis: an item whose evidence is in the first tenth of a
    680-turn transcript is the case a memory layer exists for.  Depth comes
    from the corpus, not from any arm, so the bins are identical for both
    sides of the contrast.
    """
    from analysis.hh002_dataset import load_corpus
    from analysis.hh002_run import DATASET

    depths: dict[str, float] = {}
    for conversation in load_corpus(DATASET):
        index = {t.dia_id: i for i, t in enumerate(conversation.turns)}
        total = len(conversation.turns)
        for question in conversation.scored_questions:
            positions = [index[d] for d in question.evidence if d in index]
            if not positions or total <= 1:
                continue
            depths[f"{conversation.sample_id}#{question.source_index}"] = (
                min(positions) / (total - 1)
            )

    left = load_judged(arm, base=base)
    right = load_judged(control, base=base)
    rows: list[dict[str, Any]] = []
    for b in range(bins):
        low, high = b / bins, (b + 1) / bins
        keys = [
            k
            for k, d in depths.items()
            if k in left and k in right and (low <= d < high or (b == bins - 1 and d == 1.0))
        ]
        if not keys:
            continue
        t = sum(left[k]["llm_score"] for k in keys) / len(keys)
        c = sum(right[k]["llm_score"] for k in keys) / len(keys)
        rows.append(
            {
                "quartile": b + 1,
                "depth_range": [round(low, 2), round(high, 2)],
                "n": len(keys),
                f"{arm}_points": round(t * 100, 2),
                f"{control}_points": round(c * 100, 2),
                "delta_points": round((t - c) * 100, 2),
            }
        )
    return rows


__all__ = [
    "Contrast",
    "HH002AnalysisError",
    "cost_summary",
    "depth_strata",
    "gctrl",
    "judge_variance",
    "leaderboard",
    "load_judged",
    "load_predictions",
    "paired",
    "reachability",
]

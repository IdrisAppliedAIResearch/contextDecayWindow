"""Deterministic registered reporting for HH-003."""

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Sequence

from analysis.hh002_run import _read_json, _write_json, score
from analysis.hh003_drive import ARMS, RUN

ROOT = Path(__file__).resolve().parents[2]
HH002 = ROOT / "experiments" / "comparisons" / "hh_002" / "artifacts"
CONTROLS = ("A_CDW", "A_RAG", "A_FULL")


class HH003ReportError(RuntimeError):
    pass


def two_sided_exact_binomial(gains: int, losses: int) -> float:
    n = gains + losses
    if n == 0:
        return 1.0
    tail = min(gains, losses)
    probability = sum(math.comb(n, k) for k in range(tail + 1)) / (1 << n)
    return min(1.0, 2.0 * probability)


def _identity(row: dict[str, Any]) -> tuple[str, int]:
    return str(row["sample_id"]), int(row["source_index"])


def _indexed(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    rows = list(rows)
    indexed = {_identity(row): row for row in rows}
    if len(indexed) != len(rows):
        raise HH003ReportError("duplicate comparison identity")
    return indexed


def _records(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path) or {}
    rows = payload.get("records", [])
    if len(rows) != 1540:
        raise HH003ReportError(f"expected 1,540 records at {path}, found {len(rows)}")
    return rows


def _contrast(left: str, right: str, populations: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    left_rows = _indexed(populations[left])
    right_rows = _indexed(populations[right])
    if set(left_rows) != set(right_rows):
        raise HH003ReportError(f"identity mismatch: {left} versus {right}")
    gains = sum(left_rows[key]["llm_score"] > right_rows[key]["llm_score"] for key in left_rows)
    losses = sum(left_rows[key]["llm_score"] < right_rows[key]["llm_score"] for key in left_rows)
    return {
        "left": left,
        "right": right,
        "n": len(left_rows),
        "left_correct": sum(row["llm_score"] for row in left_rows.values()),
        "right_correct": sum(row["llm_score"] for row in right_rows.values()),
        "gains": gains,
        "losses": losses,
        "ties": len(left_rows) - gains - losses,
        "discordant": gains + losses,
        "two_sided_exact_binomial_p": two_sided_exact_binomial(gains, losses),
        "cross_date": right in CONTROLS,
    }


def _distribution(values: Sequence[float]) -> dict[str, float | int]:
    ordered = sorted(values)
    p95 = ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)]
    return {
        "n": len(ordered), "min": ordered[0], "median": median(ordered),
        "mean": mean(ordered), "p95": p95, "max": ordered[-1],
        "total": sum(ordered),
    }


def _operational(arm: str) -> dict[str, Any]:
    context_payload = _read_json(RUN / arm / "contexts.json") or {}
    contexts = list(context_payload.get("items", {}).values())
    predictions = _records(RUN / arm / "predictions.json")
    if len(contexts) != 1540 or {_identity(row) for row in contexts} != {_identity(row) for row in predictions}:
        raise HH003ReportError(f"context/prediction identity mismatch for {arm}")
    detail_fields = (
        "retrieval_chars_delivered", "episodes_delivered", "episodes_dropped",
        "recency_count", "semantic_count", "aspect_count", "latency_ms",
    )
    result = {
        field: _distribution([float(row["detail"][field]) for row in contexts])
        for field in detail_fields
    }
    for field in ("context_chars", "prompt_tokens", "completion_tokens", "response_time"):
        result[field] = _distribution([float(row[field]) for row in predictions])
    result["truncated_count"] = sum(bool(row["detail"]["truncated"]) for row in contexts)
    result["store_mutation_count"] = sum(not bool(row["detail"]["store_unchanged"]) for row in contexts)
    return result


def build_report() -> dict[str, Any]:
    populations = {arm: _records(RUN / arm / "judged_r1.json") for arm in ARMS}
    populations.update({arm: _records(HH002 / arm / "judged_r1.json") for arm in CONTROLS})
    comparisons = [("A_EPISODIC_ASPECT", "A_EPISODIC")]
    comparisons.extend((arm, control) for arm in ARMS for control in CONTROLS)
    report = {
        "population": 1540,
        "primary_endpoint": "llm_score",
        "arms": {arm: score(populations[arm]) for arm in ARMS},
        "contrasts": [_contrast(left, right, populations) for left, right in comparisons],
        "operational": {arm: _operational(arm) for arm in ARMS},
        "limits": [
            "LoCoMo is spent; results are descriptive, not confirmatory.",
            "HH-002 control contrasts are cross-date and confound memory with service time.",
            "Judge score is accompanied by deterministic F1 and exact match.",
        ],
    }
    return report


def _markdown(report: dict[str, Any]) -> str:
    lines = ["# HH-003 Findings", "", "## Scores", "", "| Arm | Correct | LLM score | F1 | Exact match |", "|---|---:|---:|---:|---:|"]
    for arm, row in report["arms"].items():
        lines.append(f"| `{arm}` | {round(row['llm_score'] * row['n'])}/{row['n']} | {row['llm_score']:.4f} | {row['f1']:.4f} | {row['exact_match']:.4f} |")
    lines.extend(["", "## Paired Contrasts", "", "Positive net favors the left arm. HH-002 comparisons are cross-date.", "", "| Left | Right | Gains | Losses | Ties | Net | Two-sided p |", "|---|---|---:|---:|---:|---:|---:|"])
    for row in report["contrasts"]:
        lines.append(f"| `{row['left']}` | `{row['right']}` | {row['gains']} | {row['losses']} | {row['ties']} | {row['gains'] - row['losses']:+d} | {row['two_sided_exact_binomial_p']:.6g} |")
    lines.extend(["", "## Interpretation", "", "HH-003 registers no directional success bar and no automatic adoption decision. The primary judge endpoint, deterministic F1, category results, and operational distributions are recorded in `artifacts/run/report.json`.", "", "LoCoMo is spent, and comparisons with HH-002 controls are cross-date. This run does not establish general superiority or current Mem0 product performance.", ""])
    return "\n".join(lines)


def main() -> int:
    report = build_report()
    _write_json(RUN / "report.json", report)
    (RUN.parents[1] / "HH_003_FINDINGS.md").write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report["arms"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Deterministic sealed report for HH-004."""

from __future__ import annotations

import json
import math
import hashlib
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

import numpy as np

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "experiments" / "comparisons" / "hh_004"
RUN = BASE / "artifacts" / "run"
ARM = "A_DA098_ARCH32_DECODED"
EXPECTED = 842
CONTROL_FILES = {
    "A_EPISODIC": "hh_003/artifacts/run/A_EPISODIC/judged_r1.json",
    "A_EPISODIC_ASPECT": "hh_003/artifacts/run/A_EPISODIC_ASPECT/judged_r1.json",
    "A_CDW": "hh_002/artifacts/A_CDW/judged_r1.json",
    "A_RAG": "hh_002/artifacts/A_RAG/judged_r1.json",
    "A_FULL": "hh_002/artifacts/A_FULL/judged_r1.json",
}

PREDICTIONS_SHA256 = "dc1709010e8741bc36e10c2a139e35cb4a651a2071d83f3c05eab8b8151570ba"
JUDGEMENTS_SHA256 = "542508c3b871599b2d4db08a75cb0ab916d6eaf661ca4cf375a1e82aa9ba0cc8"
CONTEXTS_SHA256 = "43e0bcadd19af5f5915b3f4a4cbcf8539f094a2250ce14196beb04a333942924"


class HH004ReportError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _records(path: Path) -> list[dict[str, Any]]:
    return list((_read_json(path) or {}).get("records", []))


def _dist(values: Iterable[float]) -> dict[str, float]:
    array = np.asarray(list(values), dtype=float)
    return {name: round(float(np.percentile(array, q)), 4)
            for name, q in (("min", 0), ("p10", 10), ("p50", 50),
                            ("p90", 90), ("max", 100))}


def _score(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"n": len(rows), "correct": sum(int(row["llm_score"]) for row in rows),
            "llm_score": round(mean(float(row["llm_score"]) for row in rows), 6),
            "f1": round(mean(float(row["f1"]) for row in rows), 6),
            "exact_match": round(mean(float(row["exact_match"]) for row in rows), 6)}


def _paired(left: dict[tuple[str, int], dict[str, Any]],
            right: dict[tuple[str, int], dict[str, Any]]) -> dict[str, Any]:
    if left.keys() != right.keys() or len(left) != EXPECTED:
        raise HH004ReportError("paired population differs")
    gains = losses = 0
    for key in left:
        a, b = bool(left[key]["llm_score"]), bool(right[key]["llm_score"])
        gains += int(a and not b)
        losses += int(b and not a)
    discordant = gains + losses
    tail = min(gains, losses)
    p = min(1.0, 2 * sum(math.comb(discordant, k) for k in range(tail + 1)) /
            2**discordant) if discordant else 1.0
    return {"gains": gains, "losses": losses, "net": gains - losses,
            "ties": EXPECTED - discordant, "discordant": discordant,
            "two_sided_exact_p": p}


def analyze() -> dict[str, Any]:
    arm_dir = RUN / ARM
    paths = {"contexts": arm_dir / "contexts.json",
             "predictions": arm_dir / "predictions.json",
             "judgements": arm_dir / "judged_r1.json"}
    expected_hashes = {"contexts": CONTEXTS_SHA256, "predictions": PREDICTIONS_SHA256,
                       "judgements": JUDGEMENTS_SHA256}
    hashes = {name: sha256_file(path) for name, path in paths.items()}
    if hashes != expected_hashes:
        raise HH004ReportError(f"sealed HH-004 artifacts differ: {hashes}")
    contexts = (_read_json(paths["contexts"]) or {})["items"]
    predictions = _records(paths["predictions"])
    judgements = _records(paths["judgements"])
    health = _read_json(RUN / "health.json") or {}
    if health.get("status") != "COMPLETE" or len(predictions) != EXPECTED or len(judgements) != EXPECTED:
        raise HH004ReportError("HH-004 run is incomplete")
    identity = lambda row: (str(row["sample_id"]), int(row["source_index"]))
    new = {identity(row): row for row in judgements}
    if len(new) != EXPECTED:
        raise HH004ReportError("new-arm identity collision")

    controls, comparisons = {}, {}
    root = BASE.parent
    for arm, relative in CONTROL_FILES.items():
        rows = {identity(row): row for row in _records(root / relative) if identity(row) in new}
        controls[arm] = _score(list(rows.values()))
        comparisons[arm] = _paired(new, rows)

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in judgements:
        groups[str(row["sample_id"])].append(row)
        categories[str(row["category"])].append(row)
    answer_usage = {"calls": EXPECTED,
                    "prompt_tokens": sum(int(row["prompt_tokens"]) for row in predictions),
                    "completion_tokens": sum(int(row["completion_tokens"]) for row in predictions),
                    "cached_tokens": sum(int(row["cached_tokens"]) for row in predictions),
                    "seconds": round(sum(float(row["response_time"]) for row in predictions), 3)}
    pilot = _read_json(BASE / "artifacts" / "preflight" / "g4_paid_pilot.json") or {}
    judge_final = (_read_json(paths["judgements"]) or {}).get("usage", {})
    judge_usage = {key: int(pilot["judge"]["usage"].get(key, 0)) + int(judge_final.get(key, 0))
                   for key in ("calls", "prompt_tokens", "completion_tokens", "cached_tokens")}
    judge_usage["seconds"] = round(float(pilot["judge"]["usage"]["seconds"]) +
                                   float(judge_final["seconds"]), 3)
    fresh = answer_usage["prompt_tokens"] + judge_usage["prompt_tokens"] - answer_usage["cached_tokens"]
    cached = answer_usage["cached_tokens"] + judge_usage["cached_tokens"]
    output = answer_usage["completion_tokens"] + judge_usage["completion_tokens"]
    usd = (fresh * .150 + cached * .075 + output * .600) / 1_000_000
    return {"schema": "hh004-report-v1", "status": "COMPLETE", "population": EXPECTED,
            "arm": ARM, "model": "gpt-4o-mini-2024-07-18", "hashes": hashes,
            "score": _score(judgements), "controls": controls, "comparisons": comparisons,
            "by_conversation": {key: _score(groups[key]) for key in sorted(groups)},
            "by_category": {key: _score(categories[key]) for key in sorted(categories)},
            "context_chars": _dist(row["context_chars"] for row in predictions),
            "prompt_tokens": _dist(row["prompt_tokens"] for row in predictions),
            "response_seconds": _dist(row["response_time"] for row in predictions),
            "answer_usage": answer_usage, "judge_usage": judge_usage,
            "successful_calls": answer_usage["calls"] + judge_usage["calls"],
            "estimated_usd": round(usd, 4),
            "malformed_judgements": sum(row.get("judge_label") == "__MALFORMED__" for row in judgements),
            "failed_items": 0, "watchdog_restarts": int(health["restarts"]),
            "restart_accounting_note": "Successful sealed calls only; up to eight uncheckpointed answer calls may have completed during the stale-process restart."}


def main() -> int:
    report = analyze()
    _write_json(RUN / "report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

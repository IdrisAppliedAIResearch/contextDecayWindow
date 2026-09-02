"""Deterministic sealed report for HH-005."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "experiments" / "comparisons" / "hh_005"
RUN = BASE / "artifacts" / "run"
EXPECTED = 842
ARMS = ("A_SEMANTIC_DA_V2_16K", "A_SEMANTIC_DA_V2_32K")
HASHES = {
    ARMS[0]: {"predictions": "ee78c1071055266bc8bbc53f55c1aa7c95e5716e4ecb418c168dc42d1407bbde",
              "judgements": "b6cd48d25a7ec84d6a101e588cc750db51411c1f64f944df3c244761e47edf05"},
    ARMS[1]: {"predictions": "7871e66db6fe9fa8f51566060ff003d5f4156643b797fc82e6f41b3077abc3e1",
              "judgements": "9daf6b7530ad11824ffdf09ad081203fb5d150c79945165904260a8a89e55404"},
}
CONTROL = (REPO / "experiments" / "comparisons" / "hh_003" / "artifacts" /
           "run" / "A_EPISODIC_ASPECT" / "judged_r1.json")
CONTROL_HASH = "aefc8e91bd602c6449e0b5fa038b9c815070291b36024faecae937e46536ffc7"


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _identity(row: dict[str, Any]) -> tuple[str, int]:
    return str(row["sample_id"]), int(row["source_index"])


def _score(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"n": len(rows), "correct": sum(int(row["llm_score"]) for row in rows),
            "llm_score": round(mean(float(row["llm_score"]) for row in rows), 6),
            "f1": round(mean(float(row["f1"]) for row in rows), 6),
            "exact_match": round(mean(float(row["exact_match"]) for row in rows), 6)}


def _paired(left: dict, right: dict) -> dict[str, Any]:
    if left.keys() != right.keys() or len(left) != EXPECTED:
        raise RuntimeError("paired population differs")
    gains = sum(bool(left[k]["llm_score"]) and not bool(right[k]["llm_score"]) for k in left)
    losses = sum(bool(right[k]["llm_score"]) and not bool(left[k]["llm_score"]) for k in left)
    n = gains + losses
    tail = min(gains, losses)
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(tail + 1)) / 2**n) if n else 1.0
    return {"gains": gains, "losses": losses, "net": gains - losses,
            "ties": EXPECTED - n, "discordant": n, "two_sided_exact_p": p}


def _dist(values: list[float]) -> dict[str, float]:
    return {name: round(float(np.percentile(values, q)), 4)
            for name, q in (("min", 0), ("p10", 10), ("p50", 50), ("p90", 90), ("max", 100))}


def analyze() -> dict[str, Any]:
    health = _read(RUN / "health.json")
    if health["status"] != "COMPLETE":
        raise RuntimeError("run incomplete")
    control_path = CONTROL
    if _sha(control_path) != CONTROL_HASH:
        raise RuntimeError("ASPECT-v1 control differs")
    control_all = {_identity(row): row for row in _read(control_path)["records"]}
    arm_rows, arm_maps, reports = {}, {}, {}
    for arm in ARMS:
        directory = RUN / arm
        predictions_path, judged_path = directory / "predictions.json", directory / "judged_r1.json"
        observed = {"predictions": _sha(predictions_path), "judgements": _sha(judged_path)}
        if observed != HASHES[arm]:
            raise RuntimeError(f"{arm} sealed artifact differs")
        predictions = _read(predictions_path)["records"]
        judged = _read(judged_path)["records"]
        if len(predictions) != EXPECTED or len(judged) != EXPECTED:
            raise RuntimeError(f"{arm} population differs")
        arm_rows[arm], arm_maps[arm] = judged, {_identity(row): row for row in judged}
        groups, categories = defaultdict(list), defaultdict(list)
        for row in judged:
            groups[str(row["sample_id"])].append(row)
            categories[str(row["category"])].append(row)
        reports[arm] = {"score": _score(judged),
                        "by_conversation": {k: _score(groups[k]) for k in sorted(groups)},
                        "by_category": {k: _score(categories[k]) for k in sorted(categories)},
                        "context_chars": _dist([float(row["context_chars"]) for row in predictions]),
                        "prompt_tokens": _dist([float(row["prompt_tokens"]) for row in predictions]),
                        "response_seconds": _dist([float(row["response_time"]) for row in predictions]),
                        "answer_usage": {"calls": EXPECTED,
                            "prompt_tokens": sum(int(row["prompt_tokens"]) for row in predictions),
                            "completion_tokens": sum(int(row["completion_tokens"]) for row in predictions),
                            "cached_tokens": sum(int(row["cached_tokens"]) for row in predictions),
                            "seconds": round(sum(float(row["response_time"]) for row in predictions), 3)},
                        "malformed": sum(row.get("judge_label") == "__MALFORMED__" for row in judged)}
    keys = arm_maps[ARMS[0]].keys()
    control = {key: control_all[key] for key in keys}
    return {"schema": "hh005-report-v1", "status": "COMPLETE", "population": EXPECTED,
            "arms": reports, "aspect_v1": _score(list(control.values())),
            "comparisons": {"16K_vs_ASPECT_V1": _paired(arm_maps[ARMS[0]], control),
                            "32K_vs_ASPECT_V1": _paired(arm_maps[ARMS[1]], control),
                            "32K_vs_16K": _paired(arm_maps[ARMS[1]], arm_maps[ARMS[0]])},
            "watchdog_restarts": int(health["restarts"]), "failed_items": 0,
            "judge_usage_note": "Judge token totals are not exact because one interrupted process checkpoint was superseded; all 1,684 sealed judgements are complete."}


def main() -> int:
    report = analyze()
    path = RUN / "report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

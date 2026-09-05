"""Live health checks for a running AV reader stage.

The token-cap truncation in V2_PROMPT was found by reading output by eye, after
it had already corrupted 4% of a partial run. Nothing in the harness would have
raised it: the arm produced non-empty, plausible-looking answers that happened
to be fragments of the model's own reasoning, and every aggregate would have
looked ordinary.

This is the check that should have existed. It reads the checkpoint files a run
is already writing, applies thresholds, and prints a verdict. It changes
nothing and can run against a live stage.

Checks, in the order they would have caught real problems:

* ``truncation``   finish_reason == "length". The direct signal for the bug
                   above. Was not recorded at all until it had already happened.
* ``format``       the answer line the arm promises was not produced.
* ``empty``        blank answers, which score as wrong and look like model
                   failure rather than harness failure.
* ``degenerate``   answers that are suspiciously uniform, which is what a
                   collapsed prompt or a stuck sampler looks like.
* ``stall``        the checkpoint has not grown, i.e. the run is wedged rather
                   than slow.
* ``judge``        malformed judge labels.
* ``server``       llama.cpp still answering.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

SERVER = "http://127.0.0.1:8000"

THRESHOLDS = {
    "truncated_pct": 1.0,
    "format_miss_pct": 1.0,
    "empty_pct": 0.5,
    "top_answer_pct": 25.0,
    "judge_malformed_pct": 2.0,
    "stall_seconds": 300.0,
}


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _server_ok() -> bool:
    try:
        with urllib.request.urlopen(f"{SERVER}/health", timeout=5) as response:
            return json.loads(response.read().decode("utf-8")).get("status") == "ok"
    except (urllib.error.URLError, OSError, ValueError):
        return False


def check(out_dir: Path, expected: int) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    stages: dict[str, Any] = {}

    for path in sorted(out_dir.glob("*.answers.jsonl")):
        name = path.name.split(".")[0]
        rows = _rows(path)
        if not rows:
            continue
        total = len(rows)

        def pct(count: int) -> float:
            return round(100 * count / total, 2)

        truncated = sum(1 for r in rows if r.get("truncated"))
        misses = sum(1 for r in rows if not r.get("well_formed", True))
        repaired = sum(1 for r in rows if r.get("repaired"))
        empty = sum(1 for r in rows if not str(r.get("response", "")).strip())
        counts = Counter(str(r.get("response", "")).strip().lower() for r in rows)
        top_answer, top_count = counts.most_common(1)[0]
        age = time.time() - path.stat().st_mtime

        stages[name] = {
            "rows": total,
            "of_expected": expected,
            "truncated_pct": pct(truncated),
            "format_miss_pct": pct(misses),
            "repaired": repaired,
            "empty_pct": pct(empty),
            "top_answer_pct": pct(top_count),
            "top_answer": top_answer[:60],
            "mean_answer_chars": round(
                statistics.mean(len(str(r.get("response", ""))) for r in rows), 1
            ),
            "seconds_since_write": round(age, 1),
        }

        if pct(truncated) > THRESHOLDS["truncated_pct"]:
            findings.append(
                {
                    "stage": name,
                    "check": "truncation",
                    "detail": f"{truncated}/{total} hit the token cap "
                    f"({pct(truncated)}%)",
                }
            )
        if pct(misses) > THRESHOLDS["format_miss_pct"]:
            findings.append(
                {
                    "stage": name,
                    "check": "format",
                    "detail": f"{misses}/{total} missing the answer line "
                    f"({pct(misses)}%)",
                }
            )
        if pct(empty) > THRESHOLDS["empty_pct"]:
            findings.append(
                {
                    "stage": name,
                    "check": "empty",
                    "detail": f"{empty}/{total} blank answers",
                }
            )
        if pct(top_count) > THRESHOLDS["top_answer_pct"]:
            findings.append(
                {
                    "stage": name,
                    "check": "degenerate",
                    "detail": f"{pct(top_count)}% of answers are the same "
                    f"string: {top_answer[:40]!r}",
                }
            )
        if total < expected and age > THRESHOLDS["stall_seconds"]:
            findings.append(
                {
                    "stage": name,
                    "check": "stall",
                    "detail": f"incomplete ({total}/{expected}) and no write "
                    f"for {age:.0f}s",
                }
            )

    for path in sorted(out_dir.glob("*.judged.jsonl")):
        name = path.name.split(".")[0]
        rows = _rows(path)
        if not rows:
            continue
        malformed = sum(1 for r in rows if r.get("judge_label") == "__MALFORMED__")
        share = round(100 * malformed / len(rows), 2)
        stages.setdefault(name, {})["judge_rows"] = len(rows)
        stages[name]["judge_malformed_pct"] = share
        if share > THRESHOLDS["judge_malformed_pct"]:
            findings.append(
                {
                    "stage": name,
                    "check": "judge",
                    "detail": f"{malformed}/{len(rows)} malformed labels "
                    f"({share}%)",
                }
            )

    server = _server_ok()
    if not server:
        findings.append(
            {"stage": "-", "check": "server", "detail": "llama.cpp not answering"}
        )

    return {
        "schema": "av-watchdog-v1",
        "verdict": "HEALTHY" if not findings else "ATTENTION",
        "server_ok": server,
        "thresholds": THRESHOLDS,
        "stages": stages,
        "findings": findings,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a running AV stage")
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected", type=int, default=1540)
    args = parser.parse_args(argv)
    result = check(Path(args.out), args.expected)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] == "HEALTHY" else 2


if __name__ == "__main__":
    sys.exit(main())

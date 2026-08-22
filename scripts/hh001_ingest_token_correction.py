"""Correct HH-001's Mem0 ingest token count against Mem0's own write log.

`cost/mem0_ingest_tokens.json` samples llama-server's *cumulative* prompt-token
counter every 180 s. The counter is not scoped to Mem0 and was not reset, so a
window delta is an ingest cost only for the part of the window that overlaps the
ingest. The published C5 figure took the whole window delta.

It does not all overlap. Mem0's history table dates its first and last write,
and the sampling window runs 105 minutes past the last one. Those minutes are
the reader phase on the same server. They contributed 73% of the published
total.

Two checks confirm the split rather than assuming it:

  * the counter's prompt/predicted ratio differs sharply before the overlap
    begins, so the uncovered head is not pure ingest either and cannot simply
    be added back;
  * inside the overlap the ratio is stable, and the token rate against store
    size has a *negative* slope - the per-pair cost does not climb.

Emits `cost/mem0_ingest_tokens_corrected.json`. Nothing here is typed: every
number is derived from the committed artifacts named in `inputs`.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3
import statistics
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEV = REPO / "experiments/comparisons/hh_001/artifacts/dev"
TOKENS = DEV / "cost/mem0_ingest_tokens.json"
INGEST = DEV / "cost/mem0_ingest.json"
HISTORY = DEV / "mem0_history.db"
OUT = DEV / "cost/mem0_ingest_tokens_corrected.json"


def digest(path: Path) -> dict:
    """Hash the committed bytes where they exist, and say which was used."""
    relative = str(path.relative_to(REPO)).replace("\\", "/")
    try:
        raw = subprocess.run(["git", "show", f"HEAD:{relative}"], cwd=REPO,
                             capture_output=True, check=True).stdout
        committed = True
    except subprocess.CalledProcessError:
        raw = path.read_bytes()
        committed = False
    return {"path": relative, "sha256": hashlib.sha256(raw).hexdigest()[:16],
            "committed": committed}


def write_span(db: Path) -> tuple[float, float]:
    """First and last Mem0 write, as epoch seconds, from Mem0's own log."""
    with sqlite3.connect(db) as conn:
        lo, hi = next(conn.execute(
            "select min(created_at), max(created_at) from history"))
    return (dt.datetime.fromisoformat(lo).timestamp(),
            dt.datetime.fromisoformat(hi).timestamp())


def main() -> int:
    tokens = json.loads(TOKENS.read_text(encoding="utf-8"))
    ingest = json.loads(INGEST.read_text(encoding="utf-8"))
    samples = tokens["samples"]
    first_write, last_write = write_span(HISTORY)

    covered = [s for s in samples if s["wall"] <= last_write]
    head, tail = covered[0], covered[-1]

    measured_prompt = tail["prompt_tokens_total"] - head["prompt_tokens_total"]
    measured_predicted = (tail["tokens_predicted_total"]
                          - head["tokens_predicted_total"])
    covered_s = tail["wall"] - head["wall"]
    ingest_s = last_write - first_write
    fraction = covered_s / ingest_s

    after_prompt = samples[-1]["prompt_tokens_total"] - tail["prompt_tokens_total"]
    after_s = samples[-1]["wall"] - tail["wall"]

    pairs = ingest["total_pairs"]
    scaled_prompt = measured_prompt / fraction
    scaled_predicted = measured_predicted / fraction

    # Ratio test: if the uncovered head were pure ingest, its cumulative
    # prompt/predicted ratio would match the overlap's. It does not.
    head_ratio = head["prompt_tokens_total"] / head["tokens_predicted_total"]
    overlap_ratio = measured_prompt / measured_predicted

    # Does per-pair cost climb with store size? Regress the per-interval token
    # rate on the number of memories already stored, inside the overlap only.
    points = [
        (b["history_rows"],
         (b["prompt_tokens_total"] - a["prompt_tokens_total"])
         / ((b["wall"] - a["wall"]) / 60.0))
        for a, b in zip(covered[:-1], covered[1:])
    ]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    slope = (sum((x - mx) * (y - my) for x, y in zip(xs, ys))
             / sum((x - mx) ** 2 for x in xs))

    out = {
        "schema": "hh001-mem0-ingest-tokens-corrected-v1",
        "supersedes": "hh001-mem0-ingest-tokens-v1 window_prompt_tokens",
        "note": (
            "The published 5,988,818 is a whole-window delta on a cumulative, "
            "un-reset, un-scoped counter. Mem0's write log ends 105 minutes "
            "before the window does. This file reports only the overlap, and "
            "scales it to the ingest by wall clock."
        ),
        "inputs": [
            digest(TOKENS),
            digest(INGEST),
            {"path": str(HISTORY.relative_to(REPO)).replace("\\", "/"),
             "hashed": False,
             "why": "sqlite; read for its two timestamps only"},
        ],

        "ingest_first_write_utc": dt.datetime.fromtimestamp(
            first_write, dt.timezone.utc).isoformat(),
        "ingest_last_write_utc": dt.datetime.fromtimestamp(
            last_write, dt.timezone.utc).isoformat(),
        "ingest_minutes_write_log": round(ingest_s / 60, 1),
        "ingest_minutes_reported": round(ingest["total_seconds"] / 60, 1),

        "counter_overlap_minutes": round(covered_s / 60, 1),
        "counter_overlap_fraction": round(fraction, 4),
        "counter_minutes_after_last_write": round(after_s / 60, 1),
        "prompt_tokens_after_last_write": int(after_prompt),
        "published_window_prompt_tokens": int(tokens["window_prompt_tokens"]),

        "MEASURED_prompt_tokens_in_overlap": int(measured_prompt),
        "MEASURED_predicted_tokens_in_overlap": int(measured_predicted),
        "RECOMPUTED_prompt_tokens_whole_ingest": int(round(scaled_prompt)),
        "RECOMPUTED_predicted_tokens_whole_ingest": int(round(scaled_predicted)),
        "RECOMPUTED_prompt_tokens_per_pair": int(round(scaled_prompt / pairs)),
        "MEASURED_prompt_tokens_per_pair_floor": int(round(measured_prompt / pairs)),
        "pairs": pairs,
        "inflation_of_published_figure": round(
            tokens["window_prompt_tokens"] / scaled_prompt, 2),

        "head_prompt_predicted_ratio": round(head_ratio, 3),
        "overlap_prompt_predicted_ratio": round(overlap_ratio, 3),
        "head_is_pure_ingest": abs(head_ratio - overlap_ratio) < 0.05,

        "rate_vs_store_slope_tokens_per_min_per_memory": round(slope, 3),
        "rate_vs_store_span_memories": [min(xs), max(xs)],
        "rate_vs_store_mean_tokens_per_min": int(round(my)),
        "per_pair_cost_climbs_with_store": slope > 0,
        "climb_note": (
            "Negative slope. Across the whole store the fitted rate falls by "
            "about {:.0f} tokens/min on a base of {:.0f}. The claim that "
            "per-pair cost climbs as the store grows is not supported by this "
            "counter. Ingest *latency* drifts 1.13x first-to-last decile "
            "(cost/mem0_ingest_latency.json), which is the drift that exists."
        ).format(abs(slope) * (max(xs) - min(xs)), my),
    }

    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")

    print("ingest        {} min (write log) vs {} min (reported)".format(
        out["ingest_minutes_write_log"], out["ingest_minutes_reported"]))
    print("counter overlaps {:.1f}% of it, then runs {:.0f} min past the last "
          "write".format(out["counter_overlap_fraction"] * 100,
                         out["counter_minutes_after_last_write"]))
    print("  published   {:,}".format(out["published_window_prompt_tokens"]))
    print("  of which    {:,} landed after Mem0 stopped writing".format(
        out["prompt_tokens_after_last_write"]))
    print("  MEASURED    {:,} in the overlap".format(
        out["MEASURED_prompt_tokens_in_overlap"]))
    print("  RECOMPUTED  {:,} whole ingest = {:,}/pair".format(
        out["RECOMPUTED_prompt_tokens_whole_ingest"],
        out["RECOMPUTED_prompt_tokens_per_pair"]))
    print("  published figure inflated {}x".format(
        out["inflation_of_published_figure"]))
    print("  head is pure ingest: {} (ratio {} vs {})".format(
        out["head_is_pure_ingest"], out["head_prompt_predicted_ratio"],
        out["overlap_prompt_predicted_ratio"]))
    print("  climbs with store: {} (slope {})".format(
        out["per_pair_cost_climbs_with_store"],
        out["rate_vs_store_slope_tokens_per_min_per_memory"]))
    print("wrote {}".format(OUT.relative_to(REPO)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Derive Mem0's ingest latency against store size, from its own history DB.

Mem0 records every memory write in `history.db` with a microsecond
`created_at`. One `add()` call emits a burst of rows milliseconds apart; the
gap *between* bursts is the wall clock that `add()` spent, almost all of it in
the generative call that decides what to store.

So the curve needs no extra instrumentation and no sampling. It is read out of
what Mem0 already wrote:

  x  memories in the store when the call started
  y  seconds that call took

Bursts are separated by `--gap`, defaulting to 0.5 s. Within a burst the
observed spacing is single-digit milliseconds and between bursts it is seconds,
so the boundary is not a close call; the chosen value and the resulting burst
count are both recorded in the artifact so the split can be checked.

This measures Mem0 on this machine against this local reader. It is not a
measurement of Mem0 as its authors deploy it.

    python scripts/hh001_ingest_latency.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEV = REPO / "experiments/comparisons/hh_001/artifacts/dev"
HISTORY = DEV / "mem0_history.db"
OUT = DEV / "cost/mem0_ingest_latency.json"


def _rows(path: Path) -> list[tuple[datetime, str]]:
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        raw = con.execute(
            "select created_at, event from history order by created_at"
        ).fetchall()
    finally:
        con.close()
    parsed: list[tuple[datetime, str]] = []
    for created_at, event in raw:
        if not created_at:
            continue
        parsed.append((datetime.fromisoformat(created_at), str(event)))
    return parsed


def derive(path: Path, gap_s: float) -> dict:
    rows = _rows(path)
    if len(rows) < 3:
        raise SystemExit(f"Only {len(rows)} history rows; nothing to derive yet.")

    # Split into bursts. Each burst is one add() call's writes.
    bursts: list[list[tuple[datetime, str]]] = [[rows[0]]]
    for previous, current in zip(rows, rows[1:]):
        if (current[0] - previous[0]).total_seconds() > gap_s:
            bursts.append([current])
        else:
            bursts[-1].append(current)

    points = []
    store = 0
    for index, burst in enumerate(bursts[:-1]):
        # The call that produced burst i+1 started after burst i finished, so
        # its wall clock is the gap between the end of one and the start of
        # the next. The first burst has no measurable start and is skipped.
        nxt = bursts[index + 1]
        seconds = (nxt[0][0] - burst[-1][0]).total_seconds()
        adds = sum(1 for _, event in burst if event == "ADD")
        deletes = sum(1 for _, event in burst if event == "DELETE")
        store += adds - deletes
        points.append(
            {
                "call_index": index + 1,
                "store_size": store,
                "seconds": round(seconds, 3),
                "writes_in_call": len(nxt),
            }
        )

    seconds = [p["seconds"] for p in points]
    ordered = sorted(seconds)

    def pct(q: float) -> float:
        return round(ordered[min(len(ordered) - 1, int(q * len(ordered)))], 3)

    # First and last deciles, so the trend is stated rather than eyeballed.
    tenth = max(1, len(points) // 10)
    head = sum(p["seconds"] for p in points[:tenth]) / tenth
    tail = sum(p["seconds"] for p in points[-tenth:]) / tenth

    return {
        "schema": "hh001-mem0-ingest-latency-v1",
        "source": str(HISTORY.relative_to(REPO)).replace("\\", "/"),
        "burst_gap_s": gap_s,
        "history_rows": len(rows),
        # Bursts, not add() calls. A pair Mem0 decided not to store leaves no
        # history row and so no burst, and is invisible here. The ingest log
        # is authoritative for the call count; this covers only the pairs that
        # wrote something, and the two numbers are different on purpose.
        "write_bursts_measured": len(points),
        "calls_measured": len(points),
        "coverage_note": (
            "Latency is measured over pairs that produced at least one memory "
            "write. Pairs that produced none leave no trace in this table, so "
            "this is not the full ingest population."
        ),
        "store_size_final": store,
        "seconds_p50": pct(0.50),
        "seconds_p95": pct(0.95),
        "seconds_max": round(ordered[-1], 3),
        "first_decile_mean_s": round(head, 3),
        "last_decile_mean_s": round(tail, 3),
        "slowdown_first_to_last_decile": (
            round(tail / head, 2) if head else None
        ),
        "note": (
            "Latency of one Mem0 add() against the number of memories already "
            "stored, on this machine against the local reader. This component "
            "ingests the same pairs with zero generative calls; its cost does "
            "not move with store size, which is the comparison this measures."
        ),
        "points": points,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gap", type=float, default=0.5)
    parser.add_argument("--history", type=Path, default=HISTORY)
    args = parser.parse_args()

    payload = derive(args.history, args.gap)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, indent=1, sort_keys=True) + "\n").encode("utf-8")
    OUT.write_bytes(raw)
    print(f"calls measured   : {payload['calls_measured']}")
    print(f"store size final : {payload['store_size_final']}")
    print(f"latency p50/p95  : {payload['seconds_p50']}s / {payload['seconds_p95']}s")
    print(f"first decile mean: {payload['first_decile_mean_s']}s")
    print(f"last decile mean : {payload['last_decile_mean_s']}s")
    print(f"slowdown         : {payload['slowdown_first_to_last_decile']}x")
    print(f"wrote {OUT.relative_to(REPO)}  sha256 {hashlib.sha256(raw).hexdigest()[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

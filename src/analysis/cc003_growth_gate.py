"""G-E0: does the extracted library carry Study 010's growth leak?

DX-002 returned Branch B - the `<retrieved_stm>` block in the Study 010
runner never saturated - and section 0.4 makes that a block on CC-003.
The block is on shipping a ceiling while an unbudgeted component grows
beside it, so the question this gate answers is narrow and specific:

    does `episodic` have that component?

It should not. The runner maintained the recency window and the retrieval
tier as separate budgets; `episodic.build_context` routes the recency
window, the K-threshold hits, and the coverage selection through a single
`budget` in `pack_stm_payload`, which charges the exact serialized cost of
the whole two-block payload on every admission. If that is true in
practice and not only in the docstring, the leak is a property of the
runner and CC-003 is unblocked.

The replay is the real thing: all 1,000 committed arm L episodes with
their committed embeddings, replayed turn by turn so that the store grows
exactly as it did during the run. No embedder is needed - `build_context`
is a pure function of episodes, a query vector, a budget, and a config -
so this is offline and deterministic.

The gate is the DX-002 saturation criterion applied to the library's own
output, plus the ceiling itself.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "episodic" / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "episodic" / "src"))

from episodic._config import EpisodicConfig  # noqa: E402
from episodic._context import build_context  # noqa: E402

from src.analysis.dx002_context_growth import (  # noqa: E402
    MATERIALITY_FLOOR_CHARS,
    block_summary,
    half_over_half,
    has_saturated,
    p95_growth,
)

ARM_L_DB = (
    REPO_ROOT
    / "experiments"
    / "study_010"
    / "runs"
    / "study_010_full_001"
    / "arm_l"
    / "study.db"
)

BUDGET_CHARS = 32_000
TERMINAL_WINDOW = 300


def load_episodes(db_path: Path = ARM_L_DB) -> list[dict]:
    connection = sqlite3.connect(str(db_path))
    try:
        rows = connection.execute(
            """
            SELECT id, turn_number, user_message, assistant_message, embedding
            FROM episodes
            ORDER BY turn_number ASC, id ASC
            """
        ).fetchall()
    finally:
        connection.close()
    return [
        {
            "id": row[0],
            "turn_number": row[1],
            "user_message": row[2],
            "assistant_message": row[3],
            "embedding": row[4],
        }
        for row in rows
    ]


def replay(
    episodes: list[dict],
    *,
    budget: int = BUDGET_CHARS,
    config: EpisodicConfig | None = None,
    step: int = 1,
) -> list[dict]:
    """Rebuild context at every turn, with the store grown to that turn.

    The query vector is the turn's own embedding. Study 010 did not commit
    a separate query embedding per turn, and the choice does not affect
    what this gate measures: the ceiling and the saturation of the
    delivered block are properties of packing, not of which episodes the
    relevance term happens to favour.
    """
    config = config or EpisodicConfig()
    rows = []
    for index in range(step - 1, len(episodes), step):
        visible = episodes[: index + 1]
        block, report = build_context(
            episodes=visible,
            query_embedding=visible[-1]["embedding"],
            budget=budget,
            config=config,
        )
        rows.append(
            {
                "turn": int(visible[-1]["turn_number"]),
                "store_episodes": len(visible),
                "delivered_chars": len(block),
                "chars_wanted": report.chars_wanted,
                "episodes_delivered": report.episodes_delivered,
                "episodes_dropped": report.episodes_dropped,
                "truncated": report.truncated,
                "over_budget": len(block) > budget,
            }
        )
    return rows


def evaluate(rows: list[dict], budget: int = BUDGET_CHARS) -> dict:
    delivered = [row["delivered_chars"] for row in rows]
    breaches = [row for row in rows if row["over_budget"]]

    series_rows = [
        {"turn": row["turn"], "delivered_chars": row["delivered_chars"]}
        for row in rows
    ]
    blocks = block_summary(series_rows, "delivered_chars")
    series = {"blocks": blocks}
    saturated = has_saturated(series)
    growth = p95_growth(series)
    comparison = half_over_half(series_rows, "delivered_chars", TERMINAL_WINDOW)

    ceiling_holds = not breaches
    material_growth = abs(growth) >= MATERIALITY_FLOOR_CHARS
    bounded = ceiling_holds and (saturated or not material_growth)

    return {
        "record": "CC-003 G-E0 library growth gate",
        "question": (
            "Does episodic reproduce the unbudgeted STM growth DX-002 found "
            "in the Study 010 runner?"
        ),
        "budget_chars": budget,
        "turns_replayed": len(rows),
        "ceiling": {
            "holds": ceiling_holds,
            "max_delivered_chars": max(delivered),
            "min_delivered_chars": min(delivered),
            "breach_count": len(breaches),
            "breaches": breaches[:10],
        },
        "saturation": {
            "saturated": saturated,
            "p95_growth_chars": growth,
            "materiality_floor_chars": MATERIALITY_FLOOR_CHARS,
            "material_growth": material_growth,
            "blocks": blocks,
            "window_over_window": comparison,
        },
        "truncation": {
            "turns_truncated": sum(1 for row in rows if row["truncated"]),
            "max_chars_wanted": max(row["chars_wanted"] for row in rows),
            "max_episodes_dropped": max(
                row["episodes_dropped"] for row in rows
            ),
        },
        "bounded": bounded,
        "status": "PASS" if bounded else "FAIL",
        "verdict": (
            "The library does not carry the leak. The delivered block is "
            "bounded by the budget at every turn and does not grow with "
            "store size, so DX-002's Branch B is a property of the Study "
            "010 runner's separate STM budget, not of episodic. CC-003 is "
            "unblocked."
            if bounded
            else "The library reproduces the leak. CC-003 remains blocked: "
            "the growing component must be budgeted or removed first."
        ),
    }


def write_artifacts(result: dict, rows: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "ge0_growth_gate.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    lines = [
        "turn,store_episodes,delivered_chars,chars_wanted,"
        "episodes_delivered,episodes_dropped,truncated,over_budget"
    ]
    for row in rows:
        lines.append(
            f"{row['turn']},{row['store_episodes']},{row['delivered_chars']},"
            f"{row['chars_wanted']},{row['episodes_delivered']},"
            f"{row['episodes_dropped']},{row['truncated']},{row['over_budget']}"
        )
    (output_dir / "ge0_replay_rows.csv").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CC-003 G-E0 gate.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--step", type=int, default=1)
    args = parser.parse_args()

    episodes = load_episodes()
    rows = replay(episodes, step=args.step)
    result = evaluate(rows)
    write_artifacts(result, rows, args.output_dir)
    print(f"G-E0 {result['status']}")
    print(
        f"  max delivered {result['ceiling']['max_delivered_chars']:,} of "
        f"{result['budget_chars']:,}; breaches "
        f"{result['ceiling']['breach_count']}"
    )
    print(
        f"  saturated={result['saturation']['saturated']} "
        f"p95 growth {result['saturation']['p95_growth_chars']:+,.0f} chars"
    )
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

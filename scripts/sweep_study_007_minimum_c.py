"""S7-T-026 — offline minimum-viable-C sweep. OBSERVATIONAL ONLY.

The pre-registration is explicit: **C is not changed in this study.** Formation
ships as Study 006 accepted it, at C = 50. This sweep answers a question for
*future* studies — what is the smallest per-topic cap that still forms 4/4 —
and produces no input to any Study 007 bar.

Amendment 001 raised C from 3 to 50 after the Study 006 replay gate failed at
0/4, having diagnosed that C = 3 was carried from a ~30-episode pool to a
~300-span pool. 50 was chosen as sufficient, not as minimal, and the question
of how much of it is actually needed has been open since.

Read-only over Study 005's preserved raw store, the same input Study 006's
replay used. Artifacts are hashed before and after.
"""

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.replay_study_006_policy import (  # noqa: E402
    SOURCE_DB,
    hash_study_005_artifacts,
    matches_plant,
    parse_plant_key,
)
from src.memory.span_dream_engine import SpanDreamEngine  # noqa: E402

OUT = REPO / "experiments/study_007/replay/minimum_c_sweep.json"
C_SWEEP = (3, 5, 8, 10, 15, 20, 25, 30, 40, 50)
SALIENCE_FLOOR = 0.15


def domains_formed(selected_by_domain: dict, plants: list[dict]) -> dict:
    """Which domains have at least one planted fact in the selected spans."""
    formed = {}
    for plant in plants:
        domain = plant["domain"]
        texts = selected_by_domain.get(domain, [])
        hit = any(matches_plant(text, plant["terms"]) for text in texts)
        formed.setdefault(domain, {"facts": 0, "total": 0})
        formed[domain]["total"] += 1
        formed[domain]["facts"] += 1 if hit else 0
    return formed


def main() -> int:
    before = hash_study_005_artifacts()
    plants = parse_plant_key()

    from src.embeddings.provider import embed

    conn = sqlite3.connect(f"file:{SOURCE_DB.as_posix()}?mode=ro", uri=True)
    engine = SpanDreamEngine(conn=None, embed_fn=embed)

    # Build the candidate pool once per dream event; only the cap varies.
    pools = []
    try:
        for turn, topic_id, logged in conn.execute(
            "SELECT turn, topic_id, episodes_evaluated FROM dream_events "
            "ORDER BY turn"
        ).fetchall():
            rows = conn.execute(
                """
                SELECT id, topic_id, user_message, assistant_message,
                       turn_number, ground_truth_domain, role, text
                FROM episodes
                WHERE topic_id = ? AND turn_number <= ?
                ORDER BY turn_number, created_at, id
                """,
                (topic_id, turn),
            ).fetchall()
            columns = [
                "id", "topic_id", "user_message", "assistant_message",
                "turn_number", "ground_truth_domain", "role", "text",
            ]
            episodes = [dict(zip(columns, row)) for row in rows]
            if len(episodes) != logged:
                raise AssertionError(
                    f"Snapshot reconstruction for turn {turn} produced "
                    f"{len(episodes)} episodes, Study 005 logged {logged}"
                )
            domains = {
                e["ground_truth_domain"] for e in episodes
                if e["ground_truth_domain"]
            }
            candidates, _, _ = engine.build_candidates(episodes)
            pools.append({
                "turn": turn,
                "domain": sorted(domains)[0] if len(domains) == 1 else None,
                "candidates": candidates,
            })
    finally:
        conn.close()

    results = []
    print(f"{'C':>4} {'domains formed':>15}  per-domain facts")
    for cap in C_SWEEP:
        selected_by_domain: dict[str, list[str]] = {}
        total_records = 0
        for pool in pools:
            ranked = sorted(pool["candidates"], key=engine._rank_key)
            clearing = [c for c in ranked if c.salience >= SALIENCE_FLOOR]
            chosen = clearing[:cap]
            total_records += len(chosen)
            selected_by_domain.setdefault(pool["domain"], []).extend(
                c.span.text for c in chosen
            )

        formed = domains_formed(selected_by_domain, plants)
        count = sum(1 for v in formed.values() if v["facts"] > 0)
        results.append({
            "cap": cap,
            "domains_formed": count,
            "records": total_records,
            "per_domain": formed,
        })
        detail = " ".join(
            f"{d.split('_')[0]}={v['facts']}/{v['total']}"
            for d, v in sorted(formed.items())
        )
        print(f"{cap:>4} {count:>13}/4  {detail}")

    viable = [r for r in results if r["domains_formed"] == 4]
    minimum = min(viable, key=lambda r: r["cap"]) if viable else None
    print()
    if minimum:
        print(
            f"Minimum viable C forming 4/4: {minimum['cap']} "
            f"({minimum['records']} records, vs 50 -> "
            f"{results[-1]['records']} records)"
        )
    else:
        print("No swept C forms 4/4 on this store.")

    after = hash_study_005_artifacts()
    unchanged = before == after
    print(f"Study 005 artifacts unchanged: {unchanged}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "observational_only": True,
                "note": (
                    "C is NOT changed in Study 007. This informs future "
                    "studies and feeds no bar."
                ),
                "salience_floor": SALIENCE_FLOOR,
                "shipped_cap": SpanDreamEngine.PER_TOPIC_CAP,
                "sweep": results,
                "minimum_viable_c": minimum["cap"] if minimum else None,
                "artifacts_unchanged": unchanged,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0 if unchanged else 1


if __name__ == "__main__":
    sys.exit(main())

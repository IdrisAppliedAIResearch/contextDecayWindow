"""S6-T-011/012 — replay the Study 006 selection policy over Study 005's raw store.

Read-only by construction: the Study 005 database is opened with SQLite's
``mode=ro`` URI and every artifact the replay touches is SHA-256 hashed before and
after, with the run failing if anything moved. Nothing is written back into
Study 005; all output lands under ``experiments/study_006/replay/``.

The replay reconstructs each of Study 005's four dream events - the same topics,
the same episode snapshots - and asks what the revised policy would have selected.
It cannot establish generalization, because the policy was designed after seeing
this data. Its job is narrower and stated in the pre-registration: prevent
spending a live run on a policy that provably cannot work.
"""

import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.memory.span_dream_engine import (  # noqa: E402
    SpanDreamEngine,
    calculate_span_salience,
)
from src.memory.span_segmenter import (  # noqa: E402
    extractor_name,
    segmenter_name,
)

SOURCE_DB = (
    REPO
    / "experiments/study_005/runs/study_005_full_001/condition_c/study.db"
)
SOURCE_SALIENCE = (
    REPO
    / "experiments/study_005/runs/study_005_full_001/condition_c"
    / "dream_analysis/episode_salience.csv"
)
PLANT_KEY = REPO / "experiments/study_006/q_facts_key.md"
OUTPUT_DIR = REPO / "experiments/study_006/replay"

DOMAIN_BY_HEADING = {
    "Civil engineering": "civil_engineering",
    "Renaissance art": "renaissance_art",
    "Monetary policy": "monetary_policy",
    "Marine biology": "marine_biology",
}

# Pre-registered: the Study 005 near-misses whose new ranks must be recorded.
NEAR_MISS_TURNS = {
    "renaissance_art": [55, 56, 60],
    "marine_biology": [100, 101, 102],
}

F_SWEEP = [0.05, 0.10, 0.125, 0.15, 0.175, 0.20, 0.25, 0.30]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_study_005_artifacts() -> dict[str, str]:
    root = REPO / "experiments/study_005/runs/study_005_full_001"
    return {
        str(path.relative_to(REPO)): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def parse_plant_key() -> list[dict]:
    """Read the locked plant key into rows of (domain, fact_id, terms, turn)."""
    rows = []
    domain = None
    row_pattern = re.compile(
        r"^\|\s*([a-z_]+)\s*\|\s*(.+?)\s*\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*$"
    )
    in_diff = False
    for line in PLANT_KEY.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
            in_diff = heading.startswith("Diff from")
            domain = DOMAIN_BY_HEADING.get(heading)
            continue
        if in_diff or domain is None:
            continue
        match = row_pattern.match(line)
        if not match:
            continue
        fact_id, terms_cell, turn, dependency = match.groups()
        rows.append(
            {
                "domain": domain,
                "fact_id": fact_id,
                "terms": [t.strip() for t in terms_cell.split(";") if t.strip()],
                "turn": int(turn),
                "rubric_dependency": dependency,
            }
        )
    return rows


def load_study_005_ranks() -> dict[int, dict]:
    """Per-episode Study 005 rank within its dream event, keyed by source turn."""
    import csv

    by_event: dict[int, list[dict]] = {}
    with SOURCE_SALIENCE.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            by_event.setdefault(int(row["turn"]), []).append(row)

    ranks: dict[int, dict] = {}
    for event_turn, rows in by_event.items():
        ordered = sorted(
            rows,
            key=lambda r: (-int(r["salience"]), int(r["episode_turn"])),
        )
        for rank, row in enumerate(ordered, start=1):
            ranks[int(row["episode_turn"])] = {
                "study_005_rank": rank,
                "study_005_salience": int(row["salience"]),
                "study_005_selected": row["selected"] == "True",
                "event_turn": event_turn,
                "candidates_in_event": len(rows),
            }
    return ranks


def matches_plant(text: str, terms: list[str]) -> bool:
    lowered = text.casefold()
    return all(term.casefold() in lowered for term in terms)


def replay() -> dict:
    if not SOURCE_DB.exists():
        raise FileNotFoundError(f"Study 005 replay input missing: {SOURCE_DB}")

    before = hash_study_005_artifacts()

    from src.embeddings.provider import embed

    conn = sqlite3.connect(f"file:{SOURCE_DB.as_posix()}?mode=ro", uri=True)
    engine = SpanDreamEngine(conn=None, embed_fn=embed)

    events = []
    try:
        dream_events = conn.execute(
            "SELECT turn, topic_id, topic_label, event_type, "
            "episodes_evaluated FROM dream_events ORDER BY turn"
        ).fetchall()

        for turn, topic_id, topic_label, event_type, logged_count in dream_events:
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
                "id",
                "topic_id",
                "user_message",
                "assistant_message",
                "turn_number",
                "ground_truth_domain",
                "role",
                "text",
            ]
            episodes = [dict(zip(columns, row)) for row in rows]
            if len(episodes) != logged_count:
                raise AssertionError(
                    f"Snapshot reconstruction for turn {turn} produced "
                    f"{len(episodes)} episodes, but Study 005 logged "
                    f"{logged_count}"
                )

            domains = {
                episode["ground_truth_domain"]
                for episode in episodes
                if episode["ground_truth_domain"]
            }
            domain = sorted(domains)[0] if len(domains) == 1 else None

            candidates, all_spans, spans_evaluated = engine.build_candidates(
                episodes
            )
            for candidate in candidates:
                candidate.embedding = engine._embed(candidate.span.text)
            survivors = engine.deduplicate(candidates)
            ranked = sorted(survivors, key=engine._rank_key)

            texts_by_episode = {e["id"]: e["text"] for e in episodes}
            offset_failures = [
                {
                    "episode_id": c.span.episode_id,
                    "start": c.span.start,
                    "end": c.span.end,
                }
                for c in ranked
                if texts_by_episode[c.span.episode_id][
                    c.span.start:c.span.end
                ]
                != c.span.text
            ]

            events.append(
                {
                    "turn": turn,
                    "topic_id": topic_id,
                    "topic_label": topic_label,
                    "event_type": event_type,
                    "domain": domain,
                    "episodes_evaluated": len(episodes),
                    "spans_evaluated": spans_evaluated,
                    "spans_eligible": len(candidates),
                    "survivors": len(survivors),
                    "duplicates_collapsed": len(candidates) - len(survivors),
                    "offset_failures": offset_failures,
                    "ranked": [
                        {
                            "rank": rank,
                            "episode_id": c.span.episode_id,
                            "turn_number": c.span.turn_number,
                            "role": c.span.role,
                            "start": c.span.start,
                            "end": c.span.end,
                            "word_count": c.span.word_count,
                            "named_entities": c.span.named_entities,
                            "numeric_tokens": c.span.numeric_tokens,
                            "base": c.base,
                            "density": c.density,
                            "salience": c.salience,
                            "text": c.span.text,
                        }
                        for rank, c in enumerate(ranked, start=1)
                    ],
                    "rejected": [
                        {
                            "turn_number": s.turn_number,
                            "role": s.role,
                            "reason": s.rejection_reason,
                            "word_count": s.word_count,
                            "text": s.text,
                        }
                        for s in all_spans
                        if not s.eligible
                    ],
                }
            )
    finally:
        conn.close()

    after = hash_study_005_artifacts()
    if before != after:
        changed = sorted(
            key for key in before | after if before.get(key) != after.get(key)
        )
        raise AssertionError(
            f"Replay mutated Study 005 artifacts: {changed}"
        )

    return {
        "segmenter": segmenter_name(),
        "extractor": extractor_name(),
        "source_db_sha256": sha256_file(SOURCE_DB),
        "artifacts_verified": len(before),
        "artifacts_unchanged": True,
        "cap": SpanDreamEngine.PER_TOPIC_CAP,
        "dedup_threshold": SpanDreamEngine.DEDUP_THRESHOLD,
        "events": events,
    }


def evaluate(result: dict, floor: float) -> dict:
    """Apply the coverage floor and cap, then score the gate criteria."""
    plants = parse_plant_key()
    study_005_ranks = load_study_005_ranks()

    per_event = []
    domain_hits: dict[str, list] = {}
    for event in result["events"]:
        ranked = event["ranked"]
        # Amendment 001: the floor applies per span, then the cap binds.
        clearing = [span for span in ranked if span["salience"] >= floor]
        selected = clearing[: result["cap"]]
        marker = not clearing

        hits = []
        for plant in plants:
            if plant["domain"] != event["domain"]:
                continue
            selected_match = next(
                (
                    s
                    for s in selected
                    if matches_plant(s["text"], plant["terms"])
                ),
                None,
            )
            anywhere = next(
                (
                    s
                    for s in ranked
                    if matches_plant(s["text"], plant["terms"])
                ),
                None,
            )
            hits.append(
                {
                    "fact_id": plant["fact_id"],
                    "domain": plant["domain"],
                    "terms": plant["terms"],
                    "source_turn": plant["turn"],
                    "selected": selected_match is not None,
                    "selected_rank": (
                        selected_match["rank"] if selected_match else None
                    ),
                    "best_rank": anywhere["rank"] if anywhere else None,
                    "best_salience": (
                        anywhere["salience"] if anywhere else None
                    ),
                    "matched_text": (
                        anywhere["text"] if anywhere else None
                    ),
                }
            )
        domain_hits.setdefault(event["domain"], []).extend(hits)

        per_event.append(
            {
                "turn": event["turn"],
                "domain": event["domain"],
                "marker_written": marker,
                "records_written": len(selected),
                "selected": selected,
                "plants": hits,
            }
        )

    domains_formed = {
        domain: any(hit["selected"] for hit in hits)
        for domain, hits in domain_hits.items()
    }

    near_misses = []
    for domain, turns in NEAR_MISS_TURNS.items():
        for source_turn in turns:
            event = next(
                (e for e in result["events"] if e["domain"] == domain), None
            )
            if event is None:
                continue
            spans = [
                s for s in event["ranked"] if s["turn_number"] == source_turn
            ]
            best = min(spans, key=lambda s: s["rank"]) if spans else None
            clearing_ranks = [
                span["rank"]
                for span in event["ranked"]
                if span["salience"] >= floor
            ]
            selected_now = bool(
                best
                and best["rank"] in clearing_ranks[: result["cap"]]
            )
            near_misses.append(
                {
                    "domain": domain,
                    "source_turn": source_turn,
                    "study_005": study_005_ranks.get(source_turn),
                    "study_006_best_rank": best["rank"] if best else None,
                    "study_006_salience": best["salience"] if best else None,
                    "study_006_candidates": len(event["ranked"]),
                    "selected_under_006": selected_now,
                    "text": best["text"] if best else None,
                }
            )

    offset_failures = sum(
        len(event["offset_failures"]) for event in result["events"]
    )
    markers = sum(1 for e in per_event if e["marker_written"])

    return {
        "floor": floor,
        "domains_formed": domains_formed,
        "domains_formed_count": sum(domains_formed.values()),
        "domains_total": len(domains_formed),
        "gate_4_of_4": all(domains_formed.values()),
        "non_content_selections": markers,
        "gate_zero_non_content": markers == 0,
        "offset_failures": offset_failures,
        "gate_offset_verbatim": offset_failures == 0,
        "per_event": per_event,
        "near_misses": near_misses,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = replay()

    sweep = []
    for floor in F_SWEEP:
        verdict = evaluate(result, floor)
        sweep.append(
            {
                "floor": floor,
                "domains_formed_count": verdict["domains_formed_count"],
                "gate_4_of_4": verdict["gate_4_of_4"],
                "non_content_selections": verdict["non_content_selections"],
                "total_records": sum(
                    e["records_written"] for e in verdict["per_event"]
                ),
            }
        )

    default_floor = float(
        os.environ.get("CDW_SALIENCE_FLOOR", SpanDreamEngine.SALIENCE_FLOOR)
    )
    verdict = evaluate(result, default_floor)

    payload = {
        "replay": result,
        "verdict": verdict,
        "floor_sweep": sweep,
    }
    (OUTPUT_DIR / "replay_results.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"segmenter : {result['segmenter']}")
    print(f"extractor : {result['extractor']}")
    print(f"artifacts : {result['artifacts_verified']} hashed, unchanged")
    print()
    print(f"=== gate at F = {default_floor} ===")
    for domain, formed in verdict["domains_formed"].items():
        print(f"  {domain:20} formed={formed}")
    print(f"  4/4 domains        : {verdict['gate_4_of_4']}")
    print(f"  zero non-content   : {verdict['gate_zero_non_content']}")
    print(f"  offset-verbatim    : {verdict['gate_offset_verbatim']}")
    print()
    print("=== floor sweep ===")
    for row in sweep:
        print(
            f"  F={row['floor']:<6} domains={row['domains_formed_count']}/4 "
            f"records={row['total_records']:2} "
            f"markers={row['non_content_selections']}"
        )
    print()
    print("=== near-miss rank movement ===")
    for item in verdict["near_misses"]:
        old = item["study_005"]
        old_rank = old["study_005_rank"] if old else "?"
        print(
            f"  {item['domain']:16} turn {item['source_turn']:3}  "
            f"005 rank {old_rank:>3}  ->  006 rank "
            f"{item['study_006_best_rank']}  "
            f"selected={item['selected_under_006']}"
        )


if __name__ == "__main__":
    main()

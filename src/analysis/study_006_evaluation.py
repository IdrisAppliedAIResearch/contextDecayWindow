"""Study 006 formation, faithfulness, and bar evaluation at span granularity.

Differs from the Study 005 evaluation in one substantive way: faithfulness is
checked **at the recorded character offsets** rather than by substring
containment. A record whose text happens to appear somewhere in its source but
not where its provenance claims is a failure here, because the offsets are the
provenance claim.
"""

import sqlite3
from pathlib import Path

from src.analysis.study_005_evaluation import (
    DOMAIN_HEADINGS,
    FactTarget,
    load_fact_key,
)
from src.memory.distilled_ltm_store import CONTENT_STATUS

DOMAIN_SLUGS = {
    "civil engineering": "civil_engineering",
    "renaissance art": "renaissance_art",
    "monetary policy": "monetary_policy",
    "marine biology": "marine_biology",
}


def _records(conn: sqlite3.Connection) -> list[dict]:
    """Read distilled records, tolerating the Study 005 schema.

    The control arm runs Study 005 code from its own worktree and therefore has
    no span columns at all. Selecting them unconditionally would make the
    evaluator unable to read the very baseline it has to compare against, so the
    span fields are filled with None when absent.
    """
    wanted = [
        "id", "source_episode_id", "topic_label", "text", "status", "role",
        "span_start", "span_end", "word_count", "base", "density",
        "salience_score", "dream_event", "salience",
    ]
    available = {
        row[1] for row in conn.execute("PRAGMA table_info(distilled_ltm)")
    }
    columns = [name for name in wanted if name in available]
    order = (
        "dream_event, salience_score DESC"
        if "salience_score" in available
        else "dream_event, salience DESC"
    )
    rows = conn.execute(
        f"SELECT {', '.join(columns)} FROM distilled_ltm ORDER BY {order}"
    ).fetchall()
    missing = {name: None for name in wanted if name not in available}
    return [{**missing, **dict(zip(columns, row))} for row in rows]


def evaluate_formation(
    conn: sqlite3.Connection,
    fact_key_path: str | Path,
    span_level: bool = True,
) -> dict:
    """Which planted facts reached the distilled store, and are they faithful."""
    targets = load_fact_key(fact_key_path)
    records = _records(conn)
    content = [r for r in records if r["status"] == CONTENT_STATUS]
    non_content = [r for r in records if r["status"] != CONTENT_STATUS]

    sources = {
        episode_id: text
        for episode_id, text in conn.execute("SELECT id, text FROM episodes")
    }

    faithful, unfaithful = [], []
    for record in content:
        if span_level and record["span_start"] is not None:
            source = sources.get(record["source_episode_id"])
            ok = (
                source is not None
                and source[record["span_start"]:record["span_end"]]
                == record["text"]
            )
        else:
            source = sources.get(record["source_episode_id"])
            ok = source is not None and record["text"] in source
        (faithful if ok else unfaithful).append(record["id"])

    hits = []
    for target in targets:
        slug = DOMAIN_SLUGS[target.domain]
        match = next(
            (
                r
                for r in content
                if all(
                    term.casefold() in r["text"].casefold()
                    for term in target.required_terms
                )
            ),
            None,
        )
        hits.append(
            {
                "domain": slug,
                "fact_id": target.fact_id,
                "required_terms": list(target.required_terms),
                "rubric_dependency": target.rubric_dependency,
                "present": match is not None,
                "record_id": match["id"] if match else None,
                "text": match["text"] if match else None,
                "salience": match["salience_score"] if match else None,
            }
        )

    domains = {}
    for slug in sorted(DOMAIN_SLUGS.values()):
        domain_hits = [h for h in hits if h["domain"] == slug]
        domains[slug] = {
            "formed": any(h["present"] for h in domain_hits),
            "facts_present": sum(1 for h in domain_hits if h["present"]),
            "facts_total": len(domain_hits),
        }

    return {
        "records_total": len(records),
        "records_content": len(content),
        "records_non_content": len(non_content),
        "faithful": len(faithful),
        "unfaithful": len(unfaithful),
        "unfaithful_ids": unfaithful,
        "facts": hits,
        "domains": domains,
        "domains_formed": sum(1 for d in domains.values() if d["formed"]),
        "domains_total": len(domains),
    }


def observations(conn: sqlite3.Connection) -> dict:
    """Observational measures. No pass/fail interpretation."""
    records = [r for r in _records(conn) if r["status"] == CONTENT_STATUS]
    raw_chars = sum(
        len(text or "")
        for (text,) in conn.execute("SELECT text FROM episodes")
    )
    distilled_chars = sum(len(r["text"] or "") for r in records)

    by_role = {}
    for record in records:
        by_role[record["role"]] = by_role.get(record["role"], 0) + 1

    densities = sorted(r["density"] for r in records if r["density"] is not None)
    words = [r["word_count"] for r in records if r["word_count"] is not None]

    inventory = {}
    try:
        for eligible, reason, count in conn.execute(
            "SELECT eligible, rejection_reason, COUNT(*) FROM span_inventory "
            "GROUP BY eligible, rejection_reason"
        ):
            inventory[reason or ("eligible" if eligible else "ineligible")] = count
        spans_total = conn.execute(
            "SELECT COUNT(*) FROM span_inventory"
        ).fetchone()[0]
    except sqlite3.OperationalError:
        spans_total = None

    wanted_event_columns = [
        "turn", "topic_label", "event_type", "episodes_evaluated",
        "spans_evaluated", "spans_eligible", "survivors", "records_written",
        "marker_written", "duplicates_collapsed", "inference_calls",
    ]
    available = {
        row[1] for row in conn.execute("PRAGMA table_info(dream_events)")
    }
    event_columns = [c for c in wanted_event_columns if c in available]
    missing_event = {c: None for c in wanted_event_columns if c not in available}
    dream_events = [
        {**missing_event, **dict(zip(event_columns, row))}
        for row in conn.execute(
            f"SELECT {', '.join(event_columns)} FROM dream_events ORDER BY turn"
        )
    ]

    return {
        "raw_chars": raw_chars,
        "distilled_chars": distilled_chars,
        "compression_pct": (
            100.0 * distilled_chars / raw_chars if raw_chars else None
        ),
        "records": len(records),
        "records_by_role": by_role,
        "median_density": (
            densities[len(densities) // 2] if densities else None
        ),
        "median_word_count": (
            sorted(words)[len(words) // 2] if words else None
        ),
        "span_inventory": inventory,
        "spans_logged": spans_total,
        "dream_events": dream_events,
        "inference_calls_total": sum(
            e["inference_calls"] for e in dream_events
        ),
    }


def evaluate_bars(
    formation: dict,
    treatment_scores: dict[str, float],
    control_scores: dict[str, float],
) -> dict:
    """The three pre-registered bars."""
    bar1 = {
        "criterion": "4 of 4 domains formed; 100% offset-verbatim; zero non-content",
        "domains_formed": formation["domains_formed"],
        "domains_required": 4,
        "unfaithful": formation["unfaithful"],
        "non_content": formation["records_non_content"],
        "pass": (
            formation["domains_formed"] == 4
            and formation["unfaithful"] == 0
            and formation["records_non_content"] == 0
        ),
    }

    q11 = treatment_scores.get("Q11", 0.0)
    q14 = treatment_scores.get("Q14", 0.0)
    bar2 = {
        "criterion": "Q11 >= 0.5 AND Q14 >= 0.5 AND Q11+Q14 >= 1.5",
        "evaluable": bar1["pass"],
        "Q11": q11,
        "Q14": q14,
        "sum": q11 + q14,
        "pass": bool(bar1["pass"] and q11 >= 0.5 and q14 >= 0.5 and q11 + q14 >= 1.5),
    }

    q1_13 = [f"Q{i}" for i in range(1, 14)]
    t_total = sum(treatment_scores.get(q, 0.0) for q in q1_13)
    c_total = sum(control_scores.get(q, 0.0) for q in q1_13)
    per_question = {
        q: {
            "treatment": treatment_scores.get(q, 0.0),
            "control": control_scores.get(q, 0.0),
            "delta": treatment_scores.get(q, 0.0) - control_scores.get(q, 0.0),
        }
        for q in q1_13
    }
    bar3 = {
        "criterion": "Q1-Q13 treatment >= same-seed control",
        "treatment_total": t_total,
        "control_total": c_total,
        "delta": t_total - c_total,
        "per_question": per_question,
        "regressions": [q for q, v in per_question.items() if v["delta"] < 0],
        "pass": t_total >= c_total,
    }

    if bar1["pass"] and bar2["pass"] and bar3["pass"]:
        verdict = "VALIDATED"
    elif bar1["pass"] and not bar2["evaluable"]:
        verdict = "BAR 1 PASS / BAR 2 NOT EVALUABLE"
    elif any([bar1["pass"], bar2["pass"], bar3["pass"]]):
        verdict = "PARTIAL"
    else:
        verdict = "NOT SUPPORTED"

    return {"bar1": bar1, "bar2": bar2, "bar3": bar3, "verdict": verdict}

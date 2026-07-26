"""Reproduce every measured figure in Study 007 Amendment 001 from committed artifacts.

Read-only. Verifies the claim that the read path renders a distilled record's
whole source episode rather than its selected span, and the consequences the
amendment draws from that.

Usage:
    PYTHONUTF8=1 uv run python scripts/verify_study_007_amendment_001.py
"""

import io
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TREATMENT = REPO / "experiments/study_006/runs/study_006_full_001/condition_c"
CONTROL = (
    REPO / "experiments/study_006/controls/whole_turn_seeded/run_001/condition_c"
)

PROBES = (120, 121)

PLANTED_TERMS = [
    "Halcyon", "847", "S460ML", "Bekova", "92.4",
    "Annunciation", "Melozzo", "della Rovere", "1483",
    "Priya Mehta", "reverse repurchase", "2.3%", "Federal Reserve", "Taylor",
    "Vampyroteuthis", "Watanabe", "marine snow", "photophore",
]

LTM_BLOCK = re.compile(r"<retrieved_ltm>.*?</retrieved_ltm>", re.S)
EPISODE_HEAD = re.compile(r'<episode turn="(\d+)" topic="([^"]+)"')

failures: list[str] = []


def check(label: str, actual, expected) -> None:
    ok = actual == expected
    print(f"  [{'OK ' if ok else 'FAIL'}] {label}: {actual!r}")
    if not ok:
        failures.append(f"{label}: expected {expected!r}, got {actual!r}")


def ltm_block(run_dir: Path, turn: int) -> str:
    path = run_dir / "constructed_prompts" / f"turn_{turn:03d}.txt"
    text = io.open(path, encoding="utf-8").read()
    match = LTM_BLOCK.search(text)
    return match.group(0) if match else ""


def main() -> int:
    print("Amendment 001 §3.1 — delivered LTM characters at the probes")
    measured = {}
    for name, run_dir in (("treatment", TREATMENT), ("control", CONTROL)):
        for turn in PROBES:
            block = ltm_block(run_dir, turn)
            heads = EPISODE_HEAD.findall(block)
            measured[(name, turn)] = {
                "chars": len(block),
                "episodes": len(heads),
                "topics": len({topic for _, topic in heads}),
                "terms": [t for t in PLANTED_TERMS if t in block],
            }

    check("treatment Q11 chars", measured[("treatment", 120)]["chars"], 13130)
    check("control   Q11 chars", measured[("control", 120)]["chars"], 21805)
    check("treatment Q14 chars", measured[("treatment", 121)]["chars"], 16027)
    check("control   Q14 chars", measured[("control", 121)]["chars"], 21875)

    ratio = (
        measured[("control", 120)]["chars"] / measured[("treatment", 120)]["chars"]
    )
    check("control:treatment Q11 ratio (2dp)", round(ratio, 2), 1.66)
    print(
        "         pre-registration claimed ~584 vs ~20,700 (ratio ~35x) "
        "-- refuted"
    )

    print("\nAmendment 001 §3.2 — topic coverage in the rendered block")
    check("treatment Q11 episodes", measured[("treatment", 120)]["episodes"], 4)
    check("treatment Q11 distinct topics", measured[("treatment", 120)]["topics"], 2)
    check("control   Q11 episodes", measured[("control", 120)]["episodes"], 5)
    check("control   Q11 distinct topics", measured[("control", 120)]["topics"], 4)

    print("\nAmendment 001 §3.3 — civil plants present in the treatment Q11 block")
    civil = ["Halcyon", "847", "S460ML", "Bekova", "92.4"]
    present = [t for t in civil if t in measured[("treatment", 120)]["terms"]]
    check("civil plants in treatment Q11 block", present, civil)
    print(
        "         the Study 006 analysis report recorded 'Halcyon' only, "
        "measured against record text rather than the prompt"
    )

    print("\nAmendment 001 §3.4 — record-to-episode collapse and per-topic counts")
    conn = sqlite3.connect(f"file:{TREATMENT / 'study.db'}?mode=ro", uri=True)
    try:
        records, episodes = conn.execute(
            "SELECT COUNT(*), COUNT(DISTINCT source_episode_id) "
            "FROM distilled_ltm WHERE status = 'content'"
        ).fetchone()
        check("distilled content records", records, 200)
        check("distinct source episodes", episodes, 69)

        per_topic = conn.execute(
            """
            SELECT COUNT(*), COUNT(DISTINCT d.source_episode_id)
            FROM distilled_ltm AS d
            LEFT JOIN episodes AS e ON e.id = d.source_episode_id
            WHERE d.status = 'content'
            GROUP BY COALESCE(e.topic_id, d.topic_id)
            ORDER BY COUNT(DISTINCT d.source_episode_id)
            """
        ).fetchall()
        check("spans per topic", [spans for spans, _ in per_topic], [50, 50, 50, 50])
        check("distinct episodes per topic", [eps for _, eps in per_topic],
              [15, 16, 18, 20])

        mean_rendered = conn.execute(
            """
            SELECT AVG(LENGTH(COALESCE(e.user_message, '')
                     || COALESCE(e.assistant_message, '')))
            FROM (SELECT DISTINCT source_episode_id AS sid
                  FROM distilled_ltm WHERE status = 'content') AS d
            JOIN episodes AS e ON e.id = d.sid
            """
        ).fetchone()[0]
        check("mean rendered chars per source episode", round(mean_rendered), 3940)

        mean_span = conn.execute(
            "SELECT AVG(LENGTH(text)) FROM distilled_ltm WHERE status = 'content'"
        ).fetchone()[0]
        check("mean stored span chars", round(mean_span), 146)
    finally:
        conn.close()

    print("\nAmendment 001 §4.2 — sweep floor derivation")
    check("4 topics x mean rendered episode chars, rounded to 1k",
          round(4 * mean_rendered / 1000) * 1000, 16000)

    print()
    if failures:
        print(f"FAILED — {len(failures)} check(s) did not reproduce:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("All Amendment 001 figures reproduce from committed artifacts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

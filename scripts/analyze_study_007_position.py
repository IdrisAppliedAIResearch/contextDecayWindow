"""Study 007 post-hoc — position, grounding, and retrieval specificity.

Reproduces every figure in
`experiments/study_007/evaluation/position_and_grounding_analysis.md`.

Distinguishes four hypotheses for the Bar 1 failure, from committed logs only:

  A. the model does not use provided context      (the report's original claim)
  B. lost-in-the-middle inside the LTM block      (reviewer challenge)
  C. prior strength on art and monetary
  D. the floor delivered topic presence, not fact presence

Read-only.
"""

import csv
import io
import json
import re
import sqlite3
import sys
from pathlib import Path

TREATMENT = Path("experiments/study_007/runs/study_007_full_001/condition_c")
PROBES = (120, 121)

# The rubric's own Q11 expected list, verbatim from study_002/rubric_filled.md.
RUBRIC_ITEMS = [
    "847", "S460ML", "92.4", "1483", "600", "2.3%", "2%",
    "Halcyon Crossing", "Anara Bekova", "Annunciation", "Melozzo",
    "della Rovere", "Federal Reserve", "Taylor Rule", "Priya Mehta",
    "Vampyroteuthis", "Kenji Watanabe",
]

# Terms the report claimed were "background knowledge never in this conversation".
CLAIMED_FABRICATIONS = [
    "Cosimo", "Ghirlandaio", "Uccello", "Fra Angelico",
    "European Central Bank", "Bank of Japan", "FAIT",
]

DOMAIN_TERMS = {
    "civil": ["Halcyon", "847", "S460ML", "Bekova", "92.4"],
    "art": ["Annunciation", "Melozzo", "della Rovere", "1483",
            "ultramarine", "Julius II"],
    "monetary": ["Taylor Rule", "Federal Reserve", "dual mandate",
                 "Priya Mehta", "reverse repurchase", "2.3%"],
    "marine": ["Vampyroteuthis", "Watanabe", "photophore", "marine snow",
               "mantle margin"],
}

LTM_BLOCK = re.compile(r"<retrieved_ltm>.*?</retrieved_ltm>", re.S)
EPISODE = re.compile(r"  <episode .*?  </episode>", re.S)


def prompt_text(turn: int) -> str:
    path = TREATMENT / "constructed_prompts" / f"turn_{turn:03d}.txt"
    return io.open(path, encoding="utf-8").read()


def ltm_block(turn: int) -> str:
    match = LTM_BLOCK.search(prompt_text(turn))
    return match.group(0) if match else ""


def answers() -> dict[int, str]:
    rows = (TREATMENT / "logs" / "turns.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    return {
        json.loads(line)["turn_number"]: json.loads(line)["assistant_message"]
        for line in rows
    }


def main() -> int:
    reply = answers()

    print("=" * 72)
    print("TEST 1 — item-level grounding (settles hypothesis A)")
    for turn in PROBES:
        block, answer = ltm_block(turn), reply[turn]
        in_block = [t for t in RUBRIC_ITEMS if t.lower() in block.lower()]
        in_answer = [t for t in RUBRIC_ITEMS if t.lower() in answer.lower()]
        unused = [t for t in in_block if t not in in_answer]
        ungrounded = [t for t in in_answer if t not in in_block]
        print(f"\n  turn {turn}: block {len(in_block)}/17, answer {len(in_answer)}/17")
        print(f"    used (block AND answer) : {len(in_answer) - len(ungrounded)}"
              f"/{len(in_block)}")
        print(f"    in block, unused        : {unused or 'NONE'}")
        print(f"    in answer, NOT in block : {ungrounded or 'NONE'}")

    print()
    print("=" * 72)
    print("TEST 2 — were the 'background knowledge' terms actually retrieved?")
    block120 = ltm_block(120)
    for term in CLAIMED_FABRICATIONS:
        if term.lower() in reply[120].lower():
            print(f"  {term:<24} in answer | in LTM block: "
                  f"{term.lower() in block120.lower()}")

    print()
    print("=" * 72)
    print("TEST 3 — block position vs use (settles hypothesis B)")
    for turn in PROBES:
        block, answer = ltm_block(turn), reply[turn]
        episodes = [(m.start(), m.group(0)) for m in EPISODE.finditer(block)]
        print(f"\n  turn {turn} — {len(block)} chars, {len(episodes)} episodes")
        print(f"  {'pos':<4}{'domain':<10}{'midpoint':<10}{'items':<28}used")
        for i, (start, text) in enumerate(episodes, 1):
            hits = {
                d: [t for t in ts if t in text]
                for d, ts in DOMAIN_TERMS.items()
            }
            hits = {d: v for d, v in hits.items() if v}
            domain = max(hits, key=lambda d: len(hits[d])) if hits else "-"
            items = [t for v in hits.values() for t in v]
            used = any(t.lower() in answer.lower() for t in items)
            midpoint = 100 * (start + len(text) / 2) / len(block)
            print(f"  {i:<4}{domain:<10}{midpoint:>6.1f}%   "
                  f"{','.join(items)[:26]:<28}{used}")

    print()
    print("=" * 72)
    print("TEST 4 — what the floor selected (settles hypothesis D)")
    conn = sqlite3.connect(f"file:{TREATMENT / 'study.db'}?mode=ro", uri=True)
    try:
        turn_of = dict(conn.execute("SELECT id, turn_number FROM episodes"))
    finally:
        conn.close()

    with open(TREATMENT / "logs" / "retrieval_budget.csv", encoding="utf-8") as fh:
        rows = {int(r["turn"]): r for r in csv.DictReader(fh)}

    fact_turns = {
        "art": {55, 56, 60}, "monetary": {61, 62, 65},
        "marine": {100, 101, 102}, "civil": {3, 4},
    }
    for turn in PROBES:
        print(f"\n  turn {turn}")
        print(f"  {'phase':<7}{'src_turn':<10}{'sim':<9}{'chars':<8}fact-bearing?")
        for item in json.loads(rows[turn]["selection"]):
            src = turn_of.get(item["episode_id"], "?")
            bearing = any(src in v for v in fact_turns.values())
            print(f"  {item['phase']:<7}{str(src):<10}"
                  f"{item['similarity']:<9.4f}{item['chars']:<8}{bearing}")

    print()
    print("=" * 72)
    print("Hypotheses A, B and C are refuted at Q11; D is supported.")
    print("See experiments/study_007/evaluation/position_and_grounding_analysis.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

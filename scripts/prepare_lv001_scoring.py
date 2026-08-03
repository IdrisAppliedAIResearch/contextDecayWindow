"""LV-001 scoring preparation: extract probe answers and blind the arms.

`AGENTS.md` §4: every arm's scores are committed before anyone opens mechanism
logs, and git order is the evidence. This script produces the blinded surface a
rater sees and seals the mapping, so the mapping cannot be consulted before the
scores exist.

Two layers are produced, because LV-001 §5's surrogate audit requires both:

  * a **mechanical** layer — does the required term appear at all — which is
    automatable and reported as-is;
  * a **judgement** surface for attribution, because an item restated inside an
    otherwise wrong answer must score zero, and presence alone cannot see that.

    python scripts/prepare_lv001_scoring.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "experiments/components/live_validation/runs/full_121"
SCORING = REPO / "experiments/components/live_validation/scoring"
LEDGER = REPO / "experiments/components/retrieval_mechanism_ledger/artifacts"

BREADTH_TURN = 120
# Locked rubric, experiments/study_002/rubric_filled.md.
TARGETED = {
    112: ("Q1", ["847", "S460ML"]),
    113: ("Q2", ["Anara Bekova", "92.4"]),
    114: ("Q3", ["numbered list", "Risk"]),
    115: ("Q4", ["Annunciation of Forli", "Melozzo da Forli",
                 "Giuliano della Rovere", "1483"]),
    116: ("Q5", ["lead white", "ultramarine"]),
    117: ("Q6", ["Giuliano della Rovere", "Julius II"]),
    118: ("Q7", ["Vampyroteuthis infernalis", "Kenji Watanabe", "600",
                 "marine snow"]),
    119: ("Q8", ["photophore", "mantle margin"]),
}
# Seeded so the blinding is reproducible from the record, not from memory.
BLIND_SEED = 5005


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).casefold()
    text = "".join(c for c in text if not unicodedata.combining(c))
    for dash in "–—−":
        text = text.replace(dash, "-")
    return re.sub(r"\s+", " ", text)


def load_arm(arm: str) -> dict[int, str]:
    path = RUNS / f"l_{arm}" / "turns.jsonl"
    answers = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            answers[row["turn_number"]] = row["assistant_message"]
    return answers


def q11_items() -> list[dict]:
    with (LEDGER / "e005/q11_item_matrix.csv").open(encoding="utf-8-sig",
                                                    newline="") as handle:
        return list(csv.DictReader(handle))


def mechanical(answer: str, terms: list[str]) -> list[dict]:
    folded = fold(answer)
    return [{"term": t, "present": fold(t) in folded} for t in terms]


def main() -> int:
    for arm in ("a0", "a3"):
        if not (RUNS / f"l_{arm}" / "turns.jsonl").exists():
            print(f"missing run for {arm}; nothing to prepare")
            return 1

    SCORING.mkdir(parents=True, exist_ok=True)
    arms = {arm: load_arm(arm) for arm in ("a0", "a3")}

    labels = ["A", "B"]
    random.Random(BLIND_SEED).shuffle(labels)
    mapping = {labels[0]: "a0", labels[1]: "a3"}

    surface = {}
    for label, arm in mapping.items():
        answers = arms[arm]
        entry = {"label": label, "probes": {}}
        for turn, (question, terms) in sorted(TARGETED.items()):
            entry["probes"][question] = {
                "turn": turn,
                "answer": answers.get(turn, ""),
                "mechanical": mechanical(answers.get(turn, ""), terms),
            }
        entry["probes"]["Q11"] = {
            "turn": BREADTH_TURN,
            "answer": answers.get(BREADTH_TURN, ""),
            "mechanical": [
                {"domain": row["domain"], "item": row["item"],
                 "present": fold(row["item"]) in fold(answers.get(BREADTH_TURN, ""))}
                for row in q11_items()
            ],
        }
        surface[label] = entry

    (SCORING / "blinded_surface.json").write_text(
        json.dumps(surface, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    sealed = json.dumps(mapping, sort_keys=True)
    (SCORING / "blind_mapping.sealed.json").write_text(
        json.dumps({
            "note": "Do not open until scores are committed. AGENTS.md §4: git "
                    "order is the evidence.",
            "seed": BLIND_SEED,
            "mapping_sha256": hashlib.sha256(sealed.encode()).hexdigest(),
            "mapping": mapping,
        }, indent=2) + "\n", encoding="utf-8")

    for label in sorted(surface):
        q11 = surface[label]["probes"]["Q11"]["mechanical"]
        hits = sum(1 for m in q11 if m["present"])
        print(f"arm {label}: Q11 mechanical presence {hits}/17")
        for question in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"):
            mech = surface[label]["probes"][question]["mechanical"]
            got = sum(1 for m in mech if m["present"])
            print(f"    {question}: {got}/{len(mech)} terms present")

    print("\nMechanical layer only. Attribution correctness is judged next, "
          "against the blinded surface, before the mapping is opened.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

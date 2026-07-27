from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "experiments" / "audits" / "scoring_integrity"
LAYER1 = AUDIT / "layer1"
OUT = AUDIT / "layer2"


QUESTIONS_S1 = {
    "Q1": ("What is the exact budget cap for Meridian?", "1.0 for $47,500; 0.5 for an approximation around $47k; otherwise 0."),
    "Q2": ("What is Meridian's API performance target?", "1.0 for 180ms plus 95th percentile; 0.5 for 180ms alone; otherwise 0."),
    "Q3": ("What was the exact CRISPR dosage?", "1.0 for 2.5 mg/kg; 0.5 for approximately 2-3 mg/kg; otherwise 0."),
    "Q4": ("Who leads Meridian and what is its deadline?", "1.0 for Dr. Priya Nair and October 14; 0.5 for one; otherwise 0."),
    "Q5": ("What CRISPR cell line and expression rate were used?", "1.0 for HEK-293T and 73%; 0.5 for one; otherwise 0."),
    "Q6": ("What was Meridian's response-time target after the CRISPR discussion?", "1.0 for clean 180ms retrieval; 0 if CRISPR content contaminates the response."),
    "Q7": ("Which researcher conducted the CRISPR study?", "1.0 for Dr. Yuki Tanaka without conflation; otherwise 0."),
    "Q8": ("List all numerical values across both topics.", "1.0 only if all six locked values are present and correctly attributed; otherwise 0."),
    "Q9": ("State the two formatting rules.", "1.0 for numbered lists plus confidence levels on technical recommendations; otherwise 0."),
    "Q10": ("Were both formatting rules followed in turns 25-32?", "1.0 if both appear in at least 6 of 8 turns; otherwise 0."),
}

QUESTIONS = {
    "Q1": ("What is Halcyon Crossing's main span and steel grade?", "1.0 for 847 meters and S460ML; 0.5 for one; otherwise 0."),
    "Q2": ("Who is the lead engineer and what is the maximum load rating?", "1.0 for Dr. Anara Bekova and 92.4 metric tons per axle; 0.5 for one; otherwise 0."),
    "Q3": ("State both behavioral rules.", "1.0 for numbered lists for specifications and risk classification for engineering recommendations; 0.5 for one; otherwise 0."),
    "Q4": ("Name the painting, artist, patron, and completion year.", "1.0 for all four; 0.5 for two or three; otherwise 0."),
    "Q5": ("Name the pigment ground and glaze.", "1.0 for lead white ground and ultramarine glaze; 0.5 for one; otherwise 0."),
    "Q6": ("State Cardinal Giuliano della Rovere's role and significance.", "1.0 for patron plus later Pope Julius II with no monetary/marine contamination; otherwise 0."),
    "Q7": ("Name the organism, researcher, depth range, and feeding behavior.", "1.0 for all four locked facts; 0.5 for two or three; otherwise 0."),
    "Q8": ("Name the bioluminescent organ and its location.", "1.0 for photophores along the mantle margin; 0.5 for one; otherwise 0."),
    "Q9": ("Did the Renaissance retrieval avoid monetary/marine bleed?", "1.0 for clean Renaissance retrieval; otherwise 0."),
    "Q10": ("Was Dr. Kenji Watanabe correctly attributed to Vampyroteuthis?", "1.0 for correct attribution without researcher conflation; otherwise 0."),
    "Q11": ("List all locked values and entities across all four topics.", "Binary: 1.0 for at least 14 of 17 correctly attributed atomic items with no significant cross-attribution; otherwise 0. No 0.5."),
    "Q12": ("State both behavioral rules.", "1.0 only if both are correct; otherwise 0."),
    "Q13": ("Were applicable rules honored across turns 112-120?", "1.0 if applicable rules were honored in at least 5 of 9 turns; otherwise 0. Risk rule may be N/A."),
    "Q14": ("Give one planted specific for each of the four subject areas.", "1.0 for four domain hits; 0.5 if all four are named and exactly one lacks/carries a wrong specific; otherwise 0. Denying a domain was discussed is 0."),
}


def digest(seed: str, item_id: str) -> str:
    return hashlib.sha256(f"{seed}:{item_id}".encode()).hexdigest()


def load_rows() -> list[dict]:
    return [
        json.loads(line)
        for line in (LAYER1 / "items.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def main() -> None:
    rows = load_rows()
    seeds = json.loads((AUDIT / "seeds.json").read_text(encoding="utf-8"))
    flagged = {row["item_id"] for row in rows if row["flags"]}
    breadth = {
        row["item_id"] for row in rows
        if row["study"] > 1 and row["question"] in {"Q11", "Q14"}
    }
    eligible = [
        row for row in rows
        if row["item_id"] not in flagged and row["item_id"] not in breadth
    ]
    eligible.sort(key=lambda row: digest(seeds["control_sample_seed"], row["item_id"]))
    control_count = math.ceil(seeds["control_sample_rate"] * len(eligible))
    control = {row["item_id"] for row in eligible[:control_count]}
    selected = [
        row for row in rows
        if row["item_id"] in flagged | breadth | control
    ]
    selected.sort(key=lambda row: row["item_id"])
    seal = (AUDIT / ".seal_key").read_text(encoding="ascii").strip()
    packets = []
    commitments = []
    for index, row in enumerate(selected, start=1):
        anon_id = f"SIA-{index:03d}"
        question, criterion = (QUESTIONS_S1 if row["study"] == 1 else QUESTIONS)[row["question"]]
        packets.append({
            "anon_id": anon_id,
            "question": question,
            "criterion": criterion,
            "guidance": "Only content outside reasoning blocks is scoreable. The supplied answer is already reduced to that surface. Give primary score, strict score if hedge/alternatives affect credit, and an answer-grounded rationale.",
            "answer": row["scoreable_answer"],
        })
        commitments.append({
            "anon_id": anon_id,
            "item_hmac": hashlib.sha256(f"{seal}:{row['item_id']}".encode()).hexdigest(),
        })
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "blind_corpus.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for packet in packets:
            fh.write(json.dumps(packet, ensure_ascii=False) + "\n")
    (OUT / "sealed_mapping_commitments.json").write_text(
        json.dumps({"algorithm": "SHA-256(secret:item_id)", "entries": commitments}, indent=2) + "\n",
        encoding="utf-8",
    )
    selection = {
        "total_items": len(rows),
        "flagged_items": len(flagged),
        "breadth_items": len(breadth),
        "eligible_unflagged_non_breadth": len(eligible),
        "control_items": len(control),
        "selected_unique": len(selected),
        "control_seed": seeds["control_sample_seed"],
        "control_rate": seeds["control_sample_rate"],
        "blind_corpus_sha256": hashlib.sha256((OUT / "blind_corpus.jsonl").read_bytes()).hexdigest(),
    }
    (OUT / "selection_summary.json").write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()


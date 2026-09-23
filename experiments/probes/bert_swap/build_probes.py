"""Measurement-side builder for BERT-SWAP Stage 0.

Reads Study 005 q_facts_key.md (measurement-only source) and emits probes.json.
Mechanism code never reads the key; it may consume probes.json only in scoring.
Cloze texts are authored here, faithful to the planted turn wording.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "probes.json"

# (fact_id, source_turn, pre, post, gold, distractors)
CLOZES = [
    ("civil_span", 3,
     "The main span of Halcyon Crossing measures ", " meters.",
     "847", ["92.4", "600", "1483"]),
    ("civil_engineer", 3,
     "The lead structural engineer assigned to Halcyon Crossing is Dr. ", ".",
     "Anara Bekova", ["Priya Mehta", "Kenji Watanabe", "Elena Fischer"]),
    ("civil_steel", 4,
     "The steel specification for Halcyon Crossing's primary structural members is grade ", ".",
     "S460ML", ["S355", "A36", "S960"]),
    ("civil_load", 4,
     "The bridge's maximum load rating is ", " metric tons per axle.",
     "92.4", ["600", "2.3", "847"]),
    ("art_identity", 55,
     "The Annunciation of Forl\u00ec was completed in ", " by Melozzo da Forl\u00ec.",
     "1483", ["1993", "1500", "1603"]),
    ("art_pigment", 56,
     "In The Annunciation of Forl\u00ec, Melozzo da Forl\u00ec applied layers of ",
     " glaze over a lead white ground.",
     "ultramarine", ["vermilion", "azurite", "cobalt"]),
    ("art_patron_role", 60,
     "Cardinal Giuliano della Rovere later became Pope ", ".",
     "Julius II", ["Leo X", "Paul III", "Urban VI"]),
    ("monetary_taylor", 61,
     "The Taylor Rule was originally formulated in the year ", ".",
     "1993", ["1483", "1913", "2003"]),
    ("monetary_fed", 62,
     "The Federal Reserve operates under a ",
     " mandate of maximum employment and stable prices.",
     "dual", ["single", "triple", "narrow"]),
    ("monetary_threshold", 65,
     "Dr. Priya Mehta argues that an inflation threshold of ",
     " percent better captures the Fed's revealed preference than the stated target.",
     "2.3", ["3.5", "1.5", "4.2"]),
    ("marine_identity", 100,
     "Dr. Kenji Watanabe's group studies Vampyroteuthis infernalis at depths of 600 to ",
     " meters.",
     "900", ["300", "3000", "1200"]),
    ("marine_photophores", 101,
     "The photophores of Vampyroteuthis infernalis are distributed along its ",
     " margin.",
     "mantle", ["fin", "dorsal", "ventral"]),
    ("marine_feeding", 102,
     "Vampyroteuthis infernalis feeds primarily through the aggregation of ",
     " snow particles.",
     "marine", ["volcanic", "glacial", "mineral"]),
]

# Never-planted controls: expected flat chance (~25%) under any mechanism.
CONTROLS = [
    ("ctrl_kelso", 999,
     "The city of Kelso Harbor records a population of ",
     " residents in the latest census.",
     "11230", ["8450", "6030", "9210"]),
    ("ctrl_lindqvist", 999,
     "Professor Yara Lindqvist's institute was founded in ", ".",
     "1917", ["1983", "1901", "2017"]),
    ("ctrl_nordvind", 999,
     "The ferry Nordvind crosses the fjord in ", " minutes.",
     "47", ["23", "68", "115"]),
]

# Deterministic gold placement (avoids positional bias without RNG drift):
# slot = source_turn % 4 for clozes; fixed cycle for controls.
def build():
    probes = []
    for i, (fid, src, pre, post, gold, dis) in enumerate(CLOZES + CONTROLS):
        choices = [gold] + list(dis)
        slot = src % 4 if src != 999 else i % 4
        choices[0], choices[slot] = choices[slot], choices[0]
        probes.append({
            "fact_id": fid, "source_turn": src, "pre": pre, "post": post,
            "choices": choices, "gold_idx": slot,
            "kind": "control" if src == 999 else "planted",
        })
    queries = [
        {"turn": 112, "gold": [3, 4]},
        {"turn": 113, "gold": [3, 4]},
        {"turn": 115, "gold": [55, 60]},
        {"turn": 116, "gold": [56]},
        {"turn": 117, "gold": [55, 60]},
        {"turn": 118, "gold": [100, 102]},
        {"turn": 119, "gold": [101]},
    ]
    out = {"spec": "bert_swap_stage0", "probes": probes, "queries": queries,
           "key_sha256": "C1B5C9C484C1BD82A13D7B1599BFEBC78A3200FDBD684A35DBA4D3BB4731ECA7"}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT, "probes:", len(probes), "queries:", len(queries))

if __name__ == "__main__":
    build()

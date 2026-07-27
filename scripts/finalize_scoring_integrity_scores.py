from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "experiments" / "audits" / "scoring_integrity"
L1 = AUDIT / "layer1"
L2 = AUDIT / "layer2"
OUT = AUDIT / "corrected_scores"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main() -> None:
    items = load_jsonl(L1 / "items.jsonl")
    consensus = {row["item_id"]: row for row in load_jsonl(L2 / "consensus_and_triggers.jsonl")}
    mapping = {
        row["anon_id"]: row["item_id"]
        for row in json.loads((L2 / "unsealed_mapping.json").read_text(encoding="utf-8"))["entries"]
    }
    independent = {
        mapping[row["anon_id"]]: row
        for row in load_jsonl(L2 / "independent_adjudication.jsonl")
    }
    conflict = {
        mapping[row["anon_id"]]: row
        for row in load_jsonl(L2 / "conflict_adjudication.jsonl")
    }
    pass_rows = {
        number: {mapping[row["anon_id"]]: row for row in load_jsonl(L2 / f"pass_{number}.jsonl")}
        for number in (1, 2, 3)
    }
    ledger = []
    for item in items:
        item_id = item["item_id"]
        original = float(item["original_score"])
        if item_id in independent:
            corrected = float(independent[item_id]["primary"])
            strict = float(independent[item_id]["strict"])
            basis = "independent_adjudicator"
            rationale = independent[item_id]["rationale"]
        elif item_id in conflict:
            corrected = float(conflict[item_id]["primary"])
            strict = float(conflict[item_id]["strict"])
            basis = "conflict_adjudicator"
            rationale = conflict[item_id]["rationale"]
        elif item_id in consensus:
            corrected = float(consensus[item_id]["primary_consensus"])
            strict = float(consensus[item_id]["strict_consensus"])
            basis = "ai_consensus"
            rationale = "Three-pass blind consensus; see pass files."
        else:
            corrected = original
            strict = original
            basis = "original_unselected"
            rationale = item["rationale"]
        ledger.append({
            "item_id": item_id,
            "study": item["study"],
            "arm_id": item["arm_id"],
            "arm": item["arm"],
            "question": item["question"],
            "original": original,
            "corrected": corrected,
            "strict": strict,
            "delta": corrected - original,
            "basis": basis,
            "rationale": rationale,
            "layer1_flags": item["flags"],
            "triggers": consensus.get(item_id, {}).get("triggers", []),
        })
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "corrected_score_ledger.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for row in ledger:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (OUT / "corrected_score_ledger.csv").open("w", encoding="utf-8", newline="") as fh:
        fields = ["item_id", "study", "arm_id", "arm", "question", "original", "corrected", "strict", "delta", "basis", "layer1_flags", "triggers"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in ledger:
            flat = {key: row[key] for key in fields}
            flat["layer1_flags"] = ";".join(row["layer1_flags"])
            flat["triggers"] = ";".join(row["triggers"])
            writer.writerow(flat)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in ledger:
        grouped[row["arm_id"]].append(row)
    totals = []
    for arm_id, rows in sorted(grouped.items()):
        q1_q13 = [row for row in rows if int(row["question"][1:]) <= 13]
        q14 = next((row for row in rows if row["question"] == "Q14"), None)
        by_q = {row["question"]: row for row in rows}
        if rows[0]["study"] == 1:
            categories = {
                "cat1_2": sum(by_q[f"Q{i}"]["corrected"] for i in range(1, 6)),
                "cat3": sum(by_q[f"Q{i}"]["corrected"] for i in range(6, 9)),
                "cat4": sum(by_q[f"Q{i}"]["corrected"] for i in range(9, 11)),
            }
        else:
            categories = {
                "cat1": sum(by_q[f"Q{i}"]["corrected"] for i in range(1, 4)),
                "cat2": sum(by_q[f"Q{i}"]["corrected"] for i in range(4, 7)),
                "cat3": sum(by_q[f"Q{i}"]["corrected"] for i in range(7, 9)),
                "cat4": sum(by_q[f"Q{i}"]["corrected"] for i in range(9, 12)),
                "cat5": sum(by_q[f"Q{i}"]["corrected"] for i in range(12, 14)),
            }
        totals.append({
            "study": rows[0]["study"],
            "arm_id": arm_id,
            "arm": rows[0]["arm"],
            "original_q1_q13": sum(row["original"] for row in q1_q13),
            "corrected_q1_q13": sum(row["corrected"] for row in q1_q13),
            "strict_q1_q13": sum(row["strict"] for row in q1_q13),
            "original_q14": q14["original"] if q14 else None,
            "corrected_q14": q14["corrected"] if q14 else None,
            "changed_items": sum(not math.isclose(row["original"], row["corrected"]) for row in rows),
            "corrected_categories": categories,
        })
    (OUT / "arm_totals.json").write_text(json.dumps(totals, indent=2) + "\n", encoding="utf-8")
    arms_dir = OUT / "arms"
    arms_dir.mkdir(exist_ok=True)
    for arm_id, rows in grouped.items():
        payload = {
            "arm_id": arm_id,
            "study": rows[0]["study"],
            "arm": rows[0]["arm"],
            "provenance": "Scoring Integrity Audit; originals preserved unchanged",
            "items": {
                row["question"]: {
                    "original": row["original"],
                    "corrected": row["corrected"],
                    "strict": row["strict"],
                    "basis": row["basis"],
                    "rationale": row["rationale"],
                }
                for row in rows
            },
        }
        (arms_dir / f"{arm_id}_corrected.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    seeds = json.loads((AUDIT / "seeds.json").read_text(encoding="utf-8"))
    flagged = {row["item_id"] for row in items if row["flags"]}
    breadth = {row["item_id"] for row in items if row["study"] > 1 and row["question"] in {"Q11", "Q14"}}
    eligible = [row for row in items if row["item_id"] not in flagged | breadth]
    eligible.sort(key=lambda row: hashlib.sha256(f"{seeds['control_sample_seed']}:{row['item_id']}".encode()).hexdigest())
    control = {row["item_id"] for row in eligible[:math.ceil(seeds["control_sample_rate"] * len(eligible))]}
    flagged_scored = [consensus[item_id] for item_id in flagged if item_id in consensus]
    control_scored = [consensus[item_id] for item_id in control if item_id in consensus]
    flagged_disagree = sum(abs(row["primary_consensus"] - row["original"]) >= 0.5 for row in flagged_scored)
    control_disagree = sum(abs(row["primary_consensus"] - row["original"]) >= 0.5 for row in control_scored)
    h5 = [row for row in consensus.values() if "H5" in row["triggers"]]
    h5_disagree = sum(
        not math.isclose(independent[row["item_id"]]["primary"], row["original"])
        for row in h5
    )
    reliability = {
        "ai_self_consistency_rate": sum(row["self_consistent"] for row in consensus.values()) / len(consensus),
        "flagged_disagreement_rate": flagged_disagree / len(flagged_scored),
        "control_disagreement_rate": control_disagree / len(control_scored),
        "escalation_threshold": (flagged_disagree / len(flagged_scored)) / 2,
        "full_rescore_escalation_fired": (control_disagree / len(control_scored)) >= (flagged_disagree / len(flagged_scored)) / 2,
        "h5_items": len(h5),
        "h5_disagreements": h5_disagree,
        "h5_disagreement_rate": h5_disagree / len(h5) if h5 else 0,
        "basis_counts": {
            basis: sum(row["basis"] == basis for row in ledger)
            for basis in ["independent_adjudicator", "conflict_adjudicator", "ai_consensus", "original_unselected"]
        },
        "changed_items": sum(not math.isclose(row["original"], row["corrected"]) for row in ledger),
    }
    (OUT / "reliability.json").write_text(json.dumps(reliability, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

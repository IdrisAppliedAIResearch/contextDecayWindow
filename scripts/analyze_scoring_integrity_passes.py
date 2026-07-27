from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from statistics import median

from prepare_scoring_integrity_layer2 import AUDIT, LAYER1, OUT, digest, load_rows


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


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
    control = {
        row["item_id"]
        for row in eligible[:math.ceil(seeds["control_sample_rate"] * len(eligible))]
    }
    selected = [row for row in rows if row["item_id"] in flagged | breadth | control]
    selected.sort(key=lambda row: row["item_id"])
    seal = (AUDIT / ".seal_key").read_text(encoding="ascii").strip()
    commitments = json.loads((OUT / "sealed_mapping_commitments.json").read_text(encoding="utf-8"))["entries"]
    mapping = []
    by_anon = {}
    for index, row in enumerate(selected, start=1):
        anon_id = f"SIA-{index:03d}"
        expected = hashlib.sha256(f"{seal}:{row['item_id']}".encode()).hexdigest()
        assert commitments[index - 1] == {"anon_id": anon_id, "item_hmac": expected}
        entry = {"anon_id": anon_id, "item_id": row["item_id"], "arm_id": row["arm_id"], "question": row["question"]}
        mapping.append(entry)
        by_anon[anon_id] = row
    (OUT / "unsealed_mapping.json").write_text(
        json.dumps({"seal_commitment_verified": True, "entries": mapping}, indent=2) + "\n",
        encoding="utf-8",
    )
    passes = {}
    for number in (1, 2, 3):
        passes[number] = {
            row["anon_id"]: row for row in load_jsonl(OUT / f"pass_{number}.jsonl")
        }
    consensus_rows = []
    for entry in mapping:
        anon_id = entry["anon_id"]
        source = by_anon[anon_id]
        values = [float(passes[n][anon_id]["primary"]) for n in (1, 2, 3)]
        strict_values = [float(passes[n][anon_id]["strict"]) for n in (1, 2, 3)]
        primary = float(median(values))
        strict = float(median(strict_values))
        self_consistent = len(set(values)) == 1 and len(set(strict_values)) == 1
        triggers = []
        if (
            (source["no_answer"] or source["truncated"]) and primary > 0
            or ("F4" in source["flags"] and not math.isclose(primary, float(source["original_score"])))
        ):
            triggers.append("H1")
        if not self_consistent:
            triggers.append("H2")
        if abs(primary - float(source["original_score"])) >= 0.5:
            triggers.append("H3")
        if source["study"] > 1 and source["question"] in {"Q11", "Q14"}:
            triggers.append("H4")
        consensus_rows.append({
            "anon_id": anon_id,
            "item_id": source["item_id"],
            "study": source["study"],
            "arm": source["arm"],
            "question": source["question"],
            "original": source["original_score"],
            "pass_1": values[0],
            "pass_2": values[1],
            "pass_3": values[2],
            "primary_consensus": primary,
            "strict_consensus": strict,
            "self_consistent": self_consistent,
            "layer1_flags": source["flags"],
            "triggers": triggers,
        })
    h5_eligible = [
        row for row in consensus_rows
        if row["self_consistent"]
        and math.isclose(row["primary_consensus"], float(row["original"]))
        and not row["triggers"]
    ]
    h5_eligible.sort(key=lambda row: digest(seeds["h5_sample_seed"], row["item_id"]))
    h5_count = math.ceil(seeds["h5_sample_rate"] * len(h5_eligible))
    for row in h5_eligible[:h5_count]:
        row["triggers"].append("H5")
    with (OUT / "consensus_and_triggers.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for row in consensus_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    packet_by_id = {row["anon_id"]: row for row in load_jsonl(OUT / "blind_corpus.jsonl")}
    independent_ids = {
        row["anon_id"] for row in consensus_rows
        if "H4" in row["triggers"] or "H5" in row["triggers"]
    }
    with (OUT / "independent_adjudication_packet.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for anon_id in sorted(independent_ids):
            packet = dict(packet_by_id[anon_id])
            packet["trigger_class"] = "H4/H5 independent-before-reveal"
            fh.write(json.dumps(packet, ensure_ascii=False) + "\n")
    summary = {
        "selected": len(consensus_rows),
        "self_consistent": sum(row["self_consistent"] for row in consensus_rows),
        "self_consistency_rate": sum(row["self_consistent"] for row in consensus_rows) / len(consensus_rows),
        "trigger_counts": {
            trigger: sum(trigger in row["triggers"] for row in consensus_rows)
            for trigger in ["H1", "H2", "H3", "H4", "H5"]
        },
        "triggered_unique": sum(bool(row["triggers"]) for row in consensus_rows),
        "independent_packet_items": len(independent_ids),
        "h5_eligible": len(h5_eligible),
        "h5_selected": h5_count,
    }
    (OUT / "trigger_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()


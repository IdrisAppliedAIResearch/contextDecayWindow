from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "experiments" / "audits" / "scoring_integrity"
L1 = AUDIT / "layer1"
L2 = AUDIT / "layer2"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main() -> None:
    consensus = load_jsonl(L2 / "consensus_and_triggers.jsonl")
    independent = {
        row["anon_id"] for row in load_jsonl(L2 / "independent_adjudication.jsonl")
    }
    blind = {row["anon_id"]: row for row in load_jsonl(L2 / "blind_corpus.jsonl")}
    layer1 = {row["item_id"]: row for row in load_jsonl(L1 / "items.jsonl")}
    passes = {
        number: {row["anon_id"]: row for row in load_jsonl(L2 / f"pass_{number}.jsonl")}
        for number in (1, 2, 3)
    }
    packet = []
    for row in consensus:
        conflict_triggers = sorted(set(row["triggers"]) & {"H1", "H2", "H3"})
        if not conflict_triggers or row["anon_id"] in independent:
            continue
        evidence = layer1[row["item_id"]]
        packet.append({
            "anon_id": row["anon_id"],
            "question": blind[row["anon_id"]]["question"],
            "criterion": blind[row["anon_id"]]["criterion"],
            "answer": blind[row["anon_id"]]["answer"],
            "conflict_triggers": conflict_triggers,
            "original_score": row["original"],
            "ai_passes": [
                {
                    "primary": passes[number][row["anon_id"]]["primary"],
                    "strict": passes[number][row["anon_id"]]["strict"],
                    "rationale": passes[number][row["anon_id"]]["rationale"],
                }
                for number in (1, 2, 3)
            ],
            "ai_consensus": row["primary_consensus"],
            "self_consistent": row["self_consistent"],
            "mechanical": {
                "no_answer": evidence["no_answer"],
                "truncated": evidence["truncated"],
                "unclosed_reasoning": evidence["unclosed_reasoning"],
                "facts_found": evidence["facts_found"],
                "facts_total": evidence["facts_total"],
                "fact_presence": evidence["fact_presence"],
                "flags": evidence["flags"],
            },
            "instruction": "Adjudicate the score under the criterion. Mechanical string evidence is conservative and may miss correct paraphrases; completeness classifications are decisive under the protocol.",
        })
    with (L2 / "conflict_adjudication_packet.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for row in packet:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    (L2 / "conflict_adjudication_summary.json").write_text(
        json.dumps({"items": len(packet)}, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()


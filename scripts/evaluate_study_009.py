"""Evaluate Study 009 after the blinded score commit and mapping unseal."""

import csv
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path("experiments/study_009")
OUT = ROOT / "evaluation"
ARM_PROMPTS = {
    "L": Path(
        "experiments/study_007/runs/study_007_full_001/condition_c/"
        "constructed_prompts"
    ),
    "S": ROOT / "runs/study_009_full_001/arm_s/constructed_prompts",
}
ANONYMOUS_RESPONSES = {
    "arm_A": OUT / "arm_A/responses.md",
    "arm_B": OUT / "arm_B/responses.md",
}
PROBES = {"Q11": 120, "Q14": 121}
ITEMS = [
    ("civil", "Halcyon Crossing", "halcyon crossing"),
    ("civil", "847", "847"),
    ("civil", "Dr. Anara Bekova", "anara bekova"),
    ("civil", "S460ML", "s460ml"),
    ("civil", "92.4", "92.4"),
    ("art", "The Annunciation of Forli", "annunciation of forli"),
    ("art", "Melozzo da Forli", "melozzo da forli"),
    (
        "art",
        "Cardinal Giuliano della Rovere",
        "giuliano della rovere",
    ),
    ("art", "1483", "1483"),
    ("monetary", "Taylor Rule", "taylor rule"),
    ("monetary", "Federal Reserve", "federal reserve"),
    ("monetary", "Dr. Priya Mehta", "priya mehta"),
    ("monetary", "2.3%", "2.3%"),
    (
        "marine",
        "Vampyroteuthis infernalis",
        "vampyroteuthis infernalis",
    ),
    ("marine", "Dr. Kenji Watanabe", "kenji watanabe"),
    ("marine", "600", "600"),
    ("marine", "marine snow", "marine snow"),
]
TURN_HEADER = re.compile(r"^## Turn (\d+)[^\n]*\n(.*?)(?=^## Turn |\Z)", re.M | re.S)


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def answer_blocks(path: Path) -> dict[int, str]:
    """Extract assistant-only text from an anonymized response file."""
    blocks = {}
    for turn_text, body in TURN_HEADER.findall(path.read_text(encoding="utf-8")):
        marker = "**Assistant response:**"
        if marker not in body:
            marker = "**Assistant:**"
        if marker not in body:
            raise ValueError(f"assistant marker missing at turn {turn_text} in {path}")
        answer = body.split(marker, 1)[1]
        answer = answer.split("**Score:**", 1)[0]
        answer = answer.split("\n---", 1)[0]
        blocks[int(turn_text)] = answer.strip()
    return blocks


def source_to_architecture(mapping_value: str) -> str:
    if mapping_value == "arm_l_study_007_accepted":
        return "L"
    if mapping_value == "arm_s_study_009":
        return "S"
    raise ValueError(f"unknown mapped source: {mapping_value}")


def build_rows() -> list[dict[str, object]]:
    mapping = json.loads((OUT / "sealed_mapping.json").read_text(encoding="utf-8"))
    answers = {}
    for anonymous_arm, source in mapping["mapping"].items():
        answers[source_to_architecture(source)] = answer_blocks(
            ANONYMOUS_RESPONSES[anonymous_arm]
        )

    rows = []
    for architecture in ("L", "S"):
        for question, turn in PROBES.items():
            prompt = normalize(
                (ARM_PROMPTS[architecture] / f"turn_{turn:03}.txt").read_text(
                    encoding="utf-8"
                )
            )
            answer = normalize(answers[architecture][turn])
            for domain, item, needle in ITEMS:
                in_prompt = needle in prompt
                in_answer = needle in answer
                if in_prompt and in_answer:
                    status = "recalled"
                elif in_prompt:
                    status = "unused"
                elif in_answer:
                    status = "invented"
                else:
                    status = "absent"
                rows.append(
                    {
                        "arm": architecture,
                        "question": question,
                        "turn": turn,
                        "domain": domain,
                        "item": item,
                        "in_prompt": in_prompt,
                        "in_answer": in_answer,
                        "status": status,
                    }
                )
    return rows


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    summary = {}
    for architecture in ("L", "S"):
        summary[architecture] = {}
        for question in PROBES:
            selected = [
                row
                for row in rows
                if row["arm"] == architecture and row["question"] == question
            ]
            counts = {
                status: sum(row["status"] == status for row in selected)
                for status in ("recalled", "unused", "invented", "absent")
            }
            counts["delivered"] = sum(bool(row["in_prompt"]) for row in selected)
            counts["answer_hits"] = sum(bool(row["in_answer"]) for row in selected)
            summary[architecture][question] = counts
    return summary


def write_report(summary: dict[str, object]) -> None:
    scores = json.loads((OUT / "rubric_scores.json").read_text(encoding="utf-8"))
    mapping = json.loads((OUT / "sealed_mapping.json").read_text(encoding="utf-8"))
    anonymous_for = {
        source_to_architecture(source): anonymous
        for anonymous, source in mapping["mapping"].items()
    }
    lines = [
        "# Study 009 Mechanism Analysis",
        "",
        "Generated after blinded scores were committed and the mapping was unsealed.",
        "",
        "## Score and null-test result",
        "",
        "| Arm | Anonymous label | Q1-Q13 | Q14 |",
        "|---|---|---:|---:|",
    ]
    for architecture in ("L", "S"):
        anonymous = anonymous_for[architecture]
        lines.append(
            f"| {architecture} | {anonymous} | "
            f"{scores[anonymous]['Q1_Q13_total']:.1f} | "
            f"{scores[anonymous]['Q14']['primary']:.1f} |"
        )
    lines.extend(
        [
            "",
            "Arm S trails Arm L by 1.5 points on Q1-Q13. Under the locked null-test "
            "rule, this is evidence of LTM value at the 120-turn scale and cancels "
            "retirement. Prediction P1 (S >= L) is refuted.",
            "",
            "## Atomic delivery",
            "",
            "| Arm | Probe | Delivered / 17 | Recalled | Unused | Invented | Absent |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for architecture in ("L", "S"):
        for question in PROBES:
            block = summary[architecture][question]
            lines.append(
                f"| {architecture} | {question} | {block['delivered']} | "
                f"{block['recalled']} | {block['unused']} | "
                f"{block['invented']} | {block['absent']} |"
            )
    lines.extend(
        [
            "",
            "The complete item-level matrix is `fact_delivery_matrix.csv`. "
            "A delivered item appears anywhere in the constructed prompt; a recalled "
            "item appears in the assistant-only answer. `unused` means delivered but "
            "not recalled, and `invented` means recalled without delivery in that "
            "turn's prompt.",
            "",
            "## Score-gap anatomy",
            "",
            "- Q5 accounts for 1.0 point. Arm L's turn-116 prompt contains both "
            "`lead white ground` and `ultramarine glaze`; Arm S's contains neither. "
            "L recalls both and S recalls neither.",
            "- Q8 accounts for 0.5 point. Arm L's turn-119 prompt contains "
            "photophore context but not the exact `mantle margin` phrase; it answers "
            "both parts correctly. Arm S receives neither term and gives the wrong "
            "location. This is compatible with contextual support but is not clean "
            "exact-fact delivery attribution.",
            "- Q14 adds a separate 0.5-point breadth difference: L names all four "
            "domains with one named-only lapse, while S explicitly omits two domains.",
            "",
            "## Context cost",
            "",
            "| Arm | Turn 120 estimated tokens | Turn 121 estimated tokens |",
            "|---|---:|---:|",
            "| L | 15,079 | 15,448 |",
            "| S | 5,233 | 5,408 |",
            "",
            "Arm S used roughly one third of L's estimated prompt tokens at the "
            "breadth probes, but the lower cost came with fewer delivered facts and "
            "a 1.5-point Q1-Q13 deficit.",
            "",
            "## Integrity",
            "",
            "- Arm L is the byte-verified accepted Study 007 artifact.",
            "- Arm S completed 121 turns with no forbidden LTM or digest module loaded.",
            "- The Arm S ablation and full run matched byte-for-byte for all first 35 "
            "constructed prompts and responses across fresh server lifecycles.",
            "- Git order is pre-score artifact commit `f41d133`, blinded score commit "
            "`0e676d2`, then this mechanism analysis.",
            "- The digest failed G1 and was dropped, so digest Bars 1 and 2 are not "
            "evaluable.",
            "",
        ]
    )
    (OUT / "mechanism_analysis.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = build_rows()
    with (OUT / "fact_delivery_matrix.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = summarize(rows)
    (OUT / "fact_delivery_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    write_report(summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

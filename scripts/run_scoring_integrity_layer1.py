from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "experiments" / "audits" / "scoring_integrity"
OUT = AUDIT / "layer1"


@dataclass(frozen=True)
class Arm:
    item_id: str
    study: int
    label: str
    responses: str
    scores: str
    score_key: str | None = None


ARMS = [
    Arm("s001_iterative", 1, "iterative", "experiments/study_001/runs/run_001/iterative/rubric/responses.md", "experiments/study_001/runs/run_001/iterative/rubric/scores.md"),
    Arm("s001_full_context", 1, "full_context", "experiments/study_001/runs/run_001/full_context/rubric/responses.md", "experiments/study_001/runs/run_001/full_context/rubric/scores.md"),
    Arm("s001_compaction", 1, "compaction", "experiments/study_001/runs/run_001/compaction/rubric/responses.md", "experiments/study_001/runs/run_001/compaction/rubric/scores.md"),
    Arm("s002_c", 2, "C_iterative", "experiments/study_002/runs/run_001/iterative/rubric/responses.md", "experiments/study_002/runs/run_001/iterative/rubric/scores.md"),
    Arm("s002_a", 2, "A_full_context", "experiments/study_002/runs/run_001/full_context/rubric/responses.md", "experiments/study_002/runs/run_001/full_context/rubric/scores.md"),
    Arm("s002_b", 2, "B_compaction", "experiments/study_002/runs/run_001/compaction/rubric/responses.md", "experiments/study_002/runs/run_001/compaction/rubric/scores.md"),
    Arm("s003_accepted", 3, "accepted", "experiments/study_003/runs/run_001/condition_c/rubric/responses.md", "experiments/study_003/runs/run_001/condition_c/rubric/scores.md"),
    Arm("s004_treatment", 4, "treatment", "experiments/study_004/runs/study_004_full_002/condition_c/rubric/responses.md", "experiments/study_004/runs/study_004_full_002/condition_c/rubric/scores.md"),
    Arm("s004_control", 4, "v3_control", "experiments/study_004/controls/v3_same_settings/v3_control_002/iterative/rubric/responses.md", "experiments/study_004/controls/v3_same_settings/v3_control_002/iterative/rubric/scores.md"),
    Arm("s005_treatment", 5, "treatment", "experiments/study_005/runs/study_005_full_001/condition_c/rubric/responses.md", "experiments/study_005/runs/study_005_full_001/condition_c/rubric/scores.md"),
    Arm("s005_control", 5, "promotion_control", "experiments/study_005/controls/promotion_seeded/promotion_seeded_001/condition_c/rubric/responses.md", "experiments/study_005/controls/promotion_seeded/promotion_seeded_001/condition_c/rubric/scores.md"),
    Arm("s006_treatment", 6, "treatment", "experiments/study_006/runs/study_006_full_001/condition_c/rubric/responses.md", "experiments/study_006/evaluation/rubric_scores.json", "treatment"),
    Arm("s006_control", 6, "whole_turn_control", "experiments/study_006/controls/whole_turn_seeded/run_001/condition_c/rubric/responses.md", "experiments/study_006/evaluation/rubric_scores.json", "control"),
    Arm("s007_treatment", 7, "treatment", "experiments/study_007/evaluation/arm_A/responses.md", "experiments/study_007/evaluation/rubric_scores.json", "arm_A"),
    Arm("s007_control", 7, "count_budget_control", "experiments/study_007/evaluation/arm_B/responses.md", "experiments/study_007/evaluation/rubric_scores.json", "arm_B"),
    Arm("s009_l", 9, "L", "experiments/study_009/evaluation/arm_A/responses.md", "experiments/study_009/evaluation/rubric_scores.json", "arm_A"),
    Arm("s009_s", 9, "S", "experiments/study_009/evaluation/arm_B/responses.md", "experiments/study_009/evaluation/rubric_scores.json", "arm_B"),
]


TURN_MAP_S1 = {
    "Q1": [25], "Q2": [30], "Q3": [29], "Q4": [26], "Q5": [28],
    "Q6": [20], "Q7": [31], "Q8": [32], "Q9": [27],
    "Q10": list(range(25, 33)),
}
TURN_MAP = {
    "Q1": [112], "Q2": [113], "Q3": [114], "Q4": [115], "Q5": [116],
    "Q6": [117], "Q7": [118], "Q8": [119], "Q9": [117], "Q10": [118],
    "Q11": [120], "Q12": [114], "Q13": list(range(112, 121)), "Q14": [121],
}
FACTS_S1 = {
    "Q1": ["s1_budget"],
    "Q2": ["s1_performance", "s1_percentile"],
    "Q3": ["s1_dosage"],
    "Q4": ["s1_engineer", "s1_deadline"],
    "Q5": ["s1_cell_line", "s1_expression"],
    "Q6": ["s1_performance"],
    "Q7": ["s1_researcher"],
    "Q8": ["s1_budget", "s1_deadline", "s1_performance", "s1_percentile", "s1_dosage", "s1_expression"],
    "Q9": ["s1_rule_numbered", "s1_rule_confidence"],
    "Q10": ["s1_rule_numbered", "s1_rule_confidence"],
}
FACTS = {
    "Q1": ["civil_span", "civil_steel"],
    "Q2": ["civil_engineer", "civil_load"],
    "Q3": ["rule_numbered", "rule_risk"],
    "Q4": ["art_title", "art_artist", "art_patron", "art_year"],
    "Q5": ["art_ground", "art_glaze"],
    "Q6": ["art_patron", "art_patron_role", "art_papal_identity"],
    "Q7": ["marine_species", "marine_researcher", "marine_depth", "marine_feeding"],
    "Q8": ["marine_photophores", "marine_location"],
    "Q9": ["art_patron", "art_papal_identity"],
    "Q10": ["marine_species", "marine_researcher"],
    "Q11": [
        "civil_span", "civil_steel", "civil_load", "art_year", "marine_depth",
        "monetary_threshold", "monetary_target", "civil_project", "civil_engineer",
        "art_title", "art_artist", "art_patron", "monetary_fed", "monetary_taylor",
        "monetary_researcher", "marine_species", "marine_researcher",
    ],
    "Q12": ["rule_numbered", "rule_risk"],
    "Q13": ["rule_numbered"],
    "Q14": [
        "civil_project", "civil_span", "civil_engineer", "civil_steel", "civil_load",
        "art_title", "art_artist", "art_patron", "art_year", "art_ground",
        "art_glaze", "art_papal_identity", "monetary_taylor", "monetary_fed",
        "monetary_researcher", "monetary_threshold", "monetary_target",
        "marine_species", "marine_researcher", "marine_depth",
        "marine_photophores", "marine_location", "marine_feeding",
    ],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace("–", "-").replace("—", "-")
    text = re.sub(r"[^\w.%$-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_turns(text: str) -> dict[int, str]:
    starts = list(re.finditer(r"(?m)^##\s+Turn\s+(\d+)\b[^\n]*\n", text))
    turns: dict[int, str] = {}
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        section = text[match.end():end]
        marker = re.search(r"(?mi)^\*\*Assistant response:\*\*\s*$", section)
        if marker:
            section = section[marker.end():]
        turns[int(match.group(1))] = section.strip()
    return turns


def split_questions(text: str) -> dict[str, str]:
    starts = list(re.finditer(r"(?m)^##\s+(Q\d+)\b[^\n]*\n", text))
    questions: dict[str, str] = {}
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        section = text[match.end():end]
        marker = re.search(r"(?mi)^\*\*Assistant response:\*\*\s*$", section)
        if marker:
            section = section[marker.end():]
        questions[match.group(1)] = section.strip()
    return questions


def scoreable_surface(raw: str) -> tuple[str, bool, bool]:
    transcript_assistant = list(re.finditer(r"(?mi)^\*\*Assistant:\*\*\s*", raw))
    if transcript_assistant:
        raw = raw[transcript_assistant[-1].end():]
    opens = len(re.findall(r"<think(?:\s[^>]*)?>", raw, flags=re.I))
    closes = len(re.findall(r"</think>", raw, flags=re.I))
    unclosed = opens > closes
    surface = re.sub(r"<think(?:\s[^>]*)?>.*?</think>", "", raw, flags=re.I | re.S)
    if unclosed:
        first = re.search(r"<think(?:\s[^>]*)?>", surface, flags=re.I)
        if first:
            surface = surface[:first.start()]
    surface = re.sub(r"</?response>|<memory_update>.*?</memory_update>", "", surface, flags=re.I | re.S)
    surface = re.split(r"(?mi)^--- END (?:RECENT|HISTORY|SUMMARY) ---\s*$", surface, maxsplit=1)[0]
    surface = re.split(r"(?mi)^(?:\*\*)?User:(?:\*\*)?\s*", surface, maxsplit=1)[0]
    surface = re.sub(r"</?think>", "", surface, flags=re.I)
    surface = re.sub(r"<rule_detection>.*?</rule_detection>", "", surface, flags=re.I | re.S)
    surface = re.split(r"(?mi)^\*\*(?:Score|Notes):\*\*", surface, maxsplit=1)[0]
    surface = re.sub(r"(?m)^\s*---+\s*$", "", surface)
    return surface.strip(), unclosed, opens > 0


def looks_truncated(raw: str, surface: str, unclosed: bool) -> bool:
    if unclosed:
        return True
    candidate = (surface or raw).rstrip()
    if not candidate:
        return False
    if re.search(r"(?:\.\.\.|[,;:—-]|\b(?:and|or|the|a|to|of|with|because|which|that))$", candidate, re.I):
        return True
    return False


def study1_turn20(arm: Arm) -> tuple[str, str] | None:
    base = Path(arm.responses).parents[1]
    db_rel = (base / "study.db").as_posix()
    db_path = ROOT / db_rel
    if not db_path.exists():
        log_path = ROOT / base / "logs" / "turns.jsonl"
        if not log_path.exists():
            return None
        for line in log_path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record.get("turn_number") == 20:
                return str(record.get("user_message", "")), str(record.get("assistant_message", ""))
        return None
    connection = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    try:
        row = connection.execute(
            "SELECT user_message, assistant_message FROM episodes WHERE turn_number = 20"
        ).fetchone()
    finally:
        connection.close()
    return (row[0], row[1]) if row else None


def parse_markdown_scores(text: str) -> tuple[dict[str, float], dict[str, str]]:
    scores: dict[str, float] = {}
    rationales: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\|\s*(Q\d+)\b[^|]*\|\s*([01](?:\.0)?|0\.5)\s*\|\s*(.*?)\s*\|$", line)
        if match:
            q = match.group(1)
            scores[q] = float(match.group(2))
            rationales[q] = match.group(3).strip()
    return scores, rationales


def parse_json_scores(path: Path, key: str) -> tuple[dict[str, float], dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    branch = data[key]
    scores: dict[str, float] = {}
    rationales: dict[str, str] = {}
    for q in [f"Q{i}" for i in range(1, 15)]:
        value = branch.get(q)
        if isinstance(value, dict):
            scores[q] = float(value["primary"])
            rationales[q] = str(value.get("rationale", ""))
        elif value is not None:
            scores[q] = float(value)
            rationale_root = data.get("rationale", {})
            if isinstance(rationale_root, dict):
                rationales[q] = str(rationale_root.get(q, ""))
    return scores, rationales


def fact_presence(surface: str, fact_ids: list[str], variants: dict[str, list[str]]) -> dict[str, bool]:
    haystack = normalize(surface)
    result = {}
    for fact_id in fact_ids:
        accepted = variants[fact_id]
        result[fact_id] = any(normalize(variant) in haystack for variant in accepted)
    return result


def rationale_claim_conflict(rationale: str, presence: dict[str, bool], variants: dict[str, list[str]]) -> bool:
    if not rationale:
        return False
    norm = normalize(rationale)
    if (
        any(phrase in norm for phrase in ["comprehensive response", "key entities and values present", "all required"])
        and not all(presence.values())
    ):
        return True
    for fact_id, present in presence.items():
        if present:
            continue
        if any(normalize(v) in norm for v in variants[fact_id]):
            if not re.search(r"\b(?:missing|absent|omit|wrong|incorrect|neither|not)\b", norm):
                return True
    return False


def threshold_conflict(study: int, q: str, score: float, found: int, total: int) -> bool:
    if total == 0:
        return False
    if study == 1:
        if q in {"Q1", "Q3", "Q6", "Q7"}:
            mechanical = 1.0 if found == total else 0.0
        elif q == "Q2":
            mechanical = 1.0 if found == 2 else (0.5 if found == 1 else 0.0)
        elif q in {"Q4", "Q5"}:
            mechanical = 1.0 if found == 2 else (0.5 if found == 1 else 0.0)
        elif q in {"Q8", "Q9"}:
            mechanical = 1.0 if found == total else 0.0
        else:
            return False
    else:
        if q in {"Q1", "Q2", "Q3", "Q5", "Q8", "Q12"}:
            mechanical = 1.0 if found == total else (0.5 if found == 1 else 0.0)
        elif q == "Q4":
            mechanical = 1.0 if found == 4 else (0.5 if found in {2, 3} else 0.0)
        elif q == "Q7":
            mechanical = 1.0 if found == 4 else (0.5 if found in {2, 3} else 0.0)
        elif q == "Q11":
            mechanical = 1.0 if found >= 14 else 0.0
        else:
            return False
    return not math.isclose(score, mechanical)


def artifact_registry() -> list[dict[str, object]]:
    paths = sorted({arm.responses for arm in ARMS} | {arm.scores for arm in ARMS})
    for arm in ARMS:
        if arm.study == 1:
            db_rel = (Path(arm.responses).parents[1] / "study.db").as_posix()
            if (ROOT / db_rel).exists():
                paths.append(db_rel)
            else:
                log_rel = (Path(arm.responses).parents[1] / "logs" / "turns.jsonl").as_posix()
                if (ROOT / log_rel).exists():
                    paths.append(log_rel)
    paths = sorted(set(paths))
    records = []
    for rel in paths:
        if "study_010" in rel:
            raise RuntimeError("Study 010 path rejected")
        path = ROOT / rel
        records.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256(path)})
    return records


def run() -> None:
    variants = json.loads((AUDIT / "fact_variants.json").read_text(encoding="utf-8"))["facts"]
    OUT.mkdir(parents=True, exist_ok=True)
    registry = artifact_registry()
    (OUT / "artifact_hashes_pre.json").write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    rows = []
    census = []
    for arm in ARMS:
        response_path = ROOT / arm.responses
        score_path = ROOT / arm.scores
        turns = split_turns(response_path.read_text(encoding="utf-8"))
        questions = split_questions(response_path.read_text(encoding="utf-8"))
        if arm.study == 1 and 20 not in turns:
            stored = study1_turn20(arm)
            if stored:
                turns[20] = stored[1]
        if score_path.suffix == ".json":
            scores, rationales = parse_json_scores(score_path, arm.score_key or "")
        else:
            scores, rationales = parse_markdown_scores(score_path.read_text(encoding="utf-8"))
        expected = 10 if arm.study == 1 else (13 if arm.study <= 3 else 14)
        turn_map = TURN_MAP_S1 if arm.study == 1 else TURN_MAP
        facts_map = FACTS_S1 if arm.study == 1 else FACTS
        for number in range(1, expected + 1):
            q = f"Q{number}"
            raw = questions.get(q, "") if arm.study == 3 else "\n\n".join(turns.get(t, "") for t in turn_map[q]).strip()
            source_parts = [raw] if arm.study == 3 else [turns.get(t, "") for t in turn_map[q]]
            surface_parts = [scoreable_surface(part)[0] for part in source_parts]
            surface = "\n\n".join(part for part in surface_parts if part).strip()
            unclosed = any(scoreable_surface(part)[1] for part in source_parts)
            has_reasoning = any(scoreable_surface(part)[2] for part in source_parts)
            empty = not raw.strip()
            no_answer = not surface.strip()
            truncated = looks_truncated(raw, surface, unclosed) if not empty else False
            presence = fact_presence(surface, facts_map[q], variants)
            raw_presence = fact_presence(raw, facts_map[q], variants)
            score = scores.get(q)
            rationale = rationales.get(q, "")
            flags = []
            if q not in {"Q10" if arm.study == 1 else "Q13"} and score is not None and score > 0 and (no_answer or truncated):
                flags.append("F1")
            if rationale_claim_conflict(rationale, presence, variants):
                flags.append("F2")
            if "all four" in normalize(rationale) and q in {"Q11", "Q14"}:
                domains = [
                    any(v for k, v in presence.items() if k.startswith("civil")),
                    any(v for k, v in presence.items() if k.startswith("art")),
                    any(v for k, v in presence.items() if k.startswith("monetary")),
                    any(v for k, v in presence.items() if k.startswith("marine")),
                ]
                if not all(domains):
                    flags.append("F3")
            if score is not None and threshold_conflict(arm.study, q, score, sum(presence.values()), len(presence)):
                flags.append("F4")
            if not rationale:
                flags.append("F5")
            rows.append({
                "item_id": f"{arm.item_id}_{q.lower()}",
                "arm_id": arm.item_id,
                "study": arm.study,
                "arm": arm.label,
                "question": q,
                "turns": ",".join(map(str, turn_map[q])),
                "response_path": arm.responses,
                "score_path": arm.scores,
                "response_sha256": sha256(response_path),
                "score_sha256": sha256(score_path),
                "raw_chars": len(raw),
                "scoreable_chars": len(surface),
                "empty": empty,
                "has_reasoning": has_reasoning,
                "unclosed_reasoning": unclosed,
                "truncated": truncated,
                "no_answer": no_answer,
                "original_score": score,
                "rationale": rationale,
                "facts_found": sum(presence.values()),
                "facts_total": len(presence),
                "fact_presence": presence,
                "raw_facts_found": sum(raw_presence.values()),
                "raw_fact_presence": raw_presence,
                "flags": sorted(set(flags)),
                "scoreable_answer": surface,
            })
        census.append({
            "arm_id": arm.item_id,
            "study": arm.study,
            "arm": arm.label,
            "expected_items": expected,
            "parsed_scores": len(scores),
            "parsed_turns": len(turns),
            "missing_scores": sorted(set(f"Q{i}" for i in range(1, expected + 1)) - set(scores)),
            "missing_turns": [] if (arm.study == 3 and questions) else sorted(set(sum((turn_map[f"Q{i}"] for i in range(1, expected + 1)), [])) - set(turns)),
        })
    with (OUT / "items.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (OUT / "items.csv").open("w", encoding="utf-8", newline="") as fh:
        fields = [
            "item_id", "arm_id", "study", "arm", "question", "turns",
            "raw_chars", "scoreable_chars", "empty", "has_reasoning",
            "unclosed_reasoning", "truncated", "no_answer", "original_score",
            "facts_found", "facts_total", "flags", "response_path", "score_path",
            "raw_facts_found",
        ]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            flat = {key: row[key] for key in fields}
            flat["flags"] = ";".join(row["flags"])
            writer.writerow(flat)
    (OUT / "census.json").write_text(json.dumps(census, indent=2) + "\n", encoding="utf-8")
    summary = {
        "arms": len(ARMS),
        "items": len(rows),
        "no_answer": sum(row["no_answer"] for row in rows),
        "truncated": sum(row["truncated"] for row in rows),
        "unclosed_reasoning": sum(row["unclosed_reasoning"] for row in rows),
        "flagged": sum(bool(row["flags"]) for row in rows),
        "flag_counts": {
            flag: sum(flag in row["flags"] for row in rows)
            for flag in ["F1", "F2", "F3", "F4", "F5"]
        },
        "study_001_variant_timing_limitation": True,
        "known_case_s002_c_q11": next(
            {
                "no_answer": row["no_answer"],
                "unclosed_reasoning": row["unclosed_reasoning"],
                "scoreable_facts": row["facts_found"],
                "raw_artifact_facts": row["raw_facts_found"],
                "facts_total": row["facts_total"],
                "flags": row["flags"],
            }
            for row in rows if row["item_id"] == "s002_c_q11"
        ),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    post = artifact_registry()
    (OUT / "artifact_hashes_post.json").write_text(json.dumps(post, indent=2) + "\n", encoding="utf-8")
    if registry != post:
        raise RuntimeError("Artifact hash drift detected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.parse_args()
    run()

"""Registered descriptive attribution for TC-009 discordant questions."""

from __future__ import annotations

import gzip
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from analysis.locomo_nf_development import adapt_development, sha256_file
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT
from analysis.tc007_allocation import TOTAL_BUDGETS

RUN_ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost" / "runs" / "tc009" / "run"
DIAGNOSTICS = RUN_ROOT / "diagnostics.jsonl.gz"
DIAGNOSTICS_SHA256 = "cc15bf598ea2fce23cddc4c9b076082fb57c0152d8a67799055ae69d9ab3e943"
OUTPUT = RUN_ROOT / "postrun_question_probe.json"


class TC009PostrunError(RuntimeError):
    pass


def _attribution(identifier: str, *, control: set[str], dynamic: set[str], session: set[str], a3: set[str]) -> str:
    added = identifier in dynamic and identifier not in control
    lost = identifier in control and identifier not in dynamic
    if not (added or lost):
        raise TC009PostrunError("Attribution requires a dynamic/control evidence disagreement")
    in_session = identifier in session
    in_a3 = identifier in a3
    if added:
        if in_session and in_a3:
            return "gain_shared_session_and_a3"
        if in_session:
            return "gain_shared_session_only"
        if in_a3:
            return "gain_shared_a3_only"
        return "dynamic_unique_gain"
    if not in_session and not in_a3:
        return "common_fixed_protection_loss"
    if not in_session:
        return "loss_shared_session_only"
    if not in_a3:
        return "loss_shared_a3_only"
    return "dynamic_unique_loss"


def _question_probe(row: dict[str, Any], question: Any, case: Any, budget: int) -> dict[str, Any]:
    block = row["budgets"][str(budget)]
    evidence = set(row["evidence_candidate_ids"])
    selected = {arm: set(block[arm]["selected_ids"]) for arm in ("control", "a3", "session", "dynamic")}
    by_identity = {pair.identity: pair for pair in case.pairs}
    ranks = {
        arm: {identifier: index for index, identifier in enumerate(row["orders"][arm], 1)}
        for arm in ("dense", "a3", "session", "dynamic")
    }
    dynamic_steps = {step["candidate_id"]: step for step in row["dynamic_steps"]}
    added = sorted(evidence & selected["dynamic"] - selected["control"])
    lost = sorted(evidence & selected["control"] - selected["dynamic"])

    def detail(identifier: str) -> dict[str, Any]:
        pair = by_identity[identifier]
        step = dynamic_steps[identifier]
        return {
            "candidate_id": identifier,
            "session_id": pair.session_id,
            "dense_rank": ranks["dense"][identifier],
            "a3_rank": ranks["a3"][identifier],
            "session_rank": ranks["session"][identifier],
            "dynamic_rank": ranks["dynamic"][identifier],
            "selected_by_a3": identifier in selected["a3"],
            "selected_by_session": identifier in selected["session"],
            "control_phase": block["control"]["phase"].get(identifier),
            "dynamic_phase": block["dynamic"]["phase"].get(identifier),
            "session_count_before": step["session_count_before"],
            "raw_similarity": step["raw_similarity"],
            "accumulated_penalty": step["accumulated_penalty"],
            "adjusted_score": step["adjusted_score"],
            "attribution": _attribution(identifier, **selected),
        }

    complete = {
        arm: bool(evidence) and evidence <= chosen for arm, chosen in selected.items()
    }
    counts = {arm: len(evidence & chosen) for arm, chosen in selected.items()}
    identity_changed = counts["control"] != counts["dynamic"]
    completion_changed = complete["control"] != complete["dynamic"]
    return {
        "question_id": row["question_id"],
        "question": question.question,
        "sample_id": row["sample_id"],
        "source_index": row["source_index"],
        "category": question.category,
        "population": row["population"],
        "budget": budget,
        "required_candidates": len(evidence),
        "required_sessions": sorted({by_identity[item].session_id for item in evidence}),
        "evidence_counts": counts,
        "complete": complete,
        "added_evidence": [detail(identifier) for identifier in added],
        "displaced_evidence": [detail(identifier) for identifier in lost],
        "identity_changed": identity_changed,
        "completion_changed": completion_changed,
        "identity_completion_disagreement": identity_changed != completion_changed,
        "selected_sessions": {
            arm: len({by_identity[item].session_id for item in chosen})
            for arm, chosen in selected.items()
        },
        "dynamic_only_candidates": len(selected["dynamic"] - selected["control"]),
        "control_only_candidates": len(selected["control"] - selected["dynamic"]),
    }


def _rank_summary(values: list[int]) -> dict[str, Any]:
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "median": statistics.median(values) if values else None,
        "max": max(values) if values else None,
        "values": sorted(values),
    }


def generate(output: Path = OUTPUT) -> dict[str, Any]:
    if sha256_file(DIAGNOSTICS) != DIAGNOSTICS_SHA256:
        raise TC009PostrunError("Accepted TC-009 diagnostics drifted")
    cases = adapt_development(DATASET_PATH)
    case_by_id = {case.sample_id: case for case in cases}
    question_by_source = {
        (case.sample_id, question.source_index): question
        for case in cases
        for question in case.questions
        if question.duplicate_ordinal == 0
    }
    probes: list[dict[str, Any]] = []
    with gzip.open(DIAGNOSTICS, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            question = question_by_source[(row["sample_id"], int(row["source_index"]))]
            case = case_by_id[row["sample_id"]]
            for budget in TOTAL_BUDGETS:
                probe = _question_probe(row, question, case, budget)
                if probe["identity_changed"] or probe["completion_changed"]:
                    probes.append(probe)

    by_budget: dict[str, Any] = {}
    for budget in TOTAL_BUDGETS:
        current = [probe for probe in probes if probe["budget"] == budget]
        breadth = [probe for probe in current if probe["population"] == "breadth"]
        targeted = [probe for probe in current if probe["population"] == "targeted"]
        attribution = Counter()
        breadth_sessions: dict[str, Counter[str]] = defaultdict(Counter)
        breadth_categories: dict[str, Counter[str]] = defaultdict(Counter)
        for probe in current:
            for label, field in (("gain", "added_evidence"), ("loss", "displaced_evidence")):
                for item in probe[field]:
                    attribution[item["attribution"]] += 1
                    if probe["population"] == "breadth":
                        breadth_sessions[item["session_id"]][label] += 1
                        breadth_categories[str(probe["category"])][label] += 1
        targeted_loss_ranks = [
            item["dense_rank"]
            for probe in targeted
            if probe["complete"]["control"] and not probe["complete"]["dynamic"]
            for item in probe["displaced_evidence"]
        ]
        by_budget[str(budget)] = {
            "discordant_questions": len(current),
            "breadth_share_gains": sum(
                probe["evidence_counts"]["dynamic"] > probe["evidence_counts"]["control"] for probe in breadth
            ),
            "breadth_share_losses": sum(
                probe["evidence_counts"]["dynamic"] < probe["evidence_counts"]["control"] for probe in breadth
            ),
            "breadth_complete_gains": sum(
                probe["complete"]["dynamic"] and not probe["complete"]["control"] for probe in breadth
            ),
            "breadth_complete_losses": sum(
                probe["complete"]["control"] and not probe["complete"]["dynamic"] for probe in breadth
            ),
            "breadth_by_category": {key: dict(sorted(value.items())) for key, value in sorted(breadth_categories.items())},
            "breadth_required_source_sessions": {key: dict(sorted(value.items())) for key, value in sorted(breadth_sessions.items())},
            "evidence_attribution": dict(sorted(attribution.items())),
            "targeted_complete_gains": sum(
                probe["complete"]["dynamic"] and not probe["complete"]["control"] for probe in targeted
            ),
            "targeted_complete_losses": sum(
                probe["complete"]["control"] and not probe["complete"]["dynamic"] for probe in targeted
            ),
            "targeted_loss_carrier_dense_ranks": _rank_summary(targeted_loss_ranks),
            "identity_completion_disagreements": sum(
                probe["identity_completion_disagreement"] for probe in current
            ),
        }
    result = {
        "schema": "tc009-postrun-question-probe-v1",
        "status": "DESCRIPTIVE",
        "diagnostics_sha256": DIAGNOSTICS_SHA256,
        "by_budget": by_budget,
        "questions": probes,
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["OUTPUT", "TC009PostrunError", "generate"]

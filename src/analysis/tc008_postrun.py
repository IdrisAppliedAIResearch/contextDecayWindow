"""Registered descriptive attribution for TC-008 discordant questions."""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any

from analysis.locomo_nf_development import adapt_development, sha256_file
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT
from analysis.tc007_allocation import TOTAL_BUDGETS

RUN_ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost" / "runs" / "tc008" / "run"
DIAGNOSTICS = RUN_ROOT / "diagnostics.jsonl.gz"
DIAGNOSTICS_SHA256 = "f97f90707381d9219810de5b5eca64b0f1453b53f9b4e0a4d170aa19f17fd284"
OUTPUT = RUN_ROOT / "postrun_question_probe.json"


class TC008PostrunError(RuntimeError):
    pass


def _question_probe(row: dict[str, Any], question: Any, case: Any, budget: int) -> dict[str, Any]:
    block = row["budgets"][str(budget)]
    evidence = set(row["evidence_candidate_ids"])
    control = set(block["control"]["selected_ids"])
    session = set(block["session"]["selected_ids"])
    a3 = set(block["a3"]["selected_ids"])
    by_identity = {pair.identity: pair for pair in case.pairs}
    dense_rank = {identity: index for index, identity in enumerate(row["orders"]["dense"], 1)}
    session_rank = {identity: index for index, identity in enumerate(row["orders"]["session"], 1)}
    added_evidence = sorted(evidence & session - control)
    lost_evidence = sorted(evidence & control - session)

    def evidence_detail(identifier: str) -> dict[str, Any]:
        pair = by_identity[identifier]
        return {
            "candidate_id": identifier,
            "session_id": pair.session_id,
            "dense_rank": dense_rank[identifier],
            "session_spread_rank": session_rank[identifier],
            "selected_by_a3": identifier in a3,
            "session_phase": block["session"]["phase"].get(identifier),
            "control_phase": block["control"]["phase"].get(identifier),
        }

    control_complete = bool(evidence) and evidence <= control
    session_complete = bool(evidence) and evidence <= session
    a3_complete = bool(evidence) and evidence <= a3
    if lost_evidence and all(identifier not in a3 for identifier in lost_evidence):
        mechanism_read = "shared_fixed_protection_cost"
    elif lost_evidence and any(identifier in a3 for identifier in lost_evidence):
        mechanism_read = "source_session_grouping_loss_vs_a3"
    elif added_evidence and not any(identifier in a3 for identifier in added_evidence):
        mechanism_read = "source_session_unique_gain"
    elif added_evidence:
        mechanism_read = "gain_shared_with_a3"
    else:
        mechanism_read = "selected_set_change_without_required_identity_change"
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
        "control_evidence_count": len(evidence & control),
        "session_evidence_count": len(evidence & session),
        "a3_evidence_count": len(evidence & a3),
        "control_complete": control_complete,
        "session_complete": session_complete,
        "a3_complete": a3_complete,
        "added_evidence": [evidence_detail(identifier) for identifier in added_evidence],
        "lost_evidence": [evidence_detail(identifier) for identifier in lost_evidence],
        "control_selected_sessions": len({by_identity[item].session_id for item in control}),
        "session_selected_sessions": len({by_identity[item].session_id for item in session}),
        "session_only_candidates": len(session - control),
        "control_only_candidates": len(control - session),
        "mechanism_read": mechanism_read,
    }


def generate(output: Path = OUTPUT) -> dict[str, Any]:
    if sha256_file(DIAGNOSTICS) != DIAGNOSTICS_SHA256:
        raise TC008PostrunError("Accepted TC-008 diagnostics drifted")
    cases = adapt_development(DATASET_PATH)
    case_by_id = {case.sample_id: case for case in cases}
    question_by_source = {
        (case.sample_id, question.source_index): question
        for case in cases
        for question in case.questions
        if question.duplicate_ordinal == 0
    }
    with gzip.open(DIAGNOSTICS, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    probes = []
    for row in rows:
        question = question_by_source[(row["sample_id"], int(row["source_index"]))]
        case = case_by_id[row["sample_id"]]
        for budget in TOTAL_BUDGETS:
            probe = _question_probe(row, question, case, budget)
            share_changed = probe["control_evidence_count"] != probe["session_evidence_count"]
            complete_changed = probe["control_complete"] != probe["session_complete"]
            if share_changed or complete_changed:
                probes.append(probe)
    by_budget = {}
    for budget in TOTAL_BUDGETS:
        selected = [probe for probe in probes if probe["budget"] == budget]
        breadth = [probe for probe in selected if probe["population"] == "breadth"]
        targeted = [probe for probe in selected if probe["population"] == "targeted"]
        by_budget[str(budget)] = {
            "discordant_questions": len(selected),
            "breadth_share_gains": sum(
                probe["session_evidence_count"] > probe["control_evidence_count"] for probe in breadth
            ),
            "breadth_share_losses": sum(
                probe["session_evidence_count"] < probe["control_evidence_count"] for probe in breadth
            ),
            "targeted_complete_gains": sum(
                probe["session_complete"] and not probe["control_complete"] for probe in targeted
            ),
            "targeted_complete_losses": sum(
                probe["control_complete"] and not probe["session_complete"] for probe in targeted
            ),
            "mechanism_reads": dict(sorted(Counter(probe["mechanism_read"] for probe in selected).items())),
        }
    result = {
        "schema": "tc008-postrun-question-probe-v1",
        "status": "DESCRIPTIVE",
        "diagnostics_sha256": DIAGNOSTICS_SHA256,
        "by_budget": by_budget,
        "questions": probes,
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["OUTPUT", "TC008PostrunError", "generate"]

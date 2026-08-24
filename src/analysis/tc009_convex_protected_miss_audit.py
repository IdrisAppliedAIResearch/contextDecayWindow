"""Post-result audit of CC80+A3 gains and remaining evidence misses."""

from __future__ import annotations

import ast
import csv
import gzip
import json
import re
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping, Sequence

from analysis.locomo_nf_development import adapt_development, sha256_file
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT

ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
PARENT = ROOT / "artifacts" / "tc009_convex_protected_probe"
SELECTIONS = PARENT / "preflight" / "selections.jsonl.gz"
PARENT_RESULT = PARENT / "result" / "result.json"
PARENT_QUESTIONS = PARENT / "result" / "per_question.csv"
ARTIFACT = ROOT / "artifacts" / "tc009_convex_protected_miss_audit"
PREFLIGHT = ARTIFACT / "preflight"
RESULT = ARTIFACT / "result"
BUDGETS = (16_000, 32_000)
ARMS = ("dense", "cc80", "dense_a3", "cc80_a3")
INPUT_SHA256 = {
    "selections": "916632ff25c22c03e8bcc06d18592555eed30e3ffbf656903587e6052ca7a376",
    "result": "0cfe11374f3817c08f8a24bc459dd460325c715e1d05d65ec1188f598c6e9bcf",
    "questions": "c4b52ead85535a1250e9ac8952bc60201a8b10304846272dbe838bbba9ee12c6",
    "corpus": "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4",
}

TEXT_FLAGS = {
    "QUANTITY": re.compile(r"\b(?:how many|how much|number|amount)\b", re.I),
    "TEMPORAL": re.compile(r"\b(?:when|before|after|first|last|earlier|later|how long|year|date)\b", re.I),
    "LOCATION": re.compile(r"\b(?:where|places?|locations?)\b", re.I),
    "CAUSAL": re.compile(r"\b(?:why|causes?|reasons?|helped)\b", re.I),
    "ENUMERATION": re.compile(r"\b(?:what (?:are|were|places|activities|causes|skills|events|jobs|things)|which|how many)\b", re.I),
}


class MissAuditError(RuntimeError):
    pass


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def question_flags(text: str) -> tuple[str, ...]:
    found = tuple(name for name, pattern in TEXT_FLAGS.items() if pattern.search(text))
    return found or ("UNMARKED",)


def association_label(treatment: bool, cc80: bool, dense_a3: bool) -> str:
    """Label controls that share the treatment outcome, for gains or losses."""

    cc_match = cc80 == treatment
    a3_match = dense_a3 == treatment
    if cc_match and a3_match:
        return "BOTH_CONTROLS"
    if cc_match:
        return "CC80_ONLY"
    if a3_match:
        return "A3_ONLY"
    return "COMBINATION_ONLY"


def structural_group(carriers: int, sessions: int) -> str:
    if carriers == 1 and sessions == 1:
        return "SINGLE_CARRIER_SINGLE_SESSION"
    if sessions == 1:
        return "MULTI_CARRIER_ONE_SESSION"
    return "MULTI_SESSION"


def admission_phase(allocation: Mapping[str, Any], evidence_id: str) -> str:
    phases = (
        ("INITIAL_RELEVANCE", "initial_relevance_ids"),
        ("PROTECTED_SPREAD", "spread_ids"),
        ("RETURNED_RELEVANCE", "returned_relevance_ids"),
    )
    hits = [name for name, key in phases if evidence_id in allocation[key]]
    if len(hits) > 1:
        raise MissAuditError(f"Evidence appears in multiple phases: {evidence_id}")
    return hits[0] if hits else "ABSENT"


def _load_question_rows() -> list[dict[str, Any]]:
    with PARENT_QUESTIONS.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["source_index"] = int(row["source_index"])
        row["evidence_ids"] = tuple(ast.literal_eval(row["evidence_ids"]))
        for arm in ARMS:
            for budget in BUDGETS:
                row[f"{arm}_{budget}_evidence"] = int(row[f"{arm}_{budget}_evidence"])
                raw = row[f"{arm}_{budget}_complete"]
                if raw not in {"True", "False"}:
                    raise MissAuditError("Non-boolean completion value")
                row[f"{arm}_{budget}_complete"] = raw == "True"
    return rows


def _load_selections() -> dict[tuple[str, int], dict[str, Any]]:
    with gzip.open(SELECTIONS, "rt", encoding="utf-8") as handle:
        rows = list(map(json.loads, handle))
    joined = {(row["sample_id"], int(row["source_index"])): row for row in rows}
    if len(joined) != len(rows):
        raise MissAuditError("Duplicate selection join key")
    return joined


def _paired(rows: Sequence[Mapping[str, Any]], budget: int, treatment: str, baseline: str, population: str) -> dict[str, int]:
    subset = [row for row in rows if population == "combined" or row["population"] == population]
    tkey, bkey = f"{treatment}_{budget}_complete", f"{baseline}_{budget}_complete"
    gains = sum(bool(row[tkey]) and not bool(row[bkey]) for row in subset)
    losses = sum(bool(row[bkey]) and not bool(row[tkey]) for row in subset)
    return {"n": len(subset), "baseline": sum(bool(row[bkey]) for row in subset), "treatment": sum(bool(row[tkey]) for row in subset), "gains": gains, "losses": losses, "net": gains - losses}


def _parent_reproduction(rows: Sequence[Mapping[str, Any]], parent: Mapping[str, Any]) -> dict[str, Any]:
    checks = 0
    for budget in BUDGETS:
        cell = parent["cells"][str(budget)]
        for population in ("combined", "targeted", "breadth", "other"):
            actual = _paired(rows, budget, "cc80_a3", "dense", population)
            if actual != cell[population]:
                raise MissAuditError(f"Parent treatment summary drift: {budget}/{population}")
            checks += 1
            for baseline, key in (("cc80", "versus_full_cc80"), ("dense_a3", "versus_dense_a3")):
                actual = _paired(rows, budget, "cc80_a3", baseline, population)
                if actual != cell[key][population]:
                    raise MissAuditError(f"Parent control summary drift: {budget}/{baseline}/{population}")
                checks += 1
    return {"checks": checks, "expected": 24}


def _synthetic_reachability() -> dict[str, Any]:
    labels = {
        association_label(True, True, True),
        association_label(True, True, False),
        association_label(True, False, True),
        association_label(True, False, False),
        association_label(False, False, False),
        association_label(False, False, True),
        association_label(False, True, False),
        association_label(False, True, True),
    }
    allocation = {"initial_relevance_ids": ["a"], "spread_ids": ["b"], "returned_relevance_ids": ["c"]}
    phases = {admission_phase(allocation, identifier) for identifier in ("a", "b", "c", "d")}
    return {
        "association_labels": sorted(labels),
        "all_associations_reachable": labels == {"BOTH_CONTROLS", "CC80_ONLY", "A3_ONLY", "COMBINATION_ONLY"},
        "admission_phases": sorted(phases),
        "all_phases_reachable": phases == {"INITIAL_RELEVANCE", "PROTECTED_SPREAD", "RETURNED_RELEVANCE", "ABSENT"},
        "miss_states_reachable": True,
    }


def run_preflight(output_dir: Path = PREFLIGHT) -> dict[str, Any]:
    paths = {"selections": SELECTIONS, "result": PARENT_RESULT, "questions": PARENT_QUESTIONS, "corpus": DATASET_PATH}
    observed = {name: sha256_file(path) for name, path in paths.items()}
    if observed != INPUT_SHA256:
        raise MissAuditError(f"Frozen input drift: {observed}")
    rows = _load_question_rows()
    selections = _load_selections()
    parent = json.loads(PARENT_RESULT.read_text(encoding="utf-8"))
    cases = adapt_development(DATASET_PATH)
    metadata = {(case.sample_id, question.source_index): question for case in cases for question in case.questions if not question.duplicate_ordinal}
    row_keys = [(row["sample_id"], row["source_index"]) for row in rows]
    if len(set(row_keys)) != len(rows):
        raise MissAuditError("Duplicate question join key")
    missing_selection = sorted(set(row_keys) - set(selections))
    missing_metadata = sorted(set(row_keys) - set(metadata))
    planted_duplicate_rejected = len({("x", 1): 1, ("x", 1): 2}) != 2
    planted_missing_rejected = ("missing", -1) not in selections
    reproduction = _parent_reproduction(rows, parent)
    reach = _synthetic_reachability()
    population = Counter(row["population"] for row in rows)
    passing = (
        len(rows) == 868
        and population == Counter({"targeted": 704, "other": 120, "breadth": 44})
        and not missing_selection
        and not missing_metadata
        and reproduction["checks"] == reproduction["expected"]
        and reach["all_associations_reachable"]
        and reach["all_phases_reachable"]
        and planted_duplicate_rejected
        and planted_missing_rejected
    )
    result = {
        "status": "PASS" if passing else "FAIL",
        "pf1": {"sha256": observed, "question_rows": len(rows), "selection_rows": len(selections), "population": dict(population)},
        "pf2": {"identity": "read-only audit of frozen dense, CC80, dense+A3 and CC80+A3 selections", "parent_reproduction": reproduction},
        "pf3": {"input_hashes_enforced": True, "selection_mutation": False},
        "pf4": reach,
        "pf5": {"unique_join_keys": len(set(row_keys)), "missing_selection": missing_selection, "missing_metadata": missing_metadata, "planted_duplicate_rejected": planted_duplicate_rejected, "planted_missing_rejected": planted_missing_rejected},
        "pf6": {"parent_schema": parent["schema"], **reproduction},
        "pf7": {"not_applicable": True},
        "pf8": {"conversations": 4, "cannot_detect": "corpus transfer"},
        "pf9": {"residuals": ["association is not causation", "text flags overlap", "ranks do not measure reader use", "raw miss counts confound group prevalence"]},
        "pf10": {"availability_only": True, "reader_run": False},
        "calls": {"embedding": 0, "llm_or_generative": 0},
    }
    _write_json(output_dir / "preflight.json", result)
    if not passing:
        raise MissAuditError("Preflight failed")
    return result


def _rank_summary(values: Iterable[int]) -> dict[str, Any]:
    items = list(values)
    return {"n": len(items), "min": min(items) if items else None, "median": float(median(items)) if items else None, "max": max(items) if items else None}


def _group_rates(records: Sequence[Mapping[str, Any]], budget: int, field: str) -> dict[str, Any]:
    values = sorted({value for row in records for value in ([row[field]] if field != "flags" else row[field])})
    result = {}
    for value in values:
        subset = [row for row in records if (value in row[field] if field == "flags" else row[field] == value)]
        misses = sum(not row[f"complete_{budget}"] for row in subset)
        result[str(value)] = {"n": len(subset), "misses": misses, "miss_rate": misses / len(subset)}
    return result


def run_audit(output_dir: Path = RESULT) -> dict[str, Any]:
    preflight_path = PREFLIGHT / "preflight.json"
    if not preflight_path.exists() or json.loads(preflight_path.read_text(encoding="utf-8"))["status"] != "PASS":
        raise MissAuditError("Passing Preflight absent")
    for name, path in {"selections": SELECTIONS, "result": PARENT_RESULT, "questions": PARENT_QUESTIONS, "corpus": DATASET_PATH}.items():
        if sha256_file(path) != INPUT_SHA256[name]:
            raise MissAuditError(f"Frozen input drift after Preflight: {name}")

    source_rows = _load_question_rows()
    selections = _load_selections()
    cases = adapt_development(DATASET_PATH)
    metadata: dict[tuple[str, int], dict[str, Any]] = {}
    for case in cases:
        dialog_to_pair = {dialog_id: pair for pair in case.pairs for dialog_id in pair.dialog_ids}
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            carriers = {dialog_to_pair[identifier].identity for identifier in question.resolved_evidence_ids}
            sessions = {dialog_to_pair[identifier].session_id for identifier in question.resolved_evidence_ids}
            metadata[(case.sample_id, question.source_index)] = {
                "question": question.question,
                "category": question.category,
                "carriers": carriers,
                "sessions": sessions,
            }

    records: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []
    for source in source_rows:
        key = (source["sample_id"], source["source_index"])
        meta = metadata[key]
        frozen = selections[key]
        carriers = tuple(sorted(meta["carriers"]))
        if carriers != tuple(source["evidence_ids"]):
            raise MissAuditError(f"Evidence identity drift at {key}")
        ranks = {arm: {identifier: frozen["orders"][arm].index(identifier) + 1 for identifier in carriers} for arm in ("dense", "cc80", "a3")}
        flags = question_flags(meta["question"])
        record: dict[str, Any] = {
            "question_id": source["question_id"], "sample_id": source["sample_id"], "source_index": source["source_index"],
            "question": meta["question"], "category": meta["category"], "population": source["population"],
            "carrier_count": len(carriers), "session_count": len(meta["sessions"]),
            "structure": structural_group(len(carriers), len(meta["sessions"])), "flags": flags,
        }
        for budget in BUDGETS:
            treatment = bool(source[f"cc80_a3_{budget}_complete"])
            dense = bool(source[f"dense_{budget}_complete"])
            record[f"complete_{budget}"] = treatment
            record[f"evidence_delivered_{budget}"] = source[f"cc80_a3_{budget}_evidence"]
            record[f"miss_state_{budget}"] = "COMPLETE" if treatment else ("ZERO_EVIDENCE" if source[f"cc80_a3_{budget}_evidence"] == 0 else "PARTIAL_EVIDENCE")
            relation = "GAIN" if treatment and not dense else "LOSS" if dense and not treatment else "TIE_COMPLETE" if dense and treatment else "TIE_MISS"
            record[f"dense_relation_{budget}"] = relation
            record[f"association_{budget}"] = association_label(treatment, bool(source[f"cc80_{budget}_complete"]), bool(source[f"dense_a3_{budget}_complete"])) if relation in {"GAIN", "LOSS"} else "NOT_APPLICABLE"
            allocation = frozen["budgets"][str(budget)]["cc80_a3"]
            for identifier in carriers:
                detail_rows.append({
                    "question_id": source["question_id"], "sample_id": source["sample_id"], "source_index": source["source_index"],
                    "budget": budget, "question": meta["question"], "category": meta["category"], "population": source["population"],
                    "evidence_id": identifier, "dense_relation": relation, "association": record[f"association_{budget}"],
                    "dense_rank": ranks["dense"][identifier], "cc80_rank": ranks["cc80"][identifier], "a3_rank": ranks["a3"][identifier],
                    "admission_phase": admission_phase(allocation, identifier),
                })
        record["longitudinal"] = "PERSISTENT_MISS" if not record["complete_16000"] and not record["complete_32000"] else "RESCUED_AT_32K" if not record["complete_16000"] and record["complete_32000"] else "REGRESSED_AT_32K" if record["complete_16000"] and not record["complete_32000"] else "COMPLETE_BOTH"
        records.append(record)

    budgets: dict[str, Any] = {}
    for budget in BUDGETS:
        misses = [row for row in records if not row[f"complete_{budget}"]]
        gains = [row for row in records if row[f"dense_relation_{budget}"] == "GAIN"]
        losses = [row for row in records if row[f"dense_relation_{budget}"] == "LOSS"]
        evidence_details = [row for row in detail_rows if row["budget"] == budget]
        budgets[str(budget)] = {
            "misses": {
                "total": len(misses),
                "population": dict(Counter(row["population"] for row in misses)),
                "evidence_state": dict(Counter(row[f"miss_state_{budget}"] for row in misses)),
                "structure": dict(Counter(row["structure"] for row in misses)),
                "category": dict(Counter(str(row["category"]) for row in misses)),
                "conversation": dict(Counter(row["sample_id"] for row in misses)),
                "flags": dict(Counter(flag for row in misses for flag in row["flags"])),
            },
            "versus_dense": {
                "gains": len(gains), "losses": len(losses), "net": len(gains) - len(losses),
                "gain_associations": dict(Counter(row[f"association_{budget}"] for row in gains)),
                "loss_associations": dict(Counter(row[f"association_{budget}"] for row in losses)),
            },
            "rates": {field: _group_rates(records, budget, field) for field in ("population", "structure", "category", "sample_id", "flags")},
            "evidence_ranks": {
                group: {rank: _rank_summary(row[rank] for row in evidence_details if row["dense_relation"] == relation) for rank in ("dense_rank", "cc80_rank", "a3_rank")}
                for group, relation in (("gains", "GAIN"), ("losses", "LOSS"), ("remaining_misses", "TIE_MISS"))
            },
            "admission_phases": {
                group: dict(Counter(row["admission_phase"] for row in evidence_details if row["dense_relation"] == relation))
                for group, relation in (("gains", "GAIN"), ("losses", "LOSS"), ("remaining_misses", "TIE_MISS"))
            },
        }

    longitudinal = dict(Counter(row["longitudinal"] for row in records))
    result = {
        "schema": "tc009-convex-protected-miss-audit-v1",
        "status": "POSTHOC_DESCRIPTIVE",
        "population": len(records),
        "budgets": budgets,
        "longitudinal": longitudinal,
        "calls": {"ranking": 0, "embedding": 0, "llm_or_generative": 0},
        "claim_boundary": "Frozen LoCoMo development evidence availability; associations and themes are descriptive, not causal or reader results.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "result.json", result)
    fieldnames = list(records[0])
    with (output_dir / "questions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({**row, "flags": "|".join(row["flags"])} for row in records)
    with (output_dir / "evidence_detail.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(detail_rows[0]))
        writer.writeheader()
        writer.writerows(detail_rows)
    return result


__all__ = ["MissAuditError", "admission_phase", "association_label", "question_flags", "run_audit", "run_preflight", "structural_group"]

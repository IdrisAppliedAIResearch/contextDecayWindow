from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Sequence

from src.analysis.e005_diversity_selection import _q11_payload_availability
from src.analysis.sr001_exploration import (
    REPO_ROOT,
    canonical_digest,
    load_q11_sources,
    sha256_file,
)
from src.analysis.sr001_gates import evaluate_gates
from src.retrieval_bakeoff.config import corpus_spec
from src.retrieval_bakeoff.corpus import load_raw_episodes
from src.retrieval_bakeoff.models import Candidate
from src.retrieval_mechanism_ledger.sr001 import episode_to_spans


COMPONENT_ROOT = REPO_ROOT / "experiments/components/retrieval_mechanism_ledger"
EXPLORATION = COMPONENT_ROOT / "artifacts/sr001_exploration/part1_process_2/exploration.json"
PREFLIGHT = COMPONENT_ROOT / "artifacts/sr001_preflight/preflight.json"
ANSWER_KEY = REPO_ROOT / "experiments/surveys/retrieval_bakeoff/holdout/answer_key_121.json"
DEFAULT_OUTPUT = COMPONENT_ROOT / "artifacts/sr001_measurement"

PREFLIGHT_COMMIT = "709387a2297e7a96d3bafe70990dbeb84bb1a33a"
PREFLIGHT_SHA256 = "fc0025c92794e2bef0a44fb10ca9c8fb8f95bdb5758008c87379095d415cffaa"
EXPLORATION_SHA256 = "abc349a47f2a40b7d195b3843a59cea2d4f48c974aa7bf8f049e0aca74c50926"


def assert_measurement_ready() -> dict[str, Any]:
    if sha256_file(PREFLIGHT) != PREFLIGHT_SHA256:
        raise AssertionError("Committed SR-001 Preflight bytes changed")
    if sha256_file(EXPLORATION) != EXPLORATION_SHA256:
        raise AssertionError("Committed SR-001 Part 1 bytes changed")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", PREFLIGHT_COMMIT, "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
    ).returncode != 0:
        raise AssertionError("SR-001 Preflight commit is not an ancestor")
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or not preflight["measurement_authorized"]:
        raise AssertionError("SR-001 measurement is not authorized by Preflight")
    return preflight


def build_unit_map(sources: Sequence[Candidate]) -> dict[str, dict[str, Any]]:
    units: dict[str, dict[str, Any]] = {}
    for source in sources:
        units[source.source_episode_id] = {
            "unit_id": source.source_episode_id,
            "source_episode_id": source.source_episode_id,
            "turn": source.turn_number,
            "unit_type": "episode",
            "role": "episode",
            "user_text": source.user_message,
            "assistant_text": source.assistant_message,
            "text": f"{source.user_message}\n{source.assistant_message}",
        }
        for span in episode_to_spans(source):
            units[span.candidate_id] = {
                "unit_id": span.candidate_id,
                "source_episode_id": span.source_episode_id,
                "turn": span.turn_number,
                "unit_type": "span",
                "role": span.role,
                "user_text": span.span_text if span.role == "user" else "",
                "assistant_text": span.span_text if span.role == "assistant" else "",
                "text": span.span_text,
            }
    return units


def fact_matches_units(
    fact: dict[str, Any], units: Sequence[dict[str, Any]]
) -> list[str]:
    turns = {int(value) for value in fact["source_turns"]}
    role = str(fact["source_role"])
    terms = [str(value).casefold() for value in fact["required_terms"]]
    matches = []
    for unit in units:
        if int(unit["turn"]) not in turns:
            continue
        text = unit[f"{role}_text"]
        if all(term in text.casefold() for term in terms):
            matches.append(str(unit["unit_id"]))
    return matches


def selected_units(
    record: dict[str, Any], arm: str, unit_map: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    ids = record[arm]["selected_unit_ids"]
    missing = [value for value in ids if value not in unit_map]
    if missing:
        raise AssertionError(f"Selected unit identities cannot be resolved: {missing[:3]}")
    return [unit_map[value] for value in ids]


def measure_holdouts(
    records: Sequence[dict[str, Any]],
    key: dict[str, Any],
    unit_map: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    query_key = {str(row["query_id"]): row for row in key["queries"]}
    query_rows = []
    fact_rows = []
    for record in records:
        if record["query_id"] == "q11":
            continue
        registered = query_key[record["query_id"]]
        arm_results = {}
        for arm in ("C0", "T1"):
            units = selected_units(record, arm, unit_map)
            matched = []
            for fact_id in registered["required_fact_ids"]:
                matches = fact_matches_units(key["facts"][fact_id], units)
                if matches:
                    matched.append(fact_id)
                fact_rows.append(
                    {
                        "query_id": record["query_id"],
                        "query_class": registered["query_class"],
                        "required_domains": registered["domains"],
                        "arm": arm,
                        "fact_id": fact_id,
                        "packed_available": bool(matches),
                        "match_unit_ids": matches,
                    }
                )
            required = len(registered["required_fact_ids"])
            arm_results[arm] = {
                "matched_fact_ids": matched,
                "matched_fact_count": len(matched),
                "required_fact_count": required,
                "packed_recall": len(matched) / required,
                "selected_unit_count": len(units),
                "selected_unique_source_count": len({row["source_episode_id"] for row in units}),
                "delivered_chars": record[arm]["delivered_chars"],
                "payload_sha256": record[arm]["payload_sha256"],
            }
        delta = arm_results["T1"]["packed_recall"] - arm_results["C0"]["packed_recall"]
        query_rows.append(
            {
                "query_id": record["query_id"],
                "query_class": registered["query_class"],
                "required_domains": registered["domains"],
                "required_fact_ids": registered["required_fact_ids"],
                "C0": arm_results["C0"],
                "T1": arm_results["T1"],
                "packed_recall_delta": delta,
                "direction": "GAIN" if delta > 0 else "LOSS" if delta < 0 else "TIE",
            }
        )
    aggregates = []
    groups = (
        ("class", sorted({row["query_class"] for row in query_rows})),
        ("domain", sorted({value for row in query_rows for value in row["required_domains"]})),
    )
    for group_type, values in groups:
        for value in values:
            group = [
                row for row in query_rows
                if (row["query_class"] == value if group_type == "class" else value in row["required_domains"])
            ]
            c0 = mean(row["C0"]["packed_recall"] for row in group)
            t1 = mean(row["T1"]["packed_recall"] for row in group)
            aggregates.append(
                {
                    "group_type": group_type,
                    "group": value,
                    "query_count": len(group),
                    "C0_macro_packed_recall": c0,
                    "T1_macro_packed_recall": t1,
                    "delta": t1 - c0,
                }
            )
    return query_rows, fact_rows, aggregates


def measure_q11(
    record: dict[str, Any], unit_map: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    arms = {}
    for arm in ("C0", "T1"):
        units = selected_units(record, arm, unit_map)
        payload = "\n".join(str(row["text"]) for row in units)
        availability = _q11_payload_availability(payload)
        arms[arm] = {
            **availability,
            "selected_unit_count": len(units),
            "selected_unique_source_count": len({row["source_episode_id"] for row in units}),
            "delivered_chars": record[arm]["delivered_chars"],
            "selection_payload_sha256": record[arm]["payload_sha256"],
            "measurement_text_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        }
    return arms


def write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        raise AssertionError(f"Cannot write empty CSV: {path}")
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {key: json.dumps(value, ensure_ascii=True, sort_keys=True) if isinstance(value, (list, dict)) else value for key, value in row.items()}
            )


def run(output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite measurement output: {output_dir}")
    preflight = assert_measurement_ready()
    exploration = json.loads(EXPLORATION.read_text(encoding="utf-8"))
    key = json.loads(ANSWER_KEY.read_text(encoding="utf-8"))
    holdout_sources = load_raw_episodes(corpus_spec("c121_l"))
    q11_sources, _ = load_q11_sources()
    holdout_units = build_unit_map(holdout_sources)
    q11_units = build_unit_map(q11_sources)
    records = exploration["records"]
    q11 = measure_q11(records[0], q11_units)
    query_rows, fact_rows, aggregates = measure_holdouts(records, key, holdout_units)
    losses = [row["query_id"] for row in query_rows if row["direction"] == "LOSS"]
    regressions = [f"{row['group_type']}:{row['group']}" for row in aggregates if row["delta"] < 0]
    retrieval_match = all(
        len(row["source_identities"]) == (119 if row["query_id"] == "q11" else 111)
        and row["C0"]["delivered_chars"] <= 32_000
        and row["T1"]["delivered_chars"] <= 32_000
        for row in records
    )
    c0_total = sum(row["C0"]["matched_fact_count"] for row in query_rows)
    t1_total = sum(row["T1"]["matched_fact_count"] for row in query_rows)
    gates = evaluate_gates(
        integrity_pass=preflight["status"] == "PASS",
        retrieval_identity_match=retrieval_match,
        q11_control_facts=q11["C0"]["fact_count"],
        q11_treatment_facts=q11["T1"]["fact_count"],
        holdout_control_facts=c0_total,
        holdout_treatment_facts=t1_total,
        targeted_losses=losses,
        aggregate_regressions=regressions,
    )
    result = {
        "study": "SR-001 extractive span representation",
        "status": "COMPLETE",
        "outcome": gates["disposition"],
        "outcome_ceiling": "CHARACTERIZED",
        "calls": {"embedding": 0, "model_generation": 0, "live_runs": 0},
        "inputs": {"preflight_commit": PREFLIGHT_COMMIT, "preflight_sha256": PREFLIGHT_SHA256, "exploration_sha256": EXPLORATION_SHA256, "answer_key_sha256": sha256_file(ANSWER_KEY)},
        "q11": q11,
        "holdout": {"query_count": len(query_rows), "C0_total_matched_facts": c0_total, "T1_total_matched_facts": t1_total, "gains": sum(row["direction"] == "GAIN" for row in query_rows), "losses": len(losses), "ties": sum(row["direction"] == "TIE" for row in query_rows), "loss_query_ids": losses},
        "aggregates": aggregates,
        "query_rows": query_rows,
        "fact_rows": fact_rows,
        "gates": gates,
        "ablation_run": False,
        "live_run": False,
    }
    result["canonical_digest"] = canonical_digest(result)
    output_dir.mkdir(parents=True)
    (output_dir / "results.json").write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    write_csv(output_dir / "query_comparisons.csv", query_rows)
    write_csv(output_dir / "targeted_fact_matrix.csv", fact_rows)
    write_csv(output_dir / "class_domain_aggregates.csv", aggregates)
    manifest = {
        "canonical_digest": result["canonical_digest"],
        "files": [
            {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in sorted(output_dir.iterdir())
        ],
    }
    (output_dir / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    result = run(parse_args().output)
    print(json.dumps({"outcome": result["outcome"], "canonical_digest": result["canonical_digest"]}, sort_keys=True))

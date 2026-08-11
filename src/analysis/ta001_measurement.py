from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Sequence

from episodic._render import render_stm_payload

from src.analysis.e005_diversity_selection import _q11_payload_availability
from src.analysis.ta001_exploration import (
    ANSWER_KEY_HASH_ONLY,
    BUDGET_CHARS,
    COMPONENT_ROOT,
    REPO_ROOT,
    load_episodes,
    sha256_file,
)
from src.retrieval_mechanism_ledger.ta001 import content_sha256


EXPLORATION = COMPONENT_ROOT / "artifacts" / "ta001_exploration" / "part1_process_1" / "exploration.json"
PREFLIGHT = COMPONENT_ROOT / "artifacts" / "ta001_preflight" / "preflight.json"
DEFAULT_OUTPUT = COMPONENT_ROOT / "artifacts" / "ta001_measurement"

PREFLIGHT_COMMIT = "a4b80e613090b151ef2402e27dd9d3e26c5c4276"
PREFLIGHT_SHA256 = "2da07934d9c46302b98d3d6f88647905f629eb410d85e3a8ae5a9dcff839d50f"
EXPLORATION_SHA256 = "a18c91d4251a5a6aca8e2fb6b37ed96e86e64798ea30e3db76ff2894399ffddf"
ARMS = ("C0", "T1")


def build_payload(hashes: Sequence[str], by_hash: dict[str, dict[str, Any]]) -> str:
    return render_stm_payload([], [by_hash[value] for value in hashes])


def fact_available(fact: dict[str, Any], episodes: Sequence[dict[str, Any]]) -> tuple[bool, list[str]]:
    matches = []
    source_turns = {int(value) for value in fact["source_turns"]}
    required = [str(value).casefold() for value in fact["required_terms"]]
    for episode in episodes:
        if int(episode["turn_number"]) not in source_turns:
            continue
        serialized = render_stm_payload([], [episode]).casefold()
        if all(term in serialized for term in required):
            matches.append(content_sha256(episode))
    return bool(matches), matches


def measure_holdout(
    records: Sequence[dict[str, Any]],
    key: dict[str, Any],
    by_hash: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    query_key = {row["query_id"]: row for row in key["queries"]}
    query_rows = []
    fact_rows = []
    for record in records:
        if record["query_id"] == "q11":
            continue
        registered = query_key[record["query_id"]]
        arm_metrics = {}
        for arm in ARMS:
            candidate_episodes = [by_hash[value] for value in record[arm]["candidate_content_sha256"]]
            packed_episodes = [by_hash[value] for value in record[arm]["selected_content_sha256"]]
            candidate_count = packed_count = 0
            for fact_id in registered["required_fact_ids"]:
                fact = key["facts"][fact_id]
                candidate_available, candidate_matches = fact_available(fact, candidate_episodes)
                packed_available, packed_matches = fact_available(fact, packed_episodes)
                candidate_count += candidate_available
                packed_count += packed_available
                fact_rows.append(
                    {
                        "query_id": record["query_id"],
                        "query_class": registered["query_class"],
                        "required_domains": registered["domains"],
                        "arm": arm,
                        "fact_id": fact_id,
                        "candidate_available": candidate_available,
                        "packed_available": packed_available,
                        "candidate_match_sha256": candidate_matches,
                        "packed_match_sha256": packed_matches,
                    }
                )
            required_count = len(registered["required_fact_ids"])
            arm_metrics[arm] = {
                "candidate_facts": candidate_count,
                "packed_facts": packed_count,
                "required_facts": required_count,
                "candidate_recall": candidate_count / required_count,
                "packed_recall": packed_count / required_count,
                "candidate_count": len(record[arm]["candidate_content_sha256"]),
                "selected_count": record[arm]["selected_count"],
                "delivered_chars": record[arm]["delivered_chars"],
                "candidate_sha256": record[arm]["candidate_sha256"],
                "selected_sha256": record[arm]["selected_sha256"],
                "payload_sha256": record[arm]["payload_sha256"],
            }
        delta = arm_metrics["T1"]["packed_recall"] - arm_metrics["C0"]["packed_recall"]
        query_rows.append(
            {
                "query_id": record["query_id"],
                "query_class": registered["query_class"],
                "required_domains": registered["domains"],
                "required_fact_ids": registered["required_fact_ids"],
                "C0": arm_metrics["C0"],
                "T1": arm_metrics["T1"],
                "packed_recall_delta": delta,
                "direction": "GAIN" if delta > 0 else "LOSS" if delta < 0 else "TIE",
            }
        )

    aggregate_rows = []
    for group_type, values in (
        ("class", sorted({row["query_class"] for row in query_rows})),
        ("domain", sorted({domain for row in query_rows for domain in row["required_domains"]})),
    ):
        for value in values:
            group = [
                row for row in query_rows
                if (row["query_class"] == value if group_type == "class" else value in row["required_domains"])
            ]
            aggregate_rows.append(
                {
                    "group_type": group_type,
                    "group": value,
                    "query_count": len(group),
                    "C0_macro_packed_recall": mean(row["C0"]["packed_recall"] for row in group),
                    "T1_macro_packed_recall": mean(row["T1"]["packed_recall"] for row in group),
                }
            )
    return query_rows, fact_rows, aggregate_rows


def measure_q11(record: dict[str, Any], by_hash: dict[str, dict[str, Any]]) -> dict[str, Any]:
    arms = {}
    for arm in ARMS:
        candidate_payload = build_payload(record[arm]["candidate_content_sha256"], by_hash)
        packed_payload = build_payload(record[arm]["selected_content_sha256"], by_hash)
        candidate = _q11_payload_availability(candidate_payload)
        packed = _q11_payload_availability(packed_payload)
        arms[arm] = {
            "candidate_fact_count": candidate["fact_count"],
            "packed_fact_count": packed["fact_count"],
            "candidate_per_domain": candidate["per_domain"],
            "packed_per_domain": packed["per_domain"],
            "candidate_items": candidate["items"],
            "packed_items": packed["items"],
            "candidate_count": len(record[arm]["candidate_content_sha256"]),
            "selected_count": record[arm]["selected_count"],
            "delivered_chars": record[arm]["delivered_chars"],
            "candidate_sha256": record[arm]["candidate_sha256"],
            "selected_sha256": record[arm]["selected_sha256"],
            "candidate_payload_sha256": hashlib.sha256(candidate_payload.encode("utf-8")).hexdigest(),
            "payload_sha256": hashlib.sha256(packed_payload.encode("utf-8")).hexdigest(),
            "candidate_payload": candidate_payload,
            "packed_payload": packed_payload,
        }
    return arms


def evaluate_gates(
    q11: dict[str, Any],
    query_rows: Sequence[dict[str, Any]],
    aggregate_rows: Sequence[dict[str, Any]],
    *,
    integrity_pass: bool,
) -> dict[str, Any]:
    losses = [row["query_id"] for row in query_rows if row["direction"] == "LOSS"]
    aggregate_regressions = [
        f"{row['group_type']}:{row['group']}"
        for row in aggregate_rows
        if row["T1_macro_packed_recall"] < row["C0_macro_packed_recall"]
    ]
    gates = [
        {
            "gate": "G1",
            "pass": integrity_pass,
            "evidence": "Committed passing Preflight and exact input identities",
            "failure_disposition": "INTEGRITY_STOP",
        },
        {
            "gate": "G2",
            "pass": all(q11[arm]["candidate_count"] == 15 and q11[arm]["delivered_chars"] <= BUDGET_CHARS for arm in ARMS)
            and all(row[arm]["candidate_count"] == 15 and row[arm]["delivered_chars"] <= BUDGET_CHARS for row in query_rows for arm in ARMS),
            "evidence": {"candidate_quota": 15, "budget_chars": BUDGET_CHARS},
            "failure_disposition": "UNMATCHED_OPPORTUNITY",
        },
        {
            "gate": "G3",
            "pass": q11["T1"]["candidate_fact_count"] >= q11["C0"]["candidate_fact_count"] + 1
            and q11["T1"]["packed_fact_count"] >= q11["C0"]["packed_fact_count"] + 1,
            "evidence": {
                "C0_candidate": q11["C0"]["candidate_fact_count"],
                "T1_candidate": q11["T1"]["candidate_fact_count"],
                "C0_packed": q11["C0"]["packed_fact_count"],
                "T1_packed": q11["T1"]["packed_fact_count"],
            },
            "failure_disposition": "NO_BROAD_GAIN",
        },
        {
            "gate": "G4",
            "pass": q11["T1"]["candidate_per_domain"]["art"] == 4 and q11["T1"]["packed_per_domain"]["art"] == 4,
            "evidence": {"candidate_art": q11["T1"]["candidate_per_domain"]["art"], "packed_art": q11["T1"]["packed_per_domain"]["art"]},
            "failure_disposition": "ART_NOT_DELIVERED",
        },
        {
            "gate": "G5",
            "pass": not losses and not aggregate_regressions,
            "evidence": {"losses": losses, "aggregate_regressions": aggregate_regressions},
            "failure_disposition": "TARGETED_REGRESSION",
        },
    ]
    first_failure = next((row for row in gates if not row["pass"]), None)
    return {
        "gates": gates,
        "first_failure": first_failure["gate"] if first_failure else None,
        "disposition": first_failure["failure_disposition"] if first_failure else "ADJACENCY_BRIDGE_OFFLINE_ELIGIBLE",
        "offline_gates_pass": first_failure is None,
    }


def flatten(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        output.append({key: json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) if isinstance(value, (list, dict)) else value for key, value in row.items()})
    return output


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    materialized = flatten(rows)
    if not materialized:
        raise AssertionError(f"Refusing empty CSV: {path.name}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(materialized[0]))
        writer.writeheader()
        writer.writerows(materialized)


def run(output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite measurement output: {output_dir}")
    if sha256_file(PREFLIGHT) != PREFLIGHT_SHA256 or sha256_file(EXPLORATION) != EXPLORATION_SHA256:
        raise AssertionError("Committed gate input identity changed")
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or preflight["measurement_boundary"] != "SEALED":
        raise AssertionError("Measurement requires a committed passing Preflight")
    subprocess.run(("git", "merge-base", "--is-ancestor", PREFLIGHT_COMMIT, "HEAD"), cwd=REPO_ROOT, check=True)

    exploration = json.loads(EXPLORATION.read_text(encoding="utf-8"))
    key = json.loads(ANSWER_KEY_HASH_ONLY.read_text(encoding="utf-8"))
    episodes = load_episodes(119)
    by_hash = {content_sha256(episode): episode for episode in episodes}
    q11 = measure_q11(exploration["records"][0], by_hash)
    query_rows, fact_rows, aggregate_rows = measure_holdout(exploration["records"], key, by_hash)
    gate_result = evaluate_gates(q11, query_rows, aggregate_rows, integrity_pass=True)
    outcomes = {direction: sum(row["direction"] == direction for row in query_rows) for direction in ("GAIN", "LOSS", "TIE")}
    result = {
        "study": "TA-001 temporal-adjacency bridge",
        "status": "COMPLETE",
        "outcome_ceiling": "CHARACTERIZED",
        "preflight_commit": PREFLIGHT_COMMIT,
        "preflight_sha256": PREFLIGHT_SHA256,
        "implementation_sha256": sha256_file(Path(__file__).resolve()),
        "calls": {"embedding": 0, "model_generation": 0, "live_runs": 0},
        "q11": {arm: {key: value for key, value in row.items() if not key.endswith("payload")} for arm, row in q11.items()},
        "targeted_queries": query_rows,
        "targeted_fact_rows": fact_rows,
        "targeted_aggregates": aggregate_rows,
        "targeted_outcomes": outcomes,
        **gate_result,
        "ablation_authorized_by_result": gate_result["offline_gates_pass"],
        "full_live_run_authorized": False,
    }
    output_dir.mkdir(parents=True)
    (output_dir / "payloads").mkdir()
    for arm in ARMS:
        (output_dir / "payloads" / f"q11_{arm}_candidate.txt").write_text(q11[arm]["candidate_payload"], encoding="utf-8", newline="\n")
        (output_dir / "payloads" / f"q11_{arm}_packed.txt").write_text(q11[arm]["packed_payload"], encoding="utf-8", newline="\n")
    results_path = output_dir / "results.json"
    results_path.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    write_csv(output_dir / "query_comparisons.csv", query_rows)
    write_csv(output_dir / "targeted_fact_matrix.csv", fact_rows)
    q11_rows = []
    for arm in ARMS:
        for stage in ("candidate", "packed"):
            q11_rows.extend({"arm": arm, "stage": stage, **row} for row in q11[arm][f"{stage}_items"])
    write_csv(output_dir / "q11_fact_matrix.csv", q11_rows)
    manifest_rows = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            manifest_rows.append({"path": path.relative_to(output_dir).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {"files": manifest_rows, "result_sha256": sha256_file(results_path)}
    (output_dir / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({"disposition": result["disposition"], "offline_gates_pass": result["offline_gates_pass"]}, sort_keys=True))

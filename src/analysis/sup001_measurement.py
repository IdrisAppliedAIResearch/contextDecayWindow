from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.analysis.sup001_benchmark import STUDY_ROOT, canonical_digest
from src.analysis.sup001_control import CONTROL_PATH
from src.analysis.sup001_preflight import PREFLIGHT_PATH
from src.analysis.sup001_treatment import TREATMENT_PATH
from src.analysis.sup001_vectors import MANIFEST_PATH, MECHANISM_PATH, sha256_file
from src.biological_memory.supersession import content_sha256


KEY_PATH = STUDY_ROOT / "artifacts" / "sup001_corpus" / "SEALED_KEY_DO_NOT_OPEN.json"
MEASUREMENT_ROOT = STUDY_ROOT / "artifacts" / "sup001_measurement"
MEASUREMENT_PATH = MEASUREMENT_ROOT / "measurement.json"


def evaluate_gates(metrics: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    definitions = (
        ("G1", "integrity", bool(metrics["integrity"]), "INTEGRITY_STOP"),
        (
            "G2",
            "current-value retrieval",
            metrics["t1_current_only"] == 64 and metrics["current_only_gain"] >= 16,
            "CURRENT_VALUE_NOT_SURFACED",
        ),
        (
            "G3",
            "unchanged safety",
            metrics["unchanged_losses"] == 0,
            "UNCHANGED_FACT_REGRESSION",
        ),
        (
            "G4",
            "history recovery and natural silence",
            metrics["exact_lineages"] == 64 and metrics["natural_stale_selected"] == 0,
            "LINEAGE_OR_SILENCE_FAILURE",
        ),
        (
            "G5",
            "provenance and invariants",
            bool(metrics["provenance"]),
            "PROVENANCE_OR_INVARIANT_FAILURE",
        ),
    )
    rows: list[dict[str, Any]] = []
    stopped = False
    disposition = "SUPERSESSION_OFFLINE_ELIGIBLE"
    for gate, name, passed, failure in definitions:
        if stopped:
            rows.append({"gate": gate, "name": name, "status": "NOT_EVALUATED"})
            continue
        rows.append({"gate": gate, "name": name, "status": "PASS" if passed else "FAIL"})
        if not passed:
            stopped = True
            disposition = failure
    return rows, disposition


def _query_measurement(
    key_row: dict[str, Any], control_query: dict[str, Any], treatment_query: dict[str, Any]
) -> dict[str, Any]:
    control_ids = list(control_query["selected_ids"])
    treatment_ids = list(treatment_query["selected_ids"])
    current = str(key_row["current_sha256"])
    stale = [str(value) for value in key_row["stale_sha256"]]
    control_current = current in control_ids
    treatment_current = current in treatment_ids
    control_stale = [value for value in stale if value in control_ids]
    treatment_stale = [value for value in stale if value in treatment_ids]
    result = {
        "query_id": key_row["query_id"],
        "kind": key_row["kind"],
        "domain": key_row["domain"],
        "control": {
            "selected_ids": control_ids,
            "current_present": control_current,
            "stale_present": control_stale,
            "current_rank": control_ids.index(current) + 1 if control_current else None,
            "serialized_chars": control_query["serialized_chars"],
            "payload_sha256": control_query["payload_sha256"],
        },
        "treatment": {
            "selected_ids": treatment_ids,
            "current_present": treatment_current,
            "stale_present": treatment_stale,
            "current_rank": treatment_ids.index(current) + 1 if treatment_current else None,
            "serialized_chars": treatment_query["serialized_chars"],
            "payload_sha256": treatment_query["payload_sha256"],
        },
    }
    if key_row["kind"] == "updated":
        result["control"]["current_only"] = control_current and not control_stale
        result["treatment"]["current_only"] = treatment_current and not treatment_stale
    else:
        result["control"]["target_present"] = control_current
        result["treatment"]["target_present"] = treatment_current
        result["target_loss"] = control_current and not treatment_current
    return result


def analyze(output_path: Path = MEASUREMENT_PATH) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite SUP-001 measurement: {output_path}")
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or not preflight["measurement_authorized"]:
        raise RuntimeError("Sealed measurement is blocked until PF1-PF10 passes")
    mechanism = json.loads(MECHANISM_PATH.read_text(encoding="utf-8"))
    control = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    treatment = json.loads(TREATMENT_PATH.read_text(encoding="utf-8"))
    vector_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    key = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    control_by_query = {row["query_id"]: row for row in control["queries"]}
    treatment_by_query = {row["query_id"]: row for row in treatment["queries"]}
    query_rows = [
        _query_measurement(row, control_by_query[row["query_id"]], treatment_by_query[row["query_id"]])
        for row in key["rows"]
    ]
    treatment_lineages = {row["memory_key"]: row["records"] for row in treatment["lineages"]}
    history_rows = []
    for expected in key["history_queries"]:
        actual = treatment_lineages[expected["memory_key"]]
        actual_ids = [row["episode_sha256"] for row in actual]
        expected_ids = list(expected["lineage_sha256"])
        exact = bool(
            actual_ids == expected_ids
            and [row["accessibility"] for row in actual] == [0.0, 0.0, 1.0]
            and all(row["episode_sha256"] == row["content_hash_round_trip"] for row in actual)
            and all(
                row["supersedes"] == (actual_ids[index - 1] if index else None)
                and row["superseded_by"] == (actual_ids[index + 1] if index + 1 < len(actual_ids) else None)
                for index, row in enumerate(actual)
            )
        )
        history_rows.append(
            {
                "history_query_id": expected["history_query_id"],
                "memory_key": expected["memory_key"],
                "expected_ids": expected_ids,
                "actual_records": actual,
                "exact": exact,
            }
        )
    updated = [row for row in query_rows if row["kind"] == "updated"]
    unchanged = [row for row in query_rows if row["kind"] == "unchanged"]
    mechanism_round_trips = all(
        row["episode_sha256"] == content_sha256(row["user"], row["assistant"])
        for row in mechanism["episodes"]
    )
    vector_rows = [row for row in vector_manifest["vectors"] if row["kind"] == "episode"]
    integrity = bool(
        preflight["status"] == "PASS"
        and control["query_count"] == treatment["query_count"] == len(key["rows"]) == 96
        and treatment["episode_count"] == len(mechanism["episodes"]) == 256
        and treatment["top_k"] == control["top_k"] == 8
        and treatment["budget_chars"] == control["budget_chars"] == 32_000
        and all(len(row["control"]["selected_ids"]) == len(row["treatment"]["selected_ids"]) == 8 for row in query_rows)
        and all(row["control"]["serialized_chars"] <= 32_000 and row["treatment"]["serialized_chars"] <= 32_000 for row in query_rows)
    )
    provenance = bool(
        treatment["ledger_validation"] == {"record_count": 192, "lineage_count": 64, "accessible_count": 64, "silent_count": 128}
        and treatment["read_purity"]["state_unchanged"]
        and treatment["immutability"]["text_or_vector_rewrite_operations"] == 0
        and treatment["immutability"]["episode_identity_sequence"] == [row["episode_sha256"] for row in mechanism["episodes"]]
        and mechanism_round_trips
        and len(vector_rows) == 256
        and len({row["vector_sha256"] for row in vector_rows}) == 256
        and all(row["exact"] for row in history_rows)
    )
    metrics = {
        "integrity": integrity,
        "control_current_only": sum(row["control"]["current_only"] for row in updated),
        "t1_current_only": sum(row["treatment"]["current_only"] for row in updated),
        "current_only_gain": sum(row["treatment"]["current_only"] for row in updated) - sum(row["control"]["current_only"] for row in updated),
        "control_unchanged_targets": sum(row["control"]["target_present"] for row in unchanged),
        "t1_unchanged_targets": sum(row["treatment"]["target_present"] for row in unchanged),
        "unchanged_losses": sum(row["target_loss"] for row in unchanged),
        "exact_lineages": sum(row["exact"] for row in history_rows),
        "natural_stale_selected": sum(len(row["treatment"]["stale_present"]) for row in updated),
        "provenance": provenance,
    }
    gates, disposition = evaluate_gates(metrics)
    result = {
        "study": "SUP-001",
        "stage": "sealed offline measurement",
        "status": "COMPLETE",
        "disposition": disposition,
        "metrics": metrics,
        "gates": gates,
        "queries": query_rows,
        "history_queries": history_rows,
        "domain_summary": {
            domain: {
                "updated": sum(row["kind"] == "updated" and row["domain"] == domain for row in query_rows),
                "t1_current_only": sum(row["kind"] == "updated" and row["domain"] == domain and row["treatment"]["current_only"] for row in query_rows),
                "unchanged": sum(row["kind"] == "unchanged" and row["domain"] == domain for row in query_rows),
                "unchanged_losses": sum(row["kind"] == "unchanged" and row["domain"] == domain and row["target_loss"] for row in query_rows),
            }
            for domain in ("preference", "location", "schedule", "quantity")
        },
        "inputs": {
            "preflight_sha256": sha256_file(PREFLIGHT_PATH),
            "mechanism_sha256": sha256_file(MECHANISM_PATH),
            "control_sha256": sha256_file(CONTROL_PATH),
            "treatment_sha256": sha256_file(TREATMENT_PATH),
            "vector_manifest_sha256": sha256_file(MANIFEST_PATH),
            "sealed_key_sha256": sha256_file(KEY_PATH),
            "source_sha256": sha256_file(Path(__file__)),
        },
        "ablation_authorized": disposition == "SUPERSESSION_OFFLINE_ELIGIBLE",
        "full_live_run_authorized": False,
    }
    result["canonical_digest"] = canonical_digest(result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result

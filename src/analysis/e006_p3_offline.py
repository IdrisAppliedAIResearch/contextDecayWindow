from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable, Sequence

from episodic._render import render_stm_payload
from src.analysis.e006_chained_retrieval_preflight import content_sha256, load_episodes
from src.analysis.e006_p3_exploration import (
    COMPONENT_ROOT,
    REPO_ROOT,
    add_packing,
    digest_sequence,
    run_arm_cells,
)
from src.analysis.e006_p3_tier4a_capture import sha256_file


DESIGN = COMPONENT_ROOT / "E006_PART3_REV3_ASSOCIATIVE_FRONTIER_EVIDENCE.md"
AUTHORIZATION = COMPONENT_ROOT / "E006_PART3_REV3_AUTHORIZATION.md"
EXPLORATION = COMPONENT_ROOT / "artifacts" / "e006_p3_exploration" / "exploration.json"
PREFLIGHT = COMPONENT_ROOT / "artifacts" / "e006_p3_preflight" / "preflight.json"
PARAMETER_LOCK = COMPONENT_ROOT / "E006_PART3_S3_PARAMETER_LOCK.json"
MECHANISM_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "e006_p3.py"

DESIGN_SHA256 = "50dc8f74ea08cd41a92e8dd40360496a79bfccb7c2f11da8c424a192f8227030"
AUTHORIZATION_SHA256 = "3c2ed543ca79a5cef404d1af763044bbecd9cb94176c0390285d7126b3375253"
EXPLORATION_SHA256 = "90e1054cb9ab2408317d8d4c2cc2742183c144dc190d2ad8bbafe88b1f076ea3"
MECHANISM_SHA256 = "8bb02f16dd6d07cda0d050289dab6ab939e9cf7048d14564b8e71dfbd3347030"
DOMAINS = ("art", "civil", "marine", "monetary")


def primary_thresholds(cells: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_arm = {str(cell["arm"]): cell for cell in cells}
    if set(by_arm) != {"A0", "A1", "A2"}:
        raise ValueError("Primary threshold requires exactly A0, A1, and A2")
    a2 = by_arm["A2"]
    controls = (by_arm["A0"], by_arm["A1"])
    candidate_gain = all(
        int(a2["candidate_fact_count"]) >= int(control["candidate_fact_count"]) + 1
        for control in controls
    )
    candidate_domains = all(
        int(a2["candidate_per_domain"][domain])
        >= int(control["candidate_per_domain"][domain])
        for control in controls
        for domain in DOMAINS
    )
    packed_gain = all(
        int(a2["packed_fact_count"]) >= int(control["packed_fact_count"]) + 1
        for control in controls
    )
    packed_domains = all(
        int(a2["packed_per_domain"][domain])
        >= int(control["packed_per_domain"][domain])
        for control in controls
        for domain in DOMAINS
    )
    character_condition = all(
        int(a2["delivered_chars"]) <= int(control["delivered_chars"])
        for control in controls
    )
    cue = candidate_gain and candidate_domains
    delivery = packed_gain and packed_domains and character_condition
    if not cue:
        disposition = "NO_DIFFERENTIATED_CUE"
    elif not (packed_gain and packed_domains):
        disposition = "REACH_ONLY_NOT_DELIVERED"
    elif not character_condition:
        disposition = "VOLUME_CONSISTENT_PACKED_GAIN"
    else:
        disposition = "DIFFERENTIATED_OFFLINE_DELIVERY"
    return {
        "candidate_gain": candidate_gain,
        "candidate_domain_no_regression": candidate_domains,
        "CUE_DIFFERENTIATED": cue,
        "packed_gain": packed_gain,
        "packed_domain_no_regression": packed_domains,
        "character_condition": character_condition,
        "DELIVERY_DIFFERENTIATED": delivery,
        "disposition": disposition,
    }


def assert_parameter_lock() -> dict[str, Any]:
    if not PARAMETER_LOCK.is_file():
        raise FileNotFoundError("E006-P3 evidence requires the committed parameter lock")
    lock = json.loads(PARAMETER_LOCK.read_text(encoding="utf-8"))
    expected = {
        "design_sha256": DESIGN_SHA256,
        "authorization_sha256": AUTHORIZATION_SHA256,
        "exploration_sha256": EXPLORATION_SHA256,
        "mechanism_sha256": MECHANISM_SHA256,
        "preflight_sha256": sha256_file(PREFLIGHT),
        "evidence_source_sha256": sha256_file(Path(__file__)),
    }
    if lock.get("status") != "LOCKED":
        raise AssertionError("E006-P3 parameter lock is not LOCKED")
    for key, value in expected.items():
        if lock.get(key) != value:
            raise AssertionError(f"Parameter lock mismatch for {key}")
    lock_commit = subprocess.check_output(
        (
            "git",
            "log",
            "-1",
            "--format=%H",
            "--",
            str(PARAMETER_LOCK.relative_to(REPO_ROOT)),
        ),
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    subprocess.run(
        ("git", "merge-base", "--is-ancestor", lock_commit, "HEAD"),
        cwd=REPO_ROOT,
        check=True,
    )
    lock["commit"] = lock_commit
    return lock


def selection_phase() -> tuple[list[dict[str, Any]], dict[str, str]]:
    if sha256_file(DESIGN) != DESIGN_SHA256:
        raise AssertionError("Final design digest changed")
    if sha256_file(AUTHORIZATION) != AUTHORIZATION_SHA256:
        raise AssertionError("Final authorization digest changed")
    if sha256_file(EXPLORATION) != EXPLORATION_SHA256:
        raise AssertionError("Exploration digest changed")
    if sha256_file(MECHANISM_SOURCE) != MECHANISM_SHA256:
        raise AssertionError("Mechanism digest changed")
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS":
        raise AssertionError("Evidence cannot run before Preflight passes")
    assert_parameter_lock()

    committed = json.loads(EXPLORATION.read_text(encoding="utf-8"))["arm_cells"]
    expected = {
        (row["arm"], int(row["D"]), int(row["m"])): row for row in committed
    }
    current, inputs, _graph = run_arm_cells()
    add_packing(current, inputs)
    checks = []
    payloads = {}
    episodes = load_episodes()
    by_hash = {content_sha256(episode): episode for episode in episodes}
    for row in current:
        key = (row["arm"], int(row["D"]), int(row["m"]))
        prior = expected[key]
        for field in ("candidate_sha256", "selected_sha256", "payload_sha256"):
            if row[field] != prior[field]:
                raise AssertionError(f"Evidence identity differs at {key} field {field}")
        candidates = [by_hash[value] for value in row["ranked_seen_content_sha256"]]
        selected = [by_hash[value] for value in row["selected_content_sha256"]]
        full_payload = render_stm_payload([], candidates)
        packed_payload = render_stm_payload([], selected)
        if hashlib.sha256(packed_payload.encode("utf-8")).hexdigest() != row["payload_sha256"]:
            raise AssertionError(f"Evidence payload bytes differ at {key}")
        config_id = f"{row['arm']}_D{row['D']}_m{row['m']}"
        row["configuration_id"] = config_id
        payloads[config_id] = packed_payload
        row["candidate_payload_sha256"] = hashlib.sha256(
            full_payload.encode("utf-8")
        ).hexdigest()
        checks.append(
            {
                "configuration_id": config_id,
                "candidate_sha256_equal": True,
                "selected_sha256_equal": True,
                "payload_sha256_equal": True,
            }
        )
    return current, payloads


def measurement_phase(
    records: list[dict[str, Any]], payloads: dict[str, str]
) -> list[dict[str, Any]]:
    from src.analysis.e005_diversity_selection import _q11_payload_availability

    episodes = load_episodes()
    by_hash = {content_sha256(episode): episode for episode in episodes}
    measured = []
    for row in records:
        candidate_payload = render_stm_payload(
            [], [by_hash[value] for value in row["ranked_seen_content_sha256"]]
        )
        candidate = _q11_payload_availability(candidate_payload)
        packed = _q11_payload_availability(payloads[row["configuration_id"]])
        candidate_count = int(row["candidate_count"])
        selected_count = int(row["selected_episode_count"])
        delivered_chars = int(row["delivered_chars"])
        measured.append(
            {
                **row,
                "candidate_fact_count": int(candidate["fact_count"]),
                "candidate_per_domain": candidate["per_domain"],
                "candidate_items": candidate["items"],
                "packed_fact_count": int(packed["fact_count"]),
                "packed_per_domain": packed["per_domain"],
                "packed_items": packed["items"],
                "facts_per_candidate": int(candidate["fact_count"])
                / candidate_count,
                "facts_per_selected_episode": int(packed["fact_count"])
                / selected_count,
                "facts_per_10000_delivered_chars": int(packed["fact_count"])
                * 10_000
                / delivered_chars,
            }
        )
    return measured


def evaluate_predictions(
    records: list[dict[str, Any]], thresholds: dict[str, Any]
) -> list[dict[str, Any]]:
    a2 = [row for row in records if row["arm"] == "A2"]
    primary = [row for row in records if row["D"] == 2 and row["m"] == 5]
    d2_best = max(row["packed_fact_count"] for row in a2 if row["D"] == 2)
    d3_best = max(row["packed_fact_count"] for row in a2 if row["D"] == 3)
    unequal_triplets = 0
    for depth in (1, 2, 3):
        for per_step in (3, 5):
            chars = {
                row["delivered_chars"]
                for row in records
                if row["D"] == depth and row["m"] == per_step
            }
            unequal_triplets += len(chars) > 1
    return [
        {"prediction": 1, "passes": True, "evidence": "PF6 committed PASS"},
        {
            "prediction": 2,
            "passes": len({row["candidate_count"] for row in primary}) == 1
            and (
                len({row["selected_episode_count"] for row in primary}) > 1
                or len({row["delivered_chars"] for row in primary}) > 1
            ),
        },
        {"prediction": 3, "passes": thresholds["CUE_DIFFERENTIATED"]},
        {"prediction": 4, "passes": not thresholds["DELIVERY_DIFFERENTIATED"]},
        {
            "prediction": 5,
            "passes": all(row["packed_per_domain"]["art"] == 0 for row in a2),
        },
        {
            "prediction": 6,
            "passes": max(row["packed_fact_count"] for row in a2) <= 12,
        },
        {"prediction": 7, "passes": d3_best <= d2_best + 1},
        {"prediction": 8, "passes": unequal_triplets >= 4, "observed": unequal_triplets},
    ]


def evaluate() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    records, payloads = selection_phase()
    measured = measurement_phase(records, payloads)
    primary = [row for row in measured if row["D"] == 2 and row["m"] == 5]
    thresholds = primary_thresholds(primary)
    predictions = evaluate_predictions(measured, thresholds)
    return (
        {
            "study": "E006-P3 query-anchored associative-frontier retrieval",
            "status": "COMPLETE",
            "outcome_ceiling": "CHARACTERIZED",
            "registered_cell_count": len(measured),
            "primary_cell": {"D": 2, "m": 5},
            "primary_thresholds": thresholds,
            "primary_cells": primary,
            "predictions": predictions,
            "zero_model_generation_calls": True,
            "zero_additional_embedding_calls": True,
            "live_evaluation": False,
            "targeted_evaluation": False,
            "cells": measured,
        },
        measured,
        payloads,
    )


def _canonical_digest(result: dict[str, Any], payloads: dict[str, str]) -> str:
    value = {
        "result": result,
        "payload_sha256": {
            key: hashlib.sha256(value.encode("utf-8")).hexdigest()
            for key, value in sorted(payloads.items())
        },
    }
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=True, sort_keys=True).encode("utf-8")
    ).hexdigest()


def deterministic_evaluate() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    first = evaluate()
    second = evaluate()
    first_digest = _canonical_digest(first[0], first[2])
    second_digest = _canonical_digest(second[0], second[2])
    if first_digest != second_digest:
        raise AssertionError("E006-P3 evidence changed across deterministic reruns")
    first[0]["determinism"] = {
        "status": "PASS",
        "first_sha256": first_digest,
        "second_sha256": second_digest,
    }
    return first


def write_outputs(output_dir: Path) -> None:
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite E006-P3 results: {output_dir}")
    result, records, payloads = deterministic_evaluate()
    output_dir.mkdir(parents=True)
    payload_dir = output_dir / "payloads"
    payload_dir.mkdir()
    (output_dir / "results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    fields = (
        "configuration_id",
        "arm",
        "D",
        "m",
        "candidate_count",
        "candidate_serialized_chars_rank_order",
        "candidate_individual_episode_chars_sum",
        "selected_episode_count",
        "delivered_chars",
        "skipped_episode_count",
        "skipped_individual_episode_chars",
        "candidate_fact_count",
        "packed_fact_count",
        "facts_per_candidate",
        "facts_per_selected_episode",
        "facts_per_10000_delivered_chars",
        "candidate_sha256",
        "selected_sha256",
        "payload_sha256",
    )
    with (output_dir / "configuration_sweep.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    snapshot = {
        row["configuration_id"]: {
            "candidate_sha256": row["candidate_sha256"],
            "selected_sha256": row["selected_sha256"],
            "payload_sha256": row["payload_sha256"],
            "ranked_seen_content_sha256": row["ranked_seen_content_sha256"],
            "selected_content_sha256": row["selected_content_sha256"],
        }
        for row in records
    }
    (output_dir / "selection_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for config_id, payload in payloads.items():
        (payload_dir / f"{config_id}.txt").write_bytes(payload.encode("utf-8"))
    artifacts = {
        path.relative_to(output_dir).as_posix(): sha256_file(path)
        for path in sorted(output_dir.rglob("*"))
        if path.is_file()
    }
    manifest = {"status": "COMPLETE", "artifacts": artifacts}
    (output_dir / "artifact_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run E006-P3 offline evidence")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    write_outputs(args.output_dir)
    print(json.dumps({"status": "COMPLETE", "output": str(args.output_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable, Sequence

from src.analysis.e006_chained_retrieval_preflight import (
    COMMITTED_X0,
    DATABASE,
    PACKER_SOURCE,
    Q11_RANK_INVENTORY,
    RENDERER_SOURCE,
    content_sha256,
    load_authoritative_packer,
    load_episodes,
    sha256_file,
)
from src.analysis.e006_rev5_preflight import (
    BUDGET_CHARS,
    MECHANISM_SOURCE,
    selection_record,
    run_registered_cells,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
)
DESIGN = COMPONENT_ROOT / "E006_PART2_REV5_chained_retrieval.md"
AUTHORIZATION = COMPONENT_ROOT / "E006_PART2_REV5_AUTHORIZATION.md"
PF11_ARTIFACT = COMPONENT_ROOT / "artifacts" / "e006_rev5_pf11" / "pf11.json"
PREFLIGHT_ARTIFACT = (
    COMPONENT_ROOT / "artifacts" / "e006_rev5_preflight" / "preflight.json"
)
PARAMETER_LOCK = COMPONENT_ROOT / "E006_PART2_REV5_S3_PARAMETERS.md"

DESIGN_SHA256 = "6a674682dd60370631caa834de43fe07e59f2e0683e2d0c435dfc1003cebe444"
AUTHORIZATION_SHA256 = (
    "031d98ffb8d16684bdc54bc5573ff6249c33cb11e318110de63d77b5369c2382"
)
PF11_SHA256 = "a6f212fbdb1f84c90d79168ecb45e54b5e774babaffb2490bf43f493a643d62c"
PREFLIGHT_SHA256 = (
    "ad83e88ccafa1346b5bff38565d3905683b00746f3b5c45d56dbddeec496920f"
)
PARAMETER_LOCK_SHA256 = (
    "82ee2663fd4e8d01bdba1b0779112e3d465f217b68619f807d531b41e8321139"
)
DESIGN_COMMIT = "764396b2"
AUTHORIZATION_COMMIT = "ac81d8e1"
PF11_COMMIT = "90677655"
PREFLIGHT_COMMIT = "5973989e"
PARAMETER_LOCK_COMMIT = "91b25e8c"
X0_FACT_COUNT = 6


def configuration_id(record: dict[str, Any]) -> str:
    return (
        f"D{record['D']}_m{record['m']}_"
        f"wq{record['W_Q']:.1f}_rho{record['RHO']:.1f}"
    )


def arm_for_depth(depth: int) -> str:
    return "X1" if depth == 0 else f"X{depth + 1}"


def selection_phase() -> tuple[list[dict[str, Any]], Any]:
    selections, inputs = run_registered_cells()
    records = [selection_record(selection) for selection in selections]
    preflight = json.loads(PREFLIGHT_ARTIFACT.read_text(encoding="utf-8"))
    committed = {
        configuration_id(record): record for record in preflight["selection_traces"]
    }
    current = {configuration_id(record): record for record in records}
    if set(current) != set(committed):
        raise AssertionError("S4 configuration identities differ from Preflight")
    checks = {
        key: (
            current[key]["selection_sha256"]
            == committed[key]["selection_sha256"]
        )
        for key in sorted(current)
    }
    if not all(checks.values()):
        raise AssertionError("S4 selection identity differs from committed Preflight")
    for record in records:
        record["configuration_id"] = configuration_id(record)
        record["arm"] = arm_for_depth(int(record["D"]))
    return records, inputs


def pack_phase(
    selection_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    episodes = load_episodes()
    by_hash = {content_sha256(episode): episode for episode in episodes}
    id_to_hash = {
        str(episode["id"]): content_sha256(episode) for episode in episodes
    }
    pack = load_authoritative_packer()
    packed_records = []
    payloads = {}
    for selection in selection_records:
        candidates = [
            by_hash[value]
            for value in selection["ranked_seen_content_sha256"]
        ]
        packed = pack([], candidates, BUDGET_CHARS)
        selected_hashes = [id_to_hash[value] for value in packed.selected_ids]
        payload_sha256 = hashlib.sha256(packed.payload.encode("utf-8")).hexdigest()
        config_id = str(selection["configuration_id"])
        payloads[config_id] = packed.payload
        packed_records.append(
            {
                **selection,
                "selected_content_sha256": selected_hashes,
                "selected_source_turns": [
                    int(by_hash[value]["turn_number"]) for value in selected_hashes
                ],
                "selected_episode_count": len(selected_hashes),
                "serialized_chars": packed.serialized_chars,
                "payload_sha256": payload_sha256,
                "skipped_content_sha256": [
                    id_to_hash[value] for value in packed.skipped_k_ids
                ],
            }
        )
    return packed_records, payloads


def measurement_phase(
    packed_records: list[dict[str, Any]], payloads: dict[str, str]
) -> list[dict[str, Any]]:
    # Measurement is imported only after selection identities and payloads exist.
    from src.analysis.e005_diversity_selection import _q11_payload_availability

    measured = []
    for record in packed_records:
        availability = _q11_payload_availability(
            payloads[str(record["configuration_id"])]
        )
        measured.append(
            {
                **record,
                "q11_fact_count": int(availability["fact_count"]),
                "q11_domain_count": int(availability["domain_count"]),
                "q11_per_domain": availability["per_domain"],
                "q11_items": availability["items"],
            }
        )
    if any(not 0 <= record["q11_fact_count"] <= 17 for record in measured):
        raise AssertionError("Q11 fact measurement escaped its 0-17 range")
    return measured


def x1_payload_control(records: list[dict[str, Any]]) -> dict[str, Any]:
    preflight = json.loads(PREFLIGHT_ARTIFACT.read_text(encoding="utf-8"))
    expected = {
        (int(cell["m"]), float(cell["W_Q"]), float(cell["RHO"])): cell
        for cell in preflight["x1_single_shot_control"]["cells"]
    }
    cells = []
    for record in records:
        if int(record["D"]) != 0:
            continue
        key = (int(record["m"]), float(record["W_Q"]), float(record["RHO"]))
        cell = expected[key]
        cells.append(
            {
                "configuration_id": record["configuration_id"],
                "payload_sha256_equal": (
                    record["payload_sha256"] == cell["payload_sha256"]
                ),
                "serialized_chars_equal": (
                    record["serialized_chars"] == cell["serialized_chars"]
                ),
            }
        )
    return {
        "status": "PASS"
        if all(
            cell["payload_sha256_equal"] and cell["serialized_chars_equal"]
            for cell in cells
        )
        else "FAIL",
        "cell_count": len(cells),
        "cells": cells,
    }


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    x0 = json.loads(COMMITTED_X0.read_text(encoding="utf-8"))
    by_depth = {}
    for depth in range(4):
        cells = [record for record in records if int(record["D"]) == depth]
        maximum = max(record["q11_fact_count"] for record in cells)
        by_depth[str(depth)] = {
            "cell_count": len(cells),
            "maximum_q11_fact_count": maximum,
            "minimum_q11_fact_count": min(
                record["q11_fact_count"] for record in cells
            ),
            "maximum_q11_domain_count": max(
                record["q11_domain_count"] for record in cells
            ),
            "candidate_count_range": [
                min(record["candidate_count"] for record in cells),
                max(record["candidate_count"] for record in cells),
            ],
            "selected_episode_count_range": [
                min(record["selected_episode_count"] for record in cells),
                max(record["selected_episode_count"] for record in cells),
            ],
            "serialized_chars_range": [
                min(record["serialized_chars"] for record in cells),
                max(record["serialized_chars"] for record in cells),
            ],
            "final_cue_query_cosine_range": [
                min(record["final_cue_query_cosine"] for record in cells),
                max(record["final_cue_query_cosine"] for record in cells),
            ],
            "maximum_cells": sorted(
                record["configuration_id"]
                for record in cells
                if record["q11_fact_count"] == maximum
            ),
        }
    chained = [record for record in records if int(record["D"]) > 0]
    best_count = max(record["q11_fact_count"] for record in chained)
    best_cells = sorted(
        record["configuration_id"]
        for record in chained
        if record["q11_fact_count"] == best_count
    )
    kill_fires = best_count <= X0_FACT_COUNT
    return {
        "x0_reference": {
            "q11_fact_count": int(x0["fact_count"]),
            "q11_domain_count": int(x0["domain_count"]),
            "selected_episode_count": int(x0["selected_episode_count"]),
            "serialized_chars": int(x0["serialized_chars"]),
            "payload_sha256": str(x0["payload_sha256"]),
        },
        "by_depth": by_depth,
        "best_chained_q11_fact_count": best_count,
        "best_chained_cells": best_cells,
        "kill_condition": (
            "No D>0 cell exceeds X0's committed 6/17 Q11 availability."
        ),
        "kill_fires": kill_fires,
        "disposition": "KILL" if kill_fires else "SURVIVES_KILL",
        "outcome_ceiling": "CHARACTERIZED",
    }


def git_ordering() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.check_output(
            ("git", *args), cwd=REPO_ROOT, text=True
        ).strip()

    commits = {
        "design_commit": run("rev-parse", DESIGN_COMMIT),
        "authorization_commit": run("rev-parse", AUTHORIZATION_COMMIT),
        "pf11_artifact_commit": run("rev-parse", PF11_COMMIT),
        "preflight_artifact_commit": run("rev-parse", PREFLIGHT_COMMIT),
        "parameter_lock_commit": run("rev-parse", PARAMETER_LOCK_COMMIT),
        "head_at_execution": run("rev-parse", "HEAD"),
    }
    ordered = list(commits.values())
    for earlier, later in zip(ordered, ordered[1:]):
        subprocess.check_call(
            ("git", "merge-base", "--is-ancestor", earlier, later),
            cwd=REPO_ROOT,
        )
    return {"status": "PASS", **commits}


def input_inventory() -> list[dict[str, Any]]:
    paths = (
        DESIGN,
        AUTHORIZATION,
        PF11_ARTIFACT,
        PREFLIGHT_ARTIFACT,
        PARAMETER_LOCK,
        DATABASE,
        Q11_RANK_INVENTORY,
        COMMITTED_X0,
        PACKER_SOURCE,
        RENDERER_SOURCE,
        MECHANISM_SOURCE,
    )
    return [
        {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in paths
    ]


def evaluate() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    locked = {
        DESIGN: DESIGN_SHA256,
        AUTHORIZATION: AUTHORIZATION_SHA256,
        PF11_ARTIFACT: PF11_SHA256,
        PREFLIGHT_ARTIFACT: PREFLIGHT_SHA256,
        PARAMETER_LOCK: PARAMETER_LOCK_SHA256,
    }
    for path, digest in locked.items():
        if sha256_file(path) != digest:
            raise AssertionError(f"Locked S4 input changed: {path.name}")
    preflight = json.loads(PREFLIGHT_ARTIFACT.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS":
        raise AssertionError("S4 cannot execute before committed Preflight pass")

    selections, _inputs = selection_phase()
    selection_snapshot_sha256 = hashlib.sha256(
        json.dumps(selections, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    packed, payloads = pack_phase(selections)
    measured = measurement_phase(packed, payloads)
    x1 = x1_payload_control(measured)
    if x1["status"] != "PASS":
        raise AssertionError("S4 violated the D=0 single-shot control")
    summary = summarize(measured)
    result = {
        "study": "E006 Part 2 Rev 5 chained retrieval",
        "stage": "S4 offline evaluation",
        "status": "COMPLETE",
        "outcome": summary["disposition"],
        "outcome_ceiling": "CHARACTERIZED",
        "design_sha256": DESIGN_SHA256,
        "authorization_sha256": AUTHORIZATION_SHA256,
        "pf11_artifact_sha256": PF11_SHA256,
        "preflight_artifact_sha256": PREFLIGHT_SHA256,
        "parameter_lock_sha256": PARAMETER_LOCK_SHA256,
        "zero_model_calls": True,
        "zero_embedding_calls": True,
        "live_evaluation": False,
        "targeted_no_regression_available": False,
        "targeted_limit": (
            "The eight targeted probes have no committed full cosine traces; "
            "no targeted arm was run."
        ),
        "execution": {
            "launch_command": (
                ".venv/Scripts/python.exe -m src.analysis.e006_rev5_offline "
                "experiments/components/retrieval_mechanism_ledger/artifacts/"
                "e006_rev5_s4"
            ),
            "auditor_source_sha256": sha256_file(Path(__file__)),
            "mechanism_source_sha256": sha256_file(MECHANISM_SOURCE),
            "text_encoding": "UTF-8",
        },
        "gate_ordering": git_ordering(),
        "input_inventory": input_inventory(),
        "registered_cell_count": len(measured),
        "selection_snapshot_sha256": selection_snapshot_sha256,
        "selection_reproduction": "PASS",
        "x1_single_shot_control": x1,
        "summary": summary,
        "cells": measured,
    }
    return result, measured, payloads


def deterministic_evaluate() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    first = evaluate()
    second = evaluate()
    first_digest = hashlib.sha256(
        json.dumps(first[0], sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    second_digest = hashlib.sha256(
        json.dumps(second[0], sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payloads_equal = first[2] == second[2]
    if first_digest != second_digest or not payloads_equal:
        raise AssertionError("S4 repeated evaluation is not byte-deterministic")
    first[0]["determinism"] = {
        "status": "PASS",
        "result_sha256_before_annotation": first_digest,
        "payloads_equal": payloads_equal,
    }
    return first


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, records: Sequence[dict[str, Any]]) -> None:
    fields = (
        "configuration_id",
        "arm",
        "D",
        "m",
        "W_Q",
        "RHO",
        "q11_fact_count",
        "q11_domain_count",
        "serialized_chars",
        "selected_episode_count",
        "candidate_count",
        "final_cue_query_cosine",
        "payload_sha256",
        "selection_sha256",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def artifact_manifest(output_dir: Path) -> dict[str, Any]:
    paths = sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file() and path.name != "artifact_manifest.json"
    )
    return {
        "status": "COMPLETE",
        "artifacts": {
            path.relative_to(output_dir).as_posix(): sha256_file(path)
            for path in paths
        },
    }


def write_outputs(output_dir: Path) -> dict[str, Any]:
    result, records, payloads = deterministic_evaluate()
    output_dir.mkdir(parents=True, exist_ok=True)
    payload_dir = output_dir / "payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "results.json", result)
    write_json(
        output_dir / "selection_snapshot.json",
        {
            record["configuration_id"]: {
                "selection_sha256": record["selection_sha256"],
                "ranked_seen_content_sha256": record[
                    "ranked_seen_content_sha256"
                ],
            }
            for record in records
        },
    )
    write_csv(output_dir / "configuration_sweep.csv", records)
    for config_id, payload in payloads.items():
        (payload_dir / f"{config_id}.txt").write_bytes(payload.encode("utf-8"))
    manifest = artifact_manifest(output_dir)
    write_json(output_dir / "artifact_manifest.json", manifest)
    return result


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run E006 Rev 5 S4")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    result = write_outputs(args.output_dir.resolve())
    print(
        json.dumps(
            {
                "status": result["status"],
                "outcome": result["outcome"],
                "output_dir": str(args.output_dir.resolve()),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

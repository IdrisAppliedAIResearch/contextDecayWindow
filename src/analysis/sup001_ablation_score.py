from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.analysis.sup001_ablation_common import STUDY_ROOT, sha256_file


RAW_ROOT = STUDY_ROOT / "artifacts" / "sup001_ablation_raw"
C0_PATH = RAW_ROOT / "c0.json"
T1_PATH = RAW_ROOT / "t1.json"
KEY_PATH = STUDY_ROOT / "artifacts" / "sup001_ablation_lock" / "SEALED_ABLATION_KEY.json"
SCORE_PATH = STUDY_ROOT / "artifacts" / "sup001_ablation_score" / "score.json"
C0_SHA256 = "d99b0f72708801a56689ac05e56b773f23dd805068dcfac783b97f686c0f832c"
T1_SHA256 = "9b0f28cc6ad700e9c563eae0fd80051134da768840dcef287e3f8c9a4b931589"
KEY_SHA256 = "23bf2df2fddcc115091cf0f69a23b724b7d250c425513615f8c84ae634cb64d2"


def score_probe(response: dict[str, Any], key: dict[str, Any]) -> dict[str, Any]:
    answer = str(response["answer"])
    expected = str(key["expected"])
    payload = str(response["context"]["payload"])
    stale = [str(value) for value in key["stale"]]
    if key["class"] == "history":
        evidence_present = all(value in payload for value in expected.split(" | "))
    else:
        evidence_present = expected in payload
    return {
        "probe_id": key["probe_id"],
        "class": key["class"],
        "answer": answer,
        "expected": expected,
        "exact": answer == expected,
        "evidence_present": evidence_present,
        "stale_in_answer": [value for value in stale if value in answer],
        "stale_in_payload": [value for value in stale if value in payload],
        "selected_ids": response["context"]["selected_ids"],
        "serialized_chars": response["context"]["serialized_chars"],
        "payload_sha256": response["context"]["payload_sha256"],
    }


def score_arm(raw: dict[str, Any], key: dict[str, Any]) -> dict[str, Any]:
    responses = {row["probe_id"]: row for row in raw["responses"]}
    rows = [score_probe(responses[row["probe_id"]], row) for row in key["probes"]]
    natural = [row for row in raw["responses"] if row["route"] == "natural"]
    prefixes = [row for row in raw["responses"] if row["prefix_repeat"] is not None]
    return {
        "arm": raw["arm"],
        "rows": rows,
        "exact_total": sum(row["exact"] for row in rows),
        "exact_current": sum(row["exact"] for row in rows if row["class"] == "current"),
        "exact_unchanged": sum(row["exact"] for row in rows if row["class"] == "unchanged"),
        "exact_history": sum(row["exact"] for row in rows if row["class"] == "history"),
        "evidence_present": sum(row["evidence_present"] for row in rows),
        "stale_answer_count": sum(bool(row["stale_in_answer"]) for row in rows),
        "natural_stale_payload_count": sum(bool(row["stale_in_payload"]) for row in rows if row["class"] == "current"),
        "natural_contexts_exactly_eight": all(len(row["context"]["selected_ids"]) == 8 for row in natural),
        "all_contexts_in_budget": all(row["context"]["serialized_chars"] <= 32_000 for row in raw["responses"]),
        "prefix_byte_identical": len(prefixes) == 2 and all(row["prefix_repeat"]["byte_identical"] for row in prefixes),
        "source_unchanged": raw["source_sha256_before"] == raw["source_sha256_after"],
        "runtime_identity": {
            "server_build": raw["runtime"]["server_props"]["build_info"],
            "server_slots": raw["runtime"]["server_props"]["total_slots"],
            "model_sha256": raw["runtime"]["model_sha256"],
            "server_binary_sha256": raw["runtime"]["server_binary_sha256"],
            "seed": raw["runtime"]["server_props"]["default_generation_settings"]["params"]["seed"],
            "speculative": raw["runtime"]["server_props"]["default_generation_settings"]["params"]["speculative.types"],
        },
    }


def run(output_path: Path = SCORE_PATH) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite SUP-001 ablation score: {output_path}")
    if sha256_file(C0_PATH) != C0_SHA256 or sha256_file(T1_PATH) != T1_SHA256:
        raise AssertionError("SUP-001 raw ablation artifact hash mismatch")
    if sha256_file(KEY_PATH) != KEY_SHA256:
        raise AssertionError("SUP-001 sealed ablation key hash mismatch")
    c0_raw = json.loads(C0_PATH.read_text(encoding="utf-8"))
    t1_raw = json.loads(T1_PATH.read_text(encoding="utf-8"))
    key = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    c0 = score_arm(c0_raw, key)
    t1 = score_arm(t1_raw, key)
    c0_by_id = {row["probe_id"]: row for row in c0["rows"]}
    t1_by_id = {row["probe_id"]: row for row in t1["rows"]}
    targeted_regressions = [
        probe_id
        for probe_id, row in c0_by_id.items()
        if row["exact"] and not t1_by_id[probe_id]["exact"]
    ]
    runtime_pass = all(
        arm["prefix_byte_identical"]
        and arm["source_unchanged"]
        and arm["all_contexts_in_budget"]
        and arm["runtime_identity"] == {
            "server_build": "b9294-0f3cb3fc8",
            "server_slots": 1,
            "model_sha256": "f3b4a622e06e8ade06ec5c0eb9b40ed7c9bd707b5fada46c0215f4ab4a6bc32b",
            "server_binary_sha256": "3827a6b634a88073dc63b97edf6e0dc575d33ecf58268803ece0ed23216095fa",
            "seed": 5005,
            "speculative": "none",
        }
        for arm in (c0, t1)
    )
    t1_invariants = bool(
        t1_raw["ledger_validation"]
        == {"record_count": 12, "lineage_count": 4, "accessible_count": 4, "silent_count": 8}
        and t1_raw["state_digest_before"] == t1_raw["state_digest_after"]
        and t1["natural_contexts_exactly_eight"]
        and t1["natural_stale_payload_count"] == 0
    )
    registered_pass = bool(
        runtime_pass
        and t1_invariants
        and t1["exact_current"] == 4
        and t1["exact_unchanged"] == 4
        and t1["exact_history"] == 1
        and t1["evidence_present"] == 9
        and t1["stale_answer_count"] == 0
        and not targeted_regressions
    )
    result = {
        "study": "SUP-001",
        "stage": "35-turn ablation mechanical scoring",
        "status": "COMPLETE",
        "scoring_rule": "After runner whitespace trim, answer must equal sealed expected UTF-8 text exactly; no punctuation, numeric, case, or semantic normalization.",
        "arms": {"C0": c0, "T1": t1},
        "runtime_pass": runtime_pass,
        "t1_invariants_pass": t1_invariants,
        "targeted_regressions": targeted_regressions,
        "registered_pass": registered_pass,
        "disposition": "READY_FOR_SEPARATE_LIVE_DECISION" if registered_pass else "ABLATION_INTEGRATION_STOP",
        "score_order_deviation": {
            "present": True,
            "description": "Mechanism context summaries were inspected during runtime validation before this score artifact was committed.",
            "impact": "The scorer is fully mechanical exact-string equality with no adjudication; the deviation does not change any row, but violates the preferred score-before-mechanism-log order and is retained as a limitation.",
        },
        "inputs": {
            "C0_sha256": C0_SHA256,
            "T1_sha256": T1_SHA256,
            "sealed_key_sha256": KEY_SHA256,
            "source_sha256": sha256_file(Path(__file__)),
        },
        "full_live_run_authorized": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result

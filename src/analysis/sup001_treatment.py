from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from episodic._packing import pack_stm_payload
from src.analysis.sup001_benchmark import BUDGET_CHARS, STUDY_ROOT, TOP_K, canonical_digest
from src.analysis.sup001_control import CONTROL_PATH, candidate
from src.analysis.sup001_part1 import build_ledger, ledger_digest
from src.analysis.sup001_preflight import PREFLIGHT_PATH
from src.analysis.sup001_vectors import MANIFEST_PATH, MECHANISM_PATH, sha256_file
from src.biological_memory.supersession import content_sha256


TREATMENT_ROOT = STUDY_ROOT / "artifacts" / "sup001_treatment"
TREATMENT_PATH = TREATMENT_ROOT / "t1.json"


def compute_treatment(
    mechanism: dict[str, Any], control: dict[str, Any]
) -> dict[str, Any]:
    ledger, _transitions = build_ledger(mechanism)
    by_id = {str(row["episode_sha256"]): row for row in mechanism["episodes"]}
    before = ledger_digest(ledger)
    query_rows: list[dict[str, Any]] = []
    for control_query in control["queries"]:
        ranked = ledger.natural_rank(control_query["population"], limit=TOP_K)
        packed = pack_stm_payload(
            [],
            [candidate(by_id[row["episode_sha256"]]) for row in ranked],
            BUDGET_CHARS,
        )
        selected_ids = [row["episode_sha256"] for row in ranked]
        if list(packed.selected_ids) != selected_ids or len(selected_ids) != TOP_K:
            raise AssertionError("T1 must deliver its exact accessible top eight")
        original_rank = {
            row["episode_sha256"]: index
            for index, row in enumerate(control_query["population"], start=1)
        }
        query_rows.append(
            {
                "query_id": control_query["query_id"],
                "selected": [
                    {**row, "control_population_rank": original_rank[row["episode_sha256"]]}
                    for row in ranked
                ],
                "selected_ids": selected_ids,
                "serialized_chars": packed.serialized_chars,
                "payload_sha256": hashlib.sha256(packed.payload.encode("utf-8")).hexdigest(),
                "payload": packed.payload,
            }
        )
    lineages = []
    for registration in mechanism["registrations"]:
        if registration["operation"] != "initial":
            continue
        key = registration["memory_key"]
        records = ledger.lineage(key)
        rows = []
        for record in records:
            episode = by_id[record.episode_sha256]
            round_trip = content_sha256(episode["user"], episode["assistant"])
            rows.append({**asdict(record), "content_hash_round_trip": round_trip})
        lineages.append({"memory_key": key, "records": rows})
    after = ledger_digest(ledger)
    episode_sequence = [row["episode_sha256"] for row in mechanism["episodes"]]
    return {
        "study": "SUP-001",
        "arm": "T1",
        "status": "FROZEN_LABEL_BLIND",
        "episode_count": len(mechanism["episodes"]),
        "query_count": len(query_rows),
        "lineage_count": len(lineages),
        "top_k": TOP_K,
        "budget_chars": BUDGET_CHARS,
        "queries": query_rows,
        "lineages": lineages,
        "ledger_validation": ledger.validate(),
        "read_purity": {
            "state_digest_before": before,
            "state_digest_after": after,
            "state_unchanged": before == after,
        },
        "immutability": {
            "episode_identity_sequence": episode_sequence,
            "episode_identity_sequence_sha256": canonical_digest(episode_sequence),
            "text_or_vector_rewrite_operations": 0,
        },
    }


def freeze_treatment(output_path: Path = TREATMENT_PATH) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite frozen T1: {output_path}")
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or not preflight["measurement_authorized"]:
        raise RuntimeError("T1 is blocked until committed PF1-PF10 passes")
    mechanism = json.loads(MECHANISM_PATH.read_text(encoding="utf-8"))
    control = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    payload = compute_treatment(mechanism, control)
    payload["inputs"] = {
        "mechanism_sha256": sha256_file(MECHANISM_PATH),
        "control_sha256": sha256_file(CONTROL_PATH),
        "vector_manifest_sha256": sha256_file(MANIFEST_PATH),
        "preflight_sha256": sha256_file(PREFLIGHT_PATH),
        "source_sha256": sha256_file(Path(__file__)),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload

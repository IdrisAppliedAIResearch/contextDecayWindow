from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

import numpy as np

from episodic._packing import pack_stm_payload
from src.analysis.sup001_ablation_common import (
    CACHE_PATH,
    SCRIPT_PATH,
    VECTOR_MANIFEST_PATH,
    assert_clean_expected_worktree,
    assert_local_imports,
    complete,
    control_context,
    frozen_episodes,
    load_script,
    open_vector_cache,
    runtime_identity,
    server_props,
    sha256_file,
    sha256_post_decode_lf,
)
from src.biological_memory.supersession import SupersessionLedger


def build_ledger(script: dict[str, Any], episodes: list[dict[str, Any]]) -> SupersessionLedger:
    ledger = SupersessionLedger()
    by_turn = {row["turn_number"]: row for row in episodes}
    for row in script["turns"]:
        if "memory_key" not in row or row["kind"] != "encoding":
            continue
        identity = by_turn[row["turn"]]["episode_sha256"]
        if row["operation"] == "initial":
            ledger.register_initial(row["memory_key"], identity)
        else:
            parent = by_turn[row["supersedes_turn"]]["episode_sha256"]
            ledger.register_update(row["memory_key"], identity, supersedes=parent)
    expected = {
        "record_count": 12,
        "lineage_count": 4,
        "accessible_count": 4,
        "silent_count": 8,
    }
    if ledger.validate() != expected:
        raise AssertionError("SUP-001 ablation lineage population mismatch")
    return ledger


def ledger_digest(ledger: SupersessionLedger) -> str:
    raw = json.dumps(
        ledger.to_dict(), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def treatment_context(
    probe: dict[str, Any],
    episodes: list[dict[str, Any]],
    ledger: SupersessionLedger,
    vector_for_text: Callable[[str], np.ndarray],
    *,
    top_k: int,
    budget_chars: int,
) -> dict[str, Any]:
    baseline = control_context(
        probe["query"], episodes, vector_for_text,
        top_k=top_k, budget_chars=budget_chars,
    )
    by_id = {row["episode_sha256"]: row for row in episodes}
    if probe["route"] == "lineage":
        records = ledger.lineage(probe["memory_key"])
        selected = [
            {
                "episode_sha256": row.episode_sha256,
                "cosine": next(
                    item["cosine"]
                    for item in baseline["population"]
                    if item["episode_sha256"] == row.episode_sha256
                ),
                "accessibility": row.accessibility,
                "version": row.version,
            }
            for row in records
        ]
    else:
        selected = ledger.natural_rank(baseline["population"], limit=top_k)
    packed = pack_stm_payload(
        [], [by_id[row["episode_sha256"]] for row in selected], budget_chars
    )
    selected_ids = [row["episode_sha256"] for row in selected]
    if list(packed.selected_ids) != selected_ids:
        raise AssertionError("T1 ablation packer changed selected identities")
    if probe["route"] == "natural" and len(selected_ids) != top_k:
        raise AssertionError("T1 natural ablation must deliver exactly top-k")
    return {
        "route": probe["route"],
        "population": baseline["population"],
        "selected": selected,
        "selected_ids": selected_ids,
        "payload": packed.payload,
        "payload_sha256": hashlib.sha256(packed.payload.encode("utf-8")).hexdigest(),
        "serialized_chars": packed.serialized_chars,
    }


def run(output_path: Path, expected_commit: str, server_url: str, server_binary: Path) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite T1 ablation output: {output_path}")
    head = assert_clean_expected_worktree(expected_commit)
    imports = assert_local_imports()
    script = load_script()
    episodes = frozen_episodes(script)
    ledger = build_ledger(script, episodes)
    props = server_props(server_url)
    runtime = runtime_identity(props, server_binary)
    source_path = Path(__file__)
    source_before = sha256_file(source_path)
    state_before = ledger_digest(ledger)
    responses = []
    with open_vector_cache() as cache:
        for probe_index, probe in enumerate((row for row in script["turns"] if row["kind"] == "probe"), start=1):
            context = treatment_context(
                probe, episodes, ledger, cache,
                top_k=int(script["top_k"]), budget_chars=int(script["budget_chars"]),
            )
            prompt = script["reader_prompt_template"].format(
                memory_payload=context["payload"], query=probe["query"]
            )
            first = complete(server_url, prompt, int(script["reader_n_predict"]))
            repeat = complete(server_url, prompt, int(script["reader_n_predict"])) if probe_index <= 2 else None
            if repeat is not None and first["raw_content"] != repeat["raw_content"]:
                raise RuntimeError(f"T1 prefix determinism failed at {probe['probe_id']}")
            responses.append(
                {
                    "turn": probe["turn"],
                    "probe_id": probe["probe_id"],
                    "route": probe["route"],
                    "query": probe["query"],
                    "context": context,
                    "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    "answer": first["content"],
                    "raw_answer": first["raw_content"],
                    "tokens_predicted": first["tokens_predicted"],
                    "elapsed_seconds": first["elapsed_seconds"],
                    "prefix_repeat": None if repeat is None else {
                        "raw_answer": repeat["raw_content"],
                        "byte_identical": first["raw_content"] == repeat["raw_content"],
                        "tokens_predicted": repeat["tokens_predicted"],
                    },
                }
            )
    state_after = ledger_digest(ledger)
    source_after = sha256_file(source_path)
    if source_before != source_after:
        raise RuntimeError("T1 source changed during decoding")
    if state_before != state_after:
        raise RuntimeError("T1 reads mutated the lineage ledger")
    payload = {
        "study": "SUP-001",
        "stage": "35-turn reader ablation",
        "arm": "T1",
        "status": "COMPLETE_UNSCORED",
        "turns": 35,
        "frozen_episode_count": len(episodes),
        "probe_count": len(responses),
        "generation_calls": len(responses) + 2,
        "worktree": {"status": "PASS", "commit": head, "imports": imports},
        "runtime": runtime,
        "responses": responses,
        "ledger": ledger.to_dict(),
        "ledger_validation": ledger.validate(),
        "state_digest_before": state_before,
        "state_digest_after": state_after,
        "source_sha256_before": source_before,
        "source_sha256_after": source_after,
        "inputs": {
            "script_sha256_post_decode_lf": sha256_post_decode_lf(SCRIPT_PATH),
            "cache_sha256": sha256_file(CACHE_PATH),
            "vector_manifest_sha256": sha256_file(VECTOR_MANIFEST_PATH),
        },
        "sealed_key_opened": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload

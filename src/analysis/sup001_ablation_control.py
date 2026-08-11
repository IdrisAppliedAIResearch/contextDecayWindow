from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

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
)


FORBIDDEN_MODULES = ("src.biological_memory.supersession", "sup001_ablation_treatment", "sup001_treatment")


def assert_control_isolation(expected_commit: str) -> dict[str, Any]:
    head = assert_clean_expected_worktree(expected_commit)
    resident = sorted(name for name in sys.modules if any(token in name for token in FORBIDDEN_MODULES))
    if resident:
        raise RuntimeError(f"Treatment modules are resident in C0: {resident}")
    return {"status": "PASS", "commit": head, "resident_treatment_modules": resident, "imports": assert_local_imports()}


def run(output_path: Path, expected_commit: str, server_url: str, server_binary: Path) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite C0 ablation output: {output_path}")
    isolation = assert_control_isolation(expected_commit)
    script = load_script()
    episodes = frozen_episodes(script)
    props = server_props(server_url)
    runtime = runtime_identity(props, server_binary)
    source_path = Path(__file__)
    source_before = sha256_file(source_path)
    responses = []
    with open_vector_cache() as cache:
        for probe_index, probe in enumerate((row for row in script["turns"] if row["kind"] == "probe"), start=1):
            context = control_context(
                probe["query"], episodes, cache,
                top_k=int(script["top_k"]), budget_chars=int(script["budget_chars"]),
            )
            prompt = script["reader_prompt_template"].format(
                memory_payload=context["payload"], query=probe["query"]
            )
            first = complete(server_url, prompt, int(script["reader_n_predict"]))
            repeat = complete(server_url, prompt, int(script["reader_n_predict"])) if probe_index <= 2 else None
            if repeat is not None and first["raw_content"] != repeat["raw_content"]:
                raise RuntimeError(f"C0 prefix determinism failed at {probe['probe_id']}")
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
    source_after = sha256_file(source_path)
    if source_before != source_after:
        raise RuntimeError("C0 source changed during decoding")
    payload = {
        "study": "SUP-001",
        "stage": "35-turn reader ablation",
        "arm": "C0",
        "status": "COMPLETE_UNSCORED",
        "turns": 35,
        "frozen_episode_count": len(episodes),
        "probe_count": len(responses),
        "generation_calls": len(responses) + 2,
        "isolation": isolation,
        "runtime": runtime,
        "responses": responses,
        "source_sha256_before": source_before,
        "source_sha256_after": source_after,
        "inputs": {
            "script_sha256": sha256_file(SCRIPT_PATH),
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

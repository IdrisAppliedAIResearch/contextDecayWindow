from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np

from episodic._packing import pack_stm_payload
from src.analysis.sup001_benchmark import BUDGET_CHARS, REPO_ROOT, STUDY_ROOT, TOP_K
from src.analysis.sup001_vectors import (
    CACHE_PATH,
    MANIFEST_PATH,
    MECHANISM_PATH,
    episode_text,
    sha256_file,
)
from episodic import EmbeddingCache
from src.retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256


CONTROL_ROOT = STUDY_ROOT / "artifacts" / "sup001_control"
CONTROL_PATH = CONTROL_ROOT / "c0_frozen.json"


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    a = np.asarray(left, dtype=np.float32)
    b = np.asarray(right, dtype=np.float32)
    denominator = float(np.linalg.norm(a)) * float(np.linalg.norm(b))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(a, b) / denominator)


def candidate(episode: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(episode["episode_sha256"]),
        "turn_number": int(episode["turn_number"]),
        "user_message": str(episode["user"]),
        "assistant_message": str(episode["assistant"]),
    }


def compute_control(
    mechanism: Mapping[str, Any], vector_for_text: Callable[[str], np.ndarray]
) -> dict[str, Any]:
    episodes = list(mechanism["episodes"])
    episode_vectors = {
        str(row["episode_sha256"]): vector_for_text(episode_text(row))
        for row in episodes
    }
    queries: list[dict[str, Any]] = []
    for query in mechanism["queries"]:
        query_vector = vector_for_text(str(query["text"]))
        population = [
            {
                "episode_sha256": str(row["episode_sha256"]),
                "cosine": cosine(
                    query_vector, episode_vectors[str(row["episode_sha256"])]
                ),
            }
            for row in episodes
        ]
        population.sort(key=lambda row: (-row["cosine"], row["episode_sha256"]))
        by_id = {str(row["episode_sha256"]): row for row in episodes}
        top = population[:TOP_K]
        packed = pack_stm_payload(
            [], [candidate(by_id[row["episode_sha256"]]) for row in top], BUDGET_CHARS
        )
        expected_ids = tuple(row["episode_sha256"] for row in top)
        if packed.selected_ids != expected_ids or len(expected_ids) != TOP_K:
            raise AssertionError("C0 must deliver its exact top-8 identities")
        if packed.serialized_chars > BUDGET_CHARS:
            raise AssertionError("C0 exceeded the registered character ceiling")
        queries.append(
            {
                "query_id": str(query["query_id"]),
                "population": population,
                "selected": top,
                "selected_ids": list(packed.selected_ids),
                "serialized_chars": packed.serialized_chars,
                "payload_sha256": hashlib.sha256(packed.payload.encode("utf-8")).hexdigest(),
                "payload": packed.payload,
            }
        )
    return {
        "study": "SUP-001",
        "arm": "C0",
        "status": "FROZEN",
        "episode_count": len(episodes),
        "query_count": len(queries),
        "top_k": TOP_K,
        "budget_chars": BUDGET_CHARS,
        "queries": queries,
    }


def freeze_control(
    mechanism_path: Path = MECHANISM_PATH,
    vector_manifest_path: Path = MANIFEST_PATH,
    output_path: Path = CONTROL_PATH,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite frozen C0: {output_path}")
    mechanism = json.loads(mechanism_path.read_text(encoding="utf-8"))
    vector_manifest = json.loads(vector_manifest_path.read_text(encoding="utf-8"))
    cache_record = vector_manifest["cache"]
    with EmbeddingCache(
        CACHE_PATH,
        mode="reuse",
        expected_file_sha256=cache_record["file_sha256"],
        expected_content_sha256=cache_record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    ) as cache:
        payload = compute_control(mechanism, cache)
        if cache.misses != 0 or cache.hits != 352:
            raise AssertionError("C0 must read all 352 vectors with zero model calls")
        payload["cache_replay"] = cache.record()
    payload["inputs"] = {
        "mechanism_sha256": sha256_file(mechanism_path),
        "vector_manifest_sha256": sha256_file(vector_manifest_path),
        "vector_cache_sha256": sha256_file(CACHE_PATH),
        "source_sha256": sha256_file(Path(__file__)),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload

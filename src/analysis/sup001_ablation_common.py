from __future__ import annotations

import hashlib
import inspect
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen

import numpy as np

from episodic import EmbeddingCache
from episodic._packing import pack_stm_payload
from episodic._render import render_stm_payload
from src.retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256


REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT = REPO_ROOT / "experiments" / "components" / "biological_memory" / "sup_001"
LOCK_ROOT = STUDY_ROOT / "artifacts" / "sup001_ablation_lock"
SCRIPT_PATH = LOCK_ROOT / "ablation_script.json"
VECTOR_ROOT = STUDY_ROOT / "artifacts" / "sup001_ablation_vectors"
CACHE_PATH = VECTOR_ROOT / "ablation_vectors.sqlite"
VECTOR_MANIFEST_PATH = VECTOR_ROOT / "vector_manifest.json"
SCRIPT_SHA256 = "911fa59e3a85134225ddf066a049fcf4c68fdeff84c60e720bda89ce190a2547"
MODEL_SHA256 = "f3b4a622e06e8ade06ec5c0eb9b40ed7c9bd707b5fada46c0215f4ab4a6bc32b"
SERVER_BINARY_SHA256 = "3827a6b634a88073dc63b97edf6e0dc575d33ecf58268803ece0ed23216095fa"
SERVER_BUILD = "b9294-0f3cb3fc8"
SEED = 5005


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_post_decode_lf(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def content_sha256(user: str, assistant: str) -> str:
    payload = json.dumps(
        [["user", user], ["assistant", assistant]],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def episode_text(episode: dict[str, Any]) -> str:
    return f"User: {episode['user']}\nAssistant: {episode['assistant']}"


def load_script() -> dict[str, Any]:
    if sha256_post_decode_lf(SCRIPT_PATH) != SCRIPT_SHA256:
        raise AssertionError("SUP-001 ablation script hash changed")
    script = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    if script["turn_count"] != 35 or len(script["turns"]) != 35:
        raise AssertionError("SUP-001 ablation must contain exactly 35 turns")
    return script


def frozen_episodes(script: dict[str, Any]) -> list[dict[str, Any]]:
    episodes = []
    for row in script["turns"]:
        if row["kind"] == "probe":
            continue
        episode = {
            "id": content_sha256(row["user"], row["assistant"]),
            "episode_sha256": content_sha256(row["user"], row["assistant"]),
            "turn_number": int(row["turn"]),
            "user": row["user"],
            "assistant": row["assistant"],
            "user_message": row["user"],
            "assistant_message": row["assistant"],
        }
        episodes.append(episode)
    if len(episodes) != 26 or len({row["id"] for row in episodes}) != 26:
        raise AssertionError("SUP-001 ablation requires 26 unique frozen episodes")
    return episodes


def vector_texts(script: dict[str, Any]) -> list[str]:
    texts = [episode_text(row) for row in frozen_episodes(script)]
    texts.extend(row["query"] for row in script["turns"] if row["kind"] == "probe")
    if len(texts) != 35 or len(set(texts)) != 35:
        raise AssertionError("SUP-001 ablation requires 35 unique vector texts")
    return texts


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    a = np.asarray(left, dtype=np.float32)
    b = np.asarray(right, dtype=np.float32)
    denominator = float(np.linalg.norm(a)) * float(np.linalg.norm(b))
    return 0.0 if denominator == 0.0 else float(np.dot(a, b) / denominator)


def control_context(
    query: str,
    episodes: list[dict[str, Any]],
    vector_for_text: Callable[[str], np.ndarray],
    *,
    top_k: int,
    budget_chars: int,
) -> dict[str, Any]:
    query_vector = vector_for_text(query)
    population = [
        {
            "episode_sha256": row["episode_sha256"],
            "cosine": cosine(query_vector, vector_for_text(episode_text(row))),
        }
        for row in episodes
    ]
    population.sort(key=lambda row: (-row["cosine"], row["episode_sha256"]))
    by_id = {row["episode_sha256"]: row for row in episodes}
    selected = population[:top_k]
    packed = pack_stm_payload([], [by_id[row["episode_sha256"]] for row in selected], budget_chars)
    if list(packed.selected_ids) != [row["episode_sha256"] for row in selected]:
        raise AssertionError("C0 ablation packer did not preserve exact top-k")
    return {
        "population": population,
        "selected": selected,
        "selected_ids": list(packed.selected_ids),
        "payload": packed.payload,
        "payload_sha256": hashlib.sha256(packed.payload.encode("utf-8")).hexdigest(),
        "serialized_chars": packed.serialized_chars,
    }


def assert_local_imports() -> dict[str, str]:
    packing_path = Path(inspect.getfile(pack_stm_payload)).resolve()
    render_path = Path(inspect.getfile(render_stm_payload)).resolve()
    expected_root = (REPO_ROOT / "episodic" / "src").resolve()
    if not packing_path.is_relative_to(expected_root) or not render_path.is_relative_to(expected_root):
        raise RuntimeError("episodic import escaped the active worktree")
    return {
        "packing_path": str(packing_path),
        "render_path": str(render_path),
        "expected_root": str(expected_root),
    }


def git(*args: str) -> str:
    return subprocess.check_output(
        ("git", *args), cwd=REPO_ROOT, text=True, encoding="utf-8"
    ).strip()


def assert_clean_expected_worktree(expected_commit: str) -> str:
    head = git("rev-parse", "HEAD")
    if head != expected_commit:
        raise RuntimeError(f"Wrong ablation worktree commit: {head} != {expected_commit}")
    if git("status", "--porcelain"):
        raise RuntimeError("Ablation worktree must be clean before inference")
    return head


def server_props(server_url: str) -> dict[str, Any]:
    with urlopen(f"{server_url.rstrip('/')}/props", timeout=30) as response:
        props = json.loads(response.read().decode("utf-8"))
    params = props["default_generation_settings"]["params"]
    failures = []
    if props.get("build_info") != SERVER_BUILD:
        failures.append(f"build={props.get('build_info')}")
    if int(props.get("total_slots", 0)) != 1:
        failures.append(f"slots={props.get('total_slots')}")
    if int(params.get("seed", -1)) != SEED:
        failures.append(f"seed={params.get('seed')}")
    if params.get("speculative.types") != "none":
        failures.append(f"speculative={params.get('speculative.types')}")
    if int(props["default_generation_settings"]["n_ctx"]) < 50_000:
        failures.append(f"n_ctx={props['default_generation_settings']['n_ctx']}")
    if failures:
        raise RuntimeError("SUP-001 server guard failed: " + ", ".join(failures))
    return props


def complete(server_url: str, prompt: str, n_predict: int) -> dict[str, Any]:
    direct = f"{prompt}\n<think>\n</think>\n"
    payload = json.dumps(
        {
            "prompt": direct,
            "n_predict": n_predict,
            "reasoning_format": "none",
            "stream": False,
            "seed": SEED,
        }
    ).encode("utf-8")
    request = Request(
        f"{server_url.rstrip('/')}/completion",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urlopen(request, timeout=600) as response:
        result = json.loads(response.read().decode("utf-8"))
    return {
        "content": str(result["content"]).strip(),
        "raw_content": str(result["content"]),
        "tokens_predicted": int(result.get("tokens_predicted", 0)),
        "elapsed_seconds": time.perf_counter() - started,
    }


def open_vector_cache() -> EmbeddingCache:
    manifest = json.loads(VECTOR_MANIFEST_PATH.read_text(encoding="utf-8"))
    record = manifest["cache"]
    return EmbeddingCache(
        CACHE_PATH,
        mode="reuse",
        expected_file_sha256=record["file_sha256"],
        expected_content_sha256=record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    )


def runtime_identity(props: dict[str, Any], server_binary: Path) -> dict[str, Any]:
    model_path = Path(props["model_path"]).resolve()
    if sha256_file(model_path) != MODEL_SHA256:
        raise RuntimeError("SUP-001 reader model hash mismatch")
    if sha256_file(server_binary) != SERVER_BINARY_SHA256:
        raise RuntimeError("SUP-001 server binary hash mismatch")
    return {
        "server_props": props,
        "server_binary": str(server_binary),
        "server_binary_sha256": SERVER_BINARY_SHA256,
        "server_pid": int(os.environ["CDW_INFERENCE_SERVER_PID"]),
        "server_command": os.environ["CDW_INFERENCE_SERVER_COMMAND"],
        "model_path": str(model_path),
        "model_sha256": MODEL_SHA256,
    }

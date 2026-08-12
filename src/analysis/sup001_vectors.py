from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

from episodic import EmbeddingCache
from src.analysis.sup001_benchmark import REPO_ROOT, STUDY_ROOT
from src.retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256
from src.retrieval_bakeoff.embedding import CarriedEmbedder, normalize_embedding


CORPUS_ROOT = STUDY_ROOT / "artifacts" / "sup001_corpus"
MECHANISM_PATH = CORPUS_ROOT / "mechanism_manifest.json"
VECTOR_ROOT = STUDY_ROOT / "artifacts" / "sup001_vectors"
CACHE_PATH = VECTOR_ROOT / "sup001_vectors.sqlite"
MANIFEST_PATH = VECTOR_ROOT / "vector_manifest.json"


@dataclass(frozen=True)
class VectorText:
    kind: str
    identity: str
    text: str


class NormalizedSoloEmbedder:
    def __init__(self, delegate: Callable[[str], np.ndarray]) -> None:
        self.delegate = delegate
        self.model_sha256 = str(getattr(delegate, "model_sha256"))
        self.calls = 0

    def __call__(self, text: str) -> np.ndarray:
        self.calls += 1
        return normalize_embedding(self.delegate(text))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def episode_text(episode: dict[str, Any]) -> str:
    return f"User: {episode['user']}\nAssistant: {episode['assistant']}"


def load_vector_texts(path: Path = MECHANISM_PATH) -> tuple[VectorText, ...]:
    mechanism = json.loads(path.read_text(encoding="utf-8"))
    rows = [
        VectorText("episode", str(row["episode_sha256"]), episode_text(row))
        for row in mechanism["episodes"]
    ]
    rows.extend(
        VectorText("query", str(row["query_id"]), str(row["text"]))
        for row in mechanism["queries"]
    )
    result = tuple(rows)
    if len(result) != 352 or len({row.text for row in result}) != 352:
        raise AssertionError("SUP-001 requires 352 unique episode/query texts")
    return result


def populate_cache(
    texts: Sequence[VectorText], cache_path: Path, delegate: Callable[[str], np.ndarray]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    normalized = NormalizedSoloEmbedder(delegate)
    rows: list[dict[str, Any]] = []
    with EmbeddingCache(cache_path, mode="populate", embedder=normalized) as cache:
        for item in texts:
            vector = cache(item.text)
            raw = np.asarray(vector, dtype=np.float32).tobytes()
            rows.append(
                {
                    "kind": item.kind,
                    "identity": item.identity,
                    "text_sha256": hashlib.sha256(item.text.encode("utf-8")).hexdigest(),
                    "vector_sha256": hashlib.sha256(raw).hexdigest(),
                    "dimension": int(vector.size),
                    "dtype": str(vector.dtype),
                    "unit_norm": float(np.linalg.norm(vector)),
                }
            )
    record = cache.record()
    if normalized.calls != len(texts):
        raise AssertionError("Vector capture did not issue exactly one call per text")
    if record["entries"] != len(texts) or record["misses"] != len(texts):
        raise AssertionError("Vector cache cardinality differs from locked inventory")
    return record, rows


def assert_clean_worktree() -> None:
    output = subprocess.check_output(
        ("git", "status", "--porcelain"), cwd=REPO_ROOT, text=True
    )
    if output.strip():
        raise RuntimeError(f"SUP-001 vector capture requires a clean worktree:\n{output}")


def capture(model_path: Path, cache_path: Path, manifest_path: Path) -> dict[str, Any]:
    assert_clean_worktree()
    if cache_path.exists() or manifest_path.exists():
        raise FileExistsError("Refusing to overwrite retained SUP-001 vector artifacts")
    if importlib.metadata.version("llama-cpp-python") != "0.3.25":
        raise AssertionError("SUP-001 requires llama-cpp-python==0.3.25")

    texts = load_vector_texts()
    delegate = CarriedEmbedder(model_path)
    delegate.assert_carried_model()
    record, vectors = populate_cache(texts, cache_path, delegate)
    payload = {
        "study": "SUP-001",
        "stage": "solo-call vector lock",
        "status": "SEALED",
        "request_count": len(texts),
        "episode_vector_count": sum(row.kind == "episode" for row in texts),
        "query_vector_count": sum(row.kind == "query" for row in texts),
        "call_shape": "solo",
        "zero_model_generation_calls": True,
        "cache": record,
        "mechanism_manifest": {
            "path": MECHANISM_PATH.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_file(MECHANISM_PATH),
        },
        "vectors": vectors,
        "execution": {
            "argv": [sys.executable, *sys.argv],
            "pid": os.getpid(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "numpy": importlib.metadata.version("numpy"),
            "llama_cpp_python": importlib.metadata.version("llama-cpp-python"),
            "model_path": str(model_path.resolve()),
            "model_sha256": CARRIED_EMBEDDING_SHA256,
            "source_sha256": sha256_file(Path(__file__)),
            "thread_environment": {
                name: os.environ.get(name)
                for name in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                )
            },
            "text_encoding": "UTF-8",
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload

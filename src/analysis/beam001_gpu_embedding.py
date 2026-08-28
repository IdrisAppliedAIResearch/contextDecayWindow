"""Pinned GPU embedding runtime and durable BEAM-001 vector cache."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import numpy as np

from analysis.beam001_adapter import adapt_conversation, load_mechanism_surface
from analysis.beam001_embedding_preflight import episode_text, sha256_file

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT / "experiments/comparisons/beam_001"
MECHANISM_SURFACE = ROOT / "artifacts/corpus/mechanism_surface.jsonl.gz"
CACHE_PATH = ROOT / "artifacts/embeddings/beam001_qwen_gpu.sqlite"
RUNTIME_ROOT = ROOT / "artifacts/runtime"
PROGRESS_PATH = RUNTIME_ROOT / "embedding_progress.json"
FAILURE_PATH = RUNTIME_ROOT / "embedding_failure.json"
ANCHOR_PATH = ROOT / "artifacts/preflight/gpu_embedding_anchors.json"

MODEL_PATH = Path(
    r"C:\Users\muzaf\.cache\huggingface\hub\Qwen3-Embedding-0.6B-GGUF"
    r"\Qwen3-Embedding-0.6B-Q8_0.gguf"
)
MODEL_SHA256 = "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
SENTINEL_TEXT = "episodic call-shape sentinel: one text per call"
SENTINEL_SHA256 = "a52c6019c79957d0ea3af9bb15d863a826f825deebc9f7aa03232e31e601df3a"
LONGEST_EPISODE_KEY = "f52f820509c5b290965ac9f33eb5d54f840751d2d0dc8db8e8792120e0a29834"
LONGEST_VECTOR_SHA256 = "e81c77ddef7f75529bf147cea16337d90688bd634f931e4f7fbff38bb1d91825"
EMBEDDING_DIMENSION = 1_024
N_CTX = 32_768
N_BATCH = 2_048
N_UBATCH = 512

_SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS embeddings (
    input_sha256 TEXT PRIMARY KEY,
    token_count INTEGER NOT NULL,
    vector BLOB NOT NULL,
    vector_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bindings (
    kind TEXT NOT NULL,
    source_key TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    PRIMARY KEY (kind, source_key),
    FOREIGN KEY (input_sha256) REFERENCES embeddings(input_sha256)
);
"""


class BeamEmbeddingError(RuntimeError):
    pass


@dataclass(frozen=True)
class InputRecord:
    kind: str
    source_key: str
    text: str

    @property
    def input_sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def runtime_spec() -> dict[str, Any]:
    return {
        "model_path": str(MODEL_PATH),
        "model_sha256": MODEL_SHA256,
        "llama_cpp_version": "0.3.25",
        "backend": "CUDA",
        "n_gpu_layers": -1,
        "n_ctx": N_CTX,
        "n_batch": N_BATCH,
        "n_ubatch": N_UBATCH,
        "call_shape": "solo",
        "dimension": EMBEDDING_DIMENSION,
        "dtype": "float32",
    }


def runtime_spec_sha256() -> str:
    raw = json.dumps(runtime_spec(), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def iter_inputs(rows: Iterable[dict[str, Any]]) -> Iterator[InputRecord]:
    yield InputRecord("sentinel", "sentinel", SENTINEL_TEXT)
    for row in rows:
        for episode in adapt_conversation(row):
            yield InputRecord("episode", episode["episode_key"], episode_text(episode))
        for question in row["questions"]:
            yield InputRecord("question", question["question_key"], question["question"])


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, newline="\n"
    ) as handle:
        temporary = Path(handle.name)
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


class GpuEmbeddingRuntime:
    def __init__(self) -> None:
        if sha256_file(MODEL_PATH) != MODEL_SHA256:
            raise BeamEmbeddingError("Pinned embedding model hash drifted")
        try:
            import llama_cpp
            from llama_cpp import Llama
        except ImportError as error:
            raise BeamEmbeddingError("llama-cpp-python is required") from error
        if llama_cpp.__version__ != runtime_spec()["llama_cpp_version"]:
            raise BeamEmbeddingError("llama-cpp-python version drifted")
        self.model = Llama(
            model_path=str(MODEL_PATH),
            embedding=True,
            n_gpu_layers=-1,
            n_ctx=N_CTX,
            n_batch=N_BATCH,
            n_ubatch=N_UBATCH,
            verbose=False,
        )

    def token_count(self, text: str) -> int:
        return len(self.model.tokenize(text.encode("utf-8"), add_bos=True))

    def embed(self, text: str) -> np.ndarray:
        tokens = self.token_count(text)
        if tokens > N_CTX:
            raise BeamEmbeddingError(f"Exact input needs {tokens} tokens; limit is {N_CTX}")
        vector = np.asarray(self.model.embed(text), dtype=np.float32)
        if vector.shape != (EMBEDDING_DIMENSION,):
            raise BeamEmbeddingError(f"Embedding shape drifted: {vector.shape}")
        if not np.isfinite(vector).all() or float(np.linalg.norm(vector)) == 0.0:
            raise BeamEmbeddingError("Embedding was non-finite or zero")
        return vector


class EmbeddingCache:
    def __init__(self, path: Path, *, read_only: bool = False) -> None:
        self.path = Path(path)
        self.read_only = read_only
        if read_only:
            if not self.path.is_file():
                raise BeamEmbeddingError(f"Embedding cache does not exist: {self.path}")
            uri = self.path.resolve().as_uri() + "?mode=ro"
            self.connection = sqlite3.connect(uri, uri=True)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.path)
            self.connection.execute("PRAGMA synchronous=FULL")
            self.connection.execute("PRAGMA journal_mode=DELETE")
            self.connection.execute("PRAGMA foreign_keys=ON")
            self.connection.executescript(_SCHEMA)
            self.connection.commit()
            self._bind_metadata()
        self._verify_metadata()

    def _bind_metadata(self) -> None:
        expected = {
            "cache_version": "beam001-gpu-cache-v1",
            "model_sha256": MODEL_SHA256,
            "runtime_spec_sha256": runtime_spec_sha256(),
            "runtime_spec": json.dumps(runtime_spec(), sort_keys=True, separators=(",", ":")),
        }
        for key, value in expected.items():
            row = self.connection.execute(
                "SELECT value FROM metadata WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                self.connection.execute(
                    "INSERT INTO metadata (key, value) VALUES (?, ?)", (key, value)
                )
            elif str(row[0]) != value:
                raise BeamEmbeddingError(f"Cache metadata drifted: {key}")
        self.connection.commit()

    def _verify_metadata(self) -> None:
        rows = dict(self.connection.execute("SELECT key, value FROM metadata"))
        if rows.get("model_sha256") != MODEL_SHA256:
            raise BeamEmbeddingError("Cache model identity drifted")
        if rows.get("runtime_spec_sha256") != runtime_spec_sha256():
            raise BeamEmbeddingError("Cache runtime identity drifted")

    def has(self, text: str) -> bool:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return self.connection.execute(
            "SELECT 1 FROM embeddings WHERE input_sha256 = ?", (key,)
        ).fetchone() is not None

    def put(self, record: InputRecord, token_count: int, vector: np.ndarray) -> bool:
        if self.read_only:
            raise BeamEmbeddingError("Cannot write a read-only cache")
        raw = np.asarray(vector, dtype=np.float32).reshape(EMBEDDING_DIMENSION).tobytes()
        vector_sha = hashlib.sha256(raw).hexdigest()
        existing = self.connection.execute(
            "SELECT token_count, vector_sha256 FROM embeddings WHERE input_sha256 = ?",
            (record.input_sha256,),
        ).fetchone()
        created = existing is None
        if existing is None:
            self.connection.execute(
                "INSERT INTO embeddings VALUES (?, ?, ?, ?)",
                (record.input_sha256, int(token_count), raw, vector_sha),
            )
        elif int(existing[0]) != int(token_count) or str(existing[1]) != vector_sha:
            raise BeamEmbeddingError("Attempted to overwrite a different cached vector")
        self.connection.execute(
            "INSERT OR REPLACE INTO bindings VALUES (?, ?, ?)",
            (record.kind, record.source_key, record.input_sha256),
        )
        self.connection.commit()
        return created

    def bind_existing(self, record: InputRecord) -> None:
        if self.read_only:
            raise BeamEmbeddingError("Cannot write a read-only cache")
        if not self.has(record.text):
            raise BeamEmbeddingError("Cannot bind a missing vector")
        self.connection.execute(
            "INSERT OR REPLACE INTO bindings VALUES (?, ?, ?)",
            (record.kind, record.source_key, record.input_sha256),
        )
        self.connection.commit()

    def get(self, text: str) -> np.ndarray:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        row = self.connection.execute(
            "SELECT vector, vector_sha256 FROM embeddings WHERE input_sha256 = ?", (key,)
        ).fetchone()
        if row is None:
            raise BeamEmbeddingError(f"Read-only embedding cache miss: {key}")
        raw = bytes(row[0])
        if hashlib.sha256(raw).hexdigest() != str(row[1]):
            raise BeamEmbeddingError("Cached vector digest drifted")
        return np.frombuffer(raw, dtype=np.float32).copy().reshape(EMBEDDING_DIMENSION)

    def counts(self) -> dict[str, int]:
        return {
            "vectors": int(self.connection.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]),
            "bindings": int(self.connection.execute("SELECT COUNT(*) FROM bindings").fetchone()[0]),
        }

    def verify(self) -> dict[str, Any]:
        row = self.connection.execute("PRAGMA quick_check").fetchone()
        if row is None or str(row[0]).lower() != "ok":
            raise BeamEmbeddingError("Embedding cache integrity check failed")
        mismatches = 0
        for raw, expected in self.connection.execute(
            "SELECT vector, vector_sha256 FROM embeddings"
        ):
            if hashlib.sha256(bytes(raw)).hexdigest() != str(expected):
                mismatches += 1
        return {**self.counts(), "vector_digest_mismatches": mismatches, "quick_check": "ok"}

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "EmbeddingCache":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class CachedEmbedder:
    model_sha256 = MODEL_SHA256

    def __init__(self, path: Path = CACHE_PATH) -> None:
        self.cache = EmbeddingCache(path, read_only=True)

    def __call__(self, text: str) -> np.ndarray:
        return self.cache.get(text)

    def close(self) -> None:
        self.cache.close()


def _find_longest(records: Sequence[InputRecord], runtime: GpuEmbeddingRuntime) -> InputRecord:
    episodes = [record for record in records if record.kind == "episode"]
    if not episodes:
        raise BeamEmbeddingError("No episode inputs were found")
    longest = max(episodes, key=lambda record: runtime.token_count(record.text))
    if longest.source_key != LONGEST_EPISODE_KEY:
        raise BeamEmbeddingError("Longest episode identity drifted")
    return longest


def seed_and_preflight(
    *,
    mechanism_path: Path = MECHANISM_SURFACE,
    cache_path: Path = CACHE_PATH,
    artifact_path: Path = ANCHOR_PATH,
) -> dict[str, Any]:
    rows = load_mechanism_surface(mechanism_path)
    records = list(iter_inputs(rows))
    runtime = GpuEmbeddingRuntime()
    token_counts = [runtime.token_count(record.text) for record in records]
    oversized = [
        {"kind": record.kind, "source_key": record.source_key, "tokens": tokens}
        for record, tokens in zip(records, token_counts)
        if tokens > N_CTX
    ]
    if oversized:
        raise BeamEmbeddingError(f"{len(oversized)} exact inputs exceed n_ctx")
    longest = _find_longest(records, runtime)
    sentinel_record = records[0]
    started = time.perf_counter()
    sentinel_vector = runtime.embed(sentinel_record.text)
    sentinel_seconds = time.perf_counter() - started
    started = time.perf_counter()
    longest_vector = runtime.embed(longest.text)
    longest_seconds = time.perf_counter() - started
    sentinel_sha = hashlib.sha256(sentinel_vector.tobytes()).hexdigest()
    longest_sha = hashlib.sha256(longest_vector.tobytes()).hexdigest()
    if sentinel_sha != SENTINEL_SHA256 or longest_sha != LONGEST_VECTOR_SHA256:
        raise BeamEmbeddingError("GPU embedding anchor drifted")
    with EmbeddingCache(cache_path) as cache:
        cache.put(sentinel_record, runtime.token_count(sentinel_record.text), sentinel_vector)
        cache.put(longest, runtime.token_count(longest.text), longest_vector)
        cache_state = cache.verify()
    with EmbeddingCache(cache_path, read_only=True) as reopened:
        reopen_sentinel = hashlib.sha256(reopened.get(sentinel_record.text).tobytes()).hexdigest()
        reopen_longest = hashlib.sha256(reopened.get(longest.text).tobytes()).hexdigest()
    result = {
        "gate": "PASS",
        "disposition": "READY_FOR_DETACHED_GPU_POPULATION",
        "runtime_spec": runtime_spec(),
        "runtime_spec_sha256": runtime_spec_sha256(),
        "mechanism_surface_sha256": sha256_file(mechanism_path),
        "inputs": len(records),
        "unique_input_sha256": len({record.input_sha256 for record in records}),
        "max_tokens": max(token_counts),
        "over_n_ctx": 0,
        "sentinel": {
            "tokens": runtime.token_count(sentinel_record.text),
            "vector_sha256": sentinel_sha,
            "seconds": sentinel_seconds,
            "reopen_sha256": reopen_sentinel,
        },
        "longest": {
            "episode_key": longest.source_key,
            "tokens": runtime.token_count(longest.text),
            "vector_sha256": longest_sha,
            "seconds": longest_seconds,
            "reopen_sha256": reopen_longest,
        },
        "cache": cache_state,
        "api_requests_made": 0,
        "outcomes_opened": False,
        "script_sha256": sha256_file(Path(__file__)),
    }
    _write_json(artifact_path, result)
    return result


def populate(
    *,
    mechanism_path: Path = MECHANISM_SURFACE,
    cache_path: Path = CACHE_PATH,
    progress_path: Path = PROGRESS_PATH,
    failure_path: Path = FAILURE_PATH,
) -> dict[str, Any]:
    started = time.time()
    rows = load_mechanism_surface(mechanism_path)
    records = list(iter_inputs(rows))
    runtime = GpuEmbeddingRuntime()
    created = 0
    reused = 0
    processed = 0
    try:
        with EmbeddingCache(cache_path) as cache:
            for record in records:
                if cache.has(record.text):
                    cache.bind_existing(record)
                    reused += 1
                else:
                    tokens = runtime.token_count(record.text)
                    vector = runtime.embed(record.text)
                    cache.put(record, tokens, vector)
                    created += 1
                processed += 1
                if processed % 25 == 0 or processed == len(records):
                    _write_json(
                        progress_path,
                        {
                            "status": "RUNNING" if processed < len(records) else "COMPLETE",
                            "pid": os.getpid(),
                            "processed_bindings": processed,
                            "total_bindings": len(records),
                            "created_vectors": created,
                            "reused_bindings": reused,
                            "elapsed_seconds": time.time() - started,
                            "cache": cache.counts(),
                            "runtime_spec_sha256": runtime_spec_sha256(),
                            "api_requests_made": 0,
                        },
                    )
            verified = cache.verify()
        if failure_path.exists():
            failure_path.unlink()
        return {"status": "COMPLETE", "cache": verified}
    except Exception as error:
        _write_json(
            failure_path,
            {
                "status": "FAILED",
                "pid": os.getpid(),
                "processed_bindings": processed,
                "error_type": type(error).__name__,
                "error": str(error),
            },
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preflight", "populate", "verify"))
    parser.add_argument("--mechanism", type=Path, default=MECHANISM_SURFACE)
    parser.add_argument("--cache", type=Path, default=CACHE_PATH)
    args = parser.parse_args()
    if args.command == "preflight":
        result = seed_and_preflight(mechanism_path=args.mechanism, cache_path=args.cache)
    elif args.command == "populate":
        result = populate(mechanism_path=args.mechanism, cache_path=args.cache)
    else:
        with EmbeddingCache(args.cache, read_only=True) as cache:
            result = cache.verify()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import os

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from episodic import EmbeddingCache
from src.retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256
from src.retrieval_bakeoff.embedding import CarriedEmbedder, normalize_embedding


REPO_ROOT = Path(__file__).resolve().parents[2]
HOLDOUT_ROOT = REPO_ROOT / "experiments" / "surveys" / "retrieval_bakeoff" / "holdout"
QUERY_MANIFESTS = {
    "c1000_l": HOLDOUT_ROOT / "queries_1000.json",
    "c121_l": HOLDOUT_ROOT / "queries_121.json",
}
ALLOWED_DIRTY_PATHS = {"tmp/pr43_body.md"}


@dataclass(frozen=True)
class LockedQuery:
    corpus_id: str
    query_id: str
    text: str
    manifest_path: Path


class NormalizedSoloEmbedder:
    def __init__(self, delegate) -> None:
        self.delegate = delegate
        self.model_sha256 = str(delegate.model_sha256)
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


def load_locked_queries(
    manifests: dict[str, Path] = QUERY_MANIFESTS,
) -> tuple[LockedQuery, ...]:
    queries: list[LockedQuery] = []
    for corpus_id, path in sorted(manifests.items()):
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload["queries"]
        if len(rows) != 24 or len({str(row["query_id"]) for row in rows}) != 24:
            raise AssertionError(f"{corpus_id} must contain 24 unique queries")
        for row in rows:
            queries.append(
                LockedQuery(
                    corpus_id=corpus_id,
                    query_id=str(row["query_id"]),
                    text=str(row["text"]),
                    manifest_path=path,
                )
            )
    ordered = tuple(sorted(queries, key=lambda row: (row.corpus_id, row.query_id)))
    if len(ordered) != 48 or len({row.text for row in ordered}) != 48:
        raise AssertionError("Tier 4A capture requires 48 unique locked query texts")
    return ordered


def populate_cache(
    queries: Sequence[LockedQuery], cache_path: Path, delegate
) -> tuple[dict, list[dict]]:
    normalized = NormalizedSoloEmbedder(delegate)
    vector_rows = []
    with EmbeddingCache(cache_path, mode="populate", embedder=normalized) as cache:
        for query in queries:
            vector = cache(query.text)
            raw = np.asarray(vector, dtype=np.float32).tobytes()
            vector_rows.append(
                {
                    "corpus_id": query.corpus_id,
                    "query_id": query.query_id,
                    "text_sha256": hashlib.sha256(query.text.encode("utf-8")).hexdigest(),
                    "vector_sha256": hashlib.sha256(raw).hexdigest(),
                    "dimension": int(vector.size),
                    "dtype": str(vector.dtype),
                }
            )
    record = cache.record()
    if normalized.calls != len(queries):
        raise AssertionError("Capture did not make exactly one solo request per query")
    if record["entries"] != len(queries) or record["misses"] != len(queries):
        raise AssertionError("Retained cache cardinality differs from query inventory")
    return record, vector_rows


def assert_capture_worktree_clean() -> None:
    output = subprocess.check_output(
        ("git", "status", "--porcelain"), cwd=REPO_ROOT, text=True
    )
    dirty = {
        line[3:].replace("\\", "/")
        for line in output.splitlines()
        if line.strip()
    }
    unexpected = sorted(dirty - ALLOWED_DIRTY_PATHS)
    if unexpected:
        raise RuntimeError(f"Unexpected dirty paths before capture: {unexpected}")


def capture(model_path: Path, cache_path: Path, manifest_path: Path) -> dict:
    assert_capture_worktree_clean()
    if cache_path.exists() or manifest_path.exists():
        raise FileExistsError("Refusing to overwrite retained Tier 4A capture artifacts")
    if importlib.metadata.version("llama-cpp-python") != "0.3.25":
        raise AssertionError("Tier 4A capture requires llama-cpp-python==0.3.25")

    queries = load_locked_queries()
    delegate = CarriedEmbedder(model_path)
    delegate.assert_carried_model()
    record, vectors = populate_cache(queries, cache_path, delegate)
    manifests = {
        corpus_id: {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_file(path),
            "query_count": sum(query.corpus_id == corpus_id for query in queries),
        }
        for corpus_id, path in sorted(QUERY_MANIFESTS.items())
    }
    payload = {
        "study": "E006-P3",
        "stage": "Rev 1 Tier 4A query-vector capture",
        "status": "SEALED",
        "request_count": len(queries),
        "call_shape": "solo",
        "zero_model_generation_calls": True,
        "embedding_requests": len(queries),
        "cache": record,
        "query_manifests": manifests,
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
                name: os.environ[name]
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
        json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture E006-P3 Tier 4A queries")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    result = capture(args.model, args.cache, args.manifest)
    print(json.dumps({"status": result["status"], "requests": result["request_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

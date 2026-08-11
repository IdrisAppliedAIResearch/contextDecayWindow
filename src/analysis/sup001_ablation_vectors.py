from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
from typing import Callable

import numpy as np

from episodic import EmbeddingCache
from src.analysis.sup001_ablation_common import (
    CACHE_PATH,
    SCRIPT_PATH,
    VECTOR_MANIFEST_PATH,
    load_script,
    sha256_file,
    vector_texts,
)
from src.retrieval_bakeoff.embedding import CarriedEmbedder, normalize_embedding


class NormalizedSoloEmbedder:
    def __init__(self, delegate: Callable[[str], np.ndarray]) -> None:
        self.delegate = delegate
        self.model_sha256 = str(getattr(delegate, "model_sha256"))
        self.calls = 0

    def __call__(self, text: str) -> np.ndarray:
        self.calls += 1
        return normalize_embedding(self.delegate(text))


def capture(model_path: Path) -> dict:
    if CACHE_PATH.exists() or VECTOR_MANIFEST_PATH.exists():
        raise FileExistsError("Refusing to overwrite SUP-001 ablation vectors")
    if importlib.metadata.version("llama-cpp-python") != "0.3.25":
        raise AssertionError("SUP-001 ablation requires llama-cpp-python==0.3.25")
    texts = vector_texts(load_script())
    delegate = CarriedEmbedder(model_path)
    delegate.assert_carried_model()
    normalized = NormalizedSoloEmbedder(delegate)
    rows = []
    with EmbeddingCache(CACHE_PATH, mode="populate", embedder=normalized) as cache:
        for text in texts:
            vector = cache(text)
            raw = np.asarray(vector, dtype=np.float32).tobytes()
            rows.append(
                {
                    "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "vector_sha256": hashlib.sha256(raw).hexdigest(),
                    "dimension": int(vector.size),
                    "unit_norm": float(np.linalg.norm(vector)),
                }
            )
    record = cache.record()
    if normalized.calls != 35 or record["entries"] != 35 or record["misses"] != 35:
        raise AssertionError("Ablation vector capture was not 35 solo-call misses")
    payload = {
        "study": "SUP-001",
        "stage": "35-turn ablation vector lock",
        "status": "SEALED",
        "script_sha256": sha256_file(SCRIPT_PATH),
        "text_count": len(texts),
        "episode_vectors": 26,
        "query_vectors": 9,
        "zero_generation_calls": True,
        "cache": record,
        "vectors": rows,
        "source_sha256": sha256_file(Path(__file__)),
    }
    VECTOR_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    VECTOR_MANIFEST_PATH.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload

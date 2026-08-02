"""The carried embedding wrapper, pinned to one text per call.

The batch entry point is deliberately absent. The carried model returns
materially different vectors for the same text depending on whether it is
embedded alone or inside a batch - cosine agreement 0.999837 with a
component difference of 0.217, enough to flip committed selection payloads
(DX-001). Production embeds one text at a time, so that is the only shape
this wrapper offers, and the store asserts a sentinel vector against the
pinned shape on every open.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import numpy as np

from ._errors import EpisodicError

EMBEDDING_DIMENSION = 1_024
MODEL_PATH_VARIABLE = "CDW_EMBEDDING_MODEL_PATH"

# Embedded on every store open under the pinned call shape; the vector hash
# is stored with the store and asserted on reopen.
SENTINEL_TEXT = "episodic call-shape sentinel: one text per call"


class PinnedEmbedder:
    """The carried GGUF embedder, one text per call, single-threaded."""

    def __init__(self, model_path: str | Path | None = None) -> None:
        configured = model_path or os.environ.get(MODEL_PATH_VARIABLE)
        if not configured:
            raise EpisodicError(
                f"Set {MODEL_PATH_VARIABLE} or pass model_path: the default "
                "embedder needs the carried GGUF artifact"
            )
        self.model_path = Path(configured).resolve()
        if not self.model_path.is_file():
            raise EpisodicError(f"Embedding model not found: {self.model_path}")
        self._model_sha256: str | None = None
        self._model = None

    @property
    def model_sha256(self) -> str:
        if self._model_sha256 is None:
            digest = hashlib.sha256()
            with self.model_path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            self._model_sha256 = digest.hexdigest()
        return self._model_sha256

    def __call__(self, text: str) -> np.ndarray:
        return np.asarray(
            self._get_model().embed(text),
            dtype=np.float32,
        ).reshape(EMBEDDING_DIMENSION)

    def _get_model(self):
        if self._model is None:
            try:
                from llama_cpp import Llama
            except ImportError as error:
                raise EpisodicError(
                    "The default embedder needs llama-cpp-python; install "
                    "episodic[llama] or pass your own embedder"
                ) from error
            self._model = Llama(
                model_path=str(self.model_path),
                embedding=True,
                n_gpu_layers=0,
                n_ctx=512,
                n_threads=1,
                n_threads_batch=1,
                verbose=False,
            )
        return self._model


def embed_solo(embedder, text: str) -> np.ndarray:
    """One text, one call - the pinned shape - with a validated result."""
    vector = np.asarray(embedder(text), dtype=np.float32)
    if vector.shape != (EMBEDDING_DIMENSION,):
        raise EpisodicError(
            f"Embedder returned shape {vector.shape}; expected "
            f"({EMBEDDING_DIMENSION},)"
        )
    return vector


def vector_sha256(vector: np.ndarray) -> str:
    return hashlib.sha256(
        np.asarray(vector, dtype=np.float32).tobytes()
    ).hexdigest()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot / (norm_a * norm_b))

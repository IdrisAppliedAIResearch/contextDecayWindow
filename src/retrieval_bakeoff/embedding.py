from __future__ import annotations

import hashlib
import os
from pathlib import Path

import numpy as np
from llama_cpp import Llama

from .config import CARRIED_EMBEDDING_SHA256, EMBEDDING_DIMENSION


def normalize_embedding(vector: np.ndarray) -> np.ndarray:
    array = np.asarray(vector, dtype=np.float32).reshape(EMBEDDING_DIMENSION)
    norm = float(np.linalg.norm(array))
    return array / norm if norm else array


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class CarriedEmbedder:
    """The exact embedding model/provider carried by the completed studies."""

    def __init__(self, model_path: Path | None = None) -> None:
        configured = model_path or (
            Path(os.environ["CDW_EMBEDDING_MODEL_PATH"])
            if os.environ.get("CDW_EMBEDDING_MODEL_PATH")
            else None
        )
        if configured is None:
            raise EnvironmentError(
                "CDW_EMBEDDING_MODEL_PATH is required for registered retrieval"
            )
        self.model_path = configured.resolve()
        if not self.model_path.is_file():
            raise FileNotFoundError(self.model_path)
        os.environ["CDW_EMBEDDING_MODEL_PATH"] = str(self.model_path)
        self._model_sha256: str | None = None
        self._model: Llama | None = None

    @property
    def model_sha256(self) -> str:
        if self._model_sha256 is None:
            self._model_sha256 = sha256_file(self.model_path)
        return self._model_sha256

    def assert_carried_model(self) -> None:
        if self.model_sha256 != CARRIED_EMBEDDING_SHA256:
            raise AssertionError(
                "Embedding artifact does not match the carried Study 007 model"
            )

    def __call__(self, text: str) -> np.ndarray:
        return np.asarray(self._get_model().embed(text), dtype=np.float32).reshape(
            EMBEDDING_DIMENSION
        )

    def embed_many(
        self,
        texts: list[str],
        *,
        batch_size: int = 64,
    ) -> list[np.ndarray]:
        if not texts:
            return []
        model = self._get_model()
        result: list[np.ndarray] = []
        for start in range(0, len(texts), batch_size):
            raw = model.embed(
                texts[start : start + batch_size],
                normalize=False,
                truncate=True,
            )
            result.extend(
                np.asarray(item, dtype=np.float32).reshape(EMBEDDING_DIMENSION)
                for item in raw
            )
        return result

    def warmup(self) -> None:
        self("retrieval bakeoff embedding warmup")

    def _get_model(self) -> Llama:
        if self._model is None:
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

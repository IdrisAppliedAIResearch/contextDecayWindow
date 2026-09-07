"""Content-bound vector cache and contextual token capture; no generation API."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sqlite3

import numpy as np

from .source import canonical, digest

MODEL = Path.home() / ".cache/huggingface/hub/Qwen3-Embedding-0.6B-GGUF/Qwen3-Embedding-0.6B-Q8_0.gguf"
MODEL_HASH = "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
SPEC = dict(model_sha256=MODEL_HASH, runtime="llama-cpp-python-0.3.25", context=8192,
            batch=8192, microbatch=8192, threads=8, seed=5005, pooling="none-target-last",
            call_shape="solo", dtype="float32", dimension=1024)


class Cache:
    def __init__(self, path: Path, *, readonly=False):
        self.path, self.readonly = path, readonly
        if readonly:
            self.db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(path)
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute("CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY, spec TEXT, vector BLOB, sha TEXT)")
        self.hits = self.misses = 0

    def get(self, spec: dict):
        text = canonical(spec)
        row = self.db.execute("SELECT spec,vector,sha FROM vectors WHERE key=?", (digest(text),)).fetchone()
        if row is None:
            self.misses += 1
            if self.readonly:
                raise KeyError("Read-only vector cache miss")
            return None
        if row[0] != text or hashlib.sha256(row[1]).hexdigest() != row[2]:
            raise ValueError("Cache content corruption")
        vector = np.frombuffer(row[1], dtype=np.float32).copy()
        if vector.shape != (1024,) or not np.isfinite(vector).all() or not np.linalg.norm(vector):
            raise ValueError("Invalid cached vector")
        self.hits += 1
        return vector

    def put(self, spec: dict, vector) -> np.ndarray:
        if self.readonly:
            raise PermissionError("Cannot write read-only vectors")
        value = np.asarray(vector, dtype=np.float32)
        if value.shape != (1024,) or not np.isfinite(value).all() or not np.linalg.norm(value):
            raise ValueError("Invalid vector")
        text, raw = canonical(spec), value.tobytes()
        previous = self.db.execute("SELECT vector FROM vectors WHERE key=?", (digest(text),)).fetchone()
        if previous is not None and previous[0] != raw:
            raise ValueError("Refusing to overwrite a different vector")
        self.db.execute("INSERT OR IGNORE INTO vectors VALUES (?,?,?,?)",
                        (digest(text), text, raw, hashlib.sha256(raw).hexdigest()))
        self.db.commit()
        return value

    def close(self):
        self.db.close()


class Encoder:
    def __init__(self, cache: Cache):
        import llama_cpp
        from llama_cpp import Llama
        with MODEL.open("rb") as f:
            assert hashlib.file_digest(f, "sha256").hexdigest() == MODEL_HASH
        assert llama_cpp.__version__ == "0.3.25"
        self.cache = cache
        self.calls = 0
        self.model = Llama(model_path=str(MODEL), embedding=True, n_gpu_layers=-1,
                           n_ctx=8192, n_batch=8192, n_ubatch=8192, n_threads=8,
                           n_threads_batch=8, seed=5005,
                           pooling_type=llama_cpp.LLAMA_POOLING_TYPE_NONE, verbose=False)

    def count(self, text: str) -> int:
        return len(self.model.tokenize(text.encode("utf-8")))

    def states(self, text: str) -> tuple[np.ndarray, list[tuple[int, int]]]:
        raw = text.encode("utf-8")
        tokens = self.model.tokenize(raw)
        if len(tokens) > SPEC["context"]:
            raise ValueError(f"Embedding overflow: {len(tokens)} tokens; no truncation permitted")
        pieces = [self.model.detokenize([t]) for t in tokens]
        if b"".join(pieces) != raw:
            raise ValueError("Token offset reconstruction failed")
        offset, spans = 0, []
        for p in pieces:
            spans.append((offset, offset + len(p)))
            offset += len(p)
        a = np.asarray(self.model.embed(text, truncate=False), dtype=np.float32)
        self.calls += 1
        if a.shape != (len(tokens), 1024) or not np.isfinite(a).all():
            raise ValueError("Token-state shape or finiteness failed")
        return a, spans

    def solo(self, text: str) -> np.ndarray:
        spec = dict(runtime=SPEC, view="independent", text=text)
        vector = self.cache.get(spec)
        if vector is None:
            states, _ = self.states(text)
            vector = self.cache.put(spec, states[-1])
        return vector

    def contextual(self, units) -> tuple[dict[str, np.ndarray], dict[str, list[str]]]:
        """Session windows at whole-unit boundaries; no source content silently clipped."""
        windows, current = [], []
        for unit in units:
            if current and (unit.session != current[-1].session or
                            self.count("\n\n".join(u.text for u in current + [unit])) > 8192):
                windows.append(current)
                current = []
            if self.count(unit.text) > 8192:
                raise ValueError("A source pair exceeds encoder fit; no implicit split")
            current.append(unit)
        if current:
            windows.append(current)
        vectors, membership = {}, {}
        for window in windows:
            text = "\n\n".join(u.text for u in window)
            specs = {u.id: dict(runtime=SPEC, view="contextual-last", text=text,
                                target=u.id, members=[v.id for v in window]) for u in window}
            cached = {u.id: self.cache.get(specs[u.id]) for u in window}
            if any(v is None for v in cached.values()):
                states, spans = self.states(text)
                start = 0
                for unit in window:
                    end = start + len(unit.text.encode("utf-8"))
                    indices = [i for i, (a, b) in enumerate(spans) if b > start and a < end]
                    if not indices:
                        raise ValueError("Context target has no token states")
                    value = states[indices[-1]]
                    if cached[unit.id] is not None and not np.array_equal(cached[unit.id], value):
                        raise ValueError("Context replay changed existing target vector")
                    cached[unit.id] = self.cache.put(specs[unit.id], value)
                    start = end + 2
            for unit in window:
                vectors[unit.id] = cached[unit.id]
                membership[unit.id] = [v.id for v in window]
        return vectors, membership

    def close(self):
        self.model.close()

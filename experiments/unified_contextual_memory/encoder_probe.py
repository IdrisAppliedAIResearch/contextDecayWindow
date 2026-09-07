"""Development-only token-state feasibility; never generates text."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "artifacts" / "encoder_probe"
MODEL = Path.home() / ".cache/huggingface/hub/Qwen3-Embedding-0.6B-GGUF/Qwen3-Embedding-0.6B-Q8_0.gguf"
EXPECTED_MODEL = "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
TARGET = "I accepted the offer."
PREFIXES = {
    "northstar": "I interviewed at Northstar.\n",
    "cedar": "I interviewed at Cedar.\n",
    "cooking": "I cooked vegetable soup.\n",
}


def sha(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def save(name: str, data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open("x", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def digest_array(a: np.ndarray) -> str:
    return hashlib.sha256(a.tobytes()).hexdigest()


def cosine(a, b) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def target_indices(model, text: str, target: str) -> list[int]:
    raw = text.encode("utf-8")
    start = raw.index(target.encode("utf-8"))
    stop = start + len(target.encode("utf-8"))
    tokens = model.tokenize(raw)
    pieces = [model.detokenize([token]) for token in tokens]
    if b"".join(pieces) != raw:
        raise RuntimeError("Token byte pieces do not reproduce original source")
    at, found = 0, []
    for i, piece in enumerate(pieces):
        end = at + len(piece)
        if end > start and at < stop:
            found.append(i)
        at = end
    if not found:
        raise RuntimeError("Target has no tokens")
    return found


def main() -> None:
    import llama_cpp
    from llama_cpp import Llama
    assert sha(MODEL) == EXPECTED_MODEL
    assert llama_cpp.__version__ == "0.3.25"
    spec = dict(model_path=str(MODEL), embedding=True, n_gpu_layers=-1,
                n_ctx=8192, n_batch=8192, n_ubatch=8192, n_threads=8,
                n_threads_batch=8, seed=5005, verbose=False)
    library = Path(llama_cpp.__file__).parent
    save("header.json", dict(
        model_sha256=EXPECTED_MODEL, script_sha256=sha(Path(__file__)),
        design_sha256=sha(ROOT / "experiments/designs/unified_contextual_memory/DESIGN.md"),
        commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        runtime=spec, llama_cpp=llama_cpp.__version__,
        libraries={str(p): sha(p) for p in sorted(library.rglob("*.dll"))},
        generative_calls=0,
    ))
    started = time.monotonic()
    native = Llama(**spec)
    native_pooling = native.pooling_type()
    native_vector = np.asarray(native.embed(TARGET, truncate=False), dtype=np.float32)
    native.close()
    token_model = Llama(**spec, pooling_type=llama_cpp.LLAMA_POOLING_TYPE_NONE)
    arrays, metadata = {}, {}
    texts = {"solo": TARGET, **{k: p + TARGET for k, p in PREFIXES.items()}}
    texts["future"] = texts["northstar"] + "\nThe offer was from Cedar."
    for name, text in texts.items():
        count = len(token_model.tokenize(text.encode("utf-8")))
        assert count <= 8192
        states = np.asarray(token_model.embed(text, truncate=False), dtype=np.float32)
        assert states.shape == (count, 1024) and np.isfinite(states).all()
        indices = target_indices(token_model, text, TARGET)
        arrays[name + "_last"] = states[indices[-1]].copy()
        arrays[name + "_mean"] = states[indices].mean(axis=0, dtype=np.float64).astype(np.float32)
        if name == "solo":
            repeated = np.asarray(token_model.embed(text, truncate=False), dtype=np.float32)
            assert np.array_equal(states, repeated), "Repeated token states differ"
            assert np.array_equal(native_vector, states[-1]), "Native last pooling differs"
        metadata[name] = dict(text=text, token_count=count, target_indices=indices,
                              states_sha256=digest_array(states))
    token_model.close()
    assert native_pooling == llama_cpp.LLAMA_POOLING_TYPE_LAST
    save("raw.json", dict(native_pooling=native_pooling, texts=metadata,
         vectors={k: v.tolist() for k, v in arrays.items()},
         native_vector=native_vector.tolist(), seconds=time.monotonic() - started,
         generative_calls=0))
    result = dict(
        native_last_exact=True, solo_token_replay_exact=True, byte_offsets_exact=True,
        native_pooling=native_pooling, dimension=1024,
        contextual_cosines={mode: {
            key: cosine(arrays["solo_" + mode], arrays[key + "_" + mode])
            for key in PREFIXES} for mode in ("last", "mean")},
        future_last_max_absolute_difference=float(np.max(np.abs(arrays["northstar_last"] - arrays["future_last"]))),
        future_last_cosine=cosine(arrays["northstar_last"], arrays["future_last"]),
        artifacts={name: sha(OUT / name) for name in ("header.json", "raw.json")},
        status="MECHANICAL_FEASIBILITY_ONLY", generative_calls=0)
    save("result.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        save("failure.json", dict(type=type(exc).__name__, message=str(exc)))
        raise

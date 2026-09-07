"""Freeze source-only parser annotations and independent extractive cue vectors."""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import importlib.metadata
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from unified_memory.source import Unit
from unified_memory.references import extract
from unified_memory.encoder import Cache, Encoder
from prepare import read_rows, write_rows, write_json, sha

P = Path(__file__).parent
OUT = P / "artifacts" / "references"


def main():
    import spacy
    assert spacy.__version__ == "3.8.14"
    assert importlib.metadata.version("en-core-web-sm") == "3.8.0"
    OUT.mkdir(parents=True, exist_ok=True)
    units = [Unit(**r) for r in read_rows(P / "artifacts/prepared/sources.jsonl.gz")]
    model = spacy.load("en_core_web_sm")
    workers = min(8, os.cpu_count() or 1)
    started = time.monotonic()
    refs = []
    for unit, doc in zip(units, model.pipe((u.text for u in units), n_process=workers, batch_size=64), strict=True):
        refs.extend(extract(unit, doc))
    write_rows(OUT / "references.jsonl.gz", [r.serialize() for r in refs])
    parse_seconds = time.monotonic() - started
    print(json.dumps(dict(stage="parsed", references=len(refs), workers=workers, seconds=parse_seconds)), flush=True)
    cache = Cache(P / "artifacts/vectors.db")
    encoder = Encoder(cache)
    vectors = {}
    try:
        for i, ref in enumerate(refs, 1):
            vectors[ref.id] = encoder.solo(ref.text)
            if i % 500 == 0:
                write_json(OUT / "progress.json", dict(done=i, total=len(refs), encoder_calls=encoder.calls), exclusive=False)
                print(json.dumps(dict(done=i, total=len(refs), encoder_calls=encoder.calls)), flush=True)
        calls = encoder.calls
    finally:
        encoder.close()
        cache.close()
    with (OUT / "vectors.npz").open("xb") as f:
        np.savez_compressed(f, **vectors)
    write_json(OUT / "manifest.json", dict(
        references=len(refs), units=len(units), parse_seconds=parse_seconds,
        seconds=time.monotonic()-started, workers=workers, encoder_calls=calls,
        parser="en_core_web_sm-3.8.0", spacy=spacy.__version__, generative_calls=0,
        source_sha256=sha(P / "artifacts/prepared/sources.jsonl.gz"),
        files={n: sha(OUT / n) for n in ("references.jsonl.gz", "vectors.npz")},
        code={str(p.relative_to(ROOT)): sha(p) for p in
              [Path(__file__), ROOT / "src/unified_memory/references.py"]},
        parser_files={str(p.relative_to(Path(model.path))):sha(p) for p in sorted(Path(model.path).rglob("*")) if p.is_file()}))
    print(json.dumps(dict(status="CAPTURED", references=len(refs), calls=calls)))


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        write_json(OUT / "failure.json", dict(type=type(exc).__name__, message=str(exc)))
        raise

"""Phase A source parity, historical replay, and durable vector capture."""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from collections import Counter

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from unified_memory.source import adapt, canonical, digest
from unified_memory.encoder import Cache, Encoder, SPEC
from unified_memory.control import cosine_matrix
from analysis import lv009_exploration as prior

P = Path(__file__).parent
OUT = P / "artifacts" / "prepared"
OLD = ROOT / "experiments/locomo_relevance_timeline/artifacts"
CONTROL = Path("C:/Users/muzaf/contextDecayWindow-unified-control")


def sha(p):
    with Path(p).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def read_rows(p):
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_json(p, value, *, exclusive=True):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("x" if exclusive else "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write("\n")


def write_rows(p, rows):
    with p.open("xb") as f:
        with gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as g:
            for row in rows:
                g.write((canonical(row) + "\n").encode("utf-8"))


def main():
    if (OUT / "manifest.json").exists():
        raise RuntimeError("Prepared artifacts already sealed")
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=CONTROL, text=True).strip().startswith("946c373d")
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=CONTROL, text=True).strip()
    OUT.mkdir(parents=True, exist_ok=True)
    cases = prior.load_blind_cases()
    historical, old_caches = prior.load_full_vectors(cases)
    old_adapter = {r["id"]: r for r in read_rows(OLD / "adapter.jsonl.gz")}
    old_prompts = {r["key"]: r for r in read_rows(OLD / "prompts.jsonl.gz")}
    selections = read_rows(OLD / "selections.jsonl.gz")
    for row in selections:
        matrix = cosine_matrix([historical[old_adapter[key]["text"]] for key in row["ids"]])
        q = historical[old_prompts[row["key"]]["question"]].astype(np.float64)
        scores = matrix @ (q / np.linalg.norm(q))
        assert np.array_equal(scores, np.asarray(row["scores"]))
        selected = [key for key, score in zip(row["ids"], scores) if score >= .48]
        assert selected == row["selected"]
        block = "\n".join(old_adapter[key]["element"] for key in selected)
        assert digest(block) == row["block_sha256"]
    assert len(selections) == 1986
    write_json(OUT / "historical_replay.json", dict(groups=1986, exact_scores=True,
               exact_ids=True, exact_payloads=True, caches=old_caches, generative_calls=0))
    raw = json.loads(prior.DATASET_PATH.read_text(encoding="utf-8"))
    source = {str(r["sample_id"]): r["conversation"] for r in raw}
    all_units = {key: adapt(conversation, key) for key, conversation in sorted(source.items())}
    questions = [{k: row[k] for k in ("key", "conversation", "question", "source_index", "ordinal")}
                 for row in sorted(old_prompts.values(), key=lambda r: r["key"])]
    write_rows(OUT / "sources.jsonl.gz", [u.serialize() for group in all_units.values() for u in group])
    write_rows(OUT / "questions.jsonl.gz", questions)
    cache = Cache(P / "artifacts/vectors.db")
    encoder = Encoder(cache)
    vectors, origins, contexts, counts = {}, {}, {}, Counter()
    started = time.monotonic()
    try:
        for number, (conversation, units) in enumerate(all_units.items(), 1):
            for unit in units:
                key = "d_" + unit.id
                if unit.text in historical:
                    vectors[key] = historical[unit.text]
                    origins[key] = "historical-solo-cache"
                else:
                    vectors[key] = encoder.solo(unit.text)
                    origins[key] = "new-source-caption-solo"
                counts[origins[key]] += 1
            contextual, membership = encoder.contextual(units)
            vectors.update({"c_" + key: value for key, value in contextual.items()})
            contexts.update(membership)
            progress = dict(conversations_done=number, total=10, encoder_calls=encoder.calls,
                            elapsed_seconds=time.monotonic() - started, generative_calls=0)
            write_json(OUT / "progress.json", progress, exclusive=False)
            print(json.dumps(progress), flush=True)
        for row in questions:
            vectors["q_" + row["key"]] = historical[row["question"]]
        with (OUT / "vectors.npz").open("xb") as f:
            np.savez_compressed(f, **vectors)
        write_json(OUT / "contexts.json", contexts)
        write_json(OUT / "origins.json", origins)
        encoder_calls = encoder.calls
    finally:
        encoder.close()
        cache.close()
    files = ["historical_replay.json", "sources.jsonl.gz", "questions.jsonl.gz",
             "vectors.npz", "contexts.json", "origins.json"]
    write_json(OUT / "manifest.json", dict(
        status="SOURCE_AND_CONTEXT_CAPTURED", corpus_sha256=sha(prior.DATASET_PATH),
        source_units=sum(len(u) for u in all_units.values()), questions=len(questions),
        origins=dict(counts), encoder_calls=encoder_calls, generative_calls=0,
        runtime=SPEC, historical_caches=old_caches,
        files={f: sha(OUT / f) for f in files},
        code={str(p.relative_to(ROOT)): sha(p) for p in
              [Path(__file__), *sorted((ROOT / "src/unified_memory").glob("*.py"))]},
        control_commit="946c373d", seconds=time.monotonic()-started))
    print(json.dumps(dict(status="CAPTURED", counts=dict(counts), encoder_calls=encoder_calls)))


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        write_json(OUT / "failure.json", dict(type=type(exc).__name__, message=str(exc)))
        raise

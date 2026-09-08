"""Locked mismatch-tail calibration. No answers or evidence annotations are read."""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "8"
os.environ["OMP_NUM_THREADS"] = "8"
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from unified_memory.control import cosine_matrix
from prepare import read_rows, write_json, sha

P = Path(__file__).parent / "artifacts"
OUT = P / "calibration"


def load_vectors(path):
    with np.load(path) as f:
        return {key: f[key] for key in f.files}


def summarize(values):
    quantiles = [0, .01, .05, .1, .25, .5, .75, .9, .95, .975, .99, .995, .999, 1]
    return dict(count=int(values.size), mean=float(values.mean()),
                quantiles={str(q):float(np.quantile(values, q, method="higher")) for q in quantiles},
                sha256=hashlib.sha256(values.tobytes()).hexdigest())


def main():
    started = time.monotonic()
    for directory in (P / "prepared", P / "references"):
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        for name, expected in manifest["files"].items():
            assert sha(directory / name) == expected
    sources = read_rows(P / "prepared/sources.jsonl.gz")
    queries = read_rows(P / "prepared/questions.jsonl.gz")
    references = read_rows(P / "references/references.jsonl.gz")
    v = load_vectors(P / "prepared/vectors.npz")
    rv = load_vectors(P / "references/vectors.npz")
    source_conv = {r["id"]: r["conversation"] for r in sources}
    convs = sorted(set(source_conv.values()))
    dm = cosine_matrix([v["d_" + r["id"]] for r in sources])
    cm = cosine_matrix([v["c_" + r["id"]] for r in sources])
    results, thresholds = {}, {}
    populations = {
        "contextual": (queries, lambda r:r["conversation"], lambda r:v["q_" + r["key"]], cm),
        "support": (sources, lambda r:r["conversation"], lambda r:v["d_" + r["id"]], dm),
        "reference": (references, lambda r:source_conv[r["unit_id"]], lambda r:rv[r["id"]], dm),
    }
    for name, (rows, group, vector, candidates) in populations.items():
        chunks, groups = [], {}
        for conv in convs:
            cues = [vector(row) for row in rows if group(row) == conv]
            other = [i for i, r in enumerate(sources) if r["conversation"] != conv]
            scores = (cosine_matrix(cues) @ candidates[other].T).reshape(-1)
            chunks.append(scores)
            groups[conv] = summarize(scores)
        joined = np.concatenate(chunks)
        results[name] = dict(overall=summarize(joined), conversations=groups)
        thresholds[name] = float(np.quantile(joined, .99, method="higher"))
        print(json.dumps(dict(route=name, count=joined.size, threshold=thresholds[name])), flush=True)
        del joined, chunks
    write_json(OUT / "distributions.json", results)
    write_json(OUT / "policy.json", dict(thresholds=thresholds, alpha=.01,
               method="cross-conversation-99th-percentile-higher", direct_threshold=.48,
               design_commit="2a94b0f8", generative_calls=0))
    write_json(OUT / "manifest.json", dict(
        seconds=time.monotonic()-started, generative_calls=0, workers=8,
        code_sha256=sha(Path(__file__)),
        inputs={str(p.relative_to(P)):sha(p) for p in
                [P / "prepared/manifest.json", P / "references/manifest.json"]},
        outputs={n:sha(OUT / n) for n in ("policy.json", "distributions.json")}))


if __name__ == "__main__":
    main()

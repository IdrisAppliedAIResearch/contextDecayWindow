"""No-answer development replay: expansion, runtime, and semantic-route identity."""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from unified_memory.source import Unit, render, digest, canonical
from unified_memory.references import Reference
from unified_memory.retrieval import Policy, retrieve
from unified_memory.control import cosine_matrix
from prepare import read_rows, write_json, write_rows, sha

P = Path(__file__).parent / "artifacts"


def worker(conversation):
    units = [Unit(**r) for r in read_rows(P / "prepared/sources.jsonl.gz") if r["conversation"] == conversation]
    ids = [u.id for u in units]
    refs = [Reference(**r) for r in read_rows(P / "references/references.jsonl.gz") if r["unit_id"] in ids]
    queries = [r for r in read_rows(P / "prepared/questions.jsonl.gz") if r["conversation"] == conversation]
    v = np.load(P / "prepared/vectors.npz")
    rv = np.load(P / "references/vectors.npz")
    direct = {key:v["d_" + key] for key in ids}
    contextual = {key:v["c_" + key] for key in ids}
    cues = {r.id:rv[r.id] for r in refs}
    contexts = json.loads((P / "prepared/contexts.json").read_text(encoding="utf-8"))
    policy = Policy(**json.loads((P / "calibration/policy.json").read_text(encoding="utf-8"))["thresholds"])
    matrix = cosine_matrix([direct[key] for key in ids])
    # Same GEMV arithmetic as the uncached mechanism; compute once per fixed cue.
    scores = {r.id:matrix @ (cues[r.id].astype(np.float64) / np.linalg.norm(cues[r.id].astype(np.float64))) for r in refs}
    cache = dict(ids=ids, references=scores, support=[matrix @ row for row in matrix])
    rows, traces = [], []
    started = time.monotonic()
    total_chars = len(render(units, set(ids)))
    for index, q in enumerate(queries):
        result = retrieve(units, direct, contextual, contexts, refs, cues, v["q_" + q["key"]], policy, static_scores=cache)
        if index == 0:
            slow = retrieve(units, direct, contextual, contexts, refs, cues, v["q_" + q["key"]], policy)
            assert canonical(slow) == canonical(result), "Static score replay differs"
        chars = len(render(units, set(result["selected"])))
        control_chars = len(render(units, set(result["direct"])))
        rows.append(dict(key=q["key"], conversation=conversation, sources=len(ids),
                         direct=len(result["direct"]), selected=len(result["selected"]),
                         selected_ids=result["selected"], direct_ids=result["direct"],
                         contextual=len(result["contextual"]),
                         source_fraction=len(result["selected"])/len(ids),
                         char_fraction=chars/total_chars, direct_char_fraction=control_chars/total_chars,
                         operations=result["operations"], bound=result["operation_bound"],
                         bindings=len(result["bindings"]),
                         evidence_sha256=digest(render(units, set(result["selected"])))))
        if index < 2:
            traces.append(dict(key=q["key"], trace=result))
    v.close()
    rv.close()
    return dict(conversation=conversation, rows=rows, traces=traces,
                seconds=time.monotonic()-started, cached_replay_exact=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="characterization_v1")
    args = parser.parse_args()
    out = P / args.output
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise RuntimeError("Do not overwrite characterization")
    conversations = sorted({r["conversation"] for r in read_rows(P / "prepared/questions.jsonl.gz")})
    workers = min(8, os.cpu_count() or 1)
    started = time.monotonic()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(worker, conversations):
            results.append(result)
            print(json.dumps(dict(conversation=result["conversation"], seconds=result["seconds"])), flush=True)
    rows = [r for result in results for r in result["rows"]]
    write_rows(out / "selections.jsonl.gz", rows)
    write_rows(out / "traces.jsonl.gz", [r for result in results for r in result["traces"]])
    summary = dict(questions=len(rows), workers=workers, seconds=time.monotonic()-started,
                   generative_calls=0, cached_replay_exact=all(r["cached_replay_exact"] for r in results),
                   full_corpus=sum(r["selected"] == r["sources"] for r in rows),
                   at_least_90_percent=sum(r["char_fraction"] >= .9 for r in rows),
                   median_char_fraction=float(np.median([r["char_fraction"] for r in rows])),
                   median_control_char_fraction=float(np.median([r["direct_char_fraction"] for r in rows])),
                   direct_retained=all(set(r["direct_ids"]).issubset(r["selected_ids"]) for r in rows),
                   finite=all(r["operations"] <= r["bound"] for r in rows),
                   per_conversation={c:dict(median_char_fraction=float(np.median([r["char_fraction"] for r in rows if r["conversation"] == c]))) for c in conversations})
    write_json(out / "summary.json", summary)
    write_json(out / "manifest.json", dict(
        policy_sha256=sha(P / "calibration/policy.json"),
        code={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__), ROOT / "src/unified_memory/retrieval.py"]},
        outputs={name:sha(out / name) for name in ("selections.jsonl.gz", "traces.jsonl.gz", "summary.json")}))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()

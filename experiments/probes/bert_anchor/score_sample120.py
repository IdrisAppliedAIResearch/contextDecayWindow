"""AF-PRE-001 sample scoring: four arms on LoCoMo sample-120 + E fidelity line.

Registered in AMENDMENT_001: gold = earliest-evidence turn; top-1 equals gold;
dispositions bind only as written there. E fidelity line checks baseline
recovery of the 17 anchors with pre-stated expectation LEX=BM25=17/17.
QWEN-BI runs first (CPU GGUF, embeddings); CE loads on GPU afterward and frees.
No reader LLM is loaded at any point.
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'src'))
import arms  # noqa: E402

E_INPUTS = ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs'
OUT = HERE / 'part1_artifacts'


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - s) / d, 4), round((c + s) / d, 4))


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def top1(scores, ids):
    best = max(scores)
    tie = [i for i, s in enumerate(scores) if s == best]

    def key(i):
        head = ids[i]
        if ':' in head and head.split(':')[0][1:].isdigit():
            return (0, int(head.split(':')[0][1:]), int(head.split(':')[1]))
        return (1, i, i)
    order = sorted(tie, key=key)
    return ids[order[0]]


def main():
    pool = json.loads((OUT / 'part1e_locomo_pool.json').read_text(encoding='utf-8'))['sample']
    convs = arms.load_conversations(r'C:\Users\muzaf\Downloads\locomo10.json')
    by_conv = {}
    for item in pool:
        by_conv.setdefault(item['sample_id'], []).append(item)

    results = {arm: {'hit': 0, 'per_item': {}} for arm in ['LEX', 'BM25', 'QWEN-BI', 'CE']}
    qwen_cache_path = OUT / 'qwen_cache.json'

    for cid, items in by_conv.items():
        turns = convs[cid]
        ids = [i for i, _ in turns]
        texts = [t for _, t in turns]
        bm25 = arms.BM25(texts)
        for item in items:
            q = item['question']
            gold = item['gold_anchor_earliest']
            preds = {}
            lex = arms.lex_scores(q, texts)
            preds['LEX'] = top1(lex, ids) if max(lex) > 0 else None
            preds['BM25'] = top1(bm25.score(q), ids)
            preds['QWEN-BI'] = top1(qwen_run(q, texts, qwen_cache_path), ids)
            for arm_name, pred in preds.items():
                results[arm_name]['per_item'][item['qid']] = (pred == gold)
            item['_preds'] = preds
        print(f'{cid} done', flush=True)

    tokn, model = arms.load_ce()
    for cid, items in by_conv.items():
        turns = convs[cid]
        ids = [i for i, _ in turns]
        texts = [t for _, t in turns]
        for item in items:
            s = arms.ce_scores(tokn, model, item['question'], texts)
            pred = top1(s, ids)
            results['CE']['per_item'][item['qid']] = pred == item['gold_anchor_earliest']
            item['_preds']['CE'] = pred
    del model
    import torch
    torch.cuda.empty_cache()

    n = len(pool)
    summary = {}
    for arm_name in results:
        k = sum(results[arm_name]['per_item'].values())
        summary[arm_name] = dict(top1=k, n=n, rate=round(k / n, 4), wilson95=wilson(k, n))
    contrasts = {}
    for base in ['LEX', 'BM25', 'QWEN-BI']:
        b = sum(1 for it in pool if results['CE']['per_item'][it['qid']] and not results[base]['per_item'][it['qid']])
        c = sum(1 for it in pool if not results['CE']['per_item'][it['qid']] and results[base]['per_item'][it['qid']])
        contrasts[f'CE_vs_{base}'] = dict(ce_only=b, base_only=c, net=b - c, p=round(mcnemar_exact(b, c), 6))
    ambiguous = [it for it in pool if it['gold_anchor_earliest'] != it['gold_anchor_latest']]
    audit = [dict(qid=it['qid'], question=it['question'], earliest=it['gold_anchor_earliest'],
                  latest=it['gold_anchor_latest'], preds=it['_preds']) for it in ambiguous]
    (OUT / 'sample120_audit_items.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')

    e_fidelity = e_line()
    report = dict(summary=summary, contrasts=contrasts, ambiguous_n=len(ambiguous), e_fidelity=e_fidelity)
    (OUT / 'sample120_results.json').write_text(json.dumps(
        dict(report, per_item={a: results[a]['per_item'] for a in results}), indent=2), encoding='utf-8')
    print(json.dumps(report, indent=1))


_QWEN_CACHE = {}


def qwen_run(query, texts, cache_path):
    import os
    os.environ.setdefault('CDW_EMBEDDING_MODEL_PATH', str(arms.EMBEDDING_GGUF))
    import hashlib
    import numpy as np
    from embeddings.provider import embed
    global _QWEN_CACHE
    if not _QWEN_CACHE:
        _QWEN_CACHE = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
    vectors = []
    dirty = False
    for t in texts:
        k = hashlib.sha256(t.encode()).hexdigest()
        if k not in _QWEN_CACHE:
            _QWEN_CACHE[k] = embed(t).tolist()
            dirty = True
        vectors.append(_QWEN_CACHE[k])
    if dirty:
        cache_path.write_text(json.dumps(_QWEN_CACHE), encoding='utf-8')
    V = np.array(vectors, dtype=np.float32)
    V /= np.maximum(np.linalg.norm(V, axis=1, keepdims=True), 1e-9)
    qv = np.array(embed(query), dtype=np.float32)
    qv /= max(float(np.linalg.norm(qv)), 1e-9)
    return (V @ qv).tolist()


def e_line():
    import collections
    curves = [r for r in json.loads((ROOT / 'experiments/probes/retrieval_score_curves/artifacts/curves.json').read_text(encoding='utf-8'))
              if r['study'] == 'E' and r['type'] in ('straight', 'irrelevant', 'future', 'proposal')]
    sources = {h['id']: h for h in json.loads((E_INPUTS / 'sources.json').read_text(encoding='utf-8'))}
    blind = {r['id']: r for r in json.loads((ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json').read_text(encoding='utf-8'))}
    gaps = [c for c in curves if blind[c['id']]['arms']['PURE']['anchor_exceptions']]
    assert len(gaps) == 17
    tokn, model = arms.load_ce()
    out = {a: 0 for a in ['LEX', 'BM25', 'QWEN-BI', 'CE']}
    for c in gaps:
        eps = sources[c['history']]['episodes']
        anchor = blind[c['id']]['arms']['ANCHORED']['anchor_exceptions'][0]
        texts = [e['user_message'] + '\n' + e['assistant_message'] for e in eps]
        ids = [e['id'] for e in eps]
        order = {i: n for n, i in enumerate(ids)}
        lex = arms.lex_scores(c['query'], texts)
        preds = {'LEX': top1(lex, ids) if max(lex) > 0 else None,
                 'BM25': top1(arms.BM25(texts).score(c['query']), ids),
                 'QWEN-BI': top1(qwen_run(c['query'], texts, OUT / 'qwen_cache.json'), ids),
                 'CE': top1(arms.ce_scores(tokn, model, c['query'], texts), ids)}
        for a, p in preds.items():
            out[a] += int(p == anchor)
    del model
    import torch
    torch.cuda.empty_cache()
    return dict(gaps=17, recovered=out)


if __name__ == '__main__':
    main()

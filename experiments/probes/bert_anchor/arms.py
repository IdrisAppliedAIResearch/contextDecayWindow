"""AF-PRE-001 arms: LEX, BM25, QWEN-BI (carried, CPU GGUF), CE (pinned MiniLM, GPU).

Fixture gate first (plan 6b): arms must reproduce the registered expectations in
AF_PRE_001_FIXTURES.md before any sample scoring. Models load serially: QWEN-BI
is CPU GGUF via the carried provider; CE is a single small torch model loaded,
used, and freed per process phase. No reader LLM is ever loaded.
"""
import collections
import hashlib
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'src'))

EMBEDDING_GGUF = Path.home() / '.cache/huggingface/hub/Qwen3-Embedding-0.6B-GGUF/Qwen3-Embedding-0.6B-Q8_0.gguf'
CE_REPO = 'cross-encoder/ms-marco-MiniLM-L-6-v2'
CE_REVISION = '233902d25c440f23af6f7d6e94d2946bac0bee0a'

FIXTURES = [
    dict(id='F1', conv='conv-26', question='When did Caroline attend a pride parade in August?',
         gold='D11:4', neg='D10:7', bm25=(15.55, 18.80)),
    dict(id='F2', conv='conv-48',
         question="What was one of Jolene's favorite games to play with her mom on the nintendo wii game system?",
         gold='D24:10', neg='D24:9', bm25=(13.82, 39.73)),
    dict(id='F3', conv='conv-44', question='What special memories does Audrey have with her childhood dog, Max?',
         gold='D13:10', neg='D13:8', bm25=(18.77, 35.81)),
    dict(id='F4', conv='conv-50', question="What fuels Calvin's soul?", gold='D7:11', neg='D1:2', bm25=(19.24, 3.54)),
    dict(id='F5', conv='conv-42',
         question='What inspired Joanna to take a picture of the sunset in the field near Fort Wayne?',
         gold='D28:22', neg='D22:9', bm25=(47.73, 18.11)),
]
BM25_MUST_FAIL = {'F1', 'F2', 'F3'}
CE_EXPECTED_PASS = {'F3', 'F4', 'F5'}
CE_EXPECTED_FAIL = {'F2'}


def load_conversations(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    out = {}
    for conv in data:
        turns = []
        for k, v in conv['conversation'].items():
            if k.startswith('session_') and isinstance(v, list):
                turns += [(t['dia_id'], t['text']) for t in v]
        out[conv['sample_id']] = turns
    return out


def tok(s):
    return [w.lower().strip('.,!?()"\u2019\u2018\u201c\u201d') for w in s.split()]


class BM25:
    def __init__(self, texts):
        self.docs = [tok(t) for t in texts]
        self.df = collections.Counter(w for d in self.docs for w in set(d))
        self.n = len(self.docs)

    def score(self, query):
        q = tok(query)
        out = []
        for d in self.docs:
            tf = collections.Counter(d)
            out.append(sum((1 + math.log1p(tf[w])) * math.log(1 + (self.n - self.df[w] + .5) / (self.df[w] + .5))
                           for w in q if w in tf))
        return out


def lex_scores(query, texts):
    spans = [s for s in _quoted(query)]
    return [1.0 if any(f'"{s}"' in t for s in spans) else 0.0 for t in texts]


def _quoted(query):
    import re
    return re.findall(r'"([^"]+)"', query)


def qwen_scores(query, texts, cache_path):
    import numpy as np
    os.environ.setdefault('CDW_EMBEDDING_MODEL_PATH', str(EMBEDDING_GGUF))
    from embeddings.provider import embed
    cache = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding='utf-8'))
    keys = [hashlib.sha256(t.encode()).hexdigest() for t in texts]
    vectors = []
    for t, k in zip(texts, keys):
        if k not in cache:
            cache[k] = embed(t).tolist()
        vectors.append(cache[k])
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache), encoding='utf-8')
    import numpy as np
    V = np.array(vectors, dtype=np.float32)
    V /= np.maximum(np.linalg.norm(V, axis=1, keepdims=True), 1e-9)
    qv = np.array(embed(query), dtype=np.float32)
    qv /= max(float(np.linalg.norm(qv)), 1e-9)
    return (V @ qv).tolist()


def load_ce():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tokn = AutoTokenizer.from_pretrained(CE_REPO, revision=CE_REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(CE_REPO, revision=CE_REVISION)
    model.to('cuda' if torch.cuda.is_available() else 'cpu').eval()
    return tokn, model


def ce_scores(tokn, model, query, texts, batch=256):
    import torch
    out = []
    with torch.inference_mode():
        for i in range(0, len(texts), batch):
            chunk = texts[i:i + batch]
            enc = tokn([query] * len(chunk), chunk, padding=True, truncation=True, max_length=512,
                       return_tensors='pt').to(next(model.parameters()).device)
            out.extend(model(**enc).logits.squeeze(-1).float().cpu().tolist())
    return out


def fixture_gate(mode):
    convs = load_conversations(r'C:\Users\muzaf\Downloads\locomo10.json')
    report = {}
    for f in FIXTURES:
        turns = convs[f['conv']]
        texts = [t for _, t in turns]
        ids = [i for i, _ in turns]
        gi, ni = ids.index(f['gold']), ids.index(f['neg'])
        res = {}
        lex = lex_scores(f['question'], texts)
        res['LEX'] = lex[gi] > lex[ni]
        bm = BM25(texts).score(f['question'])
        res['BM25'] = bm[gi] > bm[ni]
        res['BM25_scores'] = (round(bm[gi], 2), round(bm[ni], 2))
        if mode in ('qwen', 'both'):
            qs = qwen_scores(f['question'], texts, HERE / 'part1_artifacts/qwen_cache.json')
            res['QWEN-BI'] = qs[gi] > qs[ni]
        report[f['id']] = res
    if mode in ('both',):
        tokn, model = load_ce()
        for f in FIXTURES:
            turns = convs[f['conv']]
            texts = [t for _, t in turns]
            ids = [i for i, _ in turns]
            gi, ni = ids.index(f['gold']), ids.index(f['neg'])
            cs = ce_scores(tokn, model, f['question'], texts)
            report[f['id']]['CE'] = cs[gi] > cs[ni]
        del model
        import torch
        torch.cuda.empty_cache()
    checks = []
    for f in FIXTURES:
        r = report[f['id']]
        checks.append(('BM25 reproduces registered scores',
                       abs(r['BM25_scores'][0] - f['bm25'][0]) < .02 and abs(r['BM25_scores'][1] - f['bm25'][1]) < .02))
        checks.append((f"BM25 must fail {f['id']}" if f['id'] in BM25_MUST_FAIL else f"BM25 must pass {f['id']}",
                       r['BM25'] != (f['id'] in BM25_MUST_FAIL)))
        if 'CE' in r:
            want = r['CE'] == (f['id'] in CE_EXPECTED_PASS)
            checks.append((f"CE matches registered expectation {f['id']} ({'pass' if r['CE'] else 'fail'})", want))
    if 'CE' in next(iter(report.values())):
        ce_pass = sum(report[f]['CE'] for f in report)
        checks.append(('CE instrument floor >= 2/5', ce_pass >= 2))
    if any('QWEN-BI' in r for r in report.values()):
        qw = sum(r.get('QWEN-BI', False) for r in report.values())
        checks.append(('QWEN-BI instrument floor >= 2/5', qw >= 2))
    return dict(fixtures=report, checks=[dict(name=n, ok=bool(o)) for n, o in checks],
                passed=all(o for _, o in checks))


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'lex_bm25'
    rep = fixture_gate(mode)
    out = HERE / 'part1_artifacts' / f'fixture_gate_{mode}.json'
    out.write_text(json.dumps(rep, indent=2), encoding='utf-8')
    print(json.dumps(rep, indent=1))
    sys.exit(0 if rep['passed'] else 1)

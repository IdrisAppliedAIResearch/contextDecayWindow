"""Check BM25 pair behaviour for the registered fixture candidates (exploration)."""
import collections
import json
import math
from pathlib import Path

data = json.loads(Path(r'C:\Users\muzaf\Downloads\locomo10.json').read_text(encoding='utf-8'))
convs = {c['sample_id']: c for c in data}

PAIRS = [
    ('conv-26', 'When did Caroline attend a pride parade in August?', 'D11:4', 'D10:7'),
    ('conv-48', "What was one of Jolene's favorite games to play with her mom on the nintendo wii game system?", 'D24:10', 'D24:9'),
    ('conv-44', 'What special memories does Audrey have with her childhood dog, Max?', 'D13:10', 'D13:8'),
    ('conv-50', "What fuels Calvin's soul?", 'D7:11', 'D1:2'),
    ('conv-42', 'What inspired Joanna to take a picture of the sunset in the field near Fort Wayne?', 'D28:22', 'D22:9'),
]


def turns(cid):
    out = []
    for k, v in convs[cid]['conversation'].items():
        if k.startswith('session_') and isinstance(v, list):
            out += [(t['dia_id'], t['text']) for t in v]
    return out


def tok(s):
    return [w.lower().strip('.,!?()"\u2019\u2018\u201c\u201d') for w in s.split()]


for cid, q, g, ng in PAIRS:
    ts = turns(cid)
    docs = [tok(t) for _, t in ts]
    df = collections.Counter(w for d in docs for w in set(d))
    N = len(docs)

    def sc(text):
        d = tok(text)
        tf = collections.Counter(d)
        return sum((1 + math.log1p(tf[w])) * math.log(1 + (N - df[w] + .5) / (df[w] + .5))
                   for w in tok(q) if w in tf)
    gt = next(t for i, t in ts if i == g)
    nt = next(t for i, t in ts if i == ng)
    print(cid, 'gold', round(sc(gt), 2), 'neg', round(sc(nt), 2), '->', 'BM25FAILS' if sc(nt) > sc(gt) else 'bm25ok')

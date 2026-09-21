"""Persist E-fidelity diagnostic: for the 17 PURE-miss anchors, where each arm ranks them."""
import json, sys
from pathlib import Path
ROOT = Path('C:/Users/muzaf/PycharmProjects/ContextDecayWindow')
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments/probes/bert_anchor'))
import arms

E = ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs'
curves = [r for r in json.load(open(ROOT / 'experiments/probes/retrieval_score_curves/artifacts/curves.json', encoding='utf-8'))
          if r['study'] == 'E' and r['type'] in ('straight', 'irrelevant', 'future', 'proposal')]
blind = {r['id']: r for r in json.load(open(ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json', encoding='utf-8'))}
sources = {h['id']: h for h in json.load(open(E / 'sources.json', encoding='utf-8'))}
gaps = [c for c in curves if blind[c['id']]['arms']['PURE']['anchor_exceptions']]
rows = []
for c in gaps:
    eps = sources[c['history']]['episodes']
    anchor = blind[c['id']]['arms']['ANCHORED']['anchor_exceptions'][0]
    texts = [e['user_message'] + '\n' + e['assistant_message'] for e in eps]
    ids = [e['id'] for e in eps]
    bm = arms.BM25(texts).score(c['query'])
    order = sorted(range(len(texts)), key=lambda i: -bm[i])
    ai = ids.index(anchor)
    rows.append(dict(id=c['id'], type=c['type'], n=len(texts),
                     bm25_anchor_rank=order.index(ai) + 1,
                     bm25_top1=texts[order[0]][:120],
                     anchor_text=texts[ai][:120]))
out = dict(interpretation='BM25 top-1 lands on record lines containing query tokens; the meeting-event anchor contains no answer tokens, so exact-top-1 recovery is 0/17 for every arm. Authoring error in Amendment 001 expectation (inclusion vs top-1), not a scoring bug.', rows=rows)
(ROOT / 'experiments/probes/bert_anchor/part1_artifacts/e_fidelity_note.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print('bm25 anchor ranks:', sorted(r['bm25_anchor_rank'] for r in rows))

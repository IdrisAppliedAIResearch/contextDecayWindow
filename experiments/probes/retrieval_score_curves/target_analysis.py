"""Retrospective state-setting carrier positions; no cutoff fitting."""
import json
from pathlib import Path

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
E=ROOT/'experiments/study_E/artifacts/confirmation/development_inputs'
curves=json.loads((P/'artifacts/curves.json').read_text())
labels=json.loads((E/'labels.json').read_text())
traces={r['history']:r for r in json.loads((E/'traces_sealed.json').read_text())}
rows=[]
for c in curves:
    if c['study']!='E' or c['type'] not in ['straight','irrelevant','future','proposal']:continue
    rationale=labels[c['id']]['rationale']
    i=c['turns'].index(rationale['target']); rank=c['order'].index(i)+1
    scores=[c['cc80'][j] for j in c['order']]
    anchor=c['turns'].index(rationale['anchor'])
    rows.append(dict(id=c['id'],history=c['history'],miss=not traces[c['history']]['evidence']['C1'],
        target_rank=rank,target_ratio=scores[rank-1]/scores[0],target_score=scores[rank-1],
        gap_after=scores[rank-1]-scores[rank] if rank<len(scores) else None,
        anchor_rank=c['order'].index(anchor)+1))
path=P/'artifacts/target_diagnostic.json'
if path.exists():
    assert json.loads(path.read_text())==rows
    print('Exact target-diagnostic replay PASS')
else:
    path.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')

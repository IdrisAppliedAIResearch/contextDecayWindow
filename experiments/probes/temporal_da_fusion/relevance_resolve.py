"""Preserve mechanical scores; resolve authorized prose exceptions before aggregates."""
import sys
import json
from preflight import P,read,save,committed,sha

OUT=P/'relevance_artifacts/reader'


def resolve():
    for n in ['scores.json','agent_judgments.json']:committed(OUT/n)
    scores=read(OUT/'scores.json');judgments={r['blind_id']:r for r in read(OUT/'agent_judgments.json')}
    assert {r['blind_id'] for r in scores if r['score'] is None}==set(judgments) and len(judgments)==3
    for r in scores:
        if r['score'] is None:r.update(judgments[r['blind_id']]);r['method']='authorized single-agent prose adjudication'
        else:r['method']='canonical mechanical'
    assert len(scores)==32 and all(r['score'] in [0,1] for r in scores)
    save(OUT/'scores_resolved.json',scores);save(OUT/'scoring_gate_resolved.json',dict(status='PASS',pending=0,canonical=29,agent=3,scores_sha256=sha(OUT/'scores_resolved.json')))


def aggregate():
    committed(OUT/'scores_resolved.json');committed(OUT/'scoring_gate_resolved.json')
    assert sha(OUT/'scores_resolved.json')==read(OUT/'scoring_gate_resolved.json')['scores_sha256']
    scores={r['blind_id']:r for r in read(OUT/'scores_resolved.json')};mapping=read(OUT/'mapping.json');rows=[];arms=['BASELINE','RELEVANCE']
    for qid in dict.fromkeys(r['id'] for r in mapping):
        rs=[r for r in mapping if r['id']==qid];f=scores[rs[0]['blind_id']]
        rows.append(dict(id=qid,type=rs[0]['type'],query=f['query'],reference=f['reference'],arms={r['arm']:dict(answer=scores[r['blind_id']]['answer'],score=scores[r['blind_id']]['score']) for r in rs}))
    totals={}
    for group in ['primary','latest','absent']:
        rs=[r for r in rows if (r['type'] not in ['latest','absent'] if group=='primary' else r['type']==group)]
        totals[group]=dict(n=len(rs),scores={a:sum(r['arms'][a]['score'] for r in rs) for a in arms},pairs={'BASELINE→RELEVANCE':dict(gains=sum(r['arms']['RELEVANCE']['score']>r['arms']['BASELINE']['score'] for r in rs),losses=sum(r['arms']['RELEVANCE']['score']<r['arms']['BASELINE']['score'] for r in rs))})
    save(OUT/'result.json',dict(scope='EXPLORATORY native-off reader;29 canonical,3 single-agent scores',totals=totals,rows=rows));print(json.dumps(totals,indent=2))


if __name__=='__main__':{'resolve':resolve,'aggregate':aggregate}[sys.argv[1]]()

"""Existing-run score curves: label-free replay first, descriptive annotation later."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
import concurrent.futures as cf
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
P=Path(__file__).resolve().parent
O=P/'artifacts'
E=ROOT/'experiments/study_E/artifacts/confirmation/development_inputs'
D=ROOT/'experiments/study_D/artifacts/confirmation'
CONTROL=ROOT.parent/'contextDecayWindow-study-D-control'
sys.path.insert(0,str(CONTROL/'episodic/src'))
from episodic._ranking import rank_cc80


def read(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def save(name,obj):
    O.mkdir(exist_ok=True)
    with (O/name).open('x',encoding='utf-8') as f: json.dump(obj,f,indent=2);f.write('\n')
def committed(path):
    raw=subprocess.check_output(['git','show','HEAD:'+path.relative_to(ROOT).as_posix()],cwd=ROOT)
    assert raw.replace(b'\r\n',b'\n')==path.read_bytes().replace(b'\r\n',b'\n')
def gap(values):
    a=np.asarray(values);delta=a[:-1]-a[1:]
    if not len(delta) or float(delta.max())<=0: return None
    return int(np.argmax(delta))+1
def dist(values):
    if not values: return {'n':0}
    return dict(n=len(values),min=float(min(values)),median=float(np.median(values)),
        p95=float(np.quantile(values,.95)),max=float(max(values)))


def extract():
    committed(P/'PLAN.md');committed(Path(__file__).resolve())
    assert not O.exists()
    assert subprocess.check_output(['git','-C',str(CONTROL),'rev-parse','HEAD'],text=True).strip()=='5ebda1ef4510c1806709039aeb66e6d79cedbbd8'
    assert not subprocess.check_output(['git','-C',str(CONTROL),'status','--porcelain'],text=True).strip()
    assert gap([1,.99,.2,.19])==2 and gap([1,1,1]) is None and gap([1]) is None
    assert np.all(np.diff([1,.5,.1])<=0) and not np.all(np.diff([1,.1,.5])<=0)
    start=time.monotonic()
    manifest=read(E/'vector_manifest.json');assert sha(E/'vectors.npz')==manifest['file_sha256']
    vectors=np.load(E/'vectors.npz')['vectors'];bytext=dict(zip(manifest['texts'],vectors))
    histories=read(E/'sources.json');traces={r['history']:r['trace'] for r in read(E/'traces_sealed.json')}
    def one(h):
        q=h['probes'][0];es=[dict(e,embedding=bytext[e['user_message']+'\n'+e['assistant_message']]) for e in h['episodes']]
        r=rank_cc80(es,q['query'],bytext[q['query']],dense_weight=.8,bm25_k1=1.2,bm25_b=.75)
        t=traces[h['id']];assert list(r.order)==t['prior']['ranking']
        eligible=t.get('eligible_after',t['prior']['route'].get('eligible',[]))
        return dict(study='E',id=q['id'],history=h['id'],type=q['type'],query=q['query'],
            ids=[e['id'] for e in es],turns=[e['turn_number'] for e in es],
            order=list(r.order),cc80=list(r.scores),cosine=list(r.dense_scores),bm25=list(r.bm25_scores),
            eligible=eligible,temporal_order=t.get('eligible_after',[]))
    with cf.ThreadPoolExecutor(max_workers=4) as pool: curves=list(pool.map(one,histories))
    assert len(curves)==192
    dh=read(D/'sources.json');dq={q['id']:(h,q) for h in dh for q in h['probes']}
    for r in read(D/'rank_scores.json'):
        h,q=dq[r['item']];es=h['episodes'];ids=[e['id'] for e in es];byid={x:i for i,x in enumerate(ids)}
        expected=sorted(range(len(es)),key=lambda i:(-r['cc80_scores'][i],es[i]['turn_number'],ids[i]))
        assert [ids[i] for i in expected]==r['order_ids']
        assert len(r['cc80_scores'])==len(r['dense_scores'])==len(r['bm25_scores'])==len(es)
        curves.append(dict(study='D',id=q['id'],history=h['id'],type=q['type'],query=q['query'],ids=ids,
            turns=[e['turn_number'] for e in es],order=expected,cc80=r['cc80_scores'],cosine=r['dense_scores'],
            bm25=r['bm25_scores'],eligible=[],temporal_order=[]))
    paths=[E/'sources.json',E/'vector_manifest.json',E/'vectors.npz',E/'traces_sealed.json',D/'sources.json',D/'rank_scores.json',CONTROL/'episodic/src/episodic/_ranking.py']
    save('curves.json',curves)
    save('replay_gate.json',dict(status='PASS',E_rank_orders_exact=192,D_rank_orders_exact=len(curves)-192,
        workers=4,numeric_threads=1,elapsed_seconds=time.monotonic()-start,model_calls=0,embedding_calls=0,
        label_free_extraction=True,fixtures='Separated,flat,singleton,monotone,nonmonotone passed',
        curves_sha256=sha(O/'curves.json'),inputs={str(p):sha(p) for p in paths},runner_sha256=sha(Path(__file__))))
    print(json.dumps(read(O/'replay_gate.json')))


def annotate():
    committed(O/'curves.json');committed(O/'replay_gate.json')
    assert sha(O/'curves.json')==read(O/'replay_gate.json')['curves_sha256']
    labels={'E':read(E/'labels.json'),'D':read(D/'labels.json')}
    traces={r['history']:r for r in read(E/'traces_sealed.json')}
    rows=[]
    for c in read(O/'curves.json'):
        label=labels[c['study']][c['id']];gold=set(label['gold_ids'])
        pools={'full':list(range(len(c['ids']))),'nonrecent':[i for i,t in enumerate(c['turns']) if t<=108]}
        if c['study']=='E' and c['type'] in ['straight','irrelevant','future','proposal']:pools['eligible']=c['eligible']
        for pool,indices in pools.items():
            for metric in ['cc80','cosine','bm25']:
                order=sorted(indices,key=lambda i:(-c[metric][i],c['turns'][i],c['ids'][i]))
                values=[c[metric][i] for i in order];boundary=gap(values)
                chosen=order[:boundary] if boundary else []
                ranks={c['ids'][i]:j+1 for j,i in enumerate(order)}
                target_turn=label.get('rationale',{}).get('target')
                target_id=next((c['ids'][i] for i,t in enumerate(c['turns']) if t==target_turn),None)
                carriers=[dict(id=k,rank=ranks.get(k),relative_rank=ranks[k]/len(order) if k in ranks else None,
                    score=c[metric][c['ids'].index(k)],score_to_top=c[metric][c['ids'].index(k)]/values[0] if values and values[0]!=0 else None) for k in sorted(gold)]
                rows.append(dict(study=c['study'],id=c['id'],type=c['type'],pool=pool,metric=metric,n=len(order),
                    boundary=boundary,gap=(values[boundary-1]-values[boundary]) if boundary else None,
                    fraction=boundary/len(order) if boundary else None,required_n=len(gold),
                    complete_at_gap=gold.issubset({c['ids'][i] for i in chosen}) if gold and boundary else None,
                    target_at_gap=target_id in {c['ids'][i] for i in chosen} if target_id and boundary else None,
                    last_required_rank=max((ranks[k] for k in gold),default=None) if gold.issubset(ranks) else None,
                    C1_complete=traces[c['history']]['evidence']['C1'] if c['study']=='E' else None,carriers=carriers))
    summary={}
    for study in ['E','D']:
        kinds=['all']+sorted({r['type'] for r in rows if r['study']==study})
        if study=='E':kinds.append('primary')
        for kind in kinds:
            for pool in ['full','nonrecent','eligible']:
                for metric in ['cc80','cosine','bm25']:
                    subset=[r for r in rows if r['study']==study and r['pool']==pool and r['metric']==metric and
                        (kind=='all' or r['type']==kind or kind=='primary' and r['type'] in ['straight','irrelevant','future','proposal'])]
                    if not subset:continue
                    summary[f'{study}/{kind}/{pool}/{metric}']=dict(n=len(subset),defined=sum(r['boundary'] is not None for r in subset),
                        prefix_size=dist([r['boundary'] for r in subset if r['boundary'] is not None]),
                        gap_size=dist([r['gap'] for r in subset if r['gap'] is not None]),
                        complete=sum(r['complete_at_gap'] is True for r in subset),answerable=sum(r['required_n']>0 for r in subset),
                        target_survives=sum(r['target_at_gap'] is True for r in subset),
                        carriers_score_to_top=dist([c['score_to_top'] for r in subset for c in r['carriers'] if c['score_to_top'] is not None]),
                        existing_misses=sum(r['C1_complete'] is False for r in subset if r['required_n']),
                        existing_misses_complete_at_gap=sum(r['C1_complete'] is False and r['complete_at_gap'] is True for r in subset),
                        existing_complete_lost=sum(r['C1_complete'] is True and r['complete_at_gap'] is False for r in subset))
    temporal=[c for c in read(O/'curves.json') if c['study']=='E' and c['temporal_order']]
    summary['temporal_order_diagnostic']=dict(n=len(temporal),nonmonotone_cc80=sum(not np.all(np.diff([c['cc80'][i] for i in c['temporal_order']])<=0) for c in temporal))
    save('diagnostic_rows.json',rows);save('summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k.startswith('E/primary') and k.endswith('/cc80') or k=='temporal_order_diagnostic'}))


if __name__=='__main__':{'extract':extract,'annotate':annotate}[sys.argv[1]]()

"""Frozen replay and local missing-carrier path diagnosis; no model calls."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
from concurrent.futures import ProcessPoolExecutor
import json
import numpy as np
from characterize import P,Unit,Reference,Policy,retrieve,cosine_matrix,read_rows,write_rows,write_json,sha

def worker(c):
    units=[Unit(**x) for x in read_rows(P/'prepared/sources.jsonl.gz') if x['conversation']==c]
    ids=[u.id for u in units]; index={k:i for i,k in enumerate(ids)}
    refs=[Reference(**x) for x in read_rows(P/'references/references.jsonl.gz') if x['unit_id'] in index]
    v=np.load(P/'prepared/vectors.npz'); rv=np.load(P/'references/vectors.npz')
    direct={k:v['d_'+k] for k in ids}; contextual={k:v['c_'+k] for k in ids}; cues={r.id:rv[r.id] for r in refs}
    contexts=json.loads((P/'prepared/contexts.json').read_text(encoding='utf-8'))
    policy=Policy(**json.loads((P/'calibration/policy.json').read_text(encoding='utf-8'))['thresholds'])
    dm=cosine_matrix([direct[k] for k in ids]); cm=cosine_matrix([contextual[k] for k in ids])
    cache=dict(ids=ids,references={r.id:dm@(cues[r.id].astype(np.float64)/np.linalg.norm(cues[r.id].astype(np.float64))) for r in refs},support=[dm@row for row in dm])
    selected={r['key']:r for r in read_rows(P/'characterization_v2/selections.jsonl.gz') if r['conversation']==c}
    diag=[r for r in read_rows(P/'subset/diagnostics.jsonl.gz') if r['conversation']==c and r['arm']=='C1']
    out=[]; carriers=[]
    for d in diag:
        k=d['key']; q=v['q_'+k].astype(np.float64); q/=np.linalg.norm(q)
        result=retrieve(units,direct,contextual,contexts,refs,cues,q,policy,static_scores=cache)
        assert result['selected']==selected[k]['selected_ids']
        assert result['operations']<=result['operation_bound']
        ds=dm@q; cs=cm@q
        out.append(dict(key=k,contextual=len(result['contextual']),selected=len(result['selected']),
                   only_traversal=sum('direct' not in reasons and 'contextual' not in reasons for reasons in result['admissions'].values()),
                   unresolved_support=len(result['unresolved_support']),weak_paths_suppressed=result['weak_paths_suppressed']))
        missing=set(d['missing_annotation_ids'])
        for i,u in enumerate(units):
            if not missing.intersection(u.member_ids): continue
            best=None
            for ref in refs:
                if ref.unit_id not in result['activation'] or ref.unit_id==u.id: continue
                score=float(cache['references'][ref.id][i])
                if score<policy.reference: continue
                strength=result['activation'][ref.unit_id]*max(0,min(1,score))
                if best is None or strength>best['product']:
                    best=dict(route='reference',parent=ref.unit_id,cue=ref.text,edge=score,parent_activation=result['activation'][ref.unit_id],product=strength)
            for seed in result['contextual']:
                if u.id==seed or u.id not in contexts[seed]: continue
                score=float(cache['support'][index[seed]][i])
                if score<policy.support: continue
                strength=result['activation'][seed]*max(0,min(1,score))
                if best is None or strength>best['product']:
                    best=dict(route='support',parent=seed,edge=score,parent_activation=result['activation'][seed],product=strength)
            assert ds[i]<.48 and cs[i]<policy.contextual
            assert best is None or best['product']<.48
            carriers.append(dict(key=k,question=d['question'],gold=d['gold'],answer=d['answer'],unit=u.id,
                        missing_ids=sorted(missing.intersection(u.member_ids)),source=u.text,date=u.date,
                        direct=float(ds[i]),contextual=float(cs[i]),best_eligible_link=best))
    return out,carriers

def main():
    out=P/'probe001'; out.mkdir(exist_ok=False)
    diag=read_rows(P/'subset/diagnostics.jsonl.gz')
    with ProcessPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(worker,sorted({r['conversation'] for r in diag})))
    queries=[x for a,b in results for x in a]; carriers=[x for a,b in results for x in b]
    assert len(queries)==566
    write_rows(out/'queries.jsonl.gz',queries); write_rows(out/'missing_carriers.jsonl.gz',carriers)
    pair={}
    for d in diag: pair.setdefault(d['key'],{})[d['arm']]=d
    changes=[dict(key=k,C0=p['C0'],C1=p['C1']) for k,p in pair.items() if p['C0']['score']!=p['C1']['score']]
    write_rows(out/'answer_changes.jsonl.gz',changes)
    summary=dict(replayed=566,exact_ids=True,model_calls=0,missing_questions=len({r['key'] for r in carriers}),
                 missing_carriers=len(carriers),eligible_edge_but_product_below_floor=sum(r['best_eligible_link'] is not None for r in carriers),
                 no_eligible_edge_from_final_frontier=sum(r['best_eligible_link'] is None for r in carriers),
                 queries_with_traversal=sum(r['only_traversal']>0 for r in queries),
                 median_traversal_only=float(np.median([r['only_traversal'] for r in queries])),
                 median_contextual_seeds=float(np.median([r['contextual'] for r in queries])),
                 median_selected=float(np.median([r['selected'] for r in queries])),
                 hashes={str(p):sha(p) for p in [P/'subset/diagnostics.jsonl.gz',P/'prepared/vectors.npz',P/'references/vectors.npz']})
    write_json(out/'summary.json',summary); print(json.dumps(summary))
if __name__=='__main__': main()

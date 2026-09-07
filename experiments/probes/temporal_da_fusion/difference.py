"""Frozen structural link ablations and separate exposed-data measurement."""
import concurrent.futures
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from preflight import P, I, O, ROOT, read, sha, save, digest, committed, require_gate
from mechanism import E, fuse, linked_order
from analyze import dist, compare

D = P/'difference_artifacts'
MODES = ('forward','backward','before_anchor')


def order_links(nodes, ranking, mode, anchor):
    groups = {}
    for i,n in enumerate(nodes): groups.setdefault(n.session_identity,[]).append(i)
    for group in groups.values(): group.sort(key=lambda i:nodes[i].pair_order)
    seen,out,edges = set(),[],[]
    def emit(i):
        if i not in seen: seen.add(i);out.append(i);return True
        return False
    for seed in ranking:
        emit(seed)
        group=groups[nodes[seed].session_identity];p=group.index(seed)
        for j in [p-1,p+1]:
            if not 0<=j<len(group):continue
            child=group[j]
            if mode=='forward' and j<p:continue
            if mode=='backward' and j>p:continue
            if mode=='before_anchor' and nodes[child].pair_order>=anchor:continue
            if emit(child):edges.append((seed,child))
    assert len(out)==len(nodes)==len(set(out))
    return out,edges


def extract():
    assert not D.exists()
    for p in [P/'DIFFERENCE_PLAN.md',P/'difference.py',O/'preflight.json',O/'blind_outputs.json']:committed(p)
    g=read(O/'preflight.json');require_gate(g);assert sha(O/'blind_outputs.json')==g['outputs_sha256']
    n=[SimpleNamespace(session_identity=s,pair_order=i) for s,i in [('a',1),('a',2),('a',3),('b',1),('b',2)]]
    rank=[1,4,0,2,3]
    assert order_links(n,rank,'forward',3)[0]==[1,2,4,0,3]
    assert order_links(n,rank,'backward',3)[0]==[1,0,4,3,2]
    assert all(n[c].pair_order<2 for _,c in order_links(n,rank,'before_anchor',2)[1])
    assert all(n[s].session_identity==n[c].session_identity for m in MODES for s,c in order_links(n,rank,m,3)[1])
    try:require_gate({'status':'FAIL'})
    except ValueError:pass
    else:raise AssertionError('Failed gate entered')
    histories={h['id']:h for h in read(I/'sources.json')}
    traces={r['history']:r['trace'] for r in read(I/'traces_sealed.json')}
    curves={r['history']:r for r in read(ROOT/'experiments/probes/retrieval_score_curves/artifacts/curves.json') if r['study']=='E'}
    start=time.monotonic()
    def one(old):
        h=histories[old['history']];es=h['episodes'];q=h['probes'][0]['query'];t=traces[h['id']]
        by={e['id']:e for e in es};recent=list(E._recency_window(es,32));recent_ids={e['id'] for e in recent}
        baseline=E.render_stm_payload(recent,[by[k] for k in old['baseline']['selected_ids']])
        assert digest(baseline)==old['baseline']['context_sha256']
        block,replayed=fuse(es,q,t,baseline)
        assert block==old['context'] and replayed['selected_ids']==old['fusion']['selected_ids']
        rank=list(t['prior']['ranking']);nodes=[SimpleNamespace(session_identity=h['id'],pair_order=e['turn_number']) for e in es]
        unrestricted,edges=order_links(nodes,rank,'all',0)
        assert tuple(unrestricted)==linked_order(nodes,rank,'TEMPORAL',len(rank))[0]
        anchor=min((es[i]['turn_number'] for i in t.get('route',{}).get('anchors',[])),default=None)
        arms={}
        for mode in MODES:
            if not old['fusion']['active']:
                arms[mode]=dict(selected_ids=old['baseline']['selected_ids'],context_sha256=digest(baseline),links=[])
                continue
            order,links=order_links(nodes,rank,mode,anchor)
            protected=t['temporal_ids'];ids=list(dict.fromkeys(protected+[es[i]['id'] for i in order if es[i]['id'] not in recent_ids]))
            packed=E.pack_stm_payload([],[by[k] for k in ids],32000)
            selected=list(packed.selected_ids);assert selected[:len(protected)]==protected
            block=E.render_stm_payload(recent,[by[k] for k in selected])
            assert len(E.render_stm_payload([],[by[k] for k in selected]))<=32000
            arms[mode]=dict(selected_ids=selected,context_sha256=digest(block),links=[[es[s]['id'],es[c]['id']] for s,c in links],chars=packed.serialized_chars)
        features=[];c=curves[h['id']];ranks={i:p+1 for p,i in enumerate(rank)};idx={e['id']:i for i,e in enumerate(es)}
        left=set(old['baseline']['selected_ids']);right=set(old['fusion']['selected_ids'])
        order=old['fusion'].get('order_ids',[])
        for k in sorted(left^right):
            i=idx[k];parents=[x['seed'] for x in old['fusion']['links'] if x['child']==k]
            features.append(dict(id=k,change='added' if k in right else 'removed',turn=es[i]['turn_number'],
                direct_rank=ranks[i],cc80=c['cc80'][i],cosine=c['cosine'][i],
                anchor=anchor,distance_to_anchor=es[i]['turn_number']-anchor if anchor is not None else None,
                before_anchor=es[i]['turn_number']<anchor if anchor is not None else None,
                fusion_order_position=order.index(k)+1 if k in order else None,
                parents=[dict(id=p,turn=by[p]['turn_number'],direct_rank=ranks[idx[p]],selected=p in right,
                    direction='forward' if by[p]['turn_number']<es[i]['turn_number'] else 'backward',
                    first_sentence=by[p]['user_message'].split('\n')[0]) for p in parents],
                first_sentence=es[i]['user_message'].split('\n')[0]))
        return dict(history=h['id'],id=old['id'],type=old['type'],arms=arms,features=features)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(one,read(O/'blind_outputs.json')))
    assert len(rows)==192
    D.mkdir();save(D/'blind.json',rows)
    save(D/'gate.json',dict(status='PASS',original_contexts_exact=192,unrestricted_orders_exact=192,
        structural_fixtures=True,failed_gate_rejected=True,outputs_sha256=sha(D/'blind.json'),
        inputs={str(p):sha(p) for p in [P/'DIFFERENCE_PLAN.md',P/'difference.py',I/'sources.json',I/'traces_sealed.json',O/'blind_outputs.json',ROOT/'experiments/probes/retrieval_score_curves/artifacts/curves.json']},
        workers=4,elapsed_seconds=time.monotonic()-start,model_calls=0,embedding_calls=0))
    print('PASS: 192 exact baseline/fusion contexts; 192 unrestricted DA orders; three structural ablations')


def measure():
    for p in [D/'blind.json',D/'gate.json']:committed(p)
    gate=read(D/'gate.json');require_gate(gate);assert sha(D/'blind.json')==gate['outputs_sha256']
    assert compare({'x'},set(),{'x'})['gain'] and compare({'x'},{'x'},set())['loss']
    assert not compare(set(),set(),set())['gain']
    labels=read(I/'labels.json');original={r['id']:r for r in read(O/'diagnostic_rows.json')}
    frozen={r['id']:r for r in read(O/'blind_outputs.json')}
    feature_rows=[];outcomes=[]
    for r in read(D/'blind.json'):
        old=original[r['id']];required=set(labels[r['id']]['gold_ids']);left=set(frozen[r['id']]['baseline']['selected_ids'])
        for f in r['features']:
            feature_rows.append(dict(**f,history=r['history'],type=r['type'],required=f['id'] in required,original_gain=old['gain'],original_loss=old['loss']))
        for mode,a in r['arms'].items():
            right=set(a['selected_ids'])
            outcomes.append(dict(id=r['id'],type=r['type'],mode=mode,**compare(required,left,right),
                original_gain=old['gain'],original_loss=old['loss'],n=len(right),
                context_changed=a['context_sha256']!=frozen[r['id']]['baseline']['context_sha256']))
    primary=lambda r:r['type'] in ['straight','irrelevant','future','proposal']
    summary={}
    for mode in MODES:
        summary[mode]={}
        for group in ['primary','original_discordances','remainder','latest','absent']:
            rs=[r for r in outcomes if r['mode']==mode and (primary(r) if group=='primary' else primary(r) and (r['original_gain'] or r['original_loss']) if group=='original_discordances' else primary(r) and not(r['original_gain'] or r['original_loss']) if group=='remainder' else r['type']==group)]
            summary[mode][group]=dict(n=len(rs),**{k:sum(r[k] for r in rs) for k in ['baseline_complete','fusion_complete','gain','loss','context_changed']},
                original_rescues_retained=sum(r['original_gain'] and r['fusion_complete'] for r in rs),original_losses_repaired=sum(r['original_loss'] and r['fusion_complete'] for r in rs))
    features={}
    for change in ['added','removed']:
        for required in [True,False]:
            rs=[r for r in feature_rows if primary(r) and r['change']==change and r['required']==required]
            features[f'{change}/required={required}']=dict(n=len(rs),before_anchor=sum(r['before_anchor'] for r in rs),
                **{k:dist([r[k] for r in rs]) for k in ['direct_rank','cc80','cosine','distance_to_anchor','fusion_order_position']},
                forward=sum(any(p['direction']=='forward' for p in r['parents']) for r in rs),backward=sum(any(p['direction']=='backward' for p in r['parents']) for r in rs))
    save(D/'features_labeled.json',feature_rows);save(D/'outcomes.json',outcomes)
    save(D/'result.json',dict(scope='EXPLORATORY; exposed remainder, no reader score',ablations=summary,features=features,labels_sha256=sha(I/'labels.json')))
    print(json.dumps(dict(ablations=summary,features=features),indent=2))


if __name__=='__main__':{'extract':extract,'measure':measure}[sys.argv[1]]()

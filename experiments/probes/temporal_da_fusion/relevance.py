"""Uncapped raw-cosine filtering; separate label annotation."""
import json
from pathlib import Path
import sys
from preflight import P,I,ROOT,read,sha,save,committed,digest,E
from analyze import dist

OUT=P/'relevance_artifacts'
CURVES=ROOT/'experiments/probes/retrieval_score_curves/artifacts/curves.json'
THRESHOLD=.48


def select(ids,turns,scores,anchors=()):
    assert len(ids)==len(turns)==len(scores)==len(set(ids))
    chosen={k for k,s in zip(ids,scores) if s>=THRESHOLD}|set(anchors)
    assert chosen.issubset(ids)
    return [ids[i] for i in sorted(range(len(ids)),key=lambda i:(turns[i],ids[i])) if ids[i] in chosen]


def extract():
    for path in [P/'RELEVANCE_PLAN.md',P/'relevance.py',CURVES]:committed(path)
    assert not OUT.exists()
    assert select(['c','a','b'],[3,1,2],[.479,.48,.481])==['a','b']
    assert select(['c','a','b'],[3,1,2],[.479,.48,.481],['c'])==['a','b','c']
    assert select(['x'],[1],[0])==[] and select(['x'],[1],[1])==['x']
    assert len(select([str(i) for i in range(200) ],list(range(200)),[1]*200))==200
    gate=read(CURVES.parent/'replay_gate.json');assert gate['status']=='PASS' and gate['curves_sha256']==sha(CURVES)
    traces={r['history']:r['trace'] for r in read(I/'traces_sealed.json')}
    histories={'E':{h['id']:h for h in read(I/'sources.json')},'D':{h['id']:h for h in read(ROOT/'experiments/study_D/artifacts/confirmation/sources.json')}}
    chrono={r['history']:r for r in read(P/'chronology_artifacts/contexts.json')};rows=[]
    for c in read(CURVES):
        h=histories[c['study']][c['history']];es=h['episodes'];ids=[e['id'] for e in es];turns=[e['turn_number'] for e in es]
        assert ids==c['ids'] and turns==c['turns'];by={e['id']:e for e in es}
        anchors=[];baseline=None
        if c['study']=='E':
            t=traces[h['id']];assert t['prior']['ranking']==c['order']
            route=t.get('route',t['prior']['route']);anchors=[es[i]['id'] for i in route.get('anchors',[])]
            old=chrono[h['id']];baseline=sorted(old['selected_ids'],key=lambda k:(by[k]['turn_number'],k))
            assert E.render_stm_payload([],[by[k] for k in baseline])==old['contexts']['CHRONO_NO_RECENT']
        pure=select(ids,turns,c['cosine']);protected=select(ids,turns,c['cosine'],anchors)
        arms={}
        for arm,chosen in [('PURE',pure),('ANCHORED',protected)] if c['study']=='E' else [('PURE',pure)]:
            block=E.render_stm_payload([],[by[k] for k in chosen]);assert block.count('<episode turn=')==len(chosen)
            chosen_set=set(chosen);kept=[s for k,s in zip(ids,c['cosine']) if k in chosen_set];rejected=[s for k,s in zip(ids,c['cosine']) if k not in chosen_set]
            arms[arm]=dict(ids=chosen,context=block,context_sha256=digest(block),chars=len(block),
                continuity_admitted=sum(k in chosen_set for k in ids[-32:]),
                min_admitted=min(kept) if kept else None,max_rejected=max(rejected) if rejected else None,
                anchor_exceptions=[k for k in anchors if k not in pure])
        rows.append(dict(study=c['study'],id=c['id'],history=c['history'],type=c['type'],query=c['query'],
            baseline_ids=baseline,anchors=anchors,arms=arms))
    assert len(rows)==416 and sum(r['study']=='E' for r in rows)==192
    OUT.mkdir();save(OUT/'blind.json',rows)
    save(OUT/'gate.json',dict(status='PASS',threshold=THRESHOLD,score='raw cosine',E_baselines_exact=192,D_score_arrays_verified=224,
        boundary_empty_full_anchor_fixtures=True,no_selection_count_or_char_cap=True,outputs_sha256=sha(OUT/'blind.json'),
        inputs={str(p):sha(p) for p in [CURVES,CURVES.parent/'replay_gate.json',I/'sources.json',I/'traces_sealed.json',P/'chronology_artifacts/contexts.json',P/'RELEVANCE_PLAN.md',P/'relevance.py']},model_calls=0,embedding_calls=0))
    print('Uncapped construction PASS: 192 E,224 D; frozen chronological baseline exact')


def annotate():
    for p in [OUT/'blind.json',OUT/'gate.json']:committed(p)
    gate=read(OUT/'gate.json');assert gate['status']=='PASS' and sha(OUT/'blind.json')==gate['outputs_sha256']
    labels={'E':read(I/'labels.json'),'D':read(ROOT/'experiments/study_D/artifacts/confirmation/labels.json')}
    rows=[]
    for r in read(OUT/'blind.json'):
        required=set(labels[r['study']][r['id']]['gold_ids'])
        for arm,a in r['arms'].items():
            chosen=set(a['ids']);base=set(r['baseline_ids'] or [])
            rows.append(dict(study=r['study'],id=r['id'],type=r['type'],arm=arm,answerable=bool(required),
                complete=bool(required) and required.issubset(chosen),baseline_complete=bool(required) and required.issubset(base),
                added_required=sorted((chosen-base)&required),missing_required=sorted(required-chosen),
                n=len(chosen),chars=a['chars'],continuity=a['continuity_admitted'],anchor_exceptions=len(a['anchor_exceptions'])))
    summary={}
    for study in ['E','D']:
        for kind in ['all','before']+sorted({r['type'] for r in rows if r['study']==study}):
            for arm in ['PURE','ANCHORED'] if study=='E' else ['PURE']:
                rs=[r for r in rows if r['study']==study and r['arm']==arm and (kind=='all' or r['type']==kind or kind=='before' and r['type'] in (['straight','irrelevant','future','proposal'] if study=='E' else ['T1']))]
                summary[f'{study}/{kind}/{arm}']=dict(n=len(rs),answerable=sum(r['answerable'] for r in rs),complete=sum(r['complete'] for r in rs),
                    baseline_complete=sum(r['baseline_complete'] for r in rs) if study=='E' else None,
                    gains=sum(r['complete'] and not r['baseline_complete'] for r in rs) if study=='E' else None,
                    losses=sum(r['baseline_complete'] and not r['complete'] for r in rs) if study=='E' else None,
                    records=dist([r['n'] for r in rs]),chars=dist([r['chars'] for r in rs]),continuity=dist([r['continuity'] for r in rs]),anchor_exceptions=sum(r['anchor_exceptions'] for r in rs))
    save(OUT/'diagnostic_rows.json',rows);save(OUT/'summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if '/before/' in k or k.startswith('E/latest') or k.startswith('E/absent')},indent=2))


if __name__=='__main__':{'extract':extract,'annotate':annotate}[sys.argv[1]]()

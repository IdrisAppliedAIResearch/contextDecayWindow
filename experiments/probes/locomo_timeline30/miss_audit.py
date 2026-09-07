"""Offline exact replay then annotated source-carrier diagnosis."""
import json
import numpy as np
import probe as q
p=q.p;r=q.r;OUT=q.OUT
def main():
    p.committed(__file__);p.committed(q.P/'MISS_AUDIT_PLAN.md')
    result=p.read(OUT/'corrected_results.json');schedule=p.read(OUT/'schedule.json')
    selections={x['key']:x for x in r.rows('selections.jsonl.gz')}
    adapters={x['id']:x for x in r.rows('adapter.jsonl.gz')}
    cases=p.prior.load_blind_cases()
    p.prior.DEV_CACHE=p.ROOT/p.prior.DEV_CACHE.relative_to(p.CONTROL)
    p.prior.HOLDOUT_CACHE=p.ROOT/p.prior.HOLDOUT_CACHE.relative_to(p.CONTROL)
    vectors,cache=p.prior.load_full_vectors(cases)
    cases={c.sample_id:c for c in cases};maxdiff=0
    for row in schedule:
        case=cases[row['conversation']];saved=selections[row['key']]
        matrix=np.asarray([vectors[x.text] for x in case.pairs],dtype=np.float64)
        matrix/=np.linalg.norm(matrix,axis=1,keepdims=True)
        v=np.asarray(vectors[row['question']],dtype=np.float64);scores=matrix@(v/np.linalg.norm(v))
        maxdiff=max(maxdiff,float(np.max(np.abs(scores-np.asarray(saved['scores'])))))
        assert np.allclose(scores,saved['scores'],atol=1e-12,rtol=0)
        assert [x.identity for x in case.pairs]==saved['ids']
        chosen=[x.identity for x,s in zip(case.pairs,scores) if s>=.48]
        assert chosen==saved['selected'] and saved['route']['reason']=='unsupported' and saved['cutoff'] is None
        block='\n'.join(adapters[k]['element'] for k in chosen)
        assert p.render_reader_prompt(row['question'],block)==row['text'] and p.digest(block)==saved['block_sha256']
    source={x['sample_id']:x for x in p.read(p.prior.DATASET_PATH)}
    rows=[]
    for row in result['rows']:
        if row['group']!='broad20' or row['evidence']=='complete':continue
        saved=selections[row['key']];case=cases[row['conversation']];scores=saved['scores']
        rank=sorted(range(len(scores)),key=lambda i:(-scores[i],i));rank={i:k+1 for k,i in enumerate(rank)}
        conv=source[row['conversation']]['conversation'];passages={t['dia_id']:dict(t,session=k,date=conv.get(k+'_date_time')) for k,ts in conv.items() if isinstance(ts,list) for t in ts}
        entry={k:row[k] for k in ['key','question','gold','answer','score','evidence','missing']}
        entry.update(conversation=row['conversation'],selected_count=len(saved['selected']),total_candidates=len(saved['ids']),carriers=[])
        sample=next(x for x in schedule if x['key']==row['key'])
        qa=source[row['conversation']]['qa'][sample['source_index']]
        for dialogue in qa['evidence']:
            matches=[i for i,x in enumerate(case.pairs) if dialogue in x.dialog_ids];assert len(matches)==1
            i=matches[0];pair=case.pairs[i];selected=pair.identity in saved['selected']
            assert selected==(dialogue not in row['missing'])
            neighbors=[]
            for j in range(max(0,i-2),min(len(case.pairs),i+3)):
                if j==i:continue
                n=case.pairs[j]
                neighbors.append(dict(offset=j-i,ids=n.dialog_ids,score=scores[j],selected=n.identity in saved['selected'],text=n.text))
            entry['carriers'].append(dict(dialogue=dialogue,source=passages[dialogue],pair_id=pair.identity,pair_text=pair.text,score=scores[i],margin=scores[i]-.48,rank=rank[i],selected=selected,pair_present_in_prompt=adapters[pair.identity]['element'] in sample['text'],neighbors=neighbors))
        rows.append(entry)
    assert len(rows)==4
    p.save(OUT/'miss_audit.json',dict(replay=dict(cases=30,exact_selections_and_payloads=True,max_cosine_difference=maxdiff),cache=cache,rows=rows,model_calls=0,hashes={str(x):p.sha(x) for x in [q.P/'MISS_AUDIT_PLAN.md',q.P/'miss_audit.py',OUT/'corrected_results.json',p.OUT/'selections.jsonl.gz',p.OUT/'adapter.jsonl.gz',p.prior.DATASET_PATH]}))
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()

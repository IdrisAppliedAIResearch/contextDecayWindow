"""Independent post-score reconstruction from sealed raw judgments."""
import gzip,json,re,hashlib
from pathlib import Path
import numpy as np

P=Path(__file__).parent
A=P/'artifacts'
R=A/'evaluation'
S=A/'subset'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8') as f: return [json.loads(x) for x in f]
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    for folder,name in [('reader','reader_complete.json'),('judges','judge_complete.json')]:
        for file,h in read(R/name)['hashes'].items(): assert sha(R/folder/file)==h
    votes=read(R/'votes.json')
    for key,v in votes.items():
        actual=[]
        for seed in [9100,9101,9102,9200]:
            response=read(R/'judges'/f'{key}_{seed}.json')['response']
            assert response['stop_type']=='eos' and not response.get('truncated')
            text=response['content']
            matches=list(re.finditer(r'(?im)^VERDICT:\s*(CORRECT|INCORRECT)\s*$',text))
            assert matches and re.search(r'(?m)^REASON:\s*\S',text[matches[-1].end():])
            actual.append(int(matches[-1].group(1).upper()=='CORRECT'))
        assert actual[-1]==v['score'] and int(sum(actual[:3])>=2)==v['majority']
    links=rows(R/'measurement_links.jsonl.gz')
    paired={}
    for x in links:
        if x['category']==5: continue
        pair=paired.setdefault(x['key'],{'conversation':x['conversation']})
        pair[x['arm']]=votes[x['blind_id']]['score']
    result=read(S/'results.json')
    xs=list(paired.values())
    n=len(xs); c0=sum(x['C0'] for x in xs); c1=sum(x['C1'] for x in xs)
    assert (n,c0,c1)==(result['primary']['n'],result['primary']['C0'],result['primary']['C1'])
    conv=sorted({x['conversation'] for x in xs})
    totals=np.array([[sum(x['C1']-x['C0'] for x in xs if x['conversation']==c),sum(x['conversation']==c for x in xs)] for c in conv])
    choices=np.random.default_rng(70107).integers(0,len(conv),(20000,len(conv)))
    sampled=totals[choices].sum(axis=1)
    interval=np.quantile(sampled[:,0]/sampled[:,1],[.025,.975])
    assert np.array_equal(interval,result['primary']['ci95'])
    sources={u['id']:u for u in rows(A/'prepared/sources.jsonl.gz')}
    selections={arm:{r['key']:r['selected_ids'] for r in rows(A/path/'selections.jsonl.gz')} for arm,path in [('C0','control'),('C1','characterization_v2')]}
    diag=rows(S/'diagnostics.jsonl.gz')
    for d in diag:
        ids={m for uid in selections[d['arm']][d['key']] for m in sources[uid]['member_ids']}
        expected=set(d['evidence'])
        assert d['annotated_all']==(bool(expected) and expected<=ids)
        assert d['score']==paired[d['key']][d['arm']]
    cross={a:{f'all_{int(av)}_correct_{co}':sum(d['arm']==a and d['has_annotation'] and d['annotated_all']==av and d['score']==co for d in diag) for av in (False,True) for co in (0,1)} for a in ['C0','C1']}
    assert cross==read(S/'availability_cross_tabs.json')
    summary=dict(status='PASS',raw_hashes_verified=True,votes_verified=len(votes),primary=result['primary'],
                 majority=result['majority_sensitivity'],strata=result['strata'],conversations=result['conversations'],
                 adversarial=result['adversarial'],cross_tabs=cross,
                 no_annotation={a:sum(d['arm']==a and not d['has_annotation'] for d in diag) for a in ['C0','C1']},
                 adjudication_changes=sum(v['adjudication_changed'] for v in votes.values()))
    with (S/'audit.json').open('x',encoding='utf-8') as f: json.dump(summary,f,indent=2)
    print(json.dumps(summary))
if __name__=='__main__': main()

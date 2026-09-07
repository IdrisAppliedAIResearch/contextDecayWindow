"""Exact matched full-adapter token counts; tokenization only, no generation."""
import json
import time
from collections import defaultdict
import numpy as np
import prepare as p
import runtime as r
from analysis.hh001_prompt import render_reader_prompt


def dist(values):
    a=np.asarray(values,dtype=float)
    return dict(n=len(a),min=float(a.min()),p05=float(np.quantile(a,.05)),median=float(np.median(a)),p95=float(np.quantile(a,.95)),max=float(a.max()),mean=float(a.mean()))


def main():
    p.committed(__file__);p.committed(p.P/'FULL_CONTEXT_CHECK_PLAN.md')
    part=p.read(p.OUT/'part1.json')
    for name,h in part['outputs'].items():assert p.sha(p.OUT/name)==h
    p.committed(p.OUT/'native_prompts.jsonl.gz')
    adapter=r.rows('adapter.jsonl.gz');native=r.rows('native_prompts.jsonl.gz')
    selections={v['key']:v for v in r.rows('selections.jsonl.gz')}
    byconv=defaultdict(list)
    for v in adapter:byconv[v['conversation']].append(v)
    byid={v['id']:v for v in adapter}
    assert len(native)==len({v['key'] for v in native})==1986
    for v in native:
        block='\n'.join(byid[k]['element'] for k in selections[v['key']]['selected'])
        assert render_reader_prompt(v['question'],block)==v['text']
    folder=p.OUT/'full_context_check'
    process=r.launch(folder)
    started=time.time()
    results=[]
    try:
        for i,v in enumerate(native):
            block='\n'.join(x['element'] for x in byconv[v['conversation']])
            text=render_reader_prompt(v['question'],block)
            prompt=r.native(text)
            # Selected native template must reproduce, including all system text.
            assert r.native(v['text'])==v['prompt']
            full=len(r.req('tokenize',dict(content=prompt,add_special=False))['tokens'])
            selected=v['tokens']
            assert selected<=full
            results.append(dict(key=v['key'],conversation=v['conversation'],category=v['category'],selected_tokens=selected,full_tokens=full,retained_ratio=selected/full,saved_tokens=full-selected,selected_records=len(selections[v['key']]['selected']),full_records=len(byconv[v['conversation']]),full_prompt_sha256=p.digest(prompt)))
            if (i+1)%200==0:print(f'Tokenized {i+1}/1986',flush=True)
        summary=dict(selected_tokens=dist([v['selected_tokens'] for v in results]),full_tokens=dist([v['full_tokens'] for v in results]),ratios=dist([v['retained_ratio'] for v in results]),saved_tokens=dist([v['saved_tokens'] for v in results]),near_full={str(t):sum(v['retained_ratio']>=t for v in results) for t in [.8,.9,.95]},empty=sum(v['selected_records']==0 for v in results),aggregate_retained=sum(v['selected_tokens'] for v in results)/sum(v['full_tokens'] for v in results))
        for group,field in [('conversations','conversation'),('categories','category')]:
            summary[group]={str(k):dict(n=len(rs),selected=dist([v['selected_tokens'] for v in rs]),full=dist([v['full_tokens'] for v in rs]),ratio=dist([v['retained_ratio'] for v in rs])) for k in sorted({v[field] for v in results}) for rs in [[v for v in results if v[field]==k]]}
        p.save(folder/'results.json',dict(status='PASS',measurement_calls=0,selected_prompt_reproductions=1986,seconds=time.time()-started,summary=summary,rows=results,hashes={str(path):p.sha(path) for path in [p.P/'FULL_CONTEXT_CHECK_PLAN.md',p.P/'full_context_check.py',p.OUT/'native_prompts.jsonl.gz',p.OUT/'adapter.jsonl.gz',p.OUT/'selections.jsonl.gz']}))
        print(json.dumps(summary),flush=True)
    finally:r.stop(process,folder)


if __name__=='__main__':main()

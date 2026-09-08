"""Executed input, reproduction, negative-gate and leakage checks."""
import ast
import json
from pathlib import Path
import re
import subprocess
from unittest.mock import patch
import prepare as p
import runtime as r
from episodic._render import render_episode_element


def main():
    p.committed(__file__)
    checks=p.fixtures()|p.e_replay()
    part=p.read(p.OUT/'part1.json')
    for path,h in part['hashes'].items():assert p.sha(path)==h
    for name,h in part['outputs'].items():assert p.sha(p.OUT/name)==h
    # The actual execution guard must reject before any transport call.
    network=[]
    for calibrated in [False,True]:
        with patch.object(r,'req',lambda *a,**k:network.append(a)), patch.object(p,'committed',lambda path:None), patch.object(p,'read',lambda path:{'status':'FAIL'}):
            try:r.gate(calibrated)
            except AssertionError:pass
            else:raise AssertionError('failed gate accepted')
    with patch.object(r,'req',lambda *a,**k:network.append(a)), patch.object(p,'committed',side_effect=FileNotFoundError('missing gate')):
        try:r.gate()
        except FileNotFoundError:pass
        else:raise AssertionError('missing gate accepted')
    assert not network
    checks['failed_missing_gate_network_calls']=len(network)
    for response in [dict(content='',stop_type='eos'),dict(content='<think>answer</think>',stop_type='eos'),dict(content='x',stop_type='limit'),dict(content='x',stop_type='eos',truncated=True)]:
        try:r.final(response)
        except AssertionError:pass
        else:raise AssertionError('invalid final accepted')
    checks['empty_reasoning_truncation_rejected']=True
    assert r.final(dict(content='Paris',stop_type='eos'))=='Paris'
    pairs={v['id']:v for v in r.rows('adapter.jsonl.gz')}
    prior_path=p.ROOT/'experiments/components/live_validation_009/artifacts/part1/prompts.jsonl.gz'
    old=p.prior._read_gzip_rows(prior_path)
    assert len(old)==1986
    index={v['comparison_key']:v for v in old}
    count=0
    # Reproduce every historical PAIRWISE element digest using the preserved pair.
    for row in r.rows('native_prompts.jsonl.gz'):
        prev=index[row['historical_key']]
        assert row['question']==prev['question'] and row['source_index']==prev['source_index']
        for identity,h in prev['arms']['PAIRWISE']['episode_element_sha256'].items():
            pair=pairs[identity]
            members=[v for v in pairs.values() if v['conversation']==pair['conversation']]
            turn=next(i+1 for i,v in enumerate(members) if v['id']==identity)
            first,sep,rest=pair['text'].partition('\n')
            record=dict(id=identity,turn_number=turn,user_message=first,assistant_message=rest,ground_truth_domain=pair['session'])
            assert p.digest(render_episode_element(record))==h
            count+=1
    checks['historical_episode_element_reproductions']=count
    # Selector signature accepts only records, scores and literal question.
    tree=ast.parse((p.P/'prepare.py').read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='select')
    assert [v.arg for v in fn.args.args]==['records','scores','question']
    text=ast.unparse(fn)
    assert not any(word in text for word in ['category','evidence','gold','answer','score.py'])
    assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in ast.walk(fn))
    checks['selector_leakage_boundary']=True
    fit=p.read(r.FIT)
    assert fit['status']=='PASS' and fit['original_prompts_exact'] and fit['context']==40960
    paths=[p.P/'IMPLEMENTATION_PLAN.md',p.P/'CAPACITY_RESOLUTION.md',p.P/'PRE_REGISTRATION.md',p.P/'prepare.py',p.P/'runtime.py',p.P/'score.py',Path(__file__),p.OUT/'part1.json',r.FIT,p.OUT/'native_prompts.jsonl.gz',p.OUT/'prompts.jsonl.gz',p.OUT/'adapter.jsonl.gz',p.OUT/'selections.jsonl.gz',prior_path]
    p.save(p.OUT/'preflight.json',dict(status='PASS',checks=checks,hashes={str(path):p.sha(path) for path in paths},measurement_calls=0,preflight_before_measurement=True))
    print(json.dumps(checks))


if __name__=='__main__':main()

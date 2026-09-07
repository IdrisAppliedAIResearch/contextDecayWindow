"""Post-completeness blinded semantic scoring; never imported by selection."""
import json
import re
import statistics
import threading
import time
import traceback
import sys
import numpy as np
import runtime as r
import prepare as p
from analysis.hh001_prompt import render_judge_prompt, parse_judge_verdict


def surface():
    complete=p.OUT/'reader/complete.json'
    p.committed(complete)
    c=p.read(complete)
    assert c['status']=='PASS' and len(c['hashes'])==1986
    raw={v['sample_id']:v for v in p.read(p.prior.DATASET_PATH)}
    packet=[]
    for row in r.rows('native_prompts.jsonl.gz'):
        path=p.OUT/'reader'/(row['key']+'.json')
        assert p.sha(path)==c['hashes'][row['key']]
        answer=r.final(p.read(path)['response'])
        if row['category']==5: continue
        qa=raw[row['conversation']]['qa'][row['source_index']]
        assert qa['question']==row['question']
        packet.append(dict(blind_id=p.digest('locomo-timeline-score\0'+row['key']), key=row['key'], question=row['question'], gold=str(qa['answer']), answer=answer))
    assert len(packet)==1540
    packet.sort(key=lambda x:x['blind_id'])
    p.save(p.OUT/'blind_mapping.json', {x['blind_id']:x.pop('key') for x in packet})
    p.save(p.OUT/'blind_surface.json',packet)


def run():
    r.gate(True)
    p.committed(__file__);p.committed(p.OUT/'blind_surface.json')
    folder=p.OUT/'judges'
    assert not folder.exists(),'EXISTING_RUN_NO_SILENT_RETRY'
    process=r.launch(folder)
    end=threading.Event()
    state=dict(phase='calibration',completed=0,total=4620,started=time.time(),request_started=None)
    elapsed=[]
    def monitor():
        while not end.wait(15):
            snapshot=dict(state,time=time.time(),server_alive=process.poll() is None)
            try: snapshot['gpu']=r.gpu()
            except Exception as e: snapshot['gpu_error']=repr(e)
            age=time.time()-(state['request_started'] or time.time())
            snapshot['slow']=age>max(180,5*statistics.median(elapsed[-20:]) if elapsed else 180)
            r.write_status(folder,snapshot)
            with (folder/'health.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(snapshot)+'\n')
            if snapshot['slow'] or not snapshot['server_alive'] or snapshot.get('gpu',{}).get('free_mib',99999)<1536:
                with (folder/'events.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(snapshot)+'\n')
    worker=threading.Thread(target=monitor,daemon=True);worker.start()
    try:
        r.calibration(folder)
        r.commit([folder], 'Gate independent judge-stage native-off calibration')
        p.committed(folder/'calibration.json')
        packet=p.read(p.OUT/'blind_surface.json')
        # Three separately ordered passes; no prior vote, arm, or evidence shown.
        for seed in [9100,9101,9102]:
            for item in sorted(packet,key=lambda x:p.digest(str(seed)+x['blind_id'])):
                assert process.poll() is None and r.gpu()['free_mib']>=1536
                identity=item['blind_id']+'_'+str(seed)
                prompt=r.native(render_judge_prompt(item['question'],item['gold'],item['answer']))
                assert len(r.req('tokenize',dict(content=prompt,add_special=False))['tokens'])+4096<=32768
                state.update(phase='judges',request_started=time.time(),current=identity)
                p.save(folder/(identity+'.pending.json'),dict(prompt_sha256=p.digest(prompt),started=state['request_started']))
                response=r.req('completion',dict(r.BASE,prompt=prompt,seed=seed,temperature=.2,top_p=.9))
                seconds=time.time()-state['request_started']
                p.save(folder/(identity+'.json'),dict(blind_id=item['blind_id'],seed=seed,response=response,seconds=seconds,prompt_sha256=p.digest(prompt)))
                verdict,reason=parse_judge_verdict(r.final(response))
                assert reason,'MISSING_RATIONALE'
                elapsed.append(seconds)
                state.update(completed=state['completed']+1,request_started=None)
        p.save(folder/'complete.json',dict(status='PASS',calls=4620,seconds=sum(elapsed),hashes={path.name:p.sha(path) for path in folder.glob('*.json') if re.fullmatch(r'[a-f0-9]{64}_910[012]\.json',path.name)}))
        state['phase']='complete'
    except BaseException as e:
        state['phase']='failure'
        p.save(folder/'failure.json',dict(error=repr(e),traceback=traceback.format_exc(),state=state))
        raise
    finally:
        end.set();worker.join(timeout=20);r.stop(process,folder);r.write_status(folder,dict(state,time=time.time()))


def votes():
    p.committed(p.OUT/'judges/complete.json')
    complete=p.read(p.OUT/'judges/complete.json')
    assert len(complete['hashes'])==4620
    values=[]
    for item in p.read(p.OUT/'blind_surface.json'):
        parsed=[]
        for seed in [9100,9101,9102]:
            name=item['blind_id']+'_'+str(seed)+'.json'
            assert p.sha(p.OUT/'judges'/name)==complete['hashes'][name]
            verdict,reason=parse_judge_verdict(r.final(p.read(p.OUT/'judges'/name)['response']))
            assert reason
            parsed.append(dict(verdict=verdict,reason=reason))
        disagreement=len({v['verdict'] for v in parsed})>1
        audit=int(p.digest('sia-h5-2026-07-26-v1'+item['blind_id'])[:8],16)%10==0
        values.append(dict(blind_id=item['blind_id'],votes=parsed,score=int(sum(v['verdict'] for v in parsed)>=2),disagreement=disagreement,audit_sample=audit))
    p.save(p.OUT/'blind_votes.json',values)
    # Primary stays the registered majority. Review changes are separate, additive.
    p.save(p.OUT/'review_packet.json',[dict(item,trigger='H2' if value['disagreement'] else 'H5') for item,value in zip(p.read(p.OUT/'blind_surface.json'),values) if value['disagreement'] or value['audit_sample']])


def report():
    p.committed(p.OUT/'blind_votes.json')
    mapping=p.read(p.OUT/'blind_mapping.json')
    votes={mapping[x['blind_id']]:x for x in p.read(p.OUT/'blind_votes.json')}
    source={v['sample_id']:v for v in p.read(p.prior.DATASET_PATH)}
    selection={v['key']:v for v in r.rows('selections.jsonl.gz')}
    adapter={v['id']:v for v in r.rows('adapter.jsonl.gz')}
    results=[]
    for row in r.rows('native_prompts.jsonl.gz'):
        response=p.read(p.OUT/'reader'/(row['key']+'.json'))
        answer=r.final(response['response'])
        required=source[row['conversation']]['qa'][row['source_index']].get('evidence',[])
        delivered={d for identity in selection[row['key']]['selected'] for d in adapter[identity]['dialogue_ids']}
        known={d for a in adapter.values() if a['conversation']==row['conversation'] for d in a['dialogue_ids']}
        required=set(map(str,required))
        status='unannotated' if not required else 'unresolved' if required-known else 'complete' if required<=delivered else 'partial' if required&delivered else 'none'
        results.append(dict(key=row['key'],conversation=row['conversation'],category=row['category'],question=row['question'],answer=answer,gold=source[row['conversation']]['qa'][row['source_index']].get('answer'),score=votes[row['key']]['score'] if row['category']!=5 else None,exact_abstention=re.sub(r'[^a-z0-9]+',' ',answer.lower()).strip()=='i don t know',evidence=status,missing=sorted(required-delivered),seconds=response['seconds'],output_tokens=response['response']['tokens_predicted']))
    primary=[v for v in results if v['category']!=5]
    def counts(group):return dict(n=len(group),correct=sum(v['score'] for v in group),accuracy=sum(v['score'] for v in group)/len(group) if group else None)
    byconv={c:counts([v for v in primary if v['conversation']==c]) for c in sorted({v['conversation'] for v in primary})}
    pairs=np.asarray([[v['correct'],v['n']] for v in byconv.values()])
    rng=np.random.default_rng(93002)
    sampled=pairs[rng.integers(0,10,size=(10000,10))].sum(axis=1)
    interval=np.quantile(sampled[:,0]/sampled[:,1],[.025,.975]).tolist()
    p.save(p.OUT/'results.json',dict(primary=counts(primary),by_category={str(c):counts([v for v in primary if v['category']==c]) for c in [1,2,3,4]},by_conversation=byconv,cluster_bootstrap_interval=interval,category5=dict(n=446,exact_abstentions=sum(v['exact_abstention'] for v in results if v['category']==5)),by_evidence={e:counts([v for v in primary if v['evidence']==e]) for e in sorted({v['evidence'] for v in primary})},rows=results))


if __name__=='__main__':
    {'surface':surface,'run':run,'votes':votes,'report':report}[sys.argv[1]]()

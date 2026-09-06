import json,hashlib,os,time,concurrent.futures,sys,html
from pathlib import Path
import numpy as np
from corpus import make_session
from mechanism import build,ENGINE
from analysis.hh001_prompt import render_reader_prompt
from episodic._render import render_stm_payload
P=Path(__file__).parent/'artifacts/part1/development'
def init():
 global EMB,SENT
 from episodic._embedding import PinnedEmbedder
 EMB=PinnedEmbedder(Path(r'C:\Users\muzaf\.cache\huggingface\hub\Qwen3-Embedding-0.6B-GGUF\Qwen3-Embedding-0.6B-Q8_0.gguf'))
 SENT=hashlib.sha256(EMB('episodic call-shape sentinel: one text per call').tobytes()).hexdigest()
def emb(t):
 start=time.process_time();v=EMB(t);return t,v,SENT,os.getpid(),time.process_time()-start
def save(n,x):(P/n).write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def main():
 P.mkdir(parents=True,exist_ok=True);sessions=[];labels={};ledgers=[]
 for seed in range(93001,93005):
  s,l,g=make_session(seed);sessions.append(s);labels.update(l);ledgers+=g
 save('sources.json',sessions);save('labels.json',labels);save('ledger.json',ledgers)
 texts=sorted({e['user_message']+'\n'+e['assistant_message'] for s in sessions for e in s['episodes']}|{q['query'] for s in sessions for q in s['probes']})
 if (P/'vectors.npz').exists():
  man=json.loads((P/'vector_manifest.json').read_text());assert man['texts']==texts;array=np.load(P/'vectors.npz')['vectors']
 else:
  started=time.monotonic()
  with concurrent.futures.ProcessPoolExecutor(max_workers=8,initializer=init) as pool:results=list(pool.map(emb,texts))
  assert len({r[2] for r in results})==1
  array=np.vstack([r[1] for r in results]);np.savez(P/'vectors.npz',vectors=array)
  save('vector_manifest.json',dict(texts=texts,file_sha256=hashlib.sha256((P/'vectors.npz').read_bytes()).hexdigest(),sentinel=results[0][2],calls=len(texts)+8,pids=sorted({r[3] for r in results}),cpu_seconds=sum(r[4] for r in results),wall_seconds=time.monotonic()-started))
 v=dict(zip(texts,array));rows=[];prompts=[]
 for s in sessions:
  es=[dict(e,embedding=v[e['user_message']+'\n'+e['assistant_message']]) for e in s['episodes']]
  by={e['id']:e for e in es}
  for q in s['probes']:
   c,t,tr=build(es,q['query'],v[q['query']]);gold=labels[q['id']];sets=gold['sufficient_sets'];avail=lambda b:any(all(html.escape(x,quote=False) in b for x in group) for group in sets)
   oracle=render_stm_payload([],[by[x] for x in gold['gold_ids']]) if gold['gold_ids'] else ''
   for arm,block in [('C0',c),('C1',t),('ORACLE',oracle),('NULL','')]:prompts.append(dict(id=q['id'],session=s['id'],type=q['type'],arm=arm,query=q['query'],reference=gold['answer'],prompt=render_reader_prompt(q['query'],block)+'\n<think>\n</think>\n'))
   rows.append(dict(session=s['id'],type=q['type'],changed=c!=t,C0=avail(c),C1=avail(t),trace=tr))
 save('prompts.json',prompts);save('rows.json',rows)
 print(json.dumps([dict(type=k,changed=sum(x['changed'] for x in rows if x['type']==k),C0=sum(x['C0'] for x in rows if x['type']==k),C1=sum(x['C1'] for x in rows if x['type']==k)) for k in ['straight','irrelevant','future','proposal','latest','absent']]))
if __name__=='__main__':main()

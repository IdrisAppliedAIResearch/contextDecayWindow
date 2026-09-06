import json,hashlib,subprocess,sys
from pathlib import Path
import numpy as np
from mechanism import build,OLD,ENGINE
from analysis.hh001_prompt import render_reader_prompt
P=Path('experiments/study_D/artifacts/confirmation');O=Path(__file__).parent/'artifacts/part1';O.mkdir(parents=True,exist_ok=True)
read=lambda n:json.loads((P/n).read_text())
for path in [OLD,ENGINE]:assert not subprocess.check_output(['git','status','--porcelain'],cwd=path).strip()
manifest=read('vector_manifest.json');assert hashlib.sha256((P/'vectors.npz').read_bytes()).hexdigest()==manifest['file_sha256']
v=dict(zip(manifest['texts'],np.load(P/'vectors.npz')['vectors']))
labels=read('labels.json');mapping=read('mapping.json');prompts=read('prompts.json');lookup={r['item']:r['prompt_sha256'] for r in mapping if r['arm']=='C1'}
rows=[]
for s in read('sources.json'):
 es=[dict(e,embedding=v[e['user_message']+'\n'+e['assistant_message']]) for e in s['episodes']]
 for q in s['probes']:
  c,t,tr=build(es,q['query'],v[q['query']]);assert render_reader_prompt(q['query'],c)+'\n<think>\n</think>\n'==prompts[lookup[q['id']]]['prompt']
  cc,tt,_=build(es,q['query'],v[q['query']]);assert (c,t)==(cc,tt)
  if q['type']!='T1':assert c==t
  sets=labels[q['id']]['sufficient_sets'];import html
  available=lambda block:any(all(html.escape(span,quote=False) in block for span in g) for g in sets)
  rows.append(dict(session=s['id'],type=q['type'],changed=c!=t,C0_complete=available(c),C1_complete=available(t),trace=tr if q['type']=='T1' else None))
assert len(rows)==224
out=dict(status='PASS',reproduced=224,repeat_equal=224,before=[dict(C0=sum(r['C0_complete'] for r in rows if r['type']=='T1'),C1=sum(r['C1_complete'] for r in rows if r['type']=='T1'))],rows=rows)
(O/'replay.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='rows'}))

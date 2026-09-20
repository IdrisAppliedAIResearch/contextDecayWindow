import sys,copy,ast
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from mechanism import D,build
from corpus import make_session

def test_corpus_state():
 for seed in range(93001,93005):
  s,labels,ledger=make_session(seed);assert len(s['episodes'])==140 and len(s['probes'])==6
  ids={e['id']:e for e in s['episodes']}
  for q in s['probes']:
   l=labels[q['id']];meta=l['rationale'];assert all(ids[x]['turn_number']<109 for x in l['gold_ids'])
   # Independent text reconstruction of effective updates, ignoring the generator ledger.
   import re
   updates=[]
   pattern=re.compile(r'The delivery location for "'+re.escape(meta['subject'])+r'" is now the (\w+)\.')
   for e in s['episodes']:
    match=pattern.search(e['user_message'])
    if match and (q['type']=='latest' or e['turn_number']<meta['anchor']):updates.append((e['turn_number'],match.group(1)))
   expected=max(updates)[1] if updates else "I don't know"
   assert expected==l['answer']
   subject_ledger=[x for x in ledger if x['subject']==meta['subject'] and (q['type']=='latest' or x['turn']<meta['anchor'])]
   assert (max(subject_ledger,key=lambda x:x['turn'])['value'] if subject_ledger else "I don't know")==expected

def examples():
 v=np.zeros(1024,dtype=np.float32);v[0]=1.
 es=[dict(id=str(i),turn_number=i,user_message=u,assistant_message='',embedding=v) for i,u in enumerate(['The setting for "A" is office.','The setting for "A" is warehouse.','The meeting "M" occurred.']+['unrelated']*35,1)]
 return es,v

def test_routes_and_repeat():
 es,v=examples();before=copy.deepcopy(es)
 queries=['What was the setting for "A" immediately before "M"?','What is the latest setting for "A"?','What was the setting for "A" after "M"?','Unknown question','What was "X" before "M"?','What was "A" before "missing"?']
 for q in queries:
  c,t,tr=build(es,q,v);assert (c,t)==build(es,q,v)[:2]
  if 'immediately before' not in q:assert c==t
  else:assert tr['eligible_after']==[2,1,0]
 assert all(x['user_message']==y['user_message'] for x,y in zip(es,before))
 es[0]['user_message']='Another meeting "M" occurred.'
 assert build(es,queries[0],v)[0]==build(es,queries[0],v)[1]

def test_recent_and_oversize():
 es,v=examples();q='What was the setting for "A" immediately before "M"?'
 assert build(es[:3],q,v)[0]==build(es[:3],q,v)[1]
 for e in es:e['user_message']+=' x'*17000
 c,t,tr=build(es,q,v);assert tr['selected_ids']==[]

def test_no_measurement_imports():
 source=Path(__file__).with_name('mechanism.py').read_text()
 def check(s):
  names=[n.module or '' for n in ast.walk(ast.parse(s)) if isinstance(n,ast.ImportFrom)]+[a.name for n in ast.walk(ast.parse(s)) if isinstance(n,ast.Import) for a in n.names]
  assert not any(any(bad in x for bad in ['corpus','scor','ledger','label']) for x in names)
 check(source)
 import pytest
 with pytest.raises(AssertionError):check(source+'\nimport corpus')

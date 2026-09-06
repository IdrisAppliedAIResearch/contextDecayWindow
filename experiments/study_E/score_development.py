import json,hashlib,re,subprocess,sys
from pathlib import Path
P=Path(__file__).parent/'artifacts/part1/reader'
def read(n):return json.loads((P/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):
 assert not (P/n).exists()
 (P/n).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def committed(p):assert subprocess.check_output(['git','show','HEAD:'+p.relative_to(Path.cwd()).as_posix()]).replace(b'\r\n',b'\n')==p.read_bytes().replace(b'\r\n',b'\n')
def score(text,reference):
 x=text.strip().replace('’',"'").strip(' \"\'`.!?').casefold();gold=reference.casefold()
 if x.startswith('the '):x=x[4:]
 if x in ['office','warehouse','studio','depot','workshop','laboratory','annex','hangar',"i don't know"]:return int(x==gold),'Canonical location or abstention compared exactly.'
 if not x:return 0,'NO_ANSWER'
 return None,'NEEDS_ADJUDICATION: outside frozen mechanical grammar.'
if sys.argv[1]=='score':
 committed(P/'complete.json');assert read('complete.json')['status']=='PASS' and sha(P/'responses.jsonl')==read('complete.json')['responses_sha256']
 rows=[json.loads(x) for x in (P/'responses.jsonl').read_text().splitlines()][3:];assert len(rows)==32
 blind=[];mapping=[]
 for r in rows:
  q=r['row'];answer=r['response']['content'];bid=hashlib.sha256((q['id']+q['arm']).encode()).hexdigest()
  blind.append(dict(blind_id=bid,query=q['query'],reference=q['reference'],response=answer))
  mapping.append(dict(blind_id=bid,type=q['type'],session=q['session'],arm=q['arm']))
 blind.sort(key=lambda x:x['blind_id']);scores=[]
 assert score('', 'office')[0]==0 and score('Not office','office')[0] is None
 for r in blind:
  v,reason=score(r['response'],r['reference']);scores.append(dict(blind_id=r['blind_id'],score=v,rationale=reason))
 save('blind_surface.json',blind);save('mapping.json',mapping);save('scores.json',scores)
 pending={x['blind_id'] for x in scores if x['score'] is None};save('pending_adjudication.json',[x for x in blind if x['blind_id'] in pending]);save('scoring_gate.json',dict(status='PENDING_ADJUDICATION' if pending else 'PASS',pending=len(pending),scores_sha256=sha(P/'scores.json')))
 print(json.dumps(read('scoring_gate.json')))
else:
 committed(P/'scores.json');assert read('scoring_gate.json')['status']=='PASS';assert sha(P/'scores.json')==read('scoring_gate.json')['scores_sha256']
 scores={x['blind_id']:x['score'] for x in read('scores.json')};mapping=read('mapping.json');out={}
 for kind in ['straight','irrelevant','future','proposal','latest','absent']:
  out[kind]={}
  for arm in ['C0','C1']:
   rows=[r for r in mapping if r['type']==kind and r['arm']==arm]
   if rows:out[kind][arm]=dict(n=len(rows),correct=sum(scores[r['blind_id']] for r in rows))
 save('descriptive_result.json',dict(status='DEVELOPMENT_ONLY',by_type=out));print(json.dumps(out))

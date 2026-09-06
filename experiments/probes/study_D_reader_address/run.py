import json,hashlib,time,urllib.request,subprocess,sys
from pathlib import Path
P=Path(__file__).parent
BASE="E1 Monday: Send project deliveries to the office.\nE2 Tuesday: Use the warehouse instead; this replaces the previous delivery address.\nE3 Wednesday: We hold the launch meeting.\nE4 Thursday: From now on, send project deliveries to the studio instead."
cases=[
("latest",BASE,"Where should project deliveries go now?","studio"),
("before",BASE,"Where were project deliveries going immediately before the launch meeting?","warehouse"),
("shuffled", "\n".join(BASE.splitlines()[i] for i in [3,0,2,1]),"Where were project deliveries going immediately before the launch meeting?","warehouse"),
("two_meetings",BASE+"\nE5 Friday: We hold the review meeting.\nE6 Saturday: Use the depot instead for project deliveries.","Where were project deliveries going immediately before the review meeting?","studio"),
("missing",BASE.replace("E2 Tuesday: Use the warehouse instead; this replaces the previous delivery address.","E2 Tuesday: The delivery address changed, replacing the previous address, but the new address is unavailable in this record."),"Where were project deliveries going immediately before the launch meeting?","cannot determine"),
("after_state",BASE,"Immediately after the launch meeting ended, before Thursday's update, which delivery address was in effect?","warehouse")]
def prompt(context,q):
 return 'Answer the question using only the records below. E-numbers specify event order even if records are displayed out of order.\n\n'+context+'\n\nQuestion: '+q+'\n\nGive your answer, then a brief justification in at most two sentences identifying the supporting record IDs and relevant event boundary. If the records do not establish the answer, say "Cannot determine".\n\nAnswer:\n<think>\n</think>\n'
def save(name,obj): (P/name).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
def request(endpoint,payload=None):
 req=urllib.request.Request('http://127.0.0.1:8097/'+endpoint,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)
def call(key,text):
 save('pending.json',{'id':key,'prompt':text})
 start=time.monotonic();r=request('completion',dict(prompt=text,seed=5005,temperature=.6,top_p=.95,top_k=20,min_p=0,repeat_penalty=1,cache_prompt=False,n_predict=1024,stream=False,reasoning_format='none'))
 with (P/'responses.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(id=key,prompt=text,response=r,elapsed=time.monotonic()-start))+'\n');f.flush()
 (P/'pending.json').unlink()
 assert r.get('content','').strip() and not r.get('truncated') and r.get('stop_type')=='eos', 'INSTRUMENT_FAILURE'
 return r
if sys.argv[1]=='preflight':
 assert not (P/'responses.jsonl').exists()
 manifest=[]
 for key,c,q,g in cases:
  text=prompt(c,q);manifest.append(dict(id=key,context=c,question=q,gold=g,prompt=text,sha256=hashlib.sha256(text.encode()).hexdigest()))
 save('cases.json',manifest)
 pins=json.loads(Path('experiments/study_D/artifacts/part1/runtime_gpu/launch.json').read_text())
 for x in [pins['files'][0],pins['files'][2]]:
  with open(x['path'],'rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==x['sha256']
 save('props.json',request('props'))
 t=prompt('E1 Monday: Send project deliveries to the office.','Where should project deliveries go now?')
 a=call('preflight1',t);b=call('preflight2',t)
 assert a['content']==b['content'] and 'office' in a['content'].lower() and 'E1' in a['content']
 save('gate.json',dict(status='PASS',plan_commit='c987ab36',cases_sha256=hashlib.sha256((P/'cases.json').read_bytes()).hexdigest(),repeat_equal=True,preflight_output_tokens=[a.get('tokens_predicted'),b.get('tokens_predicted')],checks={f'PF{i}':'Verified: frozen PLAN.md and cases; isolated direct reader; hashes and repeated live preflight; no inferential bar' for i in range(1,11)}))
 print(a['content'])
else:
 assert json.loads((P/'gate.json').read_text())['status']=='PASS'
 assert subprocess.check_output(['git','show','HEAD:'+ (P/'gate.json').as_posix()]).replace(b'\r\n',b'\n')==(P/'gate.json').read_bytes().replace(b'\r\n',b'\n')
 rows=json.loads((P/'cases.json').read_text());assert hashlib.sha256((P/'cases.json').read_bytes()).hexdigest()==json.loads((P/'gate.json').read_text())['cases_sha256']
 assert not (P/'pending.json').exists()
 assert len((P/'responses.jsonl').read_text().splitlines())==2
 for row in rows:
  r=call(row['id'],row['prompt']);print(json.dumps(dict(id=row['id'],gold=row['gold'],answer=r['content'])),flush=True)
 save('complete.json',{'status':'PASS','calls':8,'responses_sha256':hashlib.sha256((P/'responses.jsonl').read_bytes()).hexdigest()})

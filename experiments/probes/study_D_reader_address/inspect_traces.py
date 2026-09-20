import json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT.parent/'contextDecayWindow-study-D-control/episodic/src'))
from episodic._packing import pack_stm_payload
from episodic._render import render_stm_payload
P=ROOT/'experiments/study_D/artifacts/confirmation'
def read(n):return json.loads((P/n).read_text())
sources={s['id']:s['episodes'] for s in read('sources.json')};labels=read('labels.json');traces=[t for t in read('mechanism_sealed.json') if t['type']=='T1'];assert len(traces)==32
rows=[]
def attempt(order,target,budget):
 admitted=[]
 for pos,e in enumerate(order,1):
  used=len(render_stm_payload([],admitted));cost=len(render_stm_payload([],admitted+[e]))-used
  fits=used+cost<=budget
  if e['id']==target:return dict(rank=pos,cost=cost,remaining=budget-used,admitted=fits)
  if fits:admitted.append(e)
for t in traces:
 es=sources[t['session']];by={e['id']:e for e in es};g=labels[t['id']]['gold_ids'];target=next(x for x in g if by[x]['turn_number']!=45);anchor=next(x for x in g if x!=target)
 assert by[target]['turn_number']==44 and by[anchor]['turn_number']==45
 eligible=set(t['route']['eligible']);order=[es[i] for i in t['route']['anchors']]+[es[i] for i in t['ranking'] if i in eligible]
 temporal=pack_stm_payload([],order,8000);assert list(temporal.selected_ids)==t['temporal_ids']
 recent={e['id'] for e in es[-32:]};first=set(temporal.selected_ids);merged=[by[x] for x in temporal.selected_ids]+[es[i] for i in t['ranking'] if es[i]['id'] not in first|recent]
 final=pack_stm_payload([],merged,32000);assert list(final.selected_ids)==t['selected_ids']
 assert first<=set(final.selected_ids)
 rows.append(dict(session=t['session'],complete=t['availability']['C1']['complete'],target_turn=44,anchor_delivered=anchor in final.selected_ids,target_eligible=es.index(by[target]) in eligible,target_global_rank=t['ranking'].index(es.index(by[target]))+1,temporal=attempt(order,target,8000),final=attempt(merged,target,32000),target_user_chars=len(by[target]['user_message']),target_assistant_chars=len(by[target]['assistant_message']),target_fact_chars=len(by[target]['user_message'].splitlines()[0]),temporal_admissions=len(first)))
miss=[r for r in rows if not r['complete']];assert len(miss)==16
result=dict(standing='POSTHOC saved-trace replay, no new reader result',replayed=32,missing=16,inputs={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['sources.json','labels.json','mechanism_sealed.json']},rows=rows)
(Path(__file__).parent/'trace_inspection.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(miss,indent=2))
for group,name in [(miss,'misses'),([r for r in rows if r['complete']],'complete')]:
 print(name,'temporal_admitted',sum(r['temporal']['admitted'] for r in group),'anchor_delivered',sum(r['anchor_delivered'] for r in group))
 for key in ['target_global_rank','target_user_chars','target_assistant_chars','target_fact_chars']:
  vals=sorted(r[key] for r in group);print(key,min(vals),max(vals))
 for stage in ['temporal','final']:
  for key in ['rank','cost','remaining']:
   vals=[r[stage][key] for r in group];print(stage,key,min(vals),max(vals))

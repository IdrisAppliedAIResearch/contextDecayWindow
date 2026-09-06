"""Mechanical-only scorer. Reads no arm map, corpus, or mechanism artifacts."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'artifacts/confirmation'

def normalize(text):
    return text.strip().replace('\u2019',"'").replace('\u2018',"'").strip(' \t\n\r"\'`.')

def score(row):
    if not row.get('complete') or not row['response'].strip():
        return {'score':0,'parsed':None,'rationale':'NO_ANSWER or incomplete final output; no reasoning-block credit.'}
    value=normalize(row['response'])
    reference=normalize(row['reference'])
    if value.casefold()=="i don't know":
        return {'score':int(reference.casefold()=="i don't know"),'parsed':'ABSTENTION','rationale':'Explicit canonical abstention compared with the registered reference.'}
    if re.fullmatch(r'\d+(?:\s+days?)?',value,re.I):
        number=int(value.split()[0])
        correct=row['type']=='T4' and reference.isdigit() and number==int(reference)
        return {'score':int(correct),'parsed':number,'rationale':'Bare integer/day duration compared exactly; no substring matching.'}
    if re.fullmatch(r'[A-Za-z]{2,5}-[A-Za-z0-9-]+',value):
        return {'score':int(value.casefold()==reference.casefold()),'parsed':value,'rationale':'Single bare identifier compared with the registered identifier; no other claim present.'}
    return {'score':None,'parsed':None,'rationale':'NEEDS_ADJUDICATION: surface is outside the prespecified unambiguous mechanical grammar.'}

def main():
    assert not (OUT/'blind_scores.json').exists(),'Committed scores must never be overwritten'
    gate=json.loads((OUT/'reader_gate.json').read_text())
    assert gate['status']=='PASS'
    rel=(OUT/'reader_gate.json').relative_to(ROOT).as_posix()
    assert subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT).replace(b'\r\n',b'\n')==(OUT/'reader_gate.json').read_bytes().replace(b'\r\n',b'\n')
    raw=(OUT/'blind_surface.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==gate['blind_surface_sha256']
    # Required deliberate NO_ANSWER and non-substring sentinels.
    assert score({'complete':False,'response':'<think>VX-123456789ABC</think>','reference':'VX-123456789ABC','type':'T1'})['score']==0
    assert score({'complete':True,'response':'Not VX-123456789ABC','reference':'VX-123456789ABC','type':'T1'})['score'] is None
    rows=json.loads(raw)
    scores=[{'blind_id':r['blind_id'],**score(r)} for r in rows]
    pending_ids={r['blind_id'] for r in scores if r['score'] is None}
    (OUT/'blind_scores.json').write_text(json.dumps(scores,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    (OUT/'adjudication_packet.json').write_text(json.dumps([r for r in rows if r['blind_id'] in pending_ids],sort_keys=True,indent=2)+'\n',encoding='utf-8')
    status={'status':'PENDING_ADJUDICATION' if pending_ids else 'PASS','scored_surfaces':len(rows),'pending':len(pending_ids),'blind_scores_sha256':hashlib.sha256((OUT/'blind_scores.json').read_bytes()).hexdigest(),'mechanism_opened':False}
    (OUT/'scoring_gate.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(status))

if __name__=='__main__':
    main()

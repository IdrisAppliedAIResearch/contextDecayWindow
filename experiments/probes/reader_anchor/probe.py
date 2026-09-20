"""Constructed anchor diagnostic; expectations never sent to reader."""
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'locomo_relevance_timeline'))
import runtime as r
import prepare as p
P=Path(__file__).resolve().parent
OUT=P/'artifacts'
CASES=[
('one_thread',[
'May 1, Alex: I live in Bristol. I interviewed for a teaching job at Elm School today.',
'May 14, Alex: They sent me an offer for that position.',
'May 15, Alex: I said yes this morning!',
'May 20, Alex: I moved to Bath yesterday.'
], 'Identify the event meant by "Alex accepted the teaching job". Where was Alex living immediately before it?',
'Resolved: acceptance passage3, connected through1/2, Bristol. Prefix through3 preserves the stated pre-event residence.'),
('two_threads',[
'May 1, Alex: I live in Bristol. I interviewed at Elm School.',
'May 3, Alex: I also interviewed at Pine School.',
'May 14, Alex: Both schools offered me teaching positions.',
'May 15, Alex: I accepted one of the offers today.'
], 'Did Alex accept the Elm School job? Identify the acceptance event if the history establishes it.',
'Ambiguous: passage4 is an acceptance but school unresolved; Elm and Pine both possible. No justified Elm cutoff.'),
('later_clarification',[
'May 1, Alex: I interviewed at Elm School and Pine School.',
'May 14, Alex: Both offered me teaching positions.',
'May 15, Alex: I accepted an offer today!',
'May 16, Sam: Which school?',
'May 16, Alex: Elm. Pine was too far away.'
], 'Identify when Alex accepted the Elm School job and the passages that establish which offer it was.',
'Resolved May15 passage3 through clarification5 and candidates1/2. Cutoff at3 discards disambiguating later evidence.'),
('retrospective_residence',[
'May 1, Alex: I interviewed for the teaching position at Elm School.',
'May 14, Alex: Elm sent the offer.',
'May 15, Alex: I accepted it today.',
'May 20, Alex: I moved to Bath yesterday. Until that move I lived in Bristol, including when I accepted Elm.'
], 'Identify the Elm acceptance event. Where was Alex living immediately before accepting?',
'Resolved passage3 via1/2, Bristol established retrospectively in4. Cutoff at3 loses answer evidence.'),
('intention_not_event',[
'May 1, Alex: I interviewed at Elm School.',
'May 14, Alex: Elm offered me the position.',
'May 15, Alex: I plan to accept tomorrow, if we agree on salary.',
'May 16, Alex: Negotiations are still ongoing. I have not accepted.'
], 'Identify the event when Alex accepted the Elm job, if established.',
'Unresolved/not occurred in supplied history. Proposal3 is not acceptance;4 explicitly denies completion.'),
('different_people',[
'May 1, Alex: I interviewed at Elm School.',
'May 2, Sam: I interviewed at Pine School.',
'May 14, Alex: Elm sent me an offer.',
'May 14, Sam: Pine offered me the position too.',
'May 15, Sam: I accepted my offer today.',
'May 16, Alex: I am still deciding.'
], 'Did Alex accept the Elm job? Identify an event only if the history establishes it.',
'No Alex acceptance established; passage5 belongs to Sam/Pine. Passage6 leaves Alex unresolved.'),
('missing_antecedent',[
'May 15, Alex: I accepted the offer today.',
'May 16, Sam: Congratulations!'
], 'Did Alex accept a job at Elm School? Identify an event only if the history establishes it.',
'Unresolved offer type/employer. Passage1 establishes acceptance of an unspecified offer, not Elm or even a job.'),
('older_named_thread',[
'May 1, Alex: I interviewed at Elm School for a teaching position.',
'May 8, Alex: I interviewed at Pine School for an office position.',
'May 12, Alex: Pine sent its offer yesterday.',
'May 14, Alex: Elm sent its offer today.',
'May 15, Alex: I said yes to the office role. I have not decided about teaching.'
], 'Which employer did Alex accept, and which passage is the acceptance event?',
'Resolved Pine, passage5 through office-role link2 and offer3. More recent Elm offer4 is not accepted.')
]
INSTRUCTION='''Read this chronological conversation. Resolve the particular event requested by the question using only the supplied evidence. A plan is not a completed event. Do not invent missing participants or links. If several interpretations remain possible, say so.
Return a JSON object with: status (resolved, ambiguous, or unresolved), event_passages (list of integer IDs), connecting_passages (list of integer IDs), competing_interpretations (list of strings), answer (brief), cutoff_safe (true, false, or null), explanation (at most three sentences citing passage IDs). cutoff_safe asks whether keeping only passages through the event would preserve the evidence needed for this question, including later clarification or retrospective facts. If no specific event can be resolved, use null. This is a request for a brief evidence justification, not a hidden thinking trace.

Conversation:
{history}

Question: {question}'''

def gate():
    p.committed(OUT/'inputs.json')
    value=p.read(OUT/'inputs.json')
    assert value['status']=='PASS' and value['code']==p.sha(__file__)

def main():
    p.committed(P/'PLAN.md');p.committed(__file__)
    assert not OUT.exists();OUT.mkdir()
    # Actual guard rejects missing inputs and a failed gate before transport.
    try:gate()
    except Exception:pass
    else:raise AssertionError('missing input gate accepted')
    oldread,oldcommitted=p.read,p.committed
    try:
        p.read=lambda path:dict(status='FAIL');p.committed=lambda path:None
        try:gate()
        except AssertionError:pass
        else:raise AssertionError('failed input gate accepted')
    finally:p.read,p.committed=oldread,oldcommitted
    pins=p.read(r.OLD/'runtime_pins.json')
    for pin in pins:assert p.sha(pin['path'])==pin['sha256']
    rows=[];expected=[]
    for name,history,question,gold in CASES:
        text=INSTRUCTION.format(history='\n'.join(f'[{i+1}] {s}' for i,s in enumerate(history)),question=question)
        assert gold not in text
        rows.append(dict(name=name,key=p.digest(text),text=text,passages=len(history)))
        expected.append(dict(name=name,interpretation=gold))
    assert len(rows)==len({v['key'] for v in rows})==8
    p.save(OUT/'expectations.json',expected)
    p.save(OUT/'inputs.json',dict(status='PASS',code=p.sha(__file__),plan=p.sha(P/'PLAN.md'),pins=pins,rows=rows,negative_gates=True))
    r.commit([OUT], 'Freeze reader anchor histories and expectations before calls')
    gate();process=r.launch(OUT/'runtime')
    try:
        schedule=[]
        for row in rows:
            prompt=r.native(row['text'])
            tokens=len(r.req('tokenize',dict(content=prompt,add_special=False))['tokens'])
            assert tokens+4096<=r.CONTEXT
            schedule.append(dict(row,prompt=prompt,tokens=tokens))
        cal=[];cp=r.native('What is 17 + 28? Answer only the number.')
        for i in range(2):
            response=r.req('completion',dict(r.BASE,prompt=cp,n_predict=64))
            p.save(OUT/f'calibration_{i}.json',response);cal.append(response)
        assert r.final(cal[0])==r.final(cal[1])=='45' and cal[0]['content']==cal[1]['content']
        p.save(OUT/'calibration_gate.json',dict(status='PASS',schedule=schedule,native_thinking=False))
        r.commit([OUT], 'Gate native-off anchor probe calibration and prompt fit')
        gate();p.committed(OUT/'calibration_gate.json')
        for row in schedule:
            p.save(OUT/(row['name']+'.pending.json'),dict(key=row['key'],started=time.time()))
            start=time.time();response=r.req('completion',dict(r.BASE,prompt=row['prompt']))
            p.save(OUT/(row['name']+'.json'),dict(key=row['key'],response=response,seconds=time.time()-start))
            r.final(response)
            print(row['name']+' captured',flush=True)
        gate()
        p.save(OUT/'complete.json',dict(status='PASS',calls=8,hashes={row['name']:p.sha(OUT/(row['name']+'.json')) for row in rows}))
    finally:r.stop(process,OUT/'runtime')

if __name__=='__main__':main()

"""Extension-004 substantive revision history, separate from original corpus."""
import re
from corpus import make_session as original_session, key

def make_session(seed):
    session,labels=original_session(seed)
    t1=next(p for p in session['probes'] if p['type']=='T1')
    project,meeting=re.findall(r'"([^\"]+)"',t1['query'])
    reserved={10,15,20,25,30,35,40,45,50,65,75,80,85,90,95}
    assertions={}
    for e in session['episodes']:
        turn=e['turn_number']
        if turn<=100 and turn not in reserved:
            code=f'RV-{seed}-{turn:03d}'
            span=f'The approved setting for "{project}" is now {code}; this replaces the previous approved setting.'
            e['user_message']=span+'\n'+e['user_message']
            e['id']=key(e['user_message']+'\n'+e['assistant_message'])
            assertions[turn]=(span,code)
    assert len({code for _,code in assertions.values()})==len(assertions)
    for probe in session['probes']:
        if probe['type'] not in ('T1','T2'):
            continue
        old=probe['id']
        if probe['type']=='T1':
            target=max(t for t in assertions if t<45)
            assert target==44
            query=f'What was the approved setting for "{project}" immediately before "{meeting}"?'
            span,code=assertions[target]
            spans=[span,session['episodes'][44]['user_message'].split('\n')[0]]
            turns=[44,45]
        else:
            target=max(assertions)
            assert target==100
            query=f'What is the latest approved setting for "{project}"?'
            span,code=assertions[target]
            spans=[span]
            turns=[target]
        probe['query']=query
        probe['id']=key(session['id']+'\n'+probe['type']+'\n'+query)
        del labels[old]
        labels[probe['id']]={'answer':code,'sufficient_sets':[spans],'gold_ids':[session['episodes'][t-1]['id'] for t in turns]}
    return session,labels

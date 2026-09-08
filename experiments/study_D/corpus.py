"""Synthetic development corpus; labels are returned separately from source data."""
import hashlib
import random
from datetime import date, timedelta

def key(text):
    return hashlib.sha256(text.encode()).hexdigest()

def make_session(seed):
    rng=random.Random(seed)
    sid=f'session-{seed}'
    names=[f'{word}-{rng.randrange(100,999)}' for word in ('Alder','Birch','Cedar','Dahlia','Elm','Fir','Grove','Hazel','Iris','Juniper','Kestrel','Larch')]
    codes=[f'{rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")}{rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")}-{rng.randrange(1000,9999)}' for _ in range(9)]
    p1,p2,p3,meeting,start,end,bridge,team,person,unused,wrong,other=names
    d0=date(2025,1,1)+timedelta(days=rng.randrange(300))
    duration=rng.randrange(4,24)
    plants={
        10:f'The current access setting for "{p3}" is {codes[0]}.',
        15:f'The group responsible for the river survey is "{team}".',
        20:f'The approved setting for "{p1}" is {codes[1]}.',
        25:f'The event "{start}" occurred on {d0.isoformat()}.',
        30:f'The most recently reported setting for "{p2}" is {codes[2]}.',
        35:f'The access setting for "{p3}" is now {codes[3]}; this replaces the earlier setting.',
        40:f'The person who raised the archive concern is "{bridge}".',
        45:f'The meeting "{meeting}" took place at this point in the conversation.',
        50:f'The supervisor of "{team}" is "{person}".',
        65:f'The approved setting for "{p1}" is now {codes[4]}; this replaces its earlier setting.',
        75:f'The most recently reported setting for "{p2}" is {codes[5]}; this replaces the previous report.',
        80:f'The badge code assigned to "{bridge}" is {codes[6]}.',
        85:f'The current access setting for "{p3}" is now {codes[7]}; this replaces both previous settings.',
        90:f'The event "{end}" occurred on {(d0+timedelta(days=duration)).isoformat()}.',
        95:f'The locker code assigned to "{person}" is {codes[8]}.',
    }
    episodes=[]
    for turn in range(1,141):
        project=names[(turn+seed)%3]
        material=rng.choice(('brass','oak','nylon','steel','copper','canvas'))
        place=rng.choice(('north depot','west laboratory','harbour office','east workshop','south archive'))
        detail=(f'Operations note {seed}-{turn} for "{project}". '
                f'The {place} received {rng.randrange(3,99)} {material} containers in batch {rng.randrange(10000,99999)}. '
                f'The inspection team checked labels, fasteners and the receiving register. '
                f'Its measurement was {rng.randrange(100,900)} millimetres and its inventory count was {rng.randrange(20,400)}. '
                f'A separate delivery to {rng.choice(("the school","the museum","the station"))} is expected in {rng.randrange(2,14)} days. '
                f'The notes concern equipment handling and contain no change to any access setting, badge code or locker code. '
                f'The supervisor requested a receipt for shipment {rng.randrange(100000,999999)} and a review of {rng.choice(("packaging","routing","storage"))}.')
        user=(plants[turn]+'\n'+detail) if turn in plants else detail
        assistant='Recorded the operations note.'
        episodes.append({'id':key(user+'\n'+assistant),'turn_number':turn,'user_message':user,'assistant_message':assistant})
    def item(kind,query,answer,turns):
        spans=[plants[t] for t in turns]
        label={'answer':answer,'sufficient_sets':[spans] if spans else [],'gold_ids':[episodes[t-1]['id'] for t in turns]}
        return {'id':key(sid+'\n'+kind+'\n'+query),'session_id':sid,'type':kind,'query':query,'probe_turn':141},label
    pairs=[
        item('T1',f'What was the approved setting for "{p1}" before "{meeting}"?',codes[1],[20,45]),
        item('T2',f'What is the latest reported setting for "{p2}"?',codes[5],[75]),
        item('T3',f'What is the current access setting for "{p3}"?',codes[7],[85]),
        item('T4',f'How many days elapsed between "{start}" and "{end}"?',str(duration),[25,90]),
        item('M1','What is the badge code of the person who raised the archive concern?',codes[6],[40,80]),
        item('M2','What is the locker code of the supervisor of the group responsible for the river survey?',codes[8],[15,50,95]),
        item('N1',f'What is the access setting for "{unused}"?',"I don't know.",[]),
    ]
    return {'id':sid,'seed':seed,'episodes':episodes,'probes':[p for p,_ in pairs]}, {p['id']:label for p,label in pairs}

"""Development generator; source production separated from measurement ledger."""
import random,hashlib,json
VALUES=['office','warehouse','studio','depot','workshop','laboratory','annex','hangar']
KINDS=['straight','irrelevant','future','proposal','latest','absent']
def identity(x):return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
def make_session(seed):
 rng=random.Random(seed);slots=set();events={};ledger=[];queries=[];metadata=[]
 names=[f'{s}-{rng.randrange(100,999)}' for s in ['Harbor','Orchard','Meadow','Riverside','Cedar','Summit']]
 def reserve(lo,hi):
  choices=[x for x in range(lo,hi+1) if x not in slots];assert choices
  x=rng.choice(choices);slots.add(x);return x
 for k,(kind,name) in enumerate(zip(KINDS,names)):
  valid=[a for a in range(55,96) if a not in slots and any(x not in slots for x in range(a-3,a)) and any(x not in slots for x in range(a-12,a-4))];assert valid
  anchor=rng.choice(valid);slots.add(anchor);meeting=f'{name} review';target=reserve(anchor-12,anchor-5);near=reserve(anchor-3,anchor-1);early=reserve(1,target-3);later=reserve(anchor+1,105)
  vals=rng.sample(VALUES,3);old,current,new=vals
  facts={early:f'The delivery location for "{name}" is now the {old}. This replaces its previous location.',target:f'The delivery location for "{name}" is now the {current}. This replaces its previous location.',anchor:f'The meeting "{meeting}" took place at this point in the conversation.',later:f'The delivery location for "{name}" is now the {new}. This replaces its previous location.'}
  if kind=='straight':facts[near]=f'The team checked the schedule for "{name}" without changing any instructions.'
  elif kind=='irrelevant':facts[near]=f'The maintenance contact for "{name}" changed today. This says nothing about its delivery location.'
  elif kind=='future':facts[near]=f'The team announced that the delivery location for "{name}" will become the {new} after the meeting "{meeting}". The announced change is not effective yet.'
  elif kind=='proposal':facts[near]=f'A proposal would move the delivery location for "{name}" to the {new}. It has not been accepted; no delivery-location change takes effect.'
  else:facts[near]=f'The project "{name}" had a routine inventory inspection.'
  # Anchor matcher requires a unique meeting-bearing name carrier: future reference must not add a second anchor.
  if kind=='future':facts[near]=f'The team announced that the delivery location for "{name}" will become the {new} next month. It is explicitly not effective anywhere in the current recorded history.'
  if kind=='absent':
   for turn in [early,target,later]:facts[turn]=f'The equipment supplier for "{name}" is the {rng.choice(VALUES)} team. No delivery location is specified in this record.'
  for turn,text in facts.items():events[turn]=(k,text)
  for turn,value in [(early,old),(target,current),(later,new)]:
   if kind!='absent':ledger.append(dict(subject=name,turn=turn,field='delivery location',value=value,effective=True))
  query=(f'What is the latest delivery location for "{name}"?' if kind=='latest' else f'What was the delivery location for "{name}" immediately before "{meeting}"?')
  gold="I don't know" if kind=='absent' else new if kind=='latest' else current
  support=[] if kind=='absent' else [later] if kind=='latest' else [target,anchor]+([near] if kind in ['future','proposal'] else [])
  metadata.append(dict(kind=kind,subject=name,anchor=anchor,target=target,near=near,later=later,gold=gold,support_turns=support,query=query))
 episodes=[]
 for turn in range(1,141):
  if turn in events:k,head=events[turn]
  elif turn<=108:
   k=(turn-1)%6;head=f'The team reviewed delivery records for "{names[k]}". This review made no change to its delivery location.'
  else:k=turn%6;head='A separate gardening club discussed its weekend activities. No project delivery instructions appear in this exchange.'
  note=f'Operations note {rng.randrange(10000,99999)}. The receiving team inspected {rng.randrange(10,100)} containers at the {rng.choice(VALUES)}. Labels and fasteners were checked against the inventory register. The measurement was {rng.randrange(100,900)} millimetres. A supplier receipt was filed under reference {rng.randrange(100000,999999)}. The facilities committee discussed equipment handling, packaging and staffing. These operational observations do not establish or revise any project delivery location. The next routine inspection will review stock counts and maintenance logs. The shift supervisor signed the inspection sheet and requested a separate receipt for the new supplies.'
  e=dict(turn_number=turn,user_message=head+'\n'+note,assistant_message='Recorded the operations note.');e['id']=identity(e);episodes.append(e)
 labels={}
 for meta in metadata:
  q=dict(query=meta['query'],type=meta['kind'],probe_turn=141);q['id']=identity([seed,q]);queries.append(q)
  support=[episodes[t-1] for t in meta['support_turns']]
  labels[q['id']]=dict(answer=meta['gold'],gold_ids=[e['id'] for e in support],sufficient_sets=[[e['user_message'].splitlines()[0] for e in support]] if support else [],rationale=meta)
 return dict(id=f'session-{seed}',episodes=episodes,probes=queries),labels,ledger

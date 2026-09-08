from corpus import make_session as original,identity
import random,re

def make_session(seed):
 s,labels,ledger=original(seed);rng=random.Random(seed+1000000);idmap={}
 for e in s['episodes']:
  old=e['id'];head,note=e['user_message'].split('\n',1)
  extra=[re.sub(r'\d+',lambda m:str(rng.randrange(10**(len(m[0])-1),10**len(m[0]))),note) for _ in range(2)]
  e['user_message']='\n'.join([head,note,*extra]);e['id']=identity({k:v for k,v in e.items() if k!='id'});idmap[old]=e['id']
 for label in labels.values():label['gold_ids']=[idmap[x] for x in label['gold_ids']]
 return s,labels,ledger

"""Value-opacity repair; corpus-authoring only, never imported by retrieval."""
import json
import re
from corpus import key
from corpus_dense import make_session as dense_session

def make_session(seed):
    session,labels=dense_session(seed)
    text=json.dumps({'session':session,'labels':labels})
    old_codes=sorted(set(re.findall(r'RV-\d+-\d+',text)))
    replacements={code:'VX-'+key('study-D-opaque-values-v1:'+code)[:12].upper() for code in old_codes}
    assert len(set(replacements.values()))==len(replacements)
    for old,new in replacements.items():
        text=text.replace(old,new)
    obj=json.loads(text)
    session,labels=obj['session'],obj['labels']
    remap={}
    for e in session['episodes']:
        old=e['id']
        e['id']=key(e['user_message']+'\n'+e['assistant_message'])
        remap[old]=e['id']
    for label in labels.values():
        label['gold_ids']=[remap[x] for x in label['gold_ids']]
    assert not re.search(r'RV-\d+-\d+',json.dumps(session))
    return session,labels

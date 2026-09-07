"""Posthoc textual input/output correspondence, not a retrieval selector."""
from preflight import P,I,read,sha
import json

audit=read(P/'chronology_artifacts/misses_audit.json')
histories={h['id']:h for h in read(I/'sources.json')}
contexts={r['history']:r for r in read(P/'chronology_artifacts/contexts.json')}
rows=[]
for r in audit['rows']:
    selected=set(contexts[r['history']]['selected_ids'])
    candidates=[e for e in histories[r['history']]['episodes'] if e['id'] in selected and e['turn_number']<r['anchor'] and e['user_message'].startswith('The delivery location for ')]
    last=max(candidates,key=lambda e:e['turn_number'])
    statement=last['user_message'].split('\n')[0]
    assert f"is now the {r['reader_answer']}." in statement
    rows.append(dict(history=r['history'],source_id=last['id'],turn=last['turn_number'],statement=statement,reader_answer=r['reader_answer'],match=True))
path=P/'chronology_artifacts/delivered_state_matches.json';assert not path.exists()
path.write_text(json.dumps(dict(scope='Observable text match only; template-specific measurement, not causal introspection',source_sha256=sha(I/'sources.json'),rows=rows),indent=2)+'\n',encoding='utf-8')
print('All four chronological answers match last delivered effective-update text')

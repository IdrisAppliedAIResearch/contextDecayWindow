"""Blind mechanical scoring only; no aggregate or automatic prose judgment."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
P = Path(__file__).resolve().parent/'artifacts/amendment003/reader'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def committed(path):
    blob = subprocess.check_output(['git','show','HEAD:'+path.relative_to(ROOT).as_posix()], cwd=ROOT)
    assert blob.replace(b'\r\n',b'\n') == path.read_bytes().replace(b'\r\n',b'\n')


def save(name, value):
    assert not (P/name).exists()
    (P/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')


def score(text, reference):
    value = text.strip().replace('’',"'").strip(' \"\'`.!?').casefold()
    if value.startswith('the '):
        value = value[4:]
    if value in ['office','warehouse','studio','depot','workshop','laboratory','annex','hangar',"i don't know"]:
        return int(value==reference.casefold()), 'Frozen canonical value compared exactly.'
    if not value:
        return 0, 'NO_ANSWER'
    return None, 'NEEDS_ADJUDICATION: outside frozen mechanical grammar.'


def main():
    committed(P/'complete.json')
    complete = json.loads((P/'complete.json').read_text())
    assert complete['status']=='PASS' and complete['calls']==43
    assert sha(P/'responses.jsonl')==complete['responses_sha256']
    rows=[json.loads(line) for line in (P/'responses.jsonl').read_text().splitlines()][3:]
    assert len(rows)==40
    blind,mapping=[],[]
    for row in rows:
        q=row['row'];answer=row['response']['content']
        bid=hashlib.sha256((q['id']+q['arm']).encode()).hexdigest()
        blind.append(dict(blind_id=bid,query=q['query'],reference=q['reference'],response=answer))
        mapping.append(dict(blind_id=bid,session=q['session'],history=q['history'],type=q['type'],arm=q['arm']))
    blind.sort(key=lambda r:r['blind_id'])
    assert score('', 'office')[0]==0 and score('Not office','office')[0] is None
    scores=[]
    for row in blind:
        value,rationale=score(row['response'],row['reference'])
        scores.append(dict(blind_id=row['blind_id'],score=value,rationale=rationale))
    pending_ids={r['blind_id'] for r in scores if r['score'] is None}
    pending=[r for r in blind if r['blind_id'] in pending_ids]
    save('blind_surface.json',blind);save('mapping.json',mapping);save('scores.json',scores)
    save('pending_adjudication.json',pending)
    save('scoring_gate.json',dict(status='PENDING_ADJUDICATION' if pending else 'PASS',pending=len(pending),
                                count=40,scores_sha256=sha(P/'scores.json')))
    packet=['# Amendment 003 blind review packet','', 'Full returned responses; no arm identities or aggregate.', '']
    for index,row in enumerate(pending,1):
        packet.extend([f'## Item {index}', '', f"Blind ID: {row['blind_id']}", '',
                       f"Question: {row['query']}", '', f"Expected: {row['reference']}", '',
                       '```text',row['response'],'```',''])
    assert not (P/'REVIEW_PACKET.md').exists()
    (P/'REVIEW_PACKET.md').write_text('\n'.join(packet),encoding='utf-8')
    print(json.dumps(dict(count=40,pending=len(pending))),flush=True)


if __name__=='__main__':
    main()

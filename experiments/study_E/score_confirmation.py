"""Verify complete raw capture, then produce blind logical scores only."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

from score_amendment003 import score
from prepare_confirmation import REGISTRATION

ROOT=Path(__file__).resolve().parents[2]
P=Path(__file__).resolve().parent/'artifacts/confirmation/reader'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def committed(path,binary=False):
    blob=subprocess.check_output(['git','show','HEAD:'+path.relative_to(ROOT).as_posix()],cwd=ROOT)
    actual=path.read_bytes()
    assert blob==actual if binary else blob.replace(b'\r\n',b'\n')==actual.replace(b'\r\n',b'\n')


def save(name,value):
    path=P/name;assert not path.exists(),path
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')


def main():
    committed(P/'complete.json');committed(P/'responses.jsonl.gz',binary=True)
    complete=json.loads((P/'complete.json').read_text())
    assert complete['status']=='PASS' and complete['registration']==REGISTRATION
    assert complete['logical_answers']==3840 and sha(P/'responses.jsonl.gz')==complete['archive_sha256']
    with gzip.open(P/'responses.jsonl.gz','rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==complete['responses_sha256']
    assert sha(P/'logical_schedule.json')==complete['logical_schedule_sha256']
    physical={};all_calls=0
    with gzip.open(P/'responses.jsonl.gz','rt',encoding='utf-8') as stream:
        for line in stream:
            item=json.loads(line);all_calls+=1;row=item['row'];response=item['response']
            assert response['content'].strip() and not response['truncated'] and response['stop_type']=='eos'
            assert '<think>' not in response['content']
            if row['stage']=='measurement':
                assert row['physical_id'] not in physical
                physical[row['physical_id']]=response['content']
    assert all_calls==complete['calls']
    logical=json.loads((P/'logical_schedule.json').read_text());assert len(logical)==3840
    blind=[];mapping=[];scores=[];groups={}
    assert score('', 'office')[0]==0 and score('Not office','office')[0] is None
    for row in logical:
        response=physical[row['physical_id']]
        # Content grouping is for consistent blinded judgment only, never inference aliasing.
        review_key=hashlib.sha256(json.dumps([row['query'],row['reference'],response],ensure_ascii=True).encode()).hexdigest()
        blind.append(dict(blind_id=row['logical_id'],query=row['query'],reference=row['reference'],response=response,review_key=review_key))
        mapping.append(dict(blind_id=row['logical_id'],physical_id=row['physical_id'],question_id=row['question_id'],
                            session=row['session'],history=row['history'],type=row['type'],arm=row['arm'],seed=row['seed']))
        value,rationale=score(response,row['reference'])
        scores.append(dict(blind_id=row['logical_id'],score=value,rationale=rationale,review_key=review_key))
        if value is None:
            if review_key not in groups:
                groups[review_key]=dict(review_key=review_key,query=row['query'],reference=row['reference'],response=response,blind_ids=[])
            groups[review_key]['blind_ids'].append(row['logical_id'])
    blind.sort(key=lambda r:r['blind_id']);scores.sort(key=lambda r:r['blind_id'])
    pending=sorted(groups.values(),key=lambda r:r['review_key'])
    save('blind_surface.json',blind);save('mapping.json',mapping);save('scores.json',scores)
    save('pending_adjudication.json',pending)
    save('scoring_gate.json',dict(status='PENDING_ADJUDICATION' if pending else 'PASS',count=3840,
         pending_logical=sum(r['score'] is None for r in scores),pending_unique=len(pending),
         scores_sha256=sha(P/'scores.json'),all_physical_calls_complete=True))
    print(json.dumps(dict(count=3840,pending_unique=len(pending),pending_logical=sum(r['score'] is None for r in scores))),flush=True)


if __name__=='__main__':main()

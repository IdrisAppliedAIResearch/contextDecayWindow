"""Read-only verification of sealed inputs and completed response archive."""
import gzip
import hashlib
import json
from pathlib import Path

STUDY=Path(__file__).resolve().parent
ROOT=STUDY.parents[1]
OUT=STUDY/'artifacts/confirmation'

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    checks=[]
    for r in json.loads((STUDY/'registration_inputs.json').read_text(encoding='utf-8-sig')):
        assert sha(ROOT/r['path'])==r['sha256'],r['path']
        checks.append(r['path'])
    for gate_name in ('prompt_gate.json','instrument_gate.json'):
        gate=json.loads((OUT/gate_name).read_text())
        assert gate['status']=='PASS'
        for name,expected in gate['files'].items():
            assert sha(OUT/name)==expected,name
            checks.append(name)
    reader=json.loads((OUT/'reader_gate.json').read_text())
    archive=json.loads((OUT/'response_archive.json').read_text())
    assert sha(OUT/'responses.jsonl.gz')==archive['archive_sha256']
    raw=gzip.decompress((OUT/'responses.jsonl.gz').read_bytes())
    assert hashlib.sha256(raw).hexdigest()==archive['raw_sha256']
    assert len(raw)==archive['raw_bytes']
    if reader['status']=='PASS':
        assert hashlib.sha256(raw).hexdigest()==reader['responses_sha256']
        assert sha(OUT/'blind_surface.json')==reader['blind_surface_sha256']
    assert len({json.loads(line)['call_key'] for line in raw.splitlines()})==len(raw.splitlines())
    if (OUT/'scoring_gate.json').exists():
        scoring=json.loads((OUT/'scoring_gate.json').read_text())
        assert sha(OUT/'blind_scores.json')==scoring['blind_scores_sha256']
    if (OUT/'resolved_scoring_gate.json').exists():
        resolved=json.loads((OUT/'resolved_scoring_gate.json').read_text())
        assert resolved['status']=='PASS'
        assert sha(OUT/'resolved_scores.json')==resolved['blind_scores_sha256']
        assert sha(OUT/'agent_adjudication.json')==resolved['adjudication_sha256']
        original={r['blind_id']:r for r in json.loads((OUT/'blind_scores.json').read_text())}
        completed=json.loads((OUT/'resolved_scores.json').read_text())
        judgments={r['blind_id']:r for r in json.loads((OUT/'agent_adjudication.json').read_text())}
        assert len(completed)==len(original)==3675
        assert set(judgments)=={k for k,v in original.items() if v['score'] is None}
        for r in completed:
            old=original[r['blind_id']]
            assert r['score'] in (0,1)
            if old['score'] is not None: assert r==old
            else: assert r['score']==judgments[r['blind_id']]['score']
    print(json.dumps({'status':'PASS','artifact_checks':len(checks),'physical_response_rows':len(raw.splitlines()),'reader_gate':reader['status'],'new_model_calls':0}))

if __name__=='__main__':
    main()

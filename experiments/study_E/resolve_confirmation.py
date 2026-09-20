"""Merge committed blind judgments; never open confirmation arm mapping."""
import json
from pathlib import Path
from score_confirmation import P,committed,save,sha


def main():
    committed(P/'scores.json');committed(P/'pending_adjudication.json')
    scores=json.loads((P/'scores.json').read_text())
    pending=json.loads((P/'pending_adjudication.json').read_text())
    expected={r['review_key']:r for r in pending};judgments={}
    folder=P/'adjudications'
    for path in sorted(folder.glob('*.json')) if folder.exists() else []:
        committed(path)
        for row in json.loads(path.read_text(encoding='utf-8')):
            key=row['review_key']
            assert key in expected and key not in judgments
            assert row['score'] in (0,1) and row['rationale'].strip()
            assert row.get('evidence','') in expected[key]['response']
            assert row['score']==0 or row.get('evidence','').strip()
            assert isinstance(row.get('corrected_wrong_opening',False),bool)
            judgments[key]=row
    assert set(judgments)==set(expected),'Unresolved blind judgments; no aggregate permitted.'
    resolved=[]
    for row in scores:
        if row['score'] is None:
            judge=judgments[row['review_key']]
            resolved.append(dict(row,score=judge['score'],rationale=judge['rationale'],evidence=judge.get('evidence',''),
                corrected_wrong_opening=judge.get('corrected_wrong_opening',False),reviewer='registered single agent; no human audit'))
        else:
            resolved.append(dict(row,corrected_wrong_opening=False,reviewer='frozen mechanical grammar'))
    assert len(resolved)==3840 and all(r['score'] in (0,1) for r in resolved)
    save('scores_resolved.json',resolved)
    save('scoring_gate_resolved.json',dict(status='PASS',pending=0,count=3840,
        agent_unique_judgments=len(judgments),agent_logical_judgments=sum(r['score'] is None for r in scores),
        scores_sha256=sha(P/'scores_resolved.json'),measurement='registered single-agent exceptions; no human audit'))
    print('Resolved blind scores written; commit before analysis.',flush=True)


if __name__=='__main__':main()

"""Score final content before exposing thinking diagnostics."""
import sys
from pathlib import Path
import run

sys.path.insert(0, str(run.ROOT/'experiments/study_E'))
from score_amendment003 import score


def main():
    run.committed(run.O/'complete.json')
    complete=run.read(run.O/'complete.json')
    assert complete['status']=='PASS' and complete['count']==12
    rows=[]
    for row in run.read(run.O/'selection.json'):
        path=run.O/(row['case']+'.json')
        run.committed(path)
        assert run.sha(path)==complete['hashes'][row['case']]
        answer=run.final(run.read(path)['response'])
        value,rationale=score(answer,row['reference'])
        rows.append(dict(case=row['case'],query=row['query'],reference=row['reference'],
                         final=answer,score=value,rationale=rationale))
    run.save('final_scores_mechanical.json',rows)
    print(__import__('json').dumps(rows,ensure_ascii=False))


if __name__=='__main__':
    main()

"""Additive final-verdict repair; all raw judgments retained."""
import json,re,sys
import probe as q
p=q.p;OUT=q.OUT
def parse(text):
    matches=list(re.finditer(r'(?im)^VERDICT:\s*(CORRECT|INCORRECT)\s*$',text))
    assert matches,'NO_FINAL_VERDICT'
    last=matches[-1]
    reason=re.search(r'(?m)^REASON:\s*(\S.*)$',text[last.end():])
    assert reason,'NO_FINAL_REASON'
    return dict(verdict=last.group(1).upper()=='CORRECT',reason=reason.group(1),all_verdicts=[m.group(1).upper() for m in matches])
def run():
    p.committed(__file__);p.committed(q.P/'AMENDMENT_001_FINAL_VERDICT.md');p.committed(OUT/'blind_votes.json')
    for text,expected in [('VERDICT: CORRECT\nREASON: same',True),('VERDICT: INCORRECT\nREASON: wrong',False),('VERDICT: INCORRECT\nREASON: wrong\nVERDICT: CORRECT\nREASON: same',True),('VERDICT: CORRECT\nREASON: same\nVERDICT: INCORRECT\nREASON: wrong',False)]:assert parse(text)['verdict']==expected
    for text in ['', 'VERDICT: CORRECT']:
        try:parse(text)
        except AssertionError:pass
        else:raise AssertionError('invalid fixture passed')
    complete=p.read(OUT/'judge_complete.json');rs=[]
    for row in p.read(OUT/'blind_votes.json'):
        votes=[]
        for seed in [9100,9101,9102]:
            name=row['blind_id']+'_'+str(seed)+'.json';path=OUT/'judges'/name
            assert p.sha(path)==complete['hashes'][name]
            votes.append(parse(q.r.final(p.read(path)['response'])))
        rs.append(dict(row,votes=votes,original_score=row['score'],score=int(sum(x['verdict'] for x in votes)>=2),disagreement=len({x['verdict'] for x in votes})>1))
    p.save(OUT/'corrected_votes.json',rs)
def summary():
    p.committed(OUT/'corrected_votes.json')
    votes={x['key']:x for x in p.read(OUT/'corrected_votes.json')}
    old=p.read(OUT/'results.json');rs=[dict(x,**{k:votes[x['key']][k] for k in ['score','votes','disagreement','original_score']}) for x in old['rows']]
    totals={g:dict(n=len(xs),correct=sum(x['score'] for x in xs),disagreements=sum(x['disagreement'] for x in xs),evidence_complete=sum(x['evidence']=='complete' for x in xs)) for g in ['broad20','temporal10'] for xs in [[x for x in rs if x['group']==g]]}
    p.save(OUT/'corrected_results.json',dict(summary=totals,rows=rs))
    print(json.dumps(totals))
if __name__=='__main__':{'run':run,'summary':summary}[sys.argv[1]]()

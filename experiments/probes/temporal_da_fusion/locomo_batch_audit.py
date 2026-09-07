"""Audit persisted real-prompt timing and actual concurrent slot overlap."""
import json,re,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent; O=P/'locomo_batch_artifacts'
subprocess.run(['git','ls-files','--error-unmatch',str(O/'complete.json')],check=True)
arms=[json.loads((O/f'arm_{n}.json').read_text()) for n in [1,9]]
summary=[]
for a in arms:
    n=a['slots'];active=set();peak=0
    for line in (O/f'server_{n}.err').read_text().splitlines():
        m=re.search(r'id\s+(\d+) \| task \d+ \| processing task',line)
        if m:active.add(int(m[1]));peak=max(peak,len(active))
        m=re.search(r'id\s+(\d+) \| task \d+ \| stop processing',line)
        if m:active.discard(int(m[1]))
    assert peak==n and not active
    rs=[x['response'] for x in a['answers']]
    assert all(r['timings']['cache_n']==0 and not r['truncated'] and r['stop_type']=='eos' for r in rs)
    summary.append(dict(slots=n,seconds=a['seconds'],peak_active=peak,input_tokens=sum(r['tokens_evaluated'] for r in rs),output_tokens=sum(r['tokens_predicted'] for r in rs),min_free_mib=min(s['free'] for s in a['samples']),individual_seconds=[x['seconds'] for x in a['answers']]))
assert [x['key'] for x in arms[0]['answers']]==[x['key'] for x in arms[1]['answers']]
assert [x['response']['prompt'] for x in arms[0]['answers']]==[x['response']['prompt'] for x in arms[1]['answers']]
out=dict(status='PASS',arms=summary,speedup=arms[0]['seconds']/arms[1]['seconds'],identical_answers=sum(x['response']['content']==y['response']['content'] for x,y in zip(arms[0]['answers'],arms[1]['answers'])),input_lengths=arms[0]['lengths'])
with (O/'audit.json').open('x') as f:json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))

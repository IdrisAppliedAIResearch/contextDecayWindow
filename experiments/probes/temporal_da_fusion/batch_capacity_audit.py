"""Audit committed capacity records and concurrent slot lifetimes."""
import hashlib,json,re,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
O=P/'batch_capacity_artifacts_retry'
def main():
    subprocess.run(['git','ls-files','--error-unmatch',str(O/'complete.json')],check=True,stdout=subprocess.DEVNULL)
    rows=[]
    for f in sorted(O.glob('configuration_*.json'),key=lambda p:int(p.stem.split('_')[-1])):
        d=json.loads(f.read_text());n=d['slots'];log=(O/f'server_{n}.err').read_text()
        assert 'offloaded 66/66 layers to GPU' in log
        assert f'n_ctx_slot = 32768' in log
        active=set();peak=0
        for line in log.splitlines():
            m=re.search(r'id\s+(\d+) \| task \d+ \| processing task',line)
            if m:active.add(int(m[1]));peak=max(peak,len(active))
            m=re.search(r'id\s+(\d+) \| task \d+ \| stop processing',line)
            if m:active.discard(int(m[1]))
        row=dict(slots=n,status=d['status'],idle_free_mib=d['idle_gpu']['free'],peak_active=peak)
        if d['status']=='STRESS_PASS':
            assert peak==n and not active
            assert len(d['waves'])==2
            for w in d['waves']:
                assert {r['id_slot'] for r in w['responses']}==set(range(n))
                assert all(r['timings']['cache_n']==0 and r['tokens_predicted']==64 and not r['truncated'] for r in w['responses'])
            hashes=[[hashlib.sha256(r['prompt'].encode()).hexdigest() for r in w['responses']] for w in d['waves']]
            assert hashes[0]==hashes[1] and len(set(hashes[0]))==n
            row['prompt_sha256']=hashes[0]
            row.update(min_free_mib=min(s['free'] for w in d['waves'] for s in w['samples']),wave_seconds=[w['seconds'] for w in d['waves']],input_tokens=sorted(set(r['tokens_evaluated'] for w in d['waves'] for r in w['responses'])))
            row['responses_per_second']=2*n/sum(row['wave_seconds'])
        row['raw_sha256']=hashlib.sha256(f.read_bytes()).hexdigest();rows.append(row)
    with (P/'batch_capacity_audit.json').open('x') as f:json.dump(dict(status='PASS',rows=rows),f,indent=2)
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()

"""Synthetic reachability checks and dependency pins before confirmation lock."""
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
P=Path(__file__).resolve().parent


def classify(deltas):
    assert deltas.shape==(32,6)
    if np.any(deltas[:,4]):
        return 'INSTRUMENT_FAILURE', None, None
    primary=deltas[:,:4].mean(axis=1)
    mean=float(primary.mean())
    rng=np.random.default_rng(95001)
    simulated=(rng.choice([-1.,1.],size=(100000,32))*primary).mean(axis=1)
    p=float((np.count_nonzero(simulated>=mean-1e-12)+1)/100001)
    if mean<=-.025 or np.any(deltas[:,1:4].mean(axis=0)<-.05) or deltas[:,5].mean()<-.05:
        return 'REGRESSES',mean,p
    if mean>=.10 and p<=.05:
        return 'D1_WORKS',mean,p
    if mean>=.025 and p<=.10:
        return 'D2_CARRIES_SIGNAL',mean,p
    return 'NO_DEMONSTRATED_BENEFIT',mean,p


def main():
    fixtures=[]
    for name,n,expected in [('positive',7,'D1_WORKS'),('signal',4,'D2_CARRIES_SIGNAL'),('tie',0,'NO_DEMONSTRATED_BENEFIT')]:
        delta=np.zeros((32,6));delta[:n,:4]=.5
        got,mean,p=classify(delta);assert got==expected
        fixtures.append(dict(name=name,expected=expected,observed=got,mean=mean,p=p))
    for name,column in [('primary_harm',None),('irrelevant_harm',1),('future_harm',2),('proposal_harm',3),('absence_harm',5),('latest_violation',4)]:
        delta=np.zeros((32,6))
        if column is None:delta[:,:4]=-.2
        elif column==4:delta[0,4]=.2
        else:
            delta[:,:4]=.4
            delta[:,column]=-.2
        got,mean,p=classify(delta)
        expected='INSTRUMENT_FAILURE' if column==4 else 'REGRESSES'
        assert got==expected
        fixtures.append(dict(name=name,expected=expected,observed=got,mean=mean,p=p))
    pins={}
    for name in ['corpus.py','prepare_amendment003.py','mechanism.py','prelock_checks.py']:
        pins[name]=hashlib.sha256((P/name).read_bytes()).hexdigest()
    out=dict(status='PASS',fixtures=fixtures,pins=pins,
             control_replay='artifacts/part1/replay.json:224/224 exact,224 repeat',
             empirical_population='artifacts/amendment003/development/readiness_gate_exact.json: mixed C0 support and active guards',
             completed_reader='artifacts/amendment003/reader/complete.json:43 EOS calls, maximum prompt12047 tokens',
             scoring_calibration='amendments/AMENDMENT_003_RATER_CALIBRATION.json',
             unit='32 groups; five seeds averaged within question and four primary conditions within group')
    target=P/'artifacts/confirmation_prelock.json';assert not target.exists()
    target.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out,indent=2))


if __name__=='__main__':main()

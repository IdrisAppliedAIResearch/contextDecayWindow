"""Registered group-level endpoint; opens mapping only after committed scores."""
from fractions import Fraction
import json
from pathlib import Path
import numpy as np
from score_confirmation import P,committed,save,sha
from prepare_confirmation import REGISTRATION

ARMS=['C0','C1','ORACLE','NULL']
KINDS=['straight','irrelevant','future','proposal','latest','absent']


def statistics(array):
    assert array.shape==(4,32,6,5) and np.all((array==0)|(array==1))
    counts=array.sum(axis=3)
    differences=counts[1]-counts[0]
    assert np.array_equal(array[0,:,4,:],array[1,:,4,:]),'Latest identity violation'
    units=differences[:,:4].sum(axis=1)/20
    difference_count=int(differences[:,:4].sum())
    exact_mean=Fraction(difference_count,640)
    mean=float(exact_mean)
    rng=np.random.default_rng(95001)
    simulations=(rng.choice([-1.,1.],size=(100000,32))*units).mean(axis=1)
    p=float((np.count_nonzero(simulations>=mean-1e-12)+1)/100001)
    rng=np.random.default_rng(95002)
    bootstrap=units[rng.integers(0,32,size=(10000,32))].mean(axis=1)
    ci=np.quantile(bootstrap,[.025,.975],method='linear').tolist()
    challenge_counts=differences[:,1:4].sum(axis=0)
    absence_count=int(differences[:,5].sum())
    if exact_mean<=Fraction(-25,1000) or any(Fraction(int(n),160)<Fraction(-5,100) for n in challenge_counts) or Fraction(absence_count,160)<Fraction(-5,100):
        verdict='REGRESSES'
    elif exact_mean>=Fraction(10,100) and p<=.05:verdict='D1_WORKS'
    elif exact_mean>=Fraction(25,1000) and p<=.10:verdict='D2_CARRIES_SIGNAL'
    else:verdict='NO_DEMONSTRATED_BENEFIT'
    return dict(disposition=verdict,primary_delta=mean,delta_correct=difference_count,
        ci95=ci,p_improvement=p,p_reverse=float((np.count_nonzero(simulations<=mean+1e-12)+1)/100001),group_differences=units.tolist(),
        challenge_delta_counts=challenge_counts.tolist(),absence_delta_count=absence_count)


def main():
    for name in ['complete.json','scores_resolved.json','scoring_gate_resolved.json','mapping.json']:committed(P/name)
    gate=json.loads((P/'scoring_gate_resolved.json').read_text())
    assert gate['status']=='PASS' and gate['pending']==0 and gate['count']==3840
    assert sha(P/'scores_resolved.json')==gate['scores_sha256']
    completion=json.loads((P/'complete.json').read_text());assert completion['status']=='PASS' and completion['registration']==REGISTRATION
    assert sha(P/'logical_schedule.json')==completion['logical_schedule_sha256']
    scores={r['blind_id']:r for r in json.loads((P/'scores_resolved.json').read_text())}
    mapping=json.loads((P/'mapping.json').read_text())
    assert len(mapping)==len(scores)==3840
    groups=[f'session-{seed}' for seed in range(94001,94033)]
    array=np.full((4,32,6,5),-1,dtype=int)
    for row in mapping:
        key=(ARMS.index(row['arm']),groups.index(row['session']),KINDS.index(row['type']),row['seed']-5005)
        assert 0<=key[3]<5 and array[key]==-1
        array[key]=scores[row['blind_id']]['score']
    result=statistics(array)
    result.update(registration=REGISTRATION,status='COMPLETE',unit='32 groups; five seeds within question, four primary conditions',
        primary={arm:dict(correct=int(array[i,:,:4,:].sum()),n=640) for i,arm in enumerate(ARMS)},
        by_type={kind:{arm:dict(correct=int(array[i,:,k,:].sum()),n=160) for i,arm in enumerate(ARMS)} for k,kind in enumerate(KINDS)},
        logical_answers=3840,physical_calls=completion.get('actual_calls',completion['calls']),
        selected_archive_records=completion['calls'],scoring=gate)
    for arm_index,arm in enumerate(ARMS):
        rows=[r for r in mapping if r['arm']==arm]
        result.setdefault('corrected_wrong_openings',{})[arm]=sum(scores[r['blind_id']]['corrected_wrong_opening'] for r in rows)
    # Mechanism traces are opened only here, after all four arms' score commit checks.
    inputs=P.parent/'development_inputs'
    traces={r['history']:r for r in json.loads((inputs/'traces_sealed.json').read_text())}
    cross={arm:{f'{e}_{c}':0 for e in ['complete','incomplete'] for c in ['correct','wrong']} for arm in ['C0','C1']}
    for row in mapping:
        if row['arm'] not in cross or row['type'] not in KINDS[:4]:continue
        evidence=traces[row['history']]['evidence'][row['arm']]
        key=('complete' if evidence else 'incomplete')+'_'+('correct' if scores[row['blind_id']]['score'] else 'wrong')
        cross[row['arm']][key]+=1
    result['primary_exact_evidence_by_correctness']=cross
    result['paired_primary_logical']=dict(gains=int(np.count_nonzero(array[1,:,:4,:]>array[0,:,:4,:])),
        losses=int(np.count_nonzero(array[1,:,:4,:]<array[0,:,:4,:])),ties=int(np.count_nonzero(array[1,:,:4,:]==array[0,:,:4,:])))
    save('result.json',result)
    print(json.dumps({k:result[k] for k in ['disposition','primary','primary_delta','ci95','p_improvement']}),flush=True)


if __name__=='__main__':main()

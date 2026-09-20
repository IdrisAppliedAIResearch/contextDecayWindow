"""Registered session-level analysis; no retrieval or scoring imports."""
import numpy as np

def summarize(d):
    d=np.asarray(d,dtype=float)
    assert d.shape==(32,)
    mean=float(d.mean())
    rng=np.random.default_rng(93001)
    ge=0
    for _ in range(20):
        signs=rng.integers(0,2,size=(5000,32),dtype=np.int8)*2-1
        ge+=int(np.count_nonzero((signs*d).mean(axis=1)>=mean-1e-12))
    boot=np.random.default_rng(93002).choice(d,size=(10000,32),replace=True).mean(axis=1)
    return {'difference':mean,'one_sided_p':(ge+1)/100001,'ci95':np.quantile(boot,[.025,.975]).tolist(),'sessions':32}

def disposition(primary,delivery,other,absence):
    if primary['difference']<=-.025 or other<-.05 or absence<-.05:
        return 'REGRESSES'
    if delivery>=0 and primary['difference']>=.10 and primary['one_sided_p']<=.05:
        return 'D1_WORKS'
    if delivery>=0 and primary['difference']>=.025 and primary['one_sided_p']<=.10:
        return 'D2_CARRIES_SIGNAL'
    return 'NO_DEMONSTRATED_BENEFIT'

def reachability():
    cases={'works':[.5]*7+[0.]*25,'signal':[.5]*4+[0.]*28,'negative':[-.5]*7+[0.]*25,'ties':[0.]*32}
    rows={name:summarize(d) for name,d in cases.items()}
    for r in rows.values():
        r['disposition']=disposition(r,0,0,0)
    assert rows['works']['disposition']=='D1_WORKS'
    assert rows['signal']['disposition']=='D2_CARRIES_SIGNAL'
    assert rows['negative']['disposition']=='REGRESSES'
    assert rows['ties']['disposition']=='NO_DEMONSTRATED_BENEFIT'
    return rows

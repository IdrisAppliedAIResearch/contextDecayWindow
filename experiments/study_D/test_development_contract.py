"""Meaningful development invariant checks from the registered Part 1 contracts."""
import ast
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT.parent/'contextDecayWindow-study-D-control/episodic/src'),str(Path(__file__).parent)]
from temporal import build,temporal_order
from corpus_opaque import make_session

def episode(turn,text):
    return {'id':str(turn),'turn_number':turn,'user_message':text,'assistant_message':'Recorded.','embedding':np.ones(1024,dtype=np.float32)}

def test_bounds_and_anchor_admission():
    es=[episode(1,'Setting for "Oak" is AA.'),episode(2,'The meeting "Review" occurs.'),episode(3,'Setting for "Oak" is BB.')]
    rank=SimpleNamespace(order=(2,0,1))
    assert temporal_order(es,'What for "Oak" before "Review"?',rank)[0]==[1,0]
    assert temporal_order(es,'What for "Oak" after "Review"?',rank)[0]==[1,2]

@pytest.mark.parametrize('query',['An unrelated question','What for "Missing" before "Review"?','What for "Oak" before and after "Review"?','What for "Oak" before "Missing"?'])
def test_exact_fallback(query):
    es=[episode(1,'Setting for "Oak" is AA.'),episode(2,'The meeting "Review" occurs.')]
    a,b,trace=build(es,query,np.ones(1024,dtype=np.float32))
    assert a==b and trace['fallback']

def test_duplicate_anchor_falls_back():
    es=[episode(1,'Setting for "Oak" is AA.'),episode(2,'The meeting "Review" occurs.'),episode(3,'Another meeting "Review" occurs.')]
    assert temporal_order(es,'What for "Oak" before "Review"?',SimpleNamespace(order=(0,1,2)))[0]==[]

def test_duration_retains_both_endpoints():
    es=[episode(1,'The event "Open" was on 2025-01-01.'),episode(2,'The event "Close" was on 2025-01-05.')]
    assert temporal_order(es,'How many days elapsed between "Open" and "Close"?',SimpleNamespace(order=(1,0)))[0]==[0,1]

def test_source_ids_and_opaque_answers():
    s,labels=make_session(91001)
    assert len({e['id'] for e in s['episodes']})==140
    for p in s['probes']:
        label=labels[p['id']]
        assert set(label['gold_ids']) <= {e['id'] for e in s['episodes']}
        for group in label['sufficient_sets']:
            assert all(any(span in e['user_message'] for e in s['episodes']) for span in group)
        if p['type'] in ('T1','T2'):
            assert label['answer'].startswith('VX-') and '91001' not in label['answer']

def test_measurement_not_imported_by_mechanism():
    tree=ast.parse(Path(__file__).with_name('temporal.py').read_text())
    def violation(tree):
        return any(isinstance(n,ast.ImportFrom) and (n.module or '').startswith(('corpus','develop','reader_ablation')) for n in ast.walk(tree)) or any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='open' for n in ast.walk(tree))
    assert not violation(tree)
    assert violation(ast.parse('from corpus import make_session'))

def test_latest_source_changes_continuity_without_feedback():
    es=[episode(i,f'Operational fact {i}.') for i in range(1,141)]
    q=np.ones(1024,dtype=np.float32)
    a,_,_=build(es,'Unrelated',q)
    b,_,_=build(es+[episode(141,'New operational fact.')],'Unrelated',q)
    assert a!=b
    assert build(es,'Unrelated',q)[0]==a

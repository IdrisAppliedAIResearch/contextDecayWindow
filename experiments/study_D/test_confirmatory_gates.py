"""Pre-inference tests for fixed decision and scoring gates."""
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).parent))
from score_blind import score
from statistics_locked import reachability,disposition

def row(response,reference='VX-123456789ABC',kind='T1',complete=True):
    return {'response':response,'reference':reference,'type':kind,'complete':complete}

def test_no_answer_never_scores():
    assert score(row('<think>VX-123456789ABC</think>',complete=False))['score']==0
    assert score(row('',"I don't know.",'N1'))['score']==0

def test_no_substring_or_negation_credit():
    for response in ['Not VX-123456789ABC','VX-123456789ABC or VX-ABC123ABC123','The code might be VX-123456789ABC']:
        assert score(row(response))['score'] is None

def test_canonical_values_and_wrong_values():
    assert score(row('"VX-123456789ABC".'))['score']==1
    assert score(row('VX-ABC123ABC123'))['score']==0
    assert score(row('5 days.','5','T4'))['score']==1
    assert score(row('6 days.','5','T4'))['score']==0
    assert score(row("I don’t know.","I don't know.",'N1'))['score']==1
    assert score(row("I don't know."))['score']==0

def test_numerical_dispositions_are_reachable():
    outcomes=reachability()
    assert outcomes['works']['disposition']=='D1_WORKS'
    assert outcomes['signal']['disposition']=='D2_CARRIES_SIGNAL'
    assert outcomes['negative']['disposition']=='REGRESSES'
    assert outcomes['ties']['one_sided_p']==1
    assert disposition(outcomes['works'],0,0,-.06)=='REGRESSES'

def test_inference_cannot_start_without_committed_gate(monkeypatch,tmp_path):
    import confirmatory
    monkeypatch.setattr(confirmatory,'OUT',tmp_path)
    with pytest.raises(FileNotFoundError):
        confirmatory.validate_gate()

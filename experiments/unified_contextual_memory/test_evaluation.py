import pytest
from evaluation import verdict, gate, paired, disposition
from transport import Server, final


def test_final_verdict_both_directions():
    for first, last, expected in (("CORRECT","INCORRECT",False),("INCORRECT","CORRECT",True)):
        text = f"VERDICT: {first}\nREASON: initial\nVERDICT: {last}\nREASON: corrected"
        assert verdict(text) == (expected, "corrected")
    with pytest.raises(ValueError):
        verdict("VERDICT: CORRECT\nREASON: initial\nVERDICT: INCORRECT")


def test_missing_gate_precedes_generation(tmp_path):
    with pytest.raises(ValueError, match="generation forbidden"):
        gate(tmp_path)
    server = object.__new__(Server)
    server.allow_generation = False
    with pytest.raises(PermissionError):
        server.post("completion", {})


def test_bad_outputs_fail():
    for response in ({"truncated":True}, {"stop_type":"limit"}, {"stop_type":"eos","content":"<think>x</think>45"}):
        with pytest.raises(ValueError):
            final(response)


def test_disposition_reachable_in_both_directions():
    rows = [dict(conversation=str(i//10),C0=False,C1=True) for i in range(100)]
    win = paired(rows)
    assert disposition(win,{"test":win},True)=="WORKS_ON_EXPOSED_LOCOMO"
    loss = paired([dict(r,C0=True,C1=False) for r in rows])
    assert disposition(loss,{"test":loss},True)=="NO_QUALIFYING_GAIN"
    weak = dict(win,difference=.015,ci95=[-.01,.03])
    assert disposition(weak,{"test":weak},True)=="WEAK_SIGNAL_ON_EXPOSED_LOCOMO"
    assert disposition(win,{"test":win},False)=="NO_QUALIFYING_GAIN"

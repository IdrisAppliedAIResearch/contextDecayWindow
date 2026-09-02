import hashlib

from analysis.da052_contract import RetainedSetMachine


def frame(text: str) -> dict[str, object]:
    return {"kind": "FRAME", "block": text, "cost": len(text),
            "block_sha256": hashlib.sha256(text.encode()).hexdigest()}


def test_retained_set_is_append_only_and_bounded() -> None:
    machine = RetainedSetMachine()
    for value in ("a", "b", "c", "d", "e"):
        machine.next(frame(value))
        assert machine.keep()
    machine.next(frame("f"))
    assert not machine.keep()
    assert machine.retained == ["a", "b", "c", "d", "e"]


def test_duplicate_and_empty_keep_reject() -> None:
    machine = RetainedSetMachine()
    assert not machine.keep()
    machine.next(frame("a"))
    assert machine.keep()
    machine.next(frame("a"))
    assert not machine.keep()
    assert machine.retained == ["a"]

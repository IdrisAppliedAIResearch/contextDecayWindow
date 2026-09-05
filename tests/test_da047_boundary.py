import hashlib

from analysis.da047_boundary import ProtectedBoundaryMachine


def frame(text: str) -> dict[str, object]:
    return {"kind": "FRAME", "block": text, "cost": len(text),
            "block_sha256": hashlib.sha256(text.encode()).hexdigest()}


def test_substitution_preserves_retained_and_reduces_boundary_cost() -> None:
    machine = ProtectedBoundaryMachine()
    machine.next(frame("retained"))
    machine.keep()
    machine.next(frame("boundary-long"))
    assert machine.substitute_current(frame("short"))
    assert machine.current == "short"
    assert machine.retained == "retained"


def test_rejected_substitution_is_atomic() -> None:
    machine = ProtectedBoundaryMachine()
    machine.next(frame("short"))
    before = (machine.current, machine.retained, machine.peak_chars)
    assert not machine.substitute_current(frame("longer"))
    assert (machine.current, machine.retained, machine.peak_chars) == before


def test_empty_and_mutated_frames_are_rejected() -> None:
    machine = ProtectedBoundaryMachine()
    assert not machine.substitute_current(frame("x"))
    machine.next(frame("current"))
    bad = frame("new")
    bad["block_sha256"] = "0" * 64
    assert not machine.substitute_current(bad)
    assert machine.current == "current"

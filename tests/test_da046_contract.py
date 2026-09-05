import pytest

from analysis.da046_contract import DA046Error, RegisterMachine


def test_register_machine_retain_and_replace_current() -> None:
    machine = RegisterMachine()
    machine.next({"kind": "FRAME", "block": "first", "cost": 5})
    machine.keep()
    assert machine.current is None
    machine.next({"kind": "FRAME", "block": "second", "cost": 6})
    assert machine.answer() == "first"
    assert machine.peak_chars == 11


def test_keep_rejects_empty_current() -> None:
    with pytest.raises(DA046Error):
        RegisterMachine().keep()

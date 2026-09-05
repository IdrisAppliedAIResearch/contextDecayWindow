from analysis.da036_audit import DA036Error


def test_da036_error_is_runtime_error() -> None:
    assert issubclass(DA036Error, RuntimeError)

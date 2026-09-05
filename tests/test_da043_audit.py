from analysis.da043_audit import DA043Error


def test_da043_error_is_runtime_error() -> None:
    assert issubclass(DA043Error, RuntimeError)

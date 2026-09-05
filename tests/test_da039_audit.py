from analysis.da039_audit import DA039Error


def test_da039_error_is_runtime_error() -> None:
    assert issubclass(DA039Error, RuntimeError)

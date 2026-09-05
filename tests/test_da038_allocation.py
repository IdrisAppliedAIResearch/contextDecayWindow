from analysis.da038_allocation import DA038Error


def test_da038_error_is_runtime_error() -> None:
    assert issubclass(DA038Error, RuntimeError)

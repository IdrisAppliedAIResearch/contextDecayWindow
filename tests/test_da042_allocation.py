from analysis.da042_allocation import DA042Error


def test_da042_error_is_runtime_error() -> None:
    assert issubclass(DA042Error, RuntimeError)

from analysis.da037_allocation import DA037Error


def test_da037_error_is_runtime_error() -> None:
    assert issubclass(DA037Error, RuntimeError)

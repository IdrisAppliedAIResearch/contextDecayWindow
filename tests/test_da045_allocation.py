from analysis.da045_allocation import DA045Error


def test_da045_error_is_runtime_error() -> None:
    assert issubclass(DA045Error, RuntimeError)

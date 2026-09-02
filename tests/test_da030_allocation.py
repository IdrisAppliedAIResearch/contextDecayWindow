from analysis.da030_allocation import DA030Error


def test_da030_error_type_is_specific() -> None:
    assert issubclass(DA030Error, RuntimeError)


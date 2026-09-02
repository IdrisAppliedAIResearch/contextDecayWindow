from analysis.da033_allocation import DA033Error


def test_da033_error_type_is_specific() -> None:
    assert issubclass(DA033Error, RuntimeError)


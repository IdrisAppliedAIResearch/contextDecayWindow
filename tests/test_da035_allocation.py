from analysis.da035_allocation import DA035Error


def test_da035_error_type_is_specific() -> None:
    assert issubclass(DA035Error, RuntimeError)


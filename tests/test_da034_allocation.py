from analysis.da034_allocation import DA034Error


def test_da034_error_type_is_specific() -> None:
    assert issubclass(DA034Error, RuntimeError)


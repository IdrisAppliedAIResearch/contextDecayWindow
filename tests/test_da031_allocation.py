from analysis.da031_allocation import DA031Error


def test_da031_error_type_is_specific() -> None:
    assert issubclass(DA031Error, RuntimeError)


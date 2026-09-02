from analysis.da027_allocation import DA027Error


def test_da027_error_type_is_specific() -> None:
    assert issubclass(DA027Error, RuntimeError)


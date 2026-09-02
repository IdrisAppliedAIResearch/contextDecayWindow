from analysis.da026_allocation import DA026Error


def test_da026_error_type_is_specific() -> None:
    assert issubclass(DA026Error, RuntimeError)


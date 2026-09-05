from analysis.da028_allocation import DA028Error


def test_da028_error_type_is_specific() -> None:
    assert issubclass(DA028Error, RuntimeError)


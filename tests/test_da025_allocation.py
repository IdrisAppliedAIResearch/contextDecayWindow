from analysis.da025_allocation import DA025Error


def test_da025_error_type_is_specific() -> None:
    assert issubclass(DA025Error, RuntimeError)


from analysis.da040_allocation import DA040Error, parse_reference, reference_code


def test_reference_roundtrip() -> None:
    code = reference_code("~~", 37, 1)
    assert parse_reference(code, "~~") == (37, 1)


def test_da040_error_is_runtime_error() -> None:
    assert issubclass(DA040Error, RuntimeError)

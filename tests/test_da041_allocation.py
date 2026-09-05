from analysis.da041_allocation import DA041Error, head_code, parse_head


def test_head_roundtrip() -> None:
    code = head_code("~~")
    assert parse_head(code, "~~") is None


def test_da041_error_is_runtime_error() -> None:
    assert issubclass(DA041Error, RuntimeError)

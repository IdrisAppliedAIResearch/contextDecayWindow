from analysis.da044_allocation import DA044Error, parse_block, parse_page, render_block


def test_block_roundtrip() -> None:
    block = render_block("~", 12, {"speaker": "User", "text": "hello"})
    assert parse_block(block, "~") == (12, "User", "hello")


def test_da044_error_is_runtime_error() -> None:
    assert issubclass(DA044Error, RuntimeError)


def test_page_roundtrip_with_newline_text() -> None:
    first = render_block("~", 1, {"speaker": "User", "text": "hello\nworld"})
    second = render_block("~", 2, {"speaker": "Assistant", "text": "answer"})
    assert parse_page(first + "\n" + second, "~") == [
        (1, "User", "hello\nworld"), (2, "Assistant", "answer")]

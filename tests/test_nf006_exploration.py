from src.analysis.nf006_exploration import split_assistant_statements


def test_split_numbered_sections_without_blank_lines() -> None:
    text = "1. First statement.\n2. Second statement.\n3. Third statement."
    assert split_assistant_statements(text) == [
        "1. First statement.",
        "2. Second statement.",
        "3. Third statement.",
    ]


def test_split_paragraphs_and_drop_standalone_risk_metadata() -> None:
    text = "First paragraph.\n\nSecond paragraph.\n\n(Risk: Medium)"
    assert split_assistant_statements(text) == [
        "First paragraph.",
        "Second paragraph.",
    ]


def test_inline_risk_marker_is_content() -> None:
    text = "One paragraph with evidence. (Risk: Low)"
    assert split_assistant_statements(text) == [text]

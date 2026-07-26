"""Shared general-purpose informativeness score."""

from src.memory.span_segmenter import count_text_features


def density_score(
    named_entities: int,
    numeric_tokens: int,
    word_count: int,
) -> float:
    """Entity/numeric density used by formation and Study 008 retrieval."""
    base = named_entities + 2 * numeric_tokens
    return base / word_count if word_count else 0.0


def text_density(text: str) -> float:
    named_entities, numeric_tokens, word_count = count_text_features(text)
    return density_score(named_entities, numeric_tokens, word_count)

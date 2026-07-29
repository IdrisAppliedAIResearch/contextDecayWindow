from src.analysis.rendering_expansion_replay import (
    _distribution,
    _extract_block,
)


def test_distribution_uses_nearest_rank_percentiles():
    assert _distribution([1, 2, 3, 4]) == {
        "count": 4,
        "min": 1,
        "p25": 1,
        "median": 2,
        "p75": 3,
        "p95": 4,
        "max": 4,
        "total": 10,
    }


def test_distribution_handles_no_stored_spans():
    assert _distribution([]) == {
        "count": 0,
        "min": None,
        "p25": None,
        "median": None,
        "p75": None,
        "p95": None,
        "max": None,
        "total": 0,
    }


def test_extract_block_accepts_populated_and_empty_blocks():
    prompt = "before<retrieved_ltm>value</retrieved_ltm>after"
    assert _extract_block(prompt, "retrieved_ltm") == (
        "<retrieved_ltm>value</retrieved_ltm>"
    )
    assert _extract_block("<retrieved_stm/>", "retrieved_stm") == (
        "<retrieved_stm/>"
    )


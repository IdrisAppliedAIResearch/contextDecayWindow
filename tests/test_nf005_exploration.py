from __future__ import annotations

from analysis.nf005_exploration import distribution, spearman, turn_text


def test_distribution_uses_nearest_rank_quantiles() -> None:
    assert distribution(range(1, 11)) == {
        "n": 10,
        "min": 1,
        "p10": 1,
        "p50": 5,
        "p90": 9,
        "max": 10,
        "mean": 5.5,
    }


def test_spearman_handles_ties_and_direction() -> None:
    assert spearman([1, 1, 2, 3], [4, 4, 2, 1]) == -1.0


def test_turn_text_matches_carried_episode_rendering() -> None:
    assert turn_text({"role": "user", "content": "hello"}) == "User: hello"
    assert turn_text({"role": "assistant", "content": "hi"}) == "Assistant: hi"

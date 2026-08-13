from __future__ import annotations

from analysis.ranking_budget_controls import _distribution, _pack_episode_order, _paired
from analysis.nf003_ranking import Episode


def test_source_style_pack_keeps_scanning_after_overflow() -> None:
    episodes = [
        Episode("s1", 0, "a", 8, False),
        Episode("s2", 0, "b", 15, True),
        Episode("s3", 0, "c", 2, True),
    ]
    assert _pack_episode_order(episodes, [0, 1, 2], 10) == (True, False, 2, 10)


def test_paired_counts_exclude_unevaluable_rows() -> None:
    rows = [
        {"before": False, "after": True},
        {"before": True, "after": False},
        {"before": False, "after": True},
        {"before": None, "after": True},
    ]
    assert _paired(rows, "before", "after") == {
        "n": 3,
        "gains": 2,
        "losses": 1,
        "ties": 0,
        "net": 1,
        "p_one_sided": 0.5,
    }


def test_distribution_uses_registered_nearest_rank_percentiles() -> None:
    assert _distribution(range(1, 11)) == {
        "min": 1,
        "p10": 1,
        "p50": 5,
        "p90": 9,
        "max": 10,
    }

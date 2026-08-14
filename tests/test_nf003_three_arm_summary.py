from __future__ import annotations

from pathlib import Path

from analysis.nf003_three_arm_summary import summarize


def test_three_arm_summary_reproduces_both_one_factor_contrasts() -> None:
    result = summarize(Path(__file__).resolve().parents[1])
    assert [arm["strict_delivery"] for arm in result["arms"]] == [375, 388, 351]
    assert result["one_factor_contrasts"] == {
        "pack_fine_at_session_rank": {
            "net": 13,
            "gains": 17,
            "losses": 4,
            "ties": 444,
        },
        "rank_fine_at_episode_pack": {
            "net": -37,
            "gains": 26,
            "losses": 63,
            "ties": 376,
        },
    }


def test_coarse_rank_rescues_deep_own_cosine_evidence() -> None:
    result = summarize(Path(__file__).resolve().parents[1])
    distributions = result["own_cosine_rank_by_episode_pack_outcome"]
    assert distributions["coarse_rank_rescues"] == {
        "n": 63,
        "min": 9,
        "p50": 46,
        "p90": 135,
        "max": 178,
    }
    assert distributions["fine_rank_gains"] == {
        "n": 26,
        "min": 2,
        "p50": 10,
        "p90": 21,
        "max": 24,
    }
    assert result["model_calls"] == result["embedding_calls"] == 0

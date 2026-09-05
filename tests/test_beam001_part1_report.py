from __future__ import annotations

from analysis.beam001_part1_report import Metrics, distribution


def test_distribution_uses_registered_nearest_rank_points_and_histogram() -> None:
    result = distribution([0, 1, 1, 3], discrete=True)
    assert result["min"] == 0
    assert result["median"] == 1
    assert result["p95"] == 3
    assert result["histogram"] == {"0": 1, "1": 2, "3": 1}


def test_metrics_emit_scale_and_question_family_strata() -> None:
    metrics = Metrics()
    metrics.add(
        "count",
        4,
        prefix="arm=A0",
        split="100K",
        category="abstention",
    )
    rendered = metrics.render()["count"]
    assert set(rendered) == {
        "arm=A0",
        "arm=A0|split=100K",
        "arm=A0|category=abstention",
        "arm=A0|split=100K|category=abstention",
    }

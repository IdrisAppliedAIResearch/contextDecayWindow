from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.analysis.rd001_rarity_diagnostic import (
    EXPECTED_VARIANTS,
    assess_feasibility,
    plant_inventory,
    rank_pool,
)
from src.retrieval_bakeoff.config import EMBEDDING_DIMENSION


def _candidate(candidate_id: str, turn: int, embedding: np.ndarray) -> dict:
    return {
        "id": candidate_id,
        "turn_number": turn,
        "user_message": f"phrase {turn}",
        "assistant_message": "body",
        "embedding": embedding.astype(np.float32).tobytes(),
    }


def _vector(index: int) -> np.ndarray:
    result = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    result[index] = 1.0
    return result


def test_rank_pool_is_best_first_with_stable_ties() -> None:
    pool = (
        _candidate("b", 2, _vector(0)),
        _candidate("a", 1, _vector(0)),
        _candidate("c", 3, _vector(1)),
    )

    ranked = rank_pool(pool, _vector(0))

    assert [row[0]["id"] for row in ranked] == ["a", "b", "c"]


def test_plant_inventory_preserves_committed_scores() -> None:
    candidate = _candidate("episode", 7, _vector(0))
    rank_by_turn = {
        7: {
            "cosine_rank": 4,
            "cosine": 0.25,
        }
    }
    rarity = [
        {
            "plant": "p",
            "variant": "rarity_mean",
            "source_turn": "7",
            "span_text": "phrase 7",
            "score": "3.5",
            "rank": "12",
        }
    ]

    rows = plant_inventory(rarity, rank_by_turn, [candidate])

    assert rows[0]["rarity_score"] == "3.5"
    assert rows[0]["phrase_start"] == 0
    assert rows[0]["phrase_found"] is True


def test_incomplete_rarity_coverage_fails_closed_without_coefficient() -> None:
    rank_rows = [
        {
            "episode_id": f"e{index}",
            "fact_count": 1,
        }
        for index in range(76)
    ]
    rarity_rows = [
        {"plant": f"p{index}", "variant": variant}
        for index in range(6)
        for variant in EXPECTED_VARIANTS
    ]
    plant_rows = [
        {
            "episode_id": f"e{index}",
            "phrase_found": True,
        }
        for index in range(6)
        for _variant in EXPECTED_VARIANTS
    ]

    result = assess_feasibility(
        rank_rows,
        rarity_rows,
        plant_rows,
        {"status": "PASS"},
    )

    assert result["status"] == "STOP_MEASUREMENT_NOT_IDENTIFIABLE"
    assert result["registered_branch"] == "NONE"
    assert result["fact_bearing_episodes_with_committed_rarity"] == 6
    assert result["fact_bearing_episodes_without_committed_rarity"] == 70
    assert result["spearman_computed"] is False
    assert result["part_2_authorized"] is False


def test_complete_measurement_stops_before_an_unregistered_statistic() -> None:
    rank_rows = [
        {
            "episode_id": f"e{index}",
            "fact_count": 1,
        }
        for index in range(76)
    ]
    rarity_rows = [
        {"plant": f"p{index}", "variant": "registered_primary"}
        for index in range(76)
    ]
    plant_rows = [
        {
            "episode_id": f"e{index}",
            "phrase_found": True,
        }
        for index in range(76)
    ]

    with pytest.raises(AssertionError, match="register the statistic"):
        assess_feasibility(
            rank_rows,
            rarity_rows,
            plant_rows,
            {"status": "PASS"},
        )


def test_source_contains_no_spearman_or_rarity_recomputation() -> None:
    source = Path(__file__).parents[1] / "src" / "analysis" / "rd001_rarity_diagnostic.py"
    text = source.read_text(encoding="utf-8").lower()

    assert "scipy" not in text
    assert "spearmanr" not in text
    assert "idf(" not in text

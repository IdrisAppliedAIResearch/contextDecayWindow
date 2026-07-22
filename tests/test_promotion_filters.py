from dataclasses import dataclass

import numpy as np
import pytest

from src.memory.promotion_filters import (
    calculate_weighted_score,
    evaluate_promotion,
    score_association,
    score_emotional_valence,
    score_novelty,
    score_repetition,
)


@dataclass
class FakeResult:
    assistant_message: str


class FakeInferenceClient:
    def __init__(self, response: str):
        self.response = response

    def complete(self, prompt, suppress_rule_detection=False):
        assert suppress_rule_detection is True
        return FakeResult(self.response)


class TestPromotionScores:
    def test_empty_ltm_defaults(self):
        embedding = np.ones(1024, dtype=np.float32)
        assert score_novelty(embedding, None) == 1.0
        assert score_association(embedding, {}) == 0.0

    def test_single_topic_ltm_preserves_registered_complement_case(self):
        embedding = np.ones(1024, dtype=np.float32)
        centroid = np.ones(1024, dtype=np.float32)
        assert score_novelty(embedding, centroid) == pytest.approx(0.0)
        assert score_association(embedding, {"topic_1": centroid}) == pytest.approx(1.0)

    def test_two_topic_association_is_maximum_not_mean(self):
        embedding = np.zeros(1024, dtype=np.float32)
        embedding[0] = 1.0
        high = np.zeros(1024, dtype=np.float32)
        high[0] = 0.8
        high[1] = 0.6
        low = np.zeros(1024, dtype=np.float32)
        low[1] = 1.0

        score = score_association(
            embedding, {"topic_high": high, "topic_low": low}
        )

        assert score == pytest.approx(0.8)
        assert score != pytest.approx(0.4)

    def test_repetition_is_capped(self):
        assert score_repetition(0) == 0.0
        assert score_repetition(3) == pytest.approx(0.6)
        assert score_repetition(10) == 1.0

    def test_repetition_rejects_nonpositive_maximum(self):
        with pytest.raises(ValueError):
            score_repetition(1, max_count=0)

    def test_emotional_score_is_parsed_and_clamped(self):
        assert score_emotional_valence("stressful", FakeInferenceClient("1.4")) == 1.0
        assert score_emotional_valence("calm", FakeInferenceClient("-0.2")) == 0.0

    def test_emotional_parse_failure_defaults_to_zero(self, caplog):
        score = score_emotional_valence("neutral", FakeInferenceClient("unknown"))
        assert score == 0.0
        assert "Could not parse emotional-valence" in caplog.text


class TestPromotionDecision:
    def test_all_or_nothing_fires_before_weighted_threshold(self):
        assert evaluate_promotion(0.95, 0.0, 0.0, 0.0) == (
            True, "all_or_nothing", "novelty"
        )

    def test_empty_ltm_suspends_all_or_nothing_for_novelty(self):
        assert evaluate_promotion(0.95, 0.0, 0.0, 0.0, ltm_is_empty=True) == (
            False, "", None
        )
        assert evaluate_promotion(1.0, 0.0, 0.0, 0.0, ltm_is_empty=True) == (
            False, "", None
        )

    def test_empty_ltm_suspends_all_or_nothing_for_emotional(self):
        assert evaluate_promotion(0.0, 0.0, 0.0, 0.95, ltm_is_empty=True) == (
            False, "", None
        )

    def test_weighted_threshold_promotes_when_ltm_is_empty(self):
        assert evaluate_promotion(1.0, 0.60, 0.0, 0.50, ltm_is_empty=True) == (
            True, "weighted_threshold", None
        )

    def test_weighted_score_matches_registered_weights(self):
        score = calculate_weighted_score(0.70, 0.60, 0.50, 0.40)
        assert score == pytest.approx(0.585)
        assert evaluate_promotion(0.70, 0.60, 0.50, 0.40) == (
            False, "", None
        )

    def test_association_is_excluded_from_all_or_nothing_bypass(self):
        assert calculate_weighted_score(0.0, 0.0, 0.95, 0.0) == pytest.approx(0.19)
        assert evaluate_promotion(0.0, 0.0, 0.95, 0.0) == (
            False, "", None
        )

"""Scoring and decision rules for Study 003 STM-to-LTM promotion."""

import logging
import re
from typing import Optional

import numpy as np

from src.embeddings.provider import cosine_similarity


LOGGER = logging.getLogger(__name__)

WEIGHTS = {
    "novelty": 0.35,
    "repetition": 0.30,
    "association": 0.20,
    "emotional": 0.15,
}
WEIGHTED_THRESHOLD = 0.60
ALL_OR_NOTHING_THRESHOLD = 0.90

EMOTIONAL_VALENCE_PROMPT = """Score the following text for emotional significance on a scale from 0.0 to 1.0.
Emotional significance includes fear, joy, anger, stress, excitement, grief, or surprise.
Return only a single float and nothing else.

TEXT:
{episode_content}"""


def _clamp(score: float) -> float:
    return max(0.0, min(1.0, float(score)))


def score_novelty(
    episode_embedding: np.ndarray,
    ltm_centroid: Optional[np.ndarray],
) -> float:
    """Return distance from the LTM centroid, defaulting to 1.0 when empty."""
    if ltm_centroid is None:
        return 1.0
    association = _clamp(cosine_similarity(episode_embedding, ltm_centroid))
    return _clamp(1.0 - association)


def score_repetition(retrieval_count: int, max_count: int = 5) -> float:
    """Normalize home-topic retrieval frequency to the inclusive range [0, 1]."""
    if max_count <= 0:
        raise ValueError("max_count must be positive")
    return _clamp(retrieval_count / max_count)


def score_association(
    episode_embedding: np.ndarray,
    ltm_centroid: Optional[np.ndarray],
) -> float:
    """Return similarity to the LTM centroid, defaulting to 0.0 when empty."""
    if ltm_centroid is None:
        return 0.0
    return _clamp(cosine_similarity(episode_embedding, ltm_centroid))


def score_emotional_valence(episode_content: str, inference_client) -> float:
    """Ask the inference provider for an emotional-significance score."""
    prompt = EMOTIONAL_VALENCE_PROMPT.format(episode_content=episode_content)
    result = inference_client.complete(prompt, suppress_rule_detection=True)
    match = re.search(r"[-+]?(?:\d+\.\d+|\d+|\.\d+)", result.assistant_message)
    if not match:
        LOGGER.warning("Could not parse emotional-valence score; defaulting to 0.0")
        return 0.0
    return _clamp(float(match.group(0)))


def calculate_weighted_score(
    novelty: float,
    repetition: float,
    association: float,
    emotional: float,
) -> float:
    """Calculate the pre-registered weighted promotion score."""
    return (
        WEIGHTS["novelty"] * _clamp(novelty)
        + WEIGHTS["repetition"] * _clamp(repetition)
        + WEIGHTS["association"] * _clamp(association)
        + WEIGHTS["emotional"] * _clamp(emotional)
    )


def evaluate_promotion(
    novelty: float,
    repetition: float,
    association: float,
    emotional: float,
    ltm_is_empty: bool = False,
) -> tuple[bool, str, Optional[str]]:
    """Return promotion decision, trigger type, and optional triggering filter."""
    scores = {
        "novelty": _clamp(novelty),
        "repetition": _clamp(repetition),
        "association": _clamp(association),
        "emotional": _clamp(emotional),
    }
    if not ltm_is_empty:
        for filter_name, score in scores.items():
            if score >= ALL_OR_NOTHING_THRESHOLD:
                return True, "all_or_nothing", filter_name

    if calculate_weighted_score(**scores) >= WEIGHTED_THRESHOLD:
        return True, "weighted_threshold", None
    return False, "", None

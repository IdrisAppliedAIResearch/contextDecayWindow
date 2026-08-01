from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

# The A3 selector and the budgeted greedy frame moved into the episodic
# library (CC-002); re-exported here so every committed E005/DX-001
# consumer keeps its import path. A1 and A2 stay in this module: both
# build an O(n^2) similarity matrix and were not extracted.
from episodic._selection import (  # noqa: F401
    ClusterDiversitySelector,
    SelectionResult,
    SelectionStep,
    additive_weight,
    deterministic_clusters,
    relevance_vector,
    select,
    unit_vectors,
    vector,
    wrapper_chars,
)


FORBIDDEN_MECHANISM_PATH_PARTS = (
    "q_facts_key",
    "rubric",
    "atomic_items",
    "targeted_items",
)

LAMBDA_VALUES = tuple(round(value / 10.0, 1) for value in range(11))
COST_EXPONENTS = (0.0, 0.5, 1.0)
CLUSTER_COUNTS = (2, 4, 8, 16)


def assert_mechanism_path_allowed(path: str | Path) -> None:
    normalized = str(path).replace("\\", "/").lower()
    if any(part in normalized for part in FORBIDDEN_MECHANISM_PATH_PARTS):
        raise ValueError(f"Mechanism path crosses the measurement boundary: {path}")


def eligible_candidates(
    candidates: Iterable[dict],
    *,
    probe_turn: int,
) -> tuple[dict, ...]:
    eligible = tuple(
        candidate
        for candidate in candidates
        if int(candidate["turn_number"]) < probe_turn
    )
    if any(int(candidate["turn_number"]) >= probe_turn for candidate in eligible):
        raise AssertionError("Temporal eligibility filter leaked a future episode")
    return eligible


def similarity_matrix(candidates: Sequence[dict]) -> np.ndarray:
    normalized = unit_vectors(candidates)
    return normalized @ normalized.T


class MmrSelector:
    """Carbonell and Goldstein (1998). A per-step criterion, not a set function."""

    arm = "A1"
    has_set_function = False

    def __init__(self, *, lambda_: float, similarity: np.ndarray) -> None:
        self.lambda_ = float(lambda_)
        self.similarity = similarity
        self.cost_exponent = 0.0

    @property
    def parameters(self) -> tuple[tuple[str, float], ...]:
        return (("lambda", self.lambda_),)

    def scaled_gains(
        self,
        relevance: np.ndarray,
        selected: Sequence[int],
        costs: np.ndarray,
    ) -> np.ndarray:
        del costs
        if selected:
            penalty = self.similarity[:, list(selected)].max(axis=1)
        else:
            penalty = np.zeros(relevance.shape, dtype=np.float64)
        return self.lambda_ * relevance - (1.0 - self.lambda_) * penalty

    def objective_gains(
        self,
        relevance: np.ndarray,
        selected: Sequence[int],
        costs: np.ndarray,
    ) -> np.ndarray:
        return self.scaled_gains(relevance, selected, costs)

    def objective(self, selected: Sequence[int], relevance: np.ndarray) -> None:
        del selected, relevance
        return None


class FacilityLocationSelector:
    """f(S) = sum_i max_{j in S} max(0, cos(i, j)). Monotone and submodular."""

    arm = "A2"
    has_set_function = True

    def __init__(self, *, cost_exponent: float, similarity: np.ndarray) -> None:
        self.cost_exponent = float(cost_exponent)
        self.similarity = np.maximum(similarity, 0.0)

    @property
    def parameters(self) -> tuple[tuple[str, float], ...]:
        return (("r", self.cost_exponent),)

    def _coverage(self, selected: Sequence[int]) -> np.ndarray:
        if not selected:
            return np.zeros(self.similarity.shape[0], dtype=np.float64)
        return self.similarity[:, list(selected)].max(axis=1)

    def objective_gains(
        self,
        relevance: np.ndarray,
        selected: Sequence[int],
        costs: np.ndarray,
    ) -> np.ndarray:
        del relevance, costs
        current = self._coverage(selected)
        improved = np.maximum(self.similarity, current[:, None])
        return improved.sum(axis=0) - current.sum()

    def scaled_gains(
        self,
        relevance: np.ndarray,
        selected: Sequence[int],
        costs: np.ndarray,
    ) -> np.ndarray:
        gains = self.objective_gains(relevance, selected, costs)
        return gains / np.power(costs, self.cost_exponent)

    def objective(
        self,
        selected: Sequence[int],
        relevance: np.ndarray,
    ) -> float:
        del relevance
        return float(self._coverage(selected).sum())


def build_selectors(
    candidates: Sequence[dict],
) -> tuple[tuple[str, object], ...]:
    """Every registered deployable configuration, in reporting order."""
    similarity = similarity_matrix(candidates)
    clusters = {
        count: deterministic_clusters(candidates, count)
        for count in CLUSTER_COUNTS
    }
    selectors: list[tuple[str, object]] = []
    for lambda_ in LAMBDA_VALUES:
        selectors.append(
            (
                configuration_id("A1", lambda_=lambda_),
                MmrSelector(lambda_=lambda_, similarity=similarity),
            )
        )
    for exponent in COST_EXPONENTS:
        selectors.append(
            (
                configuration_id("A2", cost_exponent=exponent),
                FacilityLocationSelector(
                    cost_exponent=exponent,
                    similarity=similarity,
                ),
            )
        )
    for lambda_ in LAMBDA_VALUES:
        for exponent in COST_EXPONENTS:
            for count in CLUSTER_COUNTS:
                selectors.append(
                    (
                        configuration_id(
                            "A3",
                            lambda_=lambda_,
                            cost_exponent=exponent,
                            cluster_count=count,
                        ),
                        ClusterDiversitySelector(
                            lambda_=lambda_,
                            cost_exponent=exponent,
                            assignments=clusters[count],
                            cluster_count=count,
                        ),
                    )
                )
    return tuple(selectors)


def configuration_id(
    arm: str,
    *,
    lambda_: float | None = None,
    cost_exponent: float | None = None,
    cluster_count: int | None = None,
) -> str:
    parts = [arm]
    if lambda_ is not None:
        parts.append(f"l{lambda_:.1f}")
    if cost_exponent is not None:
        parts.append(f"r{cost_exponent:.1f}")
    if cluster_count is not None:
        parts.append(f"k{cluster_count:02d}")
    return "_".join(parts)


def result_record(
    result: SelectionResult,
    *,
    configuration_id: str,
    probe_turn: int,
    pool: str,
) -> dict:
    return {
        "configuration_id": configuration_id,
        "arm": result.arm,
        "pool": pool,
        "probe_turn": probe_turn,
        "parameters": {name: value for name, value in result.parameters},
        "budget_chars": result.budget_chars,
        "steps": [
            {
                "step": step.step,
                "candidate_id": step.candidate_id,
                "source_turn": step.source_turn,
                "domain": step.domain,
                "relevance": step.relevance,
                "objective_gain": step.objective_gain,
                "scaled_gain": step.scaled_gain,
                "additive_chars": step.additive_chars,
                "cumulative_chars": step.cumulative_chars,
            }
            for step in result.steps
        ],
        "selected_ids": list(result.selected_ids),
        "selected_source_turns": list(result.selected_source_turns),
        "selected_domains": list(result.selected_domains),
        "serialized_chars": result.serialized_chars,
        "payload_sha256": result.payload_sha256,
        "objective_value": result.objective_value,
        "optimality_bound": result.optimality_bound,
    }

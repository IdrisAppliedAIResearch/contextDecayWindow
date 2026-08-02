from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

import numpy as np

from src.memory.context_matched_stm import render_stm_payload
from src.memory.stm_context_builder import render_episode_element
from src.retrieval_bakeoff.config import EMBEDDING_DIMENSION


FORBIDDEN_MECHANISM_PATH_PARTS = (
    "q_facts_key",
    "rubric",
    "atomic_items",
    "targeted_items",
)

LAMBDA_VALUES = tuple(round(value / 10.0, 1) for value in range(11))
COST_EXPONENTS = (0.0, 0.5, 1.0)
CLUSTER_COUNTS = (2, 4, 8, 16)
LLOYD_MAX_ITERATIONS = 100


@dataclass(frozen=True)
class SelectionStep:
    step: int
    candidate_id: str
    source_turn: int
    domain: str
    relevance: float
    objective_gain: float
    scaled_gain: float
    additive_chars: int
    cumulative_chars: int


@dataclass(frozen=True)
class SelectionResult:
    arm: str
    parameters: tuple[tuple[str, float], ...]
    budget_chars: int
    steps: tuple[SelectionStep, ...]
    selected_ids: tuple[str, ...]
    selected_source_turns: tuple[int, ...]
    selected_domains: tuple[str, ...]
    serialized_chars: int
    payload_sha256: str
    payload: str
    objective_value: float | None
    optimality_bound: float | None
    skipped_ids: tuple[str, ...]


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


def additive_weight(candidate: dict) -> int:
    """Serialized cost an episode adds inside a non-empty retrieved_stm block."""
    return len(render_episode_element(candidate)) + 1


def wrapper_chars() -> int:
    """Fixed two-block payload cost charged once for a non-empty selection."""
    probe = {
        "id": "wrapper-probe",
        "turn_number": 0,
        "user_message": "",
        "assistant_message": "",
    }
    return len(render_stm_payload([], [probe])) - additive_weight(probe)


def vector(value: object) -> np.ndarray:
    if isinstance(value, (bytes, bytearray, memoryview)):
        array = np.frombuffer(value, dtype=np.float32).copy()
    else:
        array = np.asarray(value, dtype=np.float32)
    return array.reshape(EMBEDDING_DIMENSION)


def unit_vectors(candidates: Sequence[dict]) -> np.ndarray:
    matrix = np.stack([vector(candidate["embedding"]) for candidate in candidates])
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return matrix / norms


def similarity_matrix(candidates: Sequence[dict]) -> np.ndarray:
    normalized = unit_vectors(candidates)
    return normalized @ normalized.T


def relevance_vector(
    query_embedding: np.ndarray,
    candidates: Sequence[dict],
) -> np.ndarray:
    query = vector(query_embedding)
    norm = float(np.linalg.norm(query))
    if norm == 0.0:
        return np.zeros(len(candidates), dtype=np.float64)
    return (unit_vectors(candidates) @ (query / norm)).astype(np.float64)


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


class ClusterDiversitySelector:
    """Shang et al. (2018) form: modular relevance plus cluster coverage."""

    arm = "A3"
    has_set_function = True

    def __init__(
        self,
        *,
        lambda_: float,
        cost_exponent: float,
        assignments: np.ndarray,
        cluster_count: int,
    ) -> None:
        self.lambda_ = float(lambda_)
        self.cost_exponent = float(cost_exponent)
        self.assignments = assignments
        self.cluster_count = int(cluster_count)

    @property
    def parameters(self) -> tuple[tuple[str, float], ...]:
        return (
            ("lambda", self.lambda_),
            ("r", self.cost_exponent),
            ("k", float(self.cluster_count)),
        )

    def objective_gains(
        self,
        relevance: np.ndarray,
        selected: Sequence[int],
        costs: np.ndarray,
    ) -> np.ndarray:
        del costs
        covered = {int(self.assignments[index]) for index in selected}
        novel = np.array(
            [
                0.0 if int(cluster) in covered else 1.0
                for cluster in self.assignments
            ],
            dtype=np.float64,
        )
        return np.maximum(relevance, 0.0) + self.lambda_ * novel

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
        if not selected:
            return 0.0
        informativeness = float(
            np.maximum(relevance[list(selected)], 0.0).sum()
        )
        covered = {int(self.assignments[index]) for index in selected}
        return informativeness + self.lambda_ * len(covered)


def deterministic_clusters(
    candidates: Sequence[dict],
    cluster_count: int,
) -> np.ndarray:
    """Farthest-first initialization then Lloyd iterations. No RNG."""
    if cluster_count < 1:
        raise ValueError("cluster_count must be positive")
    points = unit_vectors(candidates).astype(np.float64)
    count = points.shape[0]
    if cluster_count >= count:
        return np.arange(count)

    centers = [0]
    distances = _squared_distances(points, points[0])
    while len(centers) < cluster_count:
        centers.append(int(np.argmax(distances)))
        distances = np.minimum(
            distances,
            _squared_distances(points, points[centers[-1]]),
        )
    centroids = points[centers].copy()

    assignments = np.full(count, -1)
    for _ in range(LLOYD_MAX_ITERATIONS):
        candidate_distances = np.stack(
            [_squared_distances(points, centroid) for centroid in centroids],
            axis=1,
        )
        updated = np.argmin(candidate_distances, axis=1)
        if np.array_equal(updated, assignments):
            break
        assignments = updated
        for cluster in range(cluster_count):
            members = points[assignments == cluster]
            if members.size:
                centroids[cluster] = members.mean(axis=0)
    return assignments


def select(
    *,
    candidates: Sequence[dict],
    query_embedding: np.ndarray,
    selector,
    budget_chars: int,
) -> SelectionResult:
    if not candidates:
        raise ValueError("At least one eligible candidate is required")

    relevance = relevance_vector(query_embedding, candidates)
    costs = np.array(
        [float(additive_weight(candidate)) for candidate in candidates],
        dtype=np.float64,
    )
    turns = [int(candidate["turn_number"]) for candidate in candidates]
    identifiers = [str(candidate["id"]) for candidate in candidates]
    fixed = wrapper_chars()

    selected: list[int] = []
    steps: list[SelectionStep] = []
    spent = 0
    remaining = set(range(len(candidates)))

    while remaining:
        affordable = [
            index
            for index in sorted(remaining)
            if fixed + spent + int(costs[index]) <= budget_chars
        ]
        if not affordable:
            break
        scaled = selector.scaled_gains(relevance, selected, costs)
        objective = selector.objective_gains(relevance, selected, costs)
        chosen = min(
            affordable,
            key=lambda index: (
                -float(scaled[index]),
                int(costs[index]),
                turns[index],
                identifiers[index],
            ),
        )
        spent += int(costs[chosen])
        selected.append(chosen)
        remaining.discard(chosen)
        steps.append(
            SelectionStep(
                step=len(steps) + 1,
                candidate_id=identifiers[chosen],
                source_turn=turns[chosen],
                domain=str(candidates[chosen].get("ground_truth_domain") or ""),
                relevance=float(relevance[chosen]),
                objective_gain=float(objective[chosen]),
                scaled_gain=float(scaled[chosen]),
                additive_chars=int(costs[chosen]),
                cumulative_chars=fixed + spent,
            )
        )

    chosen_candidates = [candidates[index] for index in selected]
    payload = render_stm_payload([], chosen_candidates)
    if len(payload) > budget_chars:
        raise AssertionError("E005 selection exceeded its character budget")
    if len(payload) != fixed + spent:
        raise AssertionError(
            "Additive serialized cost did not reproduce the rendered payload"
        )

    return SelectionResult(
        arm=selector.arm,
        parameters=selector.parameters,
        budget_chars=budget_chars,
        steps=tuple(steps),
        selected_ids=tuple(identifiers[index] for index in selected),
        selected_source_turns=tuple(turns[index] for index in selected),
        selected_domains=tuple(
            str(candidates[index].get("ground_truth_domain") or "")
            for index in selected
        ),
        serialized_chars=len(payload),
        payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        payload=payload,
        objective_value=selector.objective(selected, relevance),
        optimality_bound=(
            _optimality_bound(
                selector=selector,
                relevance=relevance,
                costs=costs,
                selected=selected,
                budget_chars=budget_chars,
                fixed=fixed,
                spent=spent,
            )
            if selector.has_set_function
            else None
        ),
        skipped_ids=tuple(identifiers[index] for index in sorted(remaining)),
    )


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


def _optimality_bound(
    *,
    selector,
    relevance: np.ndarray,
    costs: np.ndarray,
    selected: Sequence[int],
    budget_chars: int,
    fixed: int,
    spent: int,
) -> float:
    """Data-dependent upper bound on the optimum for a monotone submodular f.

    At the returned set S, every unselected element's marginal gain bounds its
    contribution by submodularity. Filling the residual budget fractionally in
    descending gain-per-character therefore over-states any feasible set.
    """
    value = selector.objective(selected, relevance)
    gains = selector.objective_gains(relevance, selected, costs)
    residual = float(budget_chars - fixed - spent)
    if residual <= 0.0:
        return float(value)
    ratios = sorted(
        (
            (float(gains[index]) / float(costs[index]), float(gains[index]), float(costs[index]))
            for index in range(len(costs))
            if index not in set(selected) and float(gains[index]) > 0.0
        ),
        key=lambda item: -item[0],
    )
    bound = float(value)
    for ratio, gain, cost in ratios:
        if residual <= 0.0:
            break
        take = min(1.0, residual / cost)
        bound += take * gain
        residual -= take * cost
    return bound


def _squared_distances(points: np.ndarray, centroid: np.ndarray) -> np.ndarray:
    difference = points - centroid
    return np.einsum("ij,ij->i", difference, difference)

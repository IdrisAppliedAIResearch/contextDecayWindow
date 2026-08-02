"""E005's deployable set-level selection, moved verbatim.

The A3 objective (relevance plus cluster diversity) and the budgeted
greedy frame move from the source repository's
`src/retrieval_mechanism_ledger/e005.py`. A1 (MMR) and A2 (facility
location) are deliberately not extracted: both build an O(n^2) similarity
matrix over the candidate pool, which DR-002 disqualified at scale. A3
needs only the cluster assignment vector.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from ._embedding import EMBEDDING_DIMENSION
from ._render import render_episode_element, render_stm_payload

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


def additive_weight(candidate: dict) -> int:
    """Serialized cost an episode adds inside a non-empty retrieved_stm block."""
    return len(render_episode_element(candidate)) + 1


def wrapper_chars() -> int:
    """Fixed two-block payload cost charged once for a non-empty selection."""
    sample = {
        "id": "wrapper-sample",
        "turn_number": 0,
        "user_message": "",
        "assistant_message": "",
    }
    return len(render_stm_payload([], [sample])) - additive_weight(sample)


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


def relevance_vector(
    query_embedding: np.ndarray,
    candidates: Sequence[dict],
) -> np.ndarray:
    query = vector(query_embedding)
    norm = float(np.linalg.norm(query))
    if norm == 0.0:
        return np.zeros(len(candidates), dtype=np.float64)
    return (unit_vectors(candidates) @ (query / norm)).astype(np.float64)


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
        raise AssertionError("Selection exceeded its character budget")
    if selected and len(payload) != fixed + spent:
        # ``fixed`` is the wrapper cost of a *non-empty* retrieved_stm
        # block, so the additive identity only describes a non-empty
        # selection. An empty selection renders the two self-closing tags
        # instead, and comparing that against ``fixed`` fired an assertion
        # at every budget too small to afford a single candidate (CC-003
        # E4). The budget ceiling above is checked unconditionally.
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

from __future__ import annotations

import itertools
import re
import statistics
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import DEFAULT_BUDGET, CorpusSpec
from .embedding import normalize_embedding
from .models import Candidate, Query, RankedCandidate, RetrievalResult
from .serialization import pack_ranked_candidates


GRAPH_CONFIGS: dict[str, tuple[str, ...]] = {
    "E1": ("E1",),
    "E2": ("E2",),
    "E3": ("E3",),
    "E1_E2": ("E1", "E2"),
    "E1_E3": ("E1", "E3"),
    "E2_E3": ("E2", "E3"),
    "E1_E2_E3": ("E1", "E2", "E3"),
    "E4": ("E4",),
}
_BLOCK = re.compile(
    r"<(?P<name>recent_context|retrieved_stm|retrieved_ltm)"
    r"(?:>.*?</(?P=name)>|/>)",
    flags=re.DOTALL,
)


@dataclass(frozen=True)
class GraphTransition:
    source: np.ndarray
    destination: np.ndarray
    probability: np.ndarray
    node_count: int

    def propagate(self, activation: np.ndarray) -> np.ndarray:
        if not len(self.source):
            return np.zeros(self.node_count, dtype=np.float64)
        contribution = (
            self.probability.astype(np.float64, copy=False)
            * activation[self.source]
        )
        return np.bincount(
            self.destination,
            weights=contribution,
            minlength=self.node_count,
        )


@dataclass
class GraphComponent:
    component_id: str
    transition: GraphTransition
    undirected_edge_count: int
    density: float
    connected_component_count: int
    largest_component_size: int
    isolated_node_count: int
    build_ms: float
    actual_update_median_ns: float


class AssociativeGraphIndex:
    def __init__(
        self,
        spec: CorpusSpec,
        candidates: list[Candidate],
    ) -> None:
        self.spec = spec
        self.candidates = sorted(
            candidates,
            key=lambda item: (item.turn_number, item.candidate_id),
        )
        if not self.candidates:
            raise ValueError("Cannot build an empty graph")
        observed_turns = [candidate.turn_number for candidate in self.candidates]
        expected_turns = list(
            range(spec.eligible_turn_min, spec.eligible_turn_max + 1)
        )
        if observed_turns != expected_turns:
            raise AssertionError(
                f"{spec.corpus_id} graph nodes do not cover each eligible turn"
            )
        self.matrix = np.vstack(
            [
                normalize_embedding(np.asarray(candidate.embedding))
                for candidate in self.candidates
            ]
        ).astype(np.float32, copy=False)
        self.id_rank = np.argsort(
            np.argsort(
                np.asarray(
                    [candidate.candidate_id for candidate in self.candidates]
                )
            )
        )
        self.contexts: list[list[int]] = []
        self.e3_neighbor_scores = np.full(
            (len(self.candidates), 8),
            -np.inf,
            dtype=np.float32,
        )
        self.components = self._build_components()
        self._combined: dict[str, GraphTransition] = {}
        self._combination_build_ms: dict[str, float] = {}

    def transition_for(self, config_id: str) -> GraphTransition:
        if config_id in self._combined:
            return self._combined[config_id]
        component_ids = GRAPH_CONFIGS[config_id]
        start = time.perf_counter()
        scale = np.float32(1.0 / len(component_ids))
        source = np.concatenate(
            [
                self.components[component].transition.source
                for component in component_ids
            ]
        )
        destination = np.concatenate(
            [
                self.components[component].transition.destination
                for component in component_ids
            ]
        )
        probability = np.concatenate(
            [
                self.components[component].transition.probability * scale
                for component in component_ids
            ]
        ).astype(np.float32, copy=False)
        transition = GraphTransition(
            source=source,
            destination=destination,
            probability=probability,
            node_count=len(self.candidates),
        )
        self._combined[config_id] = transition
        self._combination_build_ms[config_id] = (
            time.perf_counter() - start
        ) * 1000.0
        return transition

    def config_build_ms(self, config_id: str) -> float:
        self.transition_for(config_id)
        return sum(
            self.components[component].build_ms
            for component in GRAPH_CONFIGS[config_id]
        ) + self._combination_build_ms[config_id]

    def statistics(self) -> dict:
        return {
            "corpus_id": self.spec.corpus_id,
            "node_count": len(self.candidates),
            "eligible_turn_min": self.spec.eligible_turn_min,
            "eligible_turn_max": self.spec.eligible_turn_max,
            "parsed_context_count": len(self.contexts),
            "components": {
                component_id: {
                    "undirected_edge_count": component.undirected_edge_count,
                    "density": component.density,
                    "connected_component_count": (
                        component.connected_component_count
                    ),
                    "largest_component_size": component.largest_component_size,
                    "isolated_node_count": component.isolated_node_count,
                    "build_ms": component.build_ms,
                    "actual_update_median_ns": (
                        component.actual_update_median_ns
                    ),
                }
                for component_id, component in self.components.items()
            },
        }

    def _build_components(self) -> dict[str, GraphComponent]:
        builders = {
            "E1": self._build_e1,
            "E2": self._build_e2,
            "E3": self._build_e3,
            "E4": self._build_e4,
        }
        return {
            component_id: builder()
            for component_id, builder in builders.items()
        }

    def _build_e1(self) -> GraphComponent:
        start = time.perf_counter()
        size = len(self.candidates)
        left_nodes = np.empty(max(size - 1, 0), dtype=np.int32)
        right_nodes = np.empty(max(size - 1, 0), dtype=np.int32)
        update_times = []
        for edge_index, (left, right) in enumerate(
            zip(range(size - 1), range(1, size), strict=True)
        ):
            update_start = time.perf_counter_ns()
            left_nodes[edge_index] = left
            right_nodes[edge_index] = right
            update_times.append(time.perf_counter_ns() - update_start)
        return self._component(
            "E1",
            left_nodes,
            right_nodes,
            np.ones(len(left_nodes), dtype=np.float32),
            start,
            update_times,
        )

    def _build_e2(self) -> GraphComponent:
        start = time.perf_counter()
        self.contexts = _parse_historical_contexts(
            self.spec,
            self.candidates,
        )
        edge_counts: dict[tuple[int, int], float] = {}
        update_times = []
        for context in self.contexts:
            update_start = time.perf_counter_ns()
            for left, right in itertools.combinations(context, 2):
                edge = (left, right)
                edge_counts[edge] = edge_counts.get(edge, 0.0) + 1.0
            update_times.append(time.perf_counter_ns() - update_start)
        left_nodes, right_nodes, weights = _edge_mapping_arrays(edge_counts)
        return self._component(
            "E2",
            left_nodes,
            right_nodes,
            weights,
            start,
            update_times,
        )

    def _build_e3(self) -> GraphComponent:
        start = time.perf_counter()
        size = len(self.candidates)
        similarities = self.matrix @ self.matrix.T
        np.fill_diagonal(similarities, -np.inf)
        edge_weights: dict[tuple[int, int], float] = {}
        for index in range(size):
            order = np.lexsort((self.id_rank, -similarities[index]))
            neighbors = order[: min(8, size - 1)]
            raw_scores = similarities[index, neighbors]
            if len(raw_scores):
                padded = np.full(8, -np.inf, dtype=np.float32)
                padded[-len(raw_scores) :] = np.sort(raw_scores)
                self.e3_neighbor_scores[index] = padded
            for neighbor, raw_score in zip(
                neighbors,
                raw_scores,
                strict=True,
            ):
                score = max(float(raw_score), 0.0)
                if score <= 0:
                    continue
                edge = (
                    (index, int(neighbor))
                    if index < neighbor
                    else (int(neighbor), index)
                )
                edge_weights[edge] = max(edge_weights.get(edge, 0.0), score)
        left_nodes, right_nodes, weights = _edge_mapping_arrays(edge_weights)
        component = self._component(
            "E3",
            left_nodes,
            right_nodes,
            weights,
            start,
            [],
        )
        update_times = _replay_e3_updates(self.matrix)
        component.actual_update_median_ns = (
            float(statistics.median(update_times)) if update_times else 0.0
        )
        return component

    def _build_e4(self) -> GraphComponent:
        start = time.perf_counter()
        seen: dict[str, list[int]] = {}
        left_nodes: list[int] = []
        right_nodes: list[int] = []
        update_times = []
        for index, candidate in enumerate(self.candidates):
            update_start = time.perf_counter_ns()
            topic = candidate.topic_id
            if topic:
                previous = seen.setdefault(topic, [])
                if previous:
                    left_nodes.extend(previous)
                    right_nodes.extend([index] * len(previous))
                previous.append(index)
            update_times.append(time.perf_counter_ns() - update_start)
        left_array = np.asarray(left_nodes, dtype=np.int32)
        right_array = np.asarray(right_nodes, dtype=np.int32)
        return self._component(
            "E4",
            left_array,
            right_array,
            np.ones(len(left_array), dtype=np.float32),
            start,
            update_times,
        )

    def _component(
        self,
        component_id: str,
        left_nodes: np.ndarray,
        right_nodes: np.ndarray,
        weights: np.ndarray,
        start: float,
        update_times: list[int],
    ) -> GraphComponent:
        node_count = len(self.candidates)
        transition = _transition_from_undirected_edges(
            node_count,
            left_nodes,
            right_nodes,
            weights,
        )
        edge_count = len(left_nodes)
        possible = node_count * (node_count - 1) / 2
        component_sizes = _component_sizes(
            node_count,
            left_nodes,
            right_nodes,
        )
        component = GraphComponent(
            component_id=component_id,
            transition=transition,
            undirected_edge_count=edge_count,
            density=edge_count / possible if possible else 0.0,
            connected_component_count=len(component_sizes),
            largest_component_size=max(component_sizes, default=0),
            isolated_node_count=sum(size == 1 for size in component_sizes),
            build_ms=(time.perf_counter() - start) * 1000.0,
            actual_update_median_ns=(
                float(statistics.median(update_times))
                if update_times
                else 0.0
            ),
        )
        return component


class GraphRetriever:
    def __init__(
        self,
        graph: AssociativeGraphIndex,
        embedder,
    ) -> None:
        self.graph = graph
        self.embedder = embedder

    def retrieve(
        self,
        config_id: str,
        depth: int,
        query: Query,
        *,
        budget: int = DEFAULT_BUDGET,
        repetitions: int = 9,
    ) -> RetrievalResult:
        if depth not in {1, 2, 3}:
            raise ValueError("Graph depth must be 1, 2, or 3")
        if repetitions < 1:
            raise ValueError("repetitions must be positive")
        transition = self.graph.transition_for(config_id)
        method_id = f"G_{config_id}_d{depth}"

        encode_start = time.perf_counter()
        query_vector = normalize_embedding(self.embedder(query.text))
        encode_ms = (time.perf_counter() - encode_start) * 1000.0

        warm_ranked = self._rank(transition, depth, query_vector)
        warm_pack = pack_ranked_candidates(
            method_id,
            [(item, "fill") for item in warm_ranked],
            budget,
        )
        rank_times = []
        pack_times = []
        combined_times = []
        final_ranked = warm_ranked
        final_pack = warm_pack
        for _ in range(repetitions):
            repetition_start = time.perf_counter()
            rank_start = repetition_start
            ranked = self._rank(transition, depth, query_vector)
            rank_ms = (time.perf_counter() - rank_start) * 1000.0
            pack_start = time.perf_counter()
            packed = pack_ranked_candidates(
                method_id,
                [(item, "fill") for item in ranked],
                budget,
            )
            pack_ms = (time.perf_counter() - pack_start) * 1000.0
            combined_ms = (time.perf_counter() - repetition_start) * 1000.0
            if packed.rendered_block != warm_pack.rendered_block:
                raise AssertionError("Graph retrieval changed across repetitions")
            rank_times.append(rank_ms)
            pack_times.append(pack_ms)
            combined_times.append(combined_ms)
            final_ranked = ranked
            final_pack = packed
        return RetrievalResult(
            corpus_id=self.graph.spec.corpus_id,
            method_id=method_id,
            query=query,
            budget=budget,
            ranked_count=len(final_ranked),
            selected=final_pack.selected,
            rendered_block=final_pack.rendered_block,
            phases=final_pack.phases,
            skipped_oversized=final_pack.skipped_oversized,
            duplicate_drops=final_pack.duplicate_drops,
            query_encode_ms=encode_ms,
            rank_ms=statistics.median(rank_times),
            pack_ms=statistics.median(pack_times),
            rank_pack_ms=statistics.median(combined_times),
            index_build_ms=self.graph.config_build_ms(config_id),
            benchmark_repetitions=repetitions,
        )

    def _rank(
        self,
        transition: GraphTransition,
        depth: int,
        query_vector: np.ndarray,
    ) -> list[RankedCandidate]:
        cosine = self.graph.matrix @ query_vector
        order = np.lexsort((self.graph.id_rank, -cosine))
        seed_indices = order[: min(8, len(order))]
        seed_weights = np.maximum(cosine[seed_indices], 0.0).astype(
            np.float64
        )
        if float(np.sum(seed_weights)) <= 0:
            seed_weights = np.ones(len(seed_indices), dtype=np.float64)
        seed_weights /= np.sum(seed_weights)
        seed = np.zeros(len(order), dtype=np.float64)
        seed[seed_indices] = seed_weights
        activation = seed
        for _ in range(depth):
            activation = 0.15 * seed + 0.85 * transition.propagate(
                activation
            )
        ranked = [
            RankedCandidate(
                candidate=candidate,
                score=float(activation[index]),
                component_scores={
                    "activation": float(activation[index]),
                    "raw_cosine": float(cosine[index]),
                },
            )
            for index, candidate in enumerate(self.graph.candidates)
        ]
        ranked.sort(
            key=lambda item: (
                -item.score,
                -item.component_scores["raw_cosine"],
                item.candidate.candidate_id,
            )
        )
        return ranked


def _transition_from_undirected_edges(
    node_count: int,
    left_nodes: np.ndarray,
    right_nodes: np.ndarray,
    edge_weights: np.ndarray,
) -> GraphTransition:
    if not (len(left_nodes) == len(right_nodes) == len(edge_weights)):
        raise ValueError("Undirected graph edge arrays must have equal lengths")
    if not len(left_nodes):
        return GraphTransition(
            source=np.empty(0, dtype=np.int32),
            destination=np.empty(0, dtype=np.int32),
            probability=np.empty(0, dtype=np.float32),
            node_count=node_count,
        )
    source = np.concatenate((left_nodes, right_nodes)).astype(
        np.int32,
        copy=False,
    )
    destination = np.concatenate((right_nodes, left_nodes)).astype(
        np.int32,
        copy=False,
    )
    directed_weights = np.concatenate((edge_weights, edge_weights)).astype(
        np.float32,
        copy=False,
    )
    row_sums = np.bincount(
        source,
        weights=directed_weights,
        minlength=node_count,
    )
    probability = (directed_weights / row_sums[source]).astype(
        np.float32,
        copy=False,
    )
    return GraphTransition(
        source=source,
        destination=destination,
        probability=probability,
        node_count=node_count,
    )


def _edge_mapping_arrays(
    edges: dict[tuple[int, int], float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ordered = sorted(edges.items())
    return (
        np.asarray([edge[0][0] for edge in ordered], dtype=np.int32),
        np.asarray([edge[0][1] for edge in ordered], dtype=np.int32),
        np.asarray([edge[1] for edge in ordered], dtype=np.float32),
    )


def _component_sizes(
    node_count: int,
    left_nodes: np.ndarray,
    right_nodes: np.ndarray,
) -> list[int]:
    parent = np.arange(node_count, dtype=np.int32)
    sizes = np.ones(node_count, dtype=np.int32)

    def find(index: int) -> int:
        root = index
        while parent[root] != root:
            root = int(parent[root])
        while parent[index] != index:
            next_index = int(parent[index])
            parent[index] = root
            index = next_index
        return root

    for left, right in zip(left_nodes, right_nodes, strict=True):
        left_root = find(int(left))
        right_root = find(int(right))
        if left_root == right_root:
            continue
        if sizes[left_root] < sizes[right_root]:
            left_root, right_root = right_root, left_root
        parent[right_root] = left_root
        sizes[left_root] += sizes[right_root]
    roots = [index for index in range(node_count) if find(index) == index]
    return sorted((int(sizes[root]) for root in roots), reverse=True)


def _parse_historical_contexts(
    spec: CorpusSpec,
    candidates: list[Candidate],
) -> list[list[int]]:
    by_turn: dict[int, list[int]] = {}
    for index, candidate in enumerate(candidates):
        by_turn.setdefault(candidate.turn_number, []).append(index)
    ambiguous = [turn for turn, indices in by_turn.items() if len(indices) != 1]
    if ambiguous:
        raise AssertionError(f"Ambiguous raw episode turns: {ambiguous[:5]}")

    prompt_root = spec.run_directory / "constructed_prompts"
    contexts = []
    for turn in range(spec.eligible_turn_min, spec.eligible_turn_max + 1):
        path = prompt_root / f"turn_{turn:03d}.txt"
        if not path.is_file():
            raise FileNotFoundError(path)
        prompt = path.read_text(encoding="utf-8")
        indices: set[int] = set()
        for match in _BLOCK.finditer(prompt):
            root = ET.fromstring(match.group(0))
            for element in root:
                if element.tag == "episode":
                    attribute = "turn"
                elif element.tag == "span":
                    attribute = "source_turn"
                else:
                    raise AssertionError(
                        f"Unexpected context element {element.tag} in {path}"
                    )
                if attribute not in element.attrib:
                    raise AssertionError(
                        f"Missing {attribute} on {element.tag} in {path}"
                    )
                source_turn = int(element.attrib[attribute])
                if source_turn not in by_turn:
                    raise AssertionError(
                        f"Unresolvable source turn {source_turn} in {path}"
                    )
                indices.add(by_turn[source_turn][0])
        contexts.append(sorted(indices))
    return contexts


def _replay_e3_updates(matrix: np.ndarray) -> list[int]:
    size = len(matrix)
    retained = np.full((size, 8), -np.inf, dtype=np.float32)
    times = []
    for index in range(1, size):
        start = time.perf_counter_ns()
        scores = matrix[:index] @ matrix[index]
        neighbor_count = min(8, index)
        if neighbor_count:
            top = np.argpartition(scores, -neighbor_count)[-neighbor_count:]
            retained[index, -neighbor_count:] = np.sort(scores[top])
        entering = scores > retained[:index, 0]
        if np.any(entering):
            entering_indices = np.flatnonzero(entering)
            retained[entering_indices, 0] = scores[entering_indices]
            retained[entering_indices] = np.sort(
                retained[entering_indices],
                axis=1,
            )
        times.append(time.perf_counter_ns() - start)
    return times

"""Evidence-blind candidate granularity mechanism for TC-004.

The module deliberately has no measurement adapter.  It receives source text,
stable ordering keys, vectors, and a character budget; it returns selections.
Labels are joined only in a later sealed stage.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from analysis.tc004_preflight import ParentUnit
from episodic._packing import EMPTY_PAYLOAD_CHARS
from episodic._render import render_episode_element, render_stm_payload

SPLIT_RATES = (0.0, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.0)
_TOKEN = re.compile(r"[a-z0-9]+")


class TC004MechanismError(RuntimeError):
    pass


@dataclass(frozen=True)
class OfferedUnit:
    identity: str
    parent_index: int
    dialog_ids: tuple[str, ...]
    score: float
    session_order: int
    pair_order: int
    child_offset: int
    record: dict
    rendered: str


@dataclass(frozen=True)
class Selection:
    selected_ids: tuple[str, ...]
    delivered_dialog_ids: frozenset[str]
    serialized_chars: int
    payload_sha256: str


def unit(vector: np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(value))
    if value.shape != (1024,) or not math.isfinite(norm) or norm == 0.0:
        raise TC004MechanismError("Expected one finite non-zero 1024-vector")
    return value / norm


def cosine_maps(
    parents: Sequence[ParentUnit],
    query_vector: np.ndarray,
    child_vectors: Mapping[str, np.ndarray],
) -> tuple[dict[str, float], dict[str, float]]:
    """Own-vector scores using the carried float32 matrix-vector call shape."""

    query = unit(query_vector)
    parent_matrix = np.stack(
        [unit(np.asarray(parent.episode.record["embedding"])) for parent in parents]
    )
    parent_values = parent_matrix @ query
    parent_scores = {
        parent.episode.identity: float(parent_values[index])
        for index, parent in enumerate(parents)
    }
    children = [child for parent in parents for child in parent.children]
    child_matrix = np.stack([unit(child_vectors[child.text]) for child in children])
    child_values = child_matrix @ query
    child_scores = {
        child.identity: float(child_values[index])
        for index, child in enumerate(children)
    }
    return parent_scores, child_scores


def offered_units(
    parents: Sequence[ParentUnit],
    parent_scores: Mapping[str, float],
    child_scores: Mapping[str, float],
    split_parents: Sequence[int],
) -> tuple[OfferedUnit, ...]:
    split = frozenset(split_parents)
    if any(index < 0 or index >= len(parents) for index in split):
        raise TC004MechanismError("Split parent index is out of range")
    if any(not parents[index].splittable for index in split):
        raise TC004MechanismError("Singleton parents cannot split")
    offered: list[OfferedUnit] = []
    for parent in parents:
        pair = parent.episode.pair
        if parent.index not in split:
            record = parent.episode.record
            offered.append(
                OfferedUnit(
                    parent.episode.identity,
                    parent.index,
                    pair.dialog_ids,
                    float(parent_scores[parent.episode.identity]),
                    pair.session_order,
                    pair.pair_order,
                    -1,
                    record,
                    render_episode_element(record),
                )
            )
        else:
            for child in parent.children:
                offered.append(
                    OfferedUnit(
                        child.identity,
                        parent.index,
                        (child.dialog_id,),
                        float(child_scores[child.identity]),
                        pair.session_order,
                        pair.pair_order,
                        child.offset,
                        child.record,
                        render_episode_element(child.record),
                    )
                )
    if any(not math.isfinite(unit_.score) for unit_ in offered):
        raise TC004MechanismError("Candidate scores must be finite")
    offered.sort(
        key=lambda value: (
            -value.score,
            value.session_order,
            value.pair_order,
            value.child_offset,
        )
    )
    return tuple(offered)


def exact_incremental_pack(ranked: Sequence[OfferedUnit], budget: int) -> Selection:
    """Exact skip-on-overflow packing with additive renderer accounting.

    The committed packer repeatedly serializes the complete payload after each
    offer.  The renderer is additive for one non-empty retrieved block, so this
    implementation computes the same admission predicate and serializes once.
    G4 compares it to ``pack_stm_payload`` on real and planted overflow traces.
    """

    if budget < EMPTY_PAYLOAD_CHARS:
        payload = ""
        return Selection((), frozenset(), 0, hashlib.sha256(b"").hexdigest())
    selected: list[OfferedUnit] = []
    empty_chars = EMPTY_PAYLOAD_CHARS
    nonempty_fixed = len(render_stm_payload([], [{}])) - len(
        render_episode_element({})
    )
    used = empty_chars
    for candidate in ranked:
        proposed = (
            nonempty_fixed + len(candidate.rendered)
            if not selected
            else used + 1 + len(candidate.rendered)
        )
        if proposed <= budget:
            selected.append(candidate)
            used = proposed
    records = [candidate.record for candidate in selected]
    payload = render_stm_payload([], records)
    if len(payload) != used or len(payload) > budget:
        raise TC004MechanismError("Incremental charge diverged from serialization")
    return Selection(
        tuple(candidate.identity for candidate in selected),
        frozenset(
            dialog_id for candidate in selected for dialog_id in candidate.dialog_ids
        ),
        len(payload),
        hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    )


def select(
    parents: Sequence[ParentUnit],
    parent_scores: Mapping[str, float],
    child_scores: Mapping[str, float],
    split_parents: Sequence[int],
    budget: int,
) -> Selection:
    return exact_incremental_pack(
        offered_units(parents, parent_scores, child_scores, split_parents), budget
    )


def _lexical_cosine(left: str, right: str) -> float:
    left_counts = Counter(_TOKEN.findall(left.casefold()))
    right_counts = Counter(_TOKEN.findall(right.casefold()))
    if not left_counts or not right_counts:
        return 0.0
    numerator = sum(value * right_counts[token] for token, value in left_counts.items())
    left_norm = math.sqrt(sum(value * value for value in left_counts.values()))
    right_norm = math.sqrt(sum(value * value for value in right_counts.values()))
    return numerator / (left_norm * right_norm)


def predictor_scores(
    parents: Sequence[ParentUnit],
    parent_scores: Mapping[str, float],
    child_scores: Mapping[str, float],
    query_text: str,
) -> dict[str, dict[int, float]]:
    result = {
        "embedding_localization_gain": {},
        "length": {},
        "lexical_localization_gain": {},
    }
    for parent in parents:
        if not parent.splittable:
            continue
        result["embedding_localization_gain"][parent.index] = (
            max(child_scores[child.identity] for child in parent.children)
            - parent_scores[parent.episode.identity]
        )
        result["length"][parent.index] = float(len(parent.episode.pair.text))
        result["lexical_localization_gain"][parent.index] = (
            max(_lexical_cosine(query_text, child.text) for child in parent.children)
            - _lexical_cosine(query_text, parent.episode.pair.text)
        )
    return result


def policy_order(parents: Sequence[ParentUnit], scores: Mapping[int, float]) -> tuple[int, ...]:
    return tuple(
        sorted(
            scores,
            key=lambda index: (
                -float(scores[index]),
                parents[index].episode.pair.session_order,
                parents[index].episode.pair.pair_order,
            ),
        )
    )


def split_count(rate: float, candidates: int) -> int:
    if rate == 0.0:
        return 0
    if rate == 1.0:
        return candidates
    return min(candidates, math.ceil(rate * candidates))


__all__ = [
    "SPLIT_RATES",
    "OfferedUnit",
    "Selection",
    "TC004MechanismError",
    "cosine_maps",
    "exact_incremental_pack",
    "offered_units",
    "policy_order",
    "predictor_scores",
    "select",
    "split_count",
]

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np


FORBIDDEN_MECHANISM_PATH_PARTS = (
    "answer_key",
    "q_facts_key",
    "rubric",
    "atomic_items",
    "targeted_items",
    "scoring",
)


@dataclass(frozen=True)
class Admission:
    content_sha256: str
    source_turn: int
    role: str
    parent_seed_sha256: str
    parent_seed_rank: int
    temporal_distance: int


@dataclass(frozen=True)
class BridgeResult:
    candidates: tuple[Mapping[str, object], ...]
    admissions: tuple[Admission, ...]
    skipped_duplicates: tuple[dict[str, object], ...]


def assert_mechanism_path_allowed(path: str | Path) -> None:
    normalized = str(path).replace("\\", "/").lower()
    if any(part in normalized for part in FORBIDDEN_MECHANISM_PATH_PARTS):
        raise ValueError(f"Mechanism path crosses the measurement boundary: {path}")


def content_sha256(episode: Mapping[str, object]) -> str:
    stable = {
        "assistant_message": str(episode["assistant_message"]),
        "turn_number": int(episode["turn_number"]),
        "user_message": str(episode["user_message"]),
    }
    encoded = json.dumps(
        stable,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def rank_by_query(
    episodes: Sequence[Mapping[str, object]],
    query_vector: np.ndarray,
) -> tuple[Mapping[str, object], ...]:
    if not episodes:
        raise ValueError("At least one eligible episode is required")
    query = np.asarray(query_vector, dtype=np.float64)
    if query.ndim != 1 or not np.all(np.isfinite(query)):
        raise ValueError("Query vector must be one finite dimension")
    query_norm = float(np.linalg.norm(query))
    if query_norm == 0.0:
        raise ValueError("Query vector must be non-zero")
    query = query / query_norm

    scored = []
    for episode in episodes:
        vector = np.frombuffer(episode["embedding"], dtype=np.float32).astype(
            np.float64
        )
        if vector.shape != query.shape:
            raise ValueError("Episode and query dimensions differ")
        norm = float(np.linalg.norm(vector))
        if norm == 0.0 or not np.isfinite(norm):
            raise ValueError("Episode vector must be finite and non-zero")
        scored.append(
            (
                -float((vector / norm) @ query),
                content_sha256(episode),
                episode,
            )
        )
    scored.sort(key=lambda row: (row[0], row[1]))
    return tuple(row[2] for row in scored)


def fixed_query_candidates(
    ranked_episodes: Sequence[Mapping[str, object]],
    *,
    quota: int = 15,
) -> tuple[Mapping[str, object], ...]:
    if quota <= 0:
        raise ValueError("Candidate quota must be positive")
    if len(ranked_episodes) < quota:
        raise ValueError("Candidate quota exceeds eligible episode count")
    selected = tuple(ranked_episodes[:quota])
    hashes = tuple(content_sha256(episode) for episode in selected)
    if len(set(hashes)) != quota:
        raise ValueError("Fixed-query prefix contains duplicate episode content")
    return selected


def temporal_adjacency_bridge(
    ranked_episodes: Sequence[Mapping[str, object]],
    *,
    quota: int = 15,
    radius: int = 1,
) -> BridgeResult:
    if quota <= 0:
        raise ValueError("Candidate quota must be positive")
    if radius != 1:
        raise ValueError("TA-001 registers radius exactly one")
    if len(ranked_episodes) < quota:
        raise ValueError("Candidate quota exceeds eligible episode count")

    by_turn: dict[int, list[Mapping[str, object]]] = {}
    all_hashes: set[str] = set()
    for episode in ranked_episodes:
        digest = content_sha256(episode)
        if digest in all_hashes:
            raise ValueError("Eligible population contains duplicate episode content")
        all_hashes.add(digest)
        by_turn.setdefault(int(episode["turn_number"]), []).append(episode)
    for episodes in by_turn.values():
        episodes.sort(key=content_sha256)

    candidates: list[Mapping[str, object]] = []
    admissions: list[Admission] = []
    skipped: list[dict[str, object]] = []
    admitted: set[str] = set()

    def admit(
        episode: Mapping[str, object],
        *,
        role: str,
        parent_hash: str,
        parent_rank: int,
        distance: int,
    ) -> bool:
        digest = content_sha256(episode)
        if digest in admitted:
            skipped.append(
                {
                    "content_sha256": digest,
                    "source_turn": int(episode["turn_number"]),
                    "role": role,
                    "parent_seed_sha256": parent_hash,
                    "parent_seed_rank": parent_rank,
                    "reason": "already_admitted",
                }
            )
            return False
        admitted.add(digest)
        candidates.append(episode)
        admissions.append(
            Admission(
                content_sha256=digest,
                source_turn=int(episode["turn_number"]),
                role=role,
                parent_seed_sha256=parent_hash,
                parent_seed_rank=parent_rank,
                temporal_distance=distance,
            )
        )
        return True

    for seed_rank, seed in enumerate(ranked_episodes, start=1):
        seed_hash = content_sha256(seed)
        if seed_hash in admitted:
            skipped.append(
                {
                    "content_sha256": seed_hash,
                    "source_turn": int(seed["turn_number"]),
                    "role": "seed",
                    "parent_seed_sha256": seed_hash,
                    "parent_seed_rank": seed_rank,
                    "reason": "seed_already_admitted_as_neighbor",
                }
            )
            continue
        admit(
            seed,
            role="seed",
            parent_hash=seed_hash,
            parent_rank=seed_rank,
            distance=0,
        )
        if len(candidates) == quota:
            break

        seed_turn = int(seed["turn_number"])
        neighbors = [
            episode
            for turn in (seed_turn - 1, seed_turn + 1)
            for episode in by_turn.get(turn, ())
            if content_sha256(episode) not in admitted
        ]
        neighbors.sort(key=content_sha256)
        for neighbor in neighbors:
            neighbor_turn = int(neighbor["turn_number"])
            admit(
                neighbor,
                role="previous" if neighbor_turn < seed_turn else "next",
                parent_hash=seed_hash,
                parent_rank=seed_rank,
                distance=abs(neighbor_turn - seed_turn),
            )
            if len(candidates) == quota:
                break
        if len(candidates) == quota:
            break

    if len(candidates) != quota:
        raise RuntimeError("Temporal bridge exhausted candidates before quota")
    return BridgeResult(
        candidates=tuple(candidates),
        admissions=tuple(admissions),
        skipped_duplicates=tuple(skipped),
    )


def digest_sequence(values: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(values).encode("ascii")).hexdigest()

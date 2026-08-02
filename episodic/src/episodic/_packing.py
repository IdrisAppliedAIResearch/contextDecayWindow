"""N-first packing at exact serialized cost, moved verbatim.

From the source repository's `src/memory/context_matched_stm.py`
(DR-001 lineage): recency-tier candidates are considered before
similarity-tier candidates, every admission is charged the exact
serialized length of the full two-block payload, and a candidate that
does not fit is skipped rather than truncated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ._render import render_stm_payload


@dataclass(frozen=True)
class PackedStmPayload:
    recent_episodes: tuple[dict, ...]
    stm_episodes: tuple[dict, ...]
    payload: str
    skipped_n_ids: tuple[str, ...] = ()
    skipped_k_ids: tuple[str, ...] = ()
    duplicate_ids: tuple[str, ...] = ()

    @property
    def serialized_chars(self) -> int:
        return len(self.payload)

    @property
    def selected_ids(self) -> tuple[str, ...]:
        return tuple(
            str(episode["id"])
            for episode in (*self.recent_episodes, *self.stm_episodes)
        )


def pack_stm_payload(
    n_candidates: Iterable[dict],
    k_candidates: Iterable[dict],
    budget: int,
) -> PackedStmPayload:
    if budget < len(render_stm_payload([], [])):
        raise ValueError("Payload budget cannot fit the two empty STM blocks")

    recent: list[dict] = []
    stm: list[dict] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    skipped_n: list[str] = []
    skipped_k: list[str] = []

    def consider(candidate: dict, *, tier: str) -> None:
        candidate_id = str(candidate["id"])
        if candidate_id in seen:
            duplicates.append(candidate_id)
            return
        target = recent if tier == "n" else stm
        target.append(candidate)
        payload = render_stm_payload(recent, stm)
        if len(payload) <= budget:
            seen.add(candidate_id)
            return
        target.pop()
        if tier == "n":
            skipped_n.append(candidate_id)
        else:
            skipped_k.append(candidate_id)

    for candidate in n_candidates:
        consider(candidate, tier="n")
    for candidate in k_candidates:
        consider(candidate, tier="k")

    payload = render_stm_payload(recent, stm)
    if len(payload) > budget:
        raise AssertionError("STM payload exceeded its character budget")
    return PackedStmPayload(
        recent_episodes=tuple(recent),
        stm_episodes=tuple(stm),
        payload=payload,
        skipped_n_ids=tuple(skipped_n),
        skipped_k_ids=tuple(skipped_k),
        duplicate_ids=tuple(duplicates),
    )

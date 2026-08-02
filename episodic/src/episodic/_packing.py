"""N-first packing at exact serialized cost, moved verbatim.

From the source repository's `src/memory/context_matched_stm.py`
(DR-001 lineage): recency-tier candidates are considered before
similarity-tier candidates, every admission is charged the exact
serialized length of the full two-block payload, and a candidate that
does not fit is skipped rather than truncated.

CC-003 adds no new packing behaviour. It names the existing one as a
policy (`DROP_POLICY`), and it removes the one budget at which this
function used to raise instead of degrading.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ._render import render_stm_payload

#: Cost of the two empty block tags. No non-empty payload is cheaper, so a
#: budget below this cannot express any answer at all - not even "nothing
#: was retrieved".
EMPTY_PAYLOAD_CHARS = len(render_stm_payload([], []))

#: The drop order, named. CC-003 requires that what gets dropped be a
#: documented policy rather than an artifact of iteration order, and this
#: is that document.
#:
#: Candidates arrive in tier order - the recency window first, then the
#: K-threshold hits, then the coverage selection in the A3 selector's own
#: descending marginal-gain order. Each is charged the exact serialized
#: cost of the *whole* two-block payload as it would be with that
#: candidate added, and admitted only if the result still fits. A
#: candidate that does not fit is skipped and the walk continues.
#:
#: Skipping rather than stopping is deliberate, and it is not the same
#: policy as "drop the lowest marginal gain first". With gains [10, 9, 8]
#: where the budget fits the second and third but not the first, this
#: admits 9 and 8; strict rank-prefix would keep only 10 and leave the
#: budget mostly empty. Skipping delivers more of the objective's value
#: per character, and it is what produced every committed number in the
#: source repository - including the E005 primary at 31,569 of 32,000
#: characters that CC-002's T3 certifies byte-for-byte. Determinism comes
#: from the selector's tie-breaks (scaled gain, then cost, then source
#: turn, then id), not from dictionary or set ordering.
DROP_POLICY = "marginal_gain_order_skip_on_overflow"


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
    n_candidates = list(n_candidates)
    k_candidates = list(k_candidates)

    if budget < EMPTY_PAYLOAD_CHARS:
        # Below the cost of the empty tags there is no payload to return,
        # so return none. This used to raise, which made the ceiling
        # conditional on the caller having chosen a sensible budget - a
        # hard ceiling with an exception at the bottom is not a hard
        # ceiling (CC-003 requirement 1.2.4).
        return PackedStmPayload(
            recent_episodes=(),
            stm_episodes=(),
            payload="",
            skipped_n_ids=tuple(
                str(candidate["id"]) for candidate in n_candidates
            ),
            skipped_k_ids=tuple(
                str(candidate["id"]) for candidate in k_candidates
            ),
        )

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

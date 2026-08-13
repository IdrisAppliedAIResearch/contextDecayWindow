from __future__ import annotations

import numpy as np

from analysis.locomo_nf_development import (
    PairCandidate,
    pack_indices,
    ranking_orders,
)


def pair(session: str, session_order: int, pair_order: int, chars: int) -> PairCandidate:
    return PairCandidate(
        identity=f"{session}-{pair_order}",
        sample_id="dev",
        session_id=session,
        session_order=session_order,
        pair_order=pair_order,
        text=f"text-{session}-{pair_order}",
        chars=chars,
        dialog_ids=(f"D{session}:{pair_order}",),
    )


def test_session_arm_inherits_the_best_pair_score() -> None:
    pairs = (pair("s1", 0, 0, 10), pair("s1", 0, 1, 10), pair("s2", 1, 0, 10))
    session, episode = ranking_orders(pairs, np.array([0.1, 0.9, 0.8]))
    assert session == [0, 1, 2]
    assert episode == [1, 2, 0]


def test_skip_on_overflow_keeps_scanning() -> None:
    pairs = (pair("s1", 0, 0, 8), pair("s2", 1, 0, 15), pair("s3", 2, 0, 2))
    delivered, used = pack_indices(pairs, [0, 1, 2], budget=10)
    assert delivered == [0, 2]
    assert used == 10

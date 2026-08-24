from __future__ import annotations

import numpy as np
import pytest

from analysis.locomo_nf_development import PairCandidate
from analysis.tc001_exploration import build_episodes, flat_order
from analysis.tc005_exploration import (
    candidates_for,
    pack_order,
    rank_all,
    surface_class,
)
from retrieval_bakeoff.config import RRF_CONSTANT
from retrieval_bakeoff.methods import BM25Index
from analysis.tc005_reachability import (
    TC005ReachabilityError,
    _forbid_labelled_outcomes,
    _one_sided_extreme_p,
)


class _Case:
    sample_id = "dev"

    def __init__(self, pairs):
        self.pairs = tuple(pairs)


def _episodes(texts: list[str], vectors: list[np.ndarray]):
    pairs = [
        PairCandidate(
            identity=f"id-{index}",
            sample_id="dev",
            session_id=f"session_{index // 2 + 1}",
            session_order=index // 2,
            pair_order=index % 2,
            text=text,
            chars=len(text),
            dialog_ids=(f"D{index}",),
        )
        for index, text in enumerate(texts)
    ]
    return build_episodes(
        _Case(pairs),
        {text: np.asarray(vector, dtype=np.float32) for text, vector in zip(texts, vectors, strict=True)},
    )


def _v(x: float, y: float) -> np.ndarray:
    return np.asarray([x, y] + [0.0] * 1022, dtype=np.float32)


def test_candidate_adapter_preserves_text_and_identity() -> None:
    episodes = _episodes(["Alice: one\nBob: two"], [_v(1, 0)])
    candidate = candidates_for(episodes)[0]
    assert candidate.candidate_id == "id-0"
    assert candidate.searchable_text == episodes[0].pair.text


def test_dense_is_tc001_cosine_with_conversation_ties() -> None:
    episodes = _episodes(
        ["u: alpha\na: red", "u: beta\na: blue", "u: alpha\na: green"],
        [_v(1, 0), _v(0, 1), _v(1, 0)],
    )
    rankings = rank_all(episodes, "alpha", _v(1, 0))
    assert rankings["dense"].order == flat_order(episodes, _v(1, 0)) == (0, 2, 1)


def test_bm25_uses_carried_scores_but_common_tie_break() -> None:
    episodes = _episodes(
        ["u: alpha\na: red", "u: beta\na: blue", "u: alpha\na: green"],
        [_v(1, 0), _v(0, 1), _v(0, 1)],
    )
    rankings = rank_all(episodes, "alpha", _v(1, 0))
    scores = BM25Index(list(candidates_for(episodes))).scores("alpha")
    expected = tuple(sorted(range(3), key=lambda index: (-scores[index], index)))
    assert rankings["bm25"].order == expected


def test_hybrid_is_rrf_not_score_averaging() -> None:
    episodes = _episodes(
        ["u: alpha\na: one", "u: beta\na: alpha", "u: gamma\na: three"],
        [_v(1, 0), _v(0.8, 0.2), _v(0, 1)],
    )
    rankings = rank_all(episodes, "alpha", _v(1, 0))
    dense_rank = rankings["hybrid"].dense_rank
    bm25_rank = rankings["hybrid"].bm25_rank
    expected_scores = tuple(
        1 / (RRF_CONSTANT + dense_rank[i]) + 1 / (RRF_CONSTANT + bm25_rank[i])
        for i in range(3)
    )
    assert rankings["hybrid"].scores == expected_scores


def test_packer_skips_overflow_and_continues() -> None:
    episodes = _episodes(
        ["u: " + "x" * 2_000, "u: short", "u: also short"],
        [_v(1, 0), _v(0, 1), _v(0, 1)],
    )
    packed = pack_order(episodes, (0, 1, 2), 500)
    assert packed.selected_ids == ("id-1", "id-2")
    assert packed.skipped_ids == ("id-0",)


def test_surface_class_is_question_visible_and_deterministic() -> None:
    assert surface_class("What was the S460ML limit?") == "surface_literal"
    assert surface_class("What did they decide about the bridge?") == "paraphrase"


def test_pf4_extreme_sign_probability_is_reachable_arithmetic() -> None:
    assert _one_sided_extreme_p(10) == pytest.approx(2**-10)
    assert _one_sided_extreme_p(0) == 1.0


def test_pf4_refuses_labelled_directional_outcomes() -> None:
    _forbid_labelled_outcomes({"questions_with_set_difference": 5})
    with pytest.raises(TC005ReachabilityError):
        _forbid_labelled_outcomes({"gains": 5})

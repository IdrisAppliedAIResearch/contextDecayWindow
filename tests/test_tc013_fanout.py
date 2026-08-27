from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from analysis.tc011_spread import aspect_spread
from analysis.tc013_fanout import fanout_aspect, weighted_facet_overlap


def _episode(index: int, size: int = 8) -> SimpleNamespace:
    return SimpleNamespace(
        identity=f"e{index}",
        record={
            "id": f"e{index}",
            "turn_number": index,
            "user_message": "u" * size,
            "assistant_message": "a" * size,
            "embedding": np.asarray((1.0, 0.0), dtype=np.float32),
        },
    )


def test_single_parent_matches_first_frozen_aspect_choice() -> None:
    episodes = [_episode(index) for index in range(4)]
    facets = (
        frozenset({"noun:a", "event:x"}),
        frozenset({"noun:b", "event:x"}),
        frozenset({"noun:c", "number:3"}),
        frozenset({"noun:d"}),
    )
    idf = {facet: 1.0 for values in facets for facet in values}
    totals, overlap = weighted_facet_overlap(facets, idf)
    scores = np.asarray((1.0, 0.8, 0.7, 0.2), dtype=np.float64)
    expected = aspect_spread(
        episodes, facets, idf, scores, (0, 1, 2, 3), (0,), 10_000
    )
    actual = fanout_aspect(
        episodes, totals, overlap, scores, (0, 1, 2, 3), (0,), 10_000
    )
    assert actual.proposed == expected.order[:1]
    assert actual.marginal == expected.marginal[:1]


def test_each_parent_attempts_once_and_children_are_globally_unique() -> None:
    episodes = [_episode(index) for index in range(4)]
    facets = tuple(frozenset({f"noun:{value}"}) for value in "abcd")
    idf = {next(iter(values)): 1.0 for values in facets}
    totals, overlap = weighted_facet_overlap(facets, idf)
    trace = fanout_aspect(
        episodes,
        totals,
        overlap,
        np.asarray((1.0, 0.95, 0.9, 0.8)),
        (0, 1, 2, 3),
        (0, 1),
        10_000,
    )
    assert trace.parents == (0, 1)
    assert trace.proposed == (2, 3)
    assert trace.parent_for_child == (0, 1)
    assert trace.no_positive_child == trace.no_fitting_child == 0


def test_no_positive_and_no_fit_states_are_reachable() -> None:
    facets = (frozenset({"noun:a"}), frozenset({"noun:a"}))
    idf = {"noun:a": 1.0}
    totals, overlap = weighted_facet_overlap(facets, idf)
    no_positive = fanout_aspect(
        [_episode(0), _episode(1)],
        totals,
        overlap,
        np.asarray((1.0, 0.5)),
        (0, 1),
        (0,),
        10_000,
    )
    assert no_positive.proposed == ()
    assert no_positive.no_positive_child == 1

    no_fit = fanout_aspect(
        [_episode(0), _episode(1, size=10_000)],
        totals,
        overlap,
        np.asarray((1.0, 0.5)),
        (0, 1),
        (0,),
        1_000,
    )
    assert no_fit.proposed == ()
    assert no_fit.no_fitting_child == 1

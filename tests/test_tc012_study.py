from __future__ import annotations

import numpy as np

from analysis.tc012_dynamic import dynamic_scores, normalize_scores
from analysis.tc012_study import disposition


def _cell(good: bool) -> dict:
    return {
        "combined": {"gains": 3 if good else 1, "losses": 1 if good else 3},
        "targeted": {"gains": 1, "losses": 1 if good else 2},
        "breadth": {"gains": 2 if good else 0, "losses": 0 if good else 2},
        "breadth_identity": {"net_identities": 2 if good else -2},
        "conversation_nets": {"a": 1 if good else -1, "b": 1 if good else 0, "c": 0, "d": 0},
    }


def test_dynamic_matrix_recomparison_changes_scores() -> None:
    matrix = np.eye(3, dtype=np.float64)
    bm25 = np.asarray((0.0, 0.1, 0.2))
    first = dynamic_scores(matrix, np.asarray((1.0, 0.0, 0.0)), bm25)
    second = dynamic_scores(matrix, np.asarray((0.0, 1.0, 0.0)), bm25)
    assert not np.array_equal(first, second)
    assert np.array_equal(normalize_scores(np.asarray((2.0, 4.0))), np.asarray((0.0, 1.0)))


def test_disposition_reaches_all_registered_branches() -> None:
    good = {budget: _cell(True) for budget in ("16000", "32000")}
    bad = {budget: _cell(False) for budget in ("16000", "32000")}
    assert disposition(good, bad) == "DYNAMIC_PROMPT_WORKS"
    assert disposition(bad, good) == "DYNAMIC_PROMPT_CARRIES_SIGNAL"
    assert disposition(bad, bad) == "NO_DYNAMIC_PROMPT_SIGNAL"

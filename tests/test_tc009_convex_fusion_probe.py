from __future__ import annotations

import numpy as np
import pytest

from analysis.tc009_convex_fusion_probe import ConvexFusionProbeError, convex_scores, disposition, normalize_scores


def test_normalization_and_fixed_fusion() -> None:
    assert np.allclose(normalize_scores((2, 4, 6)), (0, 0.5, 1))
    assert np.allclose(convex_scores((0, 1, 2), (10, 30, 20)), (0, 0.6, 0.9))


def test_degenerate_range_rejected() -> None:
    with pytest.raises(ConvexFusionProbeError):
        normalize_scores((1, 1))


def test_disposition_requires_both_budgets_and_breadth_gain() -> None:
    good = {"combined": {"gains": 3, "losses": 1}, "targeted": {"gains": 1, "losses": 1}, "breadth": {"gains": 1, "losses": 0}, "breadth_identity": {"net_identities": 1}, "conversation_nets": {"a": 1, "b": 1, "c": 0, "d": 0}}
    cells = {"16000": good, "32000": {**good, "breadth_identity": {"net_identities": 0}}}
    assert disposition(cells)["status"] == "DESCRIPTIVE_POSITIVE_SIGNAL"
    cells["32000"] = {**good, "combined": {"gains": 1, "losses": 2}}
    assert disposition(cells)["status"] == "NO_POSITIVE_SIGNAL"

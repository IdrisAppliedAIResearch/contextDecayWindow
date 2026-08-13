from __future__ import annotations

from analysis.locomo_holdout_inventory import HOLDOUT_IDS
from analysis.locomo_nf_development import DEVELOPMENT_IDS


def test_locked_splits_are_disjoint_and_cover_ten_conversations() -> None:
    assert HOLDOUT_IDS.isdisjoint(DEVELOPMENT_IDS)
    assert len(HOLDOUT_IDS | DEVELOPMENT_IDS) == 10

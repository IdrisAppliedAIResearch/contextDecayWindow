from __future__ import annotations

import pytest

from analysis.tc015_opportunity_utility import (
    TC015OrderingError,
    opportunity_then_utility,
)


def test_sorts_only_retained_children_by_frozen_utility() -> None:
    result = opportunity_then_utility(
        ("a", "b", "c", "d"),
        (0.2, 0.9, 0.5, 0.1),
        ("a", "c", "d"),
    )
    assert result == ("c", "a", "d")
    assert set(result) == {"a", "c", "d"}


def test_utility_tie_preserves_parent_order() -> None:
    assert opportunity_then_utility(("b", "a"), (1.0, 1.0), ("a", "b")) == (
        "b",
        "a",
    )


@pytest.mark.parametrize(
    "assigned,utilities,retained",
    [
        ((), (), ()),
        (("a",), (), ("a",)),
        (("a", "a"), (1.0, 2.0), ("a",)),
        (("a",), (1.0,), ("b",)),
        (("a",), (float("nan"),), ("a",)),
    ],
)
def test_rejects_invalid_frozen_trace(assigned, utilities, retained) -> None:
    with pytest.raises(TC015OrderingError):
        opportunity_then_utility(assigned, utilities, retained)

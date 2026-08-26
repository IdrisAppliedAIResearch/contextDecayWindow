"""Label-blind opportunity-filtered utility ordering for TC-015."""

from __future__ import annotations

import math
from typing import Sequence


class TC015OrderingError(RuntimeError):
    pass


def opportunity_then_utility(
    assigned_children: Sequence[str],
    utilities: Sequence[float],
    retained_children: Sequence[str],
) -> tuple[str, ...]:
    """Sort TC-014's retained opportunity set by frozen edge utility.

    The retained set is immutable. Equal utilities preserve the original
    parent-order assignment, with content identity as a final deterministic
    tie breaker.
    """

    assigned = tuple(assigned_children)
    retained = tuple(retained_children)
    values = tuple(float(value) for value in utilities)
    if not assigned or len(assigned) != len(values):
        raise TC015OrderingError("assigned children and utilities must align")
    if len(assigned) != len(set(assigned)) or len(retained) != len(set(retained)):
        raise TC015OrderingError("child identities must be unique")
    if not set(retained) <= set(assigned):
        raise TC015OrderingError("retained children escaped the assigned set")
    if not all(math.isfinite(value) for value in values):
        raise TC015OrderingError("utilities must be finite")
    position = {identifier: index for index, identifier in enumerate(assigned)}
    utility = dict(zip(assigned, values, strict=True))
    return tuple(
        sorted(
            retained,
            key=lambda identifier: (
                -utility[identifier],
                position[identifier],
                identifier,
            ),
        )
    )


__all__ = ["TC015OrderingError", "opportunity_then_utility"]

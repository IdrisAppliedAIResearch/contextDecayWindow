from __future__ import annotations

from analysis.tc008_reachability import POPULATIONS, clears
from analysis.tc009_reachability import BANDS, SIGNAL_ALPHA, WORKS_ALPHA


def test_all_registered_directions_are_reachable() -> None:
    for bands in BANDS.values():
        for alpha in (WORKS_ALPHA, SIGNAL_ALPHA):
            assert any(
                clears(n, 0, bands["breadth_share_questions"], alpha)
                for n in range(1, POPULATIONS["breadth_share"] + 1)
            )
        for endpoint in ("combined_complete", "targeted_complete"):
            assert any(
                clears(n, 0, bands[endpoint], WORKS_ALPHA)
                for n in range(1, POPULATIONS[endpoint] + 1)
            )

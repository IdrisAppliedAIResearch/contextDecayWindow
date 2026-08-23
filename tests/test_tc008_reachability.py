from __future__ import annotations

from analysis.tc008_reachability import BANDS, POPULATIONS, SIGNAL_ALPHA, WORKS_ALPHA, clears, one_sided


def test_exact_sign_tail() -> None:
    assert one_sided(0, 0) == 1.0
    assert one_sided(10, 0) == 1 / 1024
    assert one_sided(0, 10) == 1.0


def test_strict_practical_band() -> None:
    assert not clears(2, 0, 2, 1.0)
    assert clears(3, 0, 2, 1.0)


def test_every_registered_cell_has_reachable_works_and_signal_counts() -> None:
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

from __future__ import annotations

import pytest

from src.analysis.e006_p3_offline import DOMAINS, primary_thresholds


def cell(
    arm: str,
    *,
    candidate: int,
    packed: int,
    chars: int,
    domains: int,
) -> dict:
    return {
        "arm": arm,
        "candidate_fact_count": candidate,
        "packed_fact_count": packed,
        "delivered_chars": chars,
        "candidate_per_domain": {domain: domains for domain in DOMAINS},
        "packed_per_domain": {domain: domains for domain in DOMAINS},
    }


@pytest.mark.parametrize(
    ("a2", "expected"),
    [
        (cell("A2", candidate=5, packed=5, chars=90, domains=1), "DIFFERENTIATED_OFFLINE_DELIVERY"),
        (cell("A2", candidate=5, packed=3, chars=90, domains=1), "REACH_ONLY_NOT_DELIVERED"),
        (cell("A2", candidate=5, packed=5, chars=110, domains=1), "VOLUME_CONSISTENT_PACKED_GAIN"),
        (cell("A2", candidate=3, packed=5, chars=90, domains=1), "NO_DIFFERENTIATED_CUE"),
    ],
)
def test_primary_dispositions_are_reachable(a2: dict, expected: str) -> None:
    controls = [
        cell("A0", candidate=4, packed=4, chars=100, domains=1),
        cell("A1", candidate=4, packed=4, chars=100, domains=1),
    ]

    assert primary_thresholds([*controls, a2])["disposition"] == expected

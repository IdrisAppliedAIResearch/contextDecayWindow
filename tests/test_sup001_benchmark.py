from __future__ import annotations

from src.analysis.sup001_benchmark import DOMAINS, build, canonical_digest


def test_registered_population_counts_and_unique_identities() -> None:
    mechanism, key = build()
    assert len(mechanism["episodes"]) == 256
    assert len(mechanism["registrations"]) == 192
    assert len(mechanism["queries"]) == 96
    assert len(key["history_queries"]) == 64
    assert len({row["episode_sha256"] for row in mechanism["episodes"]}) == 256


def test_updated_and_unchanged_counts_by_domain() -> None:
    _mechanism, key = build()
    rows = key["rows"]
    for domain in DOMAINS:
        assert sum(row["kind"] == "updated" and row["domain"] == domain for row in rows) == 16
        assert sum(row["kind"] == "unchanged" and row["domain"] == domain for row in rows) == 8


def test_every_updated_lineage_has_three_distinct_versions() -> None:
    _mechanism, key = build()
    for row in key["rows"]:
        if row["kind"] == "updated":
            assert len(row["lineage_sha256"]) == 3
            assert row["current_sha256"] == row["lineage_sha256"][-1]
            assert row["stale_sha256"] == row["lineage_sha256"][:-1]


def test_build_is_process_independent_and_canonical() -> None:
    first = build()
    second = build()
    assert canonical_digest(first) == canonical_digest(second)


from __future__ import annotations

import copy

import pytest

from src.biological_memory.supersession import (
    SupersessionError,
    SupersessionLedger,
)


def identity(value: int) -> str:
    return f"{value:064x}"


def three_version_ledger() -> SupersessionLedger:
    ledger = SupersessionLedger()
    ledger.register_initial("tea", identity(1))
    ledger.register_update("tea", identity(2), supersedes=identity(1))
    ledger.register_update("tea", identity(3), supersedes=identity(2))
    return ledger


def test_update_creates_one_accessible_leaf_and_reciprocal_lineage() -> None:
    ledger = three_version_ledger()
    rows = ledger.lineage("tea")
    assert [row.version for row in rows] == [1, 2, 3]
    assert [row.accessibility for row in rows] == [0.0, 0.0, 1.0]
    assert rows[0].superseded_by == rows[1].episode_sha256
    assert rows[2].supersedes == rows[1].episode_sha256
    assert ledger.validate() == {
        "record_count": 3,
        "lineage_count": 1,
        "accessible_count": 1,
        "silent_count": 2,
    }


def test_natural_rank_excludes_silent_versions_and_backfills() -> None:
    ledger = three_version_ledger()
    candidates = [
        {"episode_sha256": identity(1), "cosine": 0.99},
        {"episode_sha256": identity(2), "cosine": 0.98},
        {"episode_sha256": identity(3), "cosine": 0.80},
        {"episode_sha256": identity(4), "cosine": 0.70},
    ]
    selected = ledger.natural_rank(candidates, limit=2)
    assert [row["episode_sha256"] for row in selected] == [identity(3), identity(4)]


def test_unregistered_candidates_remain_accessible_and_reads_are_pure() -> None:
    ledger = three_version_ledger()
    before = copy.deepcopy(ledger.to_dict())
    assert ledger.accessibility(identity(99)) == 1.0
    ledger.lineage("tea")
    ledger.natural_rank([{"episode_sha256": identity(99), "cosine": 0.1}], limit=1)
    assert ledger.to_dict() == before


@pytest.mark.parametrize(
    "operation",
    [
        lambda ledger: ledger.register_initial("tea", identity(9)),
        lambda ledger: ledger.register_update("tea", identity(1), supersedes=identity(3)),
        lambda ledger: ledger.register_update("tea", identity(9), supersedes=identity(1)),
        lambda ledger: ledger.register_update("tea", identity(9), supersedes=identity(99)),
    ],
)
def test_duplicate_fork_and_unknown_parent_fail(operation) -> None:
    ledger = three_version_ledger()
    with pytest.raises(SupersessionError):
        operation(ledger)


def test_cross_key_update_fails() -> None:
    ledger = three_version_ledger()
    ledger.register_initial("coffee", identity(10))
    with pytest.raises(SupersessionError, match="Cross-key"):
        ledger.register_update("coffee", identity(11), supersedes=identity(3))


def test_serialized_round_trip_is_exact() -> None:
    ledger = three_version_ledger()
    assert SupersessionLedger.from_dict(ledger.to_dict()).to_dict() == ledger.to_dict()


def test_corrupt_serialized_cycle_fails() -> None:
    payload = three_version_ledger().to_dict()
    payload["lineages"]["tea"][0]["supersedes"] = identity(3)
    with pytest.raises(SupersessionError, match="reciprocal"):
        SupersessionLedger.from_dict(payload)


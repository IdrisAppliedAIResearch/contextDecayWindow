from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from analysis.nf004_measurement import paired_counts
from analysis.nf004_mechanism import Candidate, pack, ranking_orders, retrieve
from analysis.nf004_study import (
    NF004GateStop,
    REPO_ROOT,
    SOURCE_MANIFEST,
    SOURCE_MANIFEST_SHA256,
    _disposition,
    enforce_gate_order,
    leakage_gate,
    mechanism_violations,
    registration_identity,
)
from analysis.nf004_measurement import sha256_file


def candidate(
    identity: str,
    session: str,
    session_order: int,
    pair_order: int,
    chars: int = 10,
) -> Candidate:
    return Candidate(
        identity=identity,
        session_identity=session,
        session_order=session_order,
        pair_order=pair_order,
        text=identity,
        chars=chars,
    )


def vector(first: float, second: float = 0.0) -> np.ndarray:
    result = np.zeros(1024, dtype=np.float32)
    result[0] = first
    result[1] = second
    return result


def test_session_ranking_inherits_best_pair_but_pair_ranking_does_not() -> None:
    candidates = (
        candidate("s1-low", "s1", 0, 0),
        candidate("s1-high", "s1", 0, 1),
        candidate("s2-mid", "s2", 1, 0),
    )
    matrix = np.vstack((vector(0.1, 1.0), vector(1.0), vector(0.8, 0.6)))
    session, pair = ranking_orders(candidates, matrix, vector(1.0))
    assert session == (0, 1, 2)
    assert pair == (1, 2, 0)


def test_ranking_uses_cosine_not_vector_magnitude() -> None:
    candidates = (
        candidate("aligned", "s1", 0, 0),
        candidate("large-off-axis", "s2", 1, 0),
    )
    matrix = np.vstack((vector(1.0), vector(10.0, 100.0)))
    _, pair = ranking_orders(candidates, matrix, vector(1.0))
    assert pair == (0, 1)


def test_skip_on_overflow_continues_and_arms_pack_identical_candidates() -> None:
    candidates = (
        candidate("first", "s1", 0, 0, 8),
        candidate("overflow", "s2", 1, 0, 15),
        candidate("last", "s3", 2, 0, 2),
    )
    delivery = pack(candidates, (0, 1, 2), 10)
    assert delivery.selected == ("first", "last")
    assert delivery.packed_chars == 10

    matrix = np.vstack((vector(1.0), vector(0.8, 0.6), vector(0.6, 0.8)))
    arms = retrieve(candidates, matrix, vector(1.0), 10)
    assert set(arms) == {"S_SESSION_RANK", "P_PAIR_RANK"}
    assert all(set(row.order) == {"first", "overflow", "last"} for row in arms.values())


def test_mechanism_purity_rejects_planted_measurement_import() -> None:
    assert leakage_gate()["pass"]
    planted = "from analysis.nf004_measurement import adapt_split\n"
    assert mechanism_violations(planted) == [
        "forbidden import:analysis.nf004_measurement",
        "forbidden source reference:nf004_measurement",
    ]


@pytest.mark.parametrize("failure_index", range(6))
def test_each_preflight_failure_keeps_holdout_unreachable(
    failure_index: int,
) -> None:
    trace: list[str] = []

    def gate(index: int):
        def run() -> dict[str, bool]:
            trace.append(f"G{index}")
            return {"pass": index != failure_index}

        return run

    def holdout() -> None:
        trace.append("G6")

    with pytest.raises(NF004GateStop) as stopped:
        enforce_gate_order(
            tuple((f"G{index}", gate(index)) for index in range(6)), holdout
        )
    assert stopped.value.gate == f"G{failure_index}"
    assert "G6" not in trace
    assert trace == [f"G{index}" for index in range(failure_index + 1)]


def test_registration_identity_is_checked_before_corpus_access() -> None:
    result = registration_identity()
    assert result["pass"]
    assert result["corpus_accessed"] is False


def test_artifact_identity_uses_raw_bytes() -> None:
    assert sha256_file(REPO_ROOT / SOURCE_MANIFEST) == SOURCE_MANIFEST_SHA256


def comparison_rows(gains: int, losses: int, ties: int) -> list[dict]:
    rows = []
    for _ in range(gains):
        rows.append(
            {
                "arms": {
                    "S_SESSION_RANK": {"all_evidence": False},
                    "P_PAIR_RANK": {"all_evidence": True},
                }
            }
        )
    for _ in range(losses):
        rows.append(
            {
                "arms": {
                    "S_SESSION_RANK": {"all_evidence": True},
                    "P_PAIR_RANK": {"all_evidence": False},
                }
            }
        )
    for _ in range(ties):
        rows.append(
            {
                "arms": {
                    "S_SESSION_RANK": {"all_evidence": True},
                    "P_PAIR_RANK": {"all_evidence": True},
                }
            }
        )
    return rows


@pytest.mark.parametrize(
    ("gains", "losses", "expected"),
    ((6, 0, "WORKS"), (4, 1, "CARRIES_SIGNAL"), (1, 1, "NULL")),
)
def test_every_registered_disposition_is_reachable(
    gains: int, losses: int, expected: str
) -> None:
    comparison = paired_counts(comparison_rows(gains, losses, 10))
    assert _disposition(comparison) == expected


def test_nf004_modules_do_not_import_answer_key_files() -> None:
    root = Path(__file__).resolve().parents[1]
    mechanism = (root / "src/analysis/nf004_mechanism.py").read_text(
        encoding="utf-8"
    )
    assert "q_facts_key" not in mechanism

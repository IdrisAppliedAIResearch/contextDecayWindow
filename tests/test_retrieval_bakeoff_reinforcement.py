from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.retrieval_bakeoff.reinforcement import (
    ReinforcementInput,
    analyze_reinforcement,
    analyze_retrieval_log,
    sha256_file,
)


def test_reinforcement_is_confirmed_only_on_two_supporting_corpora(
    tmp_path: Path,
) -> None:
    left = _write_fixture(tmp_path / "left.jsonl", supports=True)
    right = _write_fixture(tmp_path / "right.jsonl", supports=True)
    result = analyze_reinforcement(
        inputs=(
            _spec("left", left),
            _spec("right", right),
        ),
        implementation_sha="a" * 40,
    )
    assert result["verdict"] == "CONFIRMED_ON_PRESERVED_RUNS"
    for corpus in result["corpora"]:
        assert corpus["support_status"] == "SUPPORTS"
        assert corpus["primary_delta_exact"] == "1/1"
        assert corpus["ols_slope"] > 0
        assert corpus["invariants"]["status"] == "PASS"


def test_one_supporting_corpus_is_mixed(tmp_path: Path) -> None:
    left = _write_fixture(tmp_path / "left.jsonl", supports=True)
    right = _write_fixture(tmp_path / "right.jsonl", supports=False)
    result = analyze_reinforcement(
        inputs=(
            _spec("left", left),
            _spec("right", right),
        ),
        implementation_sha="b" * 40,
    )
    assert result["verdict"] == "MIXED"
    assert [
        corpus["support_status"] for corpus in result["corpora"]
    ] == ["SUPPORTS", "DOES_NOT_SUPPORT"]


def test_zero_k_quartile_is_not_evaluable(tmp_path: Path) -> None:
    rows = [
        _row(turn, overlap=None if turn <= 2 else True)
        for turn in range(1, 9)
    ]
    path = _write_rows(tmp_path / "zero.jsonl", rows)
    result = analyze_retrieval_log(_spec("zero", path))
    assert result["support_status"] == "NOT_EVALUABLE"
    assert result["primary_delta"] is None
    assert result["not_evaluable_reasons"] == [
        "quartile_1_has_no_k_candidates"
    ]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda rows: rows[2].update(k_count=2),
            "k_count=2, but KN + K-only=1",
        ),
        (
            lambda rows: rows[2]["n_episodes"].append(
                dict(rows[2]["n_episodes"][0])
            ),
            "n_count does not match n_episodes",
        ),
        (
            lambda rows: rows[2]["n_episodes"][0].update(turn_number=3),
            "ineligible source turn",
        ),
        (
            lambda rows: rows[2].update(turn_number=4),
            "expected turn 3, observed 4",
        ),
    ],
)
def test_accounting_invariants_fail_closed(
    tmp_path: Path,
    mutation,
    message: str,
) -> None:
    rows = [
        _row(turn, overlap=None if turn == 1 else True)
        for turn in range(1, 9)
    ]
    mutation(rows)
    path = _write_rows(tmp_path / "bad.jsonl", rows)
    with pytest.raises(AssertionError, match=re.escape(message)):
        analyze_retrieval_log(_spec("bad", path))


def test_locked_hash_mismatch_fails_before_analysis(tmp_path: Path) -> None:
    path = _write_fixture(tmp_path / "source.jsonl", supports=True)
    spec = ReinforcementInput(
        corpus_id="bad_hash",
        path=path,
        expected_turns=8,
        expected_sha256="0" * 64,
    )
    with pytest.raises(AssertionError, match="source hash mismatch"):
        analyze_retrieval_log(spec)


def _write_fixture(path: Path, *, supports: bool) -> Path:
    rows = []
    for turn in range(1, 9):
        if turn == 1:
            overlap = None
        elif supports:
            overlap = turn >= 7
        else:
            overlap = turn <= 2
        rows.append(_row(turn, overlap=overlap))
    return _write_rows(path, rows)


def _row(turn: int, *, overlap: bool | None) -> dict:
    if overlap is None:
        return {
            "turn_number": turn,
            "k_count": 0,
            "n_count": 0,
            "k_episodes": [],
            "n_episodes": [],
        }
    episode = {
        "id": f"episode-{turn}",
        "turn_number": max(1, turn - 1),
        "retrieval_type": "KN" if overlap else "K",
    }
    return {
        "turn_number": turn,
        "k_count": 1,
        "n_count": int(overlap),
        "k_episodes": [] if overlap else [episode],
        "n_episodes": [episode] if overlap else [],
    }


def _write_rows(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )
    return path


def _spec(corpus_id: str, path: Path) -> ReinforcementInput:
    return ReinforcementInput(
        corpus_id=corpus_id,
        path=path,
        expected_turns=8,
        expected_sha256=sha256_file(path),
    )

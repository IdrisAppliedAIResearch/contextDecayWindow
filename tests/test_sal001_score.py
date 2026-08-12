from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest

from src.analysis.sal001_score import (
    SAL001ScoreError,
    changed_interval,
    fit_label_free_adjustment,
    token_negative_log_probability,
    user_intervals,
    validate_manifest,
)


class CharacterModel:
    def tokenize(
        self, text: bytes, add_bos: bool = False, special: bool = True
    ) -> list[int]:
        del add_bos, special
        return list(text)


class SimpleFormatter:
    def __call__(self, *, messages: list[dict[str, str]]) -> SimpleNamespace:
        rendered = "".join(
            f"<{message['role']}>{message['content']}</{message['role']}>"
            for message in messages
        )
        return SimpleNamespace(prompt=rendered)


def test_changed_interval_locates_only_inserted_content() -> None:
    full = list(b"prefixVALUEsuffix")
    blank = list(b"prefixsuffix")
    start, end = changed_interval(full, blank)
    assert bytes(full[start:end]) == b"VALUE"


def test_changed_interval_rejects_empty_change() -> None:
    with pytest.raises(SAL001ScoreError, match="empty token interval"):
        changed_interval([1, 2], [1, 2])


def test_user_intervals_are_disjoint_user_content() -> None:
    messages = [
        {"role": "user", "content": "alpha"},
        {"role": "assistant", "content": "one"},
        {"role": "user", "content": "beta"},
        {"role": "assistant", "content": "two"},
    ]
    tokens, intervals = user_intervals(CharacterModel(), SimpleFormatter(), messages)
    assert [bytes(tokens[start:end]).decode() for start, end in intervals] == [
        "alpha",
        "beta",
    ]
    assert intervals[0][1] < intervals[1][0]


def test_negative_log_probability_uses_complete_softmax() -> None:
    logits = np.asarray([0.0, 1.0, 2.0], dtype=np.float32)
    observed = token_negative_log_probability(logits, 2)
    expected = math.log(math.exp(0) + math.exp(1) + math.exp(2)) - 2
    assert observed == pytest.approx(expected, abs=1e-12)


def test_label_free_adjustment_is_full_rank_and_orthogonal() -> None:
    records = []
    session_lengths = {}
    for session_index in range(6):
        session_hash = f"{session_index:064x}"
        session_lengths[session_hash] = 5
        for exchange_index in range(5):
            token_ids = [
                10 + session_index,
                100 + exchange_index,
                200 + session_index + exchange_index,
            ]
            records.append(
                {
                    "session_sha256": session_hash,
                    "exchange_index": exchange_index,
                    "content_token_count": 3 + (exchange_index % 2),
                    "content_token_ids": token_ids,
                    "preceding_rendered_token_count": 10 + 7 * exchange_index + session_index,
                    "mean_nll": 2.0 + 0.1 * session_index + 0.2 * exchange_index + 0.03 * exchange_index**2,
                }
            )
    result = fit_label_free_adjustment(records, session_lengths)
    assert result["rank"] == 5
    assert result["residual_std"] > 0
    assert max(abs(value) for value in result["residual_feature_correlations"].values()) < 1e-10
    assert all(math.isfinite(row["adjusted_salience"]) for row in records)


def test_validate_manifest_rejects_planted_label_key() -> None:
    manifest = {
        "schema": "sal001-label-free-scorer-manifest-v1",
        "dataset_sha256": "0" * 64,
        "sessions": [],
        "labels": [True],
    }
    with pytest.raises(SAL001ScoreError, match="unauthorized top-level"):
        validate_manifest(manifest)


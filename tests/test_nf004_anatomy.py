from __future__ import annotations

import numpy as np
import pytest

from analysis.nf004_anatomy_analysis import auc, grouped_oof
from analysis.nf004_anatomy_features import FEATURES, Candidate, feature_row


def test_feature_row_is_finite_and_label_blind() -> None:
    candidates = [
        Candidate(f"c{i}", f"s{i // 2}", i // 2, i % 2, "text" * (i + 1), 4 * (i + 1))
        for i in range(6)
    ]
    scores = np.asarray([.9, .1, .8, .7, .6, .2], dtype=np.float32)
    row = feature_row(
        {"comparison_key": "q", "duplicate_ordinal": 0, "sample_id": "c", "source_index": 1, "text": "When was item 42?"},
        candidates, scores, (0, 1, 2, 3, 4, 5), (0, 2, 3, 4, 5, 1),
    )
    assert set(FEATURES) <= set(row)
    assert all(np.isfinite(float(row[name])) for name in FEATURES)
    assert row["top_session_score_range"] == pytest.approx(.8)
    assert "evidence" not in " ".join(row).lower()


def test_auc_handles_ties() -> None:
    assert auc([1, 1, 0, 0], [1, 0, 1, 0]) == pytest.approx(.5)


def test_grouped_oof_finds_cross_group_signal() -> None:
    groups = np.asarray([f"c{i // 20}" for i in range(120)])
    labels = np.asarray([(i % 20) < 10 for i in range(120)], dtype=int)
    signal = labels * 2.0 - 1.0
    matrix = np.column_stack([signal, np.arange(120) % 3])
    predicted, selected = grouped_oof(matrix, labels, groups)
    assert auc(predicted, labels) > .99
    assert set(selected) == set(groups)


def test_leakage_scan_does_not_scan_its_own_token_declaration() -> None:
    from pathlib import Path

    source = Path("src/analysis/nf004_anatomy_features.py").read_text(encoding="utf-8").lower()
    scanned = "\n".join(line for line in source.splitlines() if "forbidden_tokens =" not in line)
    assert "nf004_measurement" not in scanned
    assert "g6_holdout_outcomes" not in scanned

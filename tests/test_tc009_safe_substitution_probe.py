from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from analysis.tc009_safe_substitution_probe import ProbeError, evaluate_feature, feature_row


def test_feature_row_measures_redundancy_and_relevance_without_labels() -> None:
    pairs = {name: SimpleNamespace(session_id=f"s{index}") for index, name in enumerate(("keep", "out", "in"))}
    frozen = {
        "blind_key": "q",
        "sample_id": "c",
        "source_index": 0,
        "orders": {"dense": ["keep", "out", "in"]},
        "dynamic_steps": [
            {"candidate_id": "keep", "raw_similarity": .9, "accumulated_penalty": 0},
            {"candidate_id": "out", "raw_similarity": .8, "accumulated_penalty": 0},
            {"candidate_id": "in", "raw_similarity": .7, "accumulated_penalty": .03},
        ],
        "budgets": {"32000": {
            "control": {"selected_ids": ["keep", "out"], "payload_sha256": "a", "payload_chars": 10},
            "dynamic": {"selected_ids": ["keep", "in"], "payload_sha256": "b", "payload_chars": 10},
        }},
    }
    gram = np.asarray([[1, .6, .2], [.6, 1, .1], [.2, .1, 1]], dtype=np.float32)
    row = feature_row(frozen, pair_by_id=pairs, gram=gram, index_by_id={"keep": 0, "out": 1, "in": 2})
    assert row["query_margin_best"] == pytest.approx(-.1)
    assert row["incoming_novelty_max"] == pytest.approx(.8)
    assert row["outgoing_redundancy_max"] == pytest.approx(.6)
    assert row["neg_incoming_penalty_max"] == pytest.approx(-.03)


def test_metric_requires_all_frozen_signal_clauses() -> None:
    rows = []
    for index in range(80):
        direction = "gain" if index < 4 else "loss" if index < 20 else "tie"
        rows.append({"question_id": f"q{index}", "sample_id": f"c{index % 4}", "direction": direction, "good": 100 - index, "bad": index})
    assert evaluate_feature(rows, "good")["passes"]
    assert not evaluate_feature(rows, "bad")["passes"]


def test_extractor_rejects_label_input(tmp_path) -> None:
    from analysis.tc009_safe_substitution_probe import extract_features

    with pytest.raises(ProbeError):
        extract_features(tmp_path / "features.csv", forbidden_label_path=tmp_path / "labels.csv")

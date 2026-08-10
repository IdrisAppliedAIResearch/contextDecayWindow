from __future__ import annotations

import numpy as np
import pytest

from src.analysis.e006_rev5_preflight import (
    build_preflight,
    run_registered_cells,
)
from src.retrieval_mechanism_ledger.e006 import (
    assert_mechanism_path_allowed,
    retrieve_chained,
)


def test_chain_excludes_seen_candidates_and_returns_m_per_step() -> None:
    query = np.array([0.9, 0.8, 0.7, 0.6], dtype=np.float64)
    gram = np.eye(4, dtype=np.float64)
    hashes = tuple(f"{index:064x}" for index in range(4))

    result = retrieve_chained(
        query_cosines=query,
        gram=gram,
        content_hashes=hashes,
        depth=1,
        per_step=2,
        query_weight=0.5,
        retention=0.7,
    )

    assert len(result.steps) == 2
    assert all(step.novelty_count == 2 for step in result.steps)
    assert set(result.steps[0].hit_indices).isdisjoint(result.steps[1].hit_indices)


def test_d0_is_single_shot_query_ranking() -> None:
    selections, inputs = run_registered_cells()
    q_order = tuple(
        sorted(
            range(len(inputs.ids)),
            key=lambda index: (
                -float(inputs.query_cosines[index]),
                inputs.content_hashes[index],
            ),
        )
    )

    for selection in selections:
        if selection.depth == 0:
            assert selection.ranked_seen_indices == q_order[: selection.per_step]
            assert selection.final_cue_query_cosine == pytest.approx(1.0)


def test_mechanism_rejects_measurement_paths() -> None:
    with pytest.raises(ValueError, match="measurement boundary"):
        assert_mechanism_path_allowed("experiments/study_008/q_facts_key.md")


def test_full_preflight_is_conjunctive() -> None:
    result = build_preflight()

    assert len(result["checklist"]) == 10
    expected = all(
        check["status"] == "PASS" for check in result["checklist"].values()
    )
    assert (result["status"] == "PASS") is expected
    assert result["input_counts"]["registered_cells"] == 48

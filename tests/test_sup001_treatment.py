from __future__ import annotations

from src.analysis.sup001_benchmark import build
from src.analysis.sup001_control import compute_control
from src.analysis.sup001_treatment import compute_treatment
from src.analysis.sup001_vectors import load_vector_texts

import numpy as np


def fixture_vectors() -> dict[str, np.ndarray]:
    result = {}
    for index, row in enumerate(load_vector_texts()):
        vector = np.zeros(16, dtype=np.float32)
        vector[index % 16] = 1.0
        result[row.text] = vector
    return result


def test_treatment_excludes_silent_versions_and_preserves_exact_lineages() -> None:
    mechanism, _key = build()
    control = compute_control(mechanism, fixture_vectors().__getitem__)
    treatment = compute_treatment(mechanism, control)
    assert treatment["query_count"] == 96
    assert treatment["lineage_count"] == 64
    assert all(len(row["selected_ids"]) == 8 for row in treatment["queries"])
    assert all(row["serialized_chars"] <= 32_000 for row in treatment["queries"])
    for lineage in treatment["lineages"]:
        records = lineage["records"]
        assert len(records) == 3
        assert [row["accessibility"] for row in records] == [0.0, 0.0, 1.0]
        assert all(row["episode_sha256"] == row["content_hash_round_trip"] for row in records)
    silent = {
        row["episode_sha256"]
        for lineage in treatment["lineages"]
        for row in lineage["records"]
        if row["accessibility"] == 0.0
    }
    assert all(not (silent & set(row["selected_ids"])) for row in treatment["queries"])
    assert treatment["read_purity"]["state_unchanged"]

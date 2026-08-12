from __future__ import annotations

import numpy as np

from src.analysis.sup001_ablation_common import (
    control_context,
    frozen_episodes,
    load_script,
    vector_texts,
)


def test_locked_ablation_inventory() -> None:
    script = load_script()
    assert len(frozen_episodes(script)) == 26
    assert len(vector_texts(script)) == 35
    assert sum(row["kind"] == "probe" for row in script["turns"]) == 9


def test_control_context_ranks_all_26_and_packs_exactly_eight() -> None:
    script = load_script()
    episodes = frozen_episodes(script)
    texts = vector_texts(script)
    vectors = {}
    for index, text in enumerate(texts):
        vector = np.zeros(16, dtype=np.float32)
        vector[index % 16] = 1.0
        vectors[text] = vector
    query = next(row["query"] for row in script["turns"] if row["kind"] == "probe")
    context = control_context(query, episodes, vectors.__getitem__, top_k=8, budget_chars=32_000)
    assert len(context["population"]) == 26
    assert len(context["selected_ids"]) == 8
    assert context["serialized_chars"] <= 32_000
    assert context["selected"] == sorted(
        context["population"], key=lambda row: (-row["cosine"], row["episode_sha256"])
    )[:8]

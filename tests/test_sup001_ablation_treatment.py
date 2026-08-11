from __future__ import annotations

import numpy as np

from src.analysis.sup001_ablation_common import frozen_episodes, load_script, vector_texts
from src.analysis.sup001_ablation_treatment import build_ledger, ledger_digest, treatment_context


def vectors() -> dict[str, np.ndarray]:
    result = {}
    for index, text in enumerate(vector_texts(load_script())):
        vector = np.zeros(16, dtype=np.float32)
        vector[index % 16] = 1.0
        result[text] = vector
    return result


def test_treatment_natural_route_excludes_all_silent_ancestors() -> None:
    script = load_script()
    episodes = frozen_episodes(script)
    ledger = build_ledger(script, episodes)
    probe = next(row for row in script["turns"] if row.get("probe_id") == "current:tea")
    before = ledger_digest(ledger)
    context = treatment_context(probe, episodes, ledger, vectors().__getitem__, top_k=8, budget_chars=32_000)
    silent = {
        row.episode_sha256
        for key in ("preference:tea", "location:workshop", "schedule:dentist", "quantity:running")
        for row in ledger.lineage(key)
        if row.accessibility == 0.0
    }
    assert len(context["selected_ids"]) == 8
    assert not silent & set(context["selected_ids"])
    assert ledger_digest(ledger) == before


def test_treatment_history_route_returns_three_versions_oldest_first() -> None:
    script = load_script()
    episodes = frozen_episodes(script)
    ledger = build_ledger(script, episodes)
    probe = next(row for row in script["turns"] if row.get("probe_id") == "history:tea")
    context = treatment_context(probe, episodes, ledger, vectors().__getitem__, top_k=8, budget_chars=32_000)
    assert context["selected_ids"] == [row.episode_sha256 for row in ledger.lineage("preference:tea")]
    assert [row["version"] for row in context["selected"]] == [1, 2, 3]

from __future__ import annotations

from types import SimpleNamespace

from analysis.tc008_postrun import _question_probe


def test_probe_attributes_session_grouping_loss_when_a3_preserves_carrier() -> None:
    pairs = (
        SimpleNamespace(identity="need", session_id="s1"),
        SimpleNamespace(identity="other", session_id="s2"),
    )
    row = {
        "question_id": "q",
        "sample_id": "c",
        "source_index": 0,
        "population": "targeted",
        "evidence_candidate_ids": ["need"],
        "orders": {"dense": ["need", "other"], "session": ["other", "need"]},
        "budgets": {
            "16000": {
                "control": {"selected_ids": ["need"], "phase": {"need": "full_relevance"}},
                "session": {"selected_ids": ["other"], "phase": {"other": "protected_spread"}},
                "a3": {"selected_ids": ["need"], "phase": {"need": "protected_spread"}},
            }
        },
    }
    question = SimpleNamespace(question="Where?", category="1")
    probe = _question_probe(row, question, SimpleNamespace(pairs=pairs), 16_000)
    assert probe["mechanism_read"] == "source_session_grouping_loss_vs_a3"
    assert probe["lost_evidence"][0]["dense_rank"] == 1

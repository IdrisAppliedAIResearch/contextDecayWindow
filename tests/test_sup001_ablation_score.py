from __future__ import annotations

from src.analysis.sup001_ablation_score import score_probe


def response(answer: str, payload: str = "value") -> dict:
    return {
        "answer": answer,
        "context": {
            "payload": payload,
            "selected_ids": [str(index) for index in range(8)],
            "serialized_chars": len(payload),
            "payload_sha256": "0" * 64,
        },
    }


def test_exact_scorer_rejects_punctuation_and_numeric_reformatting() -> None:
    key = {"probe_id": "p", "class": "unchanged", "expected": "$35", "stale": []}
    assert score_probe(response("$35", "$35"), key)["exact"]
    assert not score_probe(response("$35.00", "$35"), key)["exact"]
    assert not score_probe(response("$35.", "$35"), key)["exact"]


def test_history_evidence_requires_every_ordered_value() -> None:
    key = {
        "probe_id": "h",
        "class": "history",
        "expected": "old | middle | current",
        "stale": [],
    }
    assert score_probe(response(key["expected"], "old middle current"), key)["evidence_present"]
    assert not score_probe(response(key["expected"], "old current"), key)["evidence_present"]

from __future__ import annotations

from types import SimpleNamespace

from analysis.tc009_postrun import _question_probe


def _row(*, dynamic: list[str], session: list[str], a3: list[str]) -> dict:
    identities = ["need", "other"]
    arms = {
        "control": ["need"],
        "dynamic": dynamic,
        "session": session,
        "a3": a3,
    }
    return {
        "question_id": "q",
        "sample_id": "c",
        "source_index": 0,
        "population": "targeted",
        "evidence_candidate_ids": ["need"],
        "orders": {arm: identities for arm in ("dense", "dynamic", "session", "a3")},
        "dynamic_steps": [
            {
                "candidate_id": identifier,
                "session_count_before": 0,
                "raw_similarity": 0.9,
                "accumulated_penalty": 0.0,
                "adjusted_score": 0.9,
            }
            for identifier in identities
        ],
        "budgets": {
            "16000": {
                arm: {"selected_ids": chosen, "phase": {identifier: "protected_spread" for identifier in chosen}}
                for arm, chosen in arms.items()
            }
        },
    }


def test_probe_calls_loss_dynamic_unique_when_both_predecessors_preserve() -> None:
    pairs = (
        SimpleNamespace(identity="need", session_id="s1"),
        SimpleNamespace(identity="other", session_id="s2"),
    )
    probe = _question_probe(
        _row(dynamic=["other"], session=["need"], a3=["need"]),
        SimpleNamespace(question="Where?", category="1"),
        SimpleNamespace(pairs=pairs),
        16_000,
    )
    lost = probe["displaced_evidence"][0]
    assert lost["attribution"] == "dynamic_unique_loss"
    assert lost["dense_rank"] == 1
    assert probe["identity_completion_disagreement"] is False


def test_probe_calls_loss_common_when_all_split_arms_drop_carrier() -> None:
    pairs = (
        SimpleNamespace(identity="need", session_id="s1"),
        SimpleNamespace(identity="other", session_id="s2"),
    )
    probe = _question_probe(
        _row(dynamic=["other"], session=["other"], a3=["other"]),
        SimpleNamespace(question="Where?", category="1"),
        SimpleNamespace(pairs=pairs),
        16_000,
    )
    assert probe["displaced_evidence"][0]["attribution"] == "common_fixed_protection_loss"

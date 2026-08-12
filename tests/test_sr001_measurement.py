from __future__ import annotations

from src.analysis.sr001_measurement import fact_matches_units


def test_fact_match_requires_turn_role_and_terms_in_one_unit() -> None:
    fact = {
        "source_turns": [5],
        "source_role": "user",
        "required_terms": ["alpha", "beta"],
    }
    units = [
        {"unit_id": "wrong-role", "turn": 5, "user_text": "", "assistant_text": "alpha beta"},
        {"unit_id": "split-a", "turn": 5, "user_text": "alpha", "assistant_text": ""},
        {"unit_id": "split-b", "turn": 5, "user_text": "beta", "assistant_text": ""},
        {"unit_id": "wrong-turn", "turn": 6, "user_text": "alpha beta", "assistant_text": ""},
        {"unit_id": "match", "turn": 5, "user_text": "Alpha and BETA", "assistant_text": ""},
    ]
    assert fact_matches_units(fact, units) == ["match"]


def test_episode_unit_can_match_registered_role_only() -> None:
    fact = {"source_turns": [1], "source_role": "user", "required_terms": ["needle"]}
    episode = {"unit_id": "episode", "turn": 1, "user_text": "needle", "assistant_text": "other"}
    assert fact_matches_units(fact, [episode]) == ["episode"]

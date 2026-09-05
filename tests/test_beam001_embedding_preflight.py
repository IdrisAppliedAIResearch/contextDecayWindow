from __future__ import annotations

from analysis.beam001_corpus import conversation_key
from analysis.beam001_embedding_preflight import (
    MAX_INPUT_TOKENS,
    evaluate,
)


def _row(user: str, assistant: str, question: str = "What happened?") -> dict:
    chat = [
        [
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ]
    ]
    return {
        "domain": "BEAM",
        "split": "100K",
        "conversation_key": conversation_key("100K", chat),
        "chat_batches": chat,
        "questions": [
            {
                "question_key": "fixture-question",
                "category": "fixture",
                "question": question,
                "occurrence_ordinal": 0,
            }
        ],
    }


def test_exact_inputs_pass_when_every_item_fits() -> None:
    result = evaluate([_row("short user", "short assistant")])
    assert result["gate"] == "PASS"
    assert result["disposition"] == "READY_FOR_TWO_REQUEST_SMOKE"
    assert result["api_requests_made"] == 0


def test_oversized_episode_fails_without_printing_content() -> None:
    oversized = " token" * (MAX_INPUT_TOKENS + 10)
    result = evaluate([_row(oversized, "answer")])
    assert result["gate"] == "FAIL"
    assert result["disposition"] == "EMBEDDING_INPUT_NOT_IDENTIFIED"
    assert result["episode_tokens"]["over_limit"] == 1
    assert "content" not in result["oversized_episodes"][0]

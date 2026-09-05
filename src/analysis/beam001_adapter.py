"""Question-only BEAM surface reader and strict public-store adapter."""

from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

DOMAIN = "BEAM"
FORBIDDEN_FIELDS = frozenset(
    {
        "abstention_type",
        "answer",
        "answer_key",
        "bullet_points_covered",
        "calculation_required",
        "complexity_factors",
        "compliance_indicators",
        "contradiction_type",
        "conversation_reference",
        "conversation_references",
        "conversation_sessions",
        "difficulty",
        "expected_compliance",
        "extraction_challenge",
        "ideal_answer",
        "ideal_response",
        "ideal_summary",
        "instruction_being_tested",
        "instruction_type",
        "key_elements_tested",
        "key_facts_tested",
        "non_compliance_signs",
        "ordering_tested",
        "ordering_type",
        "official_fields",
        "plan_reference",
        "potential_confusion",
        "preference_being_tested",
        "preference_type",
        "reasoning_steps",
        "reasoning_type",
        "rubric",
        "score",
        "sessions_required",
        "source_chat_ids",
        "summarization_type",
        "synthesis_required",
        "temporal_type",
        "tests_for",
        "tests_retention_of",
        "time_points",
        "topic_questioned",
        "total_mentions",
        "update_type",
        "why_unanswerable",
    }
)


class BeamAdapterError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _stable_digest(*parts: bytes) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part)
    return digest.hexdigest()


def _field_names(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _field_names(child)
    elif isinstance(value, list):
        for child in value:
            yield from _field_names(child)


def assert_mechanism_only(value: Any) -> None:
    found = sorted(set(_field_names(value)) & FORBIDDEN_FIELDS)
    if found:
        raise BeamAdapterError(f"Outcome fields reached mechanism code: {found}")


def load_mechanism_surface(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            row = json.loads(line)
            assert_mechanism_only(row)
            if not isinstance(row, dict):
                raise BeamAdapterError(f"Mechanism row {line_number} is not an object")
            rows.append(row)
    return rows


def _conversation_key(row: Mapping[str, Any]) -> str:
    return _stable_digest(
        DOMAIN.encode(),
        str(row["split"]).encode(),
        canonical_bytes(row["chat_batches"]),
    )


def adapt_conversation(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    assert_mechanism_only(row)
    expected = _conversation_key(row)
    if row.get("domain") != DOMAIN or row.get("conversation_key") != expected:
        raise BeamAdapterError("Conversation identity did not reproduce")
    batches = row.get("chat_batches")
    if not isinstance(batches, list):
        raise BeamAdapterError("chat_batches must be a list")
    messages: list[dict[str, Any]] = []
    for batch in batches:
        if not isinstance(batch, list):
            raise BeamAdapterError("Each chat batch must be a list")
        for message in batch:
            if not isinstance(message, dict):
                raise BeamAdapterError("Each message must be an object")
            messages.append(message)
    if len(messages) % 2:
        raise BeamAdapterError("Flattened chat has an unmatched message")

    duplicate_ordinals: Counter[bytes] = Counter()
    episodes: list[dict[str, Any]] = []
    for offset in range(0, len(messages), 2):
        user = messages[offset]
        assistant = messages[offset + 1]
        if user.get("role") != "user" or assistant.get("role") != "assistant":
            raise BeamAdapterError(
                f"Strict alternation failed at flattened messages {offset}/{offset + 1}"
            )
        if not isinstance(user.get("content"), str) or not isinstance(
            assistant.get("content"), str
        ):
            raise BeamAdapterError("Episode content must be strings")
        pair_bytes = canonical_bytes([user, assistant])
        ordinal = duplicate_ordinals[pair_bytes]
        duplicate_ordinals[pair_bytes] += 1
        key = _stable_digest(
            DOMAIN.encode(),
            expected.encode(),
            pair_bytes,
            str(ordinal).encode(),
        )
        episodes.append(
            {
                "id": key,
                "episode_key": key,
                "conversation_key": expected,
                "occurrence_ordinal": ordinal,
                "turn_number": len(episodes) + 1,
                "user_message": user["content"],
                "assistant_message": assistant["content"],
                "source_messages": [user, assistant],
            }
        )
    return episodes


__all__ = [
    "BeamAdapterError",
    "FORBIDDEN_FIELDS",
    "adapt_conversation",
    "assert_mechanism_only",
    "canonical_bytes",
    "load_mechanism_surface",
]

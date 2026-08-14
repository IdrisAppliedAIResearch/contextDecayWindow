"""Outcome-blind statement candidates and frozen A3 selection for NF-006."""

from __future__ import annotations

import hashlib
import re
from html import escape
from typing import Mapping, Sequence

import numpy as np

from episodic._selection import (
    ClusterDiversitySelector,
    SelectionResult,
    SelectionStep,
    deterministic_clusters,
    relevance_vector,
    vector,
)


BUDGET_CHARS = 32_000
CLUSTER_COUNT = 16
LAMBDA = 0.1
COST_EXPONENT = 0.0
_NUMBERED_START = re.compile(r"(?m)^\d+\.\s+")
_RISK_ONLY = re.compile(r"\(Risk:\s*[^)]+\)", re.IGNORECASE)


def content_identity(*parts: object) -> str:
    encoded = "\0".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parent_content_identity(candidate: Mapping[str, object]) -> str:
    return content_identity(
        candidate["turn_number"],
        candidate["user_message"],
        candidate["assistant_message"],
    )


def split_assistant_statements(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    starts = [match.start() for match in _NUMBERED_START.finditer(normalized)]
    if len(starts) >= 2:
        boundaries = [*starts, len(normalized)]
        parts = []
        prefix = normalized[: starts[0]].strip()
        if prefix:
            parts.append(prefix)
        parts.extend(
            normalized[boundaries[index] : boundaries[index + 1]].strip()
            for index in range(len(starts))
        )
    else:
        parts = [part.strip() for part in re.split(r"\n\s*\n+", normalized)]
    return [
        part for part in parts if part and _RISK_ONLY.fullmatch(part) is None
    ]


def statement_units(candidate: Mapping[str, object]) -> list[dict[str, object]]:
    turn = int(candidate["turn_number"])
    units: list[dict[str, object]] = [
        {
            "source_turn": turn,
            "role": "user",
            "ordinal": 0,
            "text": str(candidate["user_message"]).strip(),
        }
    ]
    units.extend(
        {
            "source_turn": turn,
            "role": "assistant",
            "ordinal": ordinal,
            "text": text,
        }
        for ordinal, text in enumerate(
            split_assistant_statements(str(candidate["assistant_message"])),
            start=1,
        )
    )
    if any(not row["text"] for row in units):
        raise AssertionError("Statement splitter emitted an empty unit")
    return units


def build_statement_candidates(
    parents: Sequence[dict],
    own_vectors: Mapping[str, object] | None = None,
) -> tuple[dict, ...]:
    """Split parents while keeping all statement identities content-addressed."""
    statements: list[dict] = []
    for parent_index, parent in enumerate(parents):
        parent_hash = parent_content_identity(parent)
        for unit in statement_units(parent):
            role = str(unit["role"])
            ordinal = int(unit["ordinal"])
            text = str(unit["text"])
            statement_id = content_identity(
                parent_hash,
                parent["turn_number"],
                role,
                ordinal,
                text,
            )
            statement = {
                "id": statement_id,
                "parent_content_id": parent_hash,
                "parent_index": parent_index,
                "turn_number": int(parent["turn_number"]),
                "role": role,
                "ordinal": ordinal,
                "text": text,
                "user_message": text if role == "user" else "",
                "assistant_message": text if role == "assistant" else "",
                "ground_truth_domain": str(
                    parent.get("ground_truth_domain") or ""
                ),
                "parent_embedding": parent["embedding"],
            }
            if own_vectors is not None:
                statement["own_embedding"] = own_vectors[statement_id]
            statements.append(statement)
    return tuple(statements)


def render_statement_element(candidate: Mapping[str, object]) -> str:
    turn = _attribute(candidate["turn_number"])
    parent = _attribute(candidate["parent_content_id"])
    role = _attribute(candidate["role"])
    ordinal = _attribute(candidate["ordinal"])
    return "\n".join(
        (
            (
                f'<episode turn="{turn}" parent="{parent}" '
                f'role="{role}" ordinal="{ordinal}">'
            ),
            f"<user>{_text(candidate.get('user_message', ''))}</user>",
            (
                "<assistant>"
                f"{_text(candidate.get('assistant_message', ''))}"
                "</assistant>"
            ),
            "</episode>",
        )
    )


def render_statement_payload(candidates: Sequence[Mapping[str, object]]) -> str:
    if candidates:
        retrieved = "\n".join(
            ("<retrieved_stm>", *(render_statement_element(row) for row in candidates), "</retrieved_stm>")
        )
    else:
        retrieved = "<retrieved_stm/>"
    return "\n\n".join(("<recent_context/>", retrieved))


def statement_additive_weight(candidate: Mapping[str, object]) -> int:
    return len(render_statement_element(candidate)) + 1


def statement_wrapper_chars() -> int:
    sample = {
        "turn_number": 0,
        "parent_content_id": "0" * 64,
        "role": "user",
        "ordinal": 0,
        "user_message": "",
        "assistant_message": "",
    }
    return len(render_statement_payload([sample])) - statement_additive_weight(sample)


def parent_cluster_assignments(parents: Sequence[dict]) -> np.ndarray:
    return deterministic_clusters(parents, CLUSTER_COUNT)


def expanded_cluster_assignments(
    statements: Sequence[Mapping[str, object]],
    parent_assignments: np.ndarray,
) -> np.ndarray:
    return np.asarray(
        [parent_assignments[int(row["parent_index"])] for row in statements],
        dtype=np.int64,
    )


def select_statements(
    *,
    statements: Sequence[dict],
    query_embedding: np.ndarray,
    relevance_source: str,
    budget_chars: int = BUDGET_CHARS,
) -> SelectionResult:
    if not statements:
        raise ValueError("At least one statement candidate is required")
    if relevance_source not in {"parent_embedding", "own_embedding"}:
        raise ValueError("Unknown relevance source")

    parent_count = max(int(row["parent_index"]) for row in statements) + 1
    parent_vectors: list[dict | None] = [None] * parent_count
    for row in statements:
        index = int(row["parent_index"])
        if parent_vectors[index] is None:
            parent_vectors[index] = {"embedding": row["parent_embedding"]}
    if any(row is None for row in parent_vectors):
        raise AssertionError("Statement pool does not cover a contiguous parent prefix")
    assignments = deterministic_clusters(
        [row for row in parent_vectors if row is not None],
        CLUSTER_COUNT,
    )
    expanded = expanded_cluster_assignments(statements, assignments)
    selector = ClusterDiversitySelector(
        lambda_=LAMBDA,
        cost_exponent=COST_EXPONENT,
        assignments=expanded,
        cluster_count=CLUSTER_COUNT,
    )

    ranked = [dict(row, embedding=row[relevance_source]) for row in statements]
    relevance = relevance_vector(query_embedding, ranked)
    costs = np.asarray(
        [statement_additive_weight(row) for row in statements], dtype=np.float64
    )
    turns = [int(row["turn_number"]) for row in statements]
    identifiers = [str(row["id"]) for row in statements]
    fixed = statement_wrapper_chars()
    selected: list[int] = []
    steps: list[SelectionStep] = []
    spent = 0
    remaining = set(range(len(statements)))

    while remaining:
        affordable = [
            index
            for index in sorted(remaining)
            if fixed + spent + int(costs[index]) <= budget_chars
        ]
        if not affordable:
            break
        scaled = selector.scaled_gains(relevance, selected, costs)
        objective = selector.objective_gains(relevance, selected, costs)
        chosen = min(
            affordable,
            key=lambda index: (
                -float(scaled[index]),
                int(costs[index]),
                turns[index],
                identifiers[index],
            ),
        )
        spent += int(costs[chosen])
        selected.append(chosen)
        remaining.remove(chosen)
        steps.append(
            SelectionStep(
                step=len(steps) + 1,
                candidate_id=identifiers[chosen],
                source_turn=turns[chosen],
                domain=str(statements[chosen].get("ground_truth_domain") or ""),
                relevance=float(relevance[chosen]),
                objective_gain=float(objective[chosen]),
                scaled_gain=float(scaled[chosen]),
                additive_chars=int(costs[chosen]),
                cumulative_chars=fixed + spent,
            )
        )

    chosen = [statements[index] for index in selected]
    payload = render_statement_payload(chosen)
    if len(payload) > budget_chars:
        raise AssertionError("Statement selection exceeded its character budget")
    if selected and len(payload) != fixed + spent:
        raise AssertionError("Statement additive costs differ from serialized payload")
    skipped = tuple(identifiers[index] for index in sorted(remaining))
    return SelectionResult(
        arm="A3",
        parameters=selector.parameters,
        budget_chars=budget_chars,
        steps=tuple(steps),
        selected_ids=tuple(identifiers[index] for index in selected),
        selected_source_turns=tuple(turns[index] for index in selected),
        selected_domains=tuple(
            str(statements[index].get("ground_truth_domain") or "")
            for index in selected
        ),
        serialized_chars=len(payload),
        payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        payload=payload,
        objective_value=selector.objective(selected, relevance),
        optimality_bound=None,
        skipped_ids=skipped,
    )


def _attribute(value: object) -> str:
    return escape(str(value), quote=True)


def _text(value: object) -> str:
    return escape(str(value), quote=False)

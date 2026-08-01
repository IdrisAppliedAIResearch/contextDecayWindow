from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

FORBIDDEN_MECHANISM_PATH_PARTS = (
    "q_facts_key",
    "rubric",
    "atomic_items",
    "targeted_items",
)


VAULTS = (
    ("Alder", "104729"),
    ("Birch", "215830"),
    ("Cedar", "326941"),
    ("Dogwood", "437052"),
    ("Elm", "548163"),
    ("Fir", "659274"),
    ("Ginkgo", "760385"),
    ("Hazel", "871496"),
)
NEEDLE_POSITIONS = (0, 8, 16, 24)
DISTRACTORS = tuple(
    f"Archive note {index:02d} records routine maintenance for sector "
    f"{chr(65 + index % 8)}."
    for index in range(24)
)


@dataclass(frozen=True)
class CalibrationCase:
    case_id: str
    vault: str
    code: str
    needle_position: int
    text: str
    haystack_end: int
    needle_code_start: int
    needle_code_end: int
    answer_code_start: int
    answer_code_end: int


@dataclass(frozen=True)
class TextUnit:
    index: int
    text: str
    start: int
    end: int


def assert_mechanism_path_allowed(path: str | Path) -> None:
    normalized = str(path).replace("\\", "/").lower()
    if any(part in normalized for part in FORBIDDEN_MECHANISM_PATH_PARTS):
        raise ValueError(f"Mechanism path crosses the measurement boundary: {path}")


def calibration_cases() -> tuple[CalibrationCase, ...]:
    cases = []
    for vault, code in VAULTS:
        needle = f"The access code for vault {vault} is {code}."
        for position in NEEDLE_POSITIONS:
            sentences = list(DISTRACTORS)
            sentences.insert(position, needle)
            haystack = " ".join(sentences)
            needle_start = haystack.index(needle)
            needle_code_start = needle_start + needle.index(code)
            suffix = (
                f"\nQuestion: What is the access code for vault {vault}?"
                "\nAnswer: The access code is "
            )
            answer_code_start = len(haystack) + len(suffix)
            text = f"{haystack}{suffix}{code}."
            cases.append(
                CalibrationCase(
                    case_id=f"{vault.lower()}_p{position:02d}",
                    vault=vault,
                    code=code,
                    needle_position=position,
                    text=text,
                    haystack_end=len(haystack),
                    needle_code_start=needle_code_start,
                    needle_code_end=needle_code_start + len(code),
                    answer_code_start=answer_code_start,
                    answer_code_end=answer_code_start + len(code),
                )
            )
    return tuple(cases)


def whitespace_units(text: str) -> tuple[TextUnit, ...]:
    units = tuple(
        TextUnit(index=index, text=match.group(), start=match.start(), end=match.end())
        for index, match in enumerate(re.finditer(r"\S+", text))
    )
    if not units:
        raise ValueError("Text must contain at least one non-whitespace unit")
    return units


def overlapping_token_indices(
    offsets: Sequence[Sequence[int]],
    *,
    start: int,
    end: int,
) -> tuple[int, ...]:
    if start >= end:
        raise ValueError("Span must be non-empty")
    return tuple(
        index
        for index, pair in enumerate(offsets)
        if int(pair[1]) > start and int(pair[0]) < end
    )


def score_retrieval_heads(
    attention: np.ndarray,
    *,
    haystack_indices: Sequence[int],
    answer_indices: Sequence[int],
    needle_indices: Sequence[int],
) -> tuple[np.ndarray, int]:
    if attention.ndim != 4:
        raise ValueError("Attention must have shape [layers, heads, query, key]")
    haystack = np.asarray(haystack_indices, dtype=np.int64)
    needle = set(int(index) for index in needle_indices)
    hits = np.zeros(attention.shape[:2], dtype=np.float64)
    observations = 0
    for answer_index in answer_indices:
        row = int(answer_index) - 1
        if row < 0:
            raise ValueError("Answer token has no preceding causal row")
        local = attention[:, :, row, haystack]
        winning_positions = haystack[np.argmax(local, axis=-1)]
        hits += np.isin(winning_positions, tuple(needle))
        observations += 1
    return hits, observations


def unit_scores(
    query: str,
    *,
    token_offsets: Sequence[Sequence[int]],
    token_scores: Sequence[float],
) -> tuple[tuple[TextUnit, float], ...]:
    units = whitespace_units(query)
    values = []
    for unit in units:
        total = sum(
            float(score)
            for offset, score in zip(token_offsets, token_scores, strict=True)
            if int(offset[1]) > unit.start and int(offset[0]) < unit.end
        )
        values.append((unit, total))
    return tuple(values)


def select_cue(
    scored_units: Sequence[tuple[TextUnit, float]],
    *,
    k: int,
) -> tuple[str, tuple[int, ...], float]:
    if not 1 <= k <= len(scored_units):
        raise ValueError("k must select at least one available unit")
    ranked = sorted(scored_units, key=lambda item: (-item[1], item[0].index))
    selected = sorted((unit for unit, _score in ranked[:k]), key=lambda unit: unit.index)
    selected_ids = tuple(unit.index for unit in selected)
    mass = sum(score for unit, score in scored_units if unit.index in selected_ids)
    return " ".join(unit.text for unit in selected), selected_ids, float(mass)


def path_leakage_violations(paths: Iterable[str | Path]) -> list[str]:
    violations = []
    for path in paths:
        try:
            assert_mechanism_path_allowed(path)
        except ValueError:
            violations.append(str(path))
    return violations

"""Globally shortest parsing for the DA-034 sentinel pointer language."""

from __future__ import annotations

from typing import Sequence

from analysis.da023_backrefs import Backref, EncodedMember
from analysis.da034_sentinel_backrefs import DA034CodecError, reference_code

_INF = (10**18, 0)


class _RangeMinimum:
    def __init__(self, size: int) -> None:
        width = 1
        while width < size:
            width *= 2
        self.width = width
        self.values = [_INF] * (2 * width)

    def update(self, position: int, value: tuple[int, int]) -> None:
        index = self.width + position
        self.values[index] = value
        index //= 2
        while index:
            self.values[index] = min(self.values[2 * index], self.values[2 * index + 1])
            index //= 2

    def query(self, start: int, end: int) -> tuple[int, int]:
        left, right = self.width + start, self.width + end
        result = _INF
        while left < right:
            if left & 1:
                result = min(result, self.values[left])
                left += 1
            if right & 1:
                right -= 1
                result = min(result, self.values[right])
            left //= 2
            right //= 2
        return result


def _span_buckets(limit: int) -> list[tuple[int, int]]:
    output = []
    lower = 4
    threshold = 32
    while lower <= limit:
        while threshold <= lower:
            threshold *= 32
        upper = min(limit, threshold - 1)
        output.append((lower, upper))
        lower = upper + 1
    return output


def _append_literal(segments: list[str | Backref], value: str) -> None:
    if segments and isinstance(segments[-1], str):
        segments[-1] += value
    else:
        segments.append(value)


def encode_members(texts: Sequence[str], prior: Sequence[str],
                   sentinel: str) -> tuple[EncodedMember, ...]:
    """Return the minimum-character exact parse, member by member."""
    if any(sentinel in text for text in (*prior, *texts)):
        raise DA034CodecError("Sentinel occurs in source text")
    history = list(prior)
    index: dict[str, list[tuple[int, int]]] = {}
    for member_index, source in enumerate(history):
        for start in range(max(0, len(source) - 3)):
            index.setdefault(source[start:start + 4], []).append((member_index, start))
    output = []
    for text in texts:
        size = len(text)
        costs = [0] * (size + 1)
        choices: list[tuple[str, Backref | None, int] | None] = [None] * size
        ranges = _RangeMinimum(size + 1)
        ranges.update(size, (0, -size))
        for position in range(size - 1, -1, -1):
            best_cost = 1 + costs[position + 1]
            best_key: tuple[int, int, int, int] = (0, 0, 0, 0)
            best_choice: tuple[str, Backref | None, int] = ("LITERAL", None, 1)
            candidates = index.get(text[position:position + 4], ()) if position + 4 <= size else ()
            for member_index, start in candidates:
                source = history[member_index]
                limit = min(size - position, len(source) - start)
                length = 4
                while length < limit and text[position + length] == source[start + length]:
                    length += 1
                for lower, upper in _span_buckets(length):
                    downstream, negative_endpoint = ranges.query(
                        position + lower, position + upper + 1
                    )
                    span = -negative_endpoint - position
                    ref = Backref(member_index, start, span)
                    ref_cost = len(reference_code(sentinel, ref, len(history)))
                    candidate_cost = ref_cost + downstream
                    key = (1, member_index, start, -span)
                    if candidate_cost < best_cost or (
                        candidate_cost == best_cost and key < best_key
                    ):
                        best_cost = candidate_cost
                        best_key = key
                        best_choice = ("REFERENCE", ref, span)
            costs[position] = best_cost
            choices[position] = best_choice
            ranges.update(position, (best_cost, -position))
        segments: list[str | Backref] = []
        position = 0
        while position < size:
            choice = choices[position]
            if choice is None:
                raise DA034CodecError("Optimal parse is incomplete")
            kind, ref, width = choice
            if kind == "LITERAL":
                _append_literal(segments, text[position])
            else:
                if ref is None:
                    raise DA034CodecError("Reference choice is missing")
                segments.append(ref)
            position += width
        output.append(EncodedMember(tuple(segments)))
        new_index = len(history)
        history.append(text)
        for start in range(max(0, len(text) - 3)):
            index.setdefault(text[start:start + 4], []).append((new_index, start))
    return tuple(output)


__all__ = ["encode_members"]

"""Compact relative exact-span references for DA-027."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from analysis.da023_backrefs import Backref, EncodedMember

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class DA027CodecError(RuntimeError):
    pass


def base36(value: int) -> str:
    if value < 0:
        raise DA027CodecError("Base-36 value must be nonnegative")
    if value == 0:
        return "0"
    output = ""
    while value:
        value, digit = divmod(value, 36)
        output = ALPHABET[digit] + output
    return output


def parse36(value: str) -> int:
    if not value or (len(value) > 1 and value[0] == "0"):
        raise DA027CodecError("Noncanonical base-36 integer")
    if any(char not in ALPHABET for char in value):
        raise DA027CodecError("Invalid base-36 integer")
    return int(value, 36)


def prefix_for(texts: Sequence[str]) -> str:
    prefix = "~"
    while any(prefix + marker in text for text in texts for marker in ("r", "q")):
        prefix += "~"
    return prefix


def reference_code(prefix: str, ref: Backref, history_size: int) -> str:
    distance = history_size - ref.member
    if not 1 <= distance <= history_size:
        raise DA027CodecError("Reference is not strictly backward")
    return f"{prefix}q{base36(distance)}.{base36(ref.start)}.{base36(ref.length)}{prefix}"


def parse_reference(code: str, prefix: str, history_size: int) -> Backref:
    opening, closing = prefix + "q", prefix
    if not code.startswith(opening) or not code.endswith(closing):
        raise DA027CodecError("Malformed compact reference")
    body = code[len(opening):-len(closing)]
    parts = body.split(".")
    if len(parts) != 3:
        raise DA027CodecError("Malformed compact coordinates")
    distance, start, length = map(parse36, parts)
    if not 1 <= distance <= history_size or length <= 0:
        raise DA027CodecError("Invalid compact reference bounds")
    return Backref(history_size - distance, start, length)


def _append_literal(segments: list[str | Backref], value: str) -> None:
    if segments and isinstance(segments[-1], str):
        segments[-1] += value
    else:
        segments.append(value)


def encode_members(texts: Sequence[str], prior: Sequence[str], prefix: str) -> tuple[EncodedMember, ...]:
    history = list(prior)
    index: dict[str, list[tuple[int, int]]] = {}
    for member_index, text in enumerate(history):
        for start in range(max(0, len(text) - 3)):
            index.setdefault(text[start:start + 4], []).append((member_index, start))
    output = []
    for text in texts:
        segments: list[str | Backref] = []
        position = 0
        while position < len(text):
            candidates = index.get(text[position:position + 4], ()) if position + 4 <= len(text) else ()
            best_length = 0
            best_source: tuple[int, int] | None = None
            for member_index, start in candidates:
                source = history[member_index]
                limit = min(len(text) - position, len(source) - start)
                length = 4
                while length < limit and text[position + length] == source[start + length]:
                    length += 1
                if length > best_length or (length == best_length and best_source is not None and
                                             (member_index, start) < best_source):
                    best_length, best_source = length, (member_index, start)
            if best_source is not None:
                ref = Backref(best_source[0], best_source[1], best_length)
                if best_length > len(reference_code(prefix, ref, len(history))):
                    segments.append(ref)
                    position += best_length
                    continue
            _append_literal(segments, text[position])
            position += 1
        output.append(EncodedMember(tuple(segments)))
        new_index = len(history)
        history.append(text)
        for start in range(max(0, len(text) - 3)):
            index.setdefault(text[start:start + 4], []).append((new_index, start))
    return tuple(output)


def decode_members(encoded: Sequence[EncodedMember], prior: Sequence[str]) -> tuple[str, ...]:
    history = list(prior)
    output = []
    for member in encoded:
        chunks = []
        for segment in member.segments:
            if isinstance(segment, str):
                chunks.append(segment)
                continue
            reparsed = parse_reference(reference_code("~", segment, len(history)), "~", len(history))
            if reparsed != segment or segment.start + segment.length > len(history[segment.member]):
                raise DA027CodecError("Reference exceeds prior source")
            chunks.append(history[segment.member][segment.start:segment.start + segment.length])
        text = "".join(chunks)
        history.append(text)
        output.append(text)
    return tuple(output)


def encoded_chars(encoded: Sequence[EncodedMember], prefix: str, prior_count: int = 0) -> int:
    total = 0
    for offset, member in enumerate(encoded):
        history_size = prior_count + offset
        total += sum(len(segment) if isinstance(segment, str)
                     else len(reference_code(prefix, segment, history_size))
                     for segment in member.segments)
    return total


__all__ = ["DA027CodecError", "base36", "decode_members", "encode_members",
           "encoded_chars", "parse36", "parse_reference", "prefix_for", "reference_code"]


"""Opcode-free sentinel varint span pointers for DA-034."""

from __future__ import annotations

from typing import Sequence

from analysis.da023_backrefs import Backref, EncodedMember
from analysis.da031_varint_backrefs import DA031CodecError, decode_uint, encode_uint


class DA034CodecError(RuntimeError):
    pass


def sentinel_for(texts: Sequence[str]) -> str:
    sentinel = "~"
    while any(sentinel in text for text in texts):
        sentinel += "~"
    return sentinel


def reference_code(sentinel: str, ref: Backref, history_size: int) -> str:
    distance = history_size - ref.member
    if not sentinel or set(sentinel) != {"~"}:
        raise DA034CodecError("Invalid sentinel")
    if not 1 <= distance <= history_size or ref.start < 0 or ref.length <= 0:
        raise DA034CodecError("Reference is not strictly backward and positive")
    return f"{sentinel}{encode_uint(distance)}{encode_uint(ref.start)}{encode_uint(ref.length)}{sentinel}"


def parse_reference(code: str, sentinel: str, history_size: int) -> Backref:
    if not sentinel or set(sentinel) != {"~"} or not code.startswith(sentinel) or not code.endswith(sentinel):
        raise DA034CodecError("Malformed sentinel reference")
    body = code[len(sentinel):-len(sentinel)]
    values, position = [], 0
    try:
        for _ in range(3):
            value, position = decode_uint(body, position)
            values.append(value)
    except DA031CodecError as error:
        raise DA034CodecError(str(error)) from error
    if position != len(body):
        raise DA034CodecError("Trailing sentinel reference data")
    distance, start, length = values
    if not 1 <= distance <= history_size or length <= 0:
        raise DA034CodecError("Invalid sentinel reference bounds")
    return Backref(history_size - distance, start, length)


def _append_literal(segments: list[str | Backref], value: str) -> None:
    if segments and isinstance(segments[-1], str):
        segments[-1] += value
    else:
        segments.append(value)


def encode_members(texts: Sequence[str], prior: Sequence[str], sentinel: str) -> tuple[EncodedMember, ...]:
    if any(sentinel in text for text in (*prior, *texts)):
        raise DA034CodecError("Sentinel occurs in source text")
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
                if best_length > len(reference_code(sentinel, ref, len(history))):
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


def decode_members(encoded: Sequence[EncodedMember], prior: Sequence[str], sentinel: str) -> tuple[str, ...]:
    history = list(prior)
    output = []
    for member in encoded:
        chunks = []
        for segment in member.segments:
            if isinstance(segment, str):
                if sentinel in segment:
                    raise DA034CodecError("Sentinel occurs in literal")
                chunks.append(segment)
                continue
            if not 0 <= segment.member < len(history) or segment.start < 0 or segment.length <= 0:
                raise DA034CodecError("Reference is not prior-member valid")
            if segment.start + segment.length > len(history[segment.member]):
                raise DA034CodecError("Reference exceeds source member")
            code = reference_code(sentinel, segment, len(history))
            if parse_reference(code, sentinel, len(history)) != segment:
                raise DA034CodecError("Reference roundtrip differs")
            chunks.append(history[segment.member][segment.start:segment.start + segment.length])
        text = "".join(chunks)
        history.append(text)
        output.append(text)
    return tuple(output)


def encoded_chars(encoded: Sequence[EncodedMember], sentinel: str, prior_count: int = 0) -> int:
    total = 0
    for offset, member in enumerate(encoded):
        history_size = prior_count + offset
        total += sum(len(segment) if isinstance(segment, str)
                     else len(reference_code(sentinel, segment, history_size))
                     for segment in member.segments)
    return total


__all__ = ["DA034CodecError", "decode_members", "encode_members", "encoded_chars",
           "parse_reference", "reference_code", "sentinel_for"]


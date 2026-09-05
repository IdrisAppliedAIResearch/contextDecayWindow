"""Self-delimiting base-32 relative span pointers for DA-031."""

from __future__ import annotations

from typing import Sequence

from analysis.da023_backrefs import Backref, EncodedMember

TERMINAL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
CONTINUATION = "abcdefghijklmnopqrstuvwxyz0189-_"


class DA031CodecError(RuntimeError):
    pass


def encode_uint(value: int) -> str:
    if value < 0:
        raise DA031CodecError("Varint must be nonnegative")
    digits = [value & 31]
    value >>= 5
    while value:
        digits.append(value & 31)
        value >>= 5
    return "".join(CONTINUATION[digit] for digit in digits[:-1]) + TERMINAL[digits[-1]]


def decode_uint(text: str, position: int = 0) -> tuple[int, int]:
    start, value, shift = position, 0, 0
    while position < len(text):
        char = text[position]
        position += 1
        if char in CONTINUATION:
            digit = CONTINUATION.index(char)
            value |= digit << shift
            shift += 5
            continue
        if char in TERMINAL:
            value |= TERMINAL.index(char) << shift
            if text[start:position] != encode_uint(value):
                raise DA031CodecError("Noncanonical varint")
            return value, position
        raise DA031CodecError("Invalid varint character")
    raise DA031CodecError("Truncated varint")


def prefix_for(texts: Sequence[str]) -> str:
    prefix = "~"
    while any(prefix + marker in text for text in texts for marker in ("r", "q", "v")):
        prefix += "~"
    return prefix


def reference_code(prefix: str, ref: Backref, history_size: int) -> str:
    distance = history_size - ref.member
    if not 1 <= distance <= history_size or ref.start < 0 or ref.length <= 0:
        raise DA031CodecError("Reference is not strictly backward and positive")
    return f"{prefix}v{encode_uint(distance)}{encode_uint(ref.start)}{encode_uint(ref.length)}{prefix}"


def parse_reference(code: str, prefix: str, history_size: int) -> Backref:
    opening = prefix + "v"
    if not code.startswith(opening) or not code.endswith(prefix):
        raise DA031CodecError("Malformed varint reference")
    body = code[len(opening):-len(prefix)]
    values, position = [], 0
    for _ in range(3):
        value, position = decode_uint(body, position)
        values.append(value)
    if position != len(body):
        raise DA031CodecError("Trailing varint reference data")
    distance, start, length = values
    if not 1 <= distance <= history_size or length <= 0:
        raise DA031CodecError("Invalid varint reference bounds")
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
            if not 0 <= segment.member < len(history) or segment.start < 0 or segment.length <= 0:
                raise DA031CodecError("Reference is not prior-member valid")
            if segment.start + segment.length > len(history[segment.member]):
                raise DA031CodecError("Reference exceeds source member")
            code = reference_code("~", segment, len(history))
            if parse_reference(code, "~", len(history)) != segment:
                raise DA031CodecError("Reference text roundtrip differs")
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


__all__ = ["CONTINUATION", "DA031CodecError", "TERMINAL", "decode_members", "decode_uint",
           "encode_members", "encode_uint", "encoded_chars", "parse_reference", "prefix_for",
           "reference_code"]


"""Online exact index for the DA-034 sentinel back-reference codec."""

from __future__ import annotations

from typing import Hashable, Sequence

from analysis.da023_backrefs import Backref, EncodedMember
from analysis.da034_sentinel_backrefs import reference_code


class DA099CodecError(RuntimeError):
    pass


class MemberSuffixIndex:
    """Suffix automaton whose separators prevent cross-member matches."""

    def __init__(self, texts: Sequence[str] = ()) -> None:
        self._max_length = [0]
        self._link = [-1]
        self._transitions: list[dict[Hashable, int]] = [{}]
        self._first_member = [-1]
        self._first_end = [-1]
        self._last = 0
        self._members = 0
        for text in texts:
            self.append(text)

    @property
    def member_count(self) -> int:
        return self._members

    def _extend(self, token: Hashable, member: int, end: int) -> None:
        max_length = self._max_length
        link = self._link
        transitions = self._transitions
        current = len(max_length)
        max_length.append(max_length[self._last] + 1)
        link.append(-1)
        transitions.append({})
        self._first_member.append(member)
        self._first_end.append(end)
        previous = self._last
        while previous >= 0 and token not in transitions[previous]:
            transitions[previous][token] = current
            previous = link[previous]
        if previous < 0:
            link[current] = 0
        else:
            target = transitions[previous][token]
            if max_length[previous] + 1 == max_length[target]:
                link[current] = target
            else:
                clone = len(max_length)
                max_length.append(max_length[previous] + 1)
                link.append(link[target])
                transitions.append(dict(transitions[target]))
                self._first_member.append(self._first_member[target])
                self._first_end.append(self._first_end[target])
                while previous >= 0 and transitions[previous].get(token) == target:
                    transitions[previous][token] = clone
                    previous = link[previous]
                link[target] = link[current] = clone
        self._last = current

    def append(self, text: str) -> None:
        member = self._members
        self._extend(-(member + 1), -1, -1)
        for end, character in enumerate(text):
            self._extend(character, member, end)
        self._members += 1

    def longest_prefix(self, text: str, position: int = 0) -> tuple[int, int, int] | None:
        state = 0
        length = 0
        while position + length < len(text):
            target = self._transitions[state].get(text[position + length])
            if target is None:
                break
            state = target
            length += 1
        if length < 4:
            return None
        start = self._first_end[state] - length + 1
        if self._first_member[state] < 0 or start < 0:
            raise DA099CodecError("Indexed match crosses a member boundary")
        return length, self._first_member[state], start


class IndexedSentinelCodec:
    """Encode against persistent history without rebuilding its search index."""

    def __init__(self, history: Sequence[str], sentinel: str) -> None:
        if not sentinel or any(sentinel in text for text in history):
            raise DA099CodecError("Sentinel occurs in indexed history")
        self.sentinel = sentinel
        self.index = MemberSuffixIndex(history)

    @property
    def history_size(self) -> int:
        return self.index.member_count

    @staticmethod
    def _earlier(left: tuple[int, int, int] | None,
                 right: tuple[int, int, int] | None,
                 right_offset: int) -> tuple[int, int, int] | None:
        if right is not None:
            right = (right[0], right[1] + right_offset, right[2])
        if left is None:
            return right
        if right is None:
            return left
        if right[0] != left[0]:
            return right if right[0] > left[0] else left
        return right if (right[1], right[2]) < (left[1], left[2]) else left

    def encode(self, texts: Sequence[str]) -> tuple[EncodedMember, ...]:
        if any(self.sentinel in text for text in texts):
            raise DA099CodecError("Sentinel occurs in source text")
        overlay = MemberSuffixIndex() if len(texts) > 1 else None
        history_size = self.history_size
        output: list[EncodedMember] = []
        for offset, text in enumerate(texts):
            segments: list[str | Backref] = []
            position = 0
            while position < len(text):
                match = self.index.longest_prefix(text, position)
                if overlay is not None:
                    match = self._earlier(
                        match, overlay.longest_prefix(text, position), history_size
                    )
                if match is not None:
                    length, member, start = match
                    ref = Backref(member, start, length)
                    if length > reference_length(
                        len(self.sentinel), history_size + offset - member, start, length
                    ):
                        segments.append(ref)
                        position += length
                        continue
                character = text[position]
                if segments and isinstance(segments[-1], str):
                    segments[-1] += character
                else:
                    segments.append(character)
                position += 1
            output.append(EncodedMember(tuple(segments)))
            if overlay is not None and offset + 1 < len(texts):
                overlay.append(text)
        return tuple(output)

    def append(self, texts: Sequence[str]) -> None:
        for text in texts:
            if self.sentinel in text:
                raise DA099CodecError("Sentinel occurs in admitted text")
            self.index.append(text)

    def encoded_text_length(self, text: str) -> int:
        """Return exact one-member wire length without materializing segments."""
        if self.sentinel in text:
            raise DA099CodecError("Sentinel occurs in source text")
        history_size = self.history_size
        total = 0
        position = 0
        while position < len(text):
            match = self.index.longest_prefix(text, position)
            if match is not None:
                length, member, start = match
                wire_length = reference_length(
                    len(self.sentinel), history_size - member, start, length
                )
                if length > wire_length:
                    total += wire_length
                    position += length
                    continue
            total += 1
            position += 1
        return total

    def encode_and_append(self, texts: Sequence[str]) -> tuple[EncodedMember, ...]:
        output = []
        for text in texts:
            output.extend(self.encode([text]))
            self.append([text])
        return tuple(output)


def _uint_length(value: int) -> int:
    if value < 0:
        raise DA099CodecError("Varint must be nonnegative")
    return max(1, (value.bit_length() + 4) // 5)


def reference_length(sentinel_length: int, distance: int, start: int, length: int) -> int:
    if sentinel_length <= 0 or distance <= 0 or start < 0 or length <= 0:
        raise DA099CodecError("Invalid indexed reference bounds")
    return (2 * sentinel_length + _uint_length(distance)
            + _uint_length(start) + _uint_length(length))


def encoded_length(encoded: Sequence[EncodedMember], sentinel: str,
                   prior_count: int = 0) -> int:
    total = 0
    for offset, member in enumerate(encoded):
        history_size = prior_count + offset
        for segment in member.segments:
            if isinstance(segment, str):
                total += len(segment)
            else:
                total += reference_length(
                    len(sentinel), history_size - segment.member,
                    segment.start, segment.length,
                )
    return total


__all__ = ["DA099CodecError", "IndexedSentinelCodec", "MemberSuffixIndex",
           "encoded_length", "reference_length"]

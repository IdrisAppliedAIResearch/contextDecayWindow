"""Constant-time incremental charging for frozen DA-009 role patterns."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from analysis.da009_role_pattern import RolePatternContext


class IncrementalRoleCharge:
    def __init__(self, context: RolePatternContext) -> None:
        self.speakers = list(context.speakers)
        self.codes = {speaker: index for index, speaker in enumerate(self.speakers)}
        self.default_pattern = context.default_pattern
        self.chars = context.chars

    def cost(self, pair: Sequence[Mapping[str, str]], commit: bool = False) -> int:
        if all(str(member["speaker"]) in self.codes for member in pair):
            encoded = [
                (self.codes[str(member["speaker"])], str(member["text"]))
                for member in pair
            ]
            signature = tuple(code for code, _ in encoded)
            separators = max(0, len(encoded) - 1)
            if signature == self.default_pattern:
                delta = sum(len(text) for _, text in encoded) + separators
            else:
                delta = sum(len(f"{code}:{text}") for code, text in encoded) + separators
            if commit:
                self.chars += delta
            return delta
        codes = dict(self.codes)
        speakers = list(self.speakers)
        dictionary_delta = 0
        encoded: list[tuple[int, str]] = []
        for member in pair:
            speaker = str(member["speaker"])
            if speaker not in codes:
                code = len(speakers)
                codes[speaker] = code
                speakers.append(speaker)
                dictionary_delta += len(f"@{code}={speaker}")
            encoded.append((codes[speaker], str(member["text"])))
        signature = tuple(code for code, _ in encoded)
        separators = max(0, len(encoded) - 1)
        if signature == self.default_pattern:
            pair_chars = sum(len(text) for _, text in encoded) + separators
        else:
            pair_chars = sum(len(f"{code}:{text}") for code, text in encoded) + separators
        delta = dictionary_delta + pair_chars
        if commit:
            self.codes = codes
            self.speakers = speakers
            self.chars += delta
        return delta


__all__ = ["IncrementalRoleCharge"]

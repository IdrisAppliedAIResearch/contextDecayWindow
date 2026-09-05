"""Protected evidence-blind boundary substitution contract for DA-047."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

REGISTER_CAP = 2_048
GENERAL_PEAK_CAP = 4_096


class DA047Error(RuntimeError):
    pass


def _block(action: Mapping[str, Any]) -> str:
    if str(action.get("kind")) != "FRAME":
        raise DA047Error("Substitution requires a frame")
    block = action.get("block")
    if not isinstance(block, str) or len(block) != int(action.get("cost", -1)):
        raise DA047Error("Invalid replacement frame")
    if len(block) > REGISTER_CAP:
        raise DA047Error("Replacement exceeds boundary capacity")
    if hashlib.sha256(block.encode()).hexdigest() != str(action.get("block_sha256")):
        raise DA047Error("Replacement frame hash differs")
    return block


@dataclass
class ProtectedBoundaryMachine:
    """DA-046 registers with atomic, capacity-nonincreasing current replacement."""

    current: str | None = None
    retained: str | None = None
    peak_chars: int = 0
    substitutions: int = 0
    rejections: int = 0

    def _measure(self) -> None:
        current = len(self.current) if self.current is not None else 0
        retained = len(self.retained) if self.retained is not None else 0
        if current > REGISTER_CAP or retained > REGISTER_CAP:
            raise DA047Error("Register cap exceeded")
        self.peak_chars = max(self.peak_chars, current + retained)
        if self.peak_chars > GENERAL_PEAK_CAP:
            raise DA047Error("General peak cap exceeded")

    def next(self, action: Mapping[str, Any]) -> None:
        if str(action.get("kind")) == "OVERFLOW":
            self.current = None
        else:
            self.current = _block(action)
        self._measure()

    def keep(self) -> None:
        if self.current is None:
            raise DA047Error("KEEP requires a current frame")
        self.retained = self.current
        self.current = None
        self._measure()

    def substitute_current(self, action: Mapping[str, Any]) -> bool:
        if self.current is None:
            self.rejections += 1
            return False
        previous = self.current
        retained = self.retained
        try:
            replacement = _block(action)
        except (DA047Error, TypeError, ValueError):
            self.rejections += 1
            return False
        if len(replacement) > len(previous):
            self.rejections += 1
            return False
        self.current = replacement
        try:
            self._measure()
        except DA047Error:
            self.current = previous
            self.retained = retained
            self.rejections += 1
            return False
        if self.retained != retained:
            raise DA047Error("Retained frame mutated during substitution")
        self.substitutions += 1
        return True


__all__ = ["DA047Error", "ProtectedBoundaryMachine"]

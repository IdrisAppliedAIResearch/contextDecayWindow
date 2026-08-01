"""The append-only episode store and its budgeted context constructor.

Skeleton stage: the API is final, the implementations land with the
component moves that back them.
"""

from __future__ import annotations

from pathlib import Path

from ._config import EpisodicConfig
from ._report import ContextReport


class EpisodeStore:
    """Append-only conversational memory with pure context construction."""

    def __init__(
        self,
        path: str | Path,
        config: EpisodicConfig | None = None,
        *,
        embedder=None,
        override_config: bool = False,
    ) -> None:
        raise NotImplementedError("lands with the store move")

    def append(self, role: str, content: str) -> None:
        raise NotImplementedError("lands with the store move")

    def context(self, query: str, budget: int) -> tuple[str, ContextReport]:
        raise NotImplementedError("lands with the retrieval move")

    def close(self) -> None:
        raise NotImplementedError("lands with the store move")

"""episodic - append-only conversational memory with budgeted retrieval.

The installable surface is three symbols::

    from episodic import EpisodeStore, ContextReport, EpisodicConfig

    store = EpisodeStore(path, config=EpisodicConfig())
    store.append(role, content)
    block, report = store.context(query, budget)
    store.close()

``store.context()`` is a pure function of (store state, query, budget):
no mutation, no inference calls, no network. Same inputs, same output,
byte-identical. Everything not exported here is private.
"""

from ._config import EpisodicConfig
from ._report import ContextReport
from ._store import EpisodeStore

__version__ = "0.1.0"

__all__ = ["EpisodeStore", "ContextReport", "EpisodicConfig"]

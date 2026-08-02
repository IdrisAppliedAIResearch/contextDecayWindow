"""Exception types raised by the episodic package."""


class EpisodicError(Exception):
    """Base class for every error the package raises deliberately."""


class ConfigMismatchError(EpisodicError):
    """A store was reopened with a config that differs from the one stored.

    A store's numbers are only meaningful under the config that produced
    them. Pass ``override_config=True`` only when that break is intended.
    """


class CallShapeError(EpisodicError):
    """The embedder no longer reproduces the pinned sentinel vector.

    The carried embedder returns materially different vectors for the same
    text depending on how the call is shaped (one text per call versus a
    batch), at cosine agreement above 0.9998. Numbers produced under one
    shape are not comparable to numbers produced under another. See DX-001.
    """


class TurnOrderError(EpisodicError):
    """``append`` was called out of the strict user/assistant alternation."""


class StoreCorruptError(EpisodicError):
    """The store failed SQLite's integrity check when it was opened.

    Raised instead of serving queries from a damaged file. A torn write is
    recoverable through the journal; a file damaged from outside the
    database is not, and it still opens. This makes that case loud at the
    one moment a caller can act on it (CC-004).
    """


class EmbeddingDriftError(EpisodicError):
    """A stored embedding no longer reproduces from its own source text.

    Stored vectors and freshly computed query vectors have to live in the
    same space or every cosine in the store is meaningless. See DX-001 for
    what makes this a live hazard rather than a theoretical one.
    """

"""Call and token accounting, measured rather than cited.

``HH_001_DEVELOPMENT_PLAN.md`` §5: this component's zero is architectural and is
not a finding. What is worth measuring is Mem0's observed count against the
``1 + n`` per message pair its paper describes — a figure this programme has
read but never watched.

The shim also enforces the other direction: if the A2 memory path ever makes a
generative call, that is a defect in the arm and the run must stop rather than
report a zero it did not earn.
"""

from __future__ import annotations

import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator


class HH001CostError(RuntimeError):
    pass


@dataclass
class Ledger:
    """Counts for one arm, split by phase."""

    arm: str
    generative_calls: Counter = field(default_factory=Counter)
    embedding_calls: Counter = field(default_factory=Counter)
    prompt_tokens: Counter = field(default_factory=Counter)
    completion_tokens: Counter = field(default_factory=Counter)
    seconds: Counter = field(default_factory=Counter)

    def as_dict(self) -> dict[str, Any]:
        phases = sorted(
            set(self.generative_calls)
            | set(self.embedding_calls)
            | set(self.seconds)
        )
        return {
            "arm": self.arm,
            "total_generative_calls": sum(self.generative_calls.values()),
            "total_embedding_calls": sum(self.embedding_calls.values()),
            "total_prompt_tokens": sum(self.prompt_tokens.values()),
            "total_completion_tokens": sum(self.completion_tokens.values()),
            "total_seconds": sum(self.seconds.values()),
            "by_phase": {
                phase: {
                    "generative_calls": self.generative_calls[phase],
                    "embedding_calls": self.embedding_calls[phase],
                    "prompt_tokens": self.prompt_tokens[phase],
                    "completion_tokens": self.completion_tokens[phase],
                    "seconds": self.seconds[phase],
                }
                for phase in phases
            },
        }


class CountingClient:
    """Wraps any callable that makes a generative call.

    ``phase`` is the label the count lands under — ``ingest``, ``query``,
    ``read`` or ``judge`` — so the report can say where an arm spent its calls
    and not merely how many it made.
    """

    def __init__(self, delegate: Callable[..., Any], ledger: Ledger, phase: str) -> None:
        self._delegate = delegate
        self._ledger = ledger
        self._phase = phase

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = self._delegate(*args, **kwargs)
        elapsed = time.perf_counter() - start
        self._ledger.generative_calls[self._phase] += 1
        self._ledger.seconds[self._phase] += elapsed
        tokens = _token_counts(result)
        if tokens is not None:
            prompt_tokens, completion_tokens = tokens
            self._ledger.prompt_tokens[self._phase] += prompt_tokens
            self._ledger.completion_tokens[self._phase] += completion_tokens
        return result


class CountingEmbedder:
    """Wraps an embedder so embedding calls are counted separately.

    Kept apart from generative calls on purpose. Conflating the two would let
    the headline ``zero generative calls`` absorb an embedding count, and
    ``DO_NOT_WRITE.md`` item 1 exists because that sentence was written once
    already.
    """

    def __init__(self, delegate: Callable[[str], Any], ledger: Ledger, phase: str) -> None:
        self._delegate = delegate
        self._ledger = ledger
        self._phase = phase

    def __call__(self, text: str) -> Any:
        start = time.perf_counter()
        result = self._delegate(text)
        self._ledger.embedding_calls[self._phase] += 1
        self._ledger.seconds[self._phase] += time.perf_counter() - start
        return result


def _token_counts(result: Any) -> tuple[int, int] | None:
    if isinstance(result, dict):
        usage = result.get("usage")
        if isinstance(usage, dict):
            return (
                int(usage.get("prompt_tokens", 0)),
                int(usage.get("completion_tokens", 0)),
            )
        if "tokens_predicted" in result:
            return (
                int(result.get("tokens_evaluated", 0)),
                int(result.get("tokens_predicted", 0)),
            )
    output_tokens = getattr(result, "output_tokens", None)
    if isinstance(output_tokens, int):
        return (0, output_tokens)
    return None


def assert_zero_generative(ledger: Ledger, phases: tuple[str, ...] = ("ingest", "query")) -> None:
    """Stop if a nominally call-free memory path made a generative call.

    The claim is architectural, so a non-zero count here is not a surprising
    result to report — it is a broken arm.
    """
    offending = {
        phase: ledger.generative_calls[phase]
        for phase in phases
        if ledger.generative_calls[phase]
    }
    if offending:
        raise HH001CostError(
            f"{ledger.arm} made generative calls in a call-free memory path: {offending}"
        )


@contextmanager
def timed(ledger: Ledger, phase: str) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        ledger.seconds[phase] += time.perf_counter() - start


__all__ = [
    "CountingClient",
    "CountingEmbedder",
    "HH001CostError",
    "Ledger",
    "assert_zero_generative",
    "timed",
]

"""The five memory layers HH-001 compares.

Every arm answers one question: given a conversation and a query, what text does
the reader get? Each returns a :class:`MemoryBlock` whose ``text`` is what goes
into the prompt, so the only thing that varies downstream is the block.

The budget is measured with ``len()`` on the exact string handed to the reader,
per ``HH_001_DEVELOPMENT_PLAN.md`` §4. Arms fill it in their own selection order
and truncate at the cap; nothing is reordered to help any arm.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, Sequence

import numpy as np

from analysis.hh001_corpus import Conversation, Item
from analysis.nf004_mechanism import Candidate, pack, ranking_orders

#: Joins candidates inside a rendered block. One blank line, so a pair boundary
#: is visible to the reader without introducing tokens that look like markup.
BLOCK_SEPARATOR = "\n\n"


class HH001ArmError(RuntimeError):
    pass


@dataclass(frozen=True)
class MemoryBlock:
    """What one arm delivers for one query."""

    arm: str
    text: str
    truncated: bool
    units_delivered: int
    units_available: int
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def chars(self) -> int:
        return len(self.text)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


class Embedder(Protocol):
    def __call__(self, text: str) -> np.ndarray: ...


class Arm(Protocol):
    name: str

    def block(self, item: Item, conversation: Conversation, budget: int) -> MemoryBlock:
        ...


def _pack_texts(texts: Sequence[str], budget: int) -> tuple[list[str], bool]:
    """Fill the budget in the given order, skipping what does not fit.

    Skip-on-overflow rather than stop-on-overflow, matching NF-004's packer: a
    single oversized unit must not end the fill and strand the budget.
    """
    selected: list[str] = []
    used = 0
    skipped = False
    for index, text in enumerate(texts):
        cost = len(text) + (len(BLOCK_SEPARATOR) if selected else 0)
        if used + cost > budget:
            skipped = True
            continue
        used += cost
        selected.append(text)
    return selected, skipped


# --------------------------------------------------------------------------
# A0 — no memory
# --------------------------------------------------------------------------


class NoMemoryArm:
    """The floor. Measures how much the reader answers from pretraining.

    LoCoMo has been public since February 2024, so a high score here means the
    reader has seen the corpus and no memory layer is discriminable.
    """

    name = "A0_NO_MEMORY"

    def block(self, item: Item, conversation: Conversation, budget: int) -> MemoryBlock:
        return MemoryBlock(
            arm=self.name,
            text="",
            truncated=False,
            units_delivered=0,
            units_available=0,
        )


# --------------------------------------------------------------------------
# A1 — full context
# --------------------------------------------------------------------------


class FullContextArm:
    """The ceiling: the whole conversation, unbudgeted.

    Holdout conversations run 45,616 to 90,034 characters, so this arm can
    exceed the reader's context window. It never silently truncates: the
    reader's usable character allowance is passed in and any shortfall is
    recorded on the block, because a truncated ceiling is not a ceiling.
    """

    name = "A1_FULL_CONTEXT"

    def __init__(self, reader_char_allowance: int | None = None) -> None:
        self.reader_char_allowance = reader_char_allowance

    def block(self, item: Item, conversation: Conversation, budget: int) -> MemoryBlock:
        text = conversation.full_text
        truncated = False
        allowance = self.reader_char_allowance
        if allowance is not None and len(text) > allowance:
            text = text[:allowance]
            truncated = True
        return MemoryBlock(
            arm=self.name,
            text=text,
            truncated=truncated,
            units_delivered=conversation.turn_count,
            units_available=conversation.turn_count,
            detail={
                "unbudgeted": True,
                "source_chars": conversation.chars,
                "reader_char_allowance": allowance,
            },
        )


# --------------------------------------------------------------------------
# A2 — this component, frozen at NF-004 P_PAIR_RANK
# --------------------------------------------------------------------------


class CdwPairArm:
    """This component, frozen at NF-004's confirmed ``P_PAIR_RANK``.

    Ranking and packing come from ``analysis.nf004_mechanism`` unchanged. This
    class only renders the delivered candidates into a block; it makes no
    selection decision of its own, so nothing here can drift from the mechanism
    NF-004 confirmed.
    """

    name = "A2_CDW_PAIR"

    def __init__(self, embed: Embedder) -> None:
        self._embed = embed

    def block(self, item: Item, conversation: Conversation, budget: int) -> MemoryBlock:
        sources = conversation.record.candidates
        candidates: list[Candidate] = [source.candidate for source in sources]
        if not candidates:
            raise HH001ArmError(f"{conversation.sample_id} produced no candidates")
        matrix = np.stack([self._embed(c.text) for c in candidates])
        query_vector = self._embed(item.question)
        _, pair_order = ranking_orders(candidates, matrix, query_vector)
        delivery = pack(candidates, pair_order, budget)

        by_identity = {c.identity: c for c in candidates}
        texts = [by_identity[identity].text for identity in delivery.selected]
        return MemoryBlock(
            arm=self.name,
            text=BLOCK_SEPARATOR.join(texts),
            truncated=len(delivery.selected) < len(candidates),
            units_delivered=len(delivery.selected),
            units_available=len(candidates),
            detail={
                "packed_chars": delivery.packed_chars,
                "selected": list(delivery.selected),
                "ranking": "P_PAIR_RANK",
            },
        )


# --------------------------------------------------------------------------
# A4 — naive chunked retrieval (defined before A3 so the control reads first)
# --------------------------------------------------------------------------


def chunk_text(text: str, size: int, overlap: int) -> tuple[str, ...]:
    """Fixed-width character chunks with overlap.

    Deliberately the dumbest thing that works: no sentence detection, no turn
    awareness. A4 is a control, and a control that knows about turn boundaries
    is already halfway to being a treatment.
    """
    if size <= 0:
        raise HH001ArmError("Chunk size must be positive")
    if not 0 <= overlap < size:
        raise HH001ArmError("Chunk overlap must be non-negative and below the size")
    if not text:
        return ()
    stride = size - overlap
    chunks = [text[start : start + size] for start in range(0, len(text), stride)]
    while len(chunks) > 1 and not chunks[-1].strip():
        chunks.pop()
    return tuple(chunks)


class RagFixedArm:
    """Chunk, embed, rank by cosine, fill the budget.

    Its parameters are fixed by convention before the run and never adjusted
    after seeing its score: a control that is tuned is not a control.
    """

    name = "A4_RAG_FIXED"

    def __init__(
        self,
        embed: Embedder,
        chunk_size: int = 1_000,
        chunk_overlap: int = 200,
        top_k: int | None = None,
    ) -> None:
        self._embed = embed
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k

    def block(self, item: Item, conversation: Conversation, budget: int) -> MemoryBlock:
        chunks = chunk_text(conversation.full_text, self.chunk_size, self.chunk_overlap)
        if not chunks:
            raise HH001ArmError(f"{conversation.sample_id} produced no chunks")
        matrix = np.stack([self._embed(chunk) for chunk in chunks])
        query_vector = self._embed(item.question)
        norms = np.linalg.norm(matrix, axis=1)
        if np.any(norms == 0.0):
            raise HH001ArmError("Zero-norm chunk embedding")
        query_norm = float(np.linalg.norm(query_vector))
        if query_norm == 0.0:
            raise HH001ArmError("Zero-norm query embedding")
        scores = (matrix / norms[:, None]) @ (query_vector / query_norm)
        order = sorted(range(len(chunks)), key=lambda i: (-float(scores[i]), i))
        if self.top_k is not None:
            order = order[: self.top_k]
        ranked = [chunks[i] for i in order]
        selected, skipped = _pack_texts(ranked, budget)
        return MemoryBlock(
            arm=self.name,
            text=BLOCK_SEPARATOR.join(selected),
            truncated=skipped or len(selected) < len(chunks),
            units_delivered=len(selected),
            units_available=len(chunks),
            detail={
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "top_k": self.top_k,
            },
        )


# --------------------------------------------------------------------------
# A3 — Mem0
# --------------------------------------------------------------------------

MEM0_IMPORT_HINT = (
    "The Mem0 arm needs the `mem0ai` package, which is not installed. "
    "Installing it pulls a large dependency tree into this virtual environment "
    "and can move the pinned versions the rest of the programme's results were "
    "produced under. Install it deliberately, in a separate step, and re-run "
    "the full suite afterwards to confirm the 1,832-test baseline still holds."
)


def mem0_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("mem0") is not None


class Mem0Arm:
    """Mem0, pinned version, configured onto this programme's local models.

    Two configuration choices are forced by the plan and are not defaults:

    * the embedder is the carried ``Qwen3-Embedding-0.6B-Q8_0`` (§4), so the
      contrast is memory architecture rather than embedder quality;
    * the LLM is the local reader, so no arm runs on a substrate the others
      do not.

    Both are supported Mem0 configuration, not a patch. ``mem0`` is imported
    lazily so that every other arm, and the whole endpoint and statistics path,
    stays importable and testable on a machine where Mem0 is absent.
    """

    name = "A3_MEM0"

    def __init__(
        self,
        client_factory: Callable[[], Any],
        *,
        user_id: str = "hh001",
        search_limit: int = 100,
    ) -> None:
        self._client_factory = client_factory
        self._client: Any | None = None
        self.user_id = user_id
        self.search_limit = search_limit

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    def ingest(self, conversation: Conversation) -> dict[str, Any]:
        """Write one conversation into Mem0's store, pair by pair.

        Returns the observed ingestion shape. The `1 + n` generative calls per
        message pair figure is read from Mem0's paper and has never been
        observed here; the caller records what actually happened.
        """
        added = 0
        for source in conversation.record.candidates:
            self.client.add(
                source.candidate.text,
                user_id=f"{self.user_id}-{conversation.sample_id}",
            )
            added += 1
        return {"pairs_ingested": added, "sample_id": conversation.sample_id}

    def block(self, item: Item, conversation: Conversation, budget: int) -> MemoryBlock:
        results = self.client.search(
            item.question,
            user_id=f"{self.user_id}-{conversation.sample_id}",
            limit=self.search_limit,
        )
        memories = _mem0_memory_texts(results)
        selected, skipped = _pack_texts(memories, budget)
        return MemoryBlock(
            arm=self.name,
            text=BLOCK_SEPARATOR.join(selected),
            truncated=skipped or len(selected) < len(memories),
            units_delivered=len(selected),
            units_available=len(memories),
            detail={"search_limit": self.search_limit},
        )


def _mem0_memory_texts(results: Any) -> list[str]:
    """Pull memory strings out of whatever shape Mem0's search returned.

    Mem0 has returned both a bare list and a ``{"results": [...]}`` envelope
    across versions, and the text has lived under ``memory`` and under ``text``.
    Accepting the known shapes and refusing everything else is deliberate: a
    silently-empty block would read downstream as an arm that retrieved nothing,
    which is a mechanism result, not a parse failure.
    """
    if isinstance(results, dict):
        rows = results.get("results")
        if rows is None:
            raise HH001ArmError(f"Unrecognized Mem0 search envelope: {sorted(results)}")
    else:
        rows = results
    if not isinstance(rows, (list, tuple)):
        raise HH001ArmError(f"Unrecognized Mem0 search result type: {type(rows)!r}")

    texts: list[str] = []
    for row in rows:
        if isinstance(row, str):
            texts.append(row)
            continue
        if not isinstance(row, dict):
            raise HH001ArmError(f"Unrecognized Mem0 memory row type: {type(row)!r}")
        for key in ("memory", "text", "content"):
            value = row.get(key)
            if isinstance(value, str):
                texts.append(value)
                break
        else:
            raise HH001ArmError(f"Mem0 memory row has no text field: {sorted(row)}")
    return texts


__all__ = [
    "BLOCK_SEPARATOR",
    "Arm",
    "CdwPairArm",
    "Embedder",
    "FullContextArm",
    "HH001ArmError",
    "MEM0_IMPORT_HINT",
    "Mem0Arm",
    "MemoryBlock",
    "NoMemoryArm",
    "RagFixedArm",
    "chunk_text",
    "mem0_available",
]

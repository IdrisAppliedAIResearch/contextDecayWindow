"""The memory layers HH-002 puts through the paper-era harness.

Two of these arms exist to reproduce published rows and must match the
upstream implementation: ``FullContextArm`` is ``--chunk_size -1`` and
``RagArm`` is ``--chunk_size 500 --num_chunks 1``, both from
``evaluation/src/rag.py``.  ``CdwArm`` is this programme's component at the
same seam.  ``NoMemoryArm`` is the floor, which the upstream harness has no
equivalent of and which ``HH_002_IMPLEMENTATION.md`` §3 requires.

Every arm returns a ``context`` string.  The harness then renders it into
``rag.py``'s prompt and sends it to the same model with the same system
message.  Nothing downstream of ``context`` differs between arms - that is
what makes the numbers comparable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol, Sequence

import numpy as np

from analysis.hh001_arms import BLOCK_SEPARATOR, _pack_texts
from analysis.hh002_dataset import Conversation, Question

#: Upstream ``RAGManager`` defaults, from ``evaluation/Makefile``:
#: ``run-rag`` is ``--chunk_size 500 --num_chunks 1``.
RAG_CHUNK_TOKENS = 500
RAG_NUM_CHUNKS = 1

#: ``rag.py::search`` joins multiple chunks with this.  With ``k=1`` it is
#: never reached, and it is kept only so the port is complete.
RAG_CHUNK_JOIN = "\n<->\n"


class HH002ArmError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Ranking: NF-004's mechanism, generalised in dimension only
# --------------------------------------------------------------------------


def rank_pairs(
    candidates: Sequence["PairCandidate"],
    candidate_vectors: np.ndarray,
    query_vector: np.ndarray,
) -> tuple[int, ...]:
    """``nf004_mechanism.ranking_orders``'s ``pair_order``, at any dimension.

    The frozen function guards ``shape == (n, 1024)`` because NF-004's
    embedder is 1024-dimensional.  ``text-embedding-3-small`` is 1536, and the
    guard - not the algorithm - is what refuses it: the body is a cosine
    against a unit query vector, then a sort keyed by
    ``(-score, session_order, pair_order)``.

    This is that body with the guard parameterised.  NF-004's module is not
    modified.  ``test_hh002_arms`` asserts this function returns the frozen
    function's ``pair_order`` for random 1024-dimensional input, so the
    transcription is enforced rather than asserted in prose.
    """
    matrix = np.asarray(candidate_vectors, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[0] != len(candidates):
        raise HH002ArmError(
            f"Candidate matrix {matrix.shape} does not match "
            f"{len(candidates)} candidates"
        )
    query = np.asarray(query_vector, dtype=np.float32)
    if query.shape != (matrix.shape[1],):
        raise HH002ArmError(
            f"Query vector {query.shape} does not match candidate dimension "
            f"{matrix.shape[1]}"
        )
    norms = np.linalg.norm(matrix, axis=1)
    if np.any(norms == 0.0):
        raise HH002ArmError("Zero-norm candidate embedding")
    query_norm = float(np.linalg.norm(query))
    if query_norm == 0.0:
        raise HH002ArmError("Zero-norm embedding")

    scores = (matrix / norms[:, None]) @ (query / query_norm)
    return tuple(
        sorted(
            range(len(candidates)),
            key=lambda index: (
                -float(scores[index]),
                candidates[index].session_order,
                candidates[index].pair_order,
            ),
        )
    )


@dataclass(frozen=True)
class PairCandidate:
    """One adjacent-turn pair, the unit NF-004 confirmed."""

    text: str
    session_order: int
    pair_order: int
    dia_ids: tuple[str, ...]


def build_pair_candidates(
    conversation: Conversation, with_timestamps: bool
) -> tuple[PairCandidate, ...]:
    """Non-overlapping adjacent-turn pairs, within session, in order.

    This is ``nf004_measurement.adapt_split``'s candidate construction:
    ``range(0, len(turns), 2)`` over each session's turns, joined by newline.

    The rendering of a turn is the argument.  NF-004 renders
    ``"{speaker}: {text}"``, because its endpoint was evidence delivery and
    nothing in it needed a date.  The harness renders
    ``"{timestamp} | {speaker}: {text}"`` for every arm it runs, and LoCoMo's
    category 2 is entirely temporal - "When did X happen?" is unanswerable
    from undated text however well it is retrieved.  Handing this arm undated
    turns while the harness hands RAG dated ones would be a handicap the study
    invented, so the primary arm takes the harness's convention and the
    undated variant runs beside it as a registered secondary.
    """
    by_session: dict[int, list] = {}
    for turn in conversation.turns:
        by_session.setdefault(turn.session_order, []).append(turn)

    candidates: list[PairCandidate] = []
    for session_order in sorted(by_session):
        turns = by_session[session_order]
        for pair_order, start in enumerate(range(0, len(turns), 2)):
            members = turns[start : start + 2]
            if with_timestamps:
                text = "\n".join(
                    f"{t.timestamp} | {t.speaker}: {t.text}" for t in members
                )
            else:
                text = "\n".join(f"{t.speaker}: {t.text}" for t in members)
            candidates.append(
                PairCandidate(
                    text=text,
                    session_order=session_order,
                    pair_order=pair_order,
                    dia_ids=tuple(t.dia_id for t in members),
                )
            )
    return tuple(candidates)


# --------------------------------------------------------------------------
# Arm protocol
# --------------------------------------------------------------------------


class Arm(Protocol):
    name: str

    def prepare(self, conversation: Conversation, client: Any) -> Any: ...

    def context(
        self, state: Any, question: Question, client: Any
    ) -> tuple[str, float, dict[str, Any]]: ...


# --------------------------------------------------------------------------
# G-CTRL arms: the two published rows this rig has to reproduce
# --------------------------------------------------------------------------


class FullContextArm:
    """``--technique_type rag --chunk_size -1`` - published at 72.90%.

    ``create_chunks`` returns ``[documents], []`` when ``chunk_size == -1``,
    and ``process_all_conversations`` then takes ``chunks[0]`` with
    ``search_time = 0``.  No embedding is computed and no retrieval happens.
    """

    name = "A_FULL"

    #: Rebuilding costs no API call, so the context cache is skipped.
    cacheable_contexts = False

    def prepare(self, conversation: Conversation, client: Any) -> Any:
        return conversation.clean_chat_history()

    def context(
        self, state: Any, question: Question, client: Any
    ) -> tuple[str, float, dict[str, Any]]:
        return state, 0.0, {"units_delivered": 1, "chars": len(state)}


class RagArm:
    """``--chunk_size 500 --num_chunks 1`` - published at 60.53%.

    ``create_chunks`` tokenises the whole cleaned history with
    ``tiktoken.encoding_for_model(EMBEDDING_MODEL)``, cuts it into
    ``chunk_size``-token slices with no overlap, and embeds each slice.
    ``search`` embeds the query and takes ``np.argmax`` of the cosines.
    """

    name = "A_RAG"

    def __init__(
        self, chunk_tokens: int = RAG_CHUNK_TOKENS, k: int = RAG_NUM_CHUNKS
    ) -> None:
        self.chunk_tokens = chunk_tokens
        self.k = k

    def prepare(self, conversation: Conversation, client: Any) -> Any:
        import tiktoken

        encoding = tiktoken.encoding_for_model(client.embedding_model)
        document = conversation.clean_chat_history()
        tokens = encoding.encode(document)
        chunks = [
            encoding.decode(tokens[i : i + self.chunk_tokens])
            for i in range(0, len(tokens), self.chunk_tokens)
        ]
        # One call per chunk, as ``create_chunks`` does.  Batching would be
        # cheaper and is used for this study's own arm, but this arm exists to
        # reproduce a published number and an embedding request's batch shape
        # is known in this programme to move the vectors it returns.
        vectors = np.asarray(
            [client.embed(chunk) for chunk in chunks], dtype=np.float32
        )
        return chunks, vectors

    def context(
        self, state: Any, question: Question, client: Any
    ) -> tuple[str, float, dict[str, Any]]:
        chunks, vectors = state
        started = time.time()
        query = np.asarray(client.embed(question.question), dtype=np.float32)
        # Upstream computes a plain cosine per chunk in a list comprehension.
        sims = (vectors @ query) / (
            np.linalg.norm(vectors, axis=1) * np.linalg.norm(query)
        )
        if self.k == 1:
            top = [int(np.argmax(sims))]
        else:
            top = [int(i) for i in np.argsort(sims)[-self.k :][::-1]]
        text = RAG_CHUNK_JOIN.join(chunks[i] for i in top)
        return (
            text,
            time.time() - started,
            {"units_delivered": len(top), "units_available": len(chunks),
             "chars": len(text)},
        )


# --------------------------------------------------------------------------
# The component under test
# --------------------------------------------------------------------------


class CdwArm:
    """This programme's component, frozen at NF-004's ``P_PAIR_RANK``.

    Ranking is ``rank_pairs`` - NF-004's ordering, dimension-generalised.
    Packing is HH-001's ``_pack_texts``, imported rather than reimplemented so
    the two studies cannot drift apart: it charges the block separator, so the
    delivered string is what the budget measures.
    """

    def __init__(
        self,
        budget: int,
        with_timestamps: bool = True,
        name: str | None = None,
    ) -> None:
        self.budget = budget
        self.with_timestamps = with_timestamps
        self.name = name or (
            f"A_CDW_{budget}" + ("" if with_timestamps else "_NOTS")
        )

    def prepare(self, conversation: Conversation, client: Any) -> Any:
        candidates = build_pair_candidates(conversation, self.with_timestamps)
        if not candidates:
            raise HH002ArmError(f"{conversation.sample_id} produced no candidates")
        vectors = np.asarray(
            client.embed_many([c.text for c in candidates]), dtype=np.float32
        )
        return candidates, vectors

    def context(
        self, state: Any, question: Question, client: Any
    ) -> tuple[str, float, dict[str, Any]]:
        candidates, vectors = state
        started = time.time()
        query = np.asarray(client.embed(question.question), dtype=np.float32)
        order = rank_pairs(candidates, vectors, query)
        ranked = [candidates[i].text for i in order]
        selected, skipped = _pack_texts(ranked, self.budget)
        text = BLOCK_SEPARATOR.join(selected)
        return (
            text,
            time.time() - started,
            {
                "units_delivered": len(selected),
                "units_available": len(candidates),
                "chars": len(text),
                "truncated": skipped or len(selected) < len(candidates),
                "ranking": "P_PAIR_RANK",
                "separator_charged": True,
            },
        )


class NoMemoryArm:
    """The floor.  Not an upstream arm.

    LoCoMo has been public since February 2024 and gpt-4o-mini's training data
    predates this run.  If this arm scores above zero the model knows the
    corpus, and every row of the published table - theirs included - needs
    re-reading.  HH-001's floor scored zero on a local 27B reader; that says
    nothing about this one.
    """

    name = "A_NONE"

    #: Rebuilding costs no API call, so the context cache is skipped.
    cacheable_contexts = False

    def prepare(self, conversation: Conversation, client: Any) -> Any:
        return None

    def context(
        self, state: Any, question: Question, client: Any
    ) -> tuple[str, float, dict[str, Any]]:
        return "", 0.0, {"units_delivered": 0, "chars": 0}


__all__ = [
    "Arm",
    "CdwArm",
    "FullContextArm",
    "HH002ArmError",
    "NoMemoryArm",
    "PairCandidate",
    "RAG_CHUNK_TOKENS",
    "RagArm",
    "build_pair_candidates",
    "rank_pairs",
]

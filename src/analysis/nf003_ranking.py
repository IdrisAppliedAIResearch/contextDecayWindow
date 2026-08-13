"""NF-003 Part 1: is the evidence ranked badly, or is it not similar at all?

NF-002 changed the packing unit and left the ranking unit alone - episodes still
inherit their session's rank. 74 of the 90 baseline misses survived every unit
and packing change, so the ranking is what is left. Two mechanisms explain that,
and they call for opposite successors.

**H1, dilution.** A session runs 13,000-23,000 characters and typically holds
one relevant episode. Whatever score the session carries flattens that episode
against ~95% unrelated conversation, so the evidence sinks. Ranking at episode
granularity would lift it.

**H2, similarity failure.** For multi-session and temporal-reasoning questions
the evidence episode may simply not resemble the query - "how many days between
X and Y" shares little surface with either evidence turn. Then no unit change
helps and the metric is the limit. EC-001 already found multi-session and
temporal at 0/20 in Tier 2.

The discriminator is not "try it and see whether the number moves". It is the
**cosine rank of the true evidence episode**, measured directly. Shallow ranks
mean the evidence was findable and the unit hid it; deep ranks mean it was never
findable by this metric.

Evidence is identified at episode level by LongMemEval's own `has_answer` turn
flag, not by the session-level `answer_session_ids` NF-002 used.

**Anchor.** EC-002's session ranking is *not* reconstructible from these episode
vectors: mean pooling reproduces 5.2% of positions and max pooling 9.0%, so
whatever EC-002 ranked, it was not a pooling of these. That is recorded rather
than worked around, and the anchor used instead is the direct one CC-006 was
built to provide - every composed episode text hits the cache by exact content,
zero misses, so the vectors are the ones the program's embedder produced for
those exact strings.

Zero model calls.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from analysis import nf002_streams as streams_module

SCHEMA = "nf003-ranking-v1"
CACHE = Path(
    "experiments/external/longmemeval/runs/ec002_k_first/ec002_exact_solo_embeddings.db"
)
BUDGET_CHARS = streams_module.BUDGET_CHARS


class RankingError(RuntimeError):
    pass


@dataclass
class EmbeddingCache:
    """Read-only, content-addressed, miss-is-fatal.

    CC-006's rule: a read-only miss fails rather than silently embedding, so a
    run cannot quietly acquire a vector the committed cache never held.
    """

    connection: sqlite3.Connection
    hits: int = 0

    @classmethod
    def open(cls, repository_root: Path) -> "EmbeddingCache":
        path = repository_root / CACHE
        if not path.is_file():
            raise RankingError(f"embedding cache missing: {path}")
        return cls(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True))

    def vector(self, text: str) -> np.ndarray:
        row = self.connection.execute(
            "select embedding from cache where text=?", (text,)
        ).fetchone()
        if row is None:
            raise RankingError(f"cache miss on {len(text)} characters; this run makes no model calls")
        self.hits += 1
        return np.frombuffer(row[0], dtype=np.float32).astype(np.float64)


def unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        raise RankingError("zero-norm vector")
    return vector / norm


@dataclass(frozen=True)
class Episode:
    session_id: str
    index: int
    text: str
    chars: int
    is_evidence: bool


def compose_episodes(item: dict[str, Any]) -> list[Episode]:
    """Every episode of the haystack, with turn-level evidence flags.

    `has_answer` marks the turn that carries the answer. An episode is a
    user/assistant pair, so it is evidence when either of its turns is flagged.
    """
    out: list[Episode] = []
    for session_id, turns in zip(item["haystack_session_ids"], item["haystack_sessions"]):
        index = 0
        for i in range(0, len(turns) - 1, 2):
            first, second = turns[i], turns[i + 1]
            if first.get("role") != "user" or second.get("role") != "assistant":
                continue
            text = streams_module.episode_text(
                first.get("content", ""), second.get("content", "")
            )
            out.append(
                Episode(
                    session_id=session_id,
                    index=index,
                    text=text,
                    chars=len(text),
                    is_evidence=bool(first.get("has_answer") or second.get("has_answer")),
                )
            )
            index += 1
    return out


def episode_ranking(
    cache: EmbeddingCache, question: str, episodes: list[Episode]
) -> tuple[np.ndarray, np.ndarray]:
    """Cosine of the question against each episode, and the ordering it implies.

    Ties break on episode order, which is stable and corpus-given, so the
    ranking reproduces across processes.
    """
    query = unit(cache.vector(question))
    matrix = np.vstack([unit(cache.vector(e.text)) for e in episodes])
    scores = matrix @ query
    order = np.lexsort((np.arange(len(episodes)), -scores))
    return scores, order


def pack(
    episodes: list[Episode],
    order: np.ndarray,
    answer_sessions: set[str],
    budget: int = BUDGET_CHARS,
) -> tuple[int, int]:
    """Skip-on-overflow in the given order.

    Returns (evidence sessions touched, evidence episodes delivered). Both are
    reported because they are different units and comparing across them is the
    error that produced a spurious 351-vs-396 reading on the first pass: NF-002
    counts evidence *sessions* and `has_answer` marks evidence *episodes*.
    """
    used = strict = 0
    touched: set[str] = set()
    for position in order:
        episode = episodes[int(position)]
        if used + episode.chars > budget:
            continue
        used += episode.chars
        strict += episode.is_evidence
        if episode.session_id in answer_sessions:
            touched.add(episode.session_id)
    return len(touched), strict


def analyse(repository_root: Path, dataset_path: Path | None = None) -> dict[str, Any]:
    cache = EmbeddingCache.open(repository_root)
    committed_ranking = streams_module._load_committed_ranking()
    committed_ranks = streams_module._load_committed_evidence_ranks()
    items = json.loads(
        (dataset_path or streams_module.DATASET).read_bytes().decode("utf-8")
    )

    rows: list[dict[str, Any]] = []
    no_flagged = 0
    for item in items:
        question_id = item["question_id"]
        if question_id not in committed_ranking:
            continue
        order_ids = committed_ranking[question_id]
        answer_ids = set(item["answer_session_ids"])
        # Same answerable set NF-002 used: the abstention stratum is excluded by
        # the same criterion, not by a new one.
        mine = sorted(i + 1 for i, s in enumerate(order_ids) if s in answer_ids)
        if mine != committed_ranks.get(question_id, []):
            continue

        episodes = compose_episodes(item)
        if not any(e.is_evidence for e in episodes):
            no_flagged += 1
            continue
        scores, order = episode_ranking(cache, item["question"], episodes)
        sessions_touched, episodes_delivered = pack(episodes, order, answer_ids)

        positions = {int(p): rank for rank, p in enumerate(order, start=1)}
        evidence_ranks = sorted(
            positions[i] for i, e in enumerate(episodes) if e.is_evidence
        )
        evidence_chars = sorted(e.chars for e in episodes if e.is_evidence)

        rows.append(
            {
                "question_id": question_id,
                "question_type": item.get("question_type", "unknown"),
                "episodes": len(episodes),
                "evidence_episodes": len(evidence_ranks),
                "best_evidence_rank": evidence_ranks[0],
                "best_evidence_rank_fraction": evidence_ranks[0] / len(episodes),
                "median_evidence_chars": evidence_chars[len(evidence_chars) // 2],
                "episode_ranked_sessions_touched": sessions_touched,
                "episode_ranked_episodes_delivered": episodes_delivered,
            }
        )

    return {
        "schema": SCHEMA,
        "cache_hits": cache.hits,
        "cache_misses": 0,
        "anchor": {
            "kind": "content-addressed cache coverage",
            "note": (
                "EC-002's session ranking is not reconstructible from these episode "
                "vectors: mean pooling reproduces 5.2% of positions, max pooling 9.0%. "
                "Recorded rather than worked around."
            ),
        },
        "items": len(rows),
        "items_without_turn_level_flags": no_flagged,
        "rows": rows,
    }


def write(repository_root: Path, dataset_path: Path | None = None) -> Path:
    record = analyse(repository_root, dataset_path)
    path = (
        repository_root
        / "experiments/components/biological_memory/nf_003/artifacts/part1_record.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path

"""Uncapped relevance selection with optional continuity in source order."""
from dataclasses import dataclass
import time

import numpy as np

from ._errors import EpisodicError
from ._render import render_stm_payload
from ._report import ContextReport


@dataclass(frozen=True)
class TimelineSelection:
    selected_indices: tuple[int, ...]
    recent_indices: tuple[int, ...]
    relevant_indices: tuple[int, ...]
    eligible_count: int


def _integer(value, name):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise EpisodicError(f'{name} must be a non-negative integer')


def select_timeline(episodes, scores, *, threshold=.48, recency_window_n=32,
                    through_turn=None, anchor_turn=None):
    """Union eligible relevant records, recent continuity and an explicit anchor.

    The inclusive horizon concerns recording order, never an inferred event date.
    All delivered records are sorted together; none spends a capacity allowance.
    """
    _integer(recency_window_n, 'recency_window_n')
    for name, value in [('through_turn', through_turn), ('anchor_turn', anchor_turn)]:
        if value is not None:
            _integer(value, name)
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise EpisodicError('timeline threshold must be finite and in [0, 1]')
    values = np.asarray(scores, dtype=np.float64)
    if values.shape != (len(episodes),) or not np.isfinite(values).all():
        raise EpisodicError('Expected one finite cosine per episode')
    ids = [str(e['id']) for e in episodes]
    turns = [e['turn_number'] for e in episodes]
    for turn in turns:
        _integer(turn, 'source turn')
    if len(set(ids)) != len(ids) or len(set(turns)) != len(turns):
        raise EpisodicError('Timeline requires unique episode identities and source turns')
    if anchor_turn is not None and anchor_turn not in turns:
        raise EpisodicError('anchor_turn is not a stored complete exchange')
    if anchor_turn is not None and through_turn is not None and anchor_turn > through_turn:
        raise EpisodicError('anchor_turn is after through_turn')
    eligible = sorted((i for i, turn in enumerate(turns)
                       if through_turn is None or turn <= through_turn),
                      key=lambda i: (turns[i], ids[i]))
    recent = eligible[-recency_window_n:] if recency_window_n else []
    relevant = [i for i in eligible if values[i] >= threshold]
    chosen = set(recent) | set(relevant)
    if anchor_turn is not None:
        chosen.add(turns.index(anchor_turn))
    return TimelineSelection(tuple(i for i in eligible if i in chosen),
                             tuple(recent), tuple(relevant), len(eligible))


def cosine_scores(episodes, query_embedding):
    """Float64 cosine over retained float32 embeddings, without score rescaling."""
    def array(value):
        if isinstance(value, (bytes, bytearray, memoryview)):
            value = np.frombuffer(value, dtype=np.float32)
        result = np.asarray(value, dtype=np.float64)
        if result.ndim != 1 or not result.size or not np.isfinite(result).all():
            raise EpisodicError('Expected a finite nonempty embedding vector')
        norm = np.linalg.norm(result)
        if not np.isfinite(norm) or norm == 0:
            raise EpisodicError('Expected a finite nonzero embedding norm')
        return result, norm

    query, norm = array(query_embedding)
    if not episodes:
        return np.empty(0, dtype=np.float64)
    rows = [array(e['embedding'])[0] for e in episodes]
    if any(row.shape != query.shape for row in rows):
        raise EpisodicError('Stored and query embedding dimensions differ')
    matrix = np.asarray(rows, dtype=np.float64)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix @ (query / norm)


def build_timeline_context(*, episodes, query_embedding, config,
                           through_turn=None, anchor_turn=None):
    started = time.perf_counter()
    selection = select_timeline(
        episodes, cosine_scores(episodes, query_embedding),
        threshold=config.timeline_threshold, recency_window_n=config.recency_window_n,
        through_turn=through_turn, anchor_turn=anchor_turn)
    selected = [episodes[i] for i in selection.selected_indices]
    payload = render_stm_payload([], selected)
    recent_ids = tuple(str(episodes[i]['id']) for i in selection.recent_indices)
    semantic_count = len(set(selection.relevant_indices) - set(selection.recent_indices))
    return payload, ContextReport(
        chars_delivered=len(payload), chars_wanted=len(payload),
        episodes_delivered=len(selected), episodes_dropped=0, truncated=False,
        stm_count=len(recent_ids), k_count=semantic_count, coverage_count=0,
        latency_ms=(time.perf_counter() - started) * 1000,
        pool_size=len(episodes), drop_policy='none', budget_chars=None,
        retrieval_chars_delivered=len(payload), retrieval_budget_chars=None,
        recency_count=len(recent_ids), semantic_count=semantic_count,
        recent_ids=recent_ids, recency_additive=True,
        read_policy='timeline', selected_ids=tuple(str(e['id']) for e in selected),
        eligible_count=selection.eligible_count, through_turn=through_turn,
        anchor_turn=anchor_turn, relevance_threshold=config.timeline_threshold)

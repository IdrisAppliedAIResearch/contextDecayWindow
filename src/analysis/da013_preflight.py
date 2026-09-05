"""Evidence-blind LongMemEval population and immutable direct pack for DA-013."""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
import sqlite3
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from analysis.da009_role_pattern import decode_role_pairs, role_pattern_pairs
from analysis.nf005_mechanism import Candidate, own_score_order, pack

BUDGET = 16_000
SEEDS = 16
DATASET_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
POPULATION_SHA256 = "2d29387251b109f780d7a2fe86e7a1d3244eb0f5a73515b1be1d8e7dda7e506f"
CACHE_SHA256 = "e8a31513700a0a5d1cfe34b4703bbe3c8c85dc3ca29188d7cc480c2e2417a7ad"
TOKEN = re.compile(r"[A-Za-z0-9]+")


class DA013Error(RuntimeError):
    pass


@dataclass(frozen=True)
class BlindEpisode:
    candidate: Candidate
    session_identity: str
    members: tuple[dict[str, str], dict[str, str]]


@dataclass(frozen=True)
class BlindQuestion:
    question_id: str
    question_type: str
    question: str
    episodes: tuple[BlindEpisode, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identity(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def episode_text(user: str, assistant: str) -> str:
    return f"User: {user}\nAssistant: {assistant}"


def _population_ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA013Error("NF-003 population artifact differs")
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = frozenset(str(row["question_id"]) for row in payload["rows"])
    if len(values) != 465 or int(payload["items"]) != 465:
        raise DA013Error("NF-003 population cardinality differs")
    return values


def load_blind_population(dataset_path: Path, population_path: Path) -> tuple[BlindQuestion, ...]:
    if sha256_file(dataset_path) != DATASET_SHA256:
        raise DA013Error("LongMemEval dataset differs")
    wanted = _population_ids(population_path)
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    rows = [row for row in raw if str(row.get("question_id")) in wanted]
    if {str(row["question_id"]) for row in rows} != wanted:
        raise DA013Error("DA-013 population join is incomplete")
    output = []
    for row in rows:
        question_id = str(row["question_id"])
        episodes = []
        parent_index = 0
        for session_order, (session_id, turns) in enumerate(
            zip(row["haystack_session_ids"], row["haystack_sessions"], strict=True)
        ):
            session_identity = identity(question_id, str(session_order), str(session_id))
            episode_order = 0
            for start in range(0, len(turns) - 1, 2):
                first, second = turns[start : start + 2]
                if first.get("role") != "user" or second.get("role") != "assistant":
                    continue
                user, assistant = str(first.get("content", "")), str(second.get("content", ""))
                text = episode_text(user, assistant)
                episode_id = identity(
                    question_id, session_identity, str(episode_order), "episode", text
                )
                candidate = Candidate(
                    identity=episode_id,
                    parent_index=parent_index,
                    session_order=session_order,
                    episode_order=episode_order,
                    turn_offset=-1,
                    text=text,
                    chars=len(text),
                )
                episodes.append(
                    BlindEpisode(
                        candidate,
                        session_identity,
                        (
                            {"speaker": "User", "text": user},
                            {"speaker": "Assistant", "text": assistant},
                        ),
                    )
                )
                episode_order += 1
                parent_index += 1
        output.append(
            BlindQuestion(
                question_id,
                str(row.get("question_type", "unknown")),
                str(row["question"]),
                tuple(episodes),
            )
        )
    return tuple(output)


class ReadOnlyCache:
    def __init__(self, path: Path) -> None:
        if sha256_file(path) != CACHE_SHA256:
            raise DA013Error("Retained exact-solo cache differs")
        self.connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        self.hits = 0

    def close(self) -> None:
        self.connection.close()

    def vector(self, text: str) -> np.ndarray:
        row = self.connection.execute("select embedding from cache where text=?", (text,)).fetchone()
        if row is None:
            raise DA013Error(f"Read-only vector miss for {len(text)} characters")
        self.hits += 1
        return np.frombuffer(row[0], dtype=np.float32).copy()


def _tokens(text: str) -> frozenset[str]:
    return frozenset(token.lower() for token in TOKEN.findall(text))


def _idf(records: Sequence[BlindQuestion]) -> dict[str, float]:
    documents = [_tokens(episode.candidate.text) for record in records for episode in record.episodes]
    counts = Counter(token for document in documents for token in document)
    return {token: math.log((1 + len(documents)) / (1 + count)) + 1 for token, count in counts.items()}


def _coverage(query: frozenset[str], text: str, idf: dict[str, float]) -> float:
    denominator = sum(idf.get(token, 1.0) for token in query)
    return sum(idf.get(token, 1.0) for token in query & _tokens(text)) / denominator if denominator else 0.0


def _edges(
    record: BlindQuestion, order: Sequence[int], direct_ids: frozenset[str]
) -> list[dict[str, Any]]:
    by_session: dict[str, list[int]] = {}
    for index, episode in enumerate(record.episodes):
        by_session.setdefault(episode.session_identity, []).append(index)
    emitted: set[int] = set()
    rows = []
    for seed_rank, seed in enumerate(order[:SEEDS], 1):
        members = by_session[record.episodes[seed].session_identity]
        position = members.index(seed)
        for direction, neighbor_position in ((-1, position - 1), (1, position + 1)):
            if neighbor_position < 0 or neighbor_position >= len(members):
                continue
            neighbor = members[neighbor_position]
            if record.episodes[neighbor].candidate.identity in direct_ids:
                continue
            if neighbor in emitted:
                continue
            emitted.add(neighbor)
            rows.append(
                {
                    "seed_id": record.episodes[seed].candidate.identity,
                    "neighbor_id": record.episodes[neighbor].candidate.identity,
                    "seed_rank": seed_rank,
                    "direction": direction,
                    "neighbor_index": neighbor,
                }
            )
    return rows


def build_rows(records: Sequence[BlindQuestion], cache_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    idf = _idf(records)
    cache = ReadOnlyCache(cache_path)
    rows = []
    pair_reachable = fallback_reachable = overflow_reachable = 0
    try:
        for record in records:
            candidates = tuple(episode.candidate for episode in record.episodes)
            query_vector = cache.vector(record.question)
            vectors = np.vstack([cache.vector(candidate.text) for candidate in candidates])
            order = own_score_order(candidates, vectors, query_vector)
            direct = pack(candidates, order, BUDGET)
            by_id = {episode.candidate.identity: episode for episode in record.episodes}
            direct_pairs = [by_id[value].members for value in direct.selected]
            context = role_pattern_pairs(direct_pairs)
            originals = [by_id[value].candidate.text for value in direct.selected]
            if decode_role_pairs(context) != originals or context.chars > direct.packed_chars:
                raise DA013Error("Role-pattern direct rendering is not reversible/nonexpanding")
            slack = BUDGET - context.chars
            query_tokens = _tokens(record.question)
            edge_rows = []
            for edge in _edges(record, order, frozenset(direct.selected)):
                neighbor = record.episodes[int(edge.pop("neighbor_index"))]
                pair_context = role_pattern_pairs((*direct_pairs, neighbor.members))
                pair_cost = pair_context.chars - context.chars
                member_scores = [
                    _coverage(query_tokens, member["text"], idf) for member in neighbor.members
                ]
                best_member = min(range(2), key=lambda index: (-member_scores[index], index))
                turn_text = neighbor.members[best_member]["text"]
                turn_cost = len(turn_text)
                pair_reachable += pair_cost <= slack
                fallback_reachable += pair_cost > slack and turn_cost <= slack
                overflow_reachable += pair_cost > slack
                edge_rows.append(
                    {
                        **edge,
                        "pair_cost": pair_cost,
                        "fallback_member": best_member,
                        "fallback_cost": turn_cost,
                    }
                )
            rows.append(
                {
                    "question_id": record.question_id,
                    "question_type": record.question_type,
                    "episodes": len(record.episodes),
                    "sessions": len({episode.session_identity for episode in record.episodes}),
                    "direct_ids": list(direct.selected),
                    "direct_count": len(direct.selected),
                    "original_chars": direct.packed_chars,
                    "compact_chars": context.chars,
                    "savings": direct.packed_chars - context.chars,
                    "slack": slack,
                    "default_pattern": list(context.default_pattern),
                    "edges": edge_rows,
                }
            )
    finally:
        cache.close()
    metadata = {
        "cache_hits": cache.hits,
        "idf_terms": len(idf),
        "pair_reachable_edges": pair_reachable,
        "fallback_reachable_edges": fallback_reachable,
        "overflow_edges": overflow_reachable,
    }
    return rows, metadata


def _write_rows(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(dataset_path: Path, population_path: Path, cache_path: Path, output_dir: Path) -> dict[str, Any]:
    records = load_blind_population(dataset_path, population_path)
    rows, metadata = build_rows(records, cache_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_path = output_dir / "blind_direct_and_edges.jsonl.gz"
    _write_rows(rows_path, rows)
    with tempfile.TemporaryDirectory(prefix="da013-") as directory:
        replay_rows, replay_metadata = build_rows(records, cache_path)
        replay_path = Path(directory) / rows_path.name
        _write_rows(replay_path, replay_rows)
        identical = rows_path.read_bytes() == replay_path.read_bytes() and metadata == replay_metadata
    savings = sorted(int(row["savings"]) for row in rows)
    result = {
        "schema": "da013-blind-direct-preflight-v1",
        "status": "PASS" if identical and min(savings) >= 0 and metadata["fallback_reachable_edges"] > 0 else "FAIL",
        "phase": "mechanical direct/edge seal; transferred features and scores remain unopened",
        "population": {
            "questions": len(rows),
            "episodes": sum(int(row["episodes"]) for row in rows),
            "sessions": sum(int(row["sessions"]) for row in rows),
            "question_types": dict(sorted(Counter(row["question_type"] for row in rows).items())),
        },
        "direct": {
            "selected_episodes": sum(int(row["direct_count"]) for row in rows),
            "median_savings": float(np.median(savings)),
            "min_savings": min(savings),
            "max_savings": max(savings),
            "positive_savings_questions": sum(value > 0 for value in savings),
        },
        "edges": {"total": sum(len(row["edges"]) for row in rows), **metadata},
        "selection_sha256": sha256_file(rows_path),
        "replay_byte_identical": identical,
        "calls": {"embedding": 0, "model": 0, "cache_misses": 0, "cache_mode": "read-only"},
    }
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise DA013Error("DA-013 mechanical preflight failed")
    return result


__all__ = ["DA013Error", "build_rows", "load_blind_population", "run_preflight"]

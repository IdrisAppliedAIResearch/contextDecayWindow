"""Blind frozen-query carrier utility allocations for DA-018."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from analysis.da003_edge_features import corpus_idf, tokens
from analysis.da004_pack_features import read_gzip
from analysis.da006_reserved_links import _member_maps
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da013_preflight import ReadOnlyCache, _idf, _tokens, load_blind_population, sha256_file
from analysis.da015_phrase_dictionary import encode
from analysis.da016_allocation import BUDGET, _payload_cost
from analysis.nf004_anatomy_features import load_blind_cases
from analysis.nf005_mechanism import cosine_scores

ARMS = ("PAYLOAD_COSINE", "COSINE_PER_CHAR", "MARGINAL_UTILITY")
NF_ROLE_SHA256 = "0fbe8e54d3385575749d779429488d3e1efe2e5b5815a87aa7403a4650cbf0bb"
NF_EDGE_SHA256 = "e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4"
NF_PAYLOAD_SHA256 = "51e0e648f66bf2c5a7ab6161c5fbcbc9efaadff306beb9b98ffac6a2f19d47b3"
NF_G6_SHA256 = "86690f54465e1e755ce897e7206283f29acc477bec2afead44d0a53cb742391b"
LONG_DIRECT_SHA256 = "9544fd5bc6ad85515f5cb99472cb844e2c8b9f97cd1f51a19de2d882da47ff5c"
LONG_CONTROL_SHA256 = "8ab71c95ee4cea7c78149e344ea704243cfbfa2acbfc9eddd70b105e32d39a64"


class DA018Error(RuntimeError):
    pass


def _qkey(row: Mapping[str, Any]) -> tuple[str, int]:
    return str(row["comparison_key"]), int(row["duplicate_ordinal"])


def _ekey(row: Mapping[str, Any]) -> tuple[str, int, str, str]:
    return (*_qkey(row), str(row["seed_id"]), str(row["neighbor_id"]))


def _direction(edge: Mapping[str, Any]) -> int:
    if "direction" in edge:
        return int(edge["direction"])
    return -1 if float(edge["features"]["signed_direction"]) < 0 else 1


def _tie(edge: Mapping[str, Any]) -> tuple[int, int, str]:
    rank = int(edge.get("seed_rank", edge.get("features", {}).get("seed_rank", 0)))
    return rank, 0 if _direction(edge) < 0 else 1, str(edge["neighbor_id"])


def uncovered_coverage(query: frozenset[str], payload: frozenset[str], covered: set[str],
                       idf: Mapping[str, float]) -> float:
    denominator = sum(idf.get(token, 1.0) for token in query)
    uncovered = (query & payload) - covered
    return sum(idf.get(token, 1.0) for token in uncovered) / denominator if denominator else 0.0


def utility(arm: str, cosine: float, seed_rank: int, cost: int, coverage: float) -> float:
    if arm == "PAYLOAD_COSINE":
        return cosine
    base = max(cosine, 0.0) / max(cost, 1)
    if arm == "COSINE_PER_CHAR":
        return base
    if arm == "MARGINAL_UTILITY":
        return base * (1.0 / seed_rank) * (1.0 + coverage)
    raise DA018Error(f"Unknown arm {arm}")


def _allocate(
    edges: Sequence[Mapping[str, Any]],
    arm: str,
    role: Any,
    direct_ids: Sequence[str],
    query_tokens: frozenset[str],
    idf: Mapping[str, float],
    pair_for: Callable[[str], Sequence[Mapping[str, str]]],
    selected_member: Callable[[Mapping[str, Any]], int],
    cosine_for: Callable[[Mapping[str, Any]], float],
    cost_for: Callable[[Any, Sequence[Mapping[str, str]]], int],
    initial_chars: int,
) -> dict[str, Any]:
    remaining = list(edges)
    seen = set(map(str, direct_ids))
    covered = set().union(*(tokens(str(member["text"])) for identity in direct_ids for member in pair_for(identity)))
    used = initial_chars
    actions = []
    while remaining:
        proposals = []
        for index, edge in enumerate(remaining):
            neighbor = str(edge["neighbor_id"])
            if neighbor in seen:
                proposals.append((float("inf"), _tie(edge), index, None))
                continue
            pair = pair_for(neighbor)
            full_cost = cost_for(role, pair)
            member = selected_member(edge)
            turn_cost = cost_for(role, [pair[member]])
            if used + full_cost <= BUDGET:
                kind, payload, cost = "PAIR", pair, full_cost
            else:
                kind, payload, cost = "TURN", [pair[member]], turn_cost
            payload_tokens = set().union(*(tokens(str(item["text"])) for item in payload))
            coverage = uncovered_coverage(query_tokens, frozenset(payload_tokens), covered, idf)
            score = utility(arm, cosine_for(edge), int(_tie(edge)[0]), cost, coverage)
            proposals.append((-score, _tie(edge), index, (kind, member, cost, full_cost, turn_cost, coverage, payload)))
        _, _, index, proposal = min(proposals)
        edge = remaining.pop(index)
        neighbor = str(edge["neighbor_id"])
        if proposal is None:
            actions.append({"seed_id": str(edge["seed_id"]), "neighbor_id": neighbor,
                            "kind": "DUPLICATE", "member": None, "cost": 0})
            continue
        kind, member, cost, full_cost, turn_cost, coverage, payload = proposal
        seen.add(neighbor)
        cosine = cosine_for(edge)
        score = utility(arm, cosine, int(_tie(edge)[0]), cost, coverage)
        if used + cost <= BUDGET:
            role = append_role_pair(role, payload)
            used += cost
            covered.update(*(tokens(str(item["text"])) for item in payload))
            admitted_kind = kind
        else:
            admitted_kind = "SKIP"
            cost = 0
        actions.append({"seed_id": str(edge["seed_id"]), "neighbor_id": neighbor,
                        "seed_rank": int(_tie(edge)[0]), "direction": _direction(edge),
                        "kind": admitted_kind, "member": member if kind == "TURN" else None,
                        "cost": cost, "full_cost": full_cost, "turn_cost": turn_cost,
                        "payload_cosine": cosine, "uncovered_coverage": coverage, "score": score})
    return {"final_chars": used, "actions": actions}


def build_nf_rows(dataset_path: Path, role_path: Path, edge_path: Path, payload_path: Path,
                  g6_path: Path) -> list[dict[str, Any]]:
    seals = ((role_path, NF_ROLE_SHA256), (edge_path, NF_EDGE_SHA256),
             (payload_path, NF_PAYLOAD_SHA256), (g6_path, NF_G6_SHA256))
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA018Error("DA-018 NF sealed input differs")
    cases = load_blind_cases(dataset_path)
    idf = corpus_idf(cases)
    members, questions = _member_maps(dataset_path, cases)
    roles = {_qkey(row): row for row in read_gzip(role_path)}
    payloads = {_ekey(row): row for row in read_gzip(payload_path)}
    primary = {_qkey(row): bool(row["primary_eligible"])
               for row in json.loads(g6_path.read_text(encoding="utf-8"))["rows"]}
    by_question: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for edge in read_gzip(edge_path):
        if primary[_qkey(edge)]:
            by_question[_qkey(edge)].append(edge)
    output = []
    for key in sorted(by_question):
        sealed = roles[key]
        direct_ids = list(sealed["direct_ids"])
        direct = set(direct_ids)
        edges = [edge for edge in by_question[key] if str(edge["neighbor_id"]) not in direct]
        arms = {}
        for arm in ARMS:
            role = role_pattern_pairs([members[value] for value in direct_ids])
            arms[arm] = _allocate(
                edges, arm, role, direct_ids, tokens(questions[key]), idf,
                lambda identity: members[identity],
                lambda edge: int(payloads[_ekey(edge)]["selected_member_index"]),
                lambda edge: float(edge["features"]["neighbor_query_cosine"]),
                lambda current, pair: append_role_pair(current, pair).chars - current.chars,
                role.chars,
            )
        output.append({"corpus": "NF004", "comparison_key": key[0], "duplicate_ordinal": key[1],
                       "sample_id": sealed["sample_id"], "source_index": sealed["source_index"],
                       "direct_ids": direct_ids, "arms": arms})
    if len(output) != 1_098:
        raise DA018Error("DA-018 NF population differs")
    return output


def build_long_rows(longmem_path: Path, population_path: Path, direct_path: Path,
                    cache_path: Path) -> tuple[list[dict[str, Any]], int]:
    if sha256_file(direct_path) != LONG_DIRECT_SHA256:
        raise DA018Error("DA-018 LongMem direct input differs")
    records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    directs = {row["question_id"]: row for row in read_gzip(direct_path)}
    idf = _idf(list(records.values()))
    cache = ReadOnlyCache(cache_path)
    output = []
    try:
        for question_id in sorted(records):
            record, direct = records[question_id], directs[question_id]
            by_id = {episode.candidate.identity: episode for episode in record.episodes}
            direct_ids = list(direct["direct_ids"])
            direct_pairs = [by_id[value].members for value in direct_ids]
            role = role_pattern_pairs(direct_pairs)
            direct_texts = [str(member["text"]) for pair in direct_pairs for member in pair]
            dictionary = encode(direct_texts)
            phrase_chars = role.chars - sum(map(len, direct_texts)) + dictionary.content_chars + dictionary.declaration_chars
            query_vector = cache.vector(record.question)
            neighbors = sorted({str(edge["neighbor_id"]) for edge in direct["edges"]})
            vectors = np.vstack([cache.vector(by_id[value].candidate.text) for value in neighbors])
            scores = cosine_scores(vectors, query_vector)
            cosine_by_id = {identity: float(score) for identity, score in zip(neighbors, scores, strict=True)}
            arms = {}
            for arm in ARMS:
                current = role_pattern_pairs(direct_pairs)
                arms[arm] = _allocate(
                    direct["edges"], arm, current, direct_ids, _tokens(record.question), idf,
                    lambda identity: by_id[identity].members,
                    lambda edge: int(edge["fallback_member"]),
                    lambda edge: cosine_by_id[str(edge["neighbor_id"])],
                    lambda state, pair: _payload_cost(state, pair, dictionary),
                    phrase_chars,
                )
            output.append({"corpus": "LONGMEM", "question_id": question_id,
                           "question_type": record.question_type, "direct_ids": direct_ids,
                           "phrase_chars": phrase_chars, "arms": arms})
    finally:
        cache.close()
    if len(output) != 465:
        raise DA018Error("DA-018 LongMem population differs")
    return output, cache.hits


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(nf_args: Mapping[str, Path], long_args: Mapping[str, Path], output_dir: Path) -> dict[str, Any]:
    nf_rows = build_nf_rows(**nf_args)
    long_rows, hits = build_long_rows(**long_args)
    rows = [*nf_rows, *long_rows]
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_allocations.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da018-") as directory:
        replay_nf = build_nf_rows(**nf_args)
        replay_long, replay_hits = build_long_rows(**long_args)
        replay = Path(directory) / path.name
        _write(replay, [*replay_nf, *replay_long])
        identical = path.read_bytes() == replay.read_bytes() and hits == replay_hits
    actions = {corpus: {arm: dict(Counter(action["kind"] for row in rows if row["corpus"] == corpus
                                          for action in row["arms"][arm]["actions"])) for arm in ARMS}
               for corpus in ("NF004", "LONGMEM")}
    distinct = {corpus: len({tuple(action["neighbor_id"] for action in row["arms"][arm]["actions"])
                             for row in rows if row["corpus"] == corpus for arm in ARMS})
                for corpus in ("NF004", "LONGMEM")}
    coverage = Counter("positive" if action["uncovered_coverage"] > 0 else "zero"
                       for row in rows for arm in ARMS for action in row["arms"][arm]["actions"]
                       if action["kind"] != "DUPLICATE")
    passed = (identical and all(coverage.values()) and
              all(all(cell.get("PAIR") and cell.get("TURN") and cell.get("SKIP") for cell in arms.values())
                  for arms in actions.values()))
    result = {"schema": "da018-blind-allocation-v1", "status": "PASS" if passed else "FAIL",
              "questions": {"NF004": len(nf_rows), "LONGMEM": len(long_rows)},
              "actions": actions, "coverage_margins": dict(coverage), "order_signatures": distinct,
              "cache": {"hits": hits, "misses": 0}, "allocation_sha256": sha256_file(path),
              "replay_byte_identical": identical, "calls": {"embedding": 0, "model": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA018Error("DA-018 blind preflight failed")
    return result


__all__ = ["ARMS", "DA018Error", "build_long_rows", "build_nf_rows", "run_preflight",
           "uncovered_coverage", "utility"]


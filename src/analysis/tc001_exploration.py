"""TC-001 Preflight Part 1: characterize both paths before any bar is locked.

This module runs the two configurations TC-001 will compare and records
what they *do*. It deliberately does not compute the treatment contrast:
no artifact it writes contains an arm's absolute availability, because the
null band in the pre-registration is derived from measurements taken here
and a band chosen after seeing the contrast would not be a band.

    Flat    rank every candidate by its own cosine, pack greedily to budget.
    Tiered  ``episodic.build_context`` - recency window, K threshold,
            coverage selection over the pool, packed N-first.

Both arms are offered identical candidate identities, identical vectors
from the CC-006-protected LoCoMo development cache, the identical DR-001
renderer, and the identical exact-serialized character budget. The only
thing that differs is which candidates each path chooses and in what
order it offers them to the serializer.

Zero model calls. The cache is opened in ``reuse`` mode with its file and
content digests asserted, so a miss raises rather than embedding.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from analysis.locomo_nf_development import (
    ConversationCase,
    PairCandidate,
    adapt_development,
    sha256_file,
)
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256, EpisodicConfig
from episodic._context import _candidate_pool, _recency_window, build_context
from episodic._packing import pack_stm_payload
from episodic._render import render_episode_element, render_stm_payload
from episodic._selection import relevance_vector

SCHEMA = "tc001-preflight-part1-v1"

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCOMO_ROOT = REPO_ROOT / "experiments" / "external" / "locomo"
CACHE_PATH = LOCOMO_ROOT / "artifacts" / "locomo_dev_embeddings.db"
VECTOR_MANIFEST = LOCOMO_ROOT / "artifacts" / "development_vector_manifest.json"
DATASET_PATH = Path(r"C:\Users\muzaf\Downloads\locomo10.json")

#: Both budgets are characterized here. The registration locks one of them
#: for the bars; the other is carried as a descriptive secondary.
BUDGETS = (16_000, 32_000)

#: Sham perturbations for the instrument band. A budget nudge of this size
#: cannot carry a mechanism claim, so any paired movement it produces is
#: the endpoint's own wobble at a packing boundary.
SHAM_FRACTIONS = (-0.01, -0.005, 0.005, 0.01)

#: Delivered episodes are read off the payload by the turn attribute the
#: DR-001 renderer writes, which is unique within a conversation.
_TURN_ATTRIBUTE = re.compile(r'<episode turn="(\d+)">')


class TC001ExplorationError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Candidates: LoCoMo development pairs, rendered as episodes
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Episode:
    """One adjacent-turn pair, in the shape ``build_context`` consumes."""

    record: dict
    pair: PairCandidate
    element_chars: int

    @property
    def identity(self) -> str:
        return str(self.record["id"])


def build_episodes(
    case: ConversationCase, vectors: dict[str, np.ndarray]
) -> tuple[Episode, ...]:
    """Adapt pairs into episode records without changing their identity.

    ``turn_number`` is the pair's position in the whole conversation, so
    the library's recency window means what it says on this corpus: the
    last N pairs before the question. The pair's own ``identity`` stays
    the comparison key (PF5) - nothing here is generated per run.
    """
    episodes: list[Episode] = []
    for index, pair in enumerate(case.pairs, start=1):
        # Partition, not split: 20 of the 1,365 development pairs carry a
        # newline inside a speaker's own text, and splitting on every
        # newline would drop it. `first + "\n" + rest == pair.text` holds
        # for every pair, so the rendered element carries the candidate
        # the vector was computed from, in full.
        first, separator, rest = pair.text.partition("\n")
        if first + separator + rest != pair.text:
            raise TC001ExplorationError(f"Pair text not reconstructible: {pair.identity}")
        record = {
            "id": pair.identity,
            "turn_number": index,
            "user_message": first,
            "assistant_message": rest,
            "ground_truth_domain": pair.session_id,
            "embedding": vectors[pair.text],
        }
        episodes.append(
            Episode(
                record=record,
                pair=pair,
                element_chars=len(render_episode_element(record)),
            )
        )
    return tuple(episodes)


# --------------------------------------------------------------------------
# The flat arm
# --------------------------------------------------------------------------


def flat_order(
    episodes: Sequence[Episode], query: np.ndarray
) -> tuple[int, ...]:
    """``CdwArm``'s ordering: cosine descending, then conversation order.

    This is ``hh002_arms.rank_pairs`` with the pair's position in the
    conversation as the tie-break, which on this corpus is the same key
    ``(session_order, pair_order)`` expresses. ``assert_flat_order_matches_cdw``
    holds the two together on committed data rather than in prose.
    """
    matrix = np.stack([_unit(episode.record["embedding"]) for episode in episodes])
    scores = matrix @ _unit(query)
    return tuple(
        sorted(
            range(len(episodes)),
            key=lambda index: (
                -float(scores[index]),
                episodes[index].pair.session_order,
                episodes[index].pair.pair_order,
            ),
        )
    )


def flat_context(
    episodes: Sequence[Episode], query: np.ndarray, budget: int
) -> tuple[str, tuple[str, ...]]:
    """Pack the flat order into the same two-block payload the tiers use.

    The flat path has no recency tier, so ``recent_context`` renders
    empty and every delivered episode renders inside ``retrieved_stm``.
    The packer is the shipped ``pack_stm_payload`` with an empty N tier -
    not a reimplementation of it - so both arms charge exact serialized
    cost and skip on overflow under the same committed
    ``episodic._packing.DROP_POLICY``. The single difference between the
    arms is the candidate list handed to that function.
    """
    order = flat_order(episodes, query)
    packed = pack_stm_payload(
        [], [episodes[index].record for index in order], budget
    )
    return packed.payload, packed.selected_ids


def assert_flat_order_matches_cdw(
    episodes: Sequence[Episode], query: np.ndarray
) -> dict:
    """PF2/PF6: the flat arm is ``CdwArm``'s ranking, not a rewrite of it."""
    from analysis.hh002_arms import PairCandidate as CdwPair, rank_pairs

    candidates = tuple(
        CdwPair(
            text=episode.pair.text,
            session_order=episode.pair.session_order,
            pair_order=episode.pair.pair_order,
            dia_ids=episode.pair.dialog_ids,
        )
        for episode in episodes
    )
    matrix = np.stack(
        [np.asarray(episode.record["embedding"], dtype=np.float32) for episode in episodes]
    )
    upstream = rank_pairs(candidates, matrix, np.asarray(query, dtype=np.float32))
    local = flat_order(episodes, query)
    if upstream != local:
        raise AssertionError(
            "Flat ordering diverged from hh002_arms.rank_pairs"
        )
    return {
        "status": "PASS",
        "candidates": len(episodes),
        "order_sha256": _digest(list(local)),
    }


# --------------------------------------------------------------------------
# The tiered arm, instrumented
# --------------------------------------------------------------------------


def tiered_context(
    episodes: Sequence[Episode],
    query: np.ndarray,
    budget: int,
    config: EpisodicConfig,
) -> tuple[str, tuple[str, ...], Any]:
    records = [episode.record for episode in episodes]
    payload, report = build_context(
        episodes=records,
        query_embedding=query,
        budget=budget,
        config=config,
    )
    delivered = _delivered_ids(payload, records)
    return payload, delivered, report


def tier_membership(
    episodes: Sequence[Episode], query: np.ndarray, config: EpisodicConfig
) -> dict[str, Any]:
    """What the three named tiers contain before the packer sees them."""
    records = [episode.record for episode in episodes]
    recent = _recency_window(records, config.recency_window_n)
    relevance = relevance_vector(query, records)
    by_id = {
        str(record["id"]): float(relevance[index])
        for index, record in enumerate(records)
    }
    k_hits = [r for r in records if by_id[str(r["id"])] >= config.k_threshold]
    pool = _candidate_pool(records, by_id, config)
    return {
        "recency_ids": tuple(str(r["id"]) for r in recent),
        "k_ids": tuple(str(r["id"]) for r in k_hits),
        "pool_size": len(pool),
        "relevance": by_id,
        "max_relevance": max(by_id.values()) if by_id else float("nan"),
    }


# --------------------------------------------------------------------------
# Part 1
# --------------------------------------------------------------------------


def explore(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    cache_record = manifest["cache"]
    conversations = adapt_development(DATASET_PATH)

    started = time.time()
    with EmbeddingCache(
        CACHE_PATH,
        mode="reuse",
        expected_file_sha256=cache_record["file_sha256"],
        expected_content_sha256=cache_record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDER_SHA256,
    ) as cache:
        vectors = {
            text: np.asarray(cache(text), dtype=np.float32)
            for case in conversations
            for text in (
                *(pair.text for pair in case.pairs),
                *(question.question for question in case.questions),
            )
        }
        reuse = cache.record()
    if reuse["misses"]:
        raise TC001ExplorationError(
            f"Read-only cache reported {reuse['misses']} misses; Part 1 must "
            "cost zero model calls"
        )

    config = EpisodicConfig()
    by_conversation = {
        case.sample_id: build_episodes(case, vectors) for case in conversations
    }

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PREFLIGHT_PART_1_EXPLORATION_ONLY",
        "note": (
            "No arm's absolute availability appears in this artifact. The "
            "null band registered from it is derived from within-arm sham "
            "perturbations only."
        ),
        "inputs": _inputs(manifest, reuse),
        "corpus": _corpus_shape(conversations, by_conversation),
        "identity": _identity_checks(conversations, by_conversation, vectors, config),
        "behaviour": {},
        "cost": {},
        "sham_band": {},
    }

    for budget in BUDGETS:
        key = str(budget)
        result["behaviour"][key] = _behaviour(
            conversations, by_conversation, vectors, config, budget
        )
        result["sham_band"][key] = _sham_band(
            conversations, by_conversation, vectors, config, budget
        )
    result["cost"] = _cost(conversations, by_conversation, vectors, config)
    result["elapsed_seconds"] = round(time.time() - started, 3)

    path = output_dir / "tc001_preflight_part1.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


# --------------------------------------------------------------------------
# Part 1 sections
# --------------------------------------------------------------------------


def _inputs(manifest: dict, reuse: dict) -> dict[str, Any]:
    return {
        "dataset": {
            "path": str(DATASET_PATH),
            "bytes": DATASET_PATH.stat().st_size,
            "sha256": manifest["dataset_sha256"],
        },
        "cache": {
            "path": _repo_relative(CACHE_PATH),
            "file_sha256": manifest["cache"]["file_sha256"],
            "content_sha256": manifest["cache"]["content_sha256"],
            "entries": manifest["cache"]["entries"],
            "hits": reuse["hits"],
            "misses": reuse["misses"],
        },
        "vector_manifest_sha256": sha256_file(VECTOR_MANIFEST),
        "embedder_sha256": CARRIED_EMBEDDER_SHA256,
        "development_ids": manifest["development_ids"],
        "sources": {
            _repo_relative(path): sha256_file(path)
            for path in (
                Path(__file__).resolve(),
                REPO_ROOT / "src" / "analysis" / "locomo_nf_development.py",
                REPO_ROOT / "episodic" / "src" / "episodic" / "_context.py",
                REPO_ROOT / "episodic" / "src" / "episodic" / "_packing.py",
                REPO_ROOT / "episodic" / "src" / "episodic" / "_render.py",
                REPO_ROOT / "episodic" / "src" / "episodic" / "_selection.py",
                REPO_ROOT / "src" / "analysis" / "hh002_arms.py",
            )
        },
    }


def _corpus_shape(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
) -> dict[str, Any]:
    rows = []
    for case in conversations:
        episodes = by_conversation[case.sample_id]
        unique = [q for q in case.questions if q.duplicate_ordinal == 0]
        rows.append(
            {
                "sample_id": case.sample_id,
                "candidates": len(episodes),
                "sessions": len({p.session_id for p in case.pairs}),
                "questions": len(case.questions),
                "unique_questions": len(unique),
                "questions_with_resolved_evidence": sum(
                    1 for q in unique if q.resolved_evidence_ids
                ),
                "questions_with_unresolved_evidence": sum(
                    1 for q in unique if q.unresolved_evidence_ids
                ),
                "pair_chars_total": sum(p.chars for p in case.pairs),
                "element_chars_total": sum(e.element_chars for e in episodes),
            }
        )
    all_episodes = [e for eps in by_conversation.values() for e in eps]
    return {
        "conversations": rows,
        "candidates_total": len(all_episodes),
        "unique_questions_total": sum(r["unique_questions"] for r in rows),
        "pair_chars": _distribution([e.pair.chars for e in all_episodes]),
        "element_chars": _distribution([e.element_chars for e in all_episodes]),
        "render_overhead_chars": _distribution(
            [e.element_chars - e.pair.chars for e in all_episodes]
        ),
        "empty_payload_chars": len(render_stm_payload([], [])),
    }


def _identity_checks(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    config: EpisodicConfig,
) -> dict[str, Any]:
    """PF2. Every named part of both designs, checked against its name."""
    case = conversations[0]
    episodes = by_conversation[case.sample_id]
    query = vectors[case.questions[0].question]

    records = [e.record for e in episodes]
    recent = _recency_window(records, config.recency_window_n)
    window_is_a_window = tuple(str(r["id"]) for r in recent) == tuple(
        str(r["id"]) for r in records[-config.recency_window_n :]
    )

    # Query-invariance of the recency tier, on a real trace: a window is a
    # function of position only. The N tier this programme shipped was a
    # least-recently-delivered rotation wearing the same name, so the claim
    # is tested rather than inherited.
    windows = {
        tuple(
            m["recency_ids"]
            for m in [tier_membership(episodes, vectors[q.question], config)]
        )[0]
        for q in case.questions[:25]
    }

    membership = tier_membership(episodes, query, config)
    pool_is_full_store = membership["pool_size"] == len(episodes)

    return {
        "recency_window_is_last_n": window_is_a_window,
        "recency_window_query_invariant": len(windows) == 1,
        "recency_window_probes": 25,
        "candidate_pool_is_full_store": pool_is_full_store,
        "candidate_policy": config.candidate_policy,
        "flat_order_matches_cdw_arm": assert_flat_order_matches_cdw(
            episodes, query
        ),
        "config": json.loads(config.to_json()),
    }


def _behaviour(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    config: EpisodicConfig,
    budget: int,
) -> dict[str, Any]:
    """One pass per question: what each tier proposes, and what lands.

    Distributions rather than summaries, per PREFLIGHT.md Part 1: the
    medians in this programme's paper section 9.1 concealed a path that
    delivered nothing at 8 of 8 probes, so every quantity here is reported
    by percentile and the zero counts are reported separately.

    The constant-output check rides along in the same pass. Neither path
    has feedback - both are pure functions of (store, query, budget) - so
    PF7's absorbing state cannot arise, and the degeneracy that *can*
    arise is an arm whose delivered block stops depending on the query.
    """
    k_candidate_counts: list[int] = []
    max_relevance: list[float] = []
    stm_counts: list[int] = []
    k_counts: list[int] = []
    coverage_counts: list[int] = []
    delivered_counts: list[int] = []
    chars: list[int] = []
    dropped: list[int] = []
    pool_sizes: list[int] = []
    recency_share: list[float] = []
    flat_delivered: list[int] = []
    flat_chars: list[int] = []
    overlap: list[float] = []
    degeneracy_rows: list[dict[str, Any]] = []

    for case in conversations:
        episodes = by_conversation[case.sample_id]
        elements = {e.identity: e.element_chars for e in episodes}
        tiered_sets: set[tuple[str, ...]] = set()
        flat_sets: set[tuple[str, ...]] = set()
        recency_only = 0
        questions = [q for q in case.questions if not q.duplicate_ordinal]
        for question in questions:
            query = vectors[question.question]
            membership = tier_membership(episodes, query, config)
            k_candidate_counts.append(len(membership["k_ids"]))
            max_relevance.append(membership["max_relevance"])
            pool_sizes.append(membership["pool_size"])

            _payload, delivered, report = tiered_context(
                episodes, query, budget, config
            )
            stm_counts.append(report.stm_count)
            k_counts.append(report.k_count)
            coverage_counts.append(report.coverage_count)
            delivered_counts.append(report.episodes_delivered)
            chars.append(report.chars_delivered)
            dropped.append(report.episodes_dropped)
            if report.k_count == 0 and report.coverage_count == 0:
                recency_only += 1
            recency_ids = set(membership["recency_ids"])
            recency_chars = sum(
                elements[identity]
                for identity in delivered
                if identity in recency_ids
            )
            recency_share.append(
                recency_chars / report.chars_delivered
                if report.chars_delivered
                else 0.0
            )

            flat_payload, flat_ids = flat_context(episodes, query, budget)
            flat_delivered.append(len(flat_ids))
            flat_chars.append(len(flat_payload))

            tiered_set = set(delivered)
            flat_set = set(flat_ids)
            union = tiered_set | flat_set
            overlap.append(
                len(tiered_set & flat_set) / len(union) if union else 1.0
            )
            tiered_sets.add(tuple(sorted(tiered_set)))
            flat_sets.add(tuple(sorted(flat_set)))

        degeneracy_rows.append(
            {
                "sample_id": case.sample_id,
                "questions": len(questions),
                "tiered_distinct_delivered_sets": len(tiered_sets),
                "flat_distinct_delivered_sets": len(flat_sets),
                "tiered_recency_only_questions": recency_only,
            }
        )

    return {
        "budget_chars": budget,
        "questions": len(k_candidate_counts),
        "k_threshold": config.k_threshold,
        "k_candidates_per_question": _distribution(k_candidate_counts),
        "questions_with_zero_k_candidates": sum(
            1 for value in k_candidate_counts if value == 0
        ),
        "max_relevance": _float_distribution(max_relevance),
        "pool_size": _distribution(pool_sizes),
        "tiered": {
            "recency_delivered": _distribution(stm_counts),
            "k_delivered": _distribution(k_counts),
            "coverage_delivered": _distribution(coverage_counts),
            "episodes_delivered": _distribution(delivered_counts),
            "episodes_dropped": _distribution(dropped),
            "chars_delivered": _distribution(chars),
            "recency_share_of_chars": _float_distribution(recency_share),
            "questions_with_zero_k_delivered": sum(
                1 for value in k_counts if value == 0
            ),
            "questions_with_zero_coverage_delivered": sum(
                1 for value in coverage_counts if value == 0
            ),
        },
        "flat": {
            "episodes_delivered": _distribution(flat_delivered),
            "chars_delivered": _distribution(flat_chars),
        },
        "delivered_set_jaccard": _float_distribution(overlap),
        "degeneracy": {
            "by_conversation": degeneracy_rows,
            "tiered_is_constant": all(
                row["tiered_distinct_delivered_sets"] == 1
                for row in degeneracy_rows
            ),
            "flat_is_constant": all(
                row["flat_distinct_delivered_sets"] == 1
                for row in degeneracy_rows
            ),
            "feedback_present": False,
        },
    }


def _sham_band(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    config: EpisodicConfig,
    budget: int,
) -> dict[str, Any]:
    """The null band, measured rather than chosen.

    Each arm is compared **against itself** at a nudged budget. A budget
    moved by half a percent carries no mechanism claim, so whatever paired
    movement it produces is what this endpoint does at a packing boundary.

    Only paired counts are recorded. The arms' absolute hit counts are
    deliberately not written, because a band has to be fixed before the
    contrast it governs has been seen - section 9.4's guardrail, applied
    to the one measurement that has to happen before the lock.
    """
    baseline: dict[str, dict[str, bool]] = {"flat": {}, "tiered": {}}
    wanted: dict[str, frozenset[str]] = {}
    for case in conversations:
        episodes = by_conversation[case.sample_id]
        evidence = _evidence_index(case, episodes)
        for question in case.questions:
            if question.duplicate_ordinal or not question.resolved_evidence_ids:
                continue
            query = vectors[question.question]
            target = evidence[question.identity]
            wanted[question.identity] = target
            _p, flat_ids = flat_context(episodes, query, budget)
            baseline["flat"][question.identity] = bool(target & set(flat_ids))
            _p, tiered_ids, _r = tiered_context(episodes, query, budget, config)
            baseline["tiered"][question.identity] = bool(target & set(tiered_ids))

    per_arm: dict[str, list[dict[str, Any]]] = {"flat": [], "tiered": []}
    for fraction in SHAM_FRACTIONS:
        nudged = int(round(budget * (1.0 + fraction)))
        counts = {"flat": [0, 0], "tiered": [0, 0]}
        for case in conversations:
            episodes = by_conversation[case.sample_id]
            for question in case.questions:
                if question.duplicate_ordinal or not question.resolved_evidence_ids:
                    continue
                query = vectors[question.question]
                target = wanted[question.identity]

                _p, flat_ids = flat_context(episodes, query, nudged)
                _score(
                    counts["flat"],
                    baseline["flat"][question.identity],
                    bool(target & set(flat_ids)),
                )

                _p, tiered_ids, _r = tiered_context(
                    episodes, query, nudged, config
                )
                _score(
                    counts["tiered"],
                    baseline["tiered"][question.identity],
                    bool(target & set(tiered_ids)),
                )
        for arm, (gains, losses) in counts.items():
            per_arm[arm].append(
                _sham_row(fraction, budget, nudged, gains, losses)
            )

    nets = [abs(row["net"]) for rows in per_arm.values() for row in rows]
    discordant = [row["discordant"] for rows in per_arm.values() for row in rows]
    return {
        "evaluable_questions": len(wanted),
        "perturbations": per_arm,
        "max_abs_net": max(nets),
        "max_discordant": max(discordant),
        "band_definition": (
            "The largest absolute gains-minus-losses any sham budget "
            "perturbation produced within a single arm, at this budget."
        ),
    }


def _score(counter: list[int], baseline: bool, perturbed: bool) -> None:
    if perturbed and not baseline:
        counter[0] += 1
    elif baseline and not perturbed:
        counter[1] += 1


def _cost(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    config: EpisodicConfig,
) -> dict[str, Any]:
    """Per-question wall clock for both paths, at this corpus's pool size."""
    rows = []
    for case in conversations:
        episodes = by_conversation[case.sample_id]
        questions = [q for q in case.questions if not q.duplicate_ordinal][:40]
        tiered_ms: list[float] = []
        flat_ms: list[float] = []
        for question in questions:
            query = vectors[question.question]
            started = time.perf_counter()
            tiered_context(episodes, query, BUDGETS[0], config)
            tiered_ms.append((time.perf_counter() - started) * 1_000.0)
            started = time.perf_counter()
            flat_context(episodes, query, BUDGETS[0])
            flat_ms.append((time.perf_counter() - started) * 1_000.0)
        rows.append(
            {
                "sample_id": case.sample_id,
                "pool_size": len(episodes),
                "questions_timed": len(questions),
                "tiered_ms": _float_distribution(tiered_ms),
                "flat_ms": _float_distribution(flat_ms),
            }
        )
    return {"by_conversation": rows, "budget_chars": BUDGETS[0]}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _evidence_index(
    case: ConversationCase, episodes: Sequence[Episode]
) -> dict[str, frozenset[str]]:
    """Question identity -> the episode identities carrying its evidence."""
    dialog_to_episode = {
        dialog_id: episode.identity
        for episode in episodes
        for dialog_id in episode.pair.dialog_ids
    }
    return {
        question.identity: frozenset(
            dialog_to_episode[value] for value in question.resolved_evidence_ids
        )
        for question in case.questions
    }


def _sham_row(
    fraction: float, budget: int, nudged: int, gains: int, losses: int
) -> dict[str, Any]:
    return {
        "fraction": fraction,
        "budget_chars": budget,
        "nudged_budget_chars": nudged,
        "gains": int(gains),
        "losses": int(losses),
        "net": int(gains) - int(losses),
        "discordant": int(gains) + int(losses),
    }


def _delivered_ids(payload: str, records: Sequence[dict]) -> tuple[str, ...]:
    """Which episodes the payload actually carries, in delivery order.

    Read off the delivered string rather than off the report, so the
    measurement is of the block a reader would receive. The key is the
    renderer's own ``turn`` attribute, which is unique inside a
    conversation - a content-derived position, not a generated id (PF5).
    """
    by_turn = {int(record["turn_number"]): str(record["id"]) for record in records}
    if len(by_turn) != len(records):
        raise TC001ExplorationError("turn_number is not unique within the store")
    return tuple(
        by_turn[int(match)] for match in _TURN_ATTRIBUTE.findall(payload)
    )


def _unit(value) -> np.ndarray:
    array = np.asarray(value, dtype=np.float32)
    norm = float(np.linalg.norm(array))
    return array if norm == 0.0 else array / norm


def _distribution(values: Iterable[int]) -> dict[str, Any]:
    ordered = sorted(values)
    if not ordered:
        raise TC001ExplorationError("Cannot summarize an empty distribution")

    def rank(percentile: float) -> int:
        return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]

    return {
        "n": len(ordered),
        "min": ordered[0],
        "p05": rank(0.05),
        "p25": rank(0.25),
        "p50": rank(0.50),
        "p75": rank(0.75),
        "p95": rank(0.95),
        "max": ordered[-1],
        "mean": round(statistics.fmean(ordered), 3),
    }


def _float_distribution(values: Iterable[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise TC001ExplorationError("Cannot summarize an empty distribution")

    def rank(percentile: float) -> float:
        return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]

    return {
        "n": len(ordered),
        "min": round(ordered[0], 6),
        "p05": round(rank(0.05), 6),
        "p50": round(rank(0.50), 6),
        "p95": round(rank(0.95), 6),
        "max": round(ordered[-1], 6),
        "mean": round(statistics.fmean(ordered), 6),
    }


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _repo_relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


__all__ = [
    "BUDGETS",
    "Episode",
    "SHAM_FRACTIONS",
    "build_episodes",
    "explore",
    "flat_context",
    "flat_order",
    "tier_membership",
    "tiered_context",
]

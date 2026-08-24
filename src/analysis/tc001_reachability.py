"""TC-001 PF4: is the registered bar reachable, and is it failable?

A paired sign test is decided by its discordant pairs. If the two arms
never disagree about whether a question's evidence arrived, no bar on
that contrast can fire in either direction - which is exactly the defect
DMR-001 locked and PF4 exists to catch.

**What this module deliberately does not compute.** It reports how many
questions the two arms disagree on. It does not report which way they
disagree, and it refuses to write a gains/losses split. That is the whole
point: a discordant count establishes that a bar can fire without saying
which arm it would fire for, so it can be read before the bars are locked
without §9.4's rescue risk. ``_forbid_direction`` enforces the boundary on
the artifact rather than trusting this docstring.

Zero model calls; the same read-only, digest-bound cache Part 1 uses.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from analysis.locomo_nf_development import ConversationCase, adapt_development
from analysis.tc001_exploration import (
    BUDGETS,
    CACHE_PATH,
    DATASET_PATH,
    REPO_ROOT,
    VECTOR_MANIFEST,
    Episode,
    TC001ExplorationError,
    _evidence_index,
    _repo_relative,
    build_episodes,
    flat_context,
    tiered_context,
)
from analysis.locomo_nf_development import sha256_file
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256, EpisodicConfig

SCHEMA = "tc001-preflight-pf4-reachability-v1"

#: Keys an artifact from this module may never carry.
_FORBIDDEN_KEYS = frozenset(
    {
        "gains",
        "losses",
        "net",
        "flat_hits",
        "tiered_hits",
        "flat_only",
        "tiered_only",
        "direction",
        "winner",
    }
)


def measure(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    conversations = adapt_development(DATASET_PATH)

    with EmbeddingCache(
        CACHE_PATH,
        mode="reuse",
        expected_file_sha256=manifest["cache"]["file_sha256"],
        expected_content_sha256=manifest["cache"]["content_sha256"],
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
        raise TC001ExplorationError("Read-only cache miss; this must cost no model calls")

    config = EpisodicConfig()
    by_conversation = {
        case.sample_id: build_episodes(case, vectors) for case in conversations
    }

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PREFLIGHT_PF4_ONLY",
        "note": (
            "Discordant counts only. The direction of disagreement is not "
            "computed here and must not be, until the bars are committed."
        ),
        "inputs": {
            "cache_file_sha256": manifest["cache"]["file_sha256"],
            "cache_content_sha256": manifest["cache"]["content_sha256"],
            "dataset_sha256": manifest["dataset_sha256"],
            "cache_misses": reuse["misses"],
            "sources": {
                _repo_relative(path): sha256_file(path)
                for path in (
                    Path(__file__).resolve(),
                    REPO_ROOT / "src" / "analysis" / "tc001_exploration.py",
                )
            },
        },
        "budgets": {},
    }
    for budget in BUDGETS:
        result["budgets"][str(budget)] = _reachability(
            conversations, by_conversation, vectors, config, budget
        )
    _forbid_direction(result)

    path = output_dir / "tc001_preflight_pf4_reachability.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _reachability(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    config: EpisodicConfig,
    budget: int,
) -> dict[str, Any]:
    endpoints = ("any_evidence", "complete_evidence")
    discordant = {name: 0 for name in endpoints}
    concordant = {name: 0 for name in endpoints}
    by_conversation_counts: dict[str, dict[str, int]] = {}
    evaluable = 0

    for case in conversations:
        episodes = by_conversation[case.sample_id]
        evidence = _evidence_index(case, episodes)
        local = {name: 0 for name in endpoints}
        for question in case.questions:
            if question.duplicate_ordinal or not question.resolved_evidence_ids:
                continue
            evaluable += 1
            target = evidence[question.identity]
            query = vectors[question.question]
            _p, flat_ids = flat_context(episodes, query, budget)
            _p, tiered_ids, _r = tiered_context(episodes, query, budget, config)
            flat_set, tiered_set = set(flat_ids), set(tiered_ids)
            outcomes = {
                "any_evidence": (
                    bool(target & flat_set),
                    bool(target & tiered_set),
                ),
                "complete_evidence": (
                    target <= flat_set,
                    target <= tiered_set,
                ),
            }
            for name, (flat_hit, tiered_hit) in outcomes.items():
                if flat_hit != tiered_hit:
                    discordant[name] += 1
                    local[name] += 1
                else:
                    concordant[name] += 1
        by_conversation_counts[case.sample_id] = local

    rows = {}
    for name in endpoints:
        count = discordant[name]
        rows[name] = {
            "discordant_pairs": count,
            "concordant_pairs": concordant[name],
            "smallest_one_sided_exact_p_at_this_n": (
                _one_sided_extreme_p(count) if count else 1.0
            ),
            "discordant_by_conversation": {
                sample_id: values[name]
                for sample_id, values in by_conversation_counts.items()
            },
        }
    return {
        "budget_chars": budget,
        "evaluable_questions": evaluable,
        "endpoints": rows,
    }


def _one_sided_extreme_p(discordant: int) -> float:
    """The best p a sign test could return at this many discordant pairs.

    If every discordant pair fell the same way, the one-sided exact
    binomial p is ``0.5 ** discordant``. A bar set below this number is
    unreachable by construction - PF4's failing precedent, stated as an
    arithmetic fact rather than an expectation.
    """
    return math.pow(0.5, discordant)


def _forbid_direction(payload: object, path: str = "") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in _FORBIDDEN_KEYS:
                raise TC001ExplorationError(
                    f"PF4 artifact carries a directional key at {path}/{key}"
                )
            _forbid_direction(value, f"{path}/{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            _forbid_direction(value, f"{path}[{index}]")


__all__ = ["SCHEMA", "measure"]

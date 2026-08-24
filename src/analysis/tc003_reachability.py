"""TC-003 PF4: are the registered bars reachable, and are they failable?

TC-003 locks two kinds of bar and this module has to answer for both. My own
note from DMR-001 is the reason it is written that way:

    reachability per bar, not per statistic; DMR-001 locked one that was
    unreachable by construction.

**The six statistical bars** are paired sign tests on evidence availability. A
sign test is decided by its discordant pairs, so if two arms never disagree
about whether a question's evidence arrived, no bar on that contrast can fire
in either direction. This module counts the disagreements and computes the
smallest one-sided exact *p* attainable at that count, per contrast, per
budget, per endpoint.

**The two deterministic bars** are order-invariance checks, and their
reachability question is different: not "can the bar fire" but "can the check
register a difference at all." An invariance check over an instrument that
cannot express non-invariance is not evidence of invariance. So:

    the service check   is exercised against a zero-floor control, and the
                        control has to deliver more than one distinct set
                        across the six permutations on at least one question.
    the ownership check is exercised against tier overlap, and there has to be
                        at least one question where a candidate belongs to two
                        tiers - otherwise ownership has nothing to decide and
                        an invariant result would be vacuous.

**What this module deliberately does not compute.** It reports how many
questions each pair of arms disagrees on. It does not report which way they
disagree, and it refuses to write a gains/losses split. ``_forbid_direction``
enforces that boundary on the artifact rather than trusting this docstring.

It also does not report whether the floors arm is order-invariant. That is the
study's own result and the Preflight Part 1 artifact carries it; what belongs
here is only whether the instrument could have said otherwise.

Zero model calls; the same read-only, digest-bound cache Part 1 uses.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from analysis.locomo_nf_development import (
    ConversationCase,
    adapt_development,
    sha256_file,
)
from analysis.tc001_exploration import (
    BUDGETS,
    CACHE_PATH,
    DATASET_PATH,
    REPO_ROOT,
    VECTOR_MANIFEST,
    Episode,
    _delivered_ids,
    _evidence_index,
    _repo_relative,
    build_episodes,
    flat_context,
)
from analysis.tc001b_exploration import (
    SHIPPED_CONFIG,
    dual_context,
    dual_ranked_context,
)
from analysis.tc002_exploration import pack_both
from analysis.tc003_exploration import (
    FLOOR_CONFIGS,
    SERVICE_ORDERS,
    TC003ExplorationError,
    floors_pack,
    relevance_map,
    service_permutation,
    tier_offers,
    TIERS,
)
from analysis.ec002_k_first_packing import build_candidate_state
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256

SCHEMA = "tc003-preflight-pf4-reachability-v1"

#: The registered contrasts, named left-versus-right for the artifact only.
#: Which side wins is precisely what this module refuses to compute.
CONTRASTS = (
    ("floors", "n_first"),
    ("floors", "k_first"),
    ("floors", "flat"),
    ("floors_dual", "dual"),
    ("floors_dual", "dual_ranked"),
    ("floors_dual", "flat"),
)

#: Keys an artifact from this module may never carry.
_FORBIDDEN_KEYS = frozenset(
    {
        "gains",
        "losses",
        "net",
        "direction",
        "winner",
        "wins",
        "favours",
    }
)

_FORBIDDEN_SUFFIXES = ("_hits", "_only", "_wins", "_gains", "_losses")


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
        raise TC003ExplorationError(
            "Read-only cache miss; this must cost no model calls"
        )

    by_conversation = {
        case.sample_id: build_episodes(case, vectors) for case in conversations
    }

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PREFLIGHT_PF4_ONLY",
        "note": (
            "Discordant counts and instrument reachability only. The "
            "direction of disagreement is not computed here and must not be, "
            "until the bars are committed. Whether the floors arm is "
            "order-invariant is the study's result and is not reported here."
        ),
        "contrasts": ["_vs_".join(pair) for pair in CONTRASTS],
        "inputs": {
            "cache_file_sha256": manifest["cache"]["file_sha256"],
            "cache_content_sha256": manifest["cache"]["content_sha256"],
            "dataset_sha256": manifest["dataset_sha256"],
            "cache_misses": reuse["misses"],
            "sources": {
                _repo_relative(path): sha256_file(path)
                for path in (
                    Path(__file__).resolve(),
                    REPO_ROOT / "src" / "analysis" / "tc003_exploration.py",
                    REPO_ROOT / "src" / "analysis" / "tc002_exploration.py",
                    REPO_ROOT / "src" / "analysis" / "tc001b_exploration.py",
                    REPO_ROOT / "src" / "analysis" / "tc001_exploration.py",
                    REPO_ROOT / "src" / "analysis" / "ec002_k_first_packing.py",
                )
            },
        },
        "budgets": {},
    }
    for budget in BUDGETS:
        result["budgets"][str(budget)] = _reachability(
            conversations, by_conversation, vectors, budget
        )
    _forbid_direction(result)

    path = output_dir / "tc003_preflight_pf4_reachability.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _reachability(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    budget: int,
) -> dict[str, Any]:
    endpoints = ("any_evidence", "complete_evidence")
    discordant = {
        "_vs_".join(pair): {name: 0 for name in endpoints} for pair in CONTRASTS
    }
    concordant = {
        "_vs_".join(pair): {name: 0 for name in endpoints} for pair in CONTRASTS
    }
    evaluable = 0
    control_separates = {arm: 0 for arm in FLOOR_CONFIGS}
    ownership_has_something_to_decide = {arm: 0 for arm in FLOOR_CONFIGS}

    for case in conversations:
        episodes = by_conversation[case.sample_id]
        records = [episode.record for episode in episodes]
        evidence = _evidence_index(case, episodes)
        for question in case.questions:
            if question.duplicate_ordinal or not question.resolved_evidence_ids:
                continue
            evaluable += 1
            target = evidence[question.identity]
            query = vectors[question.question]

            shipped = pack_both(records, query, budget, SHIPPED_CONFIG)
            _payload, flat_ids = flat_context(episodes, query, budget)
            _payload, dual_ids, _report = dual_context(episodes, query, budget)
            _payload, ranked_ids, _counts = dual_ranked_context(
                episodes, query, budget
            )
            sets = {
                "flat": set(flat_ids),
                "n_first": set(shipped["n_first"]["delivered"]),
                "k_first": set(shipped["k_first"]["delivered"]),
                "dual": set(dual_ids),
                "dual_ranked": set(ranked_ids),
            }
            relevance = relevance_map(records, query)
            for arm, config in FLOOR_CONFIGS.items():
                # One clustering per arm, reused by the delivery and by the
                # control below. At this pool size the clustering is roughly
                # 97 ms and everything downstream of it is under 6.
                state = build_candidate_state(
                    episodes=records,
                    query_embedding=query,
                    budget=budget,
                    config=config,
                )
                pack = floors_pack(state, relevance, budget)
                sets[arm] = set(_delivered_ids(pack.payload, records))

                control = service_permutation(
                    state, relevance, budget, floors="zero"
                )
                if control["distinct_sets"] > 1:
                    control_separates[arm] += 1
                if _tiers_overlap(state):
                    ownership_has_something_to_decide[arm] += 1

            outcomes = {
                arm: {
                    "any_evidence": bool(target & delivered),
                    "complete_evidence": target <= delivered,
                }
                for arm, delivered in sets.items()
            }
            for pair in CONTRASTS:
                key = "_vs_".join(pair)
                left, right = pair
                for name in endpoints:
                    if outcomes[left][name] != outcomes[right][name]:
                        discordant[key][name] += 1
                    else:
                        concordant[key][name] += 1

    rows: dict[str, dict[str, Any]] = {}
    for pair in CONTRASTS:
        key = "_vs_".join(pair)
        rows[key] = {}
        for name in endpoints:
            count = discordant[key][name]
            rows[key][name] = {
                "discordant_pairs": count,
                "concordant_pairs": concordant[key][name],
                # The band is compared against |gains - losses|, which cannot
                # exceed the discordant count. A band above this number is a
                # bar no result can clear, whichever way the pairs fall.
                "largest_attainable_abs_margin": count,
                "smallest_one_sided_exact_p_at_this_n": (
                    _one_sided_extreme_p(count) if count else 1.0
                ),
            }
    return {
        "budget_chars": budget,
        "evaluable_questions": evaluable,
        "contrasts": rows,
        "invariance_instrument": {
            "service_permutations_compared": len(SERVICE_ORDERS),
            "questions_where_the_zero_floor_control_separates_orders": (
                control_separates
            ),
            "questions_where_a_candidate_is_in_two_tiers": (
                ownership_has_something_to_decide
            ),
            "claim": (
                "The first count is what makes a service-order invariance "
                "result meaningful: it is the number of questions on which "
                "the same allocator, with its floors removed, does depend on "
                "the order. The second is what makes an ownership-order "
                "result meaningful: with no overlap there is nothing for "
                "ownership to decide and invariance would be vacuous."
            ),
        },
    }


def _tiers_overlap(state) -> bool:
    offers = tier_offers(state)
    seen: set[str] = set()
    for tier in TIERS:
        for episode in offers[tier]:
            identifier = str(episode["id"])
            if identifier in seen:
                return True
            seen.add(identifier)
    return False


def _one_sided_extreme_p(discordant: int) -> float:
    """The best p a sign test could return at this many discordant pairs.

    If every discordant pair fell the same way, the one-sided exact binomial p
    is ``0.5 ** discordant``. A bar set below this number is unreachable by
    construction - PF4's failing precedent, stated as an arithmetic fact rather
    than an expectation.
    """
    return math.pow(0.5, discordant)


def _forbid_direction(payload: object, path: str = "") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in _FORBIDDEN_KEYS or lowered.endswith(_FORBIDDEN_SUFFIXES):
                raise TC003ExplorationError(
                    f"PF4 artifact carries a directional key at {path}/{key}"
                )
            _forbid_direction(value, f"{path}/{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            _forbid_direction(value, f"{path}[{index}]")


__all__ = ["CONTRASTS", "SCHEMA", "measure"]

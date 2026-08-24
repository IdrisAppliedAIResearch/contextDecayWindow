"""TC-003: reserved floors against sequential tier fill.

The authoritative design is
``experiments/components/tier_cost/TC_003_PRE_REGISTRATION.md``.  This module
implements its two committed phases:

``g0``
    Reproduce twenty inherited availability cells, re-run the allocator's
    3,484 byte-identity reductions, and prove both invariance controls are live.
``run``
    Check the two deterministic order properties before opening the evidence
    labels, then measure the seven registered arms and six contrasts.

The run is offline and makes zero model calls.  The retained embedding cache is
opened read-only and every registered input digest is asserted.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from analysis.ec002_k_first_packing import build_candidate_state, pack_k_first
from analysis.locomo_nf_development import (
    ConversationCase,
    QuestionCase,
    adapt_development,
    sha256_file,
)
from analysis.tc001_exploration import (
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
    flat_order,
)
from analysis.tc001_study import ModelCallGuard, one_sided_sign_p
from analysis.tc001b_exploration import (
    DUAL_CONFIG,
    SHIPPED_CONFIG,
    dual_ranked_context,
)
from analysis.tc003_exploration import (
    FLOOR_CONFIGS,
    OWNERSHIP_DEFAULT,
    SERVICE_ORDERS,
    TIERS,
    FloorsPack,
    assert_zero_floor_reduction,
    floors_pack,
    ownership_permutation,
    relevance_map,
    service_permutation,
    tier_offers,
    tier_spend,
)
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256
from episodic._packing import DROP_POLICY, pack_stm_payload

SCHEMA = "tc003-reserved-floors-v1"

STUDY_ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
PRE_REGISTRATION = STUDY_ROOT / "TC_003_PRE_REGISTRATION.md"
PART1_ARTIFACT = (
    STUDY_ROOT / "artifacts" / "tc003" / "preflight" / "tc003_preflight_part1.json"
)
PF4_ARTIFACT = (
    STUDY_ROOT
    / "artifacts"
    / "tc003"
    / "preflight"
    / "tc003_preflight_pf4_reachability.json"
)
TC001_SUMMARY = STUDY_ROOT / "runs" / "tc001" / "run" / "summary.json"
TC002_SUMMARY = STUDY_ROOT / "runs" / "tc002" / "run" / "summary.json"


# ---------------------------------------------------------------------------
# Registered constants -- TC_003_PRE_REGISTRATION.md
# ---------------------------------------------------------------------------

PRIMARY_BUDGET = 16_000
SECONDARY_BUDGET = 32_000
PRIMARY_ENDPOINT = "complete"
SECONDARY_ENDPOINT = "any"
NULL_BAND_BY_BUDGET = {16_000: 4, 32_000: 10}
CONTRAST_COUNT = 6
ALPHA = 0.01 / CONTRAST_COUNT
SIGNAL_ALPHA = 0.10 / CONTRAST_COUNT
WRAPPER_DELTA = 18
SEED = 5005

ARMS = (
    "flat",
    "n_first",
    "k_first",
    "dual",
    "dual_ranked",
    "floors",
    "floors_dual",
)

# (id, X, Y, X-wins name, Y-wins name)
CONTRASTS = (
    ("C1", "floors", "n_first", "FLOORS_WINS", "N_FIRST_WINS"),
    ("C2", "floors", "k_first", "FLOORS_WINS", "K_FIRST_WINS"),
    ("C3", "floors", "flat", "FLOORS_WINS", "FLAT_WINS"),
    ("C4", "floors_dual", "dual", "FLOORS_DUAL_WINS", "DUAL_WINS"),
    (
        "C5",
        "floors_dual",
        "dual_ranked",
        "FLOORS_DUAL_WINS",
        "RANKED_WINS",
    ),
    ("C6", "floors_dual", "flat", "FLOORS_DUAL_WINS", "FLAT_WINS"),
)
PRIMARY_CONTRAST = "C1"
ISOLATING_CONTRAST = "C5"
NO_BAR = frozenset({(32_000, "C5")})
WRAPPER_MATCHED_CONTRASTS = ("C3",)
PHASES = ("g0", "run")

# Twenty values transcribed from section 8.1, never learned from an artifact.
ANCHOR: dict[tuple[int, str], dict[str, int]] = {
    (16_000, "complete"): {
        "flat": 749,
        "n_first": 314,
        "k_first": 461,
        "dual": 472,
        "dual_ranked": 748,
    },
    (16_000, "any"): {
        "flat": 803,
        "n_first": 381,
        "k_first": 519,
        "dual": 528,
        "dual_ranked": 801,
    },
    (32_000, "complete"): {
        "flat": 810,
        "n_first": 633,
        "k_first": 685,
        "dual": 694,
        "dual_ranked": 811,
    },
    (32_000, "any"): {
        "flat": 842,
        "n_first": 687,
        "k_first": 732,
        "dual": 740,
        "dual_ranked": 843,
    },
}

# PF4's direction-free controls, also transcribed before the run.
CONTROL_ANCHOR = {
    (16_000, "floors"): {"zero_service_separates": 871, "overlap": 871},
    (16_000, "floors_dual"): {"zero_service_separates": 633, "overlap": 871},
    (32_000, "floors"): {"zero_service_separates": 871, "overlap": 871},
    (32_000, "floors_dual"): {"zero_service_separates": 351, "overlap": 871},
}


class TC003Error(RuntimeError):
    """Raised when a registered precondition or invariant fails."""


# ---------------------------------------------------------------------------
# Candidate and arm measurement
# ---------------------------------------------------------------------------


def _state(records: Sequence[dict], query: np.ndarray, budget: int, config):
    return build_candidate_state(
        episodes=records,
        query_embedding=query,
        budget=budget,
        config=config,
    )


def _owner_map(state) -> dict[str, str]:
    offers = tier_offers(state)
    owner: dict[str, str] = {}
    for tier in OWNERSHIP_DEFAULT:
        for episode in offers[tier]:
            owner.setdefault(str(episode["id"]), tier)
    return owner


def _reserved_ids(pack: FloorsPack, state) -> frozenset[str]:
    """Recover exact reserved admissions from the allocator's committed trace.

    ``FloorsPack`` records allowances and per-tier reserved counts.  Replaying
    the pure, tier-local admission predicate gives the identities needed by
    section 4's evidence-phase attribution.  The counts and final delivered set
    are asserted so a drift fails rather than silently changing attribution.
    """
    offers = tier_offers(state)
    admitted: dict[str, list[dict]] = {tier: [] for tier in TIERS}
    identities: set[str] = set()
    for tier in OWNERSHIP_DEFAULT:
        for episode in offers[tier]:
            identifier = str(episode["id"])
            if pack.owner.get(identifier) != tier:
                continue
            candidate = [*admitted[tier], episode]
            if tier_spend(tier, candidate) <= pack.allowances[tier]:
                admitted[tier] = candidate
                identities.add(identifier)
    observed = {tier: len(admitted[tier]) for tier in TIERS}
    if observed != pack.reserved_admitted:
        raise TC003Error(
            f"Reserved-phase identity replay disagrees: {observed} != "
            f"{pack.reserved_admitted}"
        )
    if not identities <= pack.delivered:
        raise TC003Error("Reserved-phase replay contains an undelivered identity")
    return frozenset(identities)


def _tier_label(tier: str) -> str:
    return {"n": "recency", "k": "k", "c": "coverage"}.get(tier, "outside")


def _tier_counts(
    delivered: set[str], owner: Mapping[str, str]
) -> dict[str, int]:
    counts = {"recency": 0, "k": 0, "coverage": 0, "outside": 0}
    for identifier in delivered:
        counts[_tier_label(owner.get(identifier, "outside"))] += 1
    return counts


def _labels(identities: Iterable[str], labels: Mapping[str, str]) -> str:
    return "|".join(sorted({labels.get(identifier, "outside") for identifier in identities}))


def _floor_fields(
    pack: FloorsPack,
    state,
    wanted: frozenset[str],
) -> dict[str, Any]:
    delivered = set(pack.delivered)
    reserved = set(_reserved_ids(pack, state))
    owner_labels = {
        identifier: _tier_label(tier) for identifier, tier in pack.owner.items()
    }
    phase_labels = {
        identifier: ("reserved" if identifier in reserved else "contested")
        for identifier in delivered
    }
    evidence = wanted & delivered
    offers = tier_offers(state)
    owned = {
        tier: sum(
            1
            for episode in offers[tier]
            if pack.owner[str(episode["id"])] == tier
        )
        for tier in TIERS
    }
    fields: dict[str, Any] = {
        "delivered_ids": delivered,
        "chars": len(pack.payload),
        "counts": _tier_counts(delivered, pack.owner),
        "evidence_tiers": _labels(evidence, owner_labels),
        "evidence_phases": _labels(evidence, phase_labels),
        "evidence_tier_phase": "|".join(
            sorted(
                {
                    f"{owner_labels[identifier]}:{phase_labels[identifier]}"
                    for identifier in evidence
                }
            )
        ),
        "reserved_total": len(reserved),
        "contested_total": len(delivered - reserved),
        "everything_fits": len(delivered)
        == len({str(e["id"]) for tier in TIERS for e in offers[tier]}),
    }
    for tier in TIERS:
        label = _tier_label(tier)
        fields[f"reserved_{label}"] = pack.reserved_admitted[tier]
        fields[f"contested_{label}"] = pack.contested_admitted[tier]
        fields[f"floor_binds_{label}"] = owned[tier] > pack.reserved_admitted[tier]
        fields[f"floor_slack_{label}"] = (
            owned[tier] == pack.reserved_admitted[tier]
            and pack.allowances[tier] > 0
        )
    return fields


def _base_arm_fields(
    delivered: set[str],
    payload: str,
    owner: Mapping[str, str],
    wanted: frozenset[str],
) -> dict[str, Any]:
    labels = {identifier: _tier_label(tier) for identifier, tier in owner.items()}
    return {
        "delivered_ids": delivered,
        "chars": len(payload),
        "counts": _tier_counts(delivered, owner),
        "evidence_tiers": _labels(wanted & delivered, labels),
    }


def _arm_pack(
    episodes: Sequence[Episode],
    question: QuestionCase,
    query: np.ndarray,
    wanted: frozenset[str],
    budget: int,
    *,
    include_wrapper_match: bool,
) -> dict[str, Any]:
    records = [episode.record for episode in episodes]
    relevance = relevance_map(records, query)
    shipped_state = _state(records, query, budget, SHIPPED_CONFIG)
    dual_state = _state(records, query, budget, DUAL_CONFIG)

    n_pack = pack_stm_payload(
        list(shipped_state.recent),
        [*shipped_state.k_hits, *shipped_state.coverage],
        budget,
    )
    k_pack = pack_k_first(shipped_state, budget=budget)
    dual_pack = pack_stm_payload(
        list(dual_state.recent), [*dual_state.k_hits, *dual_state.coverage], budget
    )
    ranked_payload, ranked_ids, _ranked_counts = dual_ranked_context(
        episodes, query, budget
    )
    flat_payload, flat_ids = flat_context(episodes, query, budget)
    floor_pack = floors_pack(shipped_state, relevance, budget)
    floor_dual_pack = floors_pack(dual_state, relevance, budget)

    shipped_owner = _owner_map(shipped_state)
    dual_owner = _owner_map(dual_state)
    flat_owner = shipped_owner
    packed = {
        "flat": _base_arm_fields(
            set(flat_ids), flat_payload, flat_owner, wanted
        ),
        "n_first": _base_arm_fields(
            set(_delivered_ids(n_pack.payload, records)),
            n_pack.payload,
            shipped_owner,
            wanted,
        ),
        "k_first": _base_arm_fields(
            set(_delivered_ids(k_pack.payload, records)),
            k_pack.payload,
            shipped_owner,
            wanted,
        ),
        "dual": _base_arm_fields(
            set(_delivered_ids(dual_pack.payload, records)),
            dual_pack.payload,
            dual_owner,
            wanted,
        ),
        "dual_ranked": _base_arm_fields(
            set(ranked_ids), ranked_payload, dual_owner, wanted
        ),
        "floors": _floor_fields(floor_pack, shipped_state, wanted),
        "floors_dual": _floor_fields(floor_dual_pack, dual_state, wanted),
    }
    if include_wrapper_match:
        matched_payload, matched_ids = flat_context(
            episodes, query, budget - WRAPPER_DELTA
        )
        packed["flat_matched"] = _base_arm_fields(
            set(matched_ids), matched_payload, flat_owner, wanted
        )
    return packed


def _row(
    episodes: Sequence[Episode],
    question: QuestionCase,
    query: np.ndarray,
    wanted: frozenset[str],
    budget: int,
    *,
    include_wrapper_match: bool = True,
) -> dict[str, Any]:
    packed = _arm_pack(
        episodes,
        question,
        query,
        wanted,
        budget,
        include_wrapper_match=include_wrapper_match,
    )
    ranks = {
        episodes[index].identity: rank
        for rank, index in enumerate(flat_order(episodes, query), start=1)
    }
    evidence_ranks = sorted(ranks[identity] for identity in wanted)
    row: dict[str, Any] = {
        "question_id": question.identity,
        "question_content_sha256": question.content_sha256,
        "sample_id": question.sample_id,
        "source_index": question.source_index,
        "category": question.category,
        "resolved_evidence_count": len(question.resolved_evidence_ids),
        "unresolved_evidence_count": len(question.unresolved_evidence_ids),
        "complete_evaluable": not question.unresolved_evidence_ids,
        "evidence_episodes": len(wanted),
        "flat_best_evidence_rank": evidence_ranks[0],
        "flat_worst_evidence_rank": evidence_ranks[-1],
        "budget_chars": budget,
        "flat_matched_budget_chars": budget - WRAPPER_DELTA,
    }
    for arm, fields in packed.items():
        delivered = fields["delivered_ids"]
        row[f"{arm}_complete"] = wanted <= delivered
        row[f"{arm}_any"] = bool(wanted & delivered)
        row[f"{arm}_delivered"] = len(delivered)
        row[f"{arm}_evidence_delivered"] = len(wanted & delivered)
        row[f"{arm}_chars"] = fields["chars"]
        row[f"{arm}_evidence_tiers"] = fields["evidence_tiers"]
        for label, count in fields["counts"].items():
            row[f"{arm}_{label}"] = count
        if arm.startswith("floors"):
            for key, value in fields.items():
                if key not in {
                    "delivered_ids",
                    "chars",
                    "counts",
                    "evidence_tiers",
                }:
                    row[f"{arm}_{key}"] = value
    return row


def measure(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    *,
    budget: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in conversations:
        episodes = by_conversation[case.sample_id]
        evidence = _evidence_index(case, episodes)
        for question in case.questions:
            if question.duplicate_ordinal or not question.resolved_evidence_ids:
                continue
            rows.append(
                _row(
                    episodes,
                    question,
                    vectors[question.question],
                    evidence[question.identity],
                    budget,
                )
            )
    return rows


# ---------------------------------------------------------------------------
# Statistics and registered dispositions
# ---------------------------------------------------------------------------


def paired(
    rows: Sequence[dict[str, Any]], left: str, right: str, endpoint: str
) -> dict[str, Any]:
    left_key, right_key = f"{left}_{endpoint}", f"{right}_{endpoint}"
    gains = sum(1 for row in rows if row[left_key] and not row[right_key])
    losses = sum(1 for row in rows if row[right_key] and not row[left_key])
    discordant = gains + losses
    return {
        "endpoint": endpoint,
        "left": left,
        "right": right,
        "n": len(rows),
        "left_hits": sum(1 for row in rows if row[left_key]),
        "right_hits": sum(1 for row in rows if row[right_key]),
        "gains": gains,
        "losses": losses,
        "ties": len(rows) - discordant,
        "discordant": discordant,
        "net": gains - losses,
        "p_left_one_sided": one_sided_sign_p(gains, discordant),
        "p_right_one_sided": one_sided_sign_p(losses, discordant),
    }


def band_for(budget: int) -> int:
    if budget not in NULL_BAND_BY_BUDGET:
        raise TC003Error(
            f"No null band is registered for {budget}; registered budgets are "
            f"{sorted(NULL_BAND_BY_BUDGET)}"
        )
    return NULL_BAND_BY_BUDGET[budget]


def verdict(
    statistic: dict[str, Any],
    contrast: tuple[str, str, str, str, str],
    *,
    budget: int,
) -> dict[str, Any]:
    identifier, left, right, left_name, right_name = contrast
    band = band_for(budget)
    if (budget, identifier) in NO_BAR:
        return {
            "contrast": identifier,
            "left": left,
            "right": right,
            "disposition": "DESCRIPTIVE",
            "verdict": "NO_BAR_REGISTERED",
            "band": None,
            "registered_budget_band": band,
            "statistic": statistic,
        }
    net = statistic["net"]
    p_left = statistic["p_left_one_sided"]
    p_right = statistic["p_right_one_sided"]
    if abs(net) < band:
        disposition, name = "D0a", "NO_DIFFERENCE_ESTABLISHED_INSIDE_BAND"
    elif net >= band and p_left <= ALPHA:
        disposition, name = "D1", left_name
    elif net >= band and p_left <= SIGNAL_ALPHA:
        disposition, name = "D2", f"{left_name}_CARRIES_SIGNAL"
    elif net <= -band and p_right <= ALPHA:
        disposition, name = "D3", right_name
    elif net <= -band and p_right <= SIGNAL_ALPHA:
        disposition, name = "D4", f"{right_name}_CARRIES_SIGNAL"
    else:
        disposition, name = "D0b", "NO_DIFFERENCE_ESTABLISHED_NOT_SEPARABLE"
    return {
        "contrast": identifier,
        "left": left,
        "right": right,
        "disposition": disposition,
        "verdict": name,
        "band": band,
        "alpha": ALPHA,
        "signal_alpha": SIGNAL_ALPHA,
        "statistic": statistic,
    }


def all_contrasts(
    rows: Sequence[dict[str, Any]], endpoint: str, *, budget: int
) -> dict[str, Any]:
    evaluable = (
        [row for row in rows if row["complete_evaluable"]]
        if endpoint == "complete"
        else list(rows)
    )
    return {
        contrast[0]: verdict(
            paired(evaluable, contrast[1], contrast[2], endpoint),
            contrast,
            budget=budget,
        )
        for contrast in CONTRASTS
    }


def _descriptive_cuts(
    rows: Sequence[dict[str, Any]], endpoint: str
) -> dict[str, Any]:
    evaluable = (
        [row for row in rows if row["complete_evaluable"]]
        if endpoint == "complete"
        else list(rows)
    )
    return {
        "by_conversation": {
            sample_id: {
                contrast[0]: paired(
                    [row for row in evaluable if row["sample_id"] == sample_id],
                    contrast[1],
                    contrast[2],
                    endpoint,
                )
                for contrast in CONTRASTS
            }
            for sample_id in sorted({row["sample_id"] for row in evaluable})
        },
        "by_category": {
            str(category): {
                contrast[0]: paired(
                    [row for row in evaluable if row["category"] == category],
                    contrast[1],
                    contrast[2],
                    endpoint,
                )
                for contrast in CONTRASTS
            }
            for category in sorted({row["category"] for row in evaluable})
        },
    }


def _composition(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for arm in ARMS:
        carriers: dict[str, int] = {}
        for row in rows:
            label = row.get(f"{arm}_evidence_tiers", "")
            if label:
                carriers[label] = carriers.get(label, 0) + 1
        arm_result: dict[str, Any] = {
            "delivered_by_tier": {
                tier: _distribution(row[f"{arm}_{tier}"] for row in rows)
                for tier in ("recency", "k", "coverage", "outside")
            },
            "carrying_tier_when_evidence_arrived": dict(sorted(carriers.items())),
        }
        if arm.startswith("floors"):
            arm_result["reserved_admitted"] = {
                tier: _distribution(
                    row[f"{arm}_reserved_{tier}"] for row in rows
                )
                for tier in ("recency", "k", "coverage")
            }
            arm_result["contested_admitted"] = {
                tier: _distribution(
                    row[f"{arm}_contested_{tier}"] for row in rows
                )
                for tier in ("recency", "k", "coverage")
            }
            arm_result["floor_binds_questions"] = {
                tier: sum(
                    1 for row in rows if row[f"{arm}_floor_binds_{tier}"]
                )
                for tier in ("recency", "k", "coverage")
            }
            arm_result["floor_slack_questions"] = {
                tier: sum(
                    1 for row in rows if row[f"{arm}_floor_slack_{tier}"]
                )
                for tier in ("recency", "k", "coverage")
            }
            arm_result["everything_fits_questions"] = sum(
                1 for row in rows if row[f"{arm}_everything_fits"]
            )
            for key in ("evidence_phases", "evidence_tier_phase"):
                labels: dict[str, int] = {}
                for row in rows:
                    label = row.get(f"{arm}_{key}", "")
                    if label:
                        labels[label] = labels.get(label, 0) + 1
                arm_result[f"{key}_when_evidence_arrived"] = dict(
                    sorted(labels.items())
                )
        result[arm] = arm_result
    return result


def summarize(rows: Sequence[dict[str, Any]], budget: int) -> dict[str, Any]:
    complete_rows = [row for row in rows if row["complete_evaluable"]]
    cuts = {
        endpoint: _descriptive_cuts(rows, endpoint)
        for endpoint in ("complete", "any")
    }
    return {
        "budget_chars": budget,
        "null_band": band_for(budget),
        "population": {
            "questions": len(rows),
            "complete_evaluable": len(complete_rows),
        },
        "contrasts_complete": all_contrasts(rows, "complete", budget=budget),
        "contrasts_any": all_contrasts(rows, "any", budget=budget),
        "descriptive_cuts": cuts,
        "delivery": {
            arm: {
                "episodes": _distribution(row[f"{arm}_delivered"] for row in rows),
                "chars": _distribution(row[f"{arm}_chars"] for row in rows),
            }
            for arm in ARMS
        },
        "composition": _composition(rows),
    }


def wrapper_matched_c3(
    rows: Sequence[dict[str, Any]], budget: int
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "floors_budget_chars": budget,
        "flat_budget_chars": budget - WRAPPER_DELTA,
        "bar": None,
        "can_change_disposition": False,
        "endpoints": {},
    }
    for endpoint in ("complete", "any"):
        evaluable = (
            [row for row in rows if row["complete_evaluable"]]
            if endpoint == "complete"
            else list(rows)
        )
        primary = paired(evaluable, "floors", "flat", endpoint)
        matched = paired(evaluable, "floors", "flat_matched", endpoint)
        result["endpoints"][endpoint] = {
            "primary": primary,
            "wrapper_matched": matched,
            "direction_agrees": _direction(primary["net"])
            == _direction(matched["net"]),
        }
    return result


def _direction(net: int) -> str:
    return "floors" if net > 0 else ("flat" if net < 0 else "tie")


def discordant_rows(
    rows: Sequence[dict[str, Any]], left: str, right: str, endpoint: str
) -> list[dict[str, Any]]:
    evaluable = (
        [row for row in rows if row["complete_evaluable"]]
        if endpoint == "complete"
        else list(rows)
    )
    left_key, right_key = f"{left}_{endpoint}", f"{right}_{endpoint}"
    result = []
    for row in evaluable:
        if row[left_key] == row[right_key]:
            continue
        result.append(
            {
                "question_id": row["question_id"],
                "sample_id": row["sample_id"],
                "category": row["category"],
                "direction": "gain" if row[left_key] else "loss",
                "evidence_episodes": row["evidence_episodes"],
                "flat_best_evidence_rank": row["flat_best_evidence_rank"],
                "flat_worst_evidence_rank": row["flat_worst_evidence_rank"],
                f"{left}_evidence_delivered": row[f"{left}_evidence_delivered"],
                f"{right}_evidence_delivered": row[f"{right}_evidence_delivered"],
                f"{left}_evidence_tiers": row.get(f"{left}_evidence_tiers", ""),
                f"{right}_evidence_tiers": row.get(f"{right}_evidence_tiers", ""),
                f"{left}_evidence_phases": row.get(
                    f"{left}_evidence_phases", ""
                ),
                f"{right}_evidence_phases": row.get(
                    f"{right}_evidence_phases", ""
                ),
            }
        )
    return result


# ---------------------------------------------------------------------------
# G0 and deterministic gates
# ---------------------------------------------------------------------------


def _inherited_hits(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    budget: int,
) -> dict[str, dict[str, int]]:
    counts = {
        endpoint: {arm: 0 for arm in ARMS[:5]}
        for endpoint in ("complete", "any")
    }
    for case in conversations:
        episodes = by_conversation[case.sample_id]
        records = [episode.record for episode in episodes]
        evidence = _evidence_index(case, episodes)
        for question in case.questions:
            if question.duplicate_ordinal or not question.resolved_evidence_ids:
                continue
            query = vectors[question.question]
            wanted = evidence[question.identity]
            shipped_state = _state(records, query, budget, SHIPPED_CONFIG)
            dual_state = _state(records, query, budget, DUAL_CONFIG)
            n_pack = pack_stm_payload(
                list(shipped_state.recent),
                [*shipped_state.k_hits, *shipped_state.coverage],
                budget,
            )
            k_pack = pack_k_first(shipped_state, budget=budget)
            dual_pack = pack_stm_payload(
                list(dual_state.recent),
                [*dual_state.k_hits, *dual_state.coverage],
                budget,
            )
            flat_payload, flat_ids = flat_context(episodes, query, budget)
            ranked_payload, ranked_ids, _counts = dual_ranked_context(
                episodes, query, budget
            )
            del flat_payload, ranked_payload
            delivered = {
                "flat": set(flat_ids),
                "n_first": set(_delivered_ids(n_pack.payload, records)),
                "k_first": set(_delivered_ids(k_pack.payload, records)),
                "dual": set(_delivered_ids(dual_pack.payload, records)),
                "dual_ranked": set(ranked_ids),
            }
            for arm, identities in delivered.items():
                counts["any"][arm] += int(bool(wanted & identities))
                if not question.unresolved_evidence_ids:
                    counts["complete"][arm] += int(wanted <= identities)
    return counts


def _committed_anchor() -> dict[tuple[int, str], dict[str, int]]:
    tc001 = json.loads(TC001_SUMMARY.read_text(encoding="utf-8"))
    tc002 = json.loads(TC002_SUMMARY.read_text(encoding="utf-8"))
    result: dict[tuple[int, str], dict[str, int]] = {}
    tc001_blocks = {16_000: tc001["primary"], 32_000: tc001["secondary_budget"]}
    tc002_blocks = {32_000: tc002["primary"], 16_000: tc002["secondary_budget"]}
    tc001_keys = {
        "complete": "primary_complete_evidence",
        "any": "secondary_any_evidence",
    }
    for budget in (PRIMARY_BUDGET, SECONDARY_BUDGET):
        for endpoint in ("complete", "any"):
            old = tc001_blocks[budget][tc001_keys[endpoint]]
            contrasts = tc002_blocks[budget][f"contrasts_{endpoint}"]
            result[(budget, endpoint)] = {
                "flat": old["flat_hits"],
                "n_first": old["tiered_hits"],
                "k_first": contrasts["C1"]["statistic"]["left_hits"],
                "dual": contrasts["C3"]["statistic"]["left_hits"],
                "dual_ranked": contrasts["C4"]["statistic"]["left_hits"],
            }
    return result


def _overlap(state) -> bool:
    memberships = [
        {str(episode["id"]) for episode in tier_offers(state)[tier]}
        for tier in TIERS
    ]
    all_ids = set().union(*memberships)
    return any(
        sum(identifier in members for members in memberships) > 1
        for identifier in all_ids
    )


def _g0_controls(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    budget: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for arm, config in FLOOR_CONFIGS.items():
        reductions = 0
        zero_service_separates = 0
        overlaps = 0
        for case in conversations:
            episodes = by_conversation[case.sample_id]
            records = [episode.record for episode in episodes]
            for question in case.questions:
                if question.duplicate_ordinal or not question.resolved_evidence_ids:
                    continue
                query = vectors[question.question]
                state = _state(records, query, budget, config)
                relevance = relevance_map(records, query)
                assert_zero_floor_reduction(state, records, query, budget, config)
                reductions += 1
                control = service_permutation(
                    state, relevance, budget, floors="zero"
                )
                zero_service_separates += int(not control["set_invariant"])
                overlaps += int(_overlap(state))
        expected = CONTROL_ANCHOR[(budget, arm)]
        result[arm] = {
            "questions": reductions,
            "zero_floor_reductions_passed": reductions,
            "zero_service_order_separates_questions": zero_service_separates,
            "overlap_questions": overlaps,
            "registered": expected,
            "status": (
                "PASS"
                if reductions == 871
                and zero_service_separates == expected["zero_service_separates"]
                and overlaps == expected["overlap"]
                else "FAIL"
            ),
        }
    return result


def g0_reproduction(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
) -> dict[str, Any]:
    committed = _committed_anchor()
    rows: list[dict[str, Any]] = []
    mismatches: list[str] = []
    controls: dict[str, Any] = {}
    for budget in (PRIMARY_BUDGET, SECONDARY_BUDGET):
        measured = _inherited_hits(conversations, by_conversation, vectors, budget)
        for endpoint in ("complete", "any"):
            key = (budget, endpoint)
            expected = ANCHOR[key]
            recorded = committed[key]
            observed = measured[endpoint]
            agrees = observed == expected == recorded
            rows.append(
                {
                    "budget_chars": budget,
                    "endpoint": endpoint,
                    "registered": expected,
                    "recomputed": observed,
                    "committed_artifacts": recorded,
                    "agrees": agrees,
                }
            )
            if not agrees:
                mismatches.append(f"anchor {budget}/{endpoint} disagrees")
        controls[str(budget)] = _g0_controls(
            conversations, by_conversation, vectors, budget
        )
        for arm, block in controls[str(budget)].items():
            if block["status"] != "PASS":
                mismatches.append(f"control {budget}/{arm} failed")
    return {
        "schema": SCHEMA,
        "gate": "G0",
        "status": "PASS" if not mismatches else "FAIL",
        "claim": (
            "All twenty inherited cells reproduce both the transcription and "
            "committed artifacts; all 3,484 zero-floor reductions are byte-"
            "identical; both deterministic controls are live."
        ),
        "anchor_rows": rows,
        "controls": controls,
        "mismatches": mismatches,
        "committed_artifact_sha256": {
            "tc001_summary": sha256_file(TC001_SUMMARY),
            "tc002_summary": sha256_file(TC002_SUMMARY),
        },
    }


def _permutation_summary(rows: Sequence[dict[str, Any]], kind: str) -> dict[str, Any]:
    result = {
        "questions": len(rows),
        "set_invariant_questions": sum(1 for row in rows if row["set_invariant"]),
        "distinct_sets": _distribution(row["distinct_sets"] for row in rows),
    }
    if kind == "service":
        result["payload_invariant_questions"] = sum(
            1 for row in rows if row["payload_invariant"]
        )
    else:
        result["max_symmetric_difference"] = _distribution(
            row["max_symmetric_difference"] for row in rows
        )
        result["questions_with_no_overlap"] = sum(
            1 for row in rows if row["overlaps"]["in_two_or_more"] == 0
        )
    return result


def deterministic_checks(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Read I1/I2 before evidence labels are opened by the run phase."""
    budgets: dict[str, Any] = {}
    i1_failures = 0
    for budget in (PRIMARY_BUDGET, SECONDARY_BUDGET):
        budgets[str(budget)] = {}
        for arm, config in FLOOR_CONFIGS.items():
            service_rows: list[dict[str, Any]] = []
            ownership_rows: list[dict[str, Any]] = []
            ownership_zero_rows: list[dict[str, Any]] = []
            for case in conversations:
                episodes = by_conversation[case.sample_id]
                records = [episode.record for episode in episodes]
                for question in case.questions:
                    if question.duplicate_ordinal or not question.resolved_evidence_ids:
                        continue
                    query = vectors[question.question]
                    state = _state(records, query, budget, config)
                    relevance = relevance_map(records, query)
                    service_rows.append(
                        service_permutation(
                            state, relevance, budget, floors="equal"
                        )
                    )
                    ownership_rows.append(
                        ownership_permutation(
                            state, relevance, budget, floors="equal"
                        )
                    )
                    ownership_zero_rows.append(
                        ownership_permutation(
                            state, relevance, budget, floors="zero"
                        )
                    )
            service_summary = _permutation_summary(service_rows, "service")
            ownership_summary = _permutation_summary(ownership_rows, "ownership")
            zero_summary = _permutation_summary(ownership_zero_rows, "ownership")
            i1_failures += len(service_rows) - service_summary["set_invariant_questions"]
            budgets[str(budget)][arm] = {
                "I1_service_order": service_summary,
                "I2_ownership_order": ownership_summary,
                "ownership_zero_floor_reference": zero_summary,
            }
    i2_invariant = all(
        block["I2_ownership_order"]["set_invariant_questions"]
        == block["I2_ownership_order"]["questions"]
        for budget in budgets.values()
        for block in budget.values()
    )
    return {
        "schema": SCHEMA,
        "status": "PASS" if i1_failures == 0 else "FAIL",
        "I1": "PASS" if i1_failures == 0 else "FAIL",
        "I2": "PASS" if i2_invariant else "FAIL",
        "I2_registered_reading": (
            "allocation is independent of every order in the design"
            if i2_invariant
            else "floors make allocation independent of service order and leave it dependent on ownership order"
        ),
        "budgets": budgets,
    }


# ---------------------------------------------------------------------------
# Guards, phases, provenance, and output
# ---------------------------------------------------------------------------


def assert_registration_agrees() -> dict[str, Any]:
    text = PRE_REGISTRATION.read_text(encoding="utf-8")
    required = {
        "primary_budget": "Primary **16,000 characters**",
        "secondary_budget": "secondary **32,000**",
        "primary_endpoint": "**Primary endpoint.** Complete-evidence delivery at 16,000",
        "primary_population": "The primary population is 868 questions",
        "bands": "**B = 4 questions at 16,000. B = 10 questions at 32,000.**",
        "band_no_shrink": "**A band may not shrink.**",
        "family": "**Six** registered contrasts",
        "alpha": "**0.01 / 6**",
        "signal_alpha": "**0.10 / 6**",
        "headline": "**C1 is the headline, whatever it says.**",
        "isolating": "| Isolating contrast | **C5** |",
        "no_bar": "**C5 is unreachable at 32,000",
        "wrapper": "**18 characters**",
        "arms": "The seven above are the arms",
        "service_bar": "**I1 — service-order invariance.**",
        "ownership_bar": "**I2 — ownership-order invariance.**",
    }
    missing = sorted(name for name, token in required.items() if token not in text)
    if missing:
        raise TC003Error(f"Registered parameters are missing: {missing}")
    if "PENDING-" in text:
        raise TC003Error("The pre-registration contains an unlocked placeholder")
    return {
        "status": "PASS",
        "pre_registration": _repo_relative(PRE_REGISTRATION),
        "pre_registration_sha256": sha256_file(PRE_REGISTRATION),
        "design_commit": _git(
            "log", "--format=%H", "-1", "--", _repo_relative(PRE_REGISTRATION)
        ),
        "checked": sorted(required),
    }


def run_precondition(output_root: Path) -> dict[str, Any]:
    path = output_root / "g0" / "g0_reproduction.json"
    if not path.exists():
        raise TC003Error(f"G0 has not run: {path} is absent")
    if not _git_tracked(path):
        raise TC003Error(f"G0's artifact is not committed: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise TC003Error(f"G0 did not pass: {payload.get('status')}")
    relative = _repo_relative(path)
    return {
        "status": "PASS",
        "gate": relative,
        "gate_sha256": sha256_file(path),
        "gate_commit": _git("log", "--format=%H", "-1", "--", relative),
        "gate_committed_before_run": True,
    }


def run_phase(output_root: Path, phase: str) -> dict[str, Any]:
    if phase not in PHASES:
        raise TC003Error(f"Unregistered phase: {phase}")
    registration = assert_registration_agrees()
    precondition = None if phase == "g0" else run_precondition(output_root)
    started = time.time()
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    conversations = adapt_development(DATASET_PATH)
    with ModelCallGuard() as guard:
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
            raise TC003Error(f"Read-only cache reported {reuse['misses']} misses")
        by_conversation = {
            case.sample_id: build_episodes(case, vectors) for case in conversations
        }
        if phase == "g0":
            result = g0_reproduction(conversations, by_conversation, vectors)
        else:
            invariance = deterministic_checks(
                conversations, by_conversation, vectors
            )
            if invariance["I1"] == "PASS":
                primary_rows = measure(
                    conversations,
                    by_conversation,
                    vectors,
                    budget=PRIMARY_BUDGET,
                )
                secondary_rows = measure(
                    conversations,
                    by_conversation,
                    vectors,
                    budget=SECONDARY_BUDGET,
                )
            else:
                primary_rows = secondary_rows = []
    audit = guard.audit()

    if phase == "g0":
        output_dir = output_root / "g0"
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(output_dir / "g0_reproduction.json", result)
        _write_json(output_dir / "no_model_call_audit.json", audit)
        _write_json(
            output_dir / "run_header.json",
            _run_header(phase, registration, None, manifest, started, result["status"]),
        )
        _write_artifact_manifest(output_dir)
        return result

    output_dir = output_root / "run"
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "deterministic_invariance.json", invariance)
    if invariance["I1"] != "PASS":
        result = {
            "schema": SCHEMA,
            "status": "STOPPED_AT_I1",
            "standing": "INSTRUMENT_FAILURE",
            "deterministic_invariance": invariance,
            "availability_read": False,
            "cache": {"hits": reuse["hits"], "misses": reuse["misses"]},
        }
    else:
        primary = summarize(primary_rows, PRIMARY_BUDGET)
        secondary = summarize(secondary_rows, SECONDARY_BUDGET)
        headline = primary[f"contrasts_{PRIMARY_ENDPOINT}"][PRIMARY_CONTRAST]
        result = {
            "schema": SCHEMA,
            "status": "COMPLETE",
            "standing": "REGISTERED-OFFLINE_CHARACTERIZATION",
            "primary_contrast": PRIMARY_CONTRAST,
            "isolating_contrast": ISOLATING_CONTRAST,
            "primary_endpoint": PRIMARY_ENDPOINT,
            "verdict": headline,
            "deterministic_invariance": invariance,
            "primary": primary,
            "secondary_budget": secondary,
            "robustness_wrapper_matched_c3": {
                str(PRIMARY_BUDGET): wrapper_matched_c3(
                    primary_rows, PRIMARY_BUDGET
                ),
                str(SECONDARY_BUDGET): wrapper_matched_c3(
                    secondary_rows, SECONDARY_BUDGET
                ),
            },
            "cache": {"hits": reuse["hits"], "misses": reuse["misses"]},
        }
        _write_csv(output_dir / "per_question_primary.csv", primary_rows)
        _write_csv(output_dir / "per_question_secondary.csv", secondary_rows)
        for identifier, left, right, _left_name, _right_name in CONTRASTS:
            _write_csv(
                output_dir
                / f"discordant_{identifier.lower()}_{left}_vs_{right}.csv",
                discordant_rows(primary_rows, left, right, PRIMARY_ENDPOINT),
            )
        _write_json(
            output_dir / "verdict.json",
            primary[f"contrasts_{PRIMARY_ENDPOINT}"],
        )
    _write_json(output_dir / "summary.json", result)
    _write_json(output_dir / "no_model_call_audit.json", audit)
    _write_json(output_dir / "run_precondition.json", precondition)
    outcome = (
        result["verdict"]["verdict"]
        if result["status"] == "COMPLETE"
        else result["status"]
    )
    _write_json(
        output_dir / "run_header.json",
        _run_header(phase, registration, precondition, manifest, started, outcome),
    )
    _write_artifact_manifest(output_dir)
    return result


def _run_header(
    phase: str,
    registration: dict[str, Any],
    precondition: dict[str, Any] | None,
    manifest: dict[str, Any],
    started: float,
    outcome: str,
) -> dict[str, Any]:
    return {
        "study": "TC-003",
        "phase": phase,
        "outcome": outcome,
        "schema": SCHEMA,
        "launch_command": f"python scripts/run_tc003_study.py --phase {phase}",
        "server_build_hash": "NOT_APPLICABLE_OFFLINE_ZERO_INFERENCE",
        "design_commit": registration["design_commit"],
        "execution_commit": _git("rev-parse", "HEAD"),
        "source_worktree_clean": not _git(
            "status",
            "--porcelain",
            "--untracked-files=no",
            "--",
            "src",
            "scripts",
            "tests",
            "episodic",
            _repo_relative(PRE_REGISTRATION),
        ),
        "registration": registration,
        "run_precondition": precondition,
        "parameters": {
            "primary_budget_chars": PRIMARY_BUDGET,
            "secondary_budget_chars": SECONDARY_BUDGET,
            "primary_endpoint": PRIMARY_ENDPOINT,
            "secondary_endpoint": SECONDARY_ENDPOINT,
            "null_band_by_budget": {
                str(key): value for key, value in NULL_BAND_BY_BUDGET.items()
            },
            "alpha": ALPHA,
            "signal_alpha": SIGNAL_ALPHA,
            "contrast_count": CONTRAST_COUNT,
            "primary_contrast": PRIMARY_CONTRAST,
            "isolating_contrast": ISOLATING_CONTRAST,
            "no_bar": [list(value) for value in sorted(NO_BAR)],
            "wrapper_delta_chars": WRAPPER_DELTA,
            "wrapper_matched_contrasts": list(WRAPPER_MATCHED_CONTRASTS),
            "service_orders": [list(order) for order in SERVICE_ORDERS],
            "ownership_default": list(OWNERSHIP_DEFAULT),
            "arms": list(ARMS),
            "seed": SEED,
            "parallel": 1,
            "drop_policy": DROP_POLICY,
            "renderer": "post-DR-001 compact exact-cost renderer",
            "shipped_config": json.loads(SHIPPED_CONFIG.to_json()),
            "dual_config": json.loads(DUAL_CONFIG.to_json()),
        },
        "inputs": {
            "dataset_sha256": manifest["dataset_sha256"],
            "cache_file_sha256": manifest["cache"]["file_sha256"],
            "cache_content_sha256": manifest["cache"]["content_sha256"],
            "embedder_sha256": CARRIED_EMBEDDER_SHA256,
            "development_ids": manifest["development_ids"],
        },
        "sources": {
            _repo_relative(path): sha256_file(path) for path in _source_paths()
        },
        "inference_calls": 0,
        "model_calls": 0,
        "embedding_calls": 0,
        "elapsed_seconds": round(time.time() - started, 3),
    }


def _source_paths() -> list[Path]:
    return [
        Path(__file__).resolve(),
        REPO_ROOT / "src" / "analysis" / "tc003_exploration.py",
        REPO_ROOT / "src" / "analysis" / "tc003_reachability.py",
        REPO_ROOT / "src" / "analysis" / "tc001_exploration.py",
        REPO_ROOT / "src" / "analysis" / "tc001_study.py",
        REPO_ROOT / "src" / "analysis" / "tc001b_exploration.py",
        REPO_ROOT / "src" / "analysis" / "tc002_exploration.py",
        REPO_ROOT / "src" / "analysis" / "tc_standing_arms.py",
        REPO_ROOT / "src" / "analysis" / "ec002_k_first_packing.py",
        REPO_ROOT / "src" / "analysis" / "locomo_nf_development.py",
        REPO_ROOT / "src" / "analysis" / "hh002_arms.py",
        REPO_ROOT / "episodic" / "src" / "episodic" / "_context.py",
        REPO_ROOT / "episodic" / "src" / "episodic" / "_packing.py",
        REPO_ROOT / "episodic" / "src" / "episodic" / "_render.py",
        REPO_ROOT / "episodic" / "src" / "episodic" / "_selection.py",
        PRE_REGISTRATION,
        PART1_ARTIFACT,
        PF4_ARTIFACT,
    ]


def _distribution(values: Iterable[int]) -> dict[str, Any]:
    ordered = sorted(int(value) for value in values)
    if not ordered:
        return {"n": 0}
    return {
        "n": len(ordered),
        "min": ordered[0],
        "p25": ordered[len(ordered) // 4],
        "p50": int(statistics.median(ordered)),
        "p75": ordered[(3 * len(ordered)) // 4],
        "max": ordered[-1],
        "mean": round(statistics.fmean(ordered), 3),
        "zero": sum(1 for value in ordered if value == 0),
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_artifact_manifest(output_dir: Path) -> None:
    entries = {
        path.name: sha256_file(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "artifact_manifest.json"
    }
    _write_json(output_dir / "artifact_manifest.json", entries)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def _git_tracked(path: Path) -> bool:
    try:
        relative = _repo_relative(path)
    except ValueError:
        return False
    return bool(_git("ls-files", "--error-unmatch", relative))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=PHASES, required=True)
    parser.add_argument(
        "--output-root", type=Path, default=STUDY_ROOT / "runs" / "tc003"
    )
    arguments = parser.parse_args()
    result = run_phase(arguments.output_root, arguments.phase)
    json.dump(result, sys.stdout, indent=2, sort_keys=True, default=str)
    sys.stdout.write("\n")


__all__ = [
    "ALPHA",
    "ANCHOR",
    "ARMS",
    "CONTRASTS",
    "CONTROL_ANCHOR",
    "ISOLATING_CONTRAST",
    "NO_BAR",
    "NULL_BAND_BY_BUDGET",
    "PRIMARY_BUDGET",
    "PRIMARY_CONTRAST",
    "PRIMARY_ENDPOINT",
    "SCHEMA",
    "SECONDARY_BUDGET",
    "SIGNAL_ALPHA",
    "TC003Error",
    "all_contrasts",
    "assert_registration_agrees",
    "band_for",
    "deterministic_checks",
    "g0_reproduction",
    "main",
    "measure",
    "paired",
    "run_phase",
    "run_precondition",
    "summarize",
    "verdict",
    "wrapper_matched_c3",
]

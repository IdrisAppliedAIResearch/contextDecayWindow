"""TC-001B: does relevance plus coverage earn its place, with recency removed?

Every constant below is transcribed from
``experiments/components/tier_cost/TC_001B_PRE_REGISTRATION.md``, which is the
authoritative home for all of them. ``assert_registration_agrees`` reads the
registered tokens back out of that document on every run, so a constant cannot
be edited here alone.

Two phases, in this order and enforced:

    g0    Re-run A_FLAT and A_TIERED and require exact agreement with TC-001's
          committed summary. A failed G0 stops the study.
    run   All four arms, four registered contrasts, one primary.

Zero model calls. ``ModelCallGuard`` is TC-001's, reused rather than restated.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

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
    _evidence_index,
    _repo_relative,
    build_episodes,
    flat_context,
    flat_order,
    tiered_context,
    tier_membership,
)
from analysis.tc001_study import ModelCallGuard, one_sided_sign_p
from analysis.tc001b_exploration import (
    DUAL_CONFIG,
    SHIPPED_CONFIG,
    dual_context,
    dual_ranked_context,
)
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256
from episodic._packing import DROP_POLICY

SCHEMA = "tc001b-dual-arm-v1"

STUDY_ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
PRE_REGISTRATION = STUDY_ROOT / "TC_001B_PRE_REGISTRATION.md"
AMENDMENT = (
    STUDY_ROOT / "amendments" / "AMENDMENT_001_dual_arm_escalation.md"
)
PART1_ARTIFACT = (
    STUDY_ROOT / "artifacts" / "tc001b" / "preflight" / "tc001b_preflight_part1.json"
)
PF4_ARTIFACT = (
    STUDY_ROOT
    / "artifacts"
    / "tc001b"
    / "preflight"
    / "tc001b_preflight_pf4_reachability.json"
)
TC001_SUMMARY = STUDY_ROOT / "runs" / "tc001" / "run" / "summary.json"


# --------------------------------------------------------------------------
# Registered parameters - TC_001B_PRE_REGISTRATION.md
# --------------------------------------------------------------------------

#: Section 2.
PRIMARY_BUDGET = 16_000
SECONDARY_BUDGET = 32_000

#: Section 6.1, measured from within-arm sham budget perturbations.
NULL_BAND = 4

#: Section 6.2. Bonferroni over the four registered contrasts.
ALPHA = 0.0025
SIGNAL_ALPHA = 0.025
CONTRAST_COUNT = 4

#: Section 3.2. Applies to C2 alone.
WRAPPER_DELTA = 18

SEED = 5005

ARMS = ("flat", "tiered", "dual", "dual_ranked")

#: Section 6.3, instantiated. (id, X, Y, X-wins name, Y-wins name)
CONTRASTS = (
    ("C1", "dual", "flat", "DUAL_WINS", "FLAT_WINS"),
    ("C2", "dual", "tiered", "DUAL_WINS", "TIERED_WINS"),
    ("C3", "dual_ranked", "flat", "RANKED_WINS", "FLAT_WINS"),
    ("C4", "dual_ranked", "dual", "RANKED_WINS", "DUAL_WINS"),
)

#: Section 7.1. PF4 found C3's bar unreachable before the lock - three
#: discordant pairs put its best attainable one-sided p at 0.125, above both
#: alphas, and |net| <= 3 < B makes D0a its only branch. It is registered
#: DESCRIPTIVE: its counts are reported, no disposition is attached.
NO_BAR = frozenset({"C3"})

#: Section 6.4. The headline is registered so it cannot be chosen afterwards.
PRIMARY_CONTRAST = "C1"

PHASES = ("g0", "run")


class TC001BError(RuntimeError):
    """Raised when a registered precondition does not hold."""


# --------------------------------------------------------------------------
# G0 - section 8.1
# --------------------------------------------------------------------------

#: The committed TC-001 values this study is anchored to, transcribed from
#: section 8.1 of the registration rather than read out of the artifact, so
#: a corrupted artifact fails the gate instead of redefining it.
ANCHOR = {
    ("16000", "complete"): (749, 314, 8, 443, -435),
    ("16000", "any"): (803, 381, 8, 430, -422),
    ("32000", "complete"): (810, 633, 7, 184, -177),
    ("32000", "any"): (842, 687, 9, 164, -155),
}


def g0_reproduction(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Re-run TC-001's two arms and require exact agreement.

    Both the freshly computed values and TC-001's committed artifact are
    compared against the transcribed table, so this fails if either the
    instrument or the record has drifted.
    """
    committed = json.loads(TC001_SUMMARY.read_text(encoding="utf-8"))
    committed_blocks = {
        "16000": committed["primary"],
        "32000": committed["secondary_budget"],
    }
    endpoint_key = {
        "complete": "primary_complete_evidence",
        "any": "secondary_any_evidence",
    }

    rows: list[dict[str, Any]] = []
    mismatches: list[str] = []
    for budget in (PRIMARY_BUDGET, SECONDARY_BUDGET):
        measured = _anchor_pass(conversations, by_conversation, vectors, budget)
        for endpoint in ("complete", "any"):
            key = (str(budget), endpoint)
            expected = ANCHOR[key]
            observed = measured[endpoint]
            block = committed_blocks[str(budget)][endpoint_key[endpoint]]
            recorded = (
                block["flat_hits"],
                block["tiered_hits"],
                block["gains"],
                block["losses"],
                block["net"],
            )
            rows.append(
                {
                    "budget_chars": budget,
                    "endpoint": endpoint,
                    "registered": list(expected),
                    "recomputed": list(observed),
                    "committed_artifact": list(recorded),
                    "agrees": observed == expected == recorded,
                }
            )
            if observed != expected:
                mismatches.append(f"recomputed {key}: {observed} != {expected}")
            if recorded != expected:
                mismatches.append(f"committed {key}: {recorded} != {expected}")

    return {
        "schema": SCHEMA,
        "gate": "G0",
        "status": "PASS" if not mismatches else "FAIL",
        "claim": (
            "A_FLAT and A_TIERED reproduce TC-001's committed primary and "
            "secondary tables exactly, so this study's new arms are measured "
            "by the instrument that produced the result they respond to."
        ),
        "rows": rows,
        "mismatches": mismatches,
        "tc001_summary_sha256": sha256_file(TC001_SUMMARY),
    }


def _anchor_pass(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    budget: int,
) -> dict[str, tuple[int, int, int, int, int]]:
    counts = {
        "complete": [0, 0, 0, 0],
        "any": [0, 0, 0, 0],
    }
    for case in conversations:
        episodes = by_conversation[case.sample_id]
        evidence = _evidence_index(case, episodes)
        for question in case.questions:
            if question.duplicate_ordinal or not question.resolved_evidence_ids:
                continue
            target = evidence[question.identity]
            query = vectors[question.question]
            _payload, flat_ids = flat_context(episodes, query, budget)
            _payload, tiered_ids, _report = tiered_context(
                episodes, query, budget, SHIPPED_CONFIG
            )
            flat_set, tiered_set = set(flat_ids), set(tiered_ids)
            outcomes = {
                "any": (bool(target & flat_set), bool(target & tiered_set)),
                "complete": (
                    (target <= flat_set, target <= tiered_set)
                    if not question.unresolved_evidence_ids
                    else None
                ),
            }
            for endpoint, pair in outcomes.items():
                if pair is None:
                    continue
                flat_hit, tiered_hit = pair
                counts[endpoint][0] += int(flat_hit)
                counts[endpoint][1] += int(tiered_hit)
                if tiered_hit and not flat_hit:
                    counts[endpoint][2] += 1
                elif flat_hit and not tiered_hit:
                    counts[endpoint][3] += 1
    return {
        endpoint: (
            value[0],
            value[1],
            value[2],
            value[3],
            value[2] - value[3],
        )
        for endpoint, value in counts.items()
    }


# --------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------


def measure(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    *,
    budget: int,
    dual_budget: int | None = None,
) -> list[dict[str, Any]]:
    """One row per unique question, all four arms, at one budget.

    ``dual_budget`` exists only for section 8.2's wrapper-matched check on
    C2. It defaults to ``budget``, and when it does not, the row records it.
    """
    dual_budget = budget if dual_budget is None else dual_budget
    rows: list[dict[str, Any]] = []
    for case in conversations:
        episodes = by_conversation[case.sample_id]
        evidence = _evidence_index(case, episodes)
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            if not question.resolved_evidence_ids:
                continue
            rows.append(
                _row(
                    episodes,
                    question,
                    vectors[question.question],
                    evidence[question.identity],
                    budget,
                    dual_budget,
                )
            )
    return rows


def _row(
    episodes: Sequence[Episode],
    question: QuestionCase,
    query: np.ndarray,
    wanted: frozenset[str],
    budget: int,
    dual_budget: int,
) -> dict[str, Any]:
    flat_payload, flat_ids = flat_context(episodes, query, budget)
    _payload, tiered_ids, tiered_report = tiered_context(
        episodes, query, budget, SHIPPED_CONFIG
    )
    _payload, dual_ids, dual_report = dual_context(episodes, query, dual_budget)
    ranked_payload, ranked_ids, ranked_counts = dual_ranked_context(
        episodes, query, budget
    )

    shipped_tiers = tier_membership(episodes, query, SHIPPED_CONFIG)
    dual_tiers = tier_membership(episodes, query, DUAL_CONFIG)
    recency_ids = set(shipped_tiers["recency_ids"])
    k_ids = set(shipped_tiers["k_ids"])
    dual_k_ids = set(dual_tiers["k_ids"])

    delivered = {
        "flat": set(flat_ids),
        "tiered": set(tiered_ids),
        "dual": set(dual_ids),
        "dual_ranked": set(ranked_ids),
    }
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
        "dual_budget_chars": dual_budget,
    }
    for arm in ARMS:
        hits = delivered[arm]
        row[f"{arm}_complete"] = wanted <= hits
        row[f"{arm}_any"] = bool(wanted & hits)
        row[f"{arm}_delivered"] = len(hits)
        row[f"{arm}_evidence_delivered"] = len(wanted & hits)

    row["flat_chars"] = len(flat_payload)
    row["tiered_chars"] = tiered_report.chars_delivered
    row["dual_chars"] = dual_report.chars_delivered
    row["dual_ranked_chars"] = ranked_counts["chars_delivered"]

    row["tiered_recency"] = tiered_report.stm_count
    row["tiered_k"] = tiered_report.k_count
    row["tiered_coverage"] = tiered_report.coverage_count
    row["dual_recency"] = dual_report.stm_count
    row["dual_k"] = dual_report.k_count
    row["dual_coverage"] = dual_report.coverage_count
    row["dual_ranked_k"] = ranked_counts["k"]
    row["dual_ranked_coverage"] = ranked_counts["coverage"]

    row["tiered_evidence_tiers"] = _carrying_tiers(
        wanted & delivered["tiered"], recency_ids, k_ids
    )
    row["dual_evidence_tiers"] = _carrying_tiers(
        wanted & delivered["dual"], set(), dual_k_ids
    )
    row["dual_ranked_evidence_tiers"] = _carrying_tiers(
        wanted & delivered["dual_ranked"], set(), dual_k_ids
    )
    return row


def _carrying_tiers(
    delivered_evidence: set[str], recency_ids: set[str], k_ids: set[str]
) -> str:
    """Which tier carried the evidence, by ``build_context``'s own rule."""
    return "|".join(
        sorted(
            {
                "recency"
                if identity in recency_ids
                else ("k" if identity in k_ids else "coverage")
                for identity in delivered_evidence
            }
        )
    )


# --------------------------------------------------------------------------
# Statistics - section 6.2
# --------------------------------------------------------------------------


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


def verdict(
    statistic: dict[str, Any],
    contrast: tuple[str, str, str, str, str],
    *,
    band: int = NULL_BAND,
) -> dict[str, Any]:
    """Section 6.3's disposition table, applied and nothing else.

    The table is exhaustive over the real line, so this function has no
    fallback branch by construction; if it ever needed one, the table
    would be the defect.
    """
    identifier, left, right, left_name, right_name = contrast
    net = statistic["net"]
    p_left = statistic["p_left_one_sided"]
    p_right = statistic["p_right_one_sided"]

    if identifier in NO_BAR:
        # No branch of the table may be applied to this contrast. Returning
        # a disposition here - even D0a, which is the only one its
        # discordant count could reach - would be reading a verdict out of
        # a bar PF4 refused to lock.
        return {
            "contrast": identifier,
            "left": left,
            "right": right,
            "disposition": "DESCRIPTIVE",
            "verdict": "NO_BAR_REGISTERED",
            "reason": (
                "PF4 found this contrast unreachable before the lock; "
                "see TC_001B_PRE_REGISTRATION.md section 7.1"
            ),
            "band": band,
            "statistic": statistic,
        }

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
    rows: Sequence[dict[str, Any]], endpoint: str, *, band: int = NULL_BAND
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
            band=band,
        )
        for contrast in CONTRASTS
    }


def discordant_rows(
    rows: Sequence[dict[str, Any]], left: str, right: str, endpoint: str
) -> list[dict[str, Any]]:
    """Section 4's pre-specified look at the pairs that decided a contrast."""
    left_key, right_key = f"{left}_{endpoint}", f"{right}_{endpoint}"
    out = []
    for row in rows:
        if row[left_key] == row[right_key]:
            continue
        out.append(
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
            }
        )
    return out


def summarize(rows: Sequence[dict[str, Any]], budget: int) -> dict[str, Any]:
    complete_rows = [row for row in rows if row["complete_evaluable"]]
    return {
        "budget_chars": budget,
        "population": {
            "questions": len(rows),
            "complete_evaluable": len(complete_rows),
        },
        "contrasts_complete": all_contrasts(rows, "complete"),
        "contrasts_any": all_contrasts(rows, "any"),
        "by_conversation": {
            sample_id: all_contrasts(
                [row for row in complete_rows if row["sample_id"] == sample_id],
                "complete",
            )
            for sample_id in sorted({row["sample_id"] for row in rows})
        },
        "by_category": {
            str(category): all_contrasts(
                [row for row in complete_rows if row["category"] == category],
                "complete",
            )
            for category in sorted({row["category"] for row in rows})
        },
        "delivery": {
            arm: {
                "episodes": _distribution(row[f"{arm}_delivered"] for row in rows),
                "chars": _distribution(row[f"{arm}_chars"] for row in rows),
            }
            for arm in ARMS
        },
        "composition": _composition(rows),
    }


def _composition(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for arm, keys in (
        ("tiered", ("recency", "k", "coverage")),
        ("dual", ("recency", "k", "coverage")),
        ("dual_ranked", ("k", "coverage")),
    ):
        tiers = {
            key: _distribution(row[f"{arm}_{key}"] for row in rows) for key in keys
        }
        carriers: dict[str, int] = {}
        for row in rows:
            label = row.get(f"{arm}_evidence_tiers", "")
            if not label:
                continue
            carriers[label] = carriers.get(label, 0) + 1
        out[arm] = {
            "delivered_by_tier": tiers,
            "carrying_tier_when_evidence_arrived": dict(sorted(carriers.items())),
            "questions_with_zero_coverage": sum(
                1 for row in rows if row.get(f"{arm}_coverage", 0) == 0
            ),
        }
    return out


# --------------------------------------------------------------------------
# Guards
# --------------------------------------------------------------------------


def assert_registration_agrees() -> dict[str, Any]:
    """Every constant above must appear in the locked document.

    A parameter has one authoritative home and it is the registration.
    This does not prove the document means what the code does - nothing
    mechanical can - but it does stop a constant being edited here alone.
    """
    text = PRE_REGISTRATION.read_text(encoding="utf-8")
    required = {
        "primary_budget": "16,000",
        "secondary_budget": "32,000",
        "null_band": f"**B = {NULL_BAND} questions**",
        "alpha": "`p₊ ≤ 0.0025`",
        "signal_alpha": "`0.0025 < p₊ ≤ 0.025`",
        "wrapper_delta": "18 characters",
        "primary_population": "**868**",
        "primary_contrast": "**C1 is the headline, whatever it says.**",
        "contrast_count": "Four registered contrasts",
        "c3_carries_no_bar": (
            "**C3 therefore carries no bar and is registered `DESCRIPTIVE`.**"
        ),
        "divisor_may_not_shrink": "**The Bonferroni divisor stays at 4**",
    }
    missing = sorted(name for name, token in required.items() if token not in text)
    if missing:
        raise TC001BError(
            f"Registered parameters not found in the pre-registration: {missing}"
        )
    if "PENDING-" in text:
        raise TC001BError(
            "The pre-registration still carries PENDING placeholders; it is "
            "not locked and no arm may be measured against it"
        )
    return {
        "status": "PASS",
        "pre_registration": _repo_relative(PRE_REGISTRATION),
        "pre_registration_sha256": sha256_file(PRE_REGISTRATION),
        "amendment": _repo_relative(AMENDMENT),
        "amendment_sha256": sha256_file(AMENDMENT),
        "checked": sorted(required),
    }


def run_precondition(output_root: Path) -> dict[str, Any]:
    """PF3. The run phase may not open an arm before G0 is committed."""
    path = output_root / "g0" / "g0_reproduction.json"
    if not path.exists():
        raise TC001BError(f"G0 has not run: {path} is absent")
    if not _git_tracked(path):
        raise TC001BError(f"G0's artifact is not committed: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise TC001BError(f"G0 did not pass: {payload.get('status')}")
    relative = _repo_relative(path)
    return {
        "status": "PASS",
        "gate": relative,
        "gate_sha256": sha256_file(path),
        "gate_commit": _git("log", "--format=%H", "-1", "--", relative),
        "gate_committed_before_run": True,
    }


# --------------------------------------------------------------------------
# Phases
# --------------------------------------------------------------------------


def run_phase(output_root: Path, phase: str) -> dict[str, Any]:
    if phase not in PHASES:
        raise TC001BError(f"Unregistered phase: {phase}")
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
            raise TC001BError(f"Read-only cache reported {reuse['misses']} misses")

        by_conversation = {
            case.sample_id: build_episodes(case, vectors) for case in conversations
        }

        if phase == "g0":
            result = g0_reproduction(conversations, by_conversation, vectors)
        else:
            primary_rows = measure(
                conversations, by_conversation, vectors, budget=PRIMARY_BUDGET
            )
            secondary_rows = measure(
                conversations, by_conversation, vectors, budget=SECONDARY_BUDGET
            )
            robustness_rows = measure(
                conversations,
                by_conversation,
                vectors,
                budget=PRIMARY_BUDGET,
                dual_budget=PRIMARY_BUDGET - WRAPPER_DELTA,
            )
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

    primary = summarize(primary_rows, PRIMARY_BUDGET)
    secondary = summarize(secondary_rows, SECONDARY_BUDGET)
    robustness = summarize(robustness_rows, PRIMARY_BUDGET)

    headline = primary["contrasts_complete"][PRIMARY_CONTRAST]
    result = {
        "schema": SCHEMA,
        "status": "COMPLETE",
        "standing": "REGISTERED-OFFLINE",
        "primary_contrast": PRIMARY_CONTRAST,
        "verdict": headline,
        "primary": primary,
        "secondary_budget": secondary,
        "robustness_wrapper_matched_c2": {
            "dual_budget_chars": PRIMARY_BUDGET - WRAPPER_DELTA,
            "tiered_budget_chars": PRIMARY_BUDGET,
            "verdict": robustness["contrasts_complete"]["C2"],
            "agrees_with_primary": (
                robustness["contrasts_complete"]["C2"]["disposition"]
                == primary["contrasts_complete"]["C2"]["disposition"]
            ),
            "dual_chars_delivered": robustness["delivery"]["dual"]["chars"],
        },
        "cache": {"hits": reuse["hits"], "misses": reuse["misses"]},
    }

    output_dir = output_root / "run"
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "summary.json", result)
    _write_json(output_dir / "verdict.json", primary["contrasts_complete"])
    _write_json(output_dir / "no_model_call_audit.json", audit)
    _write_json(output_dir / "run_precondition.json", precondition)
    _write_csv(output_dir / "per_question_primary.csv", primary_rows)
    _write_csv(output_dir / "per_question_secondary.csv", secondary_rows)
    complete_rows = [row for row in primary_rows if row["complete_evaluable"]]
    for identifier, left, right, _lname, _rname in CONTRASTS:
        _write_csv(
            output_dir / f"discordant_{identifier.lower()}_{left}_vs_{right}.csv",
            discordant_rows(complete_rows, left, right, "complete"),
        )
    _write_json(
        output_dir / "run_header.json",
        _run_header(
            phase, registration, precondition, manifest, started, headline["verdict"]
        ),
    )
    _write_artifact_manifest(output_dir)
    return result


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------


def _run_header(
    phase: str,
    registration: dict,
    precondition: dict | None,
    manifest: dict,
    started: float,
    outcome: str,
) -> dict[str, Any]:
    return {
        "study": "TC-001B",
        "phase": phase,
        "outcome": outcome,
        "schema": SCHEMA,
        "design_commit": _git(
            "log", "--format=%H", "-1", "--", _repo_relative(PRE_REGISTRATION)
        ),
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
            "null_band": NULL_BAND,
            "alpha": ALPHA,
            "signal_alpha": SIGNAL_ALPHA,
            "contrast_count": CONTRAST_COUNT,
            "primary_contrast": PRIMARY_CONTRAST,
            "wrapper_delta_chars": WRAPPER_DELTA,
            "seed": SEED,
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
        REPO_ROOT / "src" / "analysis" / "tc001b_exploration.py",
        REPO_ROOT / "src" / "analysis" / "tc001b_reachability.py",
        REPO_ROOT / "src" / "analysis" / "tc001_exploration.py",
        REPO_ROOT / "src" / "analysis" / "tc001_study.py",
        REPO_ROOT / "src" / "analysis" / "locomo_nf_development.py",
        REPO_ROOT / "src" / "analysis" / "hh002_arms.py",
        REPO_ROOT / "episodic" / "src" / "episodic" / "_context.py",
        REPO_ROOT / "episodic" / "src" / "episodic" / "_packing.py",
        REPO_ROOT / "episodic" / "src" / "episodic" / "_render.py",
        REPO_ROOT / "episodic" / "src" / "episodic" / "_selection.py",
        PRE_REGISTRATION,
        AMENDMENT,
        PART1_ARTIFACT,
        PF4_ARTIFACT,
    ]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _distribution(values) -> dict[str, Any]:
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


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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
    import subprocess

    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def _git_tracked(path: Path) -> bool:
    try:
        relative = _repo_relative(path)
    except ValueError:
        # A gate written somewhere git cannot see is untracked, not an
        # error to report from the path arithmetic.
        return False
    return bool(_git("ls-files", "--error-unmatch", relative))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=PHASES, required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=STUDY_ROOT / "runs" / "tc001b",
    )
    arguments = parser.parse_args()
    result = run_phase(arguments.output_root, arguments.phase)
    json.dump(result, sys.stdout, indent=2, sort_keys=True, default=str)
    sys.stdout.write("\n")


__all__ = [
    "ALPHA",
    "ARMS",
    "CONTRASTS",
    "NULL_BAND",
    "PRIMARY_BUDGET",
    "PRIMARY_CONTRAST",
    "SCHEMA",
    "SECONDARY_BUDGET",
    "SIGNAL_ALPHA",
    "TC001BError",
    "all_contrasts",
    "assert_registration_agrees",
    "g0_reproduction",
    "main",
    "measure",
    "paired",
    "run_phase",
    "summarize",
    "verdict",
]

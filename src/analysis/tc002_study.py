"""TC-002: does EC-002's fill-order availability gain hold off its own corpus?

Every constant below is transcribed from
``experiments/components/tier_cost/TC_002_PRE_REGISTRATION.md``, which is the
authoritative home for all of them. ``assert_registration_agrees`` reads the
registered tokens back out of that document on every run, so a constant cannot
be edited here alone.

Two phases, in this order and enforced:

    g0    Re-run A_FLAT and A_N_FIRST and require exact agreement with TC-001's
          committed summary, and re-check that every EC-002 mechanism file is
          byte-identical to the commit EC-002's own run recorded. A failed G0
          stops the study.
    run   All five arms, four registered contrasts, one primary, plus section
          8.3's wrapper-matched pass.

``A_N_FIRST`` is TC-001's ``A_TIERED`` and ``A_K_FIRST`` is EC-002's
``build_k_first_context``; neither is reimplemented here. Zero model calls.
``ModelCallGuard`` is TC-001's, reused rather than restated.
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
from analysis.tc002_exploration import (
    EC002_RUN_COMMIT,
    EC002_SOURCES,
    pack_both,
)
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256
from episodic._packing import DROP_POLICY

SCHEMA = "tc002-fill-order-transfer-v1"

STUDY_ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
PRE_REGISTRATION = STUDY_ROOT / "TC_002_PRE_REGISTRATION.md"
PART1_ARTIFACT = (
    STUDY_ROOT / "artifacts" / "tc002" / "preflight" / "tc002_preflight_part1.json"
)
PF4_ARTIFACT = (
    STUDY_ROOT
    / "artifacts"
    / "tc002"
    / "preflight"
    / "tc002_preflight_pf4_reachability.json"
)
TC001_SUMMARY = STUDY_ROOT / "runs" / "tc001" / "run" / "summary.json"


# --------------------------------------------------------------------------
# Registered parameters - TC_002_PRE_REGISTRATION.md
# --------------------------------------------------------------------------

#: Section 2. EC-002's budget leads; the arc's other budget is secondary.
PRIMARY_BUDGET = 32_000
SECONDARY_BUDGET = 16_000

#: Section 2. EC-002's endpoint leads; TC-001's is secondary.
PRIMARY_ENDPOINT = "any"
SECONDARY_ENDPOINT = "complete"

#: Section 6.1, measured per budget from within-arm sham budget perturbations.
#: The band is a property of the endpoint at a budget, and this study is the
#: first in the arc to measure it at more than one.
NULL_BAND_BY_BUDGET = {32_000: 7, 16_000: 4}

#: Section 6.2. Bonferroni over the four registered contrasts.
ALPHA = 0.0025
SIGNAL_ALPHA = 0.025
CONTRAST_COUNT = 4

#: Section 3.3. An arm delivering any recency episode pays this much more
#: fixed wrapper than one that does not.
WRAPPER_DELTA = 18

SEED = 5005

ARMS = ("flat", "n_first", "k_first", "dual", "dual_ranked")

#: Section 6.3, instantiated. (id, X, Y, X-wins name, Y-wins name)
CONTRASTS = (
    ("C1", "k_first", "n_first", "K_FIRST_WINS", "N_FIRST_WINS"),
    ("C2", "k_first", "flat", "K_FIRST_WINS", "FLAT_WINS"),
    ("C3", "dual", "k_first", "DUAL_WINS", "K_FIRST_WINS"),
    ("C4", "dual_ranked", "k_first", "RANKED_WINS", "K_FIRST_WINS"),
)

#: Section 6.3. Unlike TC-001B, every contrast here is reachable in every
#: branch at both budgets (section 7.1), so none is registered DESCRIPTIVE.
NO_BAR: frozenset[str] = frozenset()

#: Section 6.4. The headline is registered so it cannot be chosen afterwards.
PRIMARY_CONTRAST = "C1"

#: Section 8.3. C1 is excluded: it is wrapper-symmetric already and the
#: adjustment would introduce the asymmetry it does not have.
WRAPPER_MATCHED_CONTRASTS = ("C2", "C3", "C4")

PHASES = ("g0", "run")


class TC002Error(RuntimeError):
    """Raised when a registered precondition does not hold."""


# --------------------------------------------------------------------------
# G0 - section 8.1
# --------------------------------------------------------------------------

#: TC-001's committed values, transcribed from section 8.1 rather than read
#: out of the artifact, so a corrupted artifact fails the gate instead of
#: redefining it. (flat, tiered, gains, losses, net)
ANCHOR = {
    ("16000", "complete"): (749, 314, 8, 443, -435),
    ("16000", "any"): (803, 381, 8, 430, -422),
    ("32000", "complete"): (810, 633, 7, 184, -177),
    ("32000", "any"): (842, 687, 9, 164, -155),
}


def ec002_provenance() -> dict[str, Any]:
    """Section 3.1: is the arm this study measures EC-002's arm?"""
    unchanged: dict[str, bool] = {}
    for relative in EC002_SOURCES:
        diff = subprocess.run(
            ["git", "diff", "--stat", EC002_RUN_COMMIT, "HEAD", "--", relative],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        unchanged[relative] = not diff
    return {
        "ec002_run_commit": EC002_RUN_COMMIT,
        "unchanged_since_ec002_run": unchanged,
        "status": "PASS" if all(unchanged.values()) else "FAIL",
        "claim": (
            "Every file on the K-first path is byte-identical to the revision "
            "that produced EC-002's committed 152-gain, zero-loss result."
        ),
    }


def g0_reproduction(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Re-run TC-001's two arms and require exact agreement, then check EC-002.

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
    for budget in (SECONDARY_BUDGET, PRIMARY_BUDGET):
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

    provenance = ec002_provenance()
    if provenance["status"] != "PASS":
        mismatches.append("EC-002 source provenance failed")

    return {
        "schema": SCHEMA,
        "gate": "G0",
        "status": "PASS" if not mismatches else "FAIL",
        "claim": (
            "A_FLAT and A_N_FIRST reproduce TC-001's committed primary and "
            "secondary tables exactly, and every EC-002 mechanism file is "
            "byte-identical to the revision that produced EC-002's result."
        ),
        "rows": rows,
        "ec002_provenance": provenance,
        "mismatches": mismatches,
        "tc001_summary_sha256": sha256_file(TC001_SUMMARY),
    }


def _anchor_pass(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    budget: int,
) -> dict[str, tuple[int, int, int, int, int]]:
    counts = {"complete": [0, 0, 0, 0], "any": [0, 0, 0, 0]}
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
        endpoint: (v[0], v[1], v[2], v[3], v[2] - v[3])
        for endpoint, v in counts.items()
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
    k_first_budget: int | None = None,
) -> list[dict[str, Any]]:
    """One row per unique question, all five arms, at one budget.

    ``k_first_budget`` exists only for section 8.3's wrapper-matched pass. It
    defaults to ``budget``, and when it does not, the row records it.
    """
    k_first_budget = budget if k_first_budget is None else k_first_budget
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
                    k_first_budget,
                )
            )
    return rows


def _row(
    episodes: Sequence[Episode],
    question: QuestionCase,
    query: np.ndarray,
    wanted: frozenset[str],
    budget: int,
    k_first_budget: int,
) -> dict[str, Any]:
    records = [episode.record for episode in episodes]

    # One clustering pass serves both fill orders; Preflight Part 1 proved
    # this equals build_context and build_k_first_context on 3,484
    # comparisons. The wrapper-matched pass needs a second state because the
    # two arms are then charged different budgets.
    shipped = pack_both(records, query, budget, SHIPPED_CONFIG)
    if k_first_budget == budget:
        k_block = shipped["k_first"]
    else:
        k_block = pack_both(records, query, k_first_budget, SHIPPED_CONFIG)[
            "k_first"
        ]

    flat_payload, flat_ids = flat_context(episodes, query, budget)
    _payload, dual_ids, dual_report = dual_context(episodes, query, budget)
    _payload, ranked_ids, ranked_counts = dual_ranked_context(
        episodes, query, budget
    )

    shipped_tiers = tier_membership(episodes, query, SHIPPED_CONFIG)
    dual_tiers = tier_membership(episodes, query, DUAL_CONFIG)
    recency_ids = set(shipped_tiers["recency_ids"])
    k_ids = set(shipped_tiers["k_ids"])
    dual_k_ids = set(dual_tiers["k_ids"])

    delivered = {
        "flat": set(flat_ids),
        "n_first": set(shipped["n_first"]["delivered"]),
        "k_first": set(k_block["delivered"]),
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
        "k_first_budget_chars": k_first_budget,
    }
    for arm in ARMS:
        hits = delivered[arm]
        row[f"{arm}_complete"] = wanted <= hits
        row[f"{arm}_any"] = bool(wanted & hits)
        row[f"{arm}_delivered"] = len(hits)
        row[f"{arm}_evidence_delivered"] = len(wanted & hits)

    row["flat_chars"] = len(flat_payload)
    row["n_first_chars"] = shipped["n_first"]["counts"]["chars_delivered"]
    row["k_first_chars"] = k_block["counts"]["chars_delivered"]
    row["dual_chars"] = dual_report.chars_delivered
    row["dual_ranked_chars"] = ranked_counts["chars_delivered"]

    for arm, counts in (
        ("n_first", shipped["n_first"]["counts"]),
        ("k_first", k_block["counts"]),
    ):
        row[f"{arm}_recency"] = counts["recency"]
        row[f"{arm}_k"] = counts["k"]
        row[f"{arm}_coverage"] = counts["coverage"]
    row["dual_recency"] = dual_report.stm_count
    row["dual_k"] = dual_report.k_count
    row["dual_coverage"] = dual_report.coverage_count
    row["dual_ranked_recency"] = ranked_counts["recency"]
    row["dual_ranked_k"] = ranked_counts["k"]
    row["dual_ranked_coverage"] = ranked_counts["coverage"]

    row["k_offered"] = shipped["offered"]["k"]
    row["pool_size"] = shipped["offered"]["pool_size"]
    row["fill_order_identical_payload"] = (
        shipped["n_first"]["payload"] == shipped["k_first"]["payload"]
    )

    for arm, recency, tier_k in (
        ("n_first", recency_ids, k_ids),
        ("k_first", recency_ids, k_ids),
        ("dual", set(), dual_k_ids),
        ("dual_ranked", set(), dual_k_ids),
    ):
        row[f"{arm}_evidence_tiers"] = _carrying_tiers(
            wanted & delivered[arm], recency, tier_k
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
    band: int,
) -> dict[str, Any]:
    """Section 6.3's disposition table, applied and nothing else.

    The table is exhaustive over the real line, so this function has no
    fallback branch by construction; if it ever needed one, the table would be
    the defect. ``band`` is required rather than defaulted, because TC-002's
    band depends on the budget and a default would silently pick one.
    """
    identifier, left, right, left_name, right_name = contrast
    net = statistic["net"]
    p_left = statistic["p_left_one_sided"]
    p_right = statistic["p_right_one_sided"]

    if identifier in NO_BAR:
        return {
            "contrast": identifier,
            "left": left,
            "right": right,
            "disposition": "DESCRIPTIVE",
            "verdict": "NO_BAR_REGISTERED",
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


def band_for(budget: int) -> int:
    """Section 6.1. A budget with no registered band is not a budget this
    study may report a disposition at."""
    if budget not in NULL_BAND_BY_BUDGET:
        raise TC002Error(
            f"No null band is registered for {budget} characters; "
            f"registered budgets are {sorted(NULL_BAND_BY_BUDGET)}"
        )
    return NULL_BAND_BY_BUDGET[budget]


def all_contrasts(
    rows: Sequence[dict[str, Any]], endpoint: str, *, band: int
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
    band = band_for(budget)
    complete_rows = [row for row in rows if row["complete_evaluable"]]
    return {
        "budget_chars": budget,
        "null_band": band,
        "population": {
            "questions": len(rows),
            "complete_evaluable": len(complete_rows),
        },
        "contrasts_any": all_contrasts(rows, "any", band=band),
        "contrasts_complete": all_contrasts(rows, "complete", band=band),
        "by_conversation": {
            sample_id: all_contrasts(
                [row for row in rows if row["sample_id"] == sample_id],
                "any",
                band=band,
            )
            for sample_id in sorted({row["sample_id"] for row in rows})
        },
        "by_category": {
            str(category): all_contrasts(
                [row for row in rows if row["category"] == category],
                "any",
                band=band,
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
        "fill_order_identical_payload": sum(
            1 for row in rows if row["fill_order_identical_payload"]
        ),
    }


def _composition(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for arm in ("n_first", "k_first", "dual", "dual_ranked"):
        tiers = {
            key: _distribution(row[f"{arm}_{key}"] for row in rows)
            for key in ("recency", "k", "coverage")
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

    A parameter has one authoritative home and it is the registration. This
    does not prove the document means what the code does - nothing mechanical
    can - but it does stop a constant being edited here alone.
    """
    text = PRE_REGISTRATION.read_text(encoding="utf-8")
    required = {
        "primary_budget": "Primary **32,000 characters**",
        "secondary_budget": "secondary **16,000**",
        "primary_endpoint": "Primary **any-evidence delivery**",
        "null_band": (
            "**B = 7 questions at 32,000. B = 4 questions at 16,000.**"
        ),
        "band_may_not_shrink": "**A band may not shrink.**",
        "alpha": '| α, "wins" tier | **0.0025** |',
        "signal_alpha": '| α, "carries signal" tier | **0.025** |',
        "wrapper_delta": "**18 characters**",
        "wrapper_matched_excludes_c1": "**C1 is excluded**",
        "primary_population": "The primary population is 871 questions",
        "primary_contrast": "**C1 is the headline, whatever it says.**",
        "contrast_count": "Four registered contrasts, so Bonferroni",
        "all_contrasts_carry_bars": "**All four contrasts carry bars.**",
        "divisor_may_not_shrink": "**The Bonferroni divisor stays at 4**",
        "does_not_ship": "**It is decided here: it does",
    }
    missing = sorted(name for name, token in required.items() if token not in text)
    if missing:
        raise TC002Error(
            f"Registered parameters not found in the pre-registration: {missing}"
        )
    if "PENDING-" in text:
        raise TC002Error(
            "The pre-registration still carries PENDING placeholders; it is "
            "not locked and no arm may be measured against it"
        )
    return {
        "status": "PASS",
        "pre_registration": _repo_relative(PRE_REGISTRATION),
        "pre_registration_sha256": sha256_file(PRE_REGISTRATION),
        "checked": sorted(required),
    }


def run_precondition(output_root: Path) -> dict[str, Any]:
    """PF3. The run phase may not open an arm before G0 is committed."""
    path = output_root / "g0" / "g0_reproduction.json"
    if not path.exists():
        raise TC002Error(f"G0 has not run: {path} is absent")
    if not _git_tracked(path):
        raise TC002Error(f"G0's artifact is not committed: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise TC002Error(f"G0 did not pass: {payload.get('status')}")
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
        raise TC002Error(f"Unregistered phase: {phase}")
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
            raise TC002Error(f"Read-only cache reported {reuse['misses']} misses")

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
                k_first_budget=PRIMARY_BUDGET - WRAPPER_DELTA,
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

    headline = primary[f"contrasts_{PRIMARY_ENDPOINT}"][PRIMARY_CONTRAST]
    result = {
        "schema": SCHEMA,
        "status": "COMPLETE",
        "standing": "REGISTERED-OFFLINE",
        "primary_contrast": PRIMARY_CONTRAST,
        "primary_endpoint": PRIMARY_ENDPOINT,
        "verdict": headline,
        "primary": primary,
        "secondary_budget": secondary,
        "robustness_wrapper_matched": {
            "k_first_budget_chars": PRIMARY_BUDGET - WRAPPER_DELTA,
            "other_arms_budget_chars": PRIMARY_BUDGET,
            "contrasts": {
                identifier: robustness[f"contrasts_{PRIMARY_ENDPOINT}"][identifier]
                for identifier in WRAPPER_MATCHED_CONTRASTS
            },
            "agrees_with_primary": {
                identifier: (
                    robustness[f"contrasts_{PRIMARY_ENDPOINT}"][identifier][
                        "disposition"
                    ]
                    == primary[f"contrasts_{PRIMARY_ENDPOINT}"][identifier][
                        "disposition"
                    ]
                )
                for identifier in WRAPPER_MATCHED_CONTRASTS
            },
            "c1_excluded": (
                "C1 is wrapper-symmetric already; charging one of its arms a "
                "different budget would introduce the asymmetry it does not have"
            ),
            "k_first_chars_delivered": robustness["delivery"]["k_first"]["chars"],
        },
        "cache": {"hits": reuse["hits"], "misses": reuse["misses"]},
    }

    output_dir = output_root / "run"
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "summary.json", result)
    _write_json(
        output_dir / "verdict.json", primary[f"contrasts_{PRIMARY_ENDPOINT}"]
    )
    _write_json(output_dir / "no_model_call_audit.json", audit)
    _write_json(output_dir / "run_precondition.json", precondition)
    _write_csv(output_dir / "per_question_primary.csv", primary_rows)
    _write_csv(output_dir / "per_question_secondary.csv", secondary_rows)
    for identifier, left, right, _lname, _rname in CONTRASTS:
        _write_csv(
            output_dir / f"discordant_{identifier.lower()}_{left}_vs_{right}.csv",
            discordant_rows(primary_rows, left, right, PRIMARY_ENDPOINT),
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
        "study": "TC-002",
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
        "ec002_provenance": ec002_provenance(),
        "parameters": {
            "primary_budget_chars": PRIMARY_BUDGET,
            "secondary_budget_chars": SECONDARY_BUDGET,
            "primary_endpoint": PRIMARY_ENDPOINT,
            "null_band_by_budget": {
                str(key): value for key, value in NULL_BAND_BY_BUDGET.items()
            },
            "alpha": ALPHA,
            "signal_alpha": SIGNAL_ALPHA,
            "contrast_count": CONTRAST_COUNT,
            "primary_contrast": PRIMARY_CONTRAST,
            "wrapper_delta_chars": WRAPPER_DELTA,
            "wrapper_matched_contrasts": list(WRAPPER_MATCHED_CONTRASTS),
            "arms": list(ARMS),
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
        REPO_ROOT / "src" / "analysis" / "tc002_exploration.py",
        REPO_ROOT / "src" / "analysis" / "tc002_reachability.py",
        REPO_ROOT / "src" / "analysis" / "tc_standing_arms.py",
        REPO_ROOT / "src" / "analysis" / "tc001_exploration.py",
        REPO_ROOT / "src" / "analysis" / "tc001_study.py",
        REPO_ROOT / "src" / "analysis" / "tc001b_exploration.py",
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
        "--output-root", type=Path, default=STUDY_ROOT / "runs" / "tc002"
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
    "NULL_BAND_BY_BUDGET",
    "PRIMARY_BUDGET",
    "PRIMARY_CONTRAST",
    "PRIMARY_ENDPOINT",
    "SCHEMA",
    "SECONDARY_BUDGET",
    "SIGNAL_ALPHA",
    "TC002Error",
    "all_contrasts",
    "assert_registration_agrees",
    "band_for",
    "ec002_provenance",
    "g0_reproduction",
    "main",
    "measure",
    "paired",
    "run_phase",
    "summarize",
    "verdict",
]

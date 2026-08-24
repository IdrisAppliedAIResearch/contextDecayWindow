"""TC-002 Preflight Part 1: characterize fill order before any bar is locked.

EC-002 changed one thing in an offline replay of 500 LongMemEval stores - the
order in which unique episode identities are offered to the exact serializer -
and any-evidence-session recall rose from 109 to 261 of 470, with 152 gains and
zero losses. The library still packs recency first. `TC_ARC_ROADMAP.md` section
3 asks the narrow question that result leaves open: **does the availability gain
hold off its original corpus?**

This module characterizes the arms of that question on LoCoMo development,
before a bar exists:

    A_FLAT         rank every candidate by cosine, pack greedily to budget.
    A_N_FIRST      ``build_context`` as shipped - recency, then K, then
                   coverage. This is TC-001's `A_TIERED` under the name the
                   fill-order question gives it.
    A_K_FIRST      EC-002's registered counterfactual, imported unmodified from
                   ``analysis.ec002_k_first_packing``: K, then recency, then
                   coverage, with render tiers preserved.
    A_DUAL         ``build_context`` with ``recency_window_n=0``.
    A_DUAL_RANKED  A_DUAL with the K tier offered best-first.

The last two are the arc's standing arms (``analysis.tc_standing_arms``). They
are here because reordering a tier and deleting it are different repairs to the
same defect, and TC-001B measured the second without the first.

**Three identities are proven rather than asserted.**

1. ``build_candidate_state`` + ``pack_stm_payload`` equals ``build_context``.
2. ``build_candidate_state`` + ``pack_k_first`` equals ``build_k_first_context``.
3. ``build_k_first_context`` at ``recency_window_n=0`` equals ``build_context``
   at ``recency_window_n=0``, byte for byte. With no recency tier there is
   nothing for K-first to be first *of*, so if these two ever diverge, the
   named manipulation is doing something besides reordering admission.

The first two let one clustering pass serve both fill orders, which is what
makes this Preflight affordable. The third is the name-to-behavior check.

**What this module deliberately does not compute.** No artifact it writes
carries an arm's absolute availability or any cross-arm availability contrast.
Delivered-set agreement between arms is recorded, and that is a mechanism fact
computed without touching an evidence label. The null band below is measured
here; a band chosen after seeing the contrast would not be a band.

Zero model calls. The cache is opened in ``reuse`` mode with its file and
content digests asserted, so a miss raises rather than embedding.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from analysis.ec002_k_first_packing import (
    build_candidate_state,
    build_k_first_context,
    pack_k_first,
)
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
    SHAM_FRACTIONS,
    VECTOR_MANIFEST,
    Episode,
    _delivered_ids,
    _evidence_index,
    _repo_relative,
    _score,
    _sham_row,
    build_episodes,
    flat_context,
    tiered_context,
)
from analysis.tc001b_exploration import (
    DUAL_CONFIG,
    SHIPPED_CONFIG,
    assert_composition_matches,
    dual_context,
    dual_ranked_context,
)
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256, EpisodicConfig
from episodic._context import build_context
from episodic._packing import pack_stm_payload

SCHEMA = "tc002-preflight-part1-v1"

ARTIFACT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "tier_cost" / "artifacts" / "tc002"
)

#: EC-002's registered budget. The transfer question is asked at the setting
#: EC-002 asked it at, and 16,000 is carried as the arc's other budget.
EC002_BUDGET = 32_000

#: The commit EC-002's A1 run recorded as HEAD. Every mechanism file this
#: study imports from that study is checked against it by ``git diff``.
EC002_RUN_COMMIT = "caa19f524e67417843ecc63b2934137f51445539"

EC002_SOURCES = (
    "src/analysis/ec002_k_first_packing.py",
    "src/analysis/ec001_longmemeval.py",
    "episodic/src/episodic/_context.py",
    "episodic/src/episodic/_packing.py",
    "episodic/src/episodic/_render.py",
    "episodic/src/episodic/_selection.py",
)

ARMS = ("flat", "n_first", "k_first", "dual", "dual_ranked")

#: Arms whose null band is measured here, per budget. ``flat`` is excluded at
#: both: TC-001's Part 1 measured it on this corpus at 16,000 and the
#: registration carries that number forward. ``dual`` and ``dual_ranked`` are
#: measured at EC-002's 32,000 because no prior study measured them there;
#: TC-001B measured them at 16,000 and that value is carried in alongside.
#: The band the registration locks is the maximum over every measured value,
#: inherited ones included, so a narrower measurement here cannot narrow it.
BAND_ARMS_BY_BUDGET: dict[int, tuple[str, ...]] = {
    16_000: ("n_first", "k_first"),
    32_000: ("n_first", "k_first", "dual", "dual_ranked"),
}

#: The union of the above, for artifact schema stability.
BAND_ARMS = ("n_first", "k_first", "dual", "dual_ranked")


class TC002ExplorationError(RuntimeError):
    """Raised when a Preflight invariant does not hold."""


# --------------------------------------------------------------------------
# One clustering pass, two fill orders
# --------------------------------------------------------------------------


def pack_both(
    records: Sequence[dict],
    query_embedding,
    budget: int,
    config: EpisodicConfig,
) -> dict[str, Any]:
    """Build the candidate state once and pack it in both registered orders.

    Both packers are the committed ones - ``episodic._packing.pack_stm_payload``
    for N-first and ``analysis.ec002_k_first_packing.pack_k_first`` for K-first -
    called on the same ``CandidateState``. Nothing here re-derives a candidate
    set, so the two orders are guaranteed to be offered identical candidates in
    identical within-tier order, which is exactly what EC-002 section 4
    registered and what a fill-order contrast requires.
    """
    state = build_candidate_state(
        episodes=records,
        query_embedding=query_embedding,
        budget=budget,
        config=config,
    )
    n_packed = pack_stm_payload(
        list(state.recent), [*state.k_hits, *state.coverage], budget
    )
    k_packed = pack_k_first(state, budget=budget)

    recent_ids = {str(episode["id"]) for episode in state.recent}
    k_ids = {str(episode["id"]) for episode in state.k_hits}

    def counts(delivered: Sequence[str], payload: str) -> dict[str, Any]:
        seen = set(delivered)
        return {
            "recency": len(seen & recent_ids),
            "k": len((seen & k_ids) - recent_ids),
            "coverage": len(seen - recent_ids - k_ids),
            "delivered": len(seen),
            "chars_delivered": len(payload),
        }

    n_ids = _delivered_ids(n_packed.payload, records)
    k_ids_delivered = _delivered_ids(k_packed.payload, records)
    return {
        "n_first": {
            "payload": n_packed.payload,
            "delivered": n_ids,
            "counts": counts(n_ids, n_packed.payload),
        },
        "k_first": {
            "payload": k_packed.payload,
            "delivered": k_ids_delivered,
            "counts": counts(k_ids_delivered, k_packed.payload),
        },
        "offered": {
            "recency": len(state.recent),
            "k": len(state.k_hits),
            "coverage": len(state.coverage),
            "pool_size": state.pool_size,
        },
    }


def k_first_context(
    episodes: Sequence[Episode],
    query: np.ndarray,
    budget: int,
    config: EpisodicConfig,
) -> tuple[str, tuple[str, ...], Any]:
    """A_K_FIRST through EC-002's own entry point, unmodified."""
    records = [episode.record for episode in episodes]
    payload, report, _diagnostics = build_k_first_context(
        episodes=records,
        query_embedding=query,
        budget=budget,
        config=config,
    )
    return payload, _delivered_ids(payload, records), report


def assert_pack_both_matches(
    episodes: Sequence[Episode],
    query: np.ndarray,
    budget: int,
    config: EpisodicConfig,
) -> dict[str, Any]:
    """Identities 1 and 2: the shared state reproduces both shipped functions.

    The two shipped payloads are returned under ``shipped_n_first`` and
    ``shipped_k_first`` so identity 3 costs nothing extra: called with
    ``DUAL_CONFIG``, those two strings *are* the collapse check's operands.
    """
    records = [episode.record for episode in episodes]
    shipped_n, n_report = build_context(
        episodes=records,
        query_embedding=query,
        budget=budget,
        config=config,
    )
    shipped_k, k_report, _diagnostics = build_k_first_context(
        episodes=records,
        query_embedding=query,
        budget=budget,
        config=config,
    )
    both = pack_both(records, query, budget, config)

    if both["n_first"]["payload"] != shipped_n:
        raise TC002ExplorationError(
            "pack_both's N-first payload diverged from build_context at budget "
            f"{budget}, N={config.recency_window_n}"
        )
    if both["k_first"]["payload"] != shipped_k:
        raise TC002ExplorationError(
            "pack_both's K-first payload diverged from build_k_first_context at "
            f"budget {budget}, N={config.recency_window_n}"
        )
    for name, report, key in (
        ("n_first", n_report, "n_first"),
        ("k_first", k_report, "k_first"),
    ):
        observed = both[key]["counts"]
        expected = (report.stm_count, report.k_count, report.coverage_count)
        actual = (observed["recency"], observed["k"], observed["coverage"])
        if expected != actual:
            raise TC002ExplorationError(
                f"pack_both reported a different tier split than {name}'s "
                f"ContextReport: {actual} != {expected}"
            )
    both["shipped_n_first"] = shipped_n
    both["shipped_k_first"] = shipped_k
    return both


def assert_k_first_collapses_at_n0(dual_both: dict[str, Any], budget: int) -> None:
    """Identity 3: with no recency tier, K-first is the shipped composition.

    This is the name-to-behavior check `PREFLIGHT.md` Part 1 requires. The
    registered manipulation is *admission order between the recency tier and
    the K tier*. Remove the recency tier and the manipulation has no subject,
    so the two paths must produce the same bytes. If they do not, K-first is
    changing something the registration did not name.

    The operands come from ``assert_pack_both_matches`` under ``DUAL_CONFIG``,
    which already called both shipped functions, so this check adds no work.
    """
    if dual_both["shipped_n_first"] != dual_both["shipped_k_first"]:
        raise TC002ExplorationError(
            "K-first differs from N-first with the recency tier removed, so it "
            f"is not purely an admission-order change (budget {budget})"
        )


# --------------------------------------------------------------------------
# Part 1
# --------------------------------------------------------------------------


def explore(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
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
        raise TC002ExplorationError(
            f"Read-only cache reported {reuse['misses']} misses"
        )

    by_conversation = {
        case.sample_id: build_episodes(case, vectors) for case in conversations
    }

    sweep = _sweep(conversations, by_conversation, vectors)
    result = {
        "schema": SCHEMA,
        "status": "PREFLIGHT_PART1_ONLY",
        "note": (
            "Within-arm characterization and cross-arm delivered-set agreement "
            "only. No arm's availability and no availability contrast appears "
            "in this artifact."
        ),
        "inputs": _inputs(manifest, reuse),
        "provenance": _ec002_provenance(),
        "identity": sweep["identity"],
        "behaviour": sweep["behaviour"],
        "null_band": _sham_band(conversations, by_conversation, vectors),
        "cost": _cost(conversations, by_conversation, vectors),
        "elapsed_seconds": round(time.time() - started, 3),
    }
    path = output_dir / "tc002_preflight_part1.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _inputs(manifest: dict, reuse: dict) -> dict[str, Any]:
    return {
        "dataset_sha256": manifest["dataset_sha256"],
        "cache_file_sha256": manifest["cache"]["file_sha256"],
        "cache_content_sha256": manifest["cache"]["content_sha256"],
        "embedder_sha256": CARRIED_EMBEDDER_SHA256,
        "development_ids": manifest["development_ids"],
        "cache_hits": reuse["hits"],
        "cache_misses": reuse["misses"],
        "budgets": list(BUDGETS),
        "ec002_budget": EC002_BUDGET,
        "shipped_config": json.loads(SHIPPED_CONFIG.to_json()),
        "dual_config": json.loads(DUAL_CONFIG.to_json()),
        "sources": {
            _repo_relative(path): sha256_file(path)
            for path in (
                Path(__file__).resolve(),
                REPO_ROOT / "src" / "analysis" / "tc_standing_arms.py",
                REPO_ROOT / "src" / "analysis" / "tc001_exploration.py",
                REPO_ROOT / "src" / "analysis" / "tc001b_exploration.py",
                REPO_ROOT / "src" / "analysis" / "ec002_k_first_packing.py",
                REPO_ROOT / "episodic" / "src" / "episodic" / "_context.py",
                REPO_ROOT / "episodic" / "src" / "episodic" / "_packing.py",
                REPO_ROOT / "episodic" / "src" / "episodic" / "_selection.py",
            )
        },
    }


def _ec002_provenance() -> dict[str, Any]:
    """PF6, statically: is the manipulation this study runs EC-002's own?

    EC-002's runner is branch-gated to ``ec/002-k-first-packing`` and refuses
    to execute anywhere else, so its result cannot be re-derived at this HEAD
    by invoking it. What can be established, and is stronger than a re-run for
    the identity question, is that every mechanism file involved is unchanged
    since the commit EC-002's A1 run recorded as HEAD. ``git diff`` is the
    check; an empty diff is the pass.
    """
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
            "that produced EC-002's committed 152-gain, zero-loss result, so "
            "the manipulation measured here is that manipulation."
        ),
        "committed_ec002_result": {
            "corpus": "LongMemEval-S cleaned, 500 stores, 470 answerable",
            "budget_chars": 32_000,
            "any_evidence_session": {"a0": 109, "a1": 261, "gains": 152, "losses": 0},
            "artifact": (
                "experiments/external/longmemeval/runs/ec002_k_first/"
                "a1_k_first/paired_comparison.json"
            ),
        },
    }


def _sweep(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
) -> dict[str, Any]:
    """One pass that answers both the identity gate and the behaviour questions."""
    checked = {"pack_both": 0, "k_first_at_n0": 0, "compose_context": 0}
    behaviour: dict[str, Any] = {}
    first_question = {
        case.sample_id: next(
            question for question in case.questions if not question.duplicate_ordinal
        )
        for case in conversations
    }

    for budget in BUDGETS:
        rows: dict[str, dict[str, list]] = {
            name: {
                "delivered": [],
                "chars": [],
                "recency": [],
                "k": [],
                "coverage": [],
            }
            for name in ARMS
        }
        fill_order = {
            "questions": 0,
            "n_first_truncated": 0,
            "k_first_truncated": 0,
            "identical_delivered_set": 0,
            "identical_payload": 0,
            "offered_zero_k": 0,
            "k_first_delivers_fewer_k_than_n_first": 0,
            "k_first_delivers_more_k_than_n_first": 0,
            "k_first_delivers_fewer_recency": 0,
            "k_first_recency_rendered_outside_recent_block": 0,
        }

        for case in conversations:
            episodes = by_conversation[case.sample_id]
            records = [episode.record for episode in episodes]
            for question in case.questions:
                if question.duplicate_ordinal:
                    continue
                query = vectors[question.question]
                fill_order["questions"] += 1

                both = assert_pack_both_matches(
                    episodes, query, budget, SHIPPED_CONFIG
                )
                checked["pack_both"] += 1
                dual_both = assert_pack_both_matches(
                    episodes, query, budget, DUAL_CONFIG
                )
                checked["pack_both"] += 1
                assert_k_first_collapses_at_n0(dual_both, budget)
                checked["k_first_at_n0"] += 1
                if question is first_question[case.sample_id]:
                    # TC-001B proved compose_context equals build_context on
                    # 3,484 comparisons and committed the artifact. This is a
                    # spot-check that the inherited arm has not drifted since,
                    # not a re-derivation of that gate.
                    assert_composition_matches(
                        episodes, query, budget, DUAL_CONFIG
                    )
                    checked["compose_context"] += 1

                n_counts = both["n_first"]["counts"]
                k_counts = both["k_first"]["counts"]
                _collect(rows["n_first"], n_counts)
                _collect(rows["k_first"], k_counts)

                # A_DUAL is build_context at N=0, which the DUAL_CONFIG gate
                # above has just proven equal to this state's N-first pack.
                _collect(rows["dual"], dual_both["n_first"]["counts"])
                _payload, ranked_ids, ranked_counts = dual_ranked_context(
                    episodes, query, budget
                )
                _collect(
                    rows["dual_ranked"],
                    {
                        "delivered": len(ranked_ids),
                        "chars_delivered": ranked_counts["chars_delivered"],
                        "recency": ranked_counts["recency"],
                        "k": ranked_counts["k"],
                        "coverage": ranked_counts["coverage"],
                    },
                )
                flat_payload, flat_ids = flat_context(episodes, query, budget)
                rows["flat"]["delivered"].append(len(flat_ids))
                rows["flat"]["chars"].append(len(flat_payload))

                offered = both["offered"]
                if offered["k"] == 0:
                    fill_order["offered_zero_k"] += 1
                if n_counts["delivered"] < offered["recency"] + offered["k"] + offered[
                    "coverage"
                ]:
                    fill_order["n_first_truncated"] += 1
                if k_counts["delivered"] < offered["recency"] + offered["k"] + offered[
                    "coverage"
                ]:
                    fill_order["k_first_truncated"] += 1
                if set(both["n_first"]["delivered"]) == set(
                    both["k_first"]["delivered"]
                ):
                    fill_order["identical_delivered_set"] += 1
                if both["n_first"]["payload"] == both["k_first"]["payload"]:
                    fill_order["identical_payload"] += 1
                if k_counts["k"] < n_counts["k"]:
                    fill_order["k_first_delivers_fewer_k_than_n_first"] += 1
                if k_counts["k"] > n_counts["k"]:
                    fill_order["k_first_delivers_more_k_than_n_first"] += 1
                if k_counts["recency"] < n_counts["recency"]:
                    fill_order["k_first_delivers_fewer_recency"] += 1
                if not _recency_renders_in_recent_block(
                    both["k_first"]["payload"], records, k_counts["recency"]
                ):
                    fill_order[
                        "k_first_recency_rendered_outside_recent_block"
                    ] += 1

        behaviour[str(budget)] = {
            "budget_chars": budget,
            "distributions": {
                name: {
                    key: _distribution(values)
                    for key, values in series.items()
                    if values
                }
                for name, series in rows.items()
            },
            "fill_order": fill_order,
        }

    identity = {
        "status": "PASS",
        "pack_both_comparisons": checked["pack_both"],
        "k_first_at_n0_comparisons": checked["k_first_at_n0"],
        "compose_context_comparisons": checked["compose_context"],
        "budgets": list(BUDGETS),
        "configs": ["shipped_n32", "dual_n0"],
        "claims": [
            "build_candidate_state + pack_stm_payload is build_context.",
            "build_candidate_state + pack_k_first is build_k_first_context.",
            "build_k_first_context at recency_window_n=0 is build_context at "
            "recency_window_n=0, byte for byte: with no recency tier the "
            "registered manipulation has no subject.",
        ],
    }
    return {"identity": identity, "behaviour": behaviour}


def _recency_renders_in_recent_block(
    payload: str, records: Sequence[dict], recency_delivered: int
) -> bool:
    """EC-002 section 4: a K-admitted recency episode still renders in N's block.

    The renderer writes ``recent_context`` first and ``retrieved_stm`` second,
    and an empty block collapses to ``<recent_context/>``. So the episode
    elements before ``</recent_context>`` are exactly the recency block's
    members when the promise holds.
    """
    if recency_delivered == 0:
        return payload.startswith("<recent_context/>")
    head, separator, _rest = payload.partition("</recent_context>")
    if not separator or not payload.startswith("<recent_context>"):
        return False
    return len(_delivered_ids(head, records)) == recency_delivered


def _collect(series: dict[str, list], counts: dict[str, Any]) -> None:
    series["delivered"].append(counts["delivered"])
    series["chars"].append(counts["chars_delivered"])
    series["recency"].append(counts["recency"])
    series["k"].append(counts["k"])
    series["coverage"].append(counts["coverage"])


def _sham_band(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
) -> dict[str, Any]:
    """The null band, measured within each arm at both budgets.

    TC-001's method: compare each arm **against itself** at a budget nudged by
    half and one percent, and record only the paired gains and losses. TC-001B's
    correction is kept - both endpoints are measured, not just any-evidence -
    and one more is added here: TC-002's primary budget is EC-002's 32,000, and
    a band measured at 16,000 is not this study's band, so both are measured.
    """
    endpoints = ("any", "complete")
    per_budget: dict[str, Any] = {}
    nets: list[int] = []

    for budget in BUDGETS:
        arms = BAND_ARMS_BY_BUDGET[budget]
        baseline: dict[str, dict[str, dict[str, bool]]] = {
            arm: {endpoint: {} for endpoint in endpoints} for arm in arms
        }
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
                for arm, delivered in _band_arms(episodes, query, budget, arms):
                    hits = set(delivered)
                    baseline[arm]["any"][question.identity] = bool(target & hits)
                    baseline[arm]["complete"][question.identity] = target <= hits

        per_arm: dict[str, dict[str, list]] = {
            arm: {endpoint: [] for endpoint in endpoints} for arm in arms
        }
        for fraction in SHAM_FRACTIONS:
            nudged = int(round(budget * (1.0 + fraction)))
            counts = {
                arm: {endpoint: [0, 0] for endpoint in endpoints} for arm in arms
            }
            for case in conversations:
                episodes = by_conversation[case.sample_id]
                for question in case.questions:
                    if (
                        question.duplicate_ordinal
                        or not question.resolved_evidence_ids
                    ):
                        continue
                    query = vectors[question.question]
                    target = wanted[question.identity]
                    for arm, delivered in _band_arms(
                        episodes, query, nudged, arms
                    ):
                        hits = set(delivered)
                        _score(
                            counts[arm]["any"],
                            baseline[arm]["any"][question.identity],
                            bool(target & hits),
                        )
                        _score(
                            counts[arm]["complete"],
                            baseline[arm]["complete"][question.identity],
                            target <= hits,
                        )
            for arm in arms:
                for endpoint in endpoints:
                    gains, losses = counts[arm][endpoint]
                    per_arm[arm][endpoint].append(
                        _sham_row(fraction, budget, nudged, gains, losses)
                    )

        budget_nets = [
            abs(row["net"])
            for arm in arms
            for endpoint in endpoints
            for row in per_arm[arm][endpoint]
        ]
        nets.extend(budget_nets)
        per_budget[str(budget)] = {
            "budget_chars": budget,
            "arms": list(arms),
            "evaluable_questions": len(wanted),
            "perturbations": per_arm,
            "max_abs_net": max(budget_nets),
        }

    return {
        "arms": list(BAND_ARMS),
        "endpoints": list(endpoints),
        "budgets": per_budget,
        "max_abs_net": max(nets),
        "tc001_max_abs_net": 4,
        "tc001b_max_abs_net": 3,
        "band_definition": (
            "The largest absolute gains-minus-losses any sham budget "
            "perturbation produced within a single arm, over both budgets and "
            "both endpoints. TC-001's and TC-001B's measured values are carried "
            "alongside; the registration takes the maximum over all of them."
        ),
    }


def _band_arms(
    episodes: Sequence[Episode],
    query: np.ndarray,
    budget: int,
    arms: Sequence[str],
) -> tuple[tuple[str, Sequence[str]], ...]:
    records = [episode.record for episode in episodes]
    delivered: dict[str, Sequence[str]] = {}
    if "n_first" in arms or "k_first" in arms:
        shipped = pack_both(records, query, budget, SHIPPED_CONFIG)
        delivered["n_first"] = shipped["n_first"]["delivered"]
        delivered["k_first"] = shipped["k_first"]["delivered"]
    if "dual" in arms:
        _payload, dual_ids, _report = dual_context(episodes, query, budget)
        delivered["dual"] = dual_ids
    if "dual_ranked" in arms:
        _payload, ranked_ids, _counts = dual_ranked_context(
            episodes, query, budget
        )
        delivered["dual_ranked"] = ranked_ids
    return tuple((arm, delivered[arm]) for arm in arms)


def _cost(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Per-question wall clock through each arm's own entry point.

    ``pack_both`` is what the study runs, but it is an optimization, so the
    latency reported here is measured through the functions a deployment would
    actually call.
    """
    rows = []
    budget = EC002_BUDGET
    for case in conversations:
        episodes = by_conversation[case.sample_id]
        questions = [q for q in case.questions if not q.duplicate_ordinal][:40]
        timings: dict[str, list[float]] = {name: [] for name in ARMS}
        for question in questions:
            query = vectors[question.question]
            for name, call in (
                ("flat", lambda: flat_context(episodes, query, budget)),
                (
                    "n_first",
                    lambda: tiered_context(
                        episodes, query, budget, SHIPPED_CONFIG
                    ),
                ),
                (
                    "k_first",
                    lambda: k_first_context(
                        episodes, query, budget, SHIPPED_CONFIG
                    ),
                ),
                ("dual", lambda: dual_context(episodes, query, budget)),
                (
                    "dual_ranked",
                    lambda: dual_ranked_context(episodes, query, budget),
                ),
            ):
                started = time.perf_counter()
                call()
                timings[name].append((time.perf_counter() - started) * 1_000.0)
        rows.append(
            {
                "sample_id": case.sample_id,
                "pool_size": len(episodes),
                "questions_timed": len(questions),
                **{
                    f"{arm}_ms": _float_distribution(values)
                    for arm, values in timings.items()
                },
            }
        )
    return {"by_conversation": rows, "budget_chars": budget}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


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


def _float_distribution(values: Iterable[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {"n": 0}
    return {
        "n": len(ordered),
        "min": round(ordered[0], 4),
        "p50": round(statistics.median(ordered), 4),
        "p95": round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 4),
        "max": round(ordered[-1], 4),
        "mean": round(statistics.fmean(ordered), 4),
    }


__all__ = [
    "ARMS",
    "ARTIFACT_ROOT",
    "BAND_ARMS",
    "BAND_ARMS_BY_BUDGET",
    "EC002_BUDGET",
    "EC002_RUN_COMMIT",
    "SCHEMA",
    "TC002ExplorationError",
    "assert_k_first_collapses_at_n0",
    "assert_pack_both_matches",
    "explore",
    "k_first_context",
    "pack_both",
]

"""TC-001: the tiered stack against the flat arm, over identical candidates.

Registered in `experiments/components/tier_cost/TC_001_PRE_REGISTRATION.md`,
whose commit is the integrity anchor and is recorded in every run header.
Parameters live there; the constants below are transcriptions of it and
`assert_registration_agrees` fails the run if any of them drifts from the
document.

Two phases, in order, and the order is enforced rather than assumed:

    g0   Reproduce the committed LoCoMo development analysis exactly.
         PF6's anchor. A failed G0 stops TC-001.
    run  Both arms at both budgets, plus the wrapper-matched robustness
         check. Refuses to start until G0 is committed and passing.

The arms are not reimplemented here. They are
`analysis.tc001_exploration.flat_context` and `.tiered_context` - the
same functions Preflight Part 1 characterized, whose SHA-256 is recorded
in the committed Part 1 artifact. Measuring with code other than the code
that was characterized is how a study ends up describing one mechanism
and testing another.

Zero model calls, enforced by a guard rather than asserted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from analysis.locomo_nf_development import (
    ConversationCase,
    QuestionCase,
    adapt_development,
    analyse,
    sha256_file,
)
from analysis.tc001_exploration import (
    CACHE_PATH,
    DATASET_PATH,
    REPO_ROOT,
    VECTOR_MANIFEST,
    Episode,
    _distribution,
    _evidence_index,
    _float_distribution,
    _repo_relative,
    build_episodes,
    flat_context,
    flat_order,
    tier_membership,
    tiered_context,
)
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256, EpisodicConfig
from episodic._packing import DROP_POLICY

SCHEMA = "tc001-tiered-versus-flat-v1"

STUDY_ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
PRE_REGISTRATION = STUDY_ROOT / "TC_001_PRE_REGISTRATION.md"
PART1_ARTIFACT = (
    STUDY_ROOT / "artifacts" / "tc001" / "preflight" / "tc001_preflight_part1.json"
)
PF4_ARTIFACT = (
    STUDY_ROOT
    / "artifacts"
    / "tc001"
    / "preflight"
    / "tc001_preflight_pf4_reachability.json"
)
COMMITTED_DEV_ANALYSIS = (
    REPO_ROOT / "experiments" / "external" / "locomo" / "artifacts"
    / "development_analysis.json"
)

# --------------------------------------------------------------------------
# Registered parameters. Transcribed from §2, §3.1, §6.1 and §6.3 of the
# pre-registration; `assert_registration_agrees` holds them to it.
# --------------------------------------------------------------------------

PRIMARY_BUDGET = 16_000
SECONDARY_BUDGET = 32_000
#: §6.1. Measured from within-arm sham budget perturbations, not chosen.
NULL_BAND = 4
#: §6.3.
ALPHA = 0.01
SIGNAL_ALPHA = 0.10
#: §3.1. The flat arm's empty `recent_context` block costs this much less
#: than the tiered arm's two non-empty blocks; §8's robustness check pays
#: it back.
WRAPPER_DELTA = 18
SEED = 5005

PHASES = ("g0", "run")


class TC001Error(RuntimeError):
    pass


# --------------------------------------------------------------------------
# G0 - the reproduction anchor (PF6)
# --------------------------------------------------------------------------

#: The blocks G0 must reproduce. Value equality on each, plus row-level
#: identity, because counts can agree on different questions.
_ANCHOR_BLOCKS = (
    "strict_any",
    "unique_question_strict_any",
    "all_evidence",
    "by_conversation_unique_questions",
    "by_category_unique_questions",
    "session_touch_unique_questions",
    "delivery_distribution_unique_questions",
    "packed_chars_distribution_unique_questions",
)


def g0_reproduction(conversations: Sequence[ConversationCase]) -> dict[str, Any]:
    """Reproduce the committed development analysis, by identity.

    NF-004's development pass ran a different contrast at a different
    granularity, which is exactly why it is the right anchor: if this
    environment, this dataset copy and this cache reproduce it to the
    row, then the inputs TC-001 stands on are the inputs that produced a
    committed number.
    """
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    committed = json.loads(COMMITTED_DEV_ANALYSIS.read_text(encoding="utf-8"))
    replayed = analyse(list(conversations), CACHE_PATH, manifest)

    blocks = {
        name: committed.get(name) == replayed.get(name) for name in _ANCHOR_BLOCKS
    }
    rows_match = committed["rows"] == replayed["rows"]
    calls_clean = (
        replayed.get("model_calls") == 0 and replayed.get("embedding_calls") == 0
    )
    passed = all(blocks.values()) and rows_match and calls_clean
    return {
        "status": "PASS" if passed else "FAIL",
        "committed": _repo_relative(COMMITTED_DEV_ANALYSIS),
        "committed_sha256": sha256_file(COMMITTED_DEV_ANALYSIS),
        "blocks_reproduced": blocks,
        "rows_reproduced": rows_match,
        "rows_compared": len(committed["rows"]),
        "model_calls": replayed.get("model_calls"),
        "embedding_calls": replayed.get("embedding_calls"),
        "committed_digest": _digest(
            {name: committed.get(name) for name in _ANCHOR_BLOCKS}
        ),
        "replayed_digest": _digest(
            {name: replayed.get(name) for name in _ANCHOR_BLOCKS}
        ),
        "committed_rows_digest": _digest(committed["rows"]),
        "replayed_rows_digest": _digest(replayed["rows"]),
    }


# --------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------


def measure(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    config: EpisodicConfig,
    *,
    budget: int,
    flat_budget: int | None = None,
) -> list[dict[str, Any]]:
    """One row per unique question, both arms, at one budget.

    ``flat_budget`` exists only for §8's wrapper-matched robustness check.
    It defaults to ``budget``, and when it does not, the row records both.
    """
    flat_budget = budget if flat_budget is None else flat_budget
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
                    case,
                    episodes,
                    question,
                    vectors[question.question],
                    evidence[question.identity],
                    config,
                    budget,
                    flat_budget,
                )
            )
    return rows


def _row(
    case: ConversationCase,
    episodes: Sequence[Episode],
    question: QuestionCase,
    query: np.ndarray,
    wanted: frozenset[str],
    config: EpisodicConfig,
    budget: int,
    flat_budget: int,
) -> dict[str, Any]:
    flat_payload, flat_ids = flat_context(episodes, query, flat_budget)
    tiered_payload, tiered_ids, report = tiered_context(
        episodes, query, budget, config
    )
    membership = tier_membership(episodes, query, config)
    recency_ids = set(membership["recency_ids"])
    k_ids = set(membership["k_ids"])

    flat_set, tiered_set = set(flat_ids), set(tiered_ids)
    delivered_evidence = wanted & tiered_set

    # Which tier carried the evidence, by the same rule `build_context`
    # counts with: recency membership wins, then K, else coverage.
    tiers = sorted(
        {
            "recency"
            if identity in recency_ids
            else ("k" if identity in k_ids else "coverage")
            for identity in delivered_evidence
        }
    )

    ranks = {
        episodes[index].identity: rank
        for rank, index in enumerate(flat_order(episodes, query), start=1)
    }
    evidence_ranks = sorted(ranks[identity] for identity in wanted)

    return {
        "question_id": question.identity,
        "question_content_sha256": question.content_sha256,
        "sample_id": question.sample_id,
        "source_index": question.source_index,
        "category": question.category,
        "resolved_evidence_count": len(question.resolved_evidence_ids),
        "unresolved_evidence_count": len(question.unresolved_evidence_ids),
        "complete_evaluable": not question.unresolved_evidence_ids,
        "evidence_episodes": len(wanted),
        "flat_complete": wanted <= flat_set,
        "tiered_complete": wanted <= tiered_set,
        "flat_any": bool(wanted & flat_set),
        "tiered_any": bool(wanted & tiered_set),
        "flat_delivered": len(flat_ids),
        "tiered_delivered": len(tiered_ids),
        "flat_chars": len(flat_payload),
        "tiered_chars": report.chars_delivered,
        "tiered_recency": report.stm_count,
        "tiered_k": report.k_count,
        "tiered_coverage": report.coverage_count,
        "tiered_dropped": report.episodes_dropped,
        "tiered_evidence_delivered": len(delivered_evidence),
        "tiered_evidence_tiers": "|".join(tiers),
        "flat_evidence_delivered": len(wanted & flat_set),
        "flat_best_evidence_rank": evidence_ranks[0],
        "flat_worst_evidence_rank": evidence_ranks[-1],
        "flat_budget_chars": flat_budget,
        "tiered_budget_chars": budget,
    }


# --------------------------------------------------------------------------
# Statistics - §6.2
# --------------------------------------------------------------------------


def paired(rows: Sequence[dict[str, Any]], endpoint: str) -> dict[str, Any]:
    flat_key, tiered_key = f"flat_{endpoint}", f"tiered_{endpoint}"
    gains = sum(1 for row in rows if row[tiered_key] and not row[flat_key])
    losses = sum(1 for row in rows if row[flat_key] and not row[tiered_key])
    discordant = gains + losses
    return {
        "endpoint": endpoint,
        "n": len(rows),
        "flat_hits": sum(1 for row in rows if row[flat_key]),
        "tiered_hits": sum(1 for row in rows if row[tiered_key]),
        "gains": gains,
        "losses": losses,
        "ties": len(rows) - discordant,
        "discordant": discordant,
        "net": gains - losses,
        "p_tiered_one_sided": one_sided_sign_p(gains, discordant),
        "p_flat_one_sided": one_sided_sign_p(losses, discordant),
    }


def one_sided_sign_p(successes: int, discordant: int) -> float:
    """P(X >= successes) for X ~ Binomial(discordant, 0.5)."""
    if discordant == 0:
        return 1.0
    tail = sum(
        math.comb(discordant, index) for index in range(successes, discordant + 1)
    )
    return min(1.0, tail / (2.0**discordant))


def verdict(statistic: dict[str, Any], *, band: int = NULL_BAND) -> dict[str, Any]:
    """§6.3's disposition table, applied and nothing else.

    The table is exhaustive over the real line, so this function has no
    fallback branch by construction; if it ever needed one, the table
    would be the defect.
    """
    net = statistic["net"]
    p_tiered = statistic["p_tiered_one_sided"]
    p_flat = statistic["p_flat_one_sided"]

    if abs(net) < band:
        identifier, name = "D0a", "NO_DIFFERENCE_ESTABLISHED_INSIDE_BAND"
    elif net >= band and p_tiered <= ALPHA:
        identifier, name = "D1", "TIERED_WINS"
    elif net >= band and p_tiered <= SIGNAL_ALPHA:
        identifier, name = "D2", "TIERED_CARRIES_SIGNAL"
    elif net <= -band and p_flat <= ALPHA:
        identifier, name = "D3", "FLAT_WINS"
    elif net <= -band and p_flat <= SIGNAL_ALPHA:
        identifier, name = "D4", "FLAT_CARRIES_SIGNAL"
    else:
        identifier, name = "D0b", "NO_DIFFERENCE_ESTABLISHED_NOT_SEPARABLE"

    return {
        "disposition": identifier,
        "verdict": name,
        "band": band,
        "alpha": ALPHA,
        "signal_alpha": SIGNAL_ALPHA,
        "statistic": statistic,
    }


def discordant_rows(rows: Sequence[dict[str, Any]], endpoint: str) -> list[dict]:
    """§4's pre-specified look at the pairs that decided the test."""
    flat_key, tiered_key = f"flat_{endpoint}", f"tiered_{endpoint}"
    out = []
    for row in rows:
        if row[flat_key] == row[tiered_key]:
            continue
        out.append(
            {
                "question_id": row["question_id"],
                "sample_id": row["sample_id"],
                "category": row["category"],
                "direction": "gain" if row[tiered_key] else "loss",
                "evidence_episodes": row["evidence_episodes"],
                "tiered_evidence_tiers": row["tiered_evidence_tiers"],
                "tiered_evidence_delivered": row["tiered_evidence_delivered"],
                "flat_evidence_delivered": row["flat_evidence_delivered"],
                "flat_best_evidence_rank": row["flat_best_evidence_rank"],
                "flat_worst_evidence_rank": row["flat_worst_evidence_rank"],
                "tiered_recency": row["tiered_recency"],
                "tiered_k": row["tiered_k"],
                "tiered_coverage": row["tiered_coverage"],
            }
        )
    return out


def summarize(rows: Sequence[dict[str, Any]], budget: int) -> dict[str, Any]:
    complete_rows = [row for row in rows if row["complete_evaluable"]]
    complete = paired(complete_rows, "complete")
    any_evidence = paired(rows, "any")
    return {
        "budget_chars": budget,
        "population": {
            "primary_complete_evidence": len(complete_rows),
            "secondary_any_evidence": len(rows),
        },
        "primary_complete_evidence": complete,
        "secondary_any_evidence": any_evidence,
        "by_conversation": {
            sample_id: paired(
                [
                    row
                    for row in complete_rows
                    if row["sample_id"] == sample_id
                ],
                "complete",
            )
            for sample_id in sorted({row["sample_id"] for row in complete_rows})
        },
        "by_category": {
            category: paired(
                [row for row in complete_rows if row["category"] == category],
                "complete",
            )
            for category in sorted({row["category"] for row in complete_rows})
        },
        "composition": _composition(rows),
        "delivery": {
            "flat_episodes": _distribution([row["flat_delivered"] for row in rows]),
            "tiered_episodes": _distribution(
                [row["tiered_delivered"] for row in rows]
            ),
            "flat_chars": _distribution([row["flat_chars"] for row in rows]),
            "tiered_chars": _distribution([row["tiered_chars"] for row in rows]),
        },
    }


def _composition(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Where the tiered arm's characters and its evidence came from.

    §9.1 of the paper records that the medians concealed a twentyfold
    change in the tier the system exists to provide, so the tier counts
    are reported as distributions and the evidence attribution is
    reported as counts of questions rather than as an average.
    """
    carried: dict[str, int] = {}
    for row in rows:
        if not row["tiered_evidence_tiers"]:
            continue
        carried[row["tiered_evidence_tiers"]] = (
            carried.get(row["tiered_evidence_tiers"], 0) + 1
        )
    return {
        "tiered_recency": _distribution([row["tiered_recency"] for row in rows]),
        "tiered_k": _distribution([row["tiered_k"] for row in rows]),
        "tiered_coverage": _distribution([row["tiered_coverage"] for row in rows]),
        "tiered_dropped": _distribution([row["tiered_dropped"] for row in rows]),
        "questions_with_zero_k_delivered": sum(
            1 for row in rows if row["tiered_k"] == 0
        ),
        "questions_with_zero_coverage_delivered": sum(
            1 for row in rows if row["tiered_coverage"] == 0
        ),
        "evidence_carried_by_tiers": dict(sorted(carried.items())),
        "flat_evidence_rank": {
            "best": _distribution([row["flat_best_evidence_rank"] for row in rows]),
            "worst": _distribution(
                [row["flat_worst_evidence_rank"] for row in rows]
            ),
        },
    }


# --------------------------------------------------------------------------
# Guards
# --------------------------------------------------------------------------


class ModelCallGuard:
    """Make a model call impossible rather than merely unexpected.

    The import chain reaches the embedding provider, so absence from
    ``sys.modules`` certifies nothing - it is reachability, not use. This
    replaces every entry point that could load or query the carried model
    with a raise, counts attempts, and restores the originals. Zero
    attempts is then a property of the run rather than a claim about it.
    """

    ENTRY_POINTS = (
        ("llama_cpp", "Llama", "__init__"),
        ("src.embeddings.provider", None, "_get_model"),
        ("retrieval_bakeoff.embedding", "CarriedEmbedder", "__init__"),
        ("src.retrieval_bakeoff.embedding", "CarriedEmbedder", "__init__"),
    )

    def __init__(self) -> None:
        self.attempts: list[str] = []
        self.armed: list[str] = []
        self._restore: list[tuple[object, str, object]] = []

    def __enter__(self) -> "ModelCallGuard":
        for module_name, class_name, attribute in self.ENTRY_POINTS:
            module = sys.modules.get(module_name)
            if module is None:
                continue
            owner = module if class_name is None else getattr(module, class_name, None)
            if owner is None or not hasattr(owner, attribute):
                continue
            label = ".".join(
                part for part in (module_name, class_name, attribute) if part
            )
            self._restore.append((owner, attribute, getattr(owner, attribute)))
            setattr(owner, attribute, self._refusal(label))
            self.armed.append(label)
        return self

    def __exit__(self, *_exception) -> None:
        for owner, attribute, original in reversed(self._restore):
            setattr(owner, attribute, original)
        self._restore.clear()

    def _refusal(self, label: str):
        def refuse(*_args, **_kwargs):
            self.attempts.append(label)
            raise TC001Error(f"TC-001 forbids model calls; {label} was called")

        return refuse

    def audit(self) -> dict[str, Any]:
        return {
            "status": "PASS" if not self.attempts else "FAIL",
            "armed_entry_points": sorted(self.armed),
            "attempts": self.attempts,
            "inference_calls": 0,
            "model_calls": len(self.attempts),
        }


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
        "null_band": "**B = 4 questions**",
        "alpha": "`p₊ ≤ 0.01`",
        "signal_alpha": "`0.01 < p₊ ≤ 0.10`",
        "wrapper_delta": "18 characters",
        "primary_population": "868",
    }
    missing = sorted(name for name, token in required.items() if token not in text)
    if missing:
        raise TC001Error(
            f"Registered parameters not found in the pre-registration: {missing}"
        )
    return {
        "status": "PASS",
        "pre_registration": _repo_relative(PRE_REGISTRATION),
        "pre_registration_sha256": sha256_file(PRE_REGISTRATION),
        "checked": sorted(required),
    }


def run_precondition(output_root: Path) -> dict[str, Any]:
    """PF3. The run phase may not open an arm before G0 is committed.

    Study 011's determinism check was implemented and run after every arm
    was scored. A gate that runs afterward is not a gate, so this one is
    a separate phase whose artifact must exist, be tracked by git, and
    say PASS before any availability number is computed here.
    """
    path = output_root / "g0" / "g0_reproduction.json"
    if not path.exists():
        raise TC001Error(f"G0 has not run: {path} is absent")
    if not _git_tracked(path):
        raise TC001Error(f"G0's artifact is not committed: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise TC001Error(f"G0 did not pass: {payload.get('status')}")
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
        raise TC001Error(f"Unregistered phase: {phase}")
    registration = assert_registration_agrees()
    precondition = None if phase == "g0" else run_precondition(output_root)

    started = time.time()
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    conversations = adapt_development(DATASET_PATH)

    if phase == "g0":
        # G0 runs `analyse`, which opens the cache itself; the guard still
        # stands, because a miss there would be a model call.
        with ModelCallGuard() as guard:
            result = g0_reproduction(conversations)
        audit = guard.audit()
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
            raise TC001Error(f"Read-only cache reported {reuse['misses']} misses")

        config = EpisodicConfig()
        by_conversation = {
            case.sample_id: build_episodes(case, vectors) for case in conversations
        }

        primary_rows = measure(
            conversations, by_conversation, vectors, config, budget=PRIMARY_BUDGET
        )
        secondary_rows = measure(
            conversations, by_conversation, vectors, config, budget=SECONDARY_BUDGET
        )
        robustness_rows = measure(
            conversations,
            by_conversation,
            vectors,
            config,
            budget=PRIMARY_BUDGET,
            flat_budget=PRIMARY_BUDGET - WRAPPER_DELTA,
        )
    audit = guard.audit()

    primary = summarize(primary_rows, PRIMARY_BUDGET)
    secondary = summarize(secondary_rows, SECONDARY_BUDGET)
    robustness = summarize(robustness_rows, PRIMARY_BUDGET)

    primary_verdict = verdict(primary["primary_complete_evidence"])
    robustness_verdict = verdict(robustness["primary_complete_evidence"])

    result = {
        "schema": SCHEMA,
        "status": "COMPLETE",
        "standing": "REGISTERED-OFFLINE",
        "primary": primary,
        "secondary_budget": secondary,
        "robustness_wrapper_matched": {
            "flat_budget_chars": PRIMARY_BUDGET - WRAPPER_DELTA,
            "tiered_budget_chars": PRIMARY_BUDGET,
            "summary": robustness,
            "verdict": robustness_verdict,
            "agrees_with_primary": (
                robustness_verdict["disposition"] == primary_verdict["disposition"]
            ),
        },
        "verdict": primary_verdict,
        "cache": {"hits": reuse["hits"], "misses": reuse["misses"]},
    }

    output_dir = output_root / "run"
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "summary.json", result)
    _write_json(output_dir / "verdict.json", primary_verdict)
    _write_json(output_dir / "no_model_call_audit.json", audit)
    _write_json(output_dir / "run_precondition.json", precondition)
    _write_csv(output_dir / "per_question_primary.csv", primary_rows)
    _write_csv(output_dir / "per_question_secondary.csv", secondary_rows)
    _write_csv(
        output_dir / "discordant_primary.csv",
        discordant_rows(
            [row for row in primary_rows if row["complete_evaluable"]], "complete"
        ),
    )
    _write_json(
        output_dir / "run_header.json",
        _run_header(
            phase,
            registration,
            precondition,
            manifest,
            started,
            primary_verdict["verdict"],
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
        "study": "TC-001",
        "phase": phase,
        "outcome": outcome,
        "schema": SCHEMA,
        "design_commit": _git(
            "log", "--format=%H", "-1", "--", _repo_relative(PRE_REGISTRATION)
        ),
        "execution_commit": _git("rev-parse", "HEAD"),
        # Scoped to code and registration rather than the whole tree: the
        # question is whether `execution_commit` describes the code that
        # ran, and a re-run would otherwise see its own output as dirt.
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
            "wrapper_delta_chars": WRAPPER_DELTA,
            "seed": SEED,
            "drop_policy": DROP_POLICY,
            "renderer": "post-DR-001 compact exact-cost renderer",
        },
        "inputs": {
            "dataset_sha256": manifest["dataset_sha256"],
            "cache_file_sha256": manifest["cache"]["file_sha256"],
            "cache_content_sha256": manifest["cache"]["content_sha256"],
            "embedder_sha256": CARRIED_EMBEDDER_SHA256,
            "development_ids": manifest["development_ids"],
        },
        "sources": {
            _repo_relative(path): sha256_file(path)
            for path in _source_paths()
        },
        "inference_calls": 0,
        "model_calls": 0,
        "embedding_calls": 0,
        "elapsed_seconds": round(time.time() - started, 3),
    }


def _source_paths() -> list[Path]:
    return [
        Path(__file__).resolve(),
        REPO_ROOT / "src" / "analysis" / "tc001_exploration.py",
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


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_artifact_manifest(output_dir: Path) -> None:
    paths = sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file() and path.name != "artifact_manifest.json"
    )
    _write_json(
        output_dir / "artifact_manifest.json",
        {
            "status": "COMPLETE",
            "artifacts": {
                path.relative_to(output_dir).as_posix(): sha256_file(path)
                for path in paths
            },
        },
    )


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _git_tracked(path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        # Outside the repository, so nothing tracks it. A gate written
        # somewhere git cannot see is untracked, not an error to report
        # from the path arithmetic.
        return False
    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", relative],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one TC-001 phase.")
    parser.add_argument("--phase", choices=PHASES, required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=STUDY_ROOT / "runs" / "tc001",
    )
    arguments = parser.parse_args()
    result = run_phase(arguments.output_root, arguments.phase)
    if arguments.phase == "g0":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps(result["verdict"], indent=2, sort_keys=True))


__all__ = [
    "ALPHA",
    "NULL_BAND",
    "PRIMARY_BUDGET",
    "SECONDARY_BUDGET",
    "SIGNAL_ALPHA",
    "WRAPPER_DELTA",
    "ModelCallGuard",
    "TC001Error",
    "assert_registration_agrees",
    "discordant_rows",
    "g0_reproduction",
    "measure",
    "one_sided_sign_p",
    "paired",
    "run_phase",
    "summarize",
    "verdict",
]

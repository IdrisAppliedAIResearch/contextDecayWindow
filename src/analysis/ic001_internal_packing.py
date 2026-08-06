"""IC-001 harness: the internal packing-priority counterfactual.

Offline replay against committed artifacts. No inference, no embedding
call, no mechanism change. The two arms differ only in packing order; the
candidate identities themselves come from the deployed run's committed
context log, so no vector is re-derived here at all.

The run is split into two phases because the B0 gate is binding. Phase
``b0`` writes the recency-first arm and its gate against the committed
deployed result, and nothing else. Phase ``b1`` refuses to start until
that gate is committed and PASS, then opens the K-first arm and the
paired comparison. Git order is the evidence, per DR-001/G-R1.

Rubric artifacts enter only through `ATOMIC_ITEMS`/`TARGETED_ITEMS` in
this measurement module, never through `src/internal_packing/ic001.py`.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import sqlite3
import subprocess
import sys
import unicodedata
from collections.abc import Iterable, Sequence
from pathlib import Path

from src.analysis.retrieval_bakeoff_tier6_121 import (
    ATOMIC_ITEMS,
    TARGETED_ITEMS,
)
from src.internal_packing.ic001 import (
    DROP_POLICY,
    PACKING_ORDERS,
    IC001Error,
    PackedArm,
    TierState,
    assert_b0_matches_deployed_packer,
    assert_mechanism_path_allowed,
    build_tier_state,
    dropped_by_path,
    pack_arm,
    path_accounting,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
)
STUDY_ROOT = REPO_ROOT / "experiments" / "internal" / "packing_priority"
RUN_ROOT = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier6"
    / "runs"
    / "tier6_live_121_corrected_001"
    / "context_matched_stm"
)
ANALYSIS_ROOT = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier6"
    / "analysis_corrected_121"
)
CONTEXT_LOG = RUN_ROOT / "logs" / "context_match.jsonl"
TURN_LOG = RUN_ROOT / "logs" / "turns.jsonl"
DATABASE = RUN_ROOT / "study.db"
TARGETED_MEASUREMENT = ANALYSIS_ROOT / "targeted_fact_delivery.csv"
COMMITTED_A0 = COMPONENT_ROOT / "artifacts" / "e005" / "a0_baseline.json"
AR_001_ACHIEVABILITY = (
    COMPONENT_ROOT / "artifacts" / "ar_001" / "achievability.json"
)
MECHANISM_SOURCE = REPO_ROOT / "src" / "internal_packing" / "ic001.py"
PRE_REGISTRATION = (
    STUDY_ROOT / "IC_001_internal_packing_counterfactual.md"
)

DESIGN_COMMIT_SUBJECT = "docs(ic-001): register internal packing-priority counterfactual"
Q11_TURN = 120
BUDGET_CHARS = 32_000
EXPECTED_K_THRESHOLD = 0.48
EXPECTED_N_CAP = 32
SEED = 5005
PHASES = ("b0", "b1")
ARMS = {"b0": "B0", "b1": "B1"}
ARM_LABEL = {
    "B0": "recency -> K -> coverage (deployed)",
    "B1": "K -> recency -> coverage (EC-002 A1 order)",
}
TARGETED_QUESTIONS = tuple(TARGETED_ITEMS)
PROBE_TURNS = tuple(
    sorted({turn for turn, _needles in TARGETED_ITEMS.values()})
)


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------


def load_candidates() -> tuple[dict, ...]:
    connection = sqlite3.connect(
        f"file:{DATABASE.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT
                episodes.id,
                episodes.turn_number,
                episodes.user_message,
                episodes.assistant_message,
                COALESCE(episodes.ground_truth_domain, '') AS ground_truth_domain
            FROM episodes
            ORDER BY episodes.turn_number ASC, episodes.id ASC
            """
        ).fetchall()
    finally:
        connection.close()
    return tuple(dict(row) for row in rows)


def load_context_records() -> dict[int, dict]:
    records = {
        int(row["turn_number"]): row for row in _read_jsonl(CONTEXT_LOG)
    }
    required = {Q11_TURN, *PROBE_TURNS}
    missing = sorted(required - set(records))
    if missing:
        raise IC001Error(f"Committed context log is missing probe turns: {missing}")
    return records


def build_states(
    context_records: dict[int, dict],
    by_id: dict[str, dict],
) -> dict[int, TierState]:
    """Frozen tiers per probe turn, straight from the committed log.

    The deployed configuration has no coverage tier: it is recency plus a
    K threshold, so `coverage` is empty in both arms and the two orders
    differ only in whether K or recency is offered first. That is recorded
    rather than assumed - the pre-registration names three tiers, and this
    corpus's deployed arm populates two of them.
    """

    states: dict[int, TierState] = {}
    for turn in sorted({Q11_TURN, *PROBE_TURNS}):
        record = context_records[turn]
        if float(record["k_threshold"]) != EXPECTED_K_THRESHOLD:
            raise IC001Error(
                f"Turn {turn} K threshold {record['k_threshold']} is not the "
                f"held-fixed {EXPECTED_K_THRESHOLD}"
            )
        if int(record["n_cap"]) != EXPECTED_N_CAP:
            raise IC001Error(
                f"Turn {turn} N cap {record['n_cap']} is not the held-fixed "
                f"{EXPECTED_N_CAP}"
            )
        states[turn] = build_tier_state(
            probe_turn=turn,
            n_candidate_ids=[str(value) for value in record["n_candidate_ids"]],
            k_candidate_ids=[str(value) for value in record["k_candidate_ids"]],
            by_id=by_id,
            coverage_ids=(),
        )
    return states


# --------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------


def q11_availability(payload: str) -> dict:
    normalized = _normalize(payload)
    items = [
        {
            "domain": domain,
            "item": item,
            "available": needle in normalized,
        }
        for domain, item, needle, _plant_turns in ATOMIC_ITEMS
    ]
    available = [row for row in items if row["available"]]
    per_domain = {domain: 0 for domain, _i, _n, _t in ATOMIC_ITEMS}
    for row in available:
        per_domain[row["domain"]] += 1
    return {
        "fact_count": len(available),
        "domain_count": len({row["domain"] for row in available}),
        "per_domain": per_domain,
        "items": items,
    }


def targeted_availability(payloads: dict[int, str]) -> dict[str, dict]:
    """Per-probe availability for all eight committed targeted questions."""

    result: dict[str, dict] = {}
    for question, (turn, needles) in TARGETED_ITEMS.items():
        normalized = _normalize(payloads[turn])
        items = [
            {"item": needle, "available": needle in normalized}
            for needle in needles
        ]
        result[question] = {
            "turn": turn,
            "items": items,
            "available_count": sum(1 for row in items if row["available"]),
            "item_count": len(items),
        }
    return result


def committed_targeted_items() -> dict[tuple[str, str], bool]:
    rows = _read_csv(TARGETED_MEASUREMENT)
    return {
        (row["question"], row["item"]): row["in_retrieval_payload"] == "True"
        for row in rows
        if row["arm"] == "T6"
    }


def oracle_sets() -> dict[str, dict]:
    achievability = json.loads(
        AR_001_ACHIEVABILITY.read_text(encoding="utf-8")
    )
    return {
        "exact_optimum_14_of_17": {
            "episode_ids": list(achievability["exact_optimum"]["selected_ids"]),
            "source_turns": list(
                achievability["exact_optimum"]["selected_source_turns"]
            ),
            "fact_count": achievability["exact_optimum"]["fact_count"],
            "serialized_chars": achievability["exact_optimum"][
                "serialized_chars"
            ],
        },
        "greedy_15_of_17": {
            "episode_ids": list(
                achievability["greedy_upper_bound"]["selected_ids"]
            ),
            "source_turns": list(
                achievability["greedy_upper_bound"]["selected_source_turns"]
            ),
            "fact_count": achievability["greedy_upper_bound"]["fact_count"],
            "serialized_chars": achievability["greedy_upper_bound"][
                "serialized_chars"
            ],
        },
    }


# --------------------------------------------------------------------------
# Arm construction
# --------------------------------------------------------------------------


def build_arm(
    arm: str,
    states: dict[int, TierState],
) -> dict[int, PackedArm]:
    return {
        turn: pack_arm(state, arm=arm, budget=BUDGET_CHARS)
        for turn, state in sorted(states.items())
    }


def arm_record(
    arm: str,
    states: dict[int, TierState],
    packed_by_turn: dict[int, PackedArm],
) -> dict:
    payloads = {turn: packed.payload for turn, packed in packed_by_turn.items()}
    q11 = q11_availability(payloads[Q11_TURN])
    targeted = targeted_availability(payloads)
    probes = {}
    for turn, packed in sorted(packed_by_turn.items()):
        state = states[turn]
        probes[str(turn)] = {
            "probe_turn": turn,
            "serialized_chars": packed.serialized_chars,
            "budget_chars": packed.budget_chars,
            "payload_sha256": packed.payload_sha256,
            "selected_ids": list(packed.selected_ids),
            "selected_source_turns": [
                int(episode["turn_number"])
                for episode in (
                    *packed.recent_episodes,
                    *packed.stm_episodes,
                )
            ],
            "considered_ids": list(packed.considered_ids),
            "dropped_ids": list(packed.dropped_ids),
            "dropped_by_path": dropped_by_path(state, packed),
            **path_accounting(state, packed),
        }
    return {
        "arm": arm,
        "packing_order": list(PACKING_ORDERS[arm]),
        "order_label": ARM_LABEL[arm],
        "drop_policy": DROP_POLICY,
        "budget_chars": BUDGET_CHARS,
        "q11": {
            "probe_turn": Q11_TURN,
            "fact_count": q11["fact_count"],
            "domain_count": q11["domain_count"],
            "per_domain": q11["per_domain"],
            "items": q11["items"],
            "serialized_chars": packed_by_turn[Q11_TURN].serialized_chars,
            "payload_sha256": packed_by_turn[Q11_TURN].payload_sha256,
            "selected_ids": list(packed_by_turn[Q11_TURN].selected_ids),
        },
        "targeted": targeted,
        "targeted_available_total": sum(
            entry["available_count"] for entry in targeted.values()
        ),
        "targeted_item_total": sum(
            entry["item_count"] for entry in targeted.values()
        ),
        "probes": probes,
    }


def oracle_overlap(
    packed_by_turn: dict[int, PackedArm],
    oracles: dict[str, dict],
) -> dict:
    delivered = set(packed_by_turn[Q11_TURN].selected_ids)
    return {
        name: {
            "delivered": [
                episode_id
                for episode_id in oracle["episode_ids"]
                if episode_id in delivered
            ],
            "missing": [
                episode_id
                for episode_id in oracle["episode_ids"]
                if episode_id not in delivered
            ],
            "delivered_source_turns": [
                turn
                for episode_id, turn in zip(
                    oracle["episode_ids"],
                    oracle["source_turns"],
                    strict=True,
                )
                if episode_id in delivered
            ],
            "found": sum(
                1
                for episode_id in oracle["episode_ids"]
                if episode_id in delivered
            ),
            "total": len(oracle["episode_ids"]),
        }
        for name, oracle in oracles.items()
    }


# --------------------------------------------------------------------------
# Gates
# --------------------------------------------------------------------------


def b0_gate(
    states: dict[int, TierState],
    packed_by_turn: dict[int, PackedArm],
    record: dict,
) -> dict:
    """The binding gate: B0 must be the committed deployed result.

    Fact count alone can match with different episodes, so identity,
    payload digest, character count, and the per-domain breakdown are all
    asserted (pre-registration section 7).
    """

    committed = json.loads(COMMITTED_A0.read_text(encoding="utf-8"))
    q11 = record["q11"]
    committed_items = {
        (row["domain"], row["item"]): bool(row["available"])
        for row in committed["items"]
    }
    replay_items = {
        (row["domain"], row["item"]): bool(row["available"])
        for row in q11["items"]
    }
    item_mismatches = sorted(
        f"{domain}:{item}"
        for (domain, item), value in replay_items.items()
        if committed_items.get((domain, item)) != value
    )
    committed_per_domain = {domain: 0 for domain, _i, _n, _t in ATOMIC_ITEMS}
    for (domain, _item), available in committed_items.items():
        if available:
            committed_per_domain[domain] += 1

    equivalence = assert_b0_matches_deployed_packer(
        states[Q11_TURN],
        packed_by_turn[Q11_TURN],
        budget=BUDGET_CHARS,
    )
    checks = {
        "fact_count": q11["fact_count"] == int(committed["fact_count"]),
        "domain_count": q11["domain_count"] == int(committed["domain_count"]),
        "serialized_chars": (
            q11["serialized_chars"] == int(committed["serialized_chars"])
        ),
        "selected_episode_count": (
            len(q11["selected_ids"]) == int(committed["selected_episode_count"])
        ),
        "episode_identities": (
            q11["selected_ids"] == list(committed["selected_ids"])
        ),
        "payload_sha256": (
            q11["payload_sha256"] == committed["payload_sha256"]
        ),
        "per_domain_breakdown": q11["per_domain"] == committed_per_domain,
        "item_level_match": not item_mismatches,
        "deployed_packer_equivalence": equivalence["status"] == "PASS",
    }
    return {
        "gate": "B0",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "binding": True,
        "consequence_on_failure": "IC-001 stops; the delta is uninterpretable",
        "committed_artifact": _repo_relative(COMMITTED_A0),
        "committed": {
            "fact_count": committed["fact_count"],
            "domain_count": committed["domain_count"],
            "serialized_chars": committed["serialized_chars"],
            "selected_episode_count": committed["selected_episode_count"],
            "selected_ids": committed["selected_ids"],
            "payload_sha256": committed["payload_sha256"],
            "per_domain": committed_per_domain,
        },
        "replay": {
            "fact_count": q11["fact_count"],
            "domain_count": q11["domain_count"],
            "serialized_chars": q11["serialized_chars"],
            "selected_episode_count": len(q11["selected_ids"]),
            "selected_ids": q11["selected_ids"],
            "payload_sha256": q11["payload_sha256"],
            "per_domain": q11["per_domain"],
        },
        "item_mismatches": item_mismatches,
        "deployed_packer_equivalence": equivalence,
        "checks": checks,
    }


def leakage_audit() -> dict:
    """The mechanism must not be able to see the answer key."""

    source = MECHANISM_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    forbidden_tokens = (
        "q_facts_key",
        "rubric",
        "atomic_items",
        "targeted_items",
    )
    forbidden_imports = [
        name
        for name in imported
        if any(token in name.lower() for token in forbidden_tokens)
    ]
    literal_hits = sorted(
        {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and any(token in node.value.lower() for token in forbidden_tokens)
            and node.value not in forbidden_tokens
        }
    )
    planted_rejected = False
    try:
        assert_mechanism_path_allowed(
            REPO_ROOT / "experiments" / "study_009" / "q_facts_key.md"
        )
    except ValueError:
        planted_rejected = True
    return {
        "status": (
            "PASS"
            if not forbidden_imports and not literal_hits and planted_rejected
            else "FAIL"
        ),
        "mechanism_source": _repo_relative(MECHANISM_SOURCE),
        "imports": sorted(imported),
        "forbidden_imports": forbidden_imports,
        "forbidden_literals": literal_hits,
        "planted_forbidden_path_rejected": planted_rejected,
    }


class ModelCallGuard:
    """Make a model call impossible rather than merely unexpected.

    The measurement module's import chain reaches the embedding provider,
    so module presence in `sys.modules` certifies nothing: it is
    reachability, not use. This guard replaces every entry point that
    could load or query the carried model with a raise, counts attempts,
    and restores the originals afterwards. Zero attempts is then a
    property of the run, not a claim about it.
    """

    ENTRY_POINTS = (
        ("llama_cpp", "Llama", "__init__"),
        ("src.embeddings.provider", None, "_get_model"),
        ("src.retrieval_bakeoff.embedding", "CarriedEmbedder", "__init__"),
    )

    def __init__(self) -> None:
        self.attempts: list[str] = []
        self._restore: list[tuple[object, str, object]] = []
        self.armed: list[str] = []

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
            raise AssertionError(
                f"IC-001 is an offline replay: {label} must not be called"
            )

        return refuse

    def audit(self) -> dict:
        provider = sys.modules.get("src.embeddings.provider")
        provider_model_loaded = (
            provider is not None
            and getattr(provider, "_MODEL", None) is not None
        )
        return {
            "status": (
                "PASS"
                if not self.attempts and not provider_model_loaded and self.armed
                else "FAIL"
            ),
            "model_calls": 0,
            "embedding_calls": 0,
            "cache_misses": 0,
            "vector_source": (
                "committed context_match.jsonl candidate identities; no "
                "vector is re-derived and no cache is read"
            ),
            "guarded_entry_points": self.armed,
            "attempted_calls": self.attempts,
            "embedding_provider_model_loaded": provider_model_loaded,
            "amendment": "AMENDMENT_001_no_vector_recomputation",
        }


# --------------------------------------------------------------------------
# Paired comparison and verdict
# --------------------------------------------------------------------------


def paired_comparison(b0: dict, b1: dict) -> dict:
    q11_gains = [
        f"{row['domain']}:{row['item']}"
        for row, before in zip(b1["q11"]["items"], b0["q11"]["items"], strict=True)
        if row["available"] and not before["available"]
    ]
    q11_losses = [
        f"{row['domain']}:{row['item']}"
        for row, before in zip(b1["q11"]["items"], b0["q11"]["items"], strict=True)
        if before["available"] and not row["available"]
    ]
    committed = committed_targeted_items()
    per_probe = {}
    targeted_gains: list[str] = []
    targeted_losses: list[str] = []
    for question in TARGETED_QUESTIONS:
        before = b0["targeted"][question]
        after = b1["targeted"][question]
        gains = [
            row["item"]
            for row, was in zip(after["items"], before["items"], strict=True)
            if row["available"] and not was["available"]
        ]
        losses = [
            row["item"]
            for row, was in zip(after["items"], before["items"], strict=True)
            if was["available"] and not row["available"]
        ]
        targeted_gains.extend(f"{question}:{item}" for item in gains)
        targeted_losses.extend(f"{question}:{item}" for item in losses)
        per_probe[question] = {
            "turn": before["turn"],
            "item_count": before["item_count"],
            "b0_available": before["available_count"],
            "b1_available": after["available_count"],
            "delta": after["available_count"] - before["available_count"],
            "gains": gains,
            "losses": losses,
            "committed_t6_available": sum(
                1
                for row in before["items"]
                if committed.get((question, row["item"]), False)
            ),
            "items": [
                {
                    "item": row["item"],
                    "b0": was["available"],
                    "b1": row["available"],
                    "committed_t6": committed.get((question, row["item"])),
                }
                for row, was in zip(after["items"], before["items"], strict=True)
            ],
        }
    falling_probes = [
        question for question, row in per_probe.items() if row["delta"] < 0
    ]
    rising_probes = [
        question for question, row in per_probe.items() if row["delta"] > 0
    ]
    targeted_total_delta = (
        b1["targeted_available_total"] - b0["targeted_available_total"]
    )
    return {
        "q11": {
            "b0_fact_count": b0["q11"]["fact_count"],
            "b1_fact_count": b1["q11"]["fact_count"],
            "delta": b1["q11"]["fact_count"] - b0["q11"]["fact_count"],
            "gains": q11_gains,
            "losses": q11_losses,
            "gain_count": len(q11_gains),
            "loss_count": len(q11_losses),
            "b0_per_domain": b0["q11"]["per_domain"],
            "b1_per_domain": b1["q11"]["per_domain"],
            "b0_domain_count": b0["q11"]["domain_count"],
            "b1_domain_count": b1["q11"]["domain_count"],
        },
        "targeted": {
            "per_probe": per_probe,
            "gains": targeted_gains,
            "losses": targeted_losses,
            "gain_count": len(targeted_gains),
            "loss_count": len(targeted_losses),
            "b0_available_total": b0["targeted_available_total"],
            "b1_available_total": b1["targeted_available_total"],
            "total_delta": targeted_total_delta,
            "falling_probes": falling_probes,
            "rising_probes": rising_probes,
            "falls_any_probe": bool(falling_probes),
            "falls_in_total": targeted_total_delta < 0,
            "indicators_agree": bool(falling_probes) == (targeted_total_delta < 0),
        },
        "note": (
            "Paired counts only. The program holds no variance estimate, so "
            "no count here may be converted into a significance claim."
        ),
    }


def verdict(comparison: dict) -> dict:
    """The registered four-branch rule, applied without reinterpretation.

    No materiality threshold is registered, matching EC-002's treatment,
    so 'rises materially' is read as any nonzero rise and 'unchanged or
    trivially changed' as a delta of zero. 'Q1-Q8 falls' is read at the
    per-probe grain the surrogate audit requires; the aggregate indicator
    is carried alongside and a disagreement between the two is reported
    rather than resolved silently.
    """

    q11_delta = comparison["q11"]["delta"]
    targeted = comparison["targeted"]
    falls = targeted["falls_any_probe"] or targeted["falls_in_total"]
    if q11_delta < 0:
        branch, name, consequence = (
            "D",
            "RECENCY WAS LOAD-BEARING HERE",
            "Strengthens PAPER-001 section 5's selection attribution. "
            "Record and stop.",
        )
    elif q11_delta == 0:
        branch, name, consequence = (
            "B",
            "RECENCY-RELEVANCE OVERLAP ABSORBED IT",
            "The internal corpus did not have the external failure. "
            "Section 5 stands. No recalibration. A publishable boundary "
            "condition on EC-002's finding.",
        )
    elif falls:
        branch, name, consequence = (
            "C",
            "TRADE, NOT A GAIN",
            "The LV-001 pattern reproduced offline. Report both. No "
            "promotion, no recalibration on availability alone.",
        )
    else:
        branch, name, consequence = (
            "A",
            "PACKING IS A GATE INTERNALLY TOO",
            "PAPER-001 section 5's decomposition must be revised - some "
            "selection attribution is packing attribution. Section 6's "
            "recalibration conditions become live.",
        )
    return {
        "branch": branch,
        "verdict": name,
        "consequence": consequence,
        "q11_delta": q11_delta,
        "targeted_falls_any_probe": targeted["falls_any_probe"],
        "targeted_falls_in_total": targeted["falls_in_total"],
        "targeted_indicators_agree": targeted["indicators_agree"],
        "falling_probes": targeted["falling_probes"],
        "materiality_threshold": (
            "none registered; any nonzero rise is a rise, a zero delta is "
            "unchanged"
        ),
        "interpretation_boundary": (
            "Availability only, one probe, one store, one run, no variance. "
            "Section 6.4 forbids any verdict change without a separately "
            "registered live run."
        ),
    }


# --------------------------------------------------------------------------
# Phases
# --------------------------------------------------------------------------


def run_phase(output_root: Path, phase: str) -> dict:
    if phase not in PHASES:
        raise IC001Error(f"Unregistered phase: {phase}")
    output_dir = (output_root / _phase_dir(phase)).resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite IC-001 output: {output_dir}")

    inputs = _input_paths()
    before = _hash_paths(inputs)
    leakage = leakage_audit()
    if leakage["status"] != "PASS":
        raise RuntimeError("IC-001 leakage audit failed")

    with ModelCallGuard() as guard:
        candidates = load_candidates()
        by_id = {str(candidate["id"]): candidate for candidate in candidates}
        context_records = load_context_records()
        states = build_states(context_records, by_id)

        b0_packed = build_arm("B0", states)
        b0 = arm_record("B0", states, b0_packed)
        gate = b0_gate(states, b0_packed, b0)

        if phase == "b0":
            result = _run_b0(
                output_dir,
                states=states,
                b0=b0,
                b0_packed=b0_packed,
                gate=gate,
                leakage=leakage,
                guard=guard,
            )
        else:
            result = _run_b1(
                output_dir,
                output_root=output_root,
                states=states,
                b0=b0,
                b0_packed=b0_packed,
                gate=gate,
                leakage=leakage,
                guard=guard,
            )

    after = _hash_paths(inputs)
    source_integrity = {
        "status": "PASS" if before == after else "FAIL",
        "before": before,
        "after": after,
    }
    _write_json(output_dir / "source_integrity.json", source_integrity)
    if source_integrity["status"] != "PASS":
        raise AssertionError("An IC-001 input changed during execution")
    result["source_integrity_status"] = source_integrity["status"]
    _write_json(output_dir / "run_header.json", _run_header(phase, result))
    _write_artifact_manifest(output_dir)
    return result


def _run_b0(
    output_dir: Path,
    *,
    states: dict[int, TierState],
    b0: dict,
    b0_packed: dict[int, PackedArm],
    gate: dict,
    leakage: dict,
    guard: "ModelCallGuard",
) -> dict:
    output_dir.mkdir(parents=True)
    _write_json(output_dir / "leakage_audit.json", leakage)
    _write_json(output_dir / "b0_arm.json", b0)
    _write_json(output_dir / "b0_gate.json", gate)
    (output_dir / "b0_q11_payload.txt").write_text(
        b0_packed[Q11_TURN].payload,
        encoding="utf-8",
        newline="\n",
    )
    _write_csv(
        output_dir / "b0_q11_items.csv",
        b0["q11"]["items"],
        ("domain", "item", "available"),
    )
    _write_csv(
        output_dir / "b0_targeted_items.csv",
        _targeted_rows("B0", b0),
        ("arm", "question", "turn", "item", "available"),
    )
    _write_csv(
        output_dir / "b0_path_split.csv",
        _path_rows("B0", b0),
        _PATH_FIELDS,
    )

    rerun = arm_record("B0", states, build_arm("B0", states))
    determinism = {
        "status": (
            "PASS"
            if _digest(rerun) == _digest(b0)
            else "FAIL"
        ),
        "arm_sha256": _digest(b0),
        "rerun_sha256": _digest(rerun),
    }
    _write_json(output_dir / "determinism.json", determinism)
    if determinism["status"] != "PASS":
        raise AssertionError("IC-001 B0 rerun was not identical")

    audit = guard.audit()
    _write_json(output_dir / "no_model_call_audit.json", audit)
    if audit["status"] != "PASS":
        raise AssertionError("IC-001 made a model or embedding call")

    if gate["status"] != "PASS":
        raise AssertionError(
            "B0 gate FAILED: IC-001 stops, B1 must not be opened"
        )
    return {
        "study": "IC-001",
        "phase": "b0",
        "status": "COMPLETE",
        "b0_gate_status": gate["status"],
        "leakage_audit_status": leakage["status"],
        "determinism_status": determinism["status"],
        "model_call_audit_status": audit["status"],
        "q11_fact_count": b0["q11"]["fact_count"],
        "q11_domain_count": b0["q11"]["domain_count"],
        "q11_serialized_chars": b0["q11"]["serialized_chars"],
        "targeted_available_total": b0["targeted_available_total"],
        "next": "Commit this phase before opening B1.",
    }


def _run_b1(
    output_dir: Path,
    *,
    output_root: Path,
    states: dict[int, TierState],
    b0: dict,
    b0_packed: dict[int, PackedArm],
    gate: dict,
    leakage: dict,
    guard: "ModelCallGuard",
) -> dict:
    precondition = _b1_precondition(output_root, b0, gate)
    if precondition["status"] != "PASS":
        raise AssertionError(
            "B1 refused: the committed B0 gate is missing, uncommitted, "
            "failing, or does not match this replay"
        )

    output_dir.mkdir(parents=True)
    _write_json(output_dir / "b1_gate_precondition.json", precondition)
    _write_json(output_dir / "leakage_audit.json", leakage)

    b1_packed = build_arm("B1", states)
    b1 = arm_record("B1", states, b1_packed)
    _write_json(output_dir / "b1_arm.json", b1)
    (output_dir / "b1_q11_payload.txt").write_text(
        b1_packed[Q11_TURN].payload,
        encoding="utf-8",
        newline="\n",
    )

    oracles = oracle_sets()
    overlap = {
        "oracle_sets": oracles,
        "B0": oracle_overlap(b0_packed, oracles),
        "B1": oracle_overlap(b1_packed, oracles),
    }
    _write_json(output_dir / "oracle_overlap.json", overlap)
    _write_csv(
        output_dir / "oracle_overlap.csv",
        [
            {
                "arm": arm,
                "oracle_set": name,
                "episode_id": episode_id,
                "source_turn": turn,
                "delivered": episode_id in set(overlap[arm][name]["delivered"]),
            }
            for arm in ("B0", "B1")
            for name, oracle in oracles.items()
            for episode_id, turn in zip(
                oracle["episode_ids"], oracle["source_turns"], strict=True
            )
        ],
        ("arm", "oracle_set", "episode_id", "source_turn", "delivered"),
    )

    comparison = paired_comparison(b0, b1)
    _write_json(output_dir / "paired_comparison.json", comparison)
    branch = verdict(comparison)
    _write_json(output_dir / "verdict.json", branch)

    _write_csv(
        output_dir / "q11_per_domain.csv",
        [
            {
                "arm": arm,
                **record["q11"]["per_domain"],
                "fact_count": record["q11"]["fact_count"],
                "domain_count": record["q11"]["domain_count"],
                "serialized_chars": record["q11"]["serialized_chars"],
            }
            for arm, record in (("B0", b0), ("B1", b1))
        ],
        (
            "arm",
            "civil",
            "art",
            "monetary",
            "marine",
            "fact_count",
            "domain_count",
            "serialized_chars",
        ),
    )
    _write_csv(
        output_dir / "q11_item_matrix.csv",
        [
            {
                "domain": after["domain"],
                "item": after["item"],
                "b0": before["available"],
                "b1": after["available"],
            }
            for after, before in zip(
                b1["q11"]["items"], b0["q11"]["items"], strict=True
            )
        ],
        ("domain", "item", "b0", "b1"),
    )
    _write_csv(
        output_dir / "targeted_per_probe.csv",
        [
            {
                "question": question,
                "turn": row["turn"],
                "item_count": row["item_count"],
                "committed_t6_available": row["committed_t6_available"],
                "b0_available": row["b0_available"],
                "b1_available": row["b1_available"],
                "delta": row["delta"],
                "gains": ";".join(row["gains"]),
                "losses": ";".join(row["losses"]),
            }
            for question, row in comparison["targeted"]["per_probe"].items()
        ],
        (
            "question",
            "turn",
            "item_count",
            "committed_t6_available",
            "b0_available",
            "b1_available",
            "delta",
            "gains",
            "losses",
        ),
    )
    _write_csv(
        output_dir / "path_split.csv",
        [*_path_rows("B0", b0), *_path_rows("B1", b1)],
        _PATH_FIELDS,
    )
    _write_csv(
        output_dir / "targeted_item_matrix.csv",
        [
            {
                "question": question,
                "turn": row["turn"],
                "item": item["item"],
                "b0": item["b0"],
                "b1": item["b1"],
                "committed_t6": item["committed_t6"],
            }
            for question, row in comparison["targeted"]["per_probe"].items()
            for item in row["items"]
        ],
        ("question", "turn", "item", "b0", "b1", "committed_t6"),
    )

    rerun = arm_record("B1", states, build_arm("B1", states))
    determinism = {
        "status": "PASS" if _digest(rerun) == _digest(b1) else "FAIL",
        "arm_sha256": _digest(b1),
        "rerun_sha256": _digest(rerun),
    }
    _write_json(output_dir / "determinism.json", determinism)
    if determinism["status"] != "PASS":
        raise AssertionError("IC-001 B1 rerun was not identical")

    audit = guard.audit()
    _write_json(output_dir / "no_model_call_audit.json", audit)
    if audit["status"] != "PASS":
        raise AssertionError("IC-001 made a model or embedding call")

    return {
        "study": "IC-001",
        "phase": "b1",
        "status": "COMPLETE",
        "b0_gate_status": gate["status"],
        "b1_precondition_status": precondition["status"],
        "leakage_audit_status": leakage["status"],
        "determinism_status": determinism["status"],
        "model_call_audit_status": audit["status"],
        "branch": branch["branch"],
        "verdict": branch["verdict"],
        "q11": comparison["q11"],
        "targeted_total_delta": comparison["targeted"]["total_delta"],
        "targeted_gain_count": comparison["targeted"]["gain_count"],
        "targeted_loss_count": comparison["targeted"]["loss_count"],
        "oracle_overlap": {
            arm: {name: overlap[arm][name]["found"] for name in oracles}
            for arm in ("B0", "B1")
        },
    }


def _b1_precondition(output_root: Path, b0: dict, gate: dict) -> dict:
    """B1 may not be opened until B0's gate is committed and passing."""

    b0_dir = output_root / _phase_dir("b0")
    gate_path = b0_dir / "b0_gate.json"
    arm_path = b0_dir / "b0_arm.json"
    present = gate_path.is_file() and arm_path.is_file()
    committed_gate = _git_tracked(gate_path) if present else False
    committed_arm = _git_tracked(arm_path) if present else False
    stored_gate = (
        json.loads(gate_path.read_text(encoding="utf-8")) if present else {}
    )
    stored_arm = (
        json.loads(arm_path.read_text(encoding="utf-8")) if present else {}
    )
    reproduces = present and _digest(stored_arm) == _digest(b0)
    gate_passes = stored_gate.get("status") == "PASS"
    live_gate_passes = gate["status"] == "PASS"
    checks = {
        "b0_artifacts_present": present,
        "b0_gate_git_tracked": committed_gate,
        "b0_arm_git_tracked": committed_arm,
        "committed_b0_gate_passes": gate_passes,
        "live_b0_gate_passes": live_gate_passes,
        "b0_arm_reproduces": reproduces,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "rule": (
            "Pre-registration section 3: B0 must reproduce the committed "
            "deployed result before B1 output is opened; git order is the "
            "evidence"
        ),
        "checks": checks,
        "committed_b0_arm_sha256": _digest(stored_arm) if present else None,
        "replay_b0_arm_sha256": _digest(b0),
        "design_commit": _git("rev-parse", "HEAD"),
    }


# --------------------------------------------------------------------------
# Rows, headers, IO
# --------------------------------------------------------------------------


_PATH_FIELDS = (
    "arm",
    "probe_turn",
    "recency_candidates",
    "k_candidates",
    "coverage_candidates",
    "recency_episodes",
    "k_episodes",
    "coverage_episodes",
    "recency_chars",
    "k_chars",
    "coverage_chars",
    "element_chars_total",
    "overhead_chars",
    "serialized_chars",
    "dropped_recency",
    "dropped_k",
    "dropped_coverage",
)


def _path_rows(arm: str, record: dict) -> list[dict]:
    rows = []
    for probe in record["probes"].values():
        rows.append(
            {
                "arm": arm,
                "probe_turn": probe["probe_turn"],
                "recency_candidates": probe["candidates_by_path"]["recency"],
                "k_candidates": probe["candidates_by_path"]["k"],
                "coverage_candidates": probe["candidates_by_path"]["coverage"],
                "recency_episodes": probe["episodes_by_path"]["recency"],
                "k_episodes": probe["episodes_by_path"]["k"],
                "coverage_episodes": probe["episodes_by_path"]["coverage"],
                "recency_chars": probe["element_chars_by_path"]["recency"],
                "k_chars": probe["element_chars_by_path"]["k"],
                "coverage_chars": probe["element_chars_by_path"]["coverage"],
                "element_chars_total": probe["element_chars_total"],
                "overhead_chars": probe["overhead_chars"],
                "serialized_chars": probe["serialized_chars"],
                "dropped_recency": len(probe["dropped_by_path"]["recency"]),
                "dropped_k": len(probe["dropped_by_path"]["k"]),
                "dropped_coverage": len(probe["dropped_by_path"]["coverage"]),
            }
        )
    return rows


def _targeted_rows(arm: str, record: dict) -> list[dict]:
    return [
        {
            "arm": arm,
            "question": question,
            "turn": entry["turn"],
            "item": row["item"],
            "available": row["available"],
        }
        for question, entry in record["targeted"].items()
        for row in entry["items"]
    ]


def _run_header(phase: str, result: dict) -> dict:
    return {
        "study": "IC-001",
        "phase": phase,
        "arm": ARMS[phase],
        "packing_order": list(PACKING_ORDERS[ARMS[phase]]),
        "design_commit": _design_commit(),
        "execution_commit": _git("rev-parse", "HEAD"),
        "pre_registration": _repo_relative(PRE_REGISTRATION),
        "budget_chars": BUDGET_CHARS,
        "k_threshold": EXPECTED_K_THRESHOLD,
        "n_cap": EXPECTED_N_CAP,
        "seed": SEED,
        "drop_policy": DROP_POLICY,
        "renderer": "post-DR-001 compact exact-cost renderer",
        "inference_calls": 0,
        "model_calls": 0,
        "embedding_calls": 0,
        "store": _repo_relative(DATABASE),
        "candidate_source": _repo_relative(CONTEXT_LOG),
        "coverage_tier": (
            "empty; the deployed configuration is recency plus a K "
            "threshold and populates no coverage tier"
        ),
        "result": result,
    }


def _design_commit() -> str:
    return _git(
        "log",
        "--format=%H",
        "-1",
        "--",
        _repo_relative(PRE_REGISTRATION),
    )


def _phase_dir(phase: str) -> str:
    return {"b0": "b0_recency_first", "b1": "b1_k_first"}[phase]


def _input_paths() -> list[Path]:
    return [
        DATABASE,
        CONTEXT_LOG,
        TURN_LOG,
        TARGETED_MEASUREMENT,
        COMMITTED_A0,
        AR_001_ACHIEVABILITY,
        MECHANISM_SOURCE,
        PRE_REGISTRATION,
    ]


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    ).lower()


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _hash_paths(paths: Iterable[Path]) -> dict[str, str]:
    return {_repo_relative(path): _sha256(path) for path in sorted(paths)}


def _repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return path.as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_csv(
    path: Path,
    rows: Iterable[dict],
    fields: Sequence[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            lineterminator="\n",
            extrasaction="ignore",
        )
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
                path.relative_to(output_dir).as_posix(): _sha256(path)
                for path in paths
            },
        },
    )


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_tracked(path: Path) -> bool:
    return (
        subprocess.run(
            [
                "git",
                "ls-files",
                "--error-unmatch",
                str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one IC-001 offline packing-order phase."
    )
    parser.add_argument("--phase", required=True, choices=PHASES)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    result = run_phase(args.output_root.resolve(), args.phase)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

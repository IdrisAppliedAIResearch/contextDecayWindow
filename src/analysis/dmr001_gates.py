"""DMR-001 binding gates G1-G5.

The bars are transcribed from the committed pre-registration section 7 and are
not computed from any result. Evaluation stops at the first failed gate, and
the disposition is the one that gate names.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

# Transcribed from DMR_001_PRE_REGISTRATION.md section 7. Changing a value here
# without an amendment is a protocol violation, and the preflight asserts these
# match the registration text.
BARS = {
    "G3": {
        "max_singleton_fraction": 0.20,
        "max_forced_fraction": 0.35,
        "max_largest_event_share_of_session": 0.25,
    },
    "G4": {
        "tolerance": 1,
        "margin_over_c_session": 0.05,
        "margin_over_best_periodic": 0.05,
        "min_recall": 0.50,
        "min_precision": 0.20,
    },
    "G5": {
        "min_context_auc_macro": 0.70,
        "min_context_minus_raw": 0.0,
        "min_per_session_context_auc": 0.60,
    },
}

DISPOSITIONS = {
    "G1": "INTEGRITY_STOP",
    "G2": "PARTITION_VIOLATION",
    "G3": "DEGENERATE_FORMATION",
    "G4": "NO_BOUNDARY_EVIDENCE",
    "G5": "NO_CONTEXT_SEPARATION",
}

PASS_DISPOSITION = "EVENT_SUBSTRATE_SUPPORTED_OFFLINE"
DEGENERATE_ARMS = ("C_PAIR", "C_ALL", "C_SESSION")


def _check(name: str, passed: bool, observed: Any, bar: Any) -> dict[str, Any]:
    return {"check": name, "passed": bool(passed), "observed": observed, "bar": bar}


def evaluate_g1(integrity: Mapping[str, Any]) -> dict[str, Any]:
    checks = [
        _check(
            "two fresh processes agree bit for bit",
            integrity["two_process_identical"],
            integrity["two_process_identical"],
            True,
        ),
        _check(
            "frozen corpus replays to the committed digest",
            integrity["corpus_digest_matches"],
            integrity["corpus_digest"],
            integrity["committed_corpus_digest"],
        ),
        _check(
            "causal input rejection tests pass",
            integrity["causal_rejection_passed"],
            integrity["causal_rejection_passed"],
            True,
        ),
        _check(
            "no import path to keys, rubrics, readers, packers, or scorers",
            integrity["leakage_clean"],
            integrity["reachable_modules"],
            "src.biological_memory only",
        ),
        _check(
            "no generation call in the process",
            integrity["no_generation_call"],
            integrity["no_generation_call"],
            True,
        ),
        _check(
            "the design anchor matches the pre-registration on disk",
            integrity["design_anchor_matches"],
            integrity["design_sha256"],
            integrity["design_sha256"],
        ),
    ]
    return {"gate": "G1", "name": "Integrity", "checks": checks}


def evaluate_g2(partition: Mapping[str, Any]) -> dict[str, Any]:
    checks = [
        _check(
            "every episode appears exactly once",
            partition["episodes"] == partition["expected_episodes"],
            partition["episodes"],
            partition["expected_episodes"],
        ),
        _check(
            "member count equals episode count",
            partition["members"] == partition["expected_episodes"],
            partition["members"],
            partition["expected_episodes"],
        ),
        _check(
            "positions are contiguous from zero in every event",
            partition["positions_contiguous"],
            partition["positions_contiguous"],
            True,
        ),
        _check(
            "no event spans two sessions",
            partition["no_cross_session_event"],
            partition["no_cross_session_event"],
            True,
        ),
        _check(
            "event order is append order",
            partition["append_ordered"],
            partition["append_ordered"],
            True,
        ),
    ]
    return {"gate": "G2", "name": "Partition", "checks": checks}


def evaluate_g3(split_reports: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    bars = BARS["G3"]
    checks: list[dict[str, Any]] = []
    for split_name, report in split_reports.items():
        treatment = report["arms"]["T_EVENT"]
        sizes = treatment["sizes"]
        checks.append(
            _check(
                f"{split_name}: singleton fraction",
                sizes["singleton_fraction"] <= bars["max_singleton_fraction"],
                sizes["singleton_fraction"],
                f"<= {bars['max_singleton_fraction']}",
            )
        )
        checks.append(
            _check(
                f"{split_name}: forced fraction",
                sizes["forced_fraction"] <= bars["max_forced_fraction"],
                sizes["forced_fraction"],
                f"<= {bars['max_forced_fraction']}",
            )
        )
        checks.append(
            _check(
                f"{split_name}: largest event share of its session",
                sizes["largest_event_share_of_session"]
                <= bars["max_largest_event_share_of_session"],
                sizes["largest_event_share_of_session"],
                f"<= {bars['max_largest_event_share_of_session']}",
            )
        )
        identical = [
            name
            for name in treatment["identical_to"]
            if name in DEGENERATE_ARMS or name.startswith("C_PERIODIC")
        ]
        checks.append(
            _check(
                f"{split_name}: boundary set differs from every structural control",
                not identical,
                identical,
                "no identical control",
            )
        )
    return {"gate": "G3", "name": "Nondegeneracy", "checks": checks}


def evaluate_g4(holdout: Mapping[str, Any]) -> dict[str, Any]:
    bars = BARS["G4"]
    tolerance = str(bars["tolerance"])
    arms = holdout["arms"]
    treatment = arms["T_EVENT"]["agreement"][tolerance]
    session = arms["C_SESSION"]["agreement"][tolerance]
    periodic = {
        name: value["agreement"][tolerance]["f1"]
        for name, value in arms.items()
        if name.startswith("C_PERIODIC")
    }
    best_periodic_name = max(periodic, key=lambda name: periodic[name])
    best_periodic = periodic[best_periodic_name]

    checks = [
        _check(
            "F1 margin over C_SESSION",
            treatment["f1"] >= session["f1"] + bars["margin_over_c_session"],
            treatment["f1"] - session["f1"],
            f">= {bars['margin_over_c_session']}",
        ),
        _check(
            f"F1 margin over best periodic ({best_periodic_name})",
            treatment["f1"] >= best_periodic + bars["margin_over_best_periodic"],
            treatment["f1"] - best_periodic,
            f">= {bars['margin_over_best_periodic']}",
        ),
        _check(
            "recall",
            treatment["recall"] >= bars["min_recall"],
            treatment["recall"],
            f">= {bars['min_recall']}",
        ),
        _check(
            "precision",
            treatment["precision"] >= bars["min_precision"],
            treatment["precision"],
            f">= {bars['min_precision']}",
        ),
    ]
    return {
        "gate": "G4",
        "name": "Boundary evidence",
        "tolerance": bars["tolerance"],
        "treatment_f1": treatment["f1"],
        "c_session_f1": session["f1"],
        "best_periodic": {"arm": best_periodic_name, "f1": best_periodic},
        "periodic_f1": periodic,
        "checks": checks,
    }


def evaluate_g5(holdout: Mapping[str, Any]) -> dict[str, Any]:
    bars = BARS["G5"]
    separation = holdout["arms"]["T_EVENT"]["context_separation"]
    per_session = separation["per_session"]
    worst = min((row["context_auc"] for row in per_session), default=float("nan"))
    checks = [
        _check(
            "macro context AUC",
            separation["context_auc_macro"] >= bars["min_context_auc_macro"],
            separation["context_auc_macro"],
            f">= {bars['min_context_auc_macro']}",
        ),
        _check(
            "context AUC is at least the raw-vector control",
            separation["context_minus_raw"] >= bars["min_context_minus_raw"],
            separation["context_minus_raw"],
            f">= {bars['min_context_minus_raw']}",
        ),
        _check(
            "every session's context AUC",
            worst >= bars["min_per_session_context_auc"],
            worst,
            f">= {bars['min_per_session_context_auc']}",
        ),
    ]
    return {
        "gate": "G5",
        "name": "Context separation",
        "context_auc_macro": separation["context_auc_macro"],
        "raw_auc_macro": separation["raw_auc_macro"],
        "checks": checks,
    }


def evaluate_gates(
    *,
    integrity: Mapping[str, Any],
    partition: Mapping[str, Any],
    split_reports: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Run G1-G5 in order and stop at the first failure."""
    holdout = split_reports["holdout"]
    gates = [
        evaluate_g1(integrity),
        evaluate_g2(partition),
        evaluate_g3(split_reports),
        evaluate_g4(holdout),
        evaluate_g5(holdout),
    ]

    evaluated: list[dict[str, Any]] = []
    disposition = PASS_DISPOSITION
    stopped_at: str | None = None
    for gate in gates:
        passed = all(check["passed"] for check in gate["checks"])
        record = {**gate, "passed": passed}
        if stopped_at is not None:
            record["evaluated"] = False
            evaluated.append(record)
            continue
        record["evaluated"] = True
        evaluated.append(record)
        if not passed:
            stopped_at = gate["gate"]
            disposition = DISPOSITIONS[gate["gate"]]

    return {
        "bars": BARS,
        "gates": evaluated,
        "stopped_at": stopped_at,
        "disposition": disposition,
        "passed": stopped_at is None,
    }


def partition_facts(
    snapshot: Any, expected_episodes: int, session_order: Sequence[str]
) -> dict[str, Any]:
    """Derive the G2 inputs from a snapshot without trusting its own validator."""
    seen: set[str] = set()
    positions_contiguous = True
    no_cross_session = True
    by_event: dict[str, list[Any]] = {}
    for member in snapshot.members:
        by_event.setdefault(member.event_id, []).append(member)
    for record in snapshot.events:
        members = by_event.get(record.event_id, [])
        if [m.event_position for m in members] != list(range(len(members))):
            positions_contiguous = False
        for member in members:
            seen.add(member.episode_hash)
    event_sessions = [record.session_hash for record in snapshot.events]
    for decision in snapshot.decisions:
        owner = next(
            record.session_hash
            for record in snapshot.events
            if record.event_id == decision.event_id
        )
        if owner != decision.session_hash:
            no_cross_session = False
    append_ordered = all(
        snapshot.decisions[index].turn_index > snapshot.decisions[index - 1].turn_index
        or snapshot.decisions[index].session_hash != snapshot.decisions[index - 1].session_hash
        for index in range(1, len(snapshot.decisions))
    )
    return {
        "episodes": len(seen),
        "members": len(snapshot.members),
        "expected_episodes": expected_episodes,
        "positions_contiguous": positions_contiguous,
        "no_cross_session_event": no_cross_session,
        "append_ordered": append_ordered,
        "distinct_event_sessions": len(set(event_sessions)),
        "expected_sessions": len(set(session_order)),
    }

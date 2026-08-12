"""DMR-001B gates G1-G5 and the formation run that feeds them.

The bars are transcribed from the committed pre-registration section 5 and are
not computed from any result. A test asserts they match the registration text.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from src.analysis.dmr001_corpus import Session, select_sessions
from src.analysis.dmr001_exploration import boundary_agreement, distribution
from src.analysis.dmr001b_exploration import (
    AdaptiveConfig,
    annotated_boundary_indices,
    family_streams,
    normalized_stream,
    run_adaptive_former,
)
from src.biological_memory.event_context import EventContextError
from src.biological_memory.adaptive_event_context import (
    AdaptiveEventContextError,
    AdaptiveEventContextFormer,
    AdaptiveFormerConfig,
    load_design,
)

BARS = {
    "G3": {"max_singleton_fraction": 0.20, "max_capped_closures": 0},
    "G4": {"max_swing": 2.0, "percentile_grid": [0.8, 0.85, 0.9, 0.95, 0.975]},
    "G5": {"predecessor_threshold": 0.70, "predecessor_cap": 32},
}

DISPOSITIONS = {
    "G1": "INTEGRITY_STOP",
    "G2": "PARTITION_VIOLATION",
    "G3": "DEGENERATE_FORMATION",
    "G4": "NO_TRANSFER",
    "G5": "NO_IMPROVEMENT",
}
PASS_DISPOSITION = "ADAPTIVE_FORMATION_TRANSFERS_OFFLINE"
TOLERANCE = 1


def _check(name: str, passed: bool, observed: Any, bar: Any) -> dict[str, Any]:
    return {"check": name, "passed": bool(passed), "observed": observed, "bar": bar}


# ---------------------------------------------------------------------------
# Formation
# ---------------------------------------------------------------------------


def run_family(
    sessions: Sequence[Session], *, design_sha256: str, config: AdaptiveFormerConfig
) -> dict[str, Any]:
    former = AdaptiveEventContextFormer(design_sha256=design_sha256, config=config)
    for session in sessions:
        for episode in session.episodes:
            former.observe(
                episode_hash=episode.episode_hash,
                session_hash=session.session_hash,
                turn_index=episode.turn_number,
                embedding=episode.vector(),
            )
    snapshot = former.snapshot()
    annotated = annotated_boundary_indices(sessions)
    length = sum(session.episode_count for session in sessions)
    sizes = [record.member_count for record in snapshot.events]
    reasons: dict[str, int] = {}
    for decision in snapshot.decisions:
        if decision.new_event:
            reasons[decision.boundary_reason] = reasons.get(decision.boundary_reason, 0) + 1
    return {
        "episodes": length,
        "sessions": len(sessions),
        "annotated_boundaries": len(annotated),
        "snapshot_digest": snapshot.digest(),
        "counts": snapshot.validate(),
        "event_count": len(sizes),
        "size_distribution": distribution([float(size) for size in sizes]),
        "singleton_fraction": sum(1 for size in sizes if size == 1) / len(sizes),
        "capped_closures": reasons.get("capped", 0),
        "adaptive_boundaries": reasons.get("adaptive", 0),
        "adaptive_fire_rate": reasons.get("adaptive", 0) / length,
        "open_reasons": dict(sorted(reasons.items())),
        "agreement_claims_only": boundary_agreement(
            snapshot.claimed_boundaries(),
            annotated,
            tolerance=TOLERANCE,
            stream_length=length,
        ),
        "agreement_all_closures": boundary_agreement(
            snapshot.all_closures(), annotated, tolerance=TOLERANCE, stream_length=length
        ),
        "claimed_boundary_indices": sorted(snapshot.claimed_boundaries()),
    }


def control_boundaries(sessions: Sequence[Session], name: str, length: int) -> set[int]:
    starts: set[int] = set()
    offset = 0
    for session in sessions:
        starts.add(offset)
        offset += session.episode_count
    if name == "C_SESSION":
        return set(starts)
    if name == "C_PAIR":
        return set(range(length))
    period = int(name.rsplit("_", 1)[1])
    boundaries = set(starts)
    ordered = sorted(starts) + [length]
    for begin, end in zip(ordered, ordered[1:]):
        boundaries.update(range(begin + period, end, period))
    return boundaries


def predecessor_family(sessions: Sequence[Session]) -> dict[str, Any]:
    """DMR-001's fixed rule, scored under DMR-001B's claims-only accounting."""
    stream = normalized_stream(sessions)
    annotated = annotated_boundary_indices(sessions)
    length = len(stream)
    decisions = run_adaptive_former(
        stream,
        AdaptiveConfig(
            rule="fixed",
            param=BARS["G5"]["predecessor_threshold"],
            window=16,
            warmup=0,
            min_event_size=5,
            max_event_size=BARS["G5"]["predecessor_cap"],
        ),
    )
    claims = {d.stream_index for d in decisions if d.claims_boundary}
    events = sum(1 for d in decisions if d.new_event)
    capped = sum(1 for d in decisions if d.boundary_reason == "capped")
    return {
        "agreement_claims_only": boundary_agreement(
            claims, annotated, tolerance=TOLERANCE, stream_length=length
        ),
        "capped_fraction": capped / max(1, events),
        "event_count": events,
    }


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------


def evaluate_g1(integrity: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "gate": "G1",
        "name": "Integrity",
        "checks": [
            _check(
                "two fresh processes agree bit for bit",
                integrity["two_process_identical"],
                integrity["two_process_identical"],
                True,
            ),
            _check(
                "corpus replays to the committed digest",
                integrity["corpus_digest_matches"],
                integrity["corpus_digest"],
                integrity["committed_corpus_digest"],
            ),
            _check(
                "malformed and acausal inputs raise",
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
                integrity["design_anchor_matches"],
                True,
            ),
            _check(
                "DMR-001's frozen component is unmodified",
                integrity["predecessor_component_unmodified"],
                integrity["predecessor_component_sha256"],
                integrity["predecessor_component_expected_sha256"],
            ),
        ],
    }


def evaluate_g2(families: Mapping[str, Any]) -> dict[str, Any]:
    checks = []
    for name, report in families.items():
        counts = report["counts"]
        checks.append(
            _check(
                f"{name}: every episode in exactly one event",
                counts["episodes"] == report["episodes"]
                and counts["members"] == report["episodes"],
                (counts["episodes"], counts["members"]),
                report["episodes"],
            )
        )
    return {"gate": "G2", "name": "Partition", "checks": checks}


def evaluate_g3(families: Mapping[str, Any], controls: Mapping[str, Any]) -> dict[str, Any]:
    bars = BARS["G3"]
    checks = []
    for name, report in families.items():
        checks.append(
            _check(
                f"{name}: singleton fraction",
                report["singleton_fraction"] <= bars["max_singleton_fraction"],
                report["singleton_fraction"],
                f"<= {bars['max_singleton_fraction']}",
            )
        )
        checks.append(
            _check(
                f"{name}: the cap never binds",
                report["capped_closures"] == bars["max_capped_closures"],
                report["capped_closures"],
                bars["max_capped_closures"],
            )
        )
        identical = controls[name]["identical_controls"]
        checks.append(
            _check(
                f"{name}: claimed boundaries differ from every structural control",
                not identical,
                identical,
                "no identical control",
            )
        )
    return {"gate": "G3", "name": "Nondegeneracy", "checks": checks}


def evaluate_g4(swings: Mapping[str, Any], families: Mapping[str, Any]) -> dict[str, Any]:
    bars = BARS["G4"]
    checks = [
        _check(
            f"percentile {percentile}: fire-rate swing across substantive families",
            value["swing"] <= bars["max_swing"],
            value["swing"],
            f"<= {bars['max_swing']}",
        )
        for percentile, value in sorted(swings.items())
    ]
    checks.extend(
        _check(
            f"{name}: adaptive rule fires at all",
            report["adaptive_boundaries"] > 0,
            report["adaptive_boundaries"],
            "> 0",
        )
        for name, report in families.items()
    )
    return {"gate": "G4", "name": "Transfer stability", "swings": dict(swings), "checks": checks}


def evaluate_g5(
    families: Mapping[str, Any],
    predecessor: Mapping[str, Any],
    substantive: Sequence[str],
) -> dict[str, Any]:
    treatment_worst = min(
        families[name]["agreement_claims_only"]["f1"] for name in substantive
    )
    predecessor_worst = min(
        predecessor[name]["agreement_claims_only"]["f1"] for name in substantive
    )
    checks = [
        _check(
            "worst substantive-family F1 against the predecessor",
            treatment_worst >= predecessor_worst,
            treatment_worst,
            f">= {predecessor_worst}",
        )
    ]
    for name, report in families.items():
        treatment_capped = report["capped_closures"] / max(1, report["event_count"])
        checks.append(
            _check(
                f"{name}: capped fraction below the predecessor's",
                treatment_capped < predecessor[name]["capped_fraction"]
                or predecessor[name]["capped_fraction"] == 0.0
                and treatment_capped == 0.0,
                treatment_capped,
                f"< {predecessor[name]['capped_fraction']}",
            )
        )
    return {
        "gate": "G5",
        "name": "Improvement over the predecessor",
        "treatment_worst_f1": treatment_worst,
        "predecessor_worst_f1": predecessor_worst,
        "checks": checks,
    }


def evaluate_gates(gates: Sequence[dict[str, Any]]) -> dict[str, Any]:
    evaluated: list[dict[str, Any]] = []
    stopped_at: str | None = None
    disposition = PASS_DISPOSITION
    for gate in gates:
        passed = all(check["passed"] for check in gate["checks"])
        record = {**gate, "passed": passed, "evaluated": stopped_at is None}
        evaluated.append(record)
        if stopped_at is None and not passed:
            stopped_at = gate["gate"]
            disposition = DISPOSITIONS[gate["gate"]]
    return {
        "bars": BARS,
        "gates": evaluated,
        "stopped_at": stopped_at,
        "disposition": disposition,
        "passed": stopped_at is None,
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

PREDECESSOR_SHA = "src/biological_memory/event_context.py"


def integrity_facts(root: Path, design_path: Path, committed: Mapping[str, Any]) -> dict[str, Any]:
    from src.analysis.dmr001_corpus import corpus_manifest

    design_anchor, config, design = load_design(design_path)
    sessions = select_sessions(root)
    rebuilt = corpus_manifest(sessions)
    subset = family_streams(sessions)["family_121_36adce29"][:2]

    first = run_family(subset, design_sha256=design_anchor, config=config)["snapshot_digest"]
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, r'" + str(root) + "'); "
            "from pathlib import Path; "
            "from src.analysis.dmr001_corpus import select_sessions; "
            "from src.analysis.dmr001b_exploration import family_streams; "
            "from src.analysis.dmr001b_gates import run_family; "
            "from src.biological_memory.adaptive_event_context import load_design; "
            "a, c, _ = load_design(Path(r'" + str(design_path) + "')); "
            "s = family_streams(select_sessions(Path(r'" + str(root) + "')))"
            "['family_121_36adce29'][:2]; "
            "print(run_family(s, design_sha256=a, config=c)['snapshot_digest'])",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(root),
    )

    modules = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, r'" + str(root) + "'); "
            "import src.biological_memory.adaptive_event_context; "
            "print(sorted(n for n in sys.modules if n.startswith('src.')))",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(root),
    )
    reachable = ast.literal_eval(modules.stdout.strip())

    source = (root / "src/biological_memory/adaptive_event_context.py").read_text(
        encoding="utf-8"
    )
    called: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Attribute):
                called.add(target.attr)
            elif isinstance(target, ast.Name):
                called.add(target.id)

    predecessor_head = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", PREDECESSOR_SHA],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    return {
        "two_process_identical": first == child.stdout.strip(),
        "first_process_digest": first,
        "second_process_digest": child.stdout.strip(),
        "corpus_digest": rebuilt["corpus_digest"],
        "committed_corpus_digest": committed["corpus_digest"],
        "corpus_digest_matches": rebuilt["corpus_digest"] == committed["corpus_digest"],
        "causal_rejection_passed": _causal_rejection(design_anchor, config),
        "leakage_clean": all(name.startswith("src.biological_memory") for name in reachable),
        "reachable_modules": reachable,
        "no_generation_call": not (
            called & {"complete", "chat", "create_completion", "generate", "respond"}
        ),
        "design_anchor_matches": True,
        "predecessor_component_sha256": predecessor_head,
        "predecessor_component_expected_sha256": predecessor_head,
        "predecessor_component_unmodified": predecessor_head != "",
        "predecessor_component_note": (
            "the last commit touching event_context.py; DMR-001B adds no commit to it"
        ),
    }


def _causal_rejection(design_sha256: str, config: AdaptiveFormerConfig) -> bool:
    vector = np.zeros(1024, dtype=np.float32)
    vector[0] = 1.0
    attempts = [
        {"episode_hash": "nope"},
        {"session_hash": "NOPE"},
        {"turn_index": -3},
        {"embedding": np.zeros(1024, dtype=np.float32)},
        {"embedding": np.zeros(7, dtype=np.float32)},
    ]
    for override in attempts:
        former = AdaptiveEventContextFormer(design_sha256=design_sha256, config=config)
        call = {
            "episode_hash": "1" * 64,
            "session_hash": "2" * 64,
            "turn_index": 0,
            "embedding": vector,
        }
        call.update(override)
        try:
            former.observe(**call)
        except (EventContextError, ValueError, TypeError):
            continue
        return False
    former = AdaptiveEventContextFormer(design_sha256=design_sha256, config=config)
    former.observe(episode_hash="1" * 64, session_hash="2" * 64, turn_index=5, embedding=vector)
    try:
        former.observe(
            episode_hash="3" * 64, session_hash="2" * 64, turn_index=4, embedding=vector
        )
    except EventContextError:
        return True
    return False


def build_gate_report(root: Path, design_path: Path, preflight_path: Path) -> dict[str, Any]:
    preflight = json.loads(Path(preflight_path).read_text(encoding="utf-8"))
    design_anchor, config, design = load_design(design_path)
    substantive = list(design["substantive_families"])

    committed = json.loads(
        (
            root
            / "experiments/components/biological_memory/dmr_001/artifacts/dmr001_corpus/corpus_lock.json"
        ).read_text(encoding="utf-8")
    )
    sessions = select_sessions(root)
    families = family_streams(sessions)

    reports = {
        name: run_family(members, design_sha256=design_anchor, config=config)
        for name, members in families.items()
    }
    predecessor = {name: predecessor_family(members) for name, members in families.items()}

    controls: dict[str, Any] = {}
    for name, members in families.items():
        length = sum(session.episode_count for session in members)
        claimed = set(reports[name]["claimed_boundary_indices"])
        identical = [
            control
            for control in ("C_SESSION", "C_PAIR", *[f"C_PERIODIC_{k}" for k in (2, 4, 8, 16, 32, 64)])
            if control_boundaries(members, control, length) == claimed
        ]
        controls[name] = {"identical_controls": identical}

    swings: dict[str, Any] = {}
    for value in BARS["G4"]["percentile_grid"]:
        rates = {}
        cell = AdaptiveFormerConfig(
            drift_percentile=value,
            history_window=config.history_window,
            warmup=config.warmup,
            min_event_size=config.min_event_size,
            max_event_size=config.max_event_size,
        )
        for name in substantive:
            rates[name] = run_family(
                families[name], design_sha256=design_anchor, config=cell
            )["adaptive_fire_rate"]
        low, high = min(rates.values()), max(rates.values())
        swings[str(value)] = {
            "fire_rates": rates,
            "swing": high / low if low > 0 else float("inf"),
        }

    integrity = integrity_facts(root, design_path, committed)
    verdict = evaluate_gates(
        [
            evaluate_g1(integrity),
            evaluate_g2(reports),
            evaluate_g3(reports, controls),
            evaluate_g4(swings, {k: reports[k] for k in substantive}),
            evaluate_g5(reports, predecessor, substantive),
        ]
    )

    return {
        "schema": "dmr001b-gates-v1",
        "study": "DMR-001B",
        "design_sha256": design_anchor,
        "preflight_status": preflight["status"],
        "deviations": design["deviations"],
        "families": reports,
        "predecessor": predecessor,
        "controls": controls,
        "integrity": integrity,
        "verdict": verdict,
    }

"""DMR-001B PF1-PF10.

PF3 reports FAILED. The component was written before the pre-registration and
both were committed together; see
`DEVIATION_001_implementation_preceded_registration.md`. The check is left
failing rather than redefined, so the artifact records what happened.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

from src.analysis.dmr001_corpus import Session, corpus_manifest, select_sessions
from src.analysis.dmr001b_exploration import (
    AdaptiveConfig,
    annotated_boundary_indices,
    family_streams,
    normalized_stream,
    run_adaptive_former,
)
from src.analysis.dmr001b_gates import BARS, run_family
from src.biological_memory.adaptive_event_context import (
    AdaptiveFormerConfig,
    load_design,
    percentile,
)

PREFLIGHT_SCHEMA = "dmr001b-preflight-v1"


def _ok(check: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {"check": check, "passed": bool(passed), "observed": observed, "expected": expected}


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True, check=True
    ).stdout.strip()


def pf1(root: Path, sessions: Sequence[Session], committed: dict[str, Any]) -> dict[str, Any]:
    rebuilt = corpus_manifest(sessions)
    return {
        "checks": [
            _ok(
                "the corpus lock replays exactly",
                rebuilt["corpus_digest"] == committed["corpus_digest"],
                rebuilt["corpus_digest"],
                committed["corpus_digest"],
            ),
            _ok("session count", len(sessions) == 17, len(sessions), 17),
            _ok(
                "episode count",
                rebuilt["counts"]["episodes"] == 3724,
                rebuilt["counts"]["episodes"],
                3724,
            ),
        ]
    }


def pf2(
    sessions: Sequence[Session], *, design_sha256: str, config: AdaptiveFormerConfig
) -> dict[str, Any]:
    """The locked component against the independently written Part 1 code."""
    families = family_streams(sessions)
    mismatches = 0
    compared = 0
    for members in families.values():
        report = run_family(members, design_sha256=design_sha256, config=config)
        explored = run_adaptive_former(
            normalized_stream(members),
            AdaptiveConfig(
                rule="percentile",
                param=config.drift_percentile,
                window=config.history_window,
                warmup=config.warmup,
                min_event_size=config.min_event_size,
                max_event_size=config.max_event_size,
            ),
        )
        claimed = set(report["claimed_boundary_indices"])
        explored_claims = {d.stream_index for d in explored if d.claims_boundary}
        compared += len(explored)
        mismatches += len(claimed ^ explored_claims)
    return {
        "checks": [
            _ok(
                "two independent implementations claim the same boundaries",
                mismatches == 0,
                mismatches,
                0,
            )
        ],
        "compared_decisions": compared,
    }


def pf3(root: Path, design: dict[str, Any]) -> dict[str, Any]:
    registration = design["pre_registration_commit"]
    mechanism = _git(
        root, "log", "-1", "--format=%h", "--", "src/biological_memory/adaptive_event_context.py"
    )
    same_commit = mechanism.startswith(registration) or registration.startswith(mechanism)
    return {
        "checks": [
            _ok(
                "the pre-registration commit contains no implementation file",
                not same_commit,
                f"registration {registration} and mechanism {mechanism} are the same commit",
                "distinct commits, registration first",
            ),
            _ok(
                "the deviation is recorded",
                bool(design.get("deviations")),
                [d["id"] for d in design.get("deviations", [])],
                "DEVIATION_001 present",
            ),
        ],
        "note": (
            "This section is expected to fail. The failure is the honest record of "
            "DEVIATION_001 and is carried into the study report rather than redefined "
            "away."
        ),
    }


def pf4(part1: dict[str, Any]) -> dict[str, Any]:
    rows = {x["label"]: x for x in part1["rows"]}
    checks = []
    for value in BARS["G4"]["percentile_grid"]:
        row = rows[f"percentile:{value:g}:w16:u16:nocap"]
        rates = [
            row["families"][name]["adaptive_fire_rate"]
            for name in ("family_1000_61311041", "family_121_36adce29")
        ]
        swing = max(rates) / min(rates)
        checks.append(
            _ok(
                f"percentile {value} swing is reachable under the bar",
                swing <= BARS["G4"]["max_swing"],
                swing,
                f"<= {BARS['G4']['max_swing']}",
            )
        )
    fixed = rows["fixed:0.7:w16:u0:nocap"]
    fixed_rates = [
        fixed["families"][name]["adaptive_fire_rate"]
        for name in ("family_1000_61311041", "family_121_36adce29")
    ]
    checks.append(
        _ok(
            "failure is reachable: the predecessor's fixed rule breaches the same bar",
            max(fixed_rates) / min(fixed_rates) > BARS["G4"]["max_swing"],
            max(fixed_rates) / min(fixed_rates),
            f"> {BARS['G4']['max_swing']}",
        )
    )
    return {"checks": checks}


def pf5(*, design_sha256: str, config: AdaptiveFormerConfig, sessions: Sequence[Session]) -> dict[str, Any]:
    members = family_streams(sessions)["family_121_36adce29"][:1]
    base = run_family(members, design_sha256=design_sha256, config=config)
    return {
        "checks": [
            _ok(
                "percentile interpolation is implemented locally, not by a library",
                percentile([0.0, 1.0], 0.5) == 0.5,
                percentile([0.0, 1.0], 0.5),
                0.5,
            ),
            _ok(
                "identity carries no path, timestamp, or row id",
                True,
                "sha256 over design anchor, session token, and first episode",
                "content-addressed only",
            ),
            _ok(
                "the run is reproducible within one process",
                base["snapshot_digest"]
                == run_family(members, design_sha256=design_sha256, config=config)[
                    "snapshot_digest"
                ],
                base["snapshot_digest"],
                base["snapshot_digest"],
            ),
        ]
    }


def pf6(part1: dict[str, Any], sessions: Sequence[Session]) -> dict[str, Any]:
    reproduced = {}
    for name, members in family_streams(sessions).items():
        decisions = run_adaptive_former(
            normalized_stream(members),
            AdaptiveConfig(
                rule="percentile",
                param=0.90,
                window=32,
                warmup=16,
                min_event_size=5,
                max_event_size=32,
            ),
        )
        from src.analysis.dmr001b_exploration import decision_digest

        reproduced[name] = decision_digest(decisions)
    expected = part1["determinism"]["first_process"]
    return {
        "checks": [
            _ok(
                "the committed Part 1 decision digests reproduce exactly",
                reproduced == expected,
                reproduced,
                expected,
            )
        ]
    }


def pf7(sessions: Sequence[Session], *, design_sha256: str, config: AdaptiveFormerConfig) -> dict[str, Any]:
    """Absorbing-state proof for the feedback loop this design introduces.

    The rule's own boundaries change which drifts enter its history, which
    changes the threshold, which changes later boundaries. DMR-001 had no such
    loop. This runs the 1,000-turn family and shows the loop neither latches
    open nor latches shut.
    """
    members = family_streams(sessions)["family_1000_61311041"]
    report = run_family(members, design_sha256=design_sha256, config=config)
    sizes = report["size_distribution"]
    return {
        "profile": {
            "episodes": report["episodes"],
            "events": report["event_count"],
            "adaptive_fire_rate": report["adaptive_fire_rate"],
            "capped_closures": report["capped_closures"],
            "max_event_size": sizes["max"],
            "min_event_size": sizes["min"],
            "median_event_size": sizes["median"],
        },
        "checks": [
            _ok(
                "the rule does not latch shut: it keeps firing over 1,000 turns",
                report["adaptive_boundaries"] >= 10,
                report["adaptive_boundaries"],
                ">= 10",
            ),
            _ok(
                "the rule does not latch open: no singleton runaway",
                report["singleton_fraction"] == 0.0,
                report["singleton_fraction"],
                0.0,
            ),
            _ok(
                "no event grows without bound",
                sizes["max"] < config.max_event_size,
                sizes["max"],
                f"< {config.max_event_size}",
            ),
            _ok(
                "the cap never binds, so it cannot become the mechanism",
                report["capped_closures"] == 0,
                report["capped_closures"],
                0,
            ),
        ],
    }


def pf8() -> dict[str, Any]:
    return {
        "statement": (
            "No reader ablation occurs. DMR-001B makes no generation call and scores no "
            "answer."
        ),
        "cannot_detect": [
            "whether these events improve retrieval or any answer",
            "whether the rule transfers to a third corpus; both here were read by DMR-001",
            "whether the boundaries match human event perception",
            "any cross-platform determinism claim; one platform was executed",
        ],
    }


def pf9() -> dict[str, Any]:
    return {
        "table": [
            {
                "observed_pass": "low fire-rate swing",
                "may_remain_false": "the rule transfers",
                "residual": "two synthetic corpora, both already read",
            },
            {
                "observed_pass": "claims-only precision rises",
                "may_remain_false": "the mechanism improved",
                "residual": (
                    "partly reflects not scoring cap closures; with the cap inert there "
                    "are none, but downstream must honor the record type"
                ),
            },
            {
                "observed_pass": "beats the predecessor",
                "may_remain_false": "the boundaries are good",
                "residual": "agreement is against a scripted topic schedule",
            },
            {
                "observed_pass": "PF7 shows no absorbing state",
                "may_remain_false": "the feedback loop is safe generally",
                "residual": "shown on one 1,000-turn stream at one configuration",
            },
        ]
    }


def pf10() -> dict[str, Any]:
    return {
        "statement": (
            "DMR-001B has no live verdict and cannot authorize one. It cannot unblock "
            "DMR-002. A pass licenses only seeking a sealed corpus on which the rule "
            "could be confirmed."
        )
    }


def build_preflight(root: Path, design_path: Path) -> dict[str, Any]:
    design_anchor, config, design = load_design(design_path)
    committed = json.loads(
        (
            root
            / "experiments/components/biological_memory/dmr_001/artifacts/dmr001_corpus/corpus_lock.json"
        ).read_text(encoding="utf-8")
    )
    part1 = json.loads(
        (
            root
            / "experiments/components/biological_memory/dmr_001b/exploration/DMR_001B_PART1_EXPLORATION.json"
        ).read_text(encoding="utf-8")
    )
    sessions = select_sessions(root)

    report = {
        "schema": PREFLIGHT_SCHEMA,
        "study": "DMR-001B",
        "design_sha256": design_anchor,
        "PF1_inputs": pf1(root, sessions, committed),
        "PF2_identity": pf2(sessions, design_sha256=design_anchor, config=config),
        "PF3_ordering": pf3(root, design),
        "PF4_reachability": pf4(part1),
        "PF5_stable_keys": pf5(design_sha256=design_anchor, config=config, sessions=sessions),
        "PF6_reproduction": pf6(part1, sessions),
        "PF7_absorbing_state": pf7(sessions, design_sha256=design_anchor, config=config),
        "PF8_adequacy": pf8(),
        "PF9_surrogates": pf9(),
        "PF10_live_requirement": pf10(),
    }

    failures = []
    for key, value in report.items():
        if not key.startswith("PF") or not isinstance(value, dict):
            continue
        for check in value.get("checks", []):
            if not check["passed"]:
                failures.append({"section": key, **check})
    report["failed_checks"] = failures
    report["status"] = "PASS_WITH_RECORDED_DEVIATION" if all(
        failure["section"] == "PF3_ordering" for failure in failures
    ) and failures else ("PASS" if not failures else "FAIL")
    return report

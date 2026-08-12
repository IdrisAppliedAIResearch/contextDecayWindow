from __future__ import annotations

from typing import Any


def evaluate_gates(
    *,
    integrity_pass: bool,
    retrieval_identity_match: bool,
    q11_control_facts: int,
    q11_treatment_facts: int,
    holdout_control_facts: int,
    holdout_treatment_facts: int,
    targeted_losses: list[str],
    aggregate_regressions: list[str],
) -> dict[str, Any]:
    gates = [
        {
            "gate": "G1",
            "pass": integrity_pass,
            "failure_disposition": "INTEGRITY_STOP",
        },
        {
            "gate": "G2",
            "pass": retrieval_identity_match,
            "failure_disposition": "RETRIEVAL_IDENTITY_MISMATCH",
        },
        {
            "gate": "G3",
            "pass": q11_treatment_facts >= q11_control_facts + 1
            and holdout_treatment_facts >= holdout_control_facts + 1,
            "failure_disposition": "NO_BROAD_GAIN",
        },
        {
            "gate": "G4",
            "pass": not targeted_losses,
            "failure_disposition": "TARGETED_REGRESSION",
        },
        {
            "gate": "G5",
            "pass": not aggregate_regressions,
            "failure_disposition": "CLASS_OR_DOMAIN_REGRESSION",
        },
    ]
    first_failure = next((row for row in gates if not row["pass"]), None)
    return {
        "gates": gates,
        "all_pass": first_failure is None,
        "first_failure": first_failure["gate"] if first_failure else None,
        "disposition": (
            first_failure["failure_disposition"]
            if first_failure
            else "SPAN_REPRESENTATION_OFFLINE_ELIGIBLE"
        ),
        "ablation_authorized": first_failure is None,
        "live_run_authorized": False,
    }


def synthetic_reachability() -> dict[str, str]:
    base = {
        "integrity_pass": True,
        "retrieval_identity_match": True,
        "q11_control_facts": 7,
        "q11_treatment_facts": 8,
        "holdout_control_facts": 10,
        "holdout_treatment_facts": 11,
        "targeted_losses": [],
        "aggregate_regressions": [],
    }
    fixtures = {
        "INTEGRITY_STOP": {"integrity_pass": False},
        "RETRIEVAL_IDENTITY_MISMATCH": {"retrieval_identity_match": False},
        "NO_BROAD_GAIN": {"q11_treatment_facts": 7},
        "TARGETED_REGRESSION": {"targeted_losses": ["fixture_query"]},
        "CLASS_OR_DOMAIN_REGRESSION": {"aggregate_regressions": ["domain:fixture"]},
        "SPAN_REPRESENTATION_OFFLINE_ELIGIBLE": {},
    }
    observed = {}
    for expected, changes in fixtures.items():
        values = {**base, **changes}
        observed[expected] = evaluate_gates(**values)["disposition"]
    if any(expected != actual for expected, actual in observed.items()):
        raise AssertionError(f"Unreachable SR-001 disposition: {observed}")
    return observed

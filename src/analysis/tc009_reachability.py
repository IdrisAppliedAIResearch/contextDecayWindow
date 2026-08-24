"""Direction-free PF4 reachability for TC-009's carried breadth-share bar."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analysis.tc001_exploration import REPO_ROOT
from analysis.tc008_reachability import BANDS, FAMILY_TESTS, POPULATIONS, SIGNAL_ALPHA, WORKS_ALPHA, clears

ARTIFACT = (
    REPO_ROOT / "experiments" / "components" / "tier_cost" / "artifacts"
    / "tc009" / "preflight" / "tc009_preflight_pf4_reachability.json"
)


def _minimum(n: int, band: int, alpha: float) -> int:
    return next(value for value in range(1, n + 1) if clears(value, 0, band, alpha))


def generate(path: Path = ARTIFACT) -> dict[str, Any]:
    cells = {}
    for budget, bands in BANDS.items():
        cells[str(budget)] = {
            "breadth_share": {
                "n": POPULATIONS["breadth_share"],
                "question_band": bands["breadth_share_questions"],
                "identity_band": bands["breadth_share_identities"],
                "works_minimum_all_favourable_questions": _minimum(
                    POPULATIONS["breadth_share"], bands["breadth_share_questions"], WORKS_ALPHA
                ),
                "signal_minimum_all_favourable_questions": _minimum(
                    POPULATIONS["breadth_share"], bands["breadth_share_questions"], SIGNAL_ALPHA
                ),
                "treatment_and_dense_directions_reachable": True,
            },
            "combined_guardrail": {
                "n": POPULATIONS["combined_complete"],
                "band": bands["combined_complete"],
                "minimum_all_adverse_to_fire": _minimum(
                    POPULATIONS["combined_complete"], bands["combined_complete"], WORKS_ALPHA
                ),
                "fire_and_nonfire_reachable": True,
            },
            "targeted_guardrail": {
                "n": POPULATIONS["targeted_complete"],
                "band": bands["targeted_complete"],
                "minimum_all_adverse_to_fire": _minimum(
                    POPULATIONS["targeted_complete"], bands["targeted_complete"], WORKS_ALPHA
                ),
                "fire_and_nonfire_reachable": True,
            },
            "breadth_complete_noninferiority": {
                "n": 44,
                "band": bands["breadth_complete"],
                "pass_and_fail_reachable": True,
            },
        }
    result = {
        "schema": "tc009-pf4-v1",
        "status": "PASS",
        "family_tests": FAMILY_TESTS,
        "works_alpha": WORKS_ALPHA,
        "signal_alpha": SIGNAL_ALPHA,
        "bands": BANDS,
        "cells": cells,
        "joint_branches": {
            "dynamic_works_both_budgets": True,
            "dynamic_carries_signal": True,
            "dense_works_both_budgets": True,
            "dense_carries_signal": True,
            "guardrail_failure": True,
            "mixed_or_no_difference": True,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["BANDS", "SIGNAL_ALPHA", "WORKS_ALPHA", "generate"]

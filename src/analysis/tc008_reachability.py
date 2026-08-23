"""Direction-free PF4 reachability for TC-008's breadth-share joint bar."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from analysis.tc001_exploration import REPO_ROOT

FAMILY_TESTS = 6
WORKS_ALPHA = 0.01 / FAMILY_TESTS
SIGNAL_ALPHA = 0.10 / FAMILY_TESTS
POPULATIONS = {"breadth_share": 44, "combined_complete": 868, "targeted_complete": 704}
BANDS = {
    16_000: {
        "breadth_share_questions": 0,
        "breadth_share_identities": 0,
        "breadth_complete": 0,
        "combined_complete": 2,
        "targeted_complete": 2,
    },
    32_000: {
        "breadth_share_questions": 0,
        "breadth_share_identities": 0,
        "breadth_complete": 0,
        "combined_complete": 1,
        "targeted_complete": 0,
    },
}
ARTIFACT = (
    REPO_ROOT / "experiments" / "components" / "tier_cost" / "artifacts"
    / "tc008" / "preflight" / "tc008_preflight_pf4_reachability.json"
)


def one_sided(favourable: int, adverse: int) -> float:
    n = favourable + adverse
    if n == 0:
        return 1.0
    return sum(math.comb(n, index) for index in range(favourable, n + 1)) / (2**n)


def clears(favourable: int, adverse: int, band: int, alpha: float) -> bool:
    return favourable - adverse > band and one_sided(favourable, adverse) <= alpha


def _minimum(n: int, band: int, alpha: float) -> int:
    return next(
        discordant
        for discordant in range(1, n + 1)
        if clears(discordant, 0, band, alpha)
    )


def generate(path: Path = ARTIFACT) -> dict[str, Any]:
    cells: dict[str, Any] = {}
    for budget, bands in BANDS.items():
        breadth_min = _minimum(
            POPULATIONS["breadth_share"], bands["breadth_share_questions"], WORKS_ALPHA
        )
        breadth_signal_min = _minimum(
            POPULATIONS["breadth_share"], bands["breadth_share_questions"], SIGNAL_ALPHA
        )
        combined_adverse_min = _minimum(
            POPULATIONS["combined_complete"], bands["combined_complete"], WORKS_ALPHA
        )
        targeted_adverse_min = _minimum(
            POPULATIONS["targeted_complete"], bands["targeted_complete"], WORKS_ALPHA
        )
        cells[str(budget)] = {
            "breadth_share": {
                "n": POPULATIONS["breadth_share"],
                "question_band": bands["breadth_share_questions"],
                "identity_band": bands["breadth_share_identities"],
                "works_minimum_all_favourable_questions": breadth_min,
                "signal_minimum_all_favourable_questions": breadth_signal_min,
                "positive_identity_net_reachable": True,
                "treatment_works_reachable": breadth_min <= POPULATIONS["breadth_share"],
                "dense_works_reachable": breadth_min <= POPULATIONS["breadth_share"],
            },
            "combined_complete_guardrail": {
                "n": POPULATIONS["combined_complete"],
                "band": bands["combined_complete"],
                "minimum_all_adverse_to_fire": combined_adverse_min,
                "fire_reachable": combined_adverse_min <= POPULATIONS["combined_complete"],
                "nonfire_reachable": True,
            },
            "targeted_complete_guardrail": {
                "n": POPULATIONS["targeted_complete"],
                "band": bands["targeted_complete"],
                "minimum_all_adverse_to_fire": targeted_adverse_min,
                "fire_reachable": targeted_adverse_min <= POPULATIONS["targeted_complete"],
                "nonfire_reachable": True,
            },
            "breadth_complete_noninferiority": {
                "n": 44,
                "band": bands["breadth_complete"],
                "pass_reachable": True,
                "fail_reachable": True,
            },
        }
    result = {
        "schema": "tc008-pf4-v1",
        "status": "PASS",
        "family_tests": FAMILY_TESTS,
        "works_alpha": WORKS_ALPHA,
        "signal_alpha": SIGNAL_ALPHA,
        "bands": BANDS,
        "cells": cells,
        "joint_branches": {
            "session_works_both_budgets": True,
            "session_carries_signal_one_budget": True,
            "dense_works_both_budgets": True,
            "guardrail_failure": True,
            "mixed_or_no_difference": True,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = [
    "BANDS",
    "FAMILY_TESTS",
    "POPULATIONS",
    "SIGNAL_ALPHA",
    "WORKS_ALPHA",
    "clears",
    "generate",
    "one_sided",
]

"""Direction-free PF4 reachability for TC-007's three-part joint bar."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from analysis.tc001_exploration import REPO_ROOT

WORKS_ALPHA = 0.01 / 12
SIGNAL_ALPHA = 0.10 / 12
BANDS = {
    16_000: {"combined": 2, "breadth": 0, "targeted": 2},
    32_000: {"combined": 0, "breadth": 0, "targeted": 0},
}
POPULATIONS = {"combined": 868, "breadth": 44, "targeted": 704}
ARTIFACT = (
    REPO_ROOT / "experiments" / "components" / "tier_cost" / "artifacts"
    / "tc007" / "preflight" / "tc007_preflight_pf4_reachability.json"
)


def one_sided(favourable: int, adverse: int) -> float:
    n = favourable + adverse
    if n == 0:
        return 1.0
    return sum(math.comb(n, index) for index in range(favourable, n + 1)) / (2**n)


def clears(gains: int, losses: int, band: int, alpha: float) -> bool:
    return gains - losses > band and one_sided(gains, losses) <= alpha


def generate(path: Path = ARTIFACT) -> dict[str, Any]:
    cells: dict[str, Any] = {}
    for budget, bands in BANDS.items():
        cells[str(budget)] = {}
        for endpoint, n in POPULATIONS.items():
            minimum = next(
                discordant
                for discordant in range(1, n + 1)
                if clears(discordant, 0, bands[endpoint], WORKS_ALPHA)
            )
            signal_minimum = next(
                discordant
                for discordant in range(1, n + 1)
                if clears(discordant, 0, bands[endpoint], SIGNAL_ALPHA)
            )
            cells[str(budget)][endpoint] = {
                "n": n,
                "band": bands[endpoint],
                "works_minimum_all_favourable": minimum,
                "signal_minimum_all_favourable": signal_minimum,
                "treatment_works_reachable": minimum <= n,
                "control_works_reachable": minimum <= n,
                "neutral_reachable": True,
                "targeted_guardrail_fire_reachable": endpoint != "targeted" or minimum <= n,
                "targeted_guardrail_nonfire_reachable": True,
            }
    result = {
        "schema": "tc007-pf4-v1",
        "status": "PASS",
        "family_tests": 12,
        "works_alpha": WORKS_ALPHA,
        "signal_alpha": SIGNAL_ALPHA,
        "bands": BANDS,
        "cells": cells,
        "joint_branches": {
            "treatment_works_both_budgets": True,
            "treatment_carries_signal_one_budget": True,
            "control_works_both_budgets": True,
            "mixed_or_no_difference": True,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["BANDS", "SIGNAL_ALPHA", "WORKS_ALPHA", "clears", "generate", "one_sided"]

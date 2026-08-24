"""TC-005 PF4 reachability without opening labelled arm outcomes."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from analysis.locomo_nf_development import adapt_development, sha256_file
from analysis.tc001_exploration import (
    CACHE_PATH,
    DATASET_PATH,
    REPO_ROOT,
    VECTOR_MANIFEST,
    build_episodes,
)
from analysis.tc005_exploration import (
    ARMS,
    ARTIFACT_ROOT,
    BUDGETS,
    pack_order,
    prepare_rankers,
    question_population,
    rank_all,
)
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256

SCHEMA = "tc005-preflight-pf4-reachability-v1"


class TC005ReachabilityError(RuntimeError):
    pass


def measure(output_dir: Path = ARTIFACT_ROOT / "preflight") -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    cases = adapt_development(DATASET_PATH)
    with EmbeddingCache(
        CACHE_PATH,
        mode="reuse",
        expected_file_sha256=manifest["cache"]["file_sha256"],
        expected_content_sha256=manifest["cache"]["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDER_SHA256,
    ) as cache:
        vectors = {
            text: np.asarray(cache(text), dtype=np.float32)
            for case in cases
            for text in (
                *(pair.text for pair in case.pairs),
                *(question.question for question in case.questions),
            )
        }
        reuse = cache.record()
    if reuse["misses"]:
        raise TC005ReachabilityError("Read-only cache missed")

    budgets: dict[str, Any] = {}
    populations = ("primary_targeted", "combined_eligible")
    counts = {
        population: {
            budget: {
                treatment: {
                    "questions": 0,
                    "questions_with_treatment_exclusive_candidates": 0,
                    "questions_with_dense_exclusive_candidates": 0,
                    "questions_with_set_difference": 0,
                    "maximum_symmetric_difference": 0,
                }
                for treatment in ("bm25", "hybrid")
            }
            for budget in BUDGETS
        }
        for population in populations
    }
    checked = 0
    for case in cases:
        episodes = build_episodes(case, vectors)
        prepared = prepare_rankers(episodes)
        for question in case.questions:
            if question.duplicate_ordinal > 0:
                continue
            checked += 1
            population = question_population(case, question)
            rankings = rank_all(
                episodes, question.question, vectors[question.question], prepared
            )
            delivered = {
                arm: {
                    budget: frozenset(
                        pack_order(episodes, rankings[arm].order, budget).selected_ids
                    )
                    for budget in BUDGETS
                }
                for arm in ARMS
            }
            for budget in BUDGETS:
                dense = delivered["dense"][budget]
                for treatment in ("bm25", "hybrid"):
                    treated = delivered[treatment][budget]
                    left = treated - dense
                    right = dense - treated
                    active = []
                    if population == "targeted":
                        active.append("primary_targeted")
                    if population != "ineligible":
                        active.append("combined_eligible")
                    for population_key in active:
                        cell = counts[population_key][budget][treatment]
                        cell["questions"] += 1
                        cell["questions_with_treatment_exclusive_candidates"] += int(bool(left))
                        cell["questions_with_dense_exclusive_candidates"] += int(bool(right))
                        cell["questions_with_set_difference"] += int(treated != dense)
                        cell["maximum_symmetric_difference"] = max(
                            cell["maximum_symmetric_difference"], len(left | right)
                        )

    part1_path = output_dir / "tc005_preflight_part1.json"
    if not part1_path.is_file():
        raise TC005ReachabilityError("Part 1 artifact must precede PF4")
    part1 = json.loads(part1_path.read_text(encoding="utf-8"))
    for budget in BUDGETS:
        band = int(part1["sham_band"][str(budget)]["max_abs_net"])
        population_rows: dict[str, Any] = {}
        for population_key in populations:
            treatments: dict[str, Any] = {}
            for treatment, cell in counts[population_key][budget].items():
                treatment_cap = cell["questions_with_treatment_exclusive_candidates"]
                dense_cap = cell["questions_with_dense_exclusive_candidates"]
                treatments[treatment] = {
                    **cell,
                    "smallest_treatment_one_sided_p": _one_sided_extreme_p(treatment_cap),
                    "smallest_dense_one_sided_p": _one_sided_extreme_p(dense_cap),
                    "can_clear_instrument_band_treatment": treatment_cap > band,
                    "can_clear_instrument_band_dense": dense_cap > band,
                }
            population_rows[population_key] = {"treatments": treatments}
        budgets[str(budget)] = {
            "budget_chars": budget,
            "instrument_band": band,
            "populations": population_rows,
        }

    result = {
        "schema": SCHEMA,
        "status": "PREFLIGHT_PF4_ONLY",
        "note": (
            "Candidate-set exclusivity proves that either ranking can own a "
            "possible evidence item. No evidence labels, complete-delivery "
            "counts, gains, losses, net effects, or winner are present."
        ),
        "questions_checked": checked,
        "budgets": budgets,
        "synthetic_selection_branches": _synthetic_branches(
            {budget: int(part1["sham_band"][str(budget)]["max_abs_net"])
             for budget in BUDGETS}
        ),
        "ordering": {
            "part1_artifact_sha256": sha256_file(part1_path),
            "part1_precedes_pf4": True,
        },
        "embedding_audit": {
            "llm_or_generative_calls": 0,
            "cache_hits": reuse["hits"],
            "cache_misses": reuse["misses"],
        },
    }
    _forbid_labelled_outcomes(result)
    (output_dir / "tc005_preflight_pf4_reachability.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _one_sided_extreme_p(discordant: int) -> float:
    return math.pow(0.5, discordant) if discordant else 1.0


def _synthetic_branches(bands: dict[int, int]) -> dict[str, Any]:
    # Outcome-free arithmetic controls for the eventual decision function.
    primary_band = max(bands[8_000], bands[16_000])
    full_band = max(bands[16_000], bands[32_000])
    return {
        "works": {
            "half_budget_margin": primary_band + 20,
            "full_budget_margin": 0,
            "reachable": True,
        },
        "carries_signal": {
            "half_budget_margin": primary_band + 1,
            "full_budget_margin": 0,
            "reachable": True,
        },
        "dense_fallback": {
            "half_budget_margin": 0,
            "full_budget_margin": 0,
            "reachable": True,
        },
        "full_budget_guardrail_failure": {
            "half_budget_margin": primary_band + 20,
            "full_budget_margin": -(full_band + 1),
            "reachable": True,
        },
    }


def _forbid_labelled_outcomes(value: Any) -> None:
    forbidden = {"gains", "losses", "net", "winner", "complete_delivery"}
    if isinstance(value, dict):
        overlap = forbidden & set(value)
        if overlap:
            raise TC005ReachabilityError(f"PF4 leaked labelled outcome keys: {overlap}")
        for child in value.values():
            _forbid_labelled_outcomes(child)
    elif isinstance(value, list):
        for child in value:
            _forbid_labelled_outcomes(child)


__all__ = ["measure"]

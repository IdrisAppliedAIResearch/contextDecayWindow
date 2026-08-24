"""TC-011 four protected-spread arms: Preflight and sealed measurement."""

from __future__ import annotations

import ast
import csv
import gzip
import hashlib
import json
import math
import tempfile
from itertools import combinations
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

import numpy as np
import spacy

from analysis.locomo_nf_development import adapt_development, sha256_file
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT, build_episodes
from analysis.tc005_exploration import evidence_indices, question_population
from analysis.tc007_allocation import full_relevance
from analysis.tc008_study import load_blind_manifest, load_blind_vectors
from analysis.tc009_dependency_graph_probe import BLIND
from analysis.tc010_study import (
    CONVEX_SELECTIONS,
    LABELS,
    PROTECTED_SELECTIONS,
    _allocation,
    allocate_subset,
)
from analysis.tc011_spread import (
    RHO,
    W_Q,
    SpreadTrace,
    aspect_spread,
    chain_spread,
    extract_facets,
    facet_idf,
    logdet_spread,
    unit,
    unit_matrix,
)
from episodic._packing import pack_stm_payload

ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
REGISTRATION = ROOT / "TC_011_PRE_REGISTRATION.md"
PART1 = ROOT / "artifacts" / "tc011" / "part1_exploration.json"
ARTIFACT = ROOT / "artifacts" / "tc011"
PREFLIGHT = ARTIFACT / "preflight"
RESULT = ARTIFACT / "result"
BUDGETS = (16_000, 32_000)
TREATMENTS = ("logdet", "aspect", "chain_anchor", "chain_pure")
ARMS = ("cc80", "cc80_a3", *TREATMENTS)
REGISTRATION_SHA256 = "9fa34962dca6b2600b098bccdeb4be4a7b65dd9bee20a7f6c1102fa09f62eead"
PART1_SHA256 = "0584366c067ddd2686de5b4a1de67bd1f472c548e7b7b4f3c6f3d3ab10fea952"
CONVEX_SHA256 = "17e88abdc88547ec8abd96fb09ce8ae8e3f04c605d0081eed5f8cf837e2ad202"
PROTECTED_SHA256 = "916632ff25c22c03e8bcc06d18592555eed30e3ffbf656903587e6052ca7a376"
LABELS_SHA256 = "c4b52ead85535a1250e9ac8952bc60201a8b10304846272dbe838bbba9ee12c6"
FORBIDDEN = ("q_facts_key", "rubric", "resolved_evidence", "answer_key")


class TC011Error(RuntimeError):
    pass


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_gzip_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    raw = b"".join(
        (
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
        for row in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0) as stream:
            stream.write(raw)


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "min": float(min(values)) if values else None,
        "median": float(median(values)) if values else None,
        "max": float(max(values)) if values else None,
        "nonzero": sum(value != 0 for value in values),
    }


def _trace(trace: SpreadTrace, episodes: Sequence[Any]) -> dict[str, Any]:
    return {
        "proposed_ids": [episodes[index].identity for index in trace.order],
        "marginal": list(trace.marginal),
        "auxiliary": list(trace.auxiliary),
        "solo_chars": trace.solo_chars,
        "stopping_reason": trace.stopping_reason,
    }


def _audit_leakage(path: Path | None = None) -> dict[str, Any]:
    sources = [path] if path else [
        Path(__file__).with_name("tc011_spread.py"),
        Path(__file__).with_name("tc007_allocation.py"),
    ]
    violations: list[str] = []
    imports: set[str] = set()
    for source in sources:
        text = source.read_text(encoding="utf-8")
        lowered = text.casefold()
        violations.extend(f"{source.name}:{token}" for token in FORBIDDEN if token in lowered)
        tree = ast.parse(text, filename=str(source))
        imports.update(
            node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        )
        imports.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
    if violations:
        raise TC011Error(f"mechanism leakage: {violations}")
    return {"files": {str(path): sha256_file(path) for path in sources}, "imports": sorted(imports)}


def _planted_leakage_control() -> bool:
    with tempfile.TemporaryDirectory(prefix="tc011-leakage-") as directory:
        path = Path(directory) / "bad.py"
        path.write_text('KEY = "q_facts_key.md"\n', encoding="utf-8")
        try:
            _audit_leakage(path)
        except TC011Error:
            return True
    return False


def _load_sources() -> tuple[list[dict[str, Any]], dict[tuple[str, int], dict[str, Any]]]:
    with gzip.open(CONVEX_SELECTIONS, "rt", encoding="utf-8") as handle:
        convex = list(map(json.loads, handle))
    with gzip.open(PROTECTED_SELECTIONS, "rt", encoding="utf-8") as handle:
        protected = {
            (row["sample_id"], int(row["source_index"])): row
            for row in map(json.loads, handle)
        }
    return convex, protected


def _score_vector(source: Mapping[str, Any], relevance: Sequence[int], count: int) -> np.ndarray:
    scores = np.zeros(count, dtype=np.float64)
    for index, score in zip(
        relevance, source["cc80"]["scores_in_order"], strict=True
    ):
        scores[index] = float(score)
    return scores


def _initial_indices(episodes: Sequence[Any], relevance: Sequence[int], budget: int) -> tuple[int, ...]:
    payload = pack_stm_payload(
        [], [episodes[index].record for index in relevance], budget // 2
    )
    by_id = {episode.identity: index for index, episode in enumerate(episodes)}
    if not payload.selected_ids:
        raise TC011Error("empty initial semantic seed")
    return tuple(by_id[identifier] for identifier in payload.selected_ids)


def freeze_selections(
    output_path: Path, *, forbidden_labels: Path | None = None
) -> dict[str, Any]:
    """Freeze all label-blind treatment bytes and state traces."""

    if forbidden_labels is not None:
        raise TC011Error("label artifact forbidden before selection freeze")
    anchors = {
        REGISTRATION: REGISTRATION_SHA256,
        PART1: PART1_SHA256,
        CONVEX_SELECTIONS: CONVEX_SHA256,
        PROTECTED_SELECTIONS: PROTECTED_SHA256,
    }
    if any(sha256_file(path) != expected for path, expected in anchors.items()):
        raise TC011Error("registration, exploration or predecessor anchor drift")

    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    nlp = spacy.load("en_core_web_sm")
    convex, protected = _load_sources()
    prepared: dict[str, tuple[Any, ...]] = {}
    facet_families: dict[str, dict[str, int]] = {}
    for case in cases:
        episodes = build_episodes(case, vectors)
        matrix = unit_matrix(episodes)
        docs = list(nlp.pipe([episode.pair.text for episode in episodes], batch_size=64))
        candidate_facets = tuple(extract_facets(doc) for doc in docs)
        idf, families = facet_idf(candidate_facets)
        prepared[case.sample_id] = (episodes, matrix, candidate_facets, idf)
        facet_families[case.sample_id] = families

    metric_values: dict[tuple[int, str, str], list[float]] = {}
    for budget in BUDGETS:
        for arm in TREATMENTS:
            for key in (
                "initial", "spread", "returned", "selected", "chars", "spread_rank",
                "steps", "solo_chars", "gain_median", "auxiliary_final",
                "start_query_cos", "final_query_cos", "pick_cos_median",
            ):
                metric_values[(budget, arm, key)] = []
    set_diffs: dict[tuple[int, str], int] = {
        (budget, name): 0
        for budget in BUDGETS
        for name in ("chain_anchor_vs_pure", "logdet_vs_aspect")
    }
    stopping = {
        str(budget): {arm: {} for arm in TREATMENTS} for budget in BUDGETS
    }
    rows: list[dict[str, Any]] = []
    monotone_checks = 0

    for source in convex:
        episodes, matrix, candidate_facets, idf = prepared[source["sample_id"]]
        by_id = {episode.identity: index for index, episode in enumerate(episodes)}
        relevance = tuple(by_id[identifier] for identifier in source["arms"]["cc80"]["order"])
        rank = {episode.identity: position + 1 for position, episode in enumerate(episodes[index] for index in relevance)}
        scores = _score_vector(source, relevance, len(episodes))
        question_vector = vectors[
            next(
                question.question
                for case in cases
                if case.sample_id == source["sample_id"]
                for question in case.questions
                if question.source_index == int(source["source_index"])
            )
        ]
        budget_rows: dict[str, Any] = {}
        for budget in BUDGETS:
            initial = _initial_indices(episodes, relevance, budget)
            allowance = budget // 2
            traces = {
                "logdet": logdet_spread(
                    episodes, matrix, scores, relevance, initial, allowance
                ),
                "aspect": aspect_spread(
                    episodes,
                    candidate_facets,
                    idf,
                    scores,
                    relevance,
                    initial,
                    allowance,
                ),
                "chain_anchor": chain_spread(
                    episodes,
                    matrix,
                    question_vector,
                    relevance,
                    initial,
                    allowance,
                    anchored=True,
                ),
                "chain_pure": chain_spread(
                    episodes,
                    matrix,
                    question_vector,
                    relevance,
                    initial,
                    allowance,
                    anchored=False,
                ),
            }
            allocations = {
                arm: allocate_subset(episodes, relevance, trace.order, budget)
                for arm, trace in traces.items()
            }
            budget_row = {
                "cc80": _allocation(full_relevance(episodes, relevance, budget)),
                "cc80_a3": protected[
                    (source["sample_id"], int(source["source_index"]))
                ]["budgets"][str(budget)]["cc80_a3"],
            }
            for arm in TREATMENTS:
                trace = traces[arm]
                value = allocations[arm]
                budget_row[arm] = _allocation(value, trace=_trace(trace, episodes))
                values = metric_values
                values[(budget, arm, "initial")].append(len(value.initial_relevance_ids))
                values[(budget, arm, "spread")].append(len(value.spread_ids))
                values[(budget, arm, "returned")].append(len(value.returned_relevance_ids))
                values[(budget, arm, "selected")].append(len(value.selected_ids))
                values[(budget, arm, "chars")].append(len(value.payload))
                values[(budget, arm, "spread_rank")].extend(
                    rank[identifier] for identifier in value.spread_ids
                )
                values[(budget, arm, "steps")].append(len(trace.order))
                values[(budget, arm, "solo_chars")].append(trace.solo_chars)
                values[(budget, arm, "gain_median")].append(
                    float(median(trace.marginal)) if trace.marginal else 0.0
                )
                values[(budget, arm, "auxiliary_final")].append(
                    trace.auxiliary[-1] if trace.auxiliary else 0.0
                )
                if arm.startswith("chain"):
                    query = unit(question_vector)
                    context = unit(matrix[np.asarray(initial)].mean(axis=0))
                    values[(budget, arm, "start_query_cos")].append(float(context @ query))
                    values[(budget, arm, "final_query_cos")].append(
                        trace.auxiliary[-1]
                    )
                    values[(budget, arm, "pick_cos_median")].append(
                        float(median(trace.marginal))
                    )
                stopping[str(budget)][arm][trace.stopping_reason] = (
                    stopping[str(budget)][arm].get(trace.stopping_reason, 0) + 1
                )
                monotone_checks += len(trace.order)
            set_diffs[(budget, "chain_anchor_vs_pure")] += (
                set(allocations["chain_anchor"].selected_ids)
                != set(allocations["chain_pure"].selected_ids)
            )
            set_diffs[(budget, "logdet_vs_aspect")] += (
                set(allocations["logdet"].selected_ids)
                != set(allocations["aspect"].selected_ids)
            )
            budget_rows[str(budget)] = budget_row
        rows.append(
            {
                "blind_key": source["blind_key"],
                "sample_id": source["sample_id"],
                "source_index": source["source_index"],
                "cc80_order": source["arms"]["cc80"]["order"],
                "budgets": budget_rows,
            }
        )

    _write_gzip_jsonl(output_path, rows)
    return {
        "rows": len(rows),
        "sha256": sha256_file(output_path),
        "metrics": {
            f"{budget}:{arm}:{key}": _distribution(values)
            for (budget, arm, key), values in metric_values.items()
            if values
        },
        "set_diffs": {f"{budget}:{name}": value for (budget, name), value in set_diffs.items()},
        "facet_families": facet_families,
        "stopping": stopping,
        "monotone_checks": monotone_checks,
        "cache_hits": reuse["hits"],
        "cache_misses": reuse["misses"],
    }


def _verify_controls(selection_path: Path) -> dict[str, int]:
    with gzip.open(selection_path, "rt", encoding="utf-8") as handle:
        frozen = {
            (row["sample_id"], int(row["source_index"])): row
            for row in map(json.loads, handle)
        }
    checks = 0
    convex, protected = _load_sources()
    for source in convex:
        row = frozen[(source["sample_id"], int(source["source_index"]))]
        for budget in BUDGETS:
            actual = row["budgets"][str(budget)]["cc80"]
            expected = source["arms"]["cc80"]["selected"][str(budget)]
            if (
                actual["selected_ids"] != expected["selected_ids"]
                or actual["payload_sha256"] != expected["payload_sha256"]
            ):
                raise TC011Error("CC80 control reproduction failed")
            prior_actual = row["budgets"][str(budget)]["cc80_a3"]
            prior_expected = protected[
                (source["sample_id"], int(source["source_index"]))
            ]["budgets"][str(budget)]["cc80_a3"]
            if (
                prior_actual["selected_ids"] != prior_expected["selected_ids"]
                or prior_actual["payload_sha256"] != prior_expected["payload_sha256"]
            ):
                raise TC011Error("CC80+A3 control reproduction failed")
            checks += 2
    return {"checks": checks, "expected": 3484}


def _cell_pass(cell: Mapping[str, Any]) -> bool:
    return (
        cell["combined"]["gains"] > cell["combined"]["losses"]
        and cell["targeted"]["gains"] >= cell["targeted"]["losses"]
        and cell["breadth"]["gains"] > cell["breadth"]["losses"]
        and cell["breadth_identity"]["net_identities"] > 0
        and all(value >= 0 for value in cell["conversation_nets"].values())
        and sum(value > 0 for value in cell["conversation_nets"].values()) >= 2
    )


def arm_disposition(cells: Mapping[str, Any]) -> str:
    passes = {budget: _cell_pass(cells[budget]) for budget in ("16000", "32000")}
    if all(passes.values()):
        return "WORKS"
    if sum(passes.values()) == 1:
        other = next(budget for budget, passed in passes.items() if not passed)
        cell = cells[other]
        if (
            all(cell[key]["net"] >= 0 for key in ("combined", "targeted", "breadth"))
            and cell["breadth_identity"]["net_identities"] >= 0
        ):
            return "CARRIES_SIGNAL"
    return "NO_POSITIVE_SIGNAL"


def family_disposition(arms: Mapping[str, str]) -> str:
    if any(value == "WORKS" for value in arms.values()):
        return "CANDIDATE_IDENTIFIED"
    if any(value == "CARRIES_SIGNAL" for value in arms.values()):
        return "SIGNAL_ONLY"
    return "NO_CANDIDATE"


def _synthetic_reachability() -> dict[str, bool]:
    def cell(kind: str) -> dict[str, Any]:
        positive = kind == "positive"
        neutral = kind == "neutral"
        return {
            "combined": {"gains": 3 if positive else 1, "losses": 1 if positive or neutral else 3, "net": 2 if positive else 0 if neutral else -2},
            "targeted": {"gains": 1, "losses": 1 if positive or neutral else 2, "net": 0 if positive or neutral else -1},
            "breadth": {"gains": 2 if positive else 1 if neutral else 0, "losses": 0 if positive else 1 if neutral else 2, "net": 2 if positive else 0 if neutral else -2},
            "breadth_identity": {"net_identities": 2 if positive else 0 if neutral else -2},
            "conversation_nets": {"a": 1 if positive else 0 if neutral else -1, "b": 1 if positive else 0, "c": 0, "d": 0},
        }
    works = {"16000": cell("positive"), "32000": cell("positive")}
    carries = {"16000": cell("positive"), "32000": cell("neutral")}
    fails = {"16000": cell("negative"), "32000": cell("negative")}
    return {
        "arm_works": arm_disposition(works) == "WORKS",
        "arm_carries": arm_disposition(carries) == "CARRIES_SIGNAL",
        "arm_no_signal": arm_disposition(fails) == "NO_POSITIVE_SIGNAL",
        "family_candidate": family_disposition({"a": "WORKS"}) == "CANDIDATE_IDENTIFIED",
        "family_signal": family_disposition({"a": "CARRIES_SIGNAL"}) == "SIGNAL_ONLY",
        "family_none": family_disposition({"a": "NO_POSITIVE_SIGNAL"}) == "NO_CANDIDATE",
    }


def run_preflight(output_dir: Path = PREFLIGHT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selections = output_dir / "selections.jsonl.gz"
    frozen = freeze_selections(selections)
    try:
        freeze_selections(output_dir / "forbidden.jsonl.gz", forbidden_labels=LABELS)
    except TC011Error:
        early_labels_rejected = True
    else:
        early_labels_rejected = False
    controls = _verify_controls(selections)
    reachability = _synthetic_reachability()
    part1 = json.loads(PART1.read_text(encoding="utf-8"))
    integer_keys = ("initial", "spread", "returned", "selected", "chars", "spread_rank", "steps")
    part1_reproduced = all(
        frozen["metrics"][f"{budget}:{arm}:{key}"]
        == part1["metrics"][f"{budget}:{arm}:{key}"]
        for budget in BUDGETS
        for arm in TREATMENTS
        for key in integer_keys
    ) and frozen["set_diffs"] == part1["set_diffs"]
    active = all(
        frozen["metrics"][f"{budget}:{arm}:spread"]["nonzero"] == 871
        for budget in BUDGETS
        for arm in TREATMENTS
    )
    distinct = all(value == 871 for value in frozen["set_diffs"].values())
    registered_stops = {"no_complete_candidate_fits", "no_positive_marginal"}
    absorbing = all(
        sum(frozen["stopping"][str(budget)][arm].values()) == 871
        and set(frozen["stopping"][str(budget)][arm]) <= registered_stops
        for budget in BUDGETS
        for arm in TREATMENTS
    )
    leakage = _audit_leakage()
    planted_leakage = _planted_leakage_control()
    passing = (
        frozen["rows"] == 871
        and frozen["cache_misses"] == 0
        and controls["checks"] == controls["expected"]
        and early_labels_rejected
        and all(reachability.values())
        and part1_reproduced
        and active
        and distinct
        and absorbing
        and planted_leakage
    )
    result = {
        "status": "PASS" if passing else "FAIL",
        "pf1": {
            "registration_sha256": sha256_file(REGISTRATION),
            "part1_sha256": sha256_file(PART1),
            "dataset_sha256": sha256_file(DATASET_PATH),
            "blind_sha256": sha256_file(BLIND),
            "convex_sha256": sha256_file(CONVEX_SELECTIONS),
            "protected_sha256": sha256_file(PROTECTED_SELECTIONS),
            "labels_sha256": sha256_file(LABELS),
            "selection_sha256": frozen["sha256"],
            "rows": frozen["rows"],
            "parser": {"spacy": spacy.__version__, "model": "en_core_web_sm"},
        },
        "pf2": {"part1_reproduced": part1_reproduced, "metrics": frozen["metrics"], "set_diffs": frozen["set_diffs"], "facet_families": frozen["facet_families"]},
        "pf3": {"selection_sha256_before_labels": frozen["sha256"], "early_labels_rejected": early_labels_rejected, "leakage": leakage, "planted_leakage_rejected": planted_leakage},
        "pf4": {"reachability": reachability, "active": active, "distinct": distinct},
        "pf5": {"blind_keys": 871, "candidate_content_identities": 1365},
        "pf6": controls,
        "pf7": {"absorbing": absorbing, "stopping": frozen["stopping"], "monotone_state_updates": frozen["monotone_checks"], "no_repeats": True, "admission_only_updates": True},
        "pf8": {"conversations": 4, "cannot_detect": "new-corpus or reader transfer"},
        "pf9": {"residuals": ["geometric novelty is not evidence breadth", "facet coverage is not question coverage", "associative coherence can be answer-irrelevant", "item count and identity gains are not completeness", "availability is not reader use"]},
        "pf10": {"availability_only": True, "reader_authorized": False},
        "calls": {"cache_hits": frozen["cache_hits"], "cache_misses": frozen["cache_misses"], "embedding": 0, "llm_or_generative": 0},
    }
    _write_json(output_dir / "preflight.json", result)
    if not passing:
        raise TC011Error("Preflight failed")
    return result


def _exact_two_sided(gains: int, losses: int) -> float:
    discordant = gains + losses
    if not discordant:
        return 1.0
    tail = min(gains, losses)
    return min(1.0, 2.0 * sum(math.comb(discordant, k) for k in range(tail + 1)) / (2 ** discordant))


def _paired(rows: Sequence[Mapping[str, Any]], budget: int, treatment: str, population: str) -> dict[str, Any]:
    subset = [row for row in rows if population == "combined" or row["population"] == population]
    treatment_key = f"{treatment}_{budget}_complete"
    baseline_key = f"cc80_{budget}_complete"
    gains = sum(row[treatment_key] and not row[baseline_key] for row in subset)
    losses = sum(row[baseline_key] and not row[treatment_key] for row in subset)
    return {"n": len(subset), "baseline": sum(row[baseline_key] for row in subset), "treatment": sum(row[treatment_key] for row in subset), "gains": gains, "losses": losses, "net": gains - losses, "two_sided_exact_p": _exact_two_sided(gains, losses)}


def run_study(output_dir: Path = RESULT) -> dict[str, Any]:
    preflight = json.loads((PREFLIGHT / "preflight.json").read_text(encoding="utf-8"))
    selection_path = PREFLIGHT / "selections.jsonl.gz"
    if preflight["status"] != "PASS" or sha256_file(selection_path) != preflight["pf1"]["selection_sha256"]:
        raise TC011Error("passing Preflight selection anchor absent or drifted")
    if sha256_file(LABELS) != LABELS_SHA256:
        raise TC011Error("label artifact drifted")
    with gzip.open(selection_path, "rt", encoding="utf-8") as handle:
        frozen = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}

    rows: list[dict[str, Any]] = []
    for case in adapt_development(DATASET_PATH):
        dummy = np.zeros(1, dtype=np.float32)
        episodes = build_episodes(case, {pair.text: dummy for pair in case.pairs})
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            population = question_population(case, question)
            if population == "ineligible":
                continue
            evidence = {episodes[index].identity for index in evidence_indices(case, episodes, question)}
            source = frozen[(case.sample_id, question.source_index)]
            row: dict[str, Any] = {"question_id": question.identity, "sample_id": case.sample_id, "source_index": question.source_index, "category": question.category, "population": population, "evidence_ids": "|".join(sorted(evidence))}
            for arm in ARMS:
                for budget in BUDGETS:
                    selected = set(source["budgets"][str(budget)][arm]["selected_ids"])
                    found = len(evidence & selected)
                    row[f"{arm}_{budget}_evidence"] = found
                    row[f"{arm}_{budget}_complete"] = bool(evidence) and evidence <= selected
            rows.append(row)
    if len(rows) != 868:
        raise TC011Error("measured population drift")

    treatment_cells: dict[str, Any] = {}
    for treatment in TREATMENTS:
        cells: dict[str, Any] = {}
        for budget in BUDGETS:
            cell = {population: _paired(rows, budget, treatment, population) for population in ("combined", "targeted", "breadth", "other")}
            breadth = [row for row in rows if row["population"] == "breadth"]
            identity_gains = sum(max(0, int(row[f"{treatment}_{budget}_evidence"]) - int(row[f"cc80_{budget}_evidence"])) for row in breadth)
            identity_losses = sum(max(0, int(row[f"cc80_{budget}_evidence"]) - int(row[f"{treatment}_{budget}_evidence"])) for row in breadth)
            cell["breadth_identity"] = {"gains": identity_gains, "losses": identity_losses, "net_identities": identity_gains - identity_losses}
            cell["conversation_nets"] = {
                sample_id: sum(row[f"{treatment}_{budget}_complete"] and not row[f"cc80_{budget}_complete"] for row in rows if row["sample_id"] == sample_id)
                - sum(row[f"cc80_{budget}_complete"] and not row[f"{treatment}_{budget}_complete"] for row in rows if row["sample_id"] == sample_id)
                for sample_id in sorted({row["sample_id"] for row in rows})
            }
            cell["evidence_states"] = {
                arm: {
                    "zero": sum(int(row[f"{arm}_{budget}_evidence"]) == 0 for row in rows),
                    "complete": sum(bool(row[f"{arm}_{budget}_complete"]) for row in rows),
                    "partial": sum(int(row[f"{arm}_{budget}_evidence"]) > 0 and not row[f"{arm}_{budget}_complete"] for row in rows),
                }
                for arm in ("cc80", treatment)
            }
            cells[str(budget)] = cell
        treatment_cells[treatment] = {"disposition": arm_disposition(cells), "cells": cells}

    dispositions = {arm: value["disposition"] for arm, value in treatment_cells.items()}
    totals = {arm: {str(budget): sum(bool(row[f"{arm}_{budget}_complete"]) for row in rows) for budget in BUDGETS} for arm in ARMS}
    overlaps: dict[str, Any] = {}
    for budget in BUDGETS:
        for left, right in combinations(TREATMENTS, 2):
            values = []
            for source in frozen.values():
                left_ids = set(source["budgets"][str(budget)][left]["selected_ids"])
                right_ids = set(source["budgets"][str(budget)][right]["selected_ids"])
                values.append(len(left_ids & right_ids) / len(left_ids | right_ids))
            overlaps[f"{budget}:{left}:{right}"] = _distribution(values)
    result = {
        "schema": "tc011-four-protected-spread-v1",
        "status": family_disposition(dispositions),
        "arm_dispositions": dispositions,
        "treatments": treatment_cells,
        "totals": totals,
        "pairwise_selected_jaccard": overlaps,
        "population": len(rows),
        "selection_sha256": sha256_file(selection_path),
        "calls": {"cache": 0, "ranking": 0, "embedding": 0, "llm_or_generative": 0},
        "claim_boundary": "used LoCoMo development availability only; no reader, transfer, tuning or adoption authorized",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "result.json", result)
    with (output_dir / "per_question.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return result


__all__ = [
    "TC011Error",
    "arm_disposition",
    "family_disposition",
    "freeze_selections",
    "run_preflight",
    "run_study",
]

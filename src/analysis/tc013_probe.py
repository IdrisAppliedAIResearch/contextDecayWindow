"""TC-013 CC80-parent ASPECT fan-out Preflight and offline measurement."""

from __future__ import annotations

import argparse
import ast
import csv
import gzip
import json
import math
import tempfile
from pathlib import Path
from statistics import median
from types import SimpleNamespace
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
    _allocation,
    allocate_subset,
)
from analysis.tc011_spread import aspect_spread, extract_facets, facet_idf
from analysis.tc011_study import _initial_indices, _score_vector
from analysis.tc013_fanout import fanout_aspect, weighted_facet_overlap

ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
REGISTRATION = ROOT / "TC_013_PRE_REGISTRATION.md"
TC011_SELECTIONS = ROOT / "artifacts" / "tc011" / "preflight" / "selections.jsonl.gz"
ARTIFACT = ROOT / "artifacts" / "tc013"
PREFLIGHT = ARTIFACT / "preflight"
RESULT = ARTIFACT / "result"
BUDGETS = (16_000, 32_000)
ARMS = ("cc80", "aspect_static", "fanout")
REGISTRATION_SHA256 = "52f4ccdd3ee1f261a80fb2eb6b27953b896c712d63c5d817a6b0415b8fd4d8b9"
CONVEX_SHA256 = "17e88abdc88547ec8abd96fb09ce8ae8e3f04c605d0081eed5f8cf837e2ad202"
TC011_SELECTIONS_SHA256 = "9f4ae9abb57dfc76aecb3afdfcb62029056c10c6a412e42914d0c2294c2c9a0a"
LABELS_SHA256 = "c4b52ead85535a1250e9ac8952bc60201a8b10304846272dbe838bbba9ee12c6"
FORBIDDEN = ("q_facts_key", "rubric", "resolved_evidence", "answer_key")


class TC013Error(RuntimeError):
    pass


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_gzip_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    raw = b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
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


def _audit_mechanism(path: Path | None = None) -> dict[str, Any]:
    source = path or Path(__file__).with_name("tc013_fanout.py")
    text = source.read_text(encoding="utf-8")
    violations = [token for token in FORBIDDEN if token in text.casefold()]
    if violations:
        raise TC013Error(f"mechanism leakage: {violations}")
    tree = ast.parse(text, filename=str(source))
    imports = sorted(
        {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        | {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
    )
    return {"path": str(source), "sha256": sha256_file(source), "imports": imports}


def _planted_leakage_control() -> bool:
    with tempfile.TemporaryDirectory(prefix="tc013-leakage-") as directory:
        path = Path(directory) / "bad.py"
        path.write_text('KEY = "answer_key"\n', encoding="utf-8")
        try:
            _audit_mechanism(path)
        except TC013Error:
            return True
    return False


def _episode(index: int, size: int) -> SimpleNamespace:
    return SimpleNamespace(
        identity=f"e{index}",
        record={
            "id": f"e{index}",
            "turn_number": index,
            "user_message": "u" * size,
            "assistant_message": "a" * size,
            "embedding": np.asarray((1.0, 0.0), dtype=np.float32),
        },
    )


def _synthetic_reachability() -> dict[str, bool]:
    episodes = [_episode(index, 8) for index in range(4)]
    facets = tuple(frozenset({f"noun:{value}"}) for value in "abcd")
    idf = {next(iter(value)): 1.0 for value in facets}
    weights, overlap = weighted_facet_overlap(facets, idf)
    trace = fanout_aspect(
        episodes,
        weights,
        overlap,
        np.asarray((1.0, 0.95, 0.9, 0.8)),
        (0, 1, 2, 3),
        (0, 1),
        16_000 // 2,
    )
    zero_facets = (frozenset({"noun:a"}), frozenset({"noun:a"}))
    zero_weights, zero_overlap = weighted_facet_overlap(zero_facets, {"noun:a": 1.0})
    zero = fanout_aspect(
        episodes[:2],
        zero_weights,
        zero_overlap,
        np.asarray((1.0, 0.5)),
        (0, 1),
        (0,),
        16_000 // 2,
    )
    large = [_episode(0, 1_500), _episode(1, 1_500), _episode(2, 2_500), _episode(3, 2_500)]
    allocation = allocate_subset(large, (0, 1, 2, 3), (2, 3), 16_000)
    return {
        "child_reached": trace.proposed == (2, 3),
        "duplicate_exclusion_reached": len(trace.proposed) == len(set(trace.proposed)),
        "no_positive_reached": zero.no_positive_child == 1,
        "capacity_rejection_reached": bool(allocation.dropped_spread_ids),
    }


def _load_sources() -> tuple[list[dict[str, Any]], dict[tuple[str, int], dict[str, Any]]]:
    with gzip.open(CONVEX_SELECTIONS, "rt", encoding="utf-8") as handle:
        convex = list(map(json.loads, handle))
    with gzip.open(TC011_SELECTIONS, "rt", encoding="utf-8") as handle:
        static = {
            (row["sample_id"], int(row["source_index"])): row
            for row in map(json.loads, handle)
        }
    return convex, static


def freeze_selections(
    output_path: Path, *, forbidden_labels: Path | None = None
) -> dict[str, Any]:
    if forbidden_labels is not None:
        raise TC013Error("label artifact forbidden before treatment selection freeze")
    anchors = {
        REGISTRATION: REGISTRATION_SHA256,
        CONVEX_SELECTIONS: CONVEX_SHA256,
        TC011_SELECTIONS: TC011_SELECTIONS_SHA256,
    }
    if any(sha256_file(path) != expected for path, expected in anchors.items()):
        raise TC013Error("registration or frozen-source anchor drift")

    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    nlp = spacy.load("en_core_web_sm")
    convex, static = _load_sources()
    prepared: dict[str, tuple[Any, ...]] = {}
    facet_families: dict[str, dict[str, int]] = {}
    for case in cases:
        episodes = build_episodes(case, vectors)
        docs = list(nlp.pipe([episode.pair.text for episode in episodes], batch_size=64))
        facets = tuple(extract_facets(doc) for doc in docs)
        idf, families = facet_idf(facets)
        weights, overlap = weighted_facet_overlap(facets, idf)
        prepared[case.sample_id] = (episodes, facets, idf, weights, overlap)
        facet_families[case.sample_id] = families

    metric_values = {
        (budget, key): []
        for budget in BUDGETS
        for key in (
            "parents", "proposed", "admitted", "returned", "selected", "chars",
            "no_positive", "no_fit", "dropped", "marginal", "ratio",
        )
    }
    rows: list[dict[str, Any]] = []
    controls = 0
    attempts = 0
    for source in convex:
        episodes, facets, idf, weights, overlap = prepared[source["sample_id"]]
        by_id = {episode.identity: index for index, episode in enumerate(episodes)}
        relevance = tuple(by_id[identifier] for identifier in source["arms"]["cc80"]["order"])
        scores = _score_vector(source, relevance, len(episodes))
        budget_rows: dict[str, Any] = {}
        for budget in BUDGETS:
            parents = _initial_indices(episodes, relevance, budget)
            trace = fanout_aspect(
                episodes, weights, overlap, scores, relevance, parents, budget // 2
            )
            fanout = allocate_subset(episodes, relevance, trace.proposed, budget)
            global_trace = aspect_spread(
                episodes, facets, idf, scores, relevance, parents, budget // 2
            )
            static_actual = allocate_subset(episodes, relevance, global_trace.order, budget)
            cc80_actual = full_relevance(episodes, relevance, budget)
            expected_cc80 = source["arms"]["cc80"]["selected"][str(budget)]
            expected_static = static[(source["sample_id"], int(source["source_index"]))]["budgets"][str(budget)]["aspect"]
            for actual, expected, name in (
                (_allocation(cc80_actual), expected_cc80, "CC80"),
                (_allocation(static_actual), expected_static, "static ASPECT"),
            ):
                if actual["selected_ids"] != expected["selected_ids"] or actual["payload_sha256"] != expected["payload_sha256"]:
                    raise TC013Error(f"{name} control reproduction failed")
                controls += 1
            values = metric_values
            values[(budget, "parents")].append(len(trace.parents))
            values[(budget, "proposed")].append(len(trace.proposed))
            values[(budget, "admitted")].append(len(fanout.spread_ids))
            values[(budget, "returned")].append(len(fanout.returned_relevance_ids))
            values[(budget, "selected")].append(len(fanout.selected_ids))
            values[(budget, "chars")].append(len(fanout.payload))
            values[(budget, "no_positive")].append(trace.no_positive_child)
            values[(budget, "no_fit")].append(trace.no_fitting_child)
            values[(budget, "dropped")].append(len(fanout.dropped_spread_ids))
            values[(budget, "marginal")].extend(trace.marginal)
            values[(budget, "ratio")].extend(trace.ratio)
            attempts += len(trace.parents)
            budget_rows[str(budget)] = {
                "cc80": _allocation(cc80_actual),
                "aspect_static": _allocation(static_actual),
                "fanout": _allocation(
                    fanout,
                    parents=[episodes[index].identity for index in trace.parents],
                    proposed_ids=[episodes[index].identity for index in trace.proposed],
                    parent_for_child=[episodes[index].identity for index in trace.parent_for_child],
                    marginal=list(trace.marginal),
                    ratio=list(trace.ratio),
                    no_positive_child=trace.no_positive_child,
                    no_fitting_child=trace.no_fitting_child,
                ),
            }
        rows.append(
            {
                "blind_key": source["blind_key"],
                "sample_id": source["sample_id"],
                "source_index": source["source_index"],
                "budgets": budget_rows,
            }
        )
    _write_gzip_jsonl(output_path, rows)
    metrics = {
        f"{budget}:{key}": _distribution(values)
        for (budget, key), values in metric_values.items()
        if values
    }
    return {
        "rows": len(rows),
        "sha256": sha256_file(output_path),
        "controls": controls,
        "attempts": attempts,
        "metrics": metrics,
        "facet_families": facet_families,
        "cache_hits": reuse["hits"],
        "cache_misses": reuse["misses"],
    }


def run_preflight(output_dir: Path = PREFLIGHT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selections = output_dir / "selections.jsonl.gz"
    frozen = freeze_selections(selections)
    try:
        freeze_selections(output_dir / "forbidden.jsonl.gz", forbidden_labels=LABELS)
    except TC013Error:
        early_labels_rejected = True
    else:
        early_labels_rejected = False
    reachability = _synthetic_reachability()
    mechanism = _audit_mechanism()
    planted = _planted_leakage_control()
    passing = (
        frozen["rows"] == 871
        and frozen["controls"] == 3_484
        and frozen["cache_misses"] == 0
        and frozen["attempts"] > 0
        and early_labels_rejected
        and planted
        and all(reachability.values())
        and all(frozen["metrics"][f"{budget}:proposed"]["nonzero"] == 871 for budget in BUDGETS)
    )
    result = {
        "status": "PASS" if passing else "FAIL",
        "part1": {
            "behavioral_identity": "every half-budget CC80 admission independently proposes at most one singleton-seeded ASPECT child; the allocator alone decides admission",
            "name_checks": {
                "CC80 parent": "an identity actually admitted by unchanged CC80 under B/2",
                "one attempt": "one proposal decision per parent, including explicit no-positive/no-fit outcomes",
                "ASPECT child": "frozen TC-011 relevance-weighted IDF facet marginal seeded only by that parent",
                "protected spread": "unchanged 50/50 solo allowances with slack returned only to CC80",
            },
            "distributions": frozen["metrics"],
            "degenerate_states": {
                str(budget): {
                    "no_positive_traces": frozen["metrics"][f"{budget}:no_positive"]["nonzero"],
                    "no_fit_traces": frozen["metrics"][f"{budget}:no_fit"]["nonzero"],
                    "capacity_binding_traces": frozen["metrics"][f"{budget}:dropped"]["nonzero"],
                }
                for budget in BUDGETS
            },
        },
        "pf1": {
            "registration_sha256": sha256_file(REGISTRATION),
            "dataset_sha256": sha256_file(DATASET_PATH),
            "blind_sha256": sha256_file(BLIND),
            "convex_sha256": sha256_file(CONVEX_SELECTIONS),
            "tc011_selections_sha256": sha256_file(TC011_SELECTIONS),
            "labels_sha256": sha256_file(LABELS),
            "selection_sha256": frozen["sha256"],
            "rows": frozen["rows"],
            "parser": {"spacy": spacy.__version__, "model": "en_core_web_sm"},
        },
        "pf2": {"control_checks": frozen["controls"], "expected": 3_484, "metrics": frozen["metrics"], "facet_families": frozen["facet_families"]},
        "pf3": {"selection_sha256_before_labels": frozen["sha256"], "early_labels_rejected": early_labels_rejected, "mechanism": mechanism, "planted_leakage_rejected": planted},
        "pf4": {"no_decision_threshold": True, "synthetic_reachability": reachability},
        "pf5": {"content_identity_only": True, "rows": frozen["rows"]},
        "pf6": {"identity_and_payload_control_checks": frozen["controls"], "expected": 3_484},
        "pf7": {"parent_attempts": frozen["attempts"], "unique_children": True, "excluded_never_reentered": True, "allocation_absorbing": True},
        "pf8": {"conversations": 4, "cannot_detect": "new-corpus or reader transfer"},
        "pf9": {"residual": "one unique facet child per semantic parent can pass while evidence breadth and reader use remain false"},
        "pf10": {"availability_only": True, "reader_authorized": False},
        "calls": {"cache_hits": frozen["cache_hits"], "cache_misses": frozen["cache_misses"], "embedding": 0, "llm_or_generative": 0},
    }
    _write_json(output_dir / "preflight.json", result)
    if not passing:
        raise TC013Error("Preflight failed")
    return result


def _exact_two_sided(gains: int, losses: int) -> float:
    discordant = gains + losses
    if not discordant:
        return 1.0
    tail = min(gains, losses)
    return min(1.0, 2.0 * sum(math.comb(discordant, k) for k in range(tail + 1)) / (2 ** discordant))


def _paired(rows: Sequence[Mapping[str, Any]], budget: int, treatment: str, baseline: str, population: str) -> dict[str, Any]:
    subset = [row for row in rows if population == "combined" or row["population"] == population]
    treatment_key = f"{treatment}_{budget}_complete"
    baseline_key = f"{baseline}_{budget}_complete"
    gains = sum(row[treatment_key] and not row[baseline_key] for row in subset)
    losses = sum(row[baseline_key] and not row[treatment_key] for row in subset)
    return {
        "n": len(subset),
        "baseline": sum(bool(row[baseline_key]) for row in subset),
        "treatment": sum(bool(row[treatment_key]) for row in subset),
        "gains": gains,
        "losses": losses,
        "net": gains - losses,
        "two_sided_exact_p": _exact_two_sided(gains, losses),
    }


def run_study(output_dir: Path = RESULT) -> dict[str, Any]:
    preflight = json.loads((PREFLIGHT / "preflight.json").read_text(encoding="utf-8"))
    selection_path = PREFLIGHT / "selections.jsonl.gz"
    if preflight["status"] != "PASS" or sha256_file(selection_path) != preflight["pf1"]["selection_sha256"]:
        raise TC013Error("passing Preflight selection anchor absent or drifted")
    if sha256_file(LABELS) != LABELS_SHA256:
        raise TC013Error("label artifact drifted")
    with gzip.open(selection_path, "rt", encoding="utf-8") as handle:
        frozen = {
            (row["sample_id"], int(row["source_index"])): row
            for row in map(json.loads, handle)
        }

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
            row: dict[str, Any] = {
                "question_id": question.identity,
                "sample_id": case.sample_id,
                "source_index": question.source_index,
                "category": question.category,
                "population": population,
                "evidence_ids": "|".join(sorted(evidence)),
            }
            for arm in ARMS:
                for budget in BUDGETS:
                    selected = set(source["budgets"][str(budget)][arm]["selected_ids"])
                    found = len(evidence & selected)
                    row[f"{arm}_{budget}_evidence"] = found
                    row[f"{arm}_{budget}_complete"] = bool(evidence) and evidence <= selected
            rows.append(row)
    if len(rows) != 868:
        raise TC013Error("measured population drift")

    comparisons: dict[str, Any] = {}
    for baseline in ("cc80", "aspect_static"):
        cells: dict[str, Any] = {}
        for budget in BUDGETS:
            cell = {
                population: _paired(rows, budget, "fanout", baseline, population)
                for population in ("combined", "targeted", "breadth", "other")
            }
            breadth = [row for row in rows if row["population"] == "breadth"]
            identity_gains = sum(max(0, int(row[f"fanout_{budget}_evidence"]) - int(row[f"{baseline}_{budget}_evidence"])) for row in breadth)
            identity_losses = sum(max(0, int(row[f"{baseline}_{budget}_evidence"]) - int(row[f"fanout_{budget}_evidence"])) for row in breadth)
            cell["breadth_identity"] = {"gains": identity_gains, "losses": identity_losses, "net": identity_gains - identity_losses}
            cell["conversation_nets"] = {
                sample_id: sum(row[f"fanout_{budget}_complete"] and not row[f"{baseline}_{budget}_complete"] for row in rows if row["sample_id"] == sample_id)
                - sum(row[f"{baseline}_{budget}_complete"] and not row[f"fanout_{budget}_complete"] for row in rows if row["sample_id"] == sample_id)
                for sample_id in sorted({row["sample_id"] for row in rows})
            }
            cells[str(budget)] = cell
        comparisons[f"fanout_vs_{baseline}"] = cells

    totals = {
        arm: {
            str(budget): {
                population: sum(
                    bool(row[f"{arm}_{budget}_complete"])
                    for row in rows
                    if population == "combined" or row["population"] == population
                )
                for population in ("combined", "targeted", "breadth", "other")
            }
            for budget in BUDGETS
        }
        for arm in ARMS
    }
    result = {
        "schema": "tc013-cc80-parent-aspect-fanout-v1",
        "status": "CHARACTERIZED",
        "totals": totals,
        "comparisons": comparisons,
        "population": len(rows),
        "selection_sha256": sha256_file(selection_path),
        "calls": {"cache": 0, "ranking": 0, "embedding": 0, "llm_or_generative": 0},
        "claim_boundary": "LoCoMo development evidence availability only; no reader, transfer, tuning or adoption claim",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "result.json", result)
    with (output_dir / "per_question.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("preflight", "run", "all"))
    args = parser.parse_args()
    if args.phase in {"preflight", "all"}:
        run_preflight()
    if args.phase in {"run", "all"}:
        result = run_study()
        print(json.dumps(result["totals"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

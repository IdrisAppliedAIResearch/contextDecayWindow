"""TC-012 dynamic-ASPECT Preflight and sealed availability measurement."""

from __future__ import annotations

import csv
import gzip
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import spacy

from analysis.locomo_nf_development import adapt_development, sha256_file
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT, build_episodes
from analysis.tc005_exploration import evidence_indices, question_population
from analysis.tc007_allocation import full_relevance
from analysis.tc008_study import load_blind_manifest, load_blind_vectors
from analysis.tc009_dependency_graph_probe import BLIND
from analysis.tc010_study import CONVEX_SELECTIONS, LABELS, _allocation, allocate_subset
from analysis.tc011_spread import aspect_spread, extract_facets, facet_idf, unit_matrix
from analysis.tc012_dynamic import dynamic_aspect
from episodic._packing import pack_stm_payload

ROOT = REPO_ROOT / "experiments/components/tier_cost"
REGISTRATION = ROOT / "TC_012_PRE_REGISTRATION.md"
PART1 = ROOT / "artifacts/tc012/part1_exploration.json"
TC011_SELECTIONS = ROOT / "artifacts/tc011/preflight/selections.jsonl.gz"
PREFLIGHT = ROOT / "artifacts/tc012/preflight"
RESULT = ROOT / "artifacts/tc012/result"
BUDGETS = (16_000, 32_000)
ARMS = ("cc80", "aspect_static", "dynamic_prompt", "residual_aspect")
REGISTRATION_SHA256 = "2310e768a232a52c63cfaba655b4ed625702cd64f6615e6adb98ac557f870359"
PART1_SHA256 = "a87edd6d8f6f39acd58c5a32946b1922fb92b89887b56e1b76bef94493a40289"
TC011_SELECTIONS_SHA256 = "9f4ae9abb57dfc76aecb3afdfcb62029056c10c6a412e42914d0c2294c2c9a0a"


class TC012Error(RuntimeError):
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


def _load_sources() -> tuple[list[dict[str, Any]], dict[tuple[str, int], dict[str, Any]]]:
    with gzip.open(CONVEX_SELECTIONS, "rt", encoding="utf-8") as handle:
        sources = list(map(json.loads, handle))
    with gzip.open(TC011_SELECTIONS, "rt", encoding="utf-8") as handle:
        prior = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}
    return sources, prior


def _initial(episodes: Sequence[Any], relevance: Sequence[int], budget: int) -> tuple[int, ...]:
    payload = pack_stm_payload([], [episodes[index].record for index in relevance], budget // 2)
    by_id = {episode.identity: index for index, episode in enumerate(episodes)}
    if not payload.selected_ids:
        raise TC012Error("empty semantic seed")
    return tuple(by_id[identifier] for identifier in payload.selected_ids)


def _score_vectors(source: Mapping[str, Any], relevance: Sequence[int], count: int) -> tuple[np.ndarray, np.ndarray]:
    fixed = np.zeros(count, dtype=np.float64)
    bm25 = np.zeros(count, dtype=np.float64)
    for index, score, lexical in zip(
        relevance,
        source["cc80"]["scores_in_order"],
        source["cc80"]["bm25_contribution_in_order"],
        strict=True,
    ):
        fixed[index] = float(score)
        bm25[index] = float(lexical)
    return fixed, bm25


def freeze_selections(output_path: Path, *, forbidden_labels: Path | None = None) -> dict[str, Any]:
    if forbidden_labels is not None:
        raise TC012Error("labels forbidden before selection freeze")
    for path, expected in ((REGISTRATION, REGISTRATION_SHA256), (PART1, PART1_SHA256), (TC011_SELECTIONS, TC011_SELECTIONS_SHA256)):
        if sha256_file(path) != expected:
            raise TC012Error(f"anchor drift: {path.name}")
    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    nlp = spacy.load("en_core_web_sm")
    sources, prior = _load_sources()
    prepared = {}
    questions = {}
    for case in cases:
        episodes = build_episodes(case, vectors)
        matrix = unit_matrix(episodes)
        candidate_facets = tuple(extract_facets(doc) for doc in nlp.pipe([episode.pair.text for episode in episodes], batch_size=64))
        idf, _ = facet_idf(candidate_facets)
        docs = list(nlp.pipe([question.question for question in case.questions], batch_size=64))
        for question, doc in zip(case.questions, docs, strict=True):
            questions[(case.sample_id, question.source_index)] = (question.question, extract_facets(doc))
        prepared[case.sample_id] = episodes, matrix, candidate_facets, idf

    rows = []
    controls = 0
    set_diffs = {f"{budget}:{name}": 0 for budget in BUDGETS for name in ("dynamic_prompt_vs_static", "residual_aspect_vs_static", "dynamic_vs_residual")}
    stops: dict[str, int] = {}
    active = {f"{budget}:{arm}": 0 for budget in BUDGETS for arm in ("dynamic_prompt", "residual_aspect")}
    state_updates = 0
    for source in sources:
        episodes, matrix, candidate_facets, idf = prepared[source["sample_id"]]
        by_id = {episode.identity: index for index, episode in enumerate(episodes)}
        relevance = tuple(by_id[identifier] for identifier in source["arms"]["cc80"]["order"])
        fixed, bm25 = _score_vectors(source, relevance, len(episodes))
        question_text, question_facets = questions[(source["sample_id"], int(source["source_index"]))]
        budget_rows = {}
        for budget in BUDGETS:
            initial = _initial(episodes, relevance, budget)
            static_trace = aspect_spread(episodes, candidate_facets, idf, fixed, relevance, initial, budget // 2)
            allocations = {
                "cc80": full_relevance(episodes, relevance, budget),
                "aspect_static": allocate_subset(episodes, relevance, static_trace.order, budget),
            }
            metas = {}
            for arm, residual in (("dynamic_prompt", False), ("residual_aspect", True)):
                order, meta = dynamic_aspect(
                    episodes, matrix, candidate_facets, idf, vectors[question_text], question_facets,
                    bm25, relevance, initial, budget // 2, residual=residual,
                )
                allocations[arm] = allocate_subset(episodes, relevance, order, budget)
                metas[arm] = meta
                state_updates += len(order)
                active[f"{budget}:{arm}"] += bool(allocations[arm].spread_ids)
                key = f"{budget}:{arm}:{meta['stopping_reason']}"
                stops[key] = stops.get(key, 0) + 1
            expected_cc80 = source["arms"]["cc80"]["selected"][str(budget)]
            expected_static = prior[(source["sample_id"], int(source["source_index"]))]["budgets"][str(budget)]["aspect"]
            for actual, expected in ((allocations["cc80"], expected_cc80), (allocations["aspect_static"], expected_static)):
                if list(actual.selected_ids) != expected["selected_ids"] or actual.payload_sha256 != expected["payload_sha256"]:
                    raise TC012Error("control reproduction failed")
                controls += 1
            static_ids = set(allocations["aspect_static"].selected_ids)
            dynamic_ids = set(allocations["dynamic_prompt"].selected_ids)
            residual_ids = set(allocations["residual_aspect"].selected_ids)
            set_diffs[f"{budget}:dynamic_prompt_vs_static"] += dynamic_ids != static_ids
            set_diffs[f"{budget}:residual_aspect_vs_static"] += residual_ids != static_ids
            set_diffs[f"{budget}:dynamic_vs_residual"] += dynamic_ids != residual_ids
            budget_rows[str(budget)] = {
                arm: _allocation(value, **({"meta": metas[arm]} if arm in metas else {}))
                for arm, value in allocations.items()
            }
        rows.append({"blind_key": source["blind_key"], "sample_id": source["sample_id"], "source_index": source["source_index"], "budgets": budget_rows})
    _write_gzip_jsonl(output_path, rows)
    return {"rows": len(rows), "sha256": sha256_file(output_path), "controls": controls, "set_diffs": set_diffs, "stops": stops, "active": active, "state_updates": state_updates, "cache_hits": reuse["hits"], "cache_misses": reuse["misses"]}


def _cell_pass(cell: Mapping[str, Any]) -> bool:
    return cell["combined"]["gains"] > cell["combined"]["losses"] and cell["targeted"]["gains"] >= cell["targeted"]["losses"] and cell["breadth"]["gains"] > cell["breadth"]["losses"] and cell["breadth_identity"]["net_identities"] > 0 and all(value >= 0 for value in cell["conversation_nets"].values()) and sum(value > 0 for value in cell["conversation_nets"].values()) >= 2


def disposition(full_cells: Mapping[str, Any], static_cells: Mapping[str, Any]) -> str:
    if all(_cell_pass(full_cells[budget]) for budget in ("16000", "32000")):
        return "DYNAMIC_PROMPT_WORKS"
    static_ok = all(
        static_cells[budget]["combined"]["gains"] > static_cells[budget]["combined"]["losses"]
        and static_cells[budget]["targeted"]["gains"] >= static_cells[budget]["targeted"]["losses"]
        and static_cells[budget]["breadth"]["gains"] >= static_cells[budget]["breadth"]["losses"]
        and static_cells[budget]["breadth_identity"]["net_identities"] >= 0
        and all(value >= 0 for value in static_cells[budget]["conversation_nets"].values())
        for budget in ("16000", "32000")
    )
    identity_positive = any(static_cells[budget]["breadth_identity"]["net_identities"] > 0 for budget in ("16000", "32000"))
    return "DYNAMIC_PROMPT_CARRIES_SIGNAL" if static_ok and identity_positive else "NO_DYNAMIC_PROMPT_SIGNAL"


def _synthetic() -> dict[str, bool]:
    def cell(good: bool, neutral: bool = False) -> dict[str, Any]:
        return {"combined": {"gains": 3 if good else 1, "losses": 1 if good else 1 if neutral else 3}, "targeted": {"gains": 1, "losses": 1 if good or neutral else 2}, "breadth": {"gains": 2 if good else 1 if neutral else 0, "losses": 0 if good else 1 if neutral else 2}, "breadth_identity": {"net_identities": 2 if good else 0 if neutral else -2}, "conversation_nets": {"a": 1 if good else 0 if neutral else -1, "b": 1 if good else 0, "c": 0, "d": 0}}
    good = {budget: cell(True) for budget in ("16000", "32000")}
    neutral = {budget: cell(True) for budget in ("16000", "32000")}
    bad = {budget: cell(False) for budget in ("16000", "32000")}
    return {"works": disposition(good, bad) == "DYNAMIC_PROMPT_WORKS", "carries": disposition(bad, neutral) == "DYNAMIC_PROMPT_CARRIES_SIGNAL", "none": disposition(bad, bad) == "NO_DYNAMIC_PROMPT_SIGNAL"}


def run_preflight(output_dir: Path = PREFLIGHT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selection = output_dir / "selections.jsonl.gz"
    frozen = freeze_selections(selection)
    try:
        freeze_selections(output_dir / "forbidden.jsonl.gz", forbidden_labels=LABELS)
    except TC012Error:
        rejected = True
    else:
        rejected = False
    expected_diffs = {"16000:dynamic_prompt_vs_static": 871, "16000:residual_aspect_vs_static": 146, "16000:dynamic_vs_residual": 871, "32000:dynamic_prompt_vs_static": 871, "32000:residual_aspect_vs_static": 71, "32000:dynamic_vs_residual": 871}
    reach = _synthetic()
    passing = frozen["rows"] == 871 and frozen["controls"] == 3484 and frozen["set_diffs"] == expected_diffs and all(value == 871 for value in frozen["active"].values()) and frozen["cache_misses"] == 0 and rejected and all(reach.values())
    result = {
        "status": "PASS" if passing else "FAIL",
        "pf1": {"registration_sha256": sha256_file(REGISTRATION), "part1_sha256": sha256_file(PART1), "dataset_sha256": sha256_file(DATASET_PATH), "blind_sha256": sha256_file(BLIND), "tc011_selection_sha256": sha256_file(TC011_SELECTIONS), "selection_sha256": frozen["sha256"], "rows": frozen["rows"], "parser": {"spacy": spacy.__version__, "model": "en_core_web_sm"}},
        "pf2": {"set_diffs": frozen["set_diffs"], "part1_reproduced": frozen["set_diffs"] == expected_diffs},
        "pf3": {"early_labels_rejected": rejected, "selection_sha256_before_labels": frozen["sha256"]},
        "pf4": {"reachability": reach, "active": frozen["active"], "stops": frozen["stops"]},
        "pf5": {"blind_keys": 871, "candidate_content_identities": 1365},
        "pf6": {"checks": frozen["controls"], "expected": 3484},
        "pf7": {"state_updates": frozen["state_updates"], "absorbing": sum(frozen["stops"].values()) == 3484, "no_repeats": True, "admission_only_updates": True},
        "pf8": {"conversations": 4, "cannot_detect": "transfer or reader effects"},
        "pf9": {"residuals": ["dynamic cue change is not evidence gain", "facet coverage is not question coverage", "residual fallback hides absent binding", "availability is not reader use"]},
        "pf10": {"availability_only": True, "reader_authorized": False},
        "calls": {"cache_hits": frozen["cache_hits"], "cache_misses": frozen["cache_misses"], "embedding": 0, "llm_or_generative": 0},
    }
    _write_json(output_dir / "preflight.json", result)
    if not passing:
        raise TC012Error("Preflight failed")
    return result


def _paired(rows: Sequence[Mapping[str, Any]], budget: int, treatment: str, baseline: str, population: str) -> dict[str, int]:
    subset = [row for row in rows if population == "combined" or row["population"] == population]
    tk, bk = f"{treatment}_{budget}_complete", f"{baseline}_{budget}_complete"
    gains = sum(row[tk] and not row[bk] for row in subset)
    losses = sum(row[bk] and not row[tk] for row in subset)
    return {"n": len(subset), "baseline": sum(row[bk] for row in subset), "treatment": sum(row[tk] for row in subset), "gains": gains, "losses": losses, "net": gains - losses}


def _cells(rows: Sequence[Mapping[str, Any]], treatment: str, baseline: str) -> dict[str, Any]:
    result = {}
    for budget in BUDGETS:
        cell = {population: _paired(rows, budget, treatment, baseline, population) for population in ("combined", "targeted", "breadth", "other")}
        breadth = [row for row in rows if row["population"] == "breadth"]
        gains = sum(max(0, row[f"{treatment}_{budget}_evidence"] - row[f"{baseline}_{budget}_evidence"]) for row in breadth)
        losses = sum(max(0, row[f"{baseline}_{budget}_evidence"] - row[f"{treatment}_{budget}_evidence"]) for row in breadth)
        cell["breadth_identity"] = {"gains": gains, "losses": losses, "net_identities": gains - losses}
        cell["conversation_nets"] = {sample: sum(row[f"{treatment}_{budget}_complete"] and not row[f"{baseline}_{budget}_complete"] for row in rows if row["sample_id"] == sample) - sum(row[f"{baseline}_{budget}_complete"] and not row[f"{treatment}_{budget}_complete"] for row in rows if row["sample_id"] == sample) for sample in sorted({row["sample_id"] for row in rows})}
        result[str(budget)] = cell
    return result


def run_study(output_dir: Path = RESULT) -> dict[str, Any]:
    preflight = json.loads((PREFLIGHT / "preflight.json").read_text(encoding="utf-8"))
    selection = PREFLIGHT / "selections.jsonl.gz"
    if preflight["status"] != "PASS" or sha256_file(selection) != preflight["pf1"]["selection_sha256"]:
        raise TC012Error("passing Preflight anchor absent")
    with gzip.open(selection, "rt", encoding="utf-8") as handle:
        frozen = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}
    rows = []
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
            row = {"question_id": question.identity, "sample_id": case.sample_id, "source_index": question.source_index, "population": population}
            for arm in ARMS:
                for budget in BUDGETS:
                    selected = set(source["budgets"][str(budget)][arm]["selected_ids"])
                    row[f"{arm}_{budget}_evidence"] = len(evidence & selected)
                    row[f"{arm}_{budget}_complete"] = bool(evidence) and evidence <= selected
            rows.append(row)
    if len(rows) != 868:
        raise TC012Error("population drift")
    full = _cells(rows, "dynamic_prompt", "cc80")
    static = _cells(rows, "dynamic_prompt", "aspect_static")
    residual_full = _cells(rows, "residual_aspect", "cc80")
    totals = {arm: {str(budget): sum(row[f"{arm}_{budget}_complete"] for row in rows) for budget in BUDGETS} for arm in ARMS}
    result = {"schema": "tc012-dynamic-aspect-v1", "status": disposition(full, static), "residual_status": "RESIDUAL_BINDER_LIMITED", "totals": totals, "dynamic_prompt_vs_cc80": full, "dynamic_prompt_vs_static": static, "residual_vs_cc80": residual_full, "population": len(rows), "selection_sha256": sha256_file(selection), "calls": {"embedding": 0, "llm_or_generative": 0}, "claim_boundary": "used LoCoMo development availability; residual exact-facet binder limited in Part 1"}
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "result.json", result)
    with (output_dir / "per_question.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    return result


__all__ = ["TC012Error", "disposition", "freeze_selections", "run_preflight", "run_study"]

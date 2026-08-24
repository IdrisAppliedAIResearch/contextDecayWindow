"""Frozen dependency-graph retrieval feasibility probe for TC-009."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.locomo_nf_development import adapt_development, sha256_file
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT, build_episodes
from analysis.tc005_exploration import evidence_indices, question_population
from analysis.tc007_allocation import full_relevance
from analysis.tc008_study import load_blind_manifest

ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
TC009_RUN = ROOT / "runs" / "tc009" / "run"
TC009_G0 = ROOT / "runs" / "tc009" / "g0"
BLIND = TC009_G0 / "label_blind_selection_manifest.json.gz"
ACCEPTED = TC009_RUN / "frozen_selections.jsonl.gz"
LABELS = TC009_RUN / "per_question.csv"
ARTIFACT = ROOT / "artifacts" / "tc009_dependency_graph_probe"
PREFLIGHT = ARTIFACT / "preflight"
RESULT = ARTIFACT / "result"
BUDGET = 32_000
ARMS = ("dense", "lexical", "subject_overlap", "dep_pagerank", "subject_ppr")
TREATMENTS = ARMS[1:]
ACCEPTED_SHA256 = "629bdfa1a7547b4bcf2df36c45628397d3f5b0c88c3d9b461dd2f9f48fe80900"
LABELS_SHA256 = "680835bf63571b620e59930cff4aa897a2524cd093bbccdefe3be9b67735a742"
CONTENT_POS = frozenset({"NOUN", "PROPN", "VERB", "ADJ", "NUM"})
SUBJECT_DEPS = frozenset({"nsubj", "nsubjpass", "csubj"})
DAMPING = 0.85
TOLERANCE = 1e-12
MAX_ITERATIONS = 200


class DependencyGraphProbeError(RuntimeError):
    pass


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_gzip_json(path: Path, value: Any) -> None:
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0) as stream:
            stream.write(raw)


def _write_gzip_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    raw = b"".join((json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8") for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0) as stream:
            stream.write(raw)


def _read_gzip_json(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _lemma(token: Any) -> str | None:
    if token.is_space or token.is_punct or token.is_stop or token.pos_ not in CONTENT_POS:
        return None
    value = token.lemma_.strip().casefold()
    return value or None


def graph_from_doc(doc: Any) -> dict[str, Any]:
    """Build the frozen undirected lemma dependency graph from one parsed doc."""

    token_keys = {token.i: _lemma(token) for token in doc}
    nodes = sorted({value for value in token_keys.values() if value is not None})
    subjects = sorted({token_keys[token.i] for token in doc if token.dep_ in SUBJECT_DEPS and token_keys[token.i] is not None})
    edges: Counter[tuple[str, str]] = Counter()
    for token in doc:
        left = token_keys[token.i]
        right = token_keys.get(token.head.i)
        if left is None or right is None or left == right:
            continue
        edges[tuple(sorted((left, right)))] += 1
    return {
        "nodes": nodes,
        "subjects": subjects,
        "edges": [[left, right, weight] for (left, right), weight in sorted(edges.items())],
        "token_count": len(doc),
        "sentence_count": sum(1 for _ in doc.sents),
    }


def pagerank(
    nodes: Sequence[str],
    edges: Sequence[Sequence[Any]],
    *,
    personalization: Mapping[str, float] | None = None,
    damping: float = DAMPING,
    tolerance: float = TOLERANCE,
    max_iterations: int = MAX_ITERATIONS,
) -> tuple[dict[str, float], int, float]:
    """Deterministic weighted PageRank with personalized dangling handling."""

    ordered = tuple(sorted(nodes))
    if not ordered:
        return {}, 0, 0.0
    index = {node: position for position, node in enumerate(ordered)}
    adjacency = np.zeros((len(ordered), len(ordered)), dtype=np.float64)
    for left, right, raw_weight in edges:
        weight = float(raw_weight)
        i, j = index[str(left)], index[str(right)]
        adjacency[i, j] += weight
        adjacency[j, i] += weight
    degree = adjacency.sum(axis=1)
    transition = np.zeros_like(adjacency)
    non_dangling = degree > 0
    transition[non_dangling] = adjacency[non_dangling] / degree[non_dangling, None]
    if personalization is None:
        teleport = np.full(len(ordered), 1.0 / len(ordered), dtype=np.float64)
    else:
        teleport = np.asarray([max(0.0, float(personalization.get(node, 0.0))) for node in ordered], dtype=np.float64)
        if float(teleport.sum()) <= 0:
            raise DependencyGraphProbeError("Personalization has no mass")
        teleport /= teleport.sum()
    rank = teleport.copy()
    residual = math.inf
    for iteration in range(1, max_iterations + 1):
        updated = (1.0 - damping) * teleport
        dangling = float(rank[degree == 0].sum())
        updated += damping * dangling * teleport
        updated += damping * (rank @ transition)
        residual = float(np.abs(updated - rank).sum())
        rank = updated
        if residual <= tolerance:
            return dict(zip(ordered, map(float, rank), strict=True)), iteration, residual
    raise DependencyGraphProbeError(f"PageRank failed to converge: residual={residual}")


def _load_parser() -> tuple[Any, dict[str, Any]]:
    import en_core_web_sm
    import spacy

    nlp = en_core_web_sm.load(disable=["ner", "textcat"])
    model_root = Path(en_core_web_sm.__file__).resolve().parent
    meta = next(model_root.rglob("meta.json"))
    return nlp, {
        "spacy_version": spacy.__version__,
        "model": "en_core_web_sm",
        "model_meta_sha256": sha256_file(meta),
    }


def build_graph_artifact() -> tuple[dict[str, Any], dict[str, Any]]:
    cases = load_blind_manifest(BLIND)
    pairs = [pair for case in cases for pair in case.pairs]
    questions = [question for case in cases for question in case.questions]
    nlp, parser = _load_parser()
    pair_graphs: dict[str, Any] = {}
    iterations = []
    residuals = []
    docs = nlp.pipe((pair.text for pair in pairs), batch_size=128)
    for pair, doc in zip(pairs, docs, strict=True):
        graph = graph_from_doc(doc)
        ranks, count, residual = pagerank(graph["nodes"], graph["edges"])
        graph["pagerank"] = ranks
        graph["pagerank_iterations"] = count
        graph["pagerank_residual"] = residual
        pair_graphs[pair.identity] = graph
        iterations.append(count)
        residuals.append(residual)
    question_terms = {}
    query_docs = nlp.pipe((question.question for question in questions), batch_size=128)
    for question, doc in zip(questions, query_docs, strict=True):
        question_terms[question.blind_key] = sorted({_lemma(token) for token in doc if _lemma(token) is not None})
    document_frequency = Counter(term for graph in pair_graphs.values() for term in graph["nodes"])
    idf = {term: math.log((len(pairs) + 1) / (frequency + 1)) + 1 for term, frequency in sorted(document_frequency.items())}
    graph_payload = {"pairs": pair_graphs, "questions": question_terms, "idf": idf}
    node_counts = [len(graph["nodes"]) for graph in pair_graphs.values()]
    subject_counts = [len(graph["subjects"]) for graph in pair_graphs.values()]
    overlap_candidates = []
    subject_overlap_candidates = []
    case_by_id = {case.sample_id: case for case in cases}
    for question in questions:
        terms = set(question_terms[question.blind_key])
        graphs = [pair_graphs[pair.identity] for pair in case_by_id[question.sample_id].pairs]
        overlap_candidates.append(sum(bool(terms & set(graph["nodes"])) for graph in graphs))
        subject_overlap_candidates.append(sum(bool(terms & set(graph["subjects"])) for graph in graphs))
    distribution = {
        "pairs": len(pairs),
        "questions": len(questions),
        "node_median": float(np.median(node_counts)),
        "node_max": max(node_counts),
        "subject_median": float(np.median(subject_counts)),
        "subject_max": max(subject_counts),
        "subject_empty_pairs": sum(value == 0 for value in subject_counts),
        "empty_queries": sum(not terms for terms in question_terms.values()),
        "questions_with_lexical_candidate": sum(value > 0 for value in overlap_candidates),
        "questions_with_subject_candidate": sum(value > 0 for value in subject_overlap_candidates),
        "lexical_candidate_median": float(np.median(overlap_candidates)),
        "subject_candidate_median": float(np.median(subject_overlap_candidates)),
        "pagerank_iterations_max": max(iterations),
        "pagerank_iterations_median": float(np.median(iterations)),
        "pagerank_residual_max": max(residuals),
        "parser_documents": len(pairs) + len(questions),
        **parser,
    }
    return graph_payload, distribution


def candidate_scores(
    case: Any,
    query_terms: set[str],
    graph_payload: Mapping[str, Any],
) -> tuple[dict[str, list[float]], dict[str, Any]]:
    idf = graph_payload["idf"]
    scores = {arm: [] for arm in TREATMENTS}
    ppr_iterations = []
    ppr_residuals = []
    subject_empty = []
    for pair in case.pairs:
        graph = graph_payload["pairs"][pair.identity]
        nodes = set(graph["nodes"])
        subjects = set(graph["subjects"])
        shared = query_terms & nodes
        shared_subjects = query_terms & subjects
        scores["lexical"].append(sum(float(idf[term]) for term in shared))
        scores["subject_overlap"].append(sum(float(idf[term]) for term in shared_subjects))
        scores["dep_pagerank"].append(sum(float(idf[term]) * float(graph["pagerank"][term]) for term in shared))
        if shared and subjects:
            seeds = {term: float(idf[term]) for term in shared}
            ranks, count, residual = pagerank(graph["nodes"], graph["edges"], personalization=seeds)
            scores["subject_ppr"].append(sum(ranks[term] for term in subjects))
            ppr_iterations.append(count)
            ppr_residuals.append(residual)
        else:
            scores["subject_ppr"].append(0.0)
        subject_empty.append(not subjects)
    return scores, {
        "ppr_iterations": ppr_iterations,
        "ppr_residuals": ppr_residuals,
        "subject_empty": subject_empty,
    }


def score_order(case: Any, scores: Sequence[float]) -> tuple[int, ...]:
    return tuple(sorted(range(len(case.pairs)), key=lambda index: (-float(scores[index]), case.pairs[index].session_order, case.pairs[index].pair_order, case.pairs[index].identity)))


def _dummy_episodes(case: Any) -> tuple[Any, ...]:
    dummy = np.zeros(1, dtype=np.float32)
    return build_episodes(case, {pair.text: dummy for pair in case.pairs})


def freeze_selections(output_path: Path, graph_path: Path, *, forbidden_labels: Path | None = None) -> dict[str, Any]:
    if forbidden_labels is not None:
        raise DependencyGraphProbeError("Labels are forbidden during selection freeze")
    if sha256_file(ACCEPTED) != ACCEPTED_SHA256:
        raise DependencyGraphProbeError("Accepted TC-009 selection artifact drifted")
    cases = load_blind_manifest(BLIND)
    graph_payload, distribution = build_graph_artifact()
    _write_gzip_json(graph_path, graph_payload)
    case_by_id = {case.sample_id: case for case in cases}
    rows = []
    dense_reproductions = 0
    ppr_iterations = []
    ppr_residuals = []
    with gzip.open(ACCEPTED, "rt", encoding="utf-8") as handle:
        for line in handle:
            accepted = json.loads(line)
            case = case_by_id[accepted["sample_id"]]
            episodes = _dummy_episodes(case)
            by_identity = {episode.identity: index for index, episode in enumerate(episodes)}
            dense_order = tuple(by_identity[identifier] for identifier in accepted["orders"]["dense"])
            packs = {"dense": full_relevance(episodes, dense_order, BUDGET)}
            question_terms = set(graph_payload["questions"][accepted["blind_key"]])
            scores, diagnostics = candidate_scores(case, question_terms, graph_payload)
            ppr_iterations.extend(diagnostics["ppr_iterations"])
            ppr_residuals.extend(diagnostics["ppr_residuals"])
            arm_details = {}
            for arm in TREATMENTS:
                order = score_order(case, scores[arm])
                packs[arm] = full_relevance(episodes, order, BUDGET)
                arm_details[arm] = {
                    "order": [episodes[index].identity for index in order],
                    "scores": [scores[arm][index] for index in order],
                    "zero_scores": sum(value == 0 for value in scores[arm]),
                    "selected_subject_empty": sum(diagnostics["subject_empty"][index] for index in range(len(episodes)) if episodes[index].identity in packs[arm].selected_ids),
                }
            expected = accepted["budgets"][str(BUDGET)]["control"]
            if list(packs["dense"].selected_ids) != expected["selected_ids"] or packs["dense"].payload_sha256 != expected["payload_sha256"]:
                raise DependencyGraphProbeError("Dense baseline failed accepted replay")
            dense_reproductions += 1
            rows.append({
                "blind_key": accepted["blind_key"],
                "sample_id": accepted["sample_id"],
                "source_index": accepted["source_index"],
                "arms": {arm: {"selected_ids": list(pack.selected_ids), "payload_sha256": pack.payload_sha256, "payload_chars": len(pack.payload), **(arm_details.get(arm) or {})} for arm, pack in packs.items()},
            })
    _write_gzip_jsonl(output_path, rows)
    return {
        "rows": len(rows),
        "sha256": sha256_file(output_path),
        "graph_sha256": sha256_file(graph_path),
        "dense_reproductions": dense_reproductions,
        "distribution": distribution,
        "ppr_runs": len(ppr_iterations),
        "ppr_iterations_max": max(ppr_iterations),
        "ppr_residual_max": max(ppr_residuals),
        "embedding_vectors_read": 0,
        "embedding_calls": 0,
        "parser_documents": distribution["parser_documents"],
    }


def disposition(cells: Mapping[str, Any]) -> dict[str, Any]:
    passing = []
    for arm, cell in cells.items():
        clauses = {
            "combined_positive": cell["combined"]["gains"] > cell["combined"]["losses"],
            "targeted_nonnegative": cell["targeted"]["gains"] >= cell["targeted"]["losses"],
            "breadth_identity_positive": cell["breadth_identity"]["net_identities"] > 0,
            "breadth_complete_nonnegative": cell["breadth"]["gains"] >= cell["breadth"]["losses"],
            "conversation_consistent": all(value >= 0 for value in cell["conversation_nets"].values()) and sum(value > 0 for value in cell["conversation_nets"].values()) >= 2,
        }
        cell["clauses"] = clauses
        if all(clauses.values()):
            passing.append(arm)
    return {"status": "DESCRIPTIVE_POSITIVE_SIGNAL" if passing else "NO_POSITIVE_SIGNAL", "passing_arms": passing}


def synthetic_reachability() -> dict[str, Any]:
    good = {"combined": {"gains": 3, "losses": 1}, "targeted": {"gains": 1, "losses": 1}, "breadth": {"gains": 1, "losses": 0}, "breadth_identity": {"net_identities": 1}, "conversation_nets": {"a": 1, "b": 1, "c": 0, "d": 0}}
    bad = {"combined": {"gains": 1, "losses": 2}, "targeted": {"gains": 0, "losses": 1}, "breadth": {"gains": 0, "losses": 1}, "breadth_identity": {"net_identities": -1}, "conversation_nets": {"a": -1, "b": 0, "c": 0, "d": 0}}
    return {"positive_reachable": disposition({"good": good})["status"] == "DESCRIPTIVE_POSITIVE_SIGNAL", "negative_reachable": disposition({"bad": bad})["status"] == "NO_POSITIVE_SIGNAL"}


def _path_graph_solution() -> dict[str, Any]:
    nodes = ("a", "b", "c")
    edges = (("a", "b", 1), ("b", "c", 1))
    actual, iterations, residual = pagerank(nodes, edges)
    transition = np.asarray([[0, 1, 0], [0.5, 0, 0.5], [0, 1, 0]], dtype=np.float64)
    expected = np.linalg.solve(np.eye(3) - DAMPING * transition.T, np.full(3, (1 - DAMPING) / 3))
    error = float(np.max(np.abs(expected - np.asarray([actual[node] for node in nodes]))))
    return {"max_absolute_error": error, "iterations": iterations, "residual": residual, "pass": error < 1e-10}


def run_preflight(output_dir: Path = PREFLIGHT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selections = freeze_selections(output_dir / "selections.jsonl.gz", output_dir / "graph_map.json.gz")
    try:
        freeze_selections(output_dir / "forbidden.jsonl.gz", output_dir / "forbidden_graph.json.gz", forbidden_labels=LABELS)
    except DependencyGraphProbeError:
        planted_rejection = True
    else:
        planted_rejection = False
    reach = synthetic_reachability()
    path_graph = _path_graph_solution()
    distribution = selections["distribution"]
    pass_conditions = [
        selections["dense_reproductions"] == 871,
        distribution["pairs"] == 1365,
        distribution["questions"] == 871,
        distribution["subject_empty_pairs"] == 402,
        distribution["questions_with_lexical_candidate"] == 871,
        distribution["questions_with_subject_candidate"] == 870,
        selections["ppr_iterations_max"] <= MAX_ITERATIONS,
        path_graph["pass"],
        planted_rejection,
        all(reach.values()),
    ]
    result = {
        "status": "PASS" if all(pass_conditions) else "FAIL",
        "pf1": {"dataset_sha256": sha256_file(DATASET_PATH), "blind_sha256": sha256_file(BLIND), "accepted_sha256": sha256_file(ACCEPTED), "labels_sha256": sha256_file(LABELS), "graph_sha256": selections["graph_sha256"], "selection_sha256": selections["sha256"]},
        "pf2": {"distribution": distribution, "identity": "exact lemma and grammatical-subject overlap plus weighted dependency PageRank rank complete pairs; complete pairs are packed"},
        "pf3": {"selection_sha256_before_labels": selections["sha256"], "planted_early_label_rejected": planted_rejection},
        "pf4": reach,
        "pf5": {"blind_keys": 871, "pair_content_identities": 1365},
        "pf6": {"dense_selected_id_and_payload_reproductions": selections["dense_reproductions"], "expected": 871, "dummy_vector_dimensions": 1},
        "pf7": {"real_standard_graphs_converged": 1365, "real_personalized_runs_converged": selections["ppr_runs"], "iterations_max": selections["ppr_iterations_max"], "residual_max": selections["ppr_residual_max"], "independent_path_graph": path_graph},
        "pf8": {"conversations": 4, "cannot_detect": "new-corpus transfer"},
        "pf9": {"residuals": ["word overlap is not meaning", "parser subject errors", "centrality and availability are not reader use", "degree may track document length"]},
        "pf10": {"availability_only": True, "reader_authorized": False},
        "calls": {"parser_documents": selections["parser_documents"], "embedding_vectors_read": 0, "embedding": 0, "llm_or_generative": 0},
    }
    _write_json(output_dir / "preflight.json", result)
    if result["status"] != "PASS":
        raise DependencyGraphProbeError("Preflight failed")
    return result


def _paired(rows: Sequence[Mapping[str, Any]], arm: str, population: str, baseline: str = "dense") -> dict[str, int]:
    selected = [row for row in rows if population == "combined" or row["population"] == population]
    gains = sum(row[f"{arm}_complete"] and not row[f"{baseline}_complete"] for row in selected)
    losses = sum(row[f"{baseline}_complete"] and not row[f"{arm}_complete"] for row in selected)
    return {"n": len(selected), "baseline": sum(row[f"{baseline}_complete"] for row in selected), "treatment": sum(row[f"{arm}_complete"] for row in selected), "gains": gains, "losses": losses, "net": gains - losses}


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    return {"n": len(values), "mean": float(np.mean(values)) if values else None, "median": float(np.median(values)) if values else None, "min": float(min(values)) if values else None, "max": float(max(values)) if values else None}


def run_probe(output_dir: Path = RESULT) -> dict[str, Any]:
    preflight = json.loads((PREFLIGHT / "preflight.json").read_text(encoding="utf-8"))
    selection_path = PREFLIGHT / "selections.jsonl.gz"
    graph_path = PREFLIGHT / "graph_map.json.gz"
    if preflight["status"] != "PASS" or sha256_file(selection_path) != preflight["pf3"]["selection_sha256_before_labels"] or sha256_file(graph_path) != preflight["pf1"]["graph_sha256"]:
        raise DependencyGraphProbeError("Passing Preflight anchors absent or drifted")
    with gzip.open(selection_path, "rt", encoding="utf-8") as handle:
        selections = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}
    with gzip.open(ACCEPTED, "rt", encoding="utf-8") as handle:
        accepted = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}
    graph_payload = _read_gzip_json(graph_path)
    cases = adapt_development(DATASET_PATH)
    rows = []
    for case in cases:
        episodes = _dummy_episodes(case)
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            population = question_population(case, question)
            if population == "ineligible":
                continue
            evidence = {episodes[index].identity for index in evidence_indices(case, episodes, question)}
            frozen = selections[(case.sample_id, question.source_index)]
            row = {"question_id": question.identity, "sample_id": case.sample_id, "source_index": question.source_index, "population": population, "evidence_count": len(evidence), "evidence_ids": sorted(evidence)}
            for arm in ARMS:
                chosen = set(frozen["arms"][arm]["selected_ids"])
                row[f"{arm}_evidence"] = len(evidence & chosen)
                row[f"{arm}_complete"] = bool(evidence) and evidence <= chosen
            rows.append(row)
    if len(rows) != 868:
        raise DependencyGraphProbeError("Measured population drifted")
    cells = {}
    for arm in TREATMENTS:
        cell = {name: _paired(rows, arm, name) for name in ("combined", "targeted", "breadth")}
        breadth = [row for row in rows if row["population"] == "breadth"]
        identity_gains = sum(max(0, row[f"{arm}_evidence"] - row["dense_evidence"]) for row in breadth)
        identity_losses = sum(max(0, row["dense_evidence"] - row[f"{arm}_evidence"]) for row in breadth)
        cell["breadth_identity"] = {"gains": identity_gains, "losses": identity_losses, "net_identities": identity_gains - identity_losses}
        cell["conversation_nets"] = {sample_id: sum(row[f"{arm}_complete"] and not row["dense_complete"] for row in rows if row["sample_id"] == sample_id) - sum(row["dense_complete"] and not row[f"{arm}_complete"] for row in rows if row["sample_id"] == sample_id) for sample_id in sorted({row["sample_id"] for row in rows})}
        evidence_dense_ranks = []
        evidence_treatment_ranks = []
        score_zero_counts = []
        selected_subject_empty = []
        score_length_correlations = []
        for row in rows:
            key = (row["sample_id"], int(row["source_index"]))
            frozen = selections[key]
            dense_order = accepted[key]["orders"]["dense"]
            treatment_order = frozen["arms"][arm]["order"]
            dense_rank = {identifier: rank for rank, identifier in enumerate(dense_order, 1)}
            treatment_rank = {identifier: rank for rank, identifier in enumerate(treatment_order, 1)}
            for identifier in row["evidence_ids"]:
                evidence_dense_ranks.append(dense_rank[identifier])
                evidence_treatment_ranks.append(treatment_rank[identifier])
            score_zero_counts.append(frozen["arms"][arm]["zero_scores"])
            selected_subject_empty.append(frozen["arms"][arm]["selected_subject_empty"])
            scores = [float(value) for value in frozen["arms"][arm]["scores"]]
            lengths = [len(graph_payload["pairs"][identifier]["nodes"]) for identifier in treatment_order]
            if np.std(scores) > 0 and np.std(lengths) > 0:
                score_length_correlations.append(float(np.corrcoef(scores, lengths)[0, 1]))
        cell["rank_diagnostics"] = {"all_evidence_dense": _distribution(evidence_dense_ranks), "all_evidence_treatment": _distribution(evidence_treatment_ranks)}
        cell["surrogate_audit"] = {"zero_score_candidates_per_question": _distribution(score_zero_counts), "selected_subject_empty_per_question": _distribution(selected_subject_empty), "median_score_node_count_correlation": float(np.median(score_length_correlations)), "correlation_questions": len(score_length_correlations)}
        cell["versus_lexical"] = None if arm == "lexical" else {name: _paired(rows, arm, name, baseline="lexical") for name in ("combined", "targeted", "breadth")}
        cells[arm] = cell
    verdict = disposition(cells)
    result = {"schema": "tc009-dependency-graph-probe-v1", **verdict, "cells": cells, "selection_sha256": sha256_file(selection_path), "population": len(rows), "calls": {"outcome_parser_documents": 0, "embedding_vectors_read": 0, "embedding": 0, "llm_or_generative": 0}, "claim_boundary": "used LoCoMo development availability only; no TC-010, selector, deployment, or reader authorized"}
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "result.json", result)
    with (output_dir / "per_question.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return result


__all__ = ["DependencyGraphProbeError", "candidate_scores", "disposition", "graph_from_doc", "pagerank", "run_preflight", "run_probe"]

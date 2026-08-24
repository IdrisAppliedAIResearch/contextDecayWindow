"""Frozen noun/subject span-ranking feasibility probe for TC-009."""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
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
from analysis.tc008_study import load_blind_manifest, load_blind_vectors
from retrieval_bakeoff.embedding import CarriedEmbedder

ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
TC009_RUN = ROOT / "runs" / "tc009" / "run"
TC009_G0 = ROOT / "runs" / "tc009" / "g0"
BLIND = TC009_G0 / "label_blind_selection_manifest.json.gz"
ACCEPTED = TC009_RUN / "frozen_selections.jsonl.gz"
LABELS = TC009_RUN / "per_question.csv"
ARTIFACT = ROOT / "artifacts" / "tc009_syntactic_span_probe"
CAPTURE = ARTIFACT / "capture"
PREFLIGHT = ARTIFACT / "preflight"
RESULT = ARTIFACT / "result"
BUDGET = 32_000
ARMS = ("dense", "noun", "subject")
ACCEPTED_SHA256 = "629bdfa1a7547b4bcf2df36c45628397d3f5b0c88c3d9b461dd2f9f48fe80900"
LABELS_SHA256 = "680835bf63571b620e59930cff4aa897a2524cd093bbccdefe3be9b67735a742"
SUBJECT_DEPS = frozenset({"nsubj", "nsubjpass", "csubj"})


class SpanProbeError(RuntimeError):
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


def extract_spans(doc: Any) -> dict[str, list[str]]:
    nouns = [chunk.text.strip() for chunk in doc.noun_chunks if chunk.text.strip()]
    subjects = [
        sentence.text.strip()
        for sentence in doc.sents
        if sentence.text.strip() and any(token.dep_ in SUBJECT_DEPS for token in sentence)
    ]
    return {"noun": nouns, "subject": subjects}


def extract_span_map() -> tuple[dict[str, Any], dict[str, Any]]:
    import en_core_web_sm
    import spacy

    cases = load_blind_manifest(BLIND)
    pairs = [pair for case in cases for pair in case.pairs]
    nlp = en_core_web_sm.load(disable=["ner", "lemmatizer", "textcat"])
    docs = nlp.pipe((pair.text for pair in pairs), batch_size=128)
    mapping = {}
    noun_counts = []
    subject_counts = []
    for pair, doc in zip(pairs, docs, strict=True):
        spans = extract_spans(doc)
        mapping[pair.identity] = spans
        noun_counts.append(len(spans["noun"]))
        subject_counts.append(len(spans["subject"]))
    texts = sorted({text for spans in mapping.values() for arm in ("noun", "subject") for text in spans[arm]})
    import en_core_web_sm as model_package

    model_root = Path(model_package.__file__).resolve().parent
    meta = next(model_root.rglob("meta.json"))
    distribution = {
        "pairs": len(pairs),
        "noun_occurrences": sum(noun_counts),
        "noun_unique": len({text for spans in mapping.values() for text in spans["noun"]}),
        "noun_empty": sum(value == 0 for value in noun_counts),
        "noun_median": float(np.median(noun_counts)),
        "noun_max": max(noun_counts),
        "subject_occurrences": sum(subject_counts),
        "subject_unique": len({text for spans in mapping.values() for text in spans["subject"]}),
        "subject_empty": sum(value == 0 for value in subject_counts),
        "subject_median": float(np.median(subject_counts)),
        "subject_max": max(subject_counts),
        "union_unique": len(texts),
        "text_order_sha256": hashlib.sha256("\0".join(texts).encode("utf-8")).hexdigest(),
        "parser_documents": len(pairs),
        "spacy_version": spacy.__version__,
        "model": "en_core_web_sm",
        "model_meta_sha256": sha256_file(meta),
    }
    return {"pairs": mapping, "texts": texts}, distribution


def capture_vectors(output_dir: Path = CAPTURE) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SpanProbeError("Capture output is not empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    span_map, distribution = extract_span_map()
    texts = span_map["texts"]
    embedder = CarriedEmbedder()
    embedder.assert_carried_model()
    vectors = np.vstack(embedder.embed_many(texts, batch_size=64)).astype(np.float32)
    if vectors.shape != (len(texts), 1024):
        raise SpanProbeError("Captured span-vector shape drifted")
    np.save(output_dir / "vectors.npy", vectors, allow_pickle=False)
    _write_gzip_json(output_dir / "span_map.json.gz", span_map)
    manifest = {
        "status": "CAPTURED",
        "distribution": distribution,
        "span_map_sha256": sha256_file(output_dir / "span_map.json.gz"),
        "vectors_sha256": sha256_file(output_dir / "vectors.npy"),
        "embedding_model_sha256": embedder.model_sha256,
        "embedding_texts": len(texts),
        "embedding_batches": math.ceil(len(texts) / 64),
        "parser_documents": distribution["parser_documents"],
        "llm_or_generative_calls": 0,
    }
    _write_json(output_dir / "manifest.json", manifest)
    return manifest


def load_span_vectors() -> tuple[dict[str, Any], dict[str, np.ndarray], dict[str, Any]]:
    manifest = json.loads((CAPTURE / "manifest.json").read_text(encoding="utf-8"))
    if sha256_file(CAPTURE / "span_map.json.gz") != manifest["span_map_sha256"] or sha256_file(CAPTURE / "vectors.npy") != manifest["vectors_sha256"]:
        raise SpanProbeError("Captured span artifacts drifted")
    span_map = _read_gzip_json(CAPTURE / "span_map.json.gz")
    matrix = np.load(CAPTURE / "vectors.npy", allow_pickle=False)
    if matrix.shape != (len(span_map["texts"]), 1024):
        raise SpanProbeError("Sealed span-vector cardinality drifted")
    norms = np.linalg.norm(matrix, axis=1)
    if np.any(norms == 0):
        raise SpanProbeError("Zero-norm span vector")
    unit = matrix / norms[:, None]
    return span_map, {text: unit[index] for index, text in enumerate(span_map["texts"])}, manifest


def candidate_scores(
    case: Any,
    query: np.ndarray,
    span_map: Mapping[str, Any],
    span_vectors: Mapping[str, np.ndarray],
    pair_vectors: Mapping[str, np.ndarray],
    arm: str,
) -> tuple[list[float], list[str | None], list[bool]]:
    query = np.asarray(query, dtype=np.float32)
    query /= np.linalg.norm(query)
    scores = []
    winners = []
    fallbacks = []
    for pair in case.pairs:
        spans = list(span_map["pairs"][pair.identity][arm])
        if spans:
            values = [float(span_vectors[text] @ query) for text in spans]
            best = max(range(len(values)), key=lambda index: (values[index], -index))
            scores.append(values[best])
            winners.append(spans[best])
            fallbacks.append(False)
        else:
            vector = np.asarray(pair_vectors[pair.identity], dtype=np.float32)
            vector /= np.linalg.norm(vector)
            scores.append(float(vector @ query))
            winners.append(None)
            fallbacks.append(True)
    return scores, winners, fallbacks


def score_order(case: Any, scores: Sequence[float]) -> tuple[int, ...]:
    return tuple(sorted(range(len(case.pairs)), key=lambda index: (-float(scores[index]), case.pairs[index].session_order, case.pairs[index].pair_order, case.pairs[index].identity)))


def freeze_selections(output_path: Path, *, forbidden_labels: Path | None = None) -> dict[str, Any]:
    if forbidden_labels is not None:
        raise SpanProbeError("Labels are forbidden during selection freeze")
    if sha256_file(ACCEPTED) != ACCEPTED_SHA256:
        raise SpanProbeError("Accepted TC-009 selection artifact drifted")
    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    span_map, span_vectors, capture = load_span_vectors()
    case_by_id = {case.sample_id: case for case in cases}
    rows = []
    dense_reproductions = 0
    with gzip.open(ACCEPTED, "rt", encoding="utf-8") as handle:
        for line in handle:
            accepted = json.loads(line)
            case = case_by_id[accepted["sample_id"]]
            episodes = build_episodes(case, vectors)
            query_text = next(q.question for q in case.questions if q.source_index == int(accepted["source_index"]))
            query = vectors[query_text]
            dense_order = tuple({episode.identity: index for index, episode in enumerate(episodes)}[identifier] for identifier in accepted["orders"]["dense"])
            packs = {"dense": full_relevance(episodes, dense_order, BUDGET)}
            arm_details = {}
            pair_vectors = {pair.identity: vectors[pair.text] for pair in case.pairs}
            for arm in ("noun", "subject"):
                scores, winners, fallbacks = candidate_scores(case, query, span_map, span_vectors, pair_vectors, arm)
                order = score_order(case, scores)
                packs[arm] = full_relevance(episodes, order, BUDGET)
                arm_details[arm] = {
                    "order": [episodes[index].identity for index in order],
                    "scores": [scores[index] for index in order],
                    "winning_spans": [winners[index] for index in order],
                    "fallbacks": [fallbacks[index] for index in order],
                }
            accepted_dense = accepted["budgets"][str(BUDGET)]["control"]
            if list(packs["dense"].selected_ids) != accepted_dense["selected_ids"] or packs["dense"].payload_sha256 != accepted_dense["payload_sha256"]:
                raise SpanProbeError("Dense baseline failed accepted replay")
            dense_reproductions += 1
            rows.append({
                "blind_key": accepted["blind_key"],
                "sample_id": accepted["sample_id"],
                "source_index": accepted["source_index"],
                "arms": {
                    arm: {
                        "selected_ids": list(pack.selected_ids),
                        "payload_sha256": pack.payload_sha256,
                        "payload_chars": pack.payload_chars,
                        **(arm_details.get(arm) or {}),
                    }
                    for arm, pack in packs.items()
                },
            })
    _write_gzip_jsonl(output_path, rows)
    return {"rows": len(rows), "sha256": sha256_file(output_path), "dense_reproductions": dense_reproductions, "cache_hits": reuse["hits"], "cache_misses": reuse["misses"], "embedding_calls": 0, "parser_documents": 0, "capture_manifest": capture}


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


def run_preflight(output_dir: Path = PREFLIGHT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selections = freeze_selections(output_dir / "selections.jsonl.gz")
    span_map, distribution = extract_span_map()
    try:
        freeze_selections(output_dir / "forbidden.jsonl.gz", forbidden_labels=LABELS)
    except SpanProbeError:
        planted = True
    else:
        planted = False
    reach = synthetic_reachability()
    result = {
        "status": "PASS" if selections["dense_reproductions"] == 871 and selections["cache_misses"] == 0 and planted and all(reach.values()) else "FAIL",
        "pf1": {"dataset_sha256": sha256_file(DATASET_PATH), "blind_sha256": sha256_file(BLIND), "accepted_sha256": sha256_file(ACCEPTED), "labels_sha256": sha256_file(LABELS), "capture": json.loads((CAPTURE / "manifest.json").read_text(encoding="utf-8"))},
        "pf2": {"distribution": distribution, "identity": "max noun-chunk or nominal-subject-sentence cosine ranks complete pair candidates; complete pairs are packed"},
        "pf3": {"selection_sha256_before_labels": selections["sha256"], "planted_early_label_rejected": planted},
        "pf4": reach,
        "pf5": {"blind_keys": 871, "pair_content_identities": 1365},
        "pf6": {"dense_selected_id_and_payload_reproductions": selections["dense_reproductions"], "expected": 871},
        "pf7": {"not_applicable": True},
        "pf8": {"conversations": 4, "cannot_detect": "new-corpus transfer"},
        "pf9": {"residuals": ["parser error", "max-over-many-span bias", "availability is not reader use"]},
        "pf10": {"availability_only": True, "reader_authorized": False},
        "calls": {"outcome_embedding": 0, "outcome_parser_documents": 0, "llm_or_generative": 0, "cache_misses": selections["cache_misses"]},
    }
    _write_json(output_dir / "preflight.json", result)
    if result["status"] != "PASS":
        raise SpanProbeError("Preflight failed")
    return result


def _paired(rows: Sequence[Mapping[str, Any]], arm: str, population: str) -> dict[str, int]:
    selected = [row for row in rows if population == "combined" or row["population"] == population]
    gains = sum(row[f"{arm}_complete"] and not row["dense_complete"] for row in selected)
    losses = sum(row["dense_complete"] and not row[f"{arm}_complete"] for row in selected)
    return {"n": len(selected), "dense": sum(row["dense_complete"] for row in selected), "treatment": sum(row[f"{arm}_complete"] for row in selected), "gains": gains, "losses": losses, "net": gains - losses}


def run_probe(output_dir: Path = RESULT) -> dict[str, Any]:
    preflight = json.loads((PREFLIGHT / "preflight.json").read_text(encoding="utf-8"))
    selection_path = PREFLIGHT / "selections.jsonl.gz"
    if preflight["status"] != "PASS" or sha256_file(selection_path) != preflight["pf3"]["selection_sha256_before_labels"]:
        raise SpanProbeError("Passing Preflight selection anchor absent or drifted")
    with gzip.open(selection_path, "rt", encoding="utf-8") as handle:
        selections = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}
    blind_cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(blind_cases)
    cases = adapt_development(DATASET_PATH)
    rows = []
    for case in cases:
        episodes = build_episodes(case, vectors)
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            population = question_population(case, question)
            if population == "ineligible":
                continue
            evidence = {episodes[index].identity for index in evidence_indices(case, episodes, question)}
            frozen = selections[(case.sample_id, question.source_index)]
            row = {"question_id": question.identity, "sample_id": case.sample_id, "source_index": question.source_index, "population": population, "evidence_count": len(evidence)}
            for arm in ARMS:
                chosen = set(frozen["arms"][arm]["selected_ids"])
                row[f"{arm}_evidence"] = len(evidence & chosen)
                row[f"{arm}_complete"] = bool(evidence) and evidence <= chosen
            rows.append(row)
    if len(rows) != 868:
        raise SpanProbeError("Measured population drifted")
    cells = {}
    for arm in ("noun", "subject"):
        cell = {name: _paired(rows, arm, name) for name in ("combined", "targeted", "breadth")}
        breadth = [row for row in rows if row["population"] == "breadth"]
        identity_gains = sum(max(0, row[f"{arm}_evidence"] - row["dense_evidence"]) for row in breadth)
        identity_losses = sum(max(0, row["dense_evidence"] - row[f"{arm}_evidence"]) for row in breadth)
        cell["breadth_identity"] = {"gains": identity_gains, "losses": identity_losses, "net_identities": identity_gains - identity_losses}
        cell["conversation_nets"] = {
            sample_id: sum(row[f"{arm}_complete"] and not row["dense_complete"] for row in rows if row["sample_id"] == sample_id) - sum(row["dense_complete"] and not row[f"{arm}_complete"] for row in rows if row["sample_id"] == sample_id)
            for sample_id in sorted({row["sample_id"] for row in rows})
        }
        cells[arm] = cell
    verdict = disposition(cells)
    result = {"schema": "tc009-syntactic-span-probe-v1", **verdict, "cells": cells, "selection_sha256": sha256_file(selection_path), "population": len(rows), "calls": {"embedding": 0, "parser_documents": 0, "llm_or_generative": 0, "cache_misses": reuse["misses"]}, "claim_boundary": "used LoCoMo development availability only; no TC-010, selector or reader authorized"}
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "result.json", result)
    with (output_dir / "per_question.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    return result


__all__ = ["SpanProbeError", "candidate_scores", "disposition", "extract_spans", "run_preflight", "run_probe"]

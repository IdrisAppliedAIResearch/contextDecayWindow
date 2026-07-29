from __future__ import annotations

import hashlib
import html
import json
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from statistics import fmean

from .config import QUERY_ROOT, REPO_ROOT
from .models import Candidate, RetrievalResult
from .serialization import render_candidate_element


def normalized_text_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace(
        "\r", "\n"
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_locked_artifacts() -> dict[str, str]:
    lock_path = QUERY_ROOT / "artifact_lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    observed: dict[str, str] = {}
    for relative, expected in lock["artifacts"].items():
        path = QUERY_ROOT / relative
        actual = normalized_text_sha256(path)
        if actual != expected:
            raise AssertionError(
                f"Locked artifact changed: {relative}: {actual} != {expected}"
            )
        observed[str(path.relative_to(REPO_ROOT))] = actual
    for relative, expected in lock["source_scripts"].items():
        path = REPO_ROOT / relative
        actual = normalized_text_sha256(path)
        if actual != expected:
            raise AssertionError(
                f"Locked source script changed: {relative}: {actual} != {expected}"
            )
        observed[relative] = actual
    return observed


class HoldoutEvaluator:
    """Measurement-only evaluator. Mechanism modules must never import it."""

    def __init__(self, corpus_id: str) -> None:
        suffix = "121" if corpus_id.startswith("c121") else "1000"
        path = QUERY_ROOT / f"answer_key_{suffix}.json"
        self.payload = json.loads(path.read_text(encoding="utf-8"))
        self.facts = self.payload["facts"]
        self.queries = {
            row["query_id"]: row for row in self.payload["queries"]
        }
        self.eligible_turn_min = int(self.payload["eligible_turn_min"])
        self.eligible_turn_max = int(self.payload["eligible_turn_max"])

    def evaluate(self, result: RetrievalResult) -> dict:
        key_row = self.queries.get(result.query.query_id)
        if key_row is None:
            raise KeyError(f"No locked key row for {result.query.query_id}")

        rendered_elements = [
            render_candidate_element(item) for item in result.selected
        ]
        matched: dict[str, str] = {}
        provenance_violations: list[dict] = []
        key_bearing_indices: set[int] = set()

        for fact_id in key_row["required_fact_ids"]:
            fact = self.facts[fact_id]
            required_terms = [
                str(term).casefold() for term in fact["required_terms"]
            ]
            for index, (ranked, rendered) in enumerate(
                zip(result.selected, rendered_elements, strict=True)
            ):
                semantic_element = html.unescape(rendered).casefold()
                if not all(term in semantic_element for term in required_terms):
                    continue
                candidate = ranked.candidate
                turn_ok = candidate.turn_number in {
                    int(turn) for turn in fact["source_turns"]
                }
                role_text = _source_role_text(candidate, str(fact["source_role"]))
                role_ok = all(term in role_text.casefold() for term in required_terms)
                if not turn_ok or not role_ok:
                    provenance_violations.append(
                        {
                            "fact_id": fact_id,
                            "candidate_id": candidate.candidate_id,
                            "turn_number": candidate.turn_number,
                            "turn_ok": turn_ok,
                            "role_ok": role_ok,
                        }
                    )
                    continue
                matched[fact_id] = candidate.candidate_id
                key_bearing_indices.add(index)
                break

        required_fact_ids = list(key_row["required_fact_ids"])
        required_domains = list(key_row["domains"])
        matched_domains = sorted(
            {
                _fact_domain(fact_id)
                for fact_id in matched
                if _fact_domain(fact_id) in required_domains
            }
        )
        key_bearing_characters = sum(
            len(rendered_elements[index]) for index in key_bearing_indices
        )
        delivered = len(result.rendered_block)
        return {
            "corpus_id": result.corpus_id,
            "method_id": result.method_id,
            "query_id": result.query.query_id,
            "query_text": result.query.text,
            "query_class": key_row["query_class"],
            "required_fact_ids": required_fact_ids,
            "matched_fact_ids": sorted(matched),
            "fact_matches": matched,
            "required_fact_count": len(required_fact_ids),
            "matched_fact_count": len(matched),
            "fact_recall_at_budget": (
                len(matched) / len(required_fact_ids)
                if required_fact_ids
                else 0.0
            ),
            "required_domains": required_domains,
            "matched_domains": matched_domains,
            "domain_coverage": (
                len(matched_domains) / len(required_domains)
                if required_domains
                else 0.0
            ),
            "key_bearing_characters": key_bearing_characters,
            "precision_proxy": (
                key_bearing_characters / delivered if delivered else 0.0
            ),
            "delivered_characters": delivered,
            "selected_count": len(result.selected),
            "ranked_count": result.ranked_count,
            "budget": result.budget,
            "eligible_turn_min": self.eligible_turn_min,
            "eligible_turn_max": self.eligible_turn_max,
            "query_encode_ms": result.query_encode_ms,
            "rank_ms": result.rank_ms,
            "pack_ms": result.pack_ms,
            "rank_pack_ms": result.rank_pack_ms,
            "latency_ms": result.latency_ms,
            "index_build_ms": result.index_build_ms,
            "benchmark_repetitions": result.benchmark_repetitions,
            "provenance_violations": provenance_violations,
            "evaluation_status": (
                "FAIL_PROVENANCE" if provenance_violations else "PASS"
            ),
        }


def aggregate_rows(rows: list[dict]) -> dict:
    by_corpus_class: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    by_method: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        key = (row["method_id"], row["corpus_id"], row["query_class"])
        by_corpus_class[key].append(row)
        by_method[row["method_id"]].append(row)

    corpus_class = []
    for (method_id, corpus_id, query_class), group in sorted(
        by_corpus_class.items()
    ):
        corpus_class.append(
            {
                "method_id": method_id,
                "corpus_id": corpus_id,
                "query_class": query_class,
                **_mean_metrics(group),
                "query_count": len(group),
            }
        )

    primary_corpora = {"c121_l", "c1000_l"}
    pooled_class = []
    for method_id in sorted(by_method):
        for query_class in ("lookup", "chained", "enumeration"):
            cells = [
                row
                for row in corpus_class
                if row["method_id"] == method_id
                and row["corpus_id"] in primary_corpora
                and row["query_class"] == query_class
            ]
            if len(cells) != 2:
                continue
            pooled_class.append(
                {
                    "method_id": method_id,
                    "query_class": query_class,
                    **{
                        metric: fmean(cell[metric] for cell in cells)
                        for metric in _METRICS
                        if metric != "fact_recall_at_budget"
                    },
                    **_fraction_fields(
                        sum(
                            (
                                Fraction(cell["fact_recall_exact"])
                                for cell in cells
                            ),
                            Fraction(),
                        )
                        / len(cells)
                    ),
                    "corpus_count": len(cells),
                }
            )

    overall = []
    for method_id, group in sorted(by_method.items()):
        primary = [row for row in group if row["corpus_id"] in primary_corpora]
        if primary:
            overall.append(
                {
                    "method_id": method_id,
                    **_mean_metrics(primary),
                    "query_count": len(primary),
                }
            )

    return {
        "corpus_class": corpus_class,
        "pooled_class": pooled_class,
        "overall_primary": overall,
        "advancement": advancement_decisions(pooled_class),
    }


def advancement_decisions(pooled_class: list[dict]) -> list[dict]:
    by_method_class = {
        (row["method_id"], row["query_class"]): Fraction(
            row["fact_recall_exact"]
        )
        for row in pooled_class
    }
    baseline = {
        query_class: by_method_class.get(("M1", query_class))
        for query_class in ("lookup", "chained", "enumeration")
    }
    decisions = []
    for method_id in ("M2", "M3", "M4", "M5_span", "M6"):
        values = {
            query_class: by_method_class.get((method_id, query_class))
            for query_class in baseline
        }
        complete = all(value is not None for value in [*baseline.values(), *values.values()])
        wins = []
        regressions = []
        if complete:
            wins = [
                query_class
                for query_class in baseline
                if values[query_class] > baseline[query_class]
            ]
            regressions = [
                query_class
                for query_class in baseline
                if baseline[query_class] > 0
                and values[query_class] < Fraction(9, 10) * baseline[query_class]
            ]
        decisions.append(
            {
                "method_id": method_id,
                "advances": bool(complete and wins and not regressions),
                "winning_classes": wins,
                "regressing_classes": regressions,
                "candidate_recall": {
                    key: float(value) if value is not None else None
                    for key, value in values.items()
                },
                "candidate_recall_exact": {
                    key: str(value) if value is not None else None
                    for key, value in values.items()
                },
                "baseline_recall": {
                    key: float(value) if value is not None else None
                    for key, value in baseline.items()
                },
                "baseline_recall_exact": {
                    key: str(value) if value is not None else None
                    for key, value in baseline.items()
                },
            }
        )
    return decisions


_METRICS = (
    "fact_recall_at_budget",
    "domain_coverage",
    "precision_proxy",
    "delivered_characters",
    "latency_ms",
    "index_build_ms",
)


def _mean_metrics(rows: list[dict]) -> dict[str, float | str]:
    metrics = {
        metric: fmean(float(row[metric]) for row in rows)
        for metric in _METRICS
        if metric != "fact_recall_at_budget"
    }
    exact_recall = sum(
        (
            Fraction(
                int(row["matched_fact_count"]),
                int(row["required_fact_count"]),
            )
            for row in rows
        ),
        Fraction(),
    ) / len(rows)
    return {**metrics, **_fraction_fields(exact_recall)}


def _fraction_fields(value: Fraction) -> dict[str, float | str]:
    return {
        "fact_recall_at_budget": float(value),
        "fact_recall_exact": str(value),
    }


def _fact_domain(fact_id: str) -> str:
    parts = fact_id.split("_", 2)
    return parts[1] if len(parts) >= 3 else ""


def _source_role_text(candidate: Candidate, role: str) -> str:
    if candidate.unit_type == "span":
        return candidate.span_text if candidate.role == role else ""
    if role == "user":
        return candidate.user_message
    if role == "assistant":
        return candidate.assistant_message
    return candidate.searchable_text

"""DMR-004 Part 1 record: the measured query population, before any lock.

`AGENTS.md` §4 requires Part 1 to characterize the mechanism empirically before
a test of it is designed, and says findings may change the design before
anything is locked. This module produces the committed artifact that Part 1
stands on.

It builds seven reports:

* `shape` - surface-feature distributions per source, not a summary statistic;
* `classes` - the plan-class distribution of each candidate grammar;
* `reachability` - per-class support against every bar the specification's G4
  would require, checked before locking rather than after (DMR-001 locked an
  unreachable bar and stopped on it);
* `degenerate` - each degenerate output the specification names, demonstrated
  on real queries or shown to be unreachable;
* `names` - a name-to-behavior check on every named concept in section 4;
* `perturbation` - class stability under the section 7 perturbations;
* `leakage` - whether a grammar's output separates the corpora, which is the
  G6 failure mode in measurable form.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from analysis import dmr004_corpus as corpus
from analysis import dmr004_exploration as grammar

RECORD_SCHEMA = "dmr004-part1-v1"

#: Section 8 lists conjunction and finite enumeration as separately gated
#: classes. A class cannot carry a rate bar on a corpus that holds a handful of
#: instances; this is the count below which no bar is registered.
MIN_INSTANCES_FOR_A_RATE_BAR = 30


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _percentile(ordered: Sequence[float], fraction: float) -> float:
    if not ordered:
        return float("nan")
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def shape_report(records: Sequence[corpus.QueryRecord]) -> dict[str, Any]:
    out: dict[str, Any] = {"sources": {}}
    for source, subset in corpus.iter_by_source(records):
        texts = corpus.queries_only(subset)
        lengths = sorted(len(text) for text in texts)
        words = sorted(len(text.split()) for text in texts)
        features = {}
        for name, pattern in grammar.PATTERNS.items():
            hits = sum(1 for text in texts if pattern.search(grammar.canonical(text)))
            features[name] = {"count": hits, "share": hits / len(texts)}
        for name, pattern in (("aggregate_frame", grammar.AGGREGATE), ("cardinality_like", grammar.CARDINALITY)):
            hits = sum(1 for text in texts if pattern.search(grammar.canonical(text)))
            features[name] = {"count": hits, "share": hits / len(texts)}
        multi = sum(1 for text in texts if grammar.interrogative_frames(grammar.canonical(text)) >= 2)
        features["two_or_more_interrogative_frames"] = {"count": multi, "share": multi / len(texts)}
        nfkc = sum(1 for text in texts if not grammar.canonical_is_length_preserving(text))
        features["canonicalization_changes_length"] = {"count": nfkc, "share": nfkc / len(texts)}
        out["sources"][source] = {
            "count": len(texts),
            "distinct": len(set(texts)),
            "chars": {
                "min": lengths[0],
                "median": _percentile(lengths, 0.5),
                "p95": _percentile(lengths, 0.95),
                "max": lengths[-1],
            },
            "words": {
                "min": words[0],
                "median": _percentile(words, 0.5),
                "p95": _percentile(words, 0.95),
                "max": words[-1],
            },
            "features": features,
        }
    return out


def class_report(records: Sequence[corpus.QueryRecord]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, compile_fn in grammar.GRAMMARS.items():
        per_source: dict[str, Any] = {}
        for source, subset in corpus.iter_by_source(records):
            texts = corpus.queries_only(subset)
            counts = Counter(compile_fn(text).plan_class for text in texts)
            per_source[source] = {
                cls: {"count": counts[cls], "share": counts[cls] / len(texts)}
                for cls in grammar.PLAN_CLASSES
            }
        texts = corpus.queries_only(records)
        counts = Counter(compile_fn(text).plan_class for text in texts)
        codes: Counter[str] = Counter()
        for text in texts:
            for code in compile_fn(text).codes:
                codes[code] += 1
        fractions = sorted(grammar.span_lengths(texts, name))
        out[name] = {
            "by_source": per_source,
            "all": {
                cls: {"count": counts[cls], "share": counts[cls] / len(texts)}
                for cls in grammar.PLAN_CLASSES
            },
            "ambiguity_codes": dict(sorted(codes.items())),
            "span_coverage": {
                "spans": len(fractions),
                "median_fraction_of_query": _percentile(fractions, 0.5),
                "p90_fraction_of_query": _percentile(fractions, 0.9),
                "share_covering_90_percent_or_more": (
                    sum(1 for value in fractions if value >= 0.90) / len(fractions)
                    if fractions
                    else None
                ),
            },
        }
    return out


def migration_report(records: Sequence[corpus.QueryRecord]) -> dict[str, Any]:
    """Where R1's plans go under R2, and what the difference is worth.

    The `false_finite` set is the point of the whole report: queries R1 marks
    with a fixed evidence obligation whose answers are aggregates over an
    unknown number of stored items. Section 1 says it is better to say
    completion cannot be determined than to call a partly understood request
    complete, so every member of this set is a violation of the design's own
    stated principle.
    """
    texts = corpus.queries_only(records)
    moves: Counter[tuple[str, str]] = Counter()
    false_finite: list[str] = []
    for text in texts:
        before = grammar.compile_r1(text).plan_class
        after = grammar.compile_r2(text).plan_class
        moves[(before, after)] += 1
        if before in ("LOOKUP", "HISTORY", "ENUMERATE_N") and after == "OPEN":
            false_finite.append(text)
    return {
        "transitions": [
            {"from": key[0], "to": key[1], "count": value}
            for key, value in sorted(moves.items(), key=lambda item: -item[1])
        ],
        "false_finite": {
            "count": len(false_finite),
            "share": len(false_finite) / len(texts),
            "examples": false_finite[:12],
        },
    }


def reachability_report(records: Sequence[corpus.QueryRecord]) -> dict[str, Any]:
    """PF4, applied per bar rather than per statistic.

    DMR-001 locked one bar without checking it could be met by any admissible
    result and stopped on it. The check here is deliberately blunt: for each
    class the specification would gate, how many instances exist to gate on?
    """
    texts = corpus.queries_only(records)
    rows = []
    for name, compile_fn in grammar.GRAMMARS.items():
        counts = Counter(compile_fn(text).plan_class for text in texts)
        for cls in grammar.PLAN_CLASSES:
            count = counts[cls]
            rows.append(
                {
                    "grammar": name,
                    "class": cls,
                    "instances": count,
                    "share": count / len(texts),
                    "supports_rate_bar": count >= MIN_INSTANCES_FOR_A_RATE_BAR,
                    "finest_resolvable_rate": (1.0 / count) if count else None,
                }
            )
    return {"minimum_instances_for_a_rate_bar": MIN_INSTANCES_FOR_A_RATE_BAR, "rows": rows}


def _first_matching(texts: Sequence[str], predicate) -> str | None:
    for text in texts:
        if predicate(text):
            return text
    return None


def degenerate_report(records: Sequence[corpus.QueryRecord]) -> dict[str, Any]:
    """Section 7 item 5, demonstrated on real queries rather than asserted."""
    texts = corpus.queries_only(records)
    states: dict[str, Any] = {}

    for name, compile_fn in grammar.GRAMMARS.items():
        counts = Counter(compile_fn(text).plan_class for text in texts)
        states[f"{name}:every_query_open"] = {
            "reached": counts["OPEN"] == len(texts),
            "observed_share": counts["OPEN"] / len(texts),
        }
        states[f"{name}:every_query_lookup"] = {
            "reached": counts["LOOKUP"] == len(texts),
            "observed_share": counts["LOOKUP"] / len(texts),
        }

    zero_length = _first_matching(
        texts,
        lambda text: (plan := grammar.compile_r2(text)).span is not None
        and plan.span[1] <= plan.span[0],
    )
    states["zero_length_span"] = {
        "reached": zero_length is not None,
        "example": zero_length,
        "note": "the span rule returns None rather than an empty span; the state is unreachable by construction",
    }

    whole_query = [
        text
        for text in texts
        if (plan := grammar.compile_r2(text)).span is not None
        and (plan.span[1] - plan.span[0]) / len(text) >= 0.95
    ]
    states["span_covers_whole_query"] = {
        "reached": bool(whole_query),
        "count": len(whole_query),
        "share_of_spanned": len(whole_query) / max(1, len(grammar.span_lengths(texts, "R2"))),
        "example": whole_query[0] if whole_query else None,
        "note": "the surrogate the specification's §9 warns about, realized",
    }

    counts_seen = [
        plan.requested_count
        for text in texts
        if (plan := grammar.compile_r2(text)).requested_count is not None
    ]
    big = [value for value in counts_seen if value > 10]
    states["excessive_cardinality"] = {
        "reached": bool(big),
        "count": len(big),
        "largest_requested_count": max(counts_seen, default=None),
        "threshold": 10,
    }

    duplicates = Counter(texts)
    states["duplicate_query_text"] = {
        "reached": any(value > 1 for value in duplicates.values()),
        "max_repeats": max(duplicates.values()),
    }

    # Not `span is None`: R2's aggregate branch also drops the span, so that test
    # would count 318 queries that do have a perfectly good interrogative frame.
    no_frame = [
        text for text in texts if "NO_INTERROGATIVE_FRAME" in grammar.compile_r2(text).codes
    ]
    states["no_interrogative_frame"] = {
        "reached": bool(no_frame),
        "count": len(no_frame),
        "example": no_frame[0] if no_frame else None,
    }
    return states


def name_check_report(records: Sequence[corpus.QueryRecord]) -> dict[str, Any]:
    """Does each named concept in section 4 do what its name says, on real data?"""
    texts = corpus.queries_only(records)
    checks: dict[str, Any] = {}

    history = [text for text in texts if grammar.compile_r1(text).plan_class == "HISTORY"]
    pointers = [text for text in history if grammar.PATTERNS["discourse_pointer"].search(grammar.canonical(text))]
    checks["HISTORY"] = {
        "claim": "an explicit request for how a value changed over time",
        "r1_instances": len(history),
        "of_which_discourse_pointers": len(pointers),
        "verdict": "FAILS its name under R1"
        if pointers
        else "holds",
        "evidence": pointers[:3],
        "note": "'our previous conversation about X' names where to look, not what changed",
    }

    cardinal = [
        text
        for text in texts
        if grammar.compile_r1(text).plan_class == "ENUMERATE_N"
    ]
    not_really = [
        text
        for text in cardinal
        if "NUMERAL_NOT_CARDINALITY" in grammar.compile_r2(text).codes
    ]
    checks["ENUMERATE_N / requested_count"] = {
        "claim": "an explicit finite cardinality of requested list members",
        "r1_instances": len(cardinal),
        "of_which_not_a_cardinality": len(not_really),
        "verdict": "FAILS its name under R1" if not_really else "holds",
        "evidence": not_really[:3],
        "note": "prices, dates, model numbers and ordinals all match an integer-plus-plural-noun rule",
    }

    conj = [text for text in texts if grammar.compile_r2(text).plan_class == "CONJUNCT"]
    checks["CONJUNCT"] = {
        "claim": "two or more independently valid lookup clauses",
        "instances": len(conj),
        "verdict": "not measurable" if len(conj) < MIN_INSTANCES_FOR_A_RATE_BAR else "measurable",
        "evidence": conj[:3],
    }

    lookups = [text for text in texts if grammar.compile_r2(text).plan_class == "LOOKUP"]
    checks["LOOKUP / ONE_EVIDENCE"] = {
        "claim": "one interrogative frame satisfied by one stored evidence item",
        "instances": len(lookups),
        "aggregate_frames_remaining": sum(
            1 for text in lookups if grammar.AGGREGATE.search(grammar.canonical(text))
        ),
        "verdict": "holds under R2 by construction; R1's version is the false-finite set",
    }

    spans = grammar.span_lengths(texts, "R2")
    checks["source_span"] = {
        "claim": "the contiguous substring the query asks about",
        "median_fraction_of_query": _percentile(sorted(spans), 0.5),
        "verdict": "WEAK - a span this wide overlaps any gold span",
    }

    checks["completeness_mode"] = {
        "claim": "FINITE means a fixed number of evidence items completes the request",
        "r2_finite_share": sum(
            1 for text in texts if grammar.compile_r2(text).plan_class != "OPEN"
        )
        / len(texts),
        "verdict": "holds only once aggregate frames are excluded",
    }
    return checks


def perturbation_report(records: Sequence[corpus.QueryRecord]) -> dict[str, Any]:
    texts = corpus.queries_only(records)
    out: dict[str, Any] = {}
    for name in grammar.GRAMMARS:
        table = grammar.perturbation_stability(texts, name)
        out[name] = {
            key: {
                "applicable": value["applicable"],
                "changed": value["changed"],
                "rate": value["rate"],
                "examples": [
                    {"query": item[0][:160], "from": item[1], "to": item[2]}
                    for item in value["examples"][:3]
                ],
            }
            for key, value in table.items()
        }
    return out


def leakage_report(records: Sequence[corpus.QueryRecord]) -> dict[str, Any]:
    """G6 in measurable form: does the grammar separate the corpora?

    A conjunction rule that fires on the house scripts and never on natural
    questions is not a conjunction rule, it is a corpus detector.
    """
    internal = corpus.queries_only([r for r in records if r.source == "internal"])
    external = corpus.queries_only([r for r in records if r.source == "longmemeval"])

    probes = {
        "coordinated_interrogative": re.compile(
            r",?\s+and\s+(?:what|who|where|when|which|why|how|did|do|does|is|are|was|were)\b\s",
            re.I,
        ),
        "imperative_sequence": re.compile(
            r"\b(?:name|state|list|give|identify|tell me|provide|describe)\b.*"
            r"\b(?:then|and then)\b\s*(?:name|state|list|give|identify|tell me|provide|describe)\b",
            re.I,
        ),
        "coordinated_imperative": re.compile(
            r"\b(?:name|state|list|give|identify|tell me|provide|describe)\b[^,?.]*\band\b[^,?.]*",
            re.I,
        ),
        "comma_list_of_three": re.compile(r"\b\w+[^,?.]*,[^,?.]*,[^,?.]*\band\b", re.I),
        "top_level_semicolon": re.compile(r";"),
    }
    rows = []
    for name, pattern in probes.items():
        inside = sum(1 for text in internal if pattern.search(grammar.canonical(text)))
        outside = sum(1 for text in external if pattern.search(grammar.canonical(text)))
        rows.append(
            {
                "probe": name,
                "internal_count": inside,
                "internal_share": inside / len(internal),
                "longmemeval_count": outside,
                "longmemeval_share": outside / len(external),
                "separation": abs(inside / len(internal) - outside / len(external)),
            }
        )

    label_tables: dict[str, Any] = {}
    labelled = [r for r in records if r.source == "longmemeval"]
    for name, compile_fn in grammar.GRAMMARS.items():
        table: Counter[tuple[str, str]] = Counter()
        for record in labelled:
            table[(str(record.label), compile_fn(record.text).plan_class)] += 1
        labels = sorted({str(r.label) for r in labelled})
        label_tables[name] = {
            label: {cls: table[(label, cls)] for cls in grammar.PLAN_CLASSES} for label in labels
        }
    return {"corpus_separation": rows, "benchmark_label_confusion": label_tables}


def build_part1_record(repository_root: Path) -> dict[str, Any]:
    records = corpus.read_cache(repository_root)
    record: dict[str, Any] = {
        "schema": RECORD_SCHEMA,
        "corpus": {
            "count": len(records),
            "digest": corpus.corpus_digest(records),
            "dataset_sha256": corpus.DATASET_SHA256,
        },
        "shape": shape_report(records),
        "classes": class_report(records),
        "migration": migration_report(records),
        "reachability": reachability_report(records),
        "degenerate": degenerate_report(records),
        "names": name_check_report(records),
        "perturbation": perturbation_report(records),
        "leakage": leakage_report(records),
    }
    serialized = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    record["record_sha256"] = _sha256(serialized)
    return record


def write_part1_record(repository_root: Path) -> Path:
    record = build_part1_record(repository_root)
    path = (
        repository_root
        / "experiments/components/biological_memory/dmr_004/artifacts/part1_record.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path

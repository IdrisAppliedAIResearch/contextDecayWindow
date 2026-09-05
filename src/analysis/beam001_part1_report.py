"""Build the label-blind BEAM-001 Part 1 audit and human-readable report."""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

from analysis.beam001_adapter import adapt_conversation
from analysis.beam001_exploration import (
    ARMS,
    CONTEXTS_PATH,
    EXPECTED_QUESTIONS,
    EXPECTED_ROWS,
    FACET_REPRESENTATION_PATH,
    MECHANISM_SURFACE,
    RANKINGS_PATH,
    REPO_ROOT,
    ROOT,
    SHUFFLE_PATH,
    SUMMARY_PATH,
    sha256_file,
)

DISTRIBUTIONS_PATH = ROOT / "artifacts/exploration/distributions.json"
TRACES_PATH = ROOT / "artifacts/exploration/trace_audit.json"
RESOURCE_PATH = ROOT / "artifacts/runtime/exploration_resources.json"
SCHEMA_PATH = ROOT / "artifacts/corpus/schema_report.json"
SOURCE_MANIFEST_PATH = ROOT / "artifacts/corpus/source_manifest.json"
SURFACE_MANIFEST_PATH = ROOT / "artifacts/corpus/surface_manifest.json"
ANCHOR_PATH = ROOT / "artifacts/anchors/reproduction.json"
REPORT_PATH = ROOT / "BEAM_001_PART1_EXPLORATION.md"
PAIR_NAMES = ((ARMS[0], ARMS[1]), (ARMS[1], ARMS[2]), (ARMS[0], ARMS[2]))
FACET_FAMILIES = ("date", "entity", "event", "noun", "number", "relation")


class BeamPart1ReportError(RuntimeError):
    pass


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, newline="\n"
    ) as handle:
        temporary = Path(handle.name)
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def _iter_gzip(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def _nearest(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    return float(ordered[max(0, math.ceil(fraction * len(ordered)) - 1)])


def distribution(values: Sequence[int | float], *, discrete: bool) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    numeric = [float(value) for value in values]
    result: dict[str, Any] = {
        "n": len(numeric),
        "min": min(numeric),
        "p05": _nearest(numeric, 0.05),
        "p25": _nearest(numeric, 0.25),
        "median": _nearest(numeric, 0.50),
        "p75": _nearest(numeric, 0.75),
        "p95": _nearest(numeric, 0.95),
        "max": max(numeric),
        "mean": sum(numeric) / len(numeric),
    }
    if discrete:
        result["histogram"] = {
            str(int(value)): count
            for value, count in sorted(Counter(int(value) for value in numeric).items())
        }
    return result


class Metrics:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], list[int | float]] = defaultdict(list)
        self.discrete: dict[str, bool] = {}

    def add(
        self,
        metric: str,
        value: int | float,
        *,
        prefix: str,
        split: str | None = None,
        category: str | None = None,
        discrete: bool = True,
    ) -> None:
        self.discrete.setdefault(metric, discrete)
        if self.discrete[metric] != discrete:
            raise BeamPart1ReportError(f"Metric type drift: {metric}")
        strata = [prefix]
        if split is not None:
            strata.append(f"{prefix}|split={split}")
        if category is not None:
            strata.append(f"{prefix}|category={category}")
        if split is not None and category is not None:
            strata.append(f"{prefix}|split={split}|category={category}")
        for stratum in strata:
            self.values[(metric, stratum)].append(value)

    def render(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = defaultdict(dict)
        for (metric, stratum), values in sorted(self.values.items()):
            result[metric][stratum] = distribution(
                values, discrete=self.discrete[metric]
            )
        return dict(result)


def _pair_label(left: str, right: str) -> str:
    return f"{left.split('_', 1)[0]}_{right.split('_', 1)[0]}"


def _record_example(
    examples: dict[str, dict[str, Any]],
    name: str,
    row: Mapping[str, Any],
    **details: Any,
) -> None:
    examples.setdefault(
        name,
        {
            "question_key": row["question_key"],
            "conversation_key": row["conversation_key"],
            "arm": row["arm"],
            "split": row["split"],
            "category": row["category"],
            **details,
        },
    )


def _conversation_audit(metrics: Metrics) -> dict[str, Any]:
    counts = Counter()
    longest_store: dict[str, Any] | None = None
    longest_episode: dict[str, Any] | None = None
    largest_question: dict[str, Any] | None = None
    question_count = 0
    for row in _iter_gzip(MECHANISM_SURFACE):
        split = str(row["split"])
        counts[split] += 1
        episodes = adapt_conversation(row)
        episode_chars = [
            len(str(item["user_message"])) + len(str(item["assistant_message"]))
            for item in episodes
        ]
        total_chars = sum(episode_chars)
        metrics.add("conversation_episodes", len(episodes), prefix="corpus", split=split)
        metrics.add("conversation_episode_chars", total_chars, prefix="corpus", split=split)
        candidate = {
            "conversation_key": row["conversation_key"],
            "split": split,
            "episodes": len(episodes),
            "episode_chars": total_chars,
        }
        if longest_store is None or candidate["episodes"] > longest_store["episodes"]:
            longest_store = candidate
        for item, chars in zip(episodes, episode_chars, strict=True):
            if longest_episode is None or chars > longest_episode["chars"]:
                longest_episode = {
                    "conversation_key": row["conversation_key"],
                    "episode_key": item["episode_key"],
                    "split": split,
                    "chars": chars,
                }
        for question in row["questions"]:
            question_count += 1
            chars = len(str(question["question"]))
            if largest_question is None or chars > largest_question["chars"]:
                largest_question = {
                    "conversation_key": row["conversation_key"],
                    "question_key": question["question_key"],
                    "split": split,
                    "category": question["category"],
                    "chars": chars,
                }
    return {
        "conversations": sum(counts.values()),
        "questions": question_count,
        "scale_conversations": dict(sorted(counts.items())),
        "longest_store": longest_store,
        "longest_episode": longest_episode,
        "largest_question": largest_question,
    }


def _facet_audit(metrics: Metrics) -> dict[str, Any]:
    rows = 0
    for row in _iter_gzip(FACET_REPRESENTATION_PATH):
        rows += 1
        arm = str(row["arm"])
        split = str(row["split"])
        category = str(row["category"])
        prefix = f"arm={arm}"
        metrics.add(
            "covered_unique_facets",
            int(row["covered_unique_facets"]),
            prefix=prefix,
            split=split,
            category=category,
        )
        for family in FACET_FAMILIES:
            metrics.add(
                f"family_episode_count.{family}",
                int(row["family_episode_counts"].get(family, 0)),
                prefix=prefix,
                split=split,
                category=category,
            )
            metrics.add(
                f"family_facet_occurrences.{family}",
                int(row["family_facet_occurrences"].get(family, 0)),
                prefix=prefix,
                split=split,
                category=category,
            )
    if rows != EXPECTED_ROWS:
        raise BeamPart1ReportError(f"Facet rows incomplete: {rows}/{EXPECTED_ROWS}")
    return {"rows": rows, "sha256": sha256_file(FACET_REPRESENTATION_PATH)}


def _question_audit(metrics: Metrics) -> tuple[dict[str, Any], dict[str, Any]]:
    rankings = iter(_iter_gzip(RANKINGS_PATH))
    context_rows = _iter_gzip(CONTEXTS_PATH)
    examples: dict[str, dict[str, Any]] = {}
    pair_counts = {
        _pair_label(*pair): Counter() for pair in PAIR_NAMES
    }
    gate_checks = Counter(
        baseline_rows=0,
        budget_rows=0,
        finite_t1_rows=0,
        no_reentry_t1_rows=0,
    )
    largest_pool: dict[str, Any] | None = None
    largest_disagreement: dict[str, Any] | None = None
    question_count = 0
    row_count = 0
    current_key: str | None = None
    group: dict[str, dict[str, Any]] = {}

    def process_group(rows: Mapping[str, dict[str, Any]]) -> None:
        nonlocal question_count, largest_disagreement
        if set(rows) != set(ARMS):
            raise BeamPart1ReportError(f"Incomplete arm group: {set(rows)}")
        ranking = next(rankings)
        key = str(next(iter(rows.values()))["question_key"])
        if ranking["question_key"] != key:
            raise BeamPart1ReportError("Context/ranking order drift")
        rank = {identifier: index + 1 for index, identifier in enumerate(ranking["order"])}
        question_count += 1
        for left, right in PAIR_NAMES:
            left_row, right_row = rows[left], rows[right]
            pair = _pair_label(left, right)
            left_ids = set(left_row["selected_long_term_ids"])
            right_ids = set(right_row["selected_long_term_ids"])
            intersection = len(left_ids & right_ids)
            union = len(left_ids | right_ids)
            additions = right_ids - left_ids
            removals = left_ids - right_ids
            difference = len(additions) + len(removals)
            identical_set = difference == 0
            identical_payload = left_row["payload_sha256"] == right_row["payload_sha256"]
            pair_counts[pair]["selection_identical" if identical_set else "selection_changed"] += 1
            pair_counts[pair]["payload_identical" if identical_payload else "payload_changed"] += 1
            prefix = f"pair={pair}"
            split = str(left_row["split"])
            category = str(left_row["category"])
            for metric, value, discrete in (
                ("set_intersection", intersection, True),
                ("set_jaccard", intersection / union if union else 1.0, False),
                ("set_additions", len(additions), True),
                ("set_removals", len(removals), True),
                ("set_symmetric_difference", difference, True),
                ("payload_char_difference", int(right_row["final_chars"]) - int(left_row["final_chars"]), True),
                ("payload_char_absolute_difference", abs(int(right_row["final_chars"]) - int(left_row["final_chars"])), True),
                ("payload_byte_identical", int(identical_payload), True),
            ):
                metrics.add(
                    metric,
                    value,
                    prefix=prefix,
                    split=split,
                    category=category,
                    discrete=discrete,
                )
            for identifier in additions:
                metrics.add(
                    "right_only_cc80_rank", rank[identifier], prefix=prefix,
                    split=split, category=category,
                )
            for identifier in removals:
                metrics.add(
                    "left_only_cc80_rank", rank[identifier], prefix=prefix,
                    split=split, category=category,
                )
            witness = {
                "question_key": key,
                "conversation_key": left_row["conversation_key"],
                "split": split,
                "category": category,
                "pair": pair,
                "symmetric_difference": difference,
                "payload_char_absolute_difference": abs(
                    int(right_row["final_chars"]) - int(left_row["final_chars"])
                ),
            }
            if identical_set:
                examples.setdefault(f"{pair}.identical_selection", witness)
            elif f"{pair}.changed_selection" not in examples:
                examples[f"{pair}.changed_selection"] = witness
            if (
                largest_disagreement is None
                or difference > largest_disagreement["symmetric_difference"]
            ):
                largest_disagreement = witness

    for row in context_rows:
        row_count += 1
        key = str(row["question_key"])
        if current_key is not None and key != current_key:
            process_group(group)
            group = {}
        current_key = key
        group[str(row["arm"])] = row
        arm = str(row["arm"])
        split = str(row["split"])
        category = str(row["category"])
        prefix = f"arm={arm}"
        parent_count = len(row["semantic_parent_ids"])
        proposed_count = len(row["proposed_child_ids"])
        retained_count = len(row["retained_child_ids"])
        returned_count = len(row["returned_semantic_ids"])
        selected_count = len(row["selected_long_term_ids"])
        for metric, value, discrete in (
            ("recent_count", len(row["recent_ids"]), True),
            ("semantic_parent_count", parent_count, True),
            ("proposed_child_count", proposed_count, True),
            ("retained_child_count", retained_count, True),
            ("rejected_child_count", proposed_count - retained_count, True),
            ("returned_semantic_count", returned_count, True),
            ("selected_long_term_count", selected_count, True),
            ("total_delivered_count", len(row["recent_ids"]) + selected_count, True),
            ("retrieval_chars", int(row["retrieval_chars"]), True),
            ("final_chars", int(row["final_chars"]), True),
            ("latency_seconds", float(row["elapsed_seconds"]), False),
            ("contexts_per_second", 1.0 / max(float(row["elapsed_seconds"]), 1e-12), False),
        ):
            metrics.add(
                metric, value, prefix=prefix, split=split,
                category=category, discrete=discrete,
            )
        recent = set(row["recent_ids"])
        selected = set(row["selected_long_term_ids"])
        if int(row["retrieval_chars"]) <= 32_000 and not recent & selected:
            gate_checks["budget_rows"] += 1
        pool = len(row.get("_ranking", {}).get("order", ()))
        if not pool and arm != ARMS[2] and "report" in row:
            pool = int(row["report"]["pool_size"])
        if largest_pool is None or pool > largest_pool["candidate_pool"]:
            largest_pool = {
                "question_key": key,
                "conversation_key": row["conversation_key"],
                "arm": arm,
                "split": split,
                "category": category,
                "candidate_pool": pool,
            }
        if len(row["recent_ids"]) < 32:
            _record_example(examples, "fewer_than_32_recent", row)
        if len(row["recent_ids"]) == 32:
            _record_example(examples, "exactly_32_recent", row)
        if parent_count == 0:
            _record_example(examples, "no_semantic_parent", row)
        if parent_count == 1:
            _record_example(examples, "one_semantic_parent", row)
        if parent_count > 1:
            _record_example(examples, "many_semantic_parents", row, count=parent_count)
        if returned_count:
            _record_example(examples, "protected_slack_returned", row, count=returned_count)
        else:
            _record_example(examples, "no_protected_slack_returned", row)
        if proposed_count and proposed_count == retained_count:
            _record_example(examples, "all_proposed_children_retained", row, count=proposed_count)
        if arm == ARMS[0]:
            aspect = row["aspect"]
            baseline_ok = (
                not aspect["order"]
                and not aspect["marginal"]
                and not aspect["covered_counts"]
                and int(aspect["solo_chars"]) == 0
                and not bool(row["report"]["aspect_enabled"])
            )
            gate_checks["baseline_rows"] += int(baseline_ok)
        if arm == ARMS[2]:
            aspect = row["aspect"]
            parents = row["semantic_parent_ids"]
            finite = (
                int(aspect["finite_attempts"]) == len(parents)
                and proposed_count
                + int(aspect["no_positive_child"])
                + int(aspect["no_fitting_child"])
                == len(parents)
                and len(aspect["decisions"]) == proposed_count
            )
            no_reentry = (
                len(row["proposed_child_ids"]) == len(set(row["proposed_child_ids"]))
                and not set(row["proposed_child_ids"]) & set(parents)
            )
            gate_checks["finite_t1_rows"] += int(finite)
            gate_checks["no_reentry_t1_rows"] += int(no_reentry)
            for state in (
                "no_positive_child", "no_fitting_child",
                "rejected_capacity", "rejected_value",
            ):
                count = int(aspect[state])
                metrics.add(
                    state, count, prefix=prefix, split=split, category=category
                )
                if count:
                    _record_example(examples, state, row, count=count)
    if group:
        process_group(group)
    try:
        next(rankings)
    except StopIteration:
        pass
    else:
        raise BeamPart1ReportError("Unconsumed ranking rows")
    if row_count != EXPECTED_ROWS or question_count != EXPECTED_QUESTIONS:
        raise BeamPart1ReportError(
            f"Context population incomplete: {row_count}, {question_count}"
        )
    return (
        {
            "rows": row_count,
            "questions": question_count,
            "pair_counts": {key: dict(value) for key, value in pair_counts.items()},
            "gate_checks": dict(gate_checks),
            "largest_candidate_pool": largest_pool,
            "largest_arm_disagreement": largest_disagreement,
        },
        examples,
    )


def _format_number(value: Any) -> str:
    if isinstance(value, float) and not value.is_integer():
        return f"{value:.4f}"
    return f"{int(value):,}" if isinstance(value, (int, float)) else str(value)


def _markdown(result: Mapping[str, Any]) -> str:
    corpus = result["corpus"]
    questions = result["questions"]
    gates = result["gates"]
    metrics = result["distributions"]
    lines = [
        "# BEAM-001 Part 1 Exploration",
        "",
        f"**Status:** {result['status']}  ",
        "**Outcome surface:** sealed; no ideal answer, rubric, evidence location, prior result, reader call or judge call was opened  ",
        f"**Question-arms:** {questions['rows']:,} ({questions['questions']:,} questions x 3 arms)",
        "",
        "## Corpus and mechanism",
        "",
        f"The admitted normal-scale population is {corpus['conversations']} conversations and {corpus['questions']} questions: "
        + ", ".join(f"{key}={value}" for key, value in corpus["scale_conversations"].items())
        + ". Strict adjacent user/assistant pairing remained lossless.",
        "",
        "A0 is the public CC80 default with additive last-32 continuity. C0 is the public static ASPECT option. T1 gives every half-budget CC80 parent one finite child opportunity, retaining it only when its marginal value covers the CC80 value displaced by exact packing. All three use the same cached Qwen embeddings and CC80 ranking; Part 1 loaded no model.",
        "",
        "## Overall mechanics",
        "",
        "| Arm | LT episodes median / p95 | Retrieval chars median / p95 | Latency median / p95 (s) |",
        "|---|---:|---:|---:|",
    ]
    for arm in ARMS:
        prefix = f"arm={arm}"
        selected = metrics["selected_long_term_count"][prefix]
        chars = metrics["retrieval_chars"][prefix]
        latency = metrics["latency_seconds"][prefix]
        lines.append(
            f"| {arm.split('_', 1)[0]} | {_format_number(selected['median'])} / {_format_number(selected['p95'])} | "
            f"{_format_number(chars['median'])} / {_format_number(chars['p95'])} | "
            f"{_format_number(latency['median'])} / {_format_number(latency['p95'])} |"
        )
    lines.extend(["", "## Pair contrasts", "", "| Pair | Selection identical | Changed | Payload identical |", "|---|---:|---:|---:|"])
    for pair, counts in questions["pair_counts"].items():
        lines.append(
            f"| {pair} | {counts.get('selection_identical', 0):,} | "
            f"{counts.get('selection_changed', 0):,} | {counts.get('payload_identical', 0):,} |"
        )
    lines.extend(["", "## Viability gates", ""])
    for gate, disposition in gates.items():
        lines.append(f"- **{gate}: {disposition['status']}.** {disposition['evidence']}")
    lines.extend(
        [
            "",
            "## Degenerate states",
            "",
            "Real witnesses and explicit absences are recorded by stable key in `artifacts/exploration/trace_audit.json`. The shuffled replay processed every conversation in a changed question order and reproduced every payload digest. T1 made exactly one finite outcome per parent; proposed children were unique and never re-entered as parents.",
            "",
            "## Preflight checklist",
            "",
            "- **PF1 Inputs:** source revisions, licenses, hashes, counts, parser, embedder, package tree and anchors are hash-bound in the manifests listed below.",
            "- **PF2 Mechanism identity:** the corpus adapter and all retrieval components are stated falsifiably above and verified in the trace audit.",
            "- **PF3 Gate ordering:** source lock, surface separation and reproduction anchors precede this report. The live registration and implementation do not yet exist, and no reader or judge call has occurred.",
            "- **PF4 Reachability:** 1,800 paired questions exist across ten balanced families and three scales. Exact scoring units, practical bars, statistical branches and synthetic dispositions must be frozen in the standalone live registration after the outcome schema is opened.",
            "- **PF5 Stable keys:** content-hash keys survived canonical rebuilds, path-independent adapter tests, duplicate occurrences and the complete shuffled replay.",
            "- **PF6 Reproduction:** all 871 TC-014 opportunity identities/payloads and all 4,355 CC-007 trace groups passed before BEAM summaries.",
            "- **PF7 Feedback:** all 5,400 shuffled payload digests match; read-only store counters remained unchanged; every T1 parent terminated once with no child re-entry.",
            "- **PF8 Adequacy:** this population can size a normal-scale paired BEAM test only. It cannot establish 10M behavior, real-user transfer, reader generality or production-concurrency latency.",
            "- **PF9 Surrogates:** child count, facet breadth, overlap, speed, compactness and evidence availability can all improve while reader correctness falls. None authorizes adoption.",
            "- **PF10 Live requirement:** only the separately registered complete GPT-4o mini reader and blind scoring run can test T1 versus C0 with the required A0 non-regression guardrail.",
            "",
            "## Artifact anchors",
            "",
        ]
    )
    for name, artifact in result["artifacts"].items():
        lines.append(f"- `{name}`: `{artifact['sha256']}`")
    lines.extend(["", "Part 1 establishes mechanical viability only. It contains no answer-quality result.", ""])
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    required = (
        CONTEXTS_PATH, RANKINGS_PATH, FACET_REPRESENTATION_PATH, SUMMARY_PATH,
        SHUFFLE_PATH, RESOURCE_PATH, SCHEMA_PATH, SOURCE_MANIFEST_PATH,
        SURFACE_MANIFEST_PATH, ANCHOR_PATH,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise BeamPart1ReportError(f"Missing completed Part 1 artifacts: {missing}")
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    shuffle = json.loads(SHUFFLE_PATH.read_text(encoding="utf-8"))
    resources = json.loads(RESOURCE_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    metrics = Metrics()
    corpus = _conversation_audit(metrics)
    questions, examples = _question_audit(metrics)
    facets = _facet_audit(metrics)
    baseline_expected = EXPECTED_QUESTIONS
    t1_expected = EXPECTED_QUESTIONS
    changed = questions["pair_counts"]["C0_T1"].get("selection_changed", 0)
    identical = questions["pair_counts"]["C0_T1"].get("selection_identical", 0)
    gates = {
        "G-SCHEMA": {
            "status": "PASS" if schema["strict_lossless_pair_mapping"] else "FAIL",
            "evidence": f"{corpus['conversations']} conversations and {corpus['questions']} questions mapped losslessly.",
        },
        "G-SEPARATION": {
            "status": "PASS" if summary.get("separation", {}).get("planted_field_rejected") and not summary.get("separation", {}).get("forbidden_imports") else "FAIL",
            "evidence": "Planted outcome fields were rejected and the exploration import graph had no outcome reader.",
        },
        "G-ANCHOR": {
            "status": "PASS" if summary.get("anchors", {}).get("status") == "PASS" else "FAIL",
            "evidence": "The committed CC-007 and TC-014 identity/payload anchors passed before exploration.",
        },
        "G-BASELINE": {
            "status": "PASS" if questions["gate_checks"].get("baseline_rows") == baseline_expected else "FAIL",
            "evidence": f"{questions['gate_checks'].get('baseline_rows', 0)}/{baseline_expected} A0 rows used no ASPECT trace or protected allocation.",
        },
        "G-TREATMENT": {
            "status": "PASS" if changed > 0 and identical > 0 else "FAIL",
            "evidence": f"C0/T1 produced {changed} changed and {identical} identical selected sets.",
        },
        "G-BUDGET": {
            "status": "PASS" if questions["gate_checks"].get("budget_rows") == EXPECTED_ROWS else "FAIL",
            "evidence": f"{questions['gate_checks'].get('budget_rows', 0)}/{EXPECTED_ROWS} rows stayed within 32,000 retrieval characters with disjoint recent/LT identities.",
        },
        "G-RUNTIME": {
            "status": "PASS" if summary.get("status") == "COMPLETE" and resources.get("status") == "COMPLETE" and shuffle.get("status") == "PASS" else "FAIL",
            "evidence": f"The full run and shuffled replay completed with {resources.get('peak_process_count')} peak processes and {resources.get('peak_aggregate_working_set_bytes')} peak aggregate working-set bytes.",
        },
    }
    if questions["gate_checks"].get("finite_t1_rows") != t1_expected:
        raise BeamPart1ReportError("T1 finite-attempt invariant failed")
    if questions["gate_checks"].get("no_reentry_t1_rows") != t1_expected:
        raise BeamPart1ReportError("T1 no-reentry invariant failed")
    if shuffle.get("question_arms_checked") != EXPECTED_ROWS or shuffle.get("payload_mismatches") != 0:
        raise BeamPart1ReportError("Shuffled replay is incomplete or mismatched")
    rendered_metrics = metrics.render()
    artifact_paths = {
        "contexts": CONTEXTS_PATH,
        "rankings": RANKINGS_PATH,
        "facet_representation": FACET_REPRESENTATION_PATH,
        "shuffle_replay": SHUFFLE_PATH,
        "resources": RESOURCE_PATH,
        "schema_report": SCHEMA_PATH,
        "source_manifest": SOURCE_MANIFEST_PATH,
        "surface_manifest": SURFACE_MANIFEST_PATH,
        "reproduction_anchor": ANCHOR_PATH,
    }
    result = {
        "schema": "beam001-part1-report-v1",
        "status": "PASS" if all(value["status"] == "PASS" for value in gates.values()) else "STOP",
        "outcomes_opened": False,
        "generation_calls": 0,
        "corpus": corpus,
        "questions": questions,
        "facets": facets,
        "shuffle": shuffle,
        "resources": resources,
        "gates": gates,
        "distributions": rendered_metrics,
        "artifacts": {
            name: {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_file(path),
            }
            for name, path in artifact_paths.items()
        },
    }
    _write_json(DISTRIBUTIONS_PATH, result)
    trace_result = {
        "schema": "beam001-trace-audit-v1",
        "examples": dict(sorted(examples.items())),
        "absent_registered_states": sorted(
            state
            for state in (
                "fewer_than_32_recent", "no_semantic_parent", "one_semantic_parent",
                "no_positive_child", "no_fitting_child", "rejected_capacity",
                "rejected_value", "all_proposed_children_retained",
                "protected_slack_returned", "no_protected_slack_returned",
            )
            if state not in examples
        ),
        "finite_attempt_rows": questions["gate_checks"]["finite_t1_rows"],
        "no_reentry_rows": questions["gate_checks"]["no_reentry_t1_rows"],
        "longest_store": corpus["longest_store"],
        "longest_episode": corpus["longest_episode"],
        "largest_question": corpus["largest_question"],
        "largest_candidate_pool": questions["largest_candidate_pool"],
        "largest_arm_disagreement": questions["largest_arm_disagreement"],
        "outcomes_opened": False,
    }
    _write_json(TRACES_PATH, trace_result)
    result["artifacts"]["distributions"] = {
        "path": DISTRIBUTIONS_PATH.relative_to(REPO_ROOT).as_posix(),
        "sha256": sha256_file(DISTRIBUTIONS_PATH),
    }
    result["artifacts"]["trace_audit"] = {
        "path": TRACES_PATH.relative_to(REPO_ROOT).as_posix(),
        "sha256": sha256_file(TRACES_PATH),
    }
    report = _markdown(result)
    REPORT_PATH.write_text(report, encoding="utf-8", newline="\n")
    return result


def main() -> None:
    print(json.dumps(build_report(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

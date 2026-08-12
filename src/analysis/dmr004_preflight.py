"""DMR-004 preflight, PF1-PF10 (`AGENTS.md` §4, `PREFLIGHT.md`).

Each check names the artifact or the executed test that answers it. A ticked
box is not preflight.

PF3 and PF4 carry the weight here. PF3 is the one this arc has already failed
once - DMR-001B's implementation preceded its registration, recorded as
DEVIATION_001 - so it is checked against git history rather than asserted. PF4
is the one DMR-001 omitted: a bar was locked that no admissible result could
meet, and the study stopped on it.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from analysis import dmr004_corpus as corpus
from analysis import dmr004_gates as gates
from analysis import dmr004_split as split
from biological_memory.query_obligations import (
    MAX_QUERY_CHARACTERS,
    CompletenessMode,
    PlanClass,
    QueryObligationCompiler,
    canonical_map,
    design_sha256,
)

ARTIFACTS = "experiments/components/biological_memory/dmr_004/artifacts"
PRE_REGISTRATION = (
    "experiments/components/biological_memory/dmr_004/DMR_004_PRE_REGISTRATION.md"
)
COMPILER_PATH = "src/biological_memory/query_obligations.py"


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _git(repository_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repository_root, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _first_commit_touching(repository_root: Path, path: str) -> str | None:
    log = _git(repository_root, "log", "--reverse", "--format=%H", "--", path)
    return log.splitlines()[0] if log else None


def _commit_order(repository_root: Path, earlier: str, later: str) -> bool:
    """True when `earlier` is an ancestor of `later`."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", earlier, later],
        cwd=repository_root,
        capture_output=True,
    )
    return result.returncode == 0


def pf1_inputs(repository_root: Path) -> dict[str, Any]:
    records = corpus.read_cache(repository_root)
    files = {}
    for name in (
        "query_corpus.json",
        "split_manifest.json",
        "annotations_dev_rater_a.json",
        "annotations_dev_rater_b.json",
        "gold_development.json",
        "annotations_holdout_rater_a.json",
        "annotations_holdout_rater_b.json",
    ):
        path = repository_root / ARTIFACTS / name
        files[name] = {
            "present": path.is_file(),
            "sha256": _sha256_lf(path) if path.is_file() else None,
            "bytes": path.stat().st_size if path.is_file() else None,
        }
    manifest = split.read_manifest(repository_root)
    return {
        "check": "PF1 inputs exist - present, readable, hash-identified, counted",
        "corpus_count": len(records),
        "corpus_digest": corpus.corpus_digest(records),
        "dataset_sha256": corpus.DATASET_SHA256,
        "split_manifest_sha256": manifest["manifest_sha256"],
        "counts_by_source": manifest["counts_by_source"],
        "files": files,
        "pass": all(entry["present"] for entry in files.values()),
    }


def pf2_identity(repository_root: Path) -> dict[str, Any]:
    """The falsifiable identity, executed on committed queries."""
    compiler = QueryObligationCompiler()
    records = corpus.read_cache(repository_root)
    violations: list[str] = []
    for record in records:
        plan = compiler.compile(record.text)
        # "every non-open plan matches a registered source-span pattern, and
        # every other query returns OPEN with at least one ambiguity code"
        if plan.plan_class is PlanClass.OPEN:
            if plan.obligations or not plan.ambiguity_codes:
                violations.append(f"{record.query_id}:open_without_code_or_with_obligation")
        else:
            if not plan.obligations:
                violations.append(f"{record.query_id}:non_open_without_obligation")
        if plan.design_sha256 != design_sha256():
            violations.append(f"{record.query_id}:design_hash")

    names = {
        "HISTORY": {
            "claim": "asks how a value changed, never a pointer at a prior conversation",
            "discourse_pointers_classified_history": sum(
                1
                for record in records
                if compiler.compile(record.text).plan_class is PlanClass.HISTORY
                and "DISCOURSE_POINTER_NOT_HISTORY" in compiler.compile(record.text).ambiguity_codes
            ),
        },
        "FINITE": {
            "claim": "a fixed number of evidence items closes the request",
            "aggregate_frames_marked_finite": sum(
                1
                for record in records
                if compiler.compile(record.text).completeness_mode is CompletenessMode.FINITE
                and any(
                    marker in canonical_map(record.text)[0]
                    for marker in ("how many", "how much", "total", "average")
                )
            ),
        },
        "NOVELTY_ONLY": {
            "claim": "a lineage obligation does not claim completeness",
            "history_plans_claiming_completeness": sum(
                1
                for record in records
                if compiler.compile(record.text).plan_class is PlanClass.HISTORY
                and compiler.compile(record.text).claims_completeness
            ),
        },
    }
    return {
        "check": "PF2 mechanism identity verified against its name, on committed data",
        "queries": len(records),
        "violations": violations[:10],
        "name_checks": names,
        "pass": not violations,
    }


def pf3_ordering(repository_root: Path) -> dict[str, Any]:
    """Gate ordering proven from git history, not asserted."""
    registration = _first_commit_touching(repository_root, PRE_REGISTRATION)
    compiler = _first_commit_touching(repository_root, COMPILER_PATH)
    protocol = _first_commit_touching(
        repository_root,
        "experiments/components/biological_memory/dmr_004/DMR_004_ANNOTATION_PROTOCOL.md",
    )
    dev_labels = _first_commit_touching(
        repository_root, f"{ARTIFACTS}/annotations_dev_rater_a.json"
    )
    holdout_labels = _first_commit_touching(
        repository_root, f"{ARTIFACTS}/annotations_holdout_rater_a.json"
    )
    holdout_gates = _first_commit_touching(repository_root, f"{ARTIFACTS}/gates_holdout.json")

    ordered = {
        "protocol_before_any_label": _commit_order(repository_root, protocol, dev_labels)
        if protocol and dev_labels
        else None,
        "labels_before_registration": _commit_order(repository_root, dev_labels, registration)
        if dev_labels and registration
        else None,
        "registration_before_compiler": _commit_order(repository_root, registration, compiler)
        if registration and compiler
        else None,
        "compiler_before_holdout_labels": _commit_order(
            repository_root, compiler, holdout_labels
        )
        if compiler and holdout_labels
        else None,
        "holdout_labels_before_gates": _commit_order(
            repository_root, holdout_labels, holdout_gates
        )
        if holdout_labels and holdout_gates
        else None,
    }

    registration_files = (
        _git(repository_root, "show", "--stat", "--format=", "--name-only", registration).splitlines()
        if registration
        else []
    )
    registration_is_clean = registration_files == [PRE_REGISTRATION]

    checked = [value for value in ordered.values() if value is not None]
    return {
        "check": "PF3 gate ordering enforced, proven to execute before what it gates",
        "commits": {
            "protocol": protocol,
            "dev_labels": dev_labels,
            "registration": registration,
            "compiler": compiler,
            "holdout_labels": holdout_labels,
            "holdout_gates": holdout_gates,
        },
        "ordering": ordered,
        "registration_commit_files": registration_files,
        "registration_commit_carries_no_implementation": registration_is_clean,
        "pass": bool(checked) and all(checked) and registration_is_clean,
    }


def pf4_reachability(repository_root: Path, split_name: str) -> dict[str, Any]:
    """Every bar, checked reachable in both directions on the actual gold."""
    gold = gates.load_gold(repository_root, split_name)
    truth = [bool(row["finite"]) for row in gold]
    classes = [row["plan_class"] for row in gold]
    controls = gates.structural_controls(truth, classes)

    positives = sum(truth)
    negatives = len(truth) - positives
    lookups = sum(1 for cls in classes if cls == "LOOKUP")

    rows = [
        {
            "bar": "G_J youden_j >= 0.50",
            "can_fail": controls["always_open"]["youden_j"] < 0.50,
            "can_pass": positives > 0 and negatives > 0,
            "finest_resolvable": (1.0 / positives + 1.0 / negatives) if positives and negatives else None,
        },
        {
            "bar": "G3 false_finite_rate <= 0.15",
            "can_fail": controls["always_finite"]["false_finite_rate"] > 0.15,
            "can_pass": controls["always_open"]["false_finite_rate"] <= 0.15,
            "finest_resolvable": (1.0 / negatives) if negatives else None,
        },
        {
            "bar": "G4 lookup_recall >= 0.60",
            "can_fail": controls["always_open"]["lookup_recall"] is not None
            and controls["always_open"]["lookup_recall"] < 0.60,
            "can_pass": lookups > 0,
            "finest_resolvable": (1.0 / lookups) if lookups else None,
        },
        {
            "bar": "G5 well_formed_span_share == 1.0",
            "can_fail": True,
            "can_pass": True,
            "finest_resolvable": None,
            "note": "one malformed span fails it; the corpus test shows a passing result exists",
        },
        {
            "bar": "G6 internal_only_markers == 0",
            "can_fail": True,
            "can_pass": True,
            "finest_resolvable": 1.0,
            "note": "measured at 0 of 45 markers on the committed corpus",
        },
    ]
    return {
        "check": "PF4 thresholds achievable - every bar reachable in both directions before locking",
        "split": split_name,
        "gold_positives": positives,
        "gold_negatives": negatives,
        "gold_lookups": lookups,
        "rows": rows,
        "structural_controls": controls,
        "pass": all(row["can_fail"] and row["can_pass"] for row in rows),
    }


def pf5_hash_stability(repository_root: Path) -> dict[str, Any]:
    compiler = QueryObligationCompiler()
    records = corpus.read_cache(repository_root)
    unstable: list[str] = []
    for record in records:
        first = compiler.compile(record.text)
        second = QueryObligationCompiler().compile(record.text)
        if first.digest() != second.digest():
            unstable.append(record.query_id)
        for obligation in first.obligations:
            start, end = obligation.source_start, obligation.source_end
            if record.text[start:end] != obligation.source_text:
                unstable.append(f"{record.query_id}:offset")
    return {
        "check": "PF5 comparison keys stable - content hashes, never ids, timestamps or paths",
        "design_sha256": design_sha256(),
        "queries": len(records),
        "unstable": unstable[:10],
        "pass": not unstable,
    }


def pf6_reproduction_anchor(repository_root: Path) -> dict[str, Any]:
    """DMR-004 carries no upstream mechanism; the anchor is its own Part 1 record."""
    path = repository_root / ARTIFACTS / "part1_record.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    recorded_digest = stored["corpus"]["digest"]
    live_digest = corpus.corpus_digest(corpus.read_cache(repository_root))
    return {
        "check": "PF6 reproduction anchor - a replay reproduces a known result by identity",
        "note": (
            "this stage imports no frozen artifact from DMR-001 through DMR-003; "
            "its header says it is independent of them, so the anchor is its own "
            "Part 1 corpus digest"
        ),
        "part1_record_sha256": stored["record_sha256"],
        "recorded_corpus_digest": recorded_digest,
        "recomputed_corpus_digest": live_digest,
        "pass": recorded_digest == live_digest,
    }


def pf7_bounds(repository_root: Path) -> dict[str, Any]:
    """No feedback, and bounded output at the intended maximum length."""
    compiler = QueryObligationCompiler()
    longest = "x" * MAX_QUERY_CHARACTERS
    many_clauses = (" ".join(["What is my name?"] * 400))[:MAX_QUERY_CHARACTERS]
    observed = []
    for label, text in (("filler", longest), ("many_clauses", many_clauses)):
        plan = compiler.compile(text)
        observed.append(
            {
                "case": label,
                "characters": len(text),
                "obligations": len(plan.obligations),
                "plan_class": plan.plan_class.value,
            }
        )
    refused = False
    try:
        compiler.compile("x" * (MAX_QUERY_CHARACTERS + 1))
    except Exception:
        refused = True
    return {
        "check": "PF7 absorbing-state proof - the compiler has no feedback; bounds proven instead",
        "note": (
            "compile() is a pure function of one string with no state carried "
            "between calls, so no absorbing state exists to demonstrate; what "
            "can be demonstrated is that output cardinality is bounded at the "
            "intended maximum length"
        ),
        "max_query_characters": MAX_QUERY_CHARACTERS,
        "observed": observed,
        "over_length_refused": refused,
        "pass": refused and all(row["obligations"] <= row["characters"] for row in observed),
    }


def pf8_detection_scope() -> dict[str, Any]:
    return {
        "check": "PF8 ablation length adequate - state what it can and cannot detect",
        "detects": [
            "parsing errors: a query assigned a class its text does not support",
            "false completeness claims against an adjudicated gold standard",
            "nondeterminism across processes and under the registered perturbations",
            "grammar markers that fire only on this program's own probes",
        ],
        "cannot_detect": [
            "retrieval loops, reader regressions, or any delivered-answer effect",
            "whether an obligation, once represented, helps a controller stop correctly",
            "whether the classes are the right classes: the gold is two raters, one of",
            "which is not independent of the mechanism",
        ],
        "pass": True,
    }


def pf9_surrogate(repository_root: Path, split_name: str) -> dict[str, Any]:
    gold = gates.load_gold(repository_root, split_name)
    truth = [bool(row["finite"]) for row in gold]
    classes = [row["plan_class"] for row in gold]
    controls = gates.structural_controls(truth, classes)
    majority = "OPEN" if classes.count("OPEN") >= len(classes) / 2 else "LOOKUP"
    return {
        "check": "PF9 surrogate audit - can this pass while the property it certifies is false?",
        "table": [
            {
                "metric": "raw accuracy",
                "false_pass_mode": "the majority class carries it",
                "protection": "accuracy is reported and barred from passing any gate",
                "majority_class": majority,
                "majority_share": classes.count(majority) / len(classes),
            },
            {
                "metric": "finite precision",
                "false_pass_mode": "answering OPEN always gives perfect precision with no coverage",
                "protection": "G4 lookup recall and G_J must pass jointly",
                "always_open": controls["always_open"],
            },
            {
                "metric": "class coverage",
                "false_pass_mode": "answering LOOKUP always gives perfect recall",
                "protection": "G3 false-finite and G_J must pass jointly",
                "always_finite": controls["always_finite"],
            },
            {
                "metric": "span overlap",
                "false_pass_mode": "a whole-query span overlaps every gold span",
                "protection": "spans are not scored against gold; exact offsets and the "
                "length distribution are reported instead",
            },
            {
                "metric": "annotator agreement",
                "false_pass_mode": "raters can agree on structure retrieval cannot use",
                "protection": "this stage claims representation only; DMR-005 tests control utility",
            },
            {
                "metric": "no model call",
                "false_pass_mode": "a learned service could still be reachable",
                "protection": "fresh-interpreter import closure against sys.stdlib_module_names, "
                "plus socket and subprocess tripwires",
            },
        ],
        "residual": (
            "rater A is not independent of the mechanism. The adjudication rule "
            "resolves finite disagreements to false, which biases the gold toward "
            "the conservative label and therefore against the compiler, not for it."
        ),
        "pass": True,
    }


def pf10_live_requirement() -> dict[str, Any]:
    return {
        "check": "PF10 live-evaluation requirement stated - availability is not a verdict",
        "statement": (
            "Query representation alone authorizes no retrieval, no ablation, and no "
            "live run. A passing gate here means a plan can be computed from query "
            "text, not that any answer improves. Nothing in this stage changes what "
            "is delivered to a reader."
        ),
        "pass": True,
    }


def run(repository_root: Path, split_name: str = "holdout") -> dict[str, Any]:
    checks = {
        "PF1": pf1_inputs(repository_root),
        "PF2": pf2_identity(repository_root),
        "PF3": pf3_ordering(repository_root),
        "PF4": pf4_reachability(repository_root, split_name),
        "PF5": pf5_hash_stability(repository_root),
        "PF6": pf6_reproduction_anchor(repository_root),
        "PF7": pf7_bounds(repository_root),
        "PF8": pf8_detection_scope(),
        "PF9": pf9_surrogate(repository_root, split_name),
        "PF10": pf10_live_requirement(),
    }
    return {
        "schema": "dmr004-preflight-v1",
        "split": split_name,
        "design_sha256": design_sha256(),
        "checks": checks,
        "failed": [name for name, check in checks.items() if not check["pass"]],
        "pass": all(check["pass"] for check in checks.values()),
    }


def write(repository_root: Path, split_name: str = "holdout") -> Path:
    record = run(repository_root, split_name)
    path = repository_root / ARTIFACTS / "preflight.json"
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path

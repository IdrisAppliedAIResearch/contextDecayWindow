"""Ordered execution gates and sealed result stages for TC-004."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.metadata
import inspect
import json
import math
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np

from analysis.locomo_nf_development import (
    DATASET_BYTES,
    DATASET_SHA256,
    DEVELOPMENT_IDS,
    ConversationCase,
    QuestionCase,
    adapt_development,
    sha256_file,
)
from analysis.tc001_exploration import (
    CACHE_PATH,
    DATASET_PATH,
    REPO_ROOT,
    VECTOR_MANIFEST,
    Episode,
    build_episodes,
)
from analysis.tc001_study import one_sided_sign_p
from analysis.tc004_exploration import (
    _locomo_turn_texts,
    canonical_bytes,
    canonical_digest,
)
from analysis.tc004_mechanism import (
    SPLIT_RATES,
    cosine_maps,
    offered_units,
    policy_order,
    predictor_scores,
    select,
    split_count,
)
from analysis.tc004_preflight import (
    SENTINEL_TEXT,
    SENTINEL_VECTOR_SHA256,
    TC004_CHILD_CACHE,
    TC004_CHILD_MANIFEST,
    ParentUnit,
    build_parent_units,
    mixed_context,
    parent_scores as preflight_parent_scores,
)
from analysis.tc_standing_arms import STANDING_ARMS, deliver
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256
from episodic._packing import pack_stm_payload
from retrieval_bakeoff.embedding import CarriedEmbedder

SCHEMA = "tc004-candidate-granularity-v1"
STUDY_ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
REGISTRATION = STUDY_ROOT / "TC_004_PRE_REGISTRATION.md"
REGISTRATION_COMMIT = "ea6847948984f5aba76ff1f60bae29a9daeca25e"
REGISTRATION_LF_SHA256 = (
    "c0478b6795661c5521a169334c466f07fbd0da4b28b171fc13ec93bd3ef339d9"
)
PREFLIGHT_ROOT = STUDY_ROOT / "artifacts" / "tc004" / "preflight"
PART1 = PREFLIGHT_ROOT / "tc004_preflight_part1.json"
INVENTORY = PREFLIGHT_ROOT / "tc004_locomo_split_inventory.json"
PF4 = PREFLIGHT_ROOT / "tc004_preflight_pf4_reachability.json"
PART1_SHA256 = "5833cdb331412961bd9a73c767363fc83c12b6a0cf1eb6ca22e42be8cc66df6a"
INVENTORY_SHA256 = "3b771ac61a548e4e93f3e5cdbc0b479f83e007bcae031fcab4b2380e0632a74b"
PF4_SHA256 = "512e75d4dd6c7c1067f6e9ae43c3e00fd0a2e9855ac8c6f176e856d4cdb21623"
TC003_PRIMARY = STUDY_ROOT / "runs" / "tc003" / "run" / "per_question_primary.csv"
TC003_SECONDARY = STUDY_ROOT / "runs" / "tc003" / "run" / "per_question_secondary.csv"
G0_ROOT = STUDY_ROOT / "runs" / "tc004" / "g0"
RUN_ROOT = STUDY_ROOT / "runs" / "tc004" / "run"
G0_ARTIFACT = G0_ROOT / "precondition.json"
OUTCOME_ARTIFACT = RUN_ROOT / "outcomes.json"
INTEGRITY_ARTIFACT = RUN_ROOT / "integrity.json"

PRIMARY_BUDGET = 16_000
SECONDARY_BUDGET = 32_000
POLICIES = ("embedding_localization_gain", "length", "lexical_localization_gain")
EXPECTED_PARENT_CACHE_FILE = "2ba617018a1b043bf439bb50e756191d8141fb7ca01a2e4a68c9eb822eba26f8"
EXPECTED_PARENT_CACHE_CONTENT = "e103b2933ee9ec7b8e9236f43037797618da524e413b83a9f3973a19d28b1b2a"


class TC004GateStop(RuntimeError):
    def __init__(self, gate: str, detail: str) -> None:
        super().__init__(f"{gate} stopped: {detail}")
        self.gate = gate


def _git(*args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=REPO_ROOT, text=True).strip()


def _lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _first_commit(path: Path) -> str:
    relative = path.resolve().relative_to(REPO_ROOT).as_posix()
    commits = _git("log", "--diff-filter=A", "--format=%H", "--", relative).splitlines()
    if len(commits) != 1:
        raise TC004GateStop("INTEGRITY", f"Expected one add commit for {relative}")
    return commits[0]


def _committed_identity(path: Path) -> dict[str, Any]:
    relative = path.resolve().relative_to(REPO_ROOT).as_posix()
    first = _first_commit(path)
    committed = subprocess.check_output(("git", "show", f"{first}:{relative}"), cwd=REPO_ROOT)
    if committed != path.read_bytes():
        raise TC004GateStop("INTEGRITY", f"{relative} differs from its add commit")
    return {"path": relative, "first_commit": first, "sha256": hashlib.sha256(committed).hexdigest()}


def _write(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(payload))
    return path


def registration_gate() -> dict[str, Any]:
    observed_commit = _first_commit(REGISTRATION)
    observed_sha = _lf_sha256(REGISTRATION)
    passed = observed_commit == REGISTRATION_COMMIT and observed_sha == REGISTRATION_LF_SHA256
    return {
        "pass": passed,
        "expected_first_commit": REGISTRATION_COMMIT,
        "observed_first_commit": observed_commit,
        "expected_lf_sha256": REGISTRATION_LF_SHA256,
        "observed_lf_sha256": observed_sha,
        "child_cache_opened": False,
    }


def _questions(cases: Sequence[ConversationCase]) -> list[QuestionCase]:
    return [q for case in cases for q in case.questions]


def input_gate() -> dict[str, Any]:
    cases = adapt_development(DATASET_PATH)
    questions = _questions(cases)
    pairs = [pair for case in cases for pair in case.pairs]
    turn_texts = _locomo_turn_texts(DATASET_PATH)
    child_texts = {text for text in turn_texts.values()}
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    hashes = {
        "part1": sha256_file(PART1),
        "inventory": sha256_file(INVENTORY),
        "pf4": sha256_file(PF4),
    }
    counts = {
        "conversations": len(cases),
        "question_records": len(questions),
        "unique_resolved_questions": sum(q.duplicate_ordinal == 0 and bool(q.resolved_evidence_ids) for q in questions),
        "complete_evaluable_questions": sum(q.duplicate_ordinal == 0 and bool(q.resolved_evidence_ids) and not q.unresolved_evidence_ids for q in questions),
        "parents": len(pairs),
        "splittable_parents": sum(len(pair.dialog_ids) == 2 for pair in pairs),
        "singleton_parents": sum(len(pair.dialog_ids) == 1 for pair in pairs),
        "unique_child_texts": len(child_texts),
        "absent_child_vectors": inventory["treatment_vector_coverage"]["absent_from_retained_cache"],
    }
    passed = all(
        (
            DATASET_PATH.stat().st_size == DATASET_BYTES,
            sha256_file(DATASET_PATH) == DATASET_SHA256,
            hashes == {"part1": PART1_SHA256, "inventory": INVENTORY_SHA256, "pf4": PF4_SHA256},
            manifest["cache"]["file_sha256"] == EXPECTED_PARENT_CACHE_FILE,
            manifest["cache"]["content_sha256"] == EXPECTED_PARENT_CACHE_CONTENT,
            counts == {
                "conversations": 4,
                "question_records": 882,
                "unique_resolved_questions": 871,
                "complete_evaluable_questions": 868,
                "parents": 1365,
                "splittable_parents": 1297,
                "singleton_parents": 68,
                "unique_child_texts": 2660,
                "absent_child_vectors": 2592,
            },
        )
    )
    return {
        "pass": passed,
        "dataset": {"sha256": sha256_file(DATASET_PATH), "bytes": DATASET_PATH.stat().st_size},
        "development_ids": sorted(DEVELOPMENT_IDS),
        "preflight_sha256": hashes,
        "parent_cache": manifest["cache"],
        "counts": counts,
    }


def _import_names(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def mechanism_violations(source: str) -> list[str]:
    tree = ast.parse(source)
    forbidden = {"answer", "answers", "category", "evidence", "evidence_ids", "resolved_evidence_ids", "unresolved_evidence_ids", "beneficial", "harmful", "outcome", "outcomes"}
    used = {node.id.casefold() for node in ast.walk(tree) if isinstance(node, ast.Name)}
    used.update(node.attr.casefold() for node in ast.walk(tree) if isinstance(node, ast.Attribute))
    violations = [f"forbidden identifier:{name}" for name in sorted(forbidden & used)]
    lowered = source.casefold()
    for token in ("q_facts_key", "tc004_study", "per_question_primary", "outcomes.json"):
        if token in lowered:
            violations.append(f"forbidden source reference:{token}")
    return violations


def leakage_gate() -> dict[str, Any]:
    from analysis import tc004_mechanism

    source = inspect.getsource(tc004_mechanism)
    violations = mechanism_violations(source)
    planted_import = source + "\nfrom analysis.tc004_study import outcome\n"
    planted_field = source + "\nvalue = question.resolved_evidence_ids\n"
    return {
        "pass": not violations and bool(mechanism_violations(planted_import)) and bool(mechanism_violations(planted_field)),
        "path": Path(inspect.getfile(tc004_mechanism)).resolve().relative_to(REPO_ROOT).as_posix(),
        "imports": sorted(_import_names(source)),
        "violations": violations,
        "planted_import_rejected": bool(mechanism_violations(planted_import)),
        "planted_field_rejected": bool(mechanism_violations(planted_field)),
    }


def _parent_vectors(cases: Sequence[ConversationCase]) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    texts = {pair.text for case in cases for pair in case.pairs}
    texts.update(q.question for case in cases for q in case.questions)
    with EmbeddingCache(
        CACHE_PATH,
        mode="reuse",
        expected_file_sha256=EXPECTED_PARENT_CACHE_FILE,
        expected_content_sha256=EXPECTED_PARENT_CACHE_CONTENT,
        expected_model_sha256=CARRIED_EMBEDDER_SHA256,
    ) as cache:
        vectors = {text: np.asarray(cache(text), dtype=np.float32) for text in texts}
        record = cache.record()
    if record["misses"]:
        raise TC004GateStop("G3", "Parent/query cache missed")
    return vectors, record


def _dialog_map(episodes: Sequence[Episode]) -> dict[str, tuple[str, ...]]:
    return {episode.identity: episode.pair.dialog_ids for episode in episodes}


def _evidence(delivered: Iterable[str], dialog_by_episode: Mapping[str, Sequence[str]]) -> frozenset[str]:
    return frozenset(dialog for identity in delivered for dialog in dialog_by_episode[identity])


def reproduction_gate() -> dict[str, Any]:
    cases = adapt_development(DATASET_PATH)
    vectors, reuse = _parent_vectors(cases)
    committed_by_budget: dict[int, dict[str, dict[str, str]]] = {}
    for budget, path in ((PRIMARY_BUDGET, TC003_PRIMARY), (SECONDARY_BUDGET, TC003_SECONDARY)):
        with path.open(encoding="utf-8", newline="") as handle:
            committed_by_budget[budget] = {row["question_id"]: row for row in csv.DictReader(handle)}
    comparisons = 0
    zero_identity = 0
    mismatches: list[str] = []
    counts: dict[str, dict[str, dict[str, int]]] = {}
    turn_texts = _locomo_turn_texts(DATASET_PATH)
    for case in cases:
        episodes = build_episodes(case, vectors)
        parents = build_parent_units(case, vectors, turn_texts)
        dialog_map = _dialog_map(episodes)
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            query = vectors[question.question]
            scores = preflight_parent_scores(parents, query)
            evidence = frozenset(question.resolved_evidence_ids)
            for budget in (PRIMARY_BUDGET, SECONDARY_BUDGET):
                committed = committed_by_budget[budget][question.identity]
                for arm in STANDING_ARMS:
                    payload, selected = deliver(arm, episodes, query, budget)
                    delivered_dialog = _evidence(selected, dialog_map)
                    raw_complete = bool(evidence) and evidence <= delivered_dialog
                    current = {
                        # The carried row stores resolved-ID completeness even
                        # when the row is excluded from the complete endpoint.
                        "complete": raw_complete,
                        "any": bool(evidence & delivered_dialog),
                        "delivered": len(selected),
                        "chars": len(payload),
                    }
                    for field, value in current.items():
                        expected = committed[f"{arm}_{field}"]
                        parsed: Any = expected == "True" if field in {"complete", "any"} else int(expected)
                        comparisons += 1
                        if value != parsed:
                            mismatches.append(f"{budget}:{question.identity}:{arm}:{field}")
                    key = str(budget)
                    counts.setdefault(key, {}).setdefault(arm, {"complete": 0, "any": 0})
                    counts[key][arm]["complete"] += int(
                        raw_complete and not question.unresolved_evidence_ids
                    )
                    counts[key][arm]["any"] += int(current["any"])
                zero = mixed_context(parents, scores, {}, (), budget)
                flat_payload, flat_ids = deliver("flat", episodes, query, budget)
                zero_identity += int(zero.payload == flat_payload and zero.selected_ids == flat_ids)
    return {
        "pass": not mismatches and comparisons == 20_904 and zero_identity == 1_742,
        "standing_cells_compared": comparisons,
        "zero_split_a_flat_identity_checks": zero_identity,
        "committed_csv_sha256": {"16000": sha256_file(TC003_PRIMARY), "32000": sha256_file(TC003_SECONDARY)},
        "counts": counts,
        "mismatches": mismatches[:20],
        "parent_cache": reuse,
        "child_cache_opened": False,
    }


def implementation_gate() -> dict[str, Any]:
    command = [sys.executable, "-m", "pytest", "-q", "tests/test_tc004_granularity.py", "tests/test_tc004_preflight.py", "tests/test_tc004_study.py"]
    completed = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    return {
        "pass": completed.returncode == 0,
        "command": command,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "returncode": completed.returncode,
    }


def pre_capture_gates() -> dict[str, Any]:
    gates: dict[str, Any] = {}
    for name, function in (("G0", registration_gate), ("G1", input_gate), ("G2", leakage_gate), ("G3", reproduction_gate), ("G4", implementation_gate)):
        evidence = function()
        if evidence.get("pass") is not True:
            raise TC004GateStop(name, str(evidence))
        gates[name] = evidence
    return gates


class _SoloDelegate:
    def __init__(self, delegate: CarriedEmbedder) -> None:
        self.delegate = delegate
        self.model_sha256 = delegate.model_sha256
        self.calls = 0

    def __call__(self, text: str) -> np.ndarray:
        self.calls += 1
        return self.delegate(text)


def _child_texts() -> tuple[str, ...]:
    values = set(_locomo_turn_texts(DATASET_PATH).values())
    return tuple(sorted(values, key=lambda text: hashlib.sha256(text.encode("utf-8")).hexdigest()))


def capture(model_path: Path) -> Path:
    pre_capture_gates()
    cache_path = REPO_ROOT / TC004_CHILD_CACHE
    manifest_path = REPO_ROOT / TC004_CHILD_MANIFEST
    if cache_path.exists() or manifest_path.exists():
        raise TC004GateStop("G5", "Child cache or manifest already exists")
    delegate = CarriedEmbedder(model_path)
    delegate.assert_carried_model()
    solo = _SoloDelegate(delegate)
    sentinel = np.asarray(solo(SENTINEL_TEXT), dtype=np.float32)
    sentinel_sha = hashlib.sha256(sentinel.tobytes()).hexdigest()
    if sentinel_sha != SENTINEL_VECTOR_SHA256:
        raise TC004GateStop("G5", f"Sentinel differs: {sentinel_sha}")
    texts = _child_texts()
    with EmbeddingCache(cache_path, mode="populate", embedder=solo) as cache:
        for index, text in enumerate(texts, 1):
            cache(text)
            if index % 256 == 0 or index == len(texts):
                print(f"TC-004 child vector capture {index}/{len(texts)}", flush=True)
        cache_record = cache.record()
    if len(texts) != 2660 or solo.calls != 2661 or cache_record["entries"] != 2660:
        raise TC004GateStop("G5", "Vector capture cardinality differs")
    payload = {
        "schema": "tc004-child-vectors-v1",
        "dataset_sha256": DATASET_SHA256,
        "development_ids": sorted(DEVELOPMENT_IDS),
        "expected_unique_texts": len(texts),
        "text_order_digest": canonical_digest([hashlib.sha256(text.encode("utf-8")).hexdigest() for text in texts]),
        "sentinel_text": SENTINEL_TEXT,
        "sentinel_vector_sha256": sentinel_sha,
        "cache": cache_record,
        "llama_cpp_python": importlib.metadata.version("llama-cpp-python"),
        "model_sha256": CARRIED_EMBEDDER_SHA256,
        "embedding_calls": solo.calls,
        "model_generation_calls": 0,
        "call_shape": "solo",
    }
    return _write(manifest_path, payload)


def vector_seal_gate() -> dict[str, Any]:
    manifest_path = REPO_ROOT / TC004_CHILD_MANIFEST
    cache_path = REPO_ROOT / TC004_CHILD_CACHE
    manifest_identity = _committed_identity(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    texts = _child_texts()
    with EmbeddingCache(
        cache_path,
        mode="reuse",
        expected_file_sha256=manifest["cache"]["file_sha256"],
        expected_content_sha256=manifest["cache"]["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDER_SHA256,
    ) as cache:
        for text in texts:
            cache(text)
        record = cache.record()
    passed = all((manifest["expected_unique_texts"] == 2660, manifest["embedding_calls"] == 2661, manifest["model_generation_calls"] == 0, manifest["sentinel_vector_sha256"] == SENTINEL_VECTOR_SHA256, record["hits"] == 2660, record["misses"] == 0))
    return {"pass": passed, "manifest": manifest_identity, "cache": manifest["cache"], "coverage": record}


def _load_child_vectors() -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    manifest = json.loads((REPO_ROOT / TC004_CHILD_MANIFEST).read_text(encoding="utf-8"))
    with EmbeddingCache(
        REPO_ROOT / TC004_CHILD_CACHE,
        mode="reuse",
        expected_file_sha256=manifest["cache"]["file_sha256"],
        expected_content_sha256=manifest["cache"]["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDER_SHA256,
    ) as cache:
        vectors = {text: np.asarray(cache(text), dtype=np.float32) for text in _child_texts()}
        record = cache.record()
    if record["misses"]:
        raise TC004GateStop("G6", "Child cache missed")
    return vectors, record


def _selection_cell(hasher: Any, question_id: str, name: str, budget: int, selection: Any) -> None:
    hasher.update(canonical_bytes({"question_id": question_id, "cell": name, "budget": budget, "ordered_identity_sha256": canonical_digest(selection.selected_ids), "payload_sha256": selection.payload_sha256, "serialized_chars": selection.serialized_chars}))


def selection_replay() -> dict[str, Any]:
    """Complete G6 replay without reading any question evidence field."""
    cases = adapt_development(DATASET_PATH)
    parent_vectors, parent_reuse = _parent_vectors(cases)
    child_vectors, child_reuse = _load_child_vectors()
    turn_texts = _locomo_turn_texts(DATASET_PATH)
    digest = hashlib.sha256()
    cells = questions = 0
    for case in cases:
        parents = build_parent_units(case, parent_vectors, turn_texts)
        splittable = tuple(parent.index for parent in parents if parent.splittable)
        episodes = tuple(parent.episode for parent in parents)
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            questions += 1
            query = parent_vectors[question.question]
            parent_map, child_map = cosine_maps(parents, query, child_vectors)
            policies = predictor_scores(parents, parent_map, child_map, question.question)
            orders = {name: policy_order(parents, policy) for name, policy in policies.items()}
            for budget in (PRIMARY_BUDGET, SECONDARY_BUDGET):
                zero = select(parents, parent_map, child_map, (), budget)
                _selection_cell(digest, question.identity, "zero", budget, zero)
                cells += 1
                for parent_index in splittable:
                    solo = select(parents, parent_map, child_map, (parent_index,), budget)
                    _selection_cell(digest, question.identity, f"solo:{parent_index}", budget, solo)
                    cells += 1
                for name, order in orders.items():
                    for rate in SPLIT_RATES:
                        count = split_count(rate, len(order))
                        chosen = select(parents, parent_map, child_map, order[:count], budget)
                        _selection_cell(digest, question.identity, f"policy:{name}:{rate:.2f}", budget, chosen)
                        cells += 1
                for arm in STANDING_ARMS:
                    payload, ids = deliver(arm, episodes, query, budget)
                    digest.update(canonical_bytes({"question_id": question.identity, "cell": f"standing:{arm}", "budget": budget, "ordered_identity_sha256": canonical_digest(ids), "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(), "serialized_chars": len(payload)}))
                    cells += 1
    return {
        "questions": questions,
        "selection_cells": cells,
        "selection_sha256": digest.hexdigest(),
        "parent_cache": parent_reuse,
        "child_cache": child_reuse,
        "evidence_fields_joined": False,
        "embedding_calls": 0,
        "model_generation_calls": 0,
    }


def determinism_gate() -> dict[str, Any]:
    first = selection_replay()
    second = selection_replay()
    return {
        "pass": first == second and first["questions"] == 871,
        "first": first,
        "second": second,
    }


def g0() -> Path:
    gates = pre_capture_gates()
    gates["G5"] = vector_seal_gate()
    if gates["G5"].get("pass") is not True:
        raise TC004GateStop("G5", str(gates["G5"]))
    gates["G6"] = determinism_gate()
    if gates["G6"].get("pass") is not True:
        raise TC004GateStop("G6", str(gates["G6"]))
    return _write(G0_ARTIFACT, {"schema": SCHEMA, "status": "PASS", "registration_commit": REGISTRATION_COMMIT, "gates": gates})


def average_precision(order: Sequence[int], positives: frozenset[int]) -> float | None:
    if not positives:
        return None
    hits = 0
    precisions: list[float] = []
    for rank, value in enumerate(order, 1):
        if value in positives:
            hits += 1
            precisions.append(hits / rank)
    if hits != len(positives):
        raise TC004GateStop("G7", "Predictor order omitted a positive")
    return statistics.fmean(precisions)


def _rate_key(rate: float) -> str:
    return f"{rate:.2f}"


def _question_outcomes() -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    cases = adapt_development(DATASET_PATH)
    parent_vectors, parent_reuse = _parent_vectors(cases)
    child_vectors, child_reuse = _load_child_vectors()
    turn_texts = _locomo_turn_texts(DATASET_PATH)
    digest = hashlib.sha256()
    rows: list[dict[str, Any]] = []
    cells = 0
    for case in cases:
        parents = build_parent_units(case, parent_vectors, turn_texts)
        splittable = tuple(parent.index for parent in parents if parent.splittable)
        episodes = tuple(parent.episode for parent in parents)
        dialog_map = _dialog_map(episodes)
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            query = parent_vectors[question.question]
            parent_map, child_map = cosine_maps(parents, query, child_vectors)
            policies = predictor_scores(parents, parent_map, child_map, question.question)
            orders = {name: policy_order(parents, policy) for name, policy in policies.items()}
            evidence = frozenset(question.resolved_evidence_ids)
            complete_evaluable = bool(evidence) and not question.unresolved_evidence_ids
            row: dict[str, Any] = {
                "question_id": question.identity,
                "sample_id": question.sample_id,
                "source_index": question.source_index,
                "complete_evaluable": complete_evaluable,
                "resolved_evidence_count": len(evidence),
                "unresolved_evidence_count": len(question.unresolved_evidence_ids),
                "budgets": {},
            }
            for budget in (PRIMARY_BUDGET, SECONDARY_BUDGET):
                zero = select(parents, parent_map, child_map, (), budget)
                _selection_cell(digest, question.identity, "zero", budget, zero)
                cells += 1
                zero_complete = complete_evaluable and evidence <= zero.delivered_dialog_ids
                zero_any = bool(evidence & zero.delivered_dialog_ids)
                beneficial: set[int] = set()
                harmful: set[int] = set()
                for parent_index in splittable:
                    solo = select(parents, parent_map, child_map, (parent_index,), budget)
                    _selection_cell(digest, question.identity, f"solo:{parent_index}", budget, solo)
                    cells += 1
                    solo_complete = complete_evaluable and evidence <= solo.delivered_dialog_ids
                    if not zero_complete and solo_complete:
                        beneficial.add(parent_index)
                    elif zero_complete and not solo_complete:
                        harmful.add(parent_index)
                policy_rows: dict[str, Any] = {}
                for name, order in orders.items():
                    cells_by_rate: dict[str, Any] = {}
                    for rate in SPLIT_RATES:
                        count = split_count(rate, len(order))
                        selected = select(parents, parent_map, child_map, order[:count], budget)
                        _selection_cell(digest, question.identity, f"policy:{name}:{rate:.2f}", budget, selected)
                        cells += 1
                        cells_by_rate[_rate_key(rate)] = {
                            "split_parents": count,
                            "complete": complete_evaluable and evidence <= selected.delivered_dialog_ids,
                            "any": bool(evidence & selected.delivered_dialog_ids),
                            "chars": selected.serialized_chars,
                            "delivered_units": len(selected.selected_ids),
                            "selected_digest": canonical_digest(selected.selected_ids),
                            "payload_sha256": selected.payload_sha256,
                        }
                    policy_rows[name] = {
                        "average_precision": average_precision(order, frozenset(beneficial)) if budget == PRIMARY_BUDGET and complete_evaluable else None,
                        "rates": cells_by_rate,
                    }
                standing: dict[str, Any] = {}
                for arm in STANDING_ARMS:
                    payload, ids = deliver(arm, episodes, query, budget)
                    delivered_dialog = _evidence(ids, dialog_map)
                    digest.update(canonical_bytes({"question_id": question.identity, "cell": f"standing:{arm}", "budget": budget, "ordered_identity_sha256": canonical_digest(ids), "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(), "serialized_chars": len(payload)}))
                    cells += 1
                    standing[arm] = {"complete": complete_evaluable and evidence <= delivered_dialog, "any": bool(evidence & delivered_dialog), "chars": len(payload), "delivered_units": len(ids)}
                row["budgets"][str(budget)] = {
                    "zero": {"complete": zero_complete, "any": zero_any, "chars": zero.serialized_chars, "delivered_units": len(zero.selected_ids), "selected_digest": canonical_digest(zero.selected_ids), "payload_sha256": zero.payload_sha256},
                    "beneficial_parent_indices": sorted(beneficial) if budget == PRIMARY_BUDGET else None,
                    "harmful_parent_indices": sorted(harmful) if budget == PRIMARY_BUDGET else None,
                    "policies": policy_rows,
                    "standing": standing,
                }
            rows.append(row)
    return rows, digest.hexdigest(), {"selection_cells": cells, "parent_cache": parent_reuse, "child_cache": child_reuse}


def _g0_ancestor() -> dict[str, Any]:
    identity = _committed_identity(G0_ARTIFACT)
    if subprocess.run(("git", "merge-base", "--is-ancestor", identity["first_commit"], "HEAD"), cwd=REPO_ROOT).returncode:
        raise TC004GateStop("G7", "G0 commit is not an ancestor of HEAD")
    return identity


def _ap_comparison(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    positive = [row for row in rows if row["complete_evaluable"] and row["budgets"][str(PRIMARY_BUDGET)]["beneficial_parent_indices"]]
    embedding_values: list[float] = []
    length_values: list[float] = []
    gains = losses = ties = 0
    for row in positive:
        policies = row["budgets"][str(PRIMARY_BUDGET)]["policies"]
        embedding = float(policies["embedding_localization_gain"]["average_precision"])
        length = float(policies["length"]["average_precision"])
        embedding_values.append(embedding)
        length_values.append(length)
        gains += int(embedding > length)
        losses += int(embedding < length)
        ties += int(embedding == length)
    discordant = gains + losses
    return {
        "ap_evaluable_questions": len(positive),
        "gains": gains,
        "losses": losses,
        "ties": ties,
        "mean_embedding_ap": statistics.fmean(embedding_values) if embedding_values else None,
        "mean_length_ap": statistics.fmean(length_values) if length_values else None,
        "mean_ap_difference": statistics.fmean(e - l for e, l in zip(embedding_values, length_values)) if embedding_values else None,
        "one_sided_exact_p": one_sided_sign_p(gains, discordant),
    }


def disposition(primary: Mapping[str, Any], controls: Mapping[str, Any]) -> str:
    if primary["ap_evaluable_questions"] < 6 or not controls["positive_exists"] or not controls["adverse_exists"]:
        return "INSTRUMENT_INADEQUATE"
    if primary["gains"] >= 2 * primary["losses"] and primary["one_sided_exact_p"] <= 0.05 and primary["mean_embedding_ap"] > primary["mean_length_ap"]:
        return "OPERATIONAL_TEST_WORKS"
    if primary["gains"] > primary["losses"] and primary["one_sided_exact_p"] <= 0.20 and primary["mean_embedding_ap"] > primary["mean_length_ap"]:
        return "CARRIES_SIGNAL"
    return "NO_PREDICTIVE_SIGNAL"


def outcome() -> Path:
    g0_identity = _g0_ancestor()
    sealed = json.loads(G0_ARTIFACT.read_text(encoding="utf-8"))
    expected_selection_sha = sealed["gates"]["G6"]["first"]["selection_sha256"]
    rows, selection_sha, reuse = _question_outcomes()
    if selection_sha != expected_selection_sha:
        raise TC004GateStop("G7", "Outcome selection replay differs from G6")
    primary = _ap_comparison(rows)
    controls = {
        "positive_exists": any(row["budgets"][str(PRIMARY_BUDGET)]["beneficial_parent_indices"] for row in rows),
        "adverse_exists": any(row["budgets"][str(PRIMARY_BUDGET)]["harmful_parent_indices"] for row in rows),
    }
    payload = {
        "schema": SCHEMA,
        "stage": "G7",
        "registration_commit": REGISTRATION_COMMIT,
        "g0": g0_identity,
        "selection_sha256": selection_sha,
        "cache_reuse": reuse,
        "questions": len(rows),
        "complete_evaluable_questions": sum(row["complete_evaluable"] for row in rows),
        "primary": primary,
        "controls": controls,
        "disposition_inputs": {"ap_n_at_least_6": primary["ap_evaluable_questions"] >= 6, "gains_at_least_twice_losses": primary["gains"] >= 2 * primary["losses"], "gains_exceed_losses": primary["gains"] > primary["losses"], "p_le_0_05": primary["one_sided_exact_p"] <= 0.05, "p_le_0_20": primary["one_sided_exact_p"] <= 0.20, "mean_embedding_ap_exceeds_length": primary["mean_embedding_ap"] is not None and primary["mean_embedding_ap"] > primary["mean_length_ap"]},
        "disposition": disposition(primary, controls),
        "embedding_calls_during_measurement": 0,
        "model_generation_calls": 0,
        "rows": rows,
    }
    return _write(OUTCOME_ARTIFACT, payload)


def _distribution(values: Iterable[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {"n": 0}
    def rank(q: float) -> float:
        return ordered[max(0, math.ceil(q * len(ordered)) - 1)]
    return {"n": len(ordered), "min": ordered[0], "p05": rank(.05), "p50": rank(.5), "p95": rank(.95), "max": ordered[-1], "mean": statistics.fmean(ordered)}


def integrity() -> Path:
    outcome_identity = _committed_identity(OUTCOME_ARTIFACT)
    sealed = json.loads(OUTCOME_ARTIFACT.read_text(encoding="utf-8"))
    rows, selection_sha, _reuse = _question_outcomes()
    replay = dict(sealed)
    replay["rows"] = rows
    replay["selection_sha256"] = selection_sha
    replay["primary"] = _ap_comparison(rows)
    if canonical_bytes(replay) != canonical_bytes(sealed):
        raise TC004GateStop("G8", "Outcome replay is not byte-identical")
    primary = _ap_comparison(rows)
    controls = sealed["controls"]
    if sealed["disposition"] != disposition(primary, controls):
        raise TC004GateStop("G8", "Disposition does not follow the registered table")
    curves: dict[str, Any] = {}
    for budget in (PRIMARY_BUDGET, SECONDARY_BUDGET):
        bkey = str(budget)
        curves[bkey] = {}
        for name in POLICIES:
            curves[bkey][name] = {}
            for rate in SPLIT_RATES:
                rkey = _rate_key(rate)
                cells = [row["budgets"][bkey]["policies"][name]["rates"][rkey] for row in rows]
                curves[bkey][name][rkey] = {
                    "complete": sum(cell["complete"] for cell in cells),
                    "any": sum(cell["any"] for cell in cells),
                    "chars": _distribution(cell["chars"] for cell in cells),
                    "delivered_units": _distribution(cell["delivered_units"] for cell in cells),
                }
    positive = [row for row in rows if row["budgets"][str(PRIMARY_BUDGET)]["beneficial_parent_indices"]]
    ap_distributions = {
        name: _distribution(row["budgets"][str(PRIMARY_BUDGET)]["policies"][name]["average_precision"] for row in positive)
        for name in POLICIES
    }
    result = {
        "schema": SCHEMA,
        "stage": "G8",
        "status": "PASS",
        "registration_commit": REGISTRATION_COMMIT,
        "outcome": outcome_identity,
        "outcome_sha256": sha256_file(OUTCOME_ARTIFACT),
        "replay_sha256": hashlib.sha256(canonical_bytes(replay)).hexdigest(),
        "primary": primary,
        "disposition": sealed["disposition"],
        "beneficial_parents": sum(len(row["budgets"][str(PRIMARY_BUDGET)]["beneficial_parent_indices"] or []) for row in rows),
        "harmful_parents": sum(len(row["budgets"][str(PRIMARY_BUDGET)]["harmful_parent_indices"] or []) for row in rows),
        "average_precision_distributions": ap_distributions,
        "matched_rate_curves": curves,
        "by_conversation": {
            sample: _ap_comparison([row for row in rows if row["sample_id"] == sample])
            for sample in sorted({row["sample_id"] for row in rows})
        },
        "calls": {"embedding_during_measurement": 0, "generation": 0},
    }
    return _write(INTEGRITY_ARTIFACT, result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("capture", "g0", "outcome", "integrity"))
    parser.add_argument("--model", type=Path)
    args = parser.parse_args()
    if args.stage == "capture":
        if args.model is None:
            parser.error("capture requires --model")
        path = capture(args.model)
    elif args.stage == "g0":
        path = g0()
    elif args.stage == "outcome":
        path = outcome()
    else:
        path = integrity()
    print(path)


if __name__ == "__main__":
    main()

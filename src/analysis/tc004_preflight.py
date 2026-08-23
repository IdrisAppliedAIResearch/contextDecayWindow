"""TC-004 LoCoMo transfer mechanism and PF4 reachability.

This module is pre-registration work.  It constructs the exact pair-to-turn
split population, proves that zero splits reduce to TC-001's committed flat
arm, and checks whether the planned predictive bars could fire.  It does not
compute the proposed predictor: 2,592 required child vectors do not exist yet.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.locomo_nf_development import (
    ConversationCase,
    PairCandidate,
    QuestionCase,
    adapt_development,
    sha256_file,
)
from analysis.tc001_exploration import (
    BUDGETS,
    CACHE_PATH,
    DATASET_PATH,
    REPO_ROOT,
    VECTOR_MANIFEST,
    Episode,
    build_episodes,
    flat_context,
)
from analysis.tc004_exploration import (
    ARTIFACT_ROOT,
    _locomo_turn_texts,
    canonical_bytes,
)
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256
from episodic._packing import pack_stm_payload
from episodic._render import render_episode_element

SCHEMA = "tc004-preflight-pf4-reachability-v1"
SENTINEL_TEXT = "episodic call-shape sentinel: one text per call"
SENTINEL_VECTOR_SHA256 = (
    "baecf77627380f36f75a69c4454b064d886133f04255c5e5b4d3f24f00e7c4b8"
)
TC004_CHILD_CACHE = Path(
    "experiments/components/tier_cost/artifacts/tc004/tc004_turn_embeddings.db"
)
TC004_CHILD_MANIFEST = Path(
    "experiments/components/tier_cost/artifacts/tc004/turn_vector_manifest.json"
)


class TC004PreflightError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChildUnit:
    identity: str
    dialog_id: str
    parent_index: int
    offset: int
    text: str
    record: dict[str, Any]
    element_chars: int


@dataclass(frozen=True)
class ParentUnit:
    index: int
    episode: Episode
    children: tuple[ChildUnit, ...]

    @property
    def splittable(self) -> bool:
        return len(self.children) > 1


@dataclass(frozen=True)
class MixedPack:
    payload: str
    selected_ids: tuple[str, ...]
    delivered_dialog_ids: frozenset[str]


def _identity(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def build_parent_units(
    case: ConversationCase,
    vectors: Mapping[str, np.ndarray],
    turn_texts: Mapping[tuple[str, str], str],
) -> tuple[ParentUnit, ...]:
    episodes = build_episodes(case, dict(vectors))
    units: list[ParentUnit] = []
    for parent_index, (episode, pair) in enumerate(
        zip(episodes, case.pairs, strict=True)
    ):
        children: list[ChildUnit] = []
        for offset, dialog_id in enumerate(pair.dialog_ids):
            text = turn_texts[(case.sample_id, dialog_id)]
            child_identity = _identity(
                "tc004-child",
                case.sample_id,
                pair.session_id,
                dialog_id,
                text,
            )
            record = {
                "id": child_identity,
                "turn_number": f"{parent_index + 1}.{offset}",
                "user_message": text,
                "assistant_message": "",
                "ground_truth_domain": pair.session_id,
            }
            children.append(
                ChildUnit(
                    identity=child_identity,
                    dialog_id=dialog_id,
                    parent_index=parent_index,
                    offset=offset,
                    text=text,
                    record=record,
                    element_chars=len(render_episode_element(record)),
                )
            )
        if "\n".join(child.text for child in children) != pair.text:
            raise TC004PreflightError(
                f"{pair.identity}: children do not reconstruct the parent"
            )
        units.append(ParentUnit(parent_index, episode, tuple(children)))
    return tuple(units)


def mixed_context(
    parents: Sequence[ParentUnit],
    parent_scores: Mapping[str, float],
    child_scores: Mapping[str, float],
    split_parents: Sequence[int],
    budget: int,
) -> MixedPack:
    """Replace selected parents by children, rank every surviving unit, pack."""

    split = frozenset(split_parents)
    if budget < 0:
        raise TC004PreflightError("Budget must be non-negative")
    if any(index < 0 or index >= len(parents) for index in split):
        raise TC004PreflightError("Split parent index is out of range")
    if any(not parents[index].splittable for index in split):
        raise TC004PreflightError("A singleton parent cannot split")

    offered: list[tuple[dict[str, Any], float, int, int, tuple[str, ...]]] = []
    for parent in parents:
        pair = parent.episode.pair
        if parent.index not in split:
            identity = parent.episode.identity
            if identity not in parent_scores:
                raise TC004PreflightError(f"Missing parent score {identity}")
            offered.append(
                (
                    parent.episode.record,
                    float(parent_scores[identity]),
                    pair.session_order,
                    pair.pair_order,
                    pair.dialog_ids,
                )
            )
            continue
        for child in parent.children:
            if child.identity not in child_scores:
                raise TC004PreflightError(f"Missing child score {child.identity}")
            offered.append(
                (
                    child.record,
                    float(child_scores[child.identity]),
                    pair.session_order,
                    pair.pair_order,
                    (child.dialog_id,),
                )
            )
    if any(not math.isfinite(row[1]) for row in offered):
        raise TC004PreflightError("Candidate scores must be finite")
    offered.sort(key=lambda row: (-row[1], row[2], row[3], str(row[0]["id"])))
    records = [row[0] for row in offered]
    dialog_by_identity = {str(row[0]["id"]): row[4] for row in offered}
    packed = pack_stm_payload([], records, budget)
    delivered = frozenset(
        dialog_id
        for identity in packed.selected_ids
        for dialog_id in dialog_by_identity[identity]
    )
    return MixedPack(packed.payload, packed.selected_ids, delivered)


def _unit(vector: np.ndarray) -> np.ndarray:
    # TC-001 and the retained cache rank in float32.  Promoting here can
    # reorder near-ties and would make the zero-split arm a rewrite.
    value = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(value))
    if value.shape != (1024,) or not math.isfinite(norm) or norm == 0.0:
        raise TC004PreflightError("Expected one finite non-zero 1024-vector")
    return value / norm


def parent_scores(
    parents: Sequence[ParentUnit], query_vector: np.ndarray
) -> dict[str, float]:
    query = _unit(query_vector)
    matrix = np.stack(
        [
            _unit(np.asarray(parent.episode.record["embedding"]))
            for parent in parents
        ]
    )
    # Preserve TC-001's matrix-vector call shape as well as its dtype.  A row
    # loop can differ in the last float32 bit and reorder a packing boundary.
    values = matrix @ query
    return {
        parent.episode.identity: float(values[index])
        for index, parent in enumerate(parents)
    }


def _oracle_child_scores(
    parents: Sequence[ParentUnit],
    scores: Mapping[str, float],
    evidence: frozenset[str],
    *,
    adverse: bool,
) -> dict[str, float]:
    result: dict[str, float] = {}
    for parent in parents:
        inherited = scores[parent.episode.identity]
        for child in parent.children:
            if child.dialog_id in evidence:
                result[child.identity] = -1.0 if adverse else 1.0
            else:
                result[child.identity] = inherited
    return result


def _question_evaluable(question: QuestionCase) -> bool:
    return (
        question.duplicate_ordinal == 0
        and bool(question.resolved_evidence_ids)
        and not question.unresolved_evidence_ids
    )


def _one_sided_extreme_p(discordant: int) -> float:
    return math.pow(0.5, discordant) if discordant else 1.0


def measure(output_dir: Path = ARTIFACT_ROOT) -> dict[str, Any]:
    """Run PF4 without creating or reading treatment child vectors."""

    cases = adapt_development(DATASET_PATH)
    turn_texts = _locomo_turn_texts(DATASET_PATH)
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    with EmbeddingCache(
        CACHE_PATH,
        mode="reuse",
        expected_file_sha256=manifest["cache"]["file_sha256"],
        expected_content_sha256=manifest["cache"]["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDER_SHA256,
    ) as cache:
        vectors = {
            text: np.asarray(cache(text), dtype=np.float32)
            for case in cases
            for text in (
                *(pair.text for pair in case.pairs),
                *(question.question for question in case.questions),
            )
        }
        reuse = cache.record()
    if reuse["misses"]:
        raise TC004PreflightError("The retained parent/query cache missed")

    anchors = {str(budget): 0 for budget in BUDGETS}
    evaluable = 0
    baseline_complete = {str(budget): 0 for budget in BUDGETS}
    potential_benefit = {str(budget): 0 for budget in BUDGETS}
    potential_harm = {str(budget): 0 for budget in BUDGETS}
    beneficial_candidates = {str(budget): 0 for budget in BUDGETS}
    harmful_candidates = {str(budget): 0 for budget in BUDGETS}

    for case in cases:
        parents = build_parent_units(case, vectors, turn_texts)
        for question in case.questions:
            if not _question_evaluable(question):
                continue
            evaluable += 1
            scores = parent_scores(parents, vectors[question.question])
            evidence = frozenset(question.resolved_evidence_ids)
            evidence_parents = [
                parent
                for parent in parents
                if parent.splittable
                and any(
                    child.dialog_id in evidence for child in parent.children
                )
            ]
            positive_scores = _oracle_child_scores(
                parents, scores, evidence, adverse=False
            )
            adverse_scores = _oracle_child_scores(
                parents, scores, evidence, adverse=True
            )
            for budget in BUDGETS:
                key = str(budget)
                baseline = mixed_context(parents, scores, {}, (), budget)
                flat_payload, flat_ids = flat_context(
                    tuple(parent.episode for parent in parents),
                    vectors[question.question],
                    budget,
                )
                if baseline.payload != flat_payload or baseline.selected_ids != flat_ids:
                    raise TC004PreflightError(
                        f"{question.identity}: zero split differs from A_FLAT"
                    )
                anchors[key] += 1
                baseline_hit = evidence <= baseline.delivered_dialog_ids
                baseline_complete[key] += int(baseline_hit)
                local_benefit = local_harm = 0
                for parent in evidence_parents:
                    positive = mixed_context(
                        parents, scores, positive_scores, (parent.index,), budget
                    )
                    adverse = mixed_context(
                        parents, scores, adverse_scores, (parent.index,), budget
                    )
                    local_benefit += int(
                        not baseline_hit and evidence <= positive.delivered_dialog_ids
                    )
                    local_harm += int(
                        baseline_hit and not evidence <= adverse.delivered_dialog_ids
                    )
                beneficial_candidates[key] += local_benefit
                harmful_candidates[key] += local_harm
                potential_benefit[key] += int(local_benefit > 0)
                potential_harm[key] += int(local_harm > 0)

    vector_inventory = json.loads(
        (REPO_ROOT / ARTIFACT_ROOT / "tc004_locomo_split_inventory.json").read_text(
            encoding="utf-8"
        )
    )
    absent = vector_inventory["treatment_vector_coverage"][
        "absent_from_retained_cache"
    ]
    if absent != 2_592:
        raise TC004PreflightError("Treatment-vector absence anchor differs")

    budgets: dict[str, Any] = {}
    for budget in BUDGETS:
        key = str(budget)
        positive_n = potential_benefit[key]
        budgets[key] = {
            "budget_chars": budget,
            "evaluable_complete_evidence_questions": evaluable,
            "zero_split_a_flat_identity_checks": anchors[key],
            "zero_split_complete_evidence": baseline_complete[key],
            "oracle_positive_control": {
                "questions_with_at_least_one_possible_beneficial_split": positive_n,
                "beneficial_parent_question_cases": beneficial_candidates[key],
                "largest_attainable_question_wins": positive_n,
                "smallest_one_sided_exact_p_at_this_n": _one_sided_extreme_p(
                    positive_n
                ),
            },
            "oracle_adverse_control": {
                "questions_with_at_least_one_possible_harmful_split": potential_harm[
                    key
                ],
                "harmful_parent_question_cases": harmful_candidates[key],
            },
            "registered_tier_examples": {
                "works": {
                    "gains": 6,
                    "losses": 0,
                    "one_sided_exact_p": 0.015625,
                    "reachable": positive_n >= 6,
                },
                "carries_signal": {
                    "gains": 4,
                    "losses": 1,
                    "one_sided_exact_p": 0.1875,
                    "reachable": positive_n >= 5,
                },
                "no_signal": {
                    "gains": 1,
                    "losses": 1,
                    "one_sided_exact_p": 0.75,
                    "reachable": positive_n >= 2,
                },
            },
        }

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PREFLIGHT_PF4_ONLY",
        "note": (
            "Actual child vectors, embedding-localization scores, beneficial "
            "labels, predictor AP, and predictor direction remain unopened. "
            "Oracle controls establish only that both helpful and harmful "
            "split populations can exist under the exact renderer and budget."
        ),
        "inputs": {
            "dataset_sha256": sha256_file(DATASET_PATH),
            "vector_manifest_sha256": sha256_file(VECTOR_MANIFEST),
            "parent_query_cache_file_sha256": manifest["cache"]["file_sha256"],
            "parent_query_cache_content_sha256": manifest["cache"][
                "content_sha256"
            ],
            "parent_query_cache_misses": reuse["misses"],
            "treatment_child_vectors_absent": absent,
            "treatment_cache_exists": (REPO_ROOT / TC004_CHILD_CACHE).exists(),
            "treatment_manifest_exists": (
                REPO_ROOT / TC004_CHILD_MANIFEST
            ).exists(),
            "model_generation_calls": 0,
            "embedding_calls": 0,
            "sources": {
                "src/analysis/tc004_preflight.py": sha256_file(
                    Path(__file__).resolve()
                ),
                "src/analysis/tc004_exploration.py": sha256_file(
                    REPO_ROOT / "src/analysis/tc004_exploration.py"
                ),
                "src/analysis/tc001_exploration.py": sha256_file(
                    REPO_ROOT / "src/analysis/tc001_exploration.py"
                ),
            },
        },
        "planned_vector_capture": {
            "unique_child_texts": 2_660,
            "successful_child_calls": 2_660,
            "sentinel_calls": 1,
            "total_calls": 2_661,
            "call_shape": "solo",
            "sentinel_text": SENTINEL_TEXT,
            "sentinel_vector_sha256": SENTINEL_VECTOR_SHA256,
        },
        "budgets": budgets,
    }
    output_dir = output_dir if output_dir.is_absolute() else REPO_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "tc004_preflight_pf4_reachability.json"
    path.write_bytes(canonical_bytes(result))
    return result


__all__ = [
    "ChildUnit",
    "MixedPack",
    "ParentUnit",
    "SCHEMA",
    "TC004PreflightError",
    "TC004_CHILD_CACHE",
    "TC004_CHILD_MANIFEST",
    "build_parent_units",
    "measure",
    "mixed_context",
    "parent_scores",
]

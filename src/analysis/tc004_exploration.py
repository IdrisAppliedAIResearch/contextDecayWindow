"""Pre-registration exploration for TC-004 candidate granularity.

The roadmap asks for a query/candidate statistic that predicts when replacing
an episode by its two source turns improves evidence availability, and requires
that statistic to beat parent length.  This module does not choose a registered
statistic or bar.  It characterizes several deterministic candidates on the
committed NF-005 population and, critically, applies each score to the complete
store rather than evaluating evidence-bearing episodes alone.

All vectors are retained exact-solo vectors.  Both caches are opened read-only;
a miss is an error and this module makes no model or embedding call.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from analysis.nf002_streams import DATASET
from analysis.nf005_measurement import (
    BUDGET,
    OLD_CACHE,
    QuestionRecord,
    adapt_population,
    canonical_bytes,
    canonical_digest,
    sha256_file,
)
from analysis.nf005_mechanism import Candidate, cosine_scores
from analysis.locomo_nf_development import (
    DEVELOPMENT_IDS,
    adapt_development,
    sha256_file as locomo_sha256_file,
)
from analysis.tc001_exploration import (
    CACHE_PATH as LOCOMO_CACHE,
    DATASET_PATH as LOCOMO_DATASET,
    VECTOR_MANIFEST as LOCOMO_MANIFEST,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PART1 = Path(
    "experiments/components/biological_memory/nf_003/artifacts/part1_record.json"
)
TURN_CACHE = Path(
    "experiments/components/biological_memory/nf_005/artifacts/"
    "nf005_turn_embeddings.db"
)
TURN_MANIFEST = Path(
    "experiments/components/biological_memory/nf_005/artifacts/"
    "turn_vector_manifest.json"
)
ARTIFACT_ROOT = Path(
    "experiments/components/tier_cost/artifacts/tc004/preflight"
)

# Exploration grid only.  A registration must name its own endpoint and may
# not silently inherit this grid.
SPLIT_RATES = (0.0, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.0)
POLICIES = (
    "length",
    "lexical_localization_gain",
    "localization_gain",
    "child_spread",
    "max_child",
)


class TC004ExplorationError(RuntimeError):
    pass


@dataclass(frozen=True)
class MixedDelivery:
    selected: tuple[str, ...]
    delivered_turns: frozenset[str]
    packed_chars: int
    delivered_candidates: int


class LegacyCache:
    """Read-only access to the retained EC-002 query and episode vectors."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.connection = sqlite3.connect(
            f"file:{self.path.as_posix()}?mode=ro", uri=True
        )
        self.hits = 0

    def close(self) -> None:
        self.connection.close()

    def vector(self, text: str) -> np.ndarray:
        row = self.connection.execute(
            "select embedding from cache where text=?", (text,)
        ).fetchone()
        if row is None:
            raise TC004ExplorationError(
                f"Retained episode cache miss for {len(text)} characters"
            )
        self.hits += 1
        return np.frombuffer(row[0], dtype=np.float32).copy()


def population_ids(root: Path = REPO_ROOT) -> frozenset[str]:
    payload = json.loads((root / PART1).read_text(encoding="utf-8"))
    return frozenset(str(row["question_id"]) for row in payload["rows"])


def score_candidates(
    record: QuestionRecord,
    episode_scores: np.ndarray,
    turn_scores: np.ndarray,
) -> dict[str, np.ndarray]:
    """Return evidence-blind candidate/query split scores.

    ``localization_gain`` is the prospective mechanism named by the roadmap's
    missing operational clause: how much the best child score rises above the
    aggregate parent's score.  The remaining query-conditioned scores are
    exploration comparators; ``length`` is the required free baseline.
    """

    if len(episode_scores) != len(record.episodes):
        raise TC004ExplorationError("Episode score cardinality differs")
    if len(turn_scores) != len(record.turns) or len(record.turns) != 2 * len(
        record.episodes
    ):
        raise TC004ExplorationError("Every episode must have exactly two turns")
    children = np.asarray(turn_scores, dtype=np.float64).reshape(-1, 2)
    parents = np.asarray(episode_scores, dtype=np.float64)
    if not np.all(np.isfinite(children)) or not np.all(np.isfinite(parents)):
        raise TC004ExplorationError("Split scores must be finite")
    child_max = children.max(axis=1)
    lexical_parent = np.asarray(
        [_lexical_cosine(record.question, source.candidate.text) for source in record.episodes]
    )
    lexical_children = np.asarray(
        [_lexical_cosine(record.question, source.candidate.text) for source in record.turns]
    ).reshape(-1, 2)
    return {
        "length": np.asarray(
            [source.candidate.chars for source in record.episodes],
            dtype=np.float64,
        ),
        "lexical_localization_gain": lexical_children.max(axis=1) - lexical_parent,
        "localization_gain": child_max - parents,
        "child_spread": child_max - children.min(axis=1),
        "max_child": child_max,
    }


def _tokens(text: str) -> Counter[str]:
    return Counter(re.findall(r"[a-z0-9]+", text.casefold()))


def _lexical_cosine(left: str, right: str) -> float:
    """Cosine over deterministic lowercase token-count vectors.

    This is the literal model-free comparator.  It has no vocabulary, fitted
    weights, corpus statistics, or learned parameters.
    """

    left_counts = _tokens(left)
    right_counts = _tokens(right)
    if not left_counts or not right_counts:
        return 0.0
    shared = left_counts.keys() & right_counts.keys()
    dot = sum(left_counts[token] * right_counts[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left_counts.values()))
    right_norm = math.sqrt(sum(value * value for value in right_counts.values()))
    return dot / (left_norm * right_norm)


def policy_order(
    record: QuestionRecord, scores: Sequence[float]
) -> tuple[int, ...]:
    if len(scores) != len(record.episodes):
        raise TC004ExplorationError("Policy score cardinality differs")
    if any(not math.isfinite(float(value)) for value in scores):
        raise TC004ExplorationError("Policy scores must be finite")
    return tuple(
        sorted(
            range(len(record.episodes)),
            key=lambda index: (
                -float(scores[index]),
                record.episodes[index].candidate.session_order,
                record.episodes[index].candidate.episode_order,
            ),
        )
    )


def split_count(rate: float, candidates: int) -> int:
    if not 0.0 <= rate <= 1.0:
        raise TC004ExplorationError("Split rate must be in [0, 1]")
    if rate == 0.0:
        return 0
    if rate == 1.0:
        return candidates
    return min(candidates, math.ceil(rate * candidates))


def mixed_delivery(
    record: QuestionRecord,
    episode_scores: Sequence[float],
    turn_scores: Sequence[float],
    split_parents: Iterable[int],
    *,
    budget: int = BUDGET,
) -> MixedDelivery:
    """Rank and pack a store where selected parents are replaced by children."""

    if budget < 0:
        raise TC004ExplorationError("Budget must be non-negative")
    split = frozenset(split_parents)
    if any(index < 0 or index >= len(record.episodes) for index in split):
        raise TC004ExplorationError("Split parent index is out of range")
    if len(episode_scores) != len(record.episodes):
        raise TC004ExplorationError("Episode score cardinality differs")
    if len(turn_scores) != len(record.turns):
        raise TC004ExplorationError("Turn score cardinality differs")

    units: list[tuple[Candidate, float, tuple[str, ...]]] = []
    for parent_index, source in enumerate(record.episodes):
        if parent_index not in split:
            units.append(
                (
                    source.candidate,
                    float(episode_scores[parent_index]),
                    source.turn_identities,
                )
            )
            continue
        for turn_index in (2 * parent_index, 2 * parent_index + 1):
            turn = record.turns[turn_index].candidate
            units.append((turn, float(turn_scores[turn_index]), (turn.identity,)))

    ordered = sorted(
        units,
        key=lambda row: (
            -row[1],
            row[0].session_order,
            row[0].episode_order,
            row[0].turn_offset,
        ),
    )
    used = 0
    selected: list[str] = []
    delivered: set[str] = set()
    for candidate, _score, represented_turns in ordered:
        if candidate.chars != len(candidate.text):
            raise TC004ExplorationError("Candidate cost differs from text")
        if used + candidate.chars > budget:
            continue
        used += candidate.chars
        selected.append(candidate.identity)
        delivered.update(represented_turns)
    return MixedDelivery(
        selected=tuple(selected),
        delivered_turns=frozenset(delivered),
        packed_chars=used,
        delivered_candidates=len(selected),
    )


def _quantiles(values: Sequence[float]) -> dict[str, int | float]:
    if not values:
        raise TC004ExplorationError("Cannot summarize an empty distribution")
    array = np.asarray(values, dtype=np.float64)
    return {
        "n": int(array.size),
        "min": float(array.min()),
        "p10": float(np.quantile(array, 0.10, method="nearest")),
        "p50": float(np.quantile(array, 0.50, method="nearest")),
        "p90": float(np.quantile(array, 0.90, method="nearest")),
        "max": float(array.max()),
    }


def _paired(rows: Sequence[dict[str, Any]], policy: str, rate_key: str) -> dict[str, int]:
    gains = losses = 0
    for row in rows:
        baseline = row["policies"]["length"][rate_key]["any_evidence"]
        treatment = row["policies"][policy][rate_key]["any_evidence"]
        gains += int(treatment and not baseline)
        losses += int(baseline and not treatment)
    return {
        "gains": gains,
        "losses": losses,
        "net": gains - losses,
        "discordant": gains + losses,
    }


def _rate_key(rate: float) -> str:
    return f"{rate:.2f}"


def average_precision(order: Sequence[int], positives: frozenset[int]) -> float | None:
    """Average precision for a within-store candidate ordering."""

    if len(order) != len(set(order)):
        raise TC004ExplorationError("Average-precision order contains duplicates")
    if not positives:
        return None
    if not positives <= set(order):
        raise TC004ExplorationError("A positive candidate is absent from the order")
    hits = 0
    precision_sum = 0.0
    for rank, index in enumerate(order, start=1):
        if index in positives:
            hits += 1
            precision_sum += hits / rank
    return precision_sum / len(positives)


def explore(
    output_dir: Path = ARTIFACT_ROOT,
    *,
    root: Path = REPO_ROOT,
    dataset_path: Path = DATASET,
) -> dict[str, Any]:
    """Execute TC-004 Part 1 and write its canonical artifact."""

    started = time.perf_counter()
    records = adapt_population(dataset_path, population_ids(root))
    manifest_path = root / TURN_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cache_record = manifest["cache"]

    from episodic import EmbeddingCache

    legacy = LegacyCache(root / OLD_CACHE)
    rows: list[dict[str, Any]] = []
    score_values: dict[str, list[float]] = {name: [] for name in POLICIES}
    evidence_score_values: dict[str, list[float]] = {name: [] for name in POLICIES}
    evidence_rescue_values: dict[str, list[float]] = {name: [] for name in POLICIES}
    candidate_count_values: list[float] = []
    exact_ties = {name: 0 for name in POLICIES}
    try:
        with EmbeddingCache(
            root / TURN_CACHE,
            mode="reuse",
            expected_file_sha256=cache_record["file_sha256"],
            expected_content_sha256=cache_record["content_sha256"],
            expected_model_sha256=cache_record["model_sha256"],
        ) as turn_cache:
            for record in records:
                query = legacy.vector(record.question)
                episode_vectors = np.vstack(
                    [legacy.vector(source.candidate.text) for source in record.episodes]
                )
                turn_vectors = np.vstack(
                    [
                        np.asarray(turn_cache(source.candidate.text), dtype=np.float32)
                        for source in record.turns
                    ]
                )
                episode_scores = cosine_scores(episode_vectors, query)
                turn_scores = cosine_scores(turn_vectors, query)
                policy_scores = score_candidates(record, episode_scores, turn_scores)
                candidate_count_values.append(float(len(record.episodes)))
                target_turns = frozenset(
                    source.candidate.identity
                    for source in record.turns
                    if source.is_target
                )
                evidence_parents = {
                    source.candidate.parent_index
                    for source in record.turns
                    if source.is_target
                }
                zero = mixed_delivery(record, episode_scores, turn_scores, ())
                full = mixed_delivery(
                    record,
                    episode_scores,
                    turn_scores,
                    range(len(record.episodes)),
                )
                zero_any = bool(target_turns & zero.delivered_turns)
                full_any = bool(target_turns & full.delivered_turns)
                rescue = full_any and not zero_any

                beneficial: set[int] = set()
                harmful: set[int] = set()
                for parent_index in range(len(record.episodes)):
                    solo = mixed_delivery(
                        record,
                        episode_scores,
                        turn_scores,
                        (parent_index,),
                    )
                    solo_any = bool(target_turns & solo.delivered_turns)
                    if solo_any and not zero_any:
                        beneficial.add(parent_index)
                    elif zero_any and not solo_any:
                        harmful.add(parent_index)

                row: dict[str, Any] = {
                    "question_id": record.question_id,
                    "question_type": record.question_type,
                    "candidates": len(record.episodes),
                    "target_turns": len(target_turns),
                    "zero_split": {
                        "any_evidence": zero_any,
                        "all_evidence": target_turns <= zero.delivered_turns,
                        "packed_chars": zero.packed_chars,
                        "selected_digest": canonical_digest(list(zero.selected)),
                    },
                    "full_split": {
                        "any_evidence": full_any,
                        "all_evidence": target_turns <= full.delivered_turns,
                        "packed_chars": full.packed_chars,
                        "selected_digest": canonical_digest(list(full.selected)),
                    },
                    "leave_one_out": {
                        "beneficial_candidates": len(beneficial),
                        "harmful_candidates": len(harmful),
                        "beneficial_index_digest": canonical_digest(sorted(beneficial)),
                        "harmful_index_digest": canonical_digest(sorted(harmful)),
                    },
                    "policies": {},
                }
                for name, values in policy_scores.items():
                    numeric = [float(value) for value in values]
                    score_values[name].extend(numeric)
                    evidence_score_values[name].extend(
                        numeric[index] for index in sorted(evidence_parents)
                    )
                    if rescue:
                        evidence_rescue_values[name].extend(
                            numeric[index] for index in sorted(evidence_parents)
                        )
                    exact_ties[name] += len(numeric) - len(set(numeric))
                    order = policy_order(record, numeric)
                    row["leave_one_out"].setdefault("average_precision", {})[name] = (
                        average_precision(order, frozenset(beneficial))
                    )
                    policy_rows: dict[str, Any] = {}
                    for rate in SPLIT_RATES:
                        count = split_count(rate, len(order))
                        delivery = mixed_delivery(
                            record,
                            episode_scores,
                            turn_scores,
                            order[:count],
                        )
                        policy_rows[_rate_key(rate)] = {
                            "split_candidates": count,
                            "any_evidence": bool(target_turns & delivery.delivered_turns),
                            "all_evidence": target_turns <= delivery.delivered_turns,
                            "packed_chars": delivery.packed_chars,
                            "delivered_candidates": delivery.delivered_candidates,
                            "selected_digest": canonical_digest(list(delivery.selected)),
                        }
                    row["policies"][name] = policy_rows
                rows.append(row)
            turn_hits = turn_cache.hits
            turn_misses = turn_cache.misses
    finally:
        legacy.close()

    curves: dict[str, dict[str, Any]] = {}
    for name in POLICIES:
        points: dict[str, Any] = {}
        for rate in SPLIT_RATES:
            key = _rate_key(rate)
            points[key] = {
                "any_evidence": sum(
                    row["policies"][name][key]["any_evidence"] for row in rows
                ),
                "all_evidence": sum(
                    row["policies"][name][key]["all_evidence"] for row in rows
                ),
                "split_candidates": sum(
                    row["policies"][name][key]["split_candidates"] for row in rows
                ),
                "packed_chars": _quantiles(
                    [float(row["policies"][name][key]["packed_chars"]) for row in rows]
                ),
                "vs_length": (
                    None if name == "length" else _paired(rows, name, key)
                ),
            }
        curves[name] = points

    positive_rows = [
        row for row in rows if row["leave_one_out"]["beneficial_candidates"]
    ]
    leave_one_out_policies: dict[str, Any] = {}
    for name in POLICIES:
        values = [
            float(row["leave_one_out"]["average_precision"][name])
            for row in positive_rows
        ]
        comparison = None
        if name != "length":
            gains = losses = ties = 0
            differences: list[float] = []
            for row in positive_rows:
                baseline = float(
                    row["leave_one_out"]["average_precision"]["length"]
                )
                treatment = float(
                    row["leave_one_out"]["average_precision"][name]
                )
                difference = treatment - baseline
                differences.append(difference)
                gains += int(difference > 0.0)
                losses += int(difference < 0.0)
                ties += int(difference == 0.0)
            comparison = {
                "gains": gains,
                "losses": losses,
                "ties": ties,
                "net": gains - losses,
                "mean_ap_difference": float(np.mean(differences)),
                "difference_distribution": _quantiles(differences),
            }
        leave_one_out_policies[name] = {
            "average_precision": _quantiles(values),
            "mean_average_precision": float(np.mean(values)),
            "vs_length": comparison,
        }

    zero_any = sum(row["zero_split"]["any_evidence"] for row in rows)
    full_any = sum(row["full_split"]["any_evidence"] for row in rows)
    convergence = {
        endpoint: all(
            len(
                {
                    row["policies"][name][endpoint]["selected_digest"]
                    for name in POLICIES
                }
            )
            == 1
            for row in rows
        )
        for endpoint in (_rate_key(0.0), _rate_key(1.0))
    }
    payload: dict[str, Any] = {
        "schema": "tc004-preflight-part1-v1",
        "status": "PASS" if zero_any == 351 and full_any == 461 else "FAIL",
        "question": (
            "Can a deterministic candidate/query statistic choose which parent "
            "episodes to split into source turns better than parent length alone?"
        ),
        "behavioral_identity": (
            "A split replaces one parent episode and its aggregate cosine with "
            "two independently ranked source turns; unsplit parents and split "
            "children then compete in one skip-on-overflow 32,000-character pack."
        ),
        "inputs": {
            "dataset": {
                "path": str(dataset_path),
                "sha256": sha256_file(dataset_path),
            },
            "population": {
                "path": PART1.as_posix(),
                "sha256": sha256_file(root / PART1),
                "items": len(records),
            },
            "episode_cache": {
                "path": OLD_CACHE.as_posix(),
                "sha256": sha256_file(root / OLD_CACHE),
                "hits": legacy.hits,
                "misses": 0,
            },
            "turn_cache": {
                "path": TURN_CACHE.as_posix(),
                "manifest_sha256": sha256_file(manifest_path),
                "file_sha256": cache_record["file_sha256"],
                "content_sha256": cache_record["content_sha256"],
                "hits": turn_hits,
                "misses": turn_misses,
            },
        },
        "population": {
            "items": len(rows),
            "candidate_counts": _quantiles(candidate_count_values),
            "total_parent_candidates": int(sum(candidate_count_values)),
            "zero_split_any": zero_any,
            "full_split_any": full_any,
            "zero_split_all": sum(row["zero_split"]["all_evidence"] for row in rows),
            "full_split_all": sum(row["full_split"]["all_evidence"] for row in rows),
            "full_vs_zero_gains": sum(
                row["full_split"]["any_evidence"]
                and not row["zero_split"]["any_evidence"]
                for row in rows
            ),
            "full_vs_zero_losses": sum(
                row["zero_split"]["any_evidence"]
                and not row["full_split"]["any_evidence"]
                for row in rows
            ),
        },
        "score_distributions": {
            name: {
                "all_candidates": _quantiles(score_values[name]),
                "evidence_candidates": _quantiles(evidence_score_values[name]),
                "evidence_candidates_on_rescued_questions": _quantiles(
                    evidence_rescue_values[name]
                ),
                "exact_ties_beyond_first": exact_ties[name],
            }
            for name in POLICIES
        },
        "leave_one_out": {
            "definition": (
                "A parent is beneficial when replacing only that parent by its "
                "two independently ranked turns changes the question from no "
                "exact evidence delivered to some exact evidence delivered."
            ),
            "questions_with_a_beneficial_candidate": len(positive_rows),
            "beneficial_candidates": sum(
                row["leave_one_out"]["beneficial_candidates"] for row in rows
            ),
            "harmful_candidates": sum(
                row["leave_one_out"]["harmful_candidates"] for row in rows
            ),
            "policies": leave_one_out_policies,
        },
        "split_rates": list(SPLIT_RATES),
        "curves": curves,
        "degenerate_states": {
            "zero_split_policy_convergence": convergence[_rate_key(0.0)],
            "full_split_policy_convergence": convergence[_rate_key(1.0)],
            "full_store_fit_items": sum(
                sum(source.candidate.chars for source in record.episodes) <= BUDGET
                for record in records
            ),
            "feedback": False,
            "constant_length_policy_possible": any(
                len({source.candidate.chars for source in record.episodes}) == 1
                for record in records
            ),
        },
        "surrogate_audit": {
            "candidate_only_can_pass_while_store_policy_loses": True,
            "accepted_primary_level_for_registration": (
                "paired per-question availability under a policy applied to every "
                "candidate at a matched split rate"
            ),
            "residuals": [
                "availability is not reader use",
                "source-turn boundaries are supplied by the corpus rather than discovered",
                "the retained embedder is fixed, so transfer to another embedder is untested",
                "splitting changes semantic localization and rendered granularity together",
            ],
        },
        "calls": {
            "embedding": 0,
            "generation": 0,
            "cache_misses": turn_misses,
        },
        "rows_digest": canonical_digest(rows),
        "question_rows": [
            {
                "question_id": row["question_id"],
                "question_type": row["question_type"],
                "candidates": row["candidates"],
                "target_turns": row["target_turns"],
                "zero_split_any": row["zero_split"]["any_evidence"],
                "zero_split_all": row["zero_split"]["all_evidence"],
                "full_split_any": row["full_split"]["any_evidence"],
                "full_split_all": row["full_split"]["all_evidence"],
                "beneficial_candidates": row["leave_one_out"][
                    "beneficial_candidates"
                ],
                "harmful_candidates": row["leave_one_out"]["harmful_candidates"],
                "average_precision": row["leave_one_out"]["average_precision"],
            }
            for row in rows
        ],
        "elapsed_seconds": time.perf_counter() - started,
    }
    output_dir = output_dir if output_dir.is_absolute() else root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "tc004_preflight_part1.json"
    artifact.write_bytes(canonical_bytes(payload))
    return payload


def _locomo_turn_texts(dataset_path: Path) -> dict[tuple[str, str], str]:
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    texts: dict[tuple[str, str], str] = {}
    session_pattern = re.compile(r"session_(\d+)")
    for row in raw:
        sample_id = str(row.get("sample_id", ""))
        if sample_id not in DEVELOPMENT_IDS:
            continue
        sessions = sorted(
            (
                (int(match.group(1)), key)
                for key in row["conversation"]
                if (match := session_pattern.fullmatch(key))
            )
        )
        for _order, session_id in sessions:
            for turn in row["conversation"][session_id]:
                key = (sample_id, str(turn["dia_id"]))
                if key in texts:
                    raise TC004ExplorationError(f"Duplicate LoCoMo turn {key}")
                texts[key] = f"{turn['speaker']}: {turn['text']}"
    return texts


def locomo_split_inventory(
    output_dir: Path = ARTIFACT_ROOT,
    *,
    root: Path = REPO_ROOT,
    dataset_path: Path = LOCOMO_DATASET,
) -> dict[str, Any]:
    """Characterize the unopened LoCoMo pair-to-turn transfer population.

    Evidence outcomes and child vectors are deliberately not computed.  The
    retained cache is queried read-only only to prove which exact child texts
    already exist and which would require a post-registration capture.
    """

    cases = adapt_development(dataset_path)
    turn_text = _locomo_turn_texts(dataset_path)
    parent_chars: list[float] = []
    child_chars: list[float] = []
    children_per_parent: list[float] = []
    lexical_gains: list[float] = []
    length_ties = lexical_ties = 0
    unique_children: set[str] = set()
    splittable = singleton = 0

    for case in cases:
        children_by_pair: list[tuple[str, ...]] = []
        for pair in case.pairs:
            children = tuple(turn_text[(case.sample_id, value)] for value in pair.dialog_ids)
            if "\n".join(children) != pair.text:
                raise TC004ExplorationError(
                    f"{pair.identity}: child texts do not reconstruct the parent"
                )
            children_by_pair.append(children)
            parent_chars.append(float(pair.chars))
            child_chars.extend(float(len(text)) for text in children)
            children_per_parent.append(float(len(children)))
            unique_children.update(children)
            if len(children) > 1:
                splittable += 1
            else:
                singleton += 1

        for question in case.questions:
            length_scores: list[float] = []
            local_scores: list[float] = []
            for pair, children in zip(case.pairs, children_by_pair, strict=True):
                if len(children) < 2:
                    continue
                parent_score = _lexical_cosine(question.question, pair.text)
                local = max(
                    _lexical_cosine(question.question, child) for child in children
                ) - parent_score
                length_scores.append(float(pair.chars))
                local_scores.append(local)
                lexical_gains.append(local)
            length_ties += len(length_scores) - len(set(length_scores))
            lexical_ties += len(local_scores) - len(set(local_scores))

    manifest = json.loads(LOCOMO_MANIFEST.read_text(encoding="utf-8"))
    connection = sqlite3.connect(
        f"file:{LOCOMO_CACHE.resolve().as_posix()}?mode=ro", uri=True
    )
    try:
        existing = sum(
            connection.execute(
                "select 1 from cache where text=?", (text,)
            ).fetchone()
            is not None
            for text in unique_children
        )
    finally:
        connection.close()

    payload: dict[str, Any] = {
        "schema": "tc004-locomo-split-inventory-v1",
        "status": "PREFLIGHT_PART_1_ONLY",
        "behavioral_identity": (
            "A LoCoMo split replaces one adjacent dialogue pair by its exact "
            "one or two speaker-labelled turns; singleton pairs cannot split."
        ),
        "inputs": {
            "dataset": {
                "path": str(dataset_path),
                "sha256": locomo_sha256_file(dataset_path),
            },
            "development_ids": sorted(DEVELOPMENT_IDS),
            "vector_manifest": {
                "path": LOCOMO_MANIFEST.relative_to(root).as_posix(),
                "sha256": sha256_file(LOCOMO_MANIFEST),
            },
            "retained_cache": {
                "path": LOCOMO_CACHE.relative_to(root).as_posix(),
                "file_sha256": manifest["cache"]["file_sha256"],
                "content_sha256": manifest["cache"]["content_sha256"],
            },
        },
        "population": {
            "conversations": len(cases),
            "questions": sum(len(case.questions) for case in cases),
            "unique_nonduplicate_questions_with_resolved_evidence": sum(
                not question.duplicate_ordinal and bool(question.resolved_evidence_ids)
                for case in cases
                for question in case.questions
            ),
            "parents": sum(len(case.pairs) for case in cases),
            "splittable_parents": splittable,
            "singleton_parents": singleton,
            "parent_chars": _quantiles(parent_chars),
            "child_occurrences": int(sum(children_per_parent)),
            "unique_child_texts": len(unique_children),
            "child_chars": _quantiles(child_chars),
            "children_per_parent": _quantiles(children_per_parent),
        },
        "model_free_score": {
            "name": "lexical_localization_gain",
            "definition": (
                "maximum child/query lowercase token-count cosine minus "
                "parent/query lowercase token-count cosine"
            ),
            "distribution": _quantiles(lexical_gains),
            "length_exact_ties_beyond_first": length_ties,
            "score_exact_ties_beyond_first": lexical_ties,
            "learned_parameters": 0,
            "corpus_statistics": 0,
            "model_calls": 0,
        },
        "treatment_vector_coverage": {
            "unique_child_texts": len(unique_children),
            "already_in_retained_cache": existing,
            "absent_from_retained_cache": len(unique_children) - existing,
            "treatment_outcome_opened": False,
        },
        "degenerate_states": {
            "feedback": False,
            "singleton_pairs_cannot_split": singleton,
            "constant_score_pairs": sum(value == 0.0 for value in lexical_gains),
            "all_parents_singleton": splittable == 0,
        },
        "calls": {"embedding": 0, "generation": 0},
    }
    output_dir = output_dir if output_dir.is_absolute() else root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "tc004_locomo_split_inventory.json"
    artifact.write_bytes(canonical_bytes(payload))
    return payload


__all__ = [
    "ARTIFACT_ROOT",
    "POLICIES",
    "SPLIT_RATES",
    "MixedDelivery",
    "TC004ExplorationError",
    "explore",
    "average_precision",
    "mixed_delivery",
    "locomo_split_inventory",
    "policy_order",
    "score_candidates",
    "split_count",
]

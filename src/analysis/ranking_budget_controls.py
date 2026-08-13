"""Development-only ranking and budget controls for LoCoMo and LongMemEval."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from analysis import nf002_streams
from analysis.locomo_nf_development import (
    ConversationCase,
    PairCandidate,
    _unit,
    adapt_development,
    pack_indices,
    ranking_orders,
)
from analysis.nf002_gates import assign_split
from analysis.nf003_ranking import EmbeddingCache as LongMemEvalCache
from analysis.nf003_ranking import compose_episodes, episode_ranking
from episodic import EmbeddingCache
from retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256

SCHEMA = "ranking-budget-development-controls-v1"
SPEC = Path("experiments/external/locomo/RANKING_BUDGET_CONTROL_PLAN.md")
SPEC_COMMIT = "cddb1a86faa251eb5920715bbced235698e7ae9e"
SPEC_LF_SHA256 = "6f46bb7513b9b06d7859137ba4fc1b9735f6eda25c4b0cb83d5a522f6fb59450"
LOCOMO_ANALYSIS = Path(
    "experiments/external/locomo/artifacts/development_analysis.json"
)
LOCOMO_ANALYSIS_SHA256 = "d3621b30cae18e679cedf13811e1240a47eb565efe69fbb24583ce2af63b95ab"
LOCOMO_BUDGETS = (
    4_000,
    8_000,
    12_000,
    16_000,
    20_000,
    24_000,
    28_000,
    32_000,
    40_000,
    48_000,
    56_000,
    64_000,
    80_000,
    96_000,
)
LONGMEMEVAL_BUDGETS = (
    8_000,
    16_000,
    24_000,
    32_000,
    40_000,
    48_000,
    64_000,
    80_000,
    96_000,
)


class RankingBudgetControlError(RuntimeError):
    pass


def _lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _distribution(values: Iterable[float]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        raise RankingBudgetControlError("Cannot summarize an empty distribution")

    def nearest(percentile: float) -> float:
        return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]

    return {
        "min": ordered[0],
        "p10": nearest(0.10),
        "p50": nearest(0.50),
        "p90": nearest(0.90),
        "max": ordered[-1],
    }


def _paired(
    rows: Sequence[dict[str, Any]], baseline: str, treatment: str
) -> dict[str, Any]:
    eligible = [
        row for row in rows if row[baseline] is not None and row[treatment] is not None
    ]
    gains = sum(row[treatment] and not row[baseline] for row in eligible)
    losses = sum(row[baseline] and not row[treatment] for row in eligible)
    discordant = gains + losses
    p = (
        sum(math.comb(discordant, k) for k in range(gains, discordant + 1))
        / (2**discordant)
        if discordant
        else 1.0
    )
    return {
        "n": len(eligible),
        "gains": gains,
        "losses": losses,
        "ties": len(eligible) - discordant,
        "net": gains - losses,
        "p_one_sided": p,
    }


def _arm_summary(
    rows: Sequence[dict[str, Any]], arm: str
) -> dict[str, Any]:
    any_key = f"{arm}_any"
    all_key = f"{arm}_all"
    all_rows = [row for row in rows if row[all_key] is not None]
    return {
        "any_evidence": {
            "hits": sum(row[any_key] for row in rows),
            "n": len(rows),
        },
        "all_evidence": {
            "hits": sum(row[all_key] for row in all_rows),
            "n": len(all_rows),
        },
        "delivered_candidates": _distribution(
            float(row[f"{arm}_delivered"]) for row in rows
        ),
        "packed_chars": _distribution(float(row[f"{arm}_chars"]) for row in rows),
    }


def _locomo_controls(
    conversations: Sequence[ConversationCase],
    cache_path: Path,
    vector_manifest: dict[str, Any],
) -> dict[str, Any]:
    cache_record = vector_manifest["cache"]
    outcomes: list[dict[str, Any]] = []
    with EmbeddingCache(
        cache_path,
        mode="reuse",
        expected_file_sha256=cache_record["file_sha256"],
        expected_content_sha256=cache_record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    ) as cache:
        for case in conversations:
            pair_matrix = np.vstack([_unit(cache(pair.text)) for pair in case.pairs])
            dialog_to_pair = {
                dialog_id: index
                for index, pair in enumerate(case.pairs)
                for dialog_id in pair.dialog_ids
            }
            source_order = list(range(len(case.pairs)))
            total_chars = sum(pair.chars for pair in case.pairs)
            for question in case.questions:
                if question.duplicate_ordinal > 0:
                    continue
                query = _unit(cache(question.question))
                session_order, pair_order = ranking_orders(
                    case.pairs, pair_matrix @ query
                )
                evidence_pairs = {
                    dialog_to_pair[value] for value in question.resolved_evidence_ids
                }
                all_evaluable = not question.unresolved_evidence_ids
                for budget in LOCOMO_BUDGETS:
                    row: dict[str, Any] = {
                        "question_id": question.identity,
                        "sample_id": case.sample_id,
                        "category": question.category,
                        "budget": budget,
                        "total_candidate_chars": total_chars,
                    }
                    for arm, order in (
                        ("source", source_order),
                        ("session_rank", session_order),
                        ("pair_rank", pair_order),
                    ):
                        delivered, chars = pack_indices(case.pairs, order, budget)
                        delivered_set = set(delivered)
                        row[f"{arm}_any"] = bool(evidence_pairs & delivered_set)
                        row[f"{arm}_all"] = (
                            evidence_pairs <= delivered_set if all_evaluable else None
                        )
                        row[f"{arm}_delivered"] = len(delivered)
                        row[f"{arm}_chars"] = chars
                    outcomes.append(row)
        reuse_record = cache.record()

    budgets = []
    for budget in LOCOMO_BUDGETS:
        rows = [row for row in outcomes if row["budget"] == budget]
        entry = {
            "budget": budget,
            "oversubscription": _distribution(
                row["total_candidate_chars"] / budget for row in rows
            ),
            "arms": {
                arm: _arm_summary(rows, arm)
                for arm in ("source", "session_rank", "pair_rank")
            },
            "comparisons": {
                measure: {
                    "pair_vs_session": _paired(
                        rows, f"session_rank_{measure}", f"pair_rank_{measure}"
                    ),
                    "session_vs_source": _paired(
                        rows, f"source_{measure}", f"session_rank_{measure}"
                    ),
                    "pair_vs_source": _paired(
                        rows, f"source_{measure}", f"pair_rank_{measure}"
                    ),
                }
                for measure in ("any", "all")
            },
            "by_conversation_all_evidence_pair_vs_session": {
                sample_id: _paired(
                    [row for row in rows if row["sample_id"] == sample_id],
                    "session_rank_all",
                    "pair_rank_all",
                )
                for sample_id in sorted({row["sample_id"] for row in rows})
            },
        }
        budgets.append(entry)

    anchor = next(row for row in budgets if row["budget"] == 32_000)
    expected = {
        "session_any": 820,
        "pair_any": 855,
        "session_all": 773,
        "pair_all": 826,
    }
    observed = {
        "session_any": anchor["arms"]["session_rank"]["any_evidence"]["hits"],
        "pair_any": anchor["arms"]["pair_rank"]["any_evidence"]["hits"],
        "session_all": anchor["arms"]["session_rank"]["all_evidence"]["hits"],
        "pair_all": anchor["arms"]["pair_rank"]["all_evidence"]["hits"],
    }
    if observed != expected:
        raise RankingBudgetControlError(f"LoCoMo 32k anchor failed: {observed}")
    return {
        "population": {
            "unique_questions": len({row["question_id"] for row in outcomes}),
            "all_evidence_evaluable": sum(
                row["session_rank_all"] is not None
                for row in outcomes
                if row["budget"] == LOCOMO_BUDGETS[0]
            ),
            "conversations": len(conversations),
        },
        "anchor_32k": {"expected": expected, "observed": observed, "passes": True},
        "source_order_query_independent": True,
        "cache": reuse_record,
        "budgets": budgets,
        "outcomes": sorted(
            outcomes, key=lambda row: (row["budget"], row["question_id"])
        ),
    }


def _pack_episode_order(
    episodes: Sequence[Any], order: Iterable[int], budget: int
) -> tuple[bool, bool, int, int]:
    used = 0
    delivered: list[int] = []
    for index in order:
        episode = episodes[int(index)]
        if used + episode.chars > budget:
            continue
        used += episode.chars
        delivered.append(int(index))
    evidence = {index for index, episode in enumerate(episodes) if episode.is_evidence}
    delivered_set = set(delivered)
    return (
        bool(evidence & delivered_set),
        evidence <= delivered_set,
        len(delivered),
        used,
    )


def _longmemeval_controls(repository_root: Path) -> dict[str, Any]:
    streams, stream_anchor = nf002_streams.load_streams()
    assignment = assign_split(streams)
    streams_by_id = {stream.question_id: stream for stream in streams}
    items = json.loads(nf002_streams.DATASET.read_text(encoding="utf-8"))
    cache = LongMemEvalCache.open(repository_root)
    all_anchor: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    for item in items:
        question_id = item["question_id"]
        stream = streams_by_id.get(question_id)
        if stream is None:
            continue
        episodes = compose_episodes(item)
        if not any(episode.is_evidence for episode in episodes):
            continue
        session_rank = {candidate.session_id: candidate.rank for candidate in stream.candidates}
        inherited_order = sorted(
            range(len(episodes)),
            key=lambda index: (
                session_rank[episodes[index].session_id],
                episodes[index].index,
            ),
        )
        _, pair_order = episode_ranking(cache, item["question"], episodes)
        anchor_session = _pack_episode_order(episodes, inherited_order, 32_000)
        anchor_pair = _pack_episode_order(episodes, pair_order, 32_000)
        all_anchor.append(
            {
                "question_id": question_id,
                "session_any": anchor_session[0],
                "episode_any": anchor_pair[0],
            }
        )
        if assignment[question_id] != "development":
            continue
        total_chars = sum(episode.chars for episode in episodes)
        for budget in LONGMEMEVAL_BUDGETS:
            session = _pack_episode_order(episodes, inherited_order, budget)
            pair = _pack_episode_order(episodes, pair_order, budget)
            outcomes.append(
                {
                    "question_id": question_id,
                    "question_type": item.get("question_type", "unknown"),
                    "budget": budget,
                    "total_candidate_chars": total_chars,
                    "session_rank_any": session[0],
                    "session_rank_all": session[1],
                    "session_rank_delivered": session[2],
                    "session_rank_chars": session[3],
                    "episode_rank_any": pair[0],
                    "episode_rank_all": pair[1],
                    "episode_rank_delivered": pair[2],
                    "episode_rank_chars": pair[3],
                }
            )
    observed_anchor = {
        "session_any": sum(row["session_any"] for row in all_anchor),
        "episode_any": sum(row["episode_any"] for row in all_anchor),
        "n": len(all_anchor),
    }
    expected_anchor = {"session_any": 388, "episode_any": 351, "n": 465}
    if observed_anchor != expected_anchor:
        raise RankingBudgetControlError(
            f"LongMemEval 32k anchor failed: {observed_anchor}"
        )

    budgets = []
    for budget in LONGMEMEVAL_BUDGETS:
        rows = [row for row in outcomes if row["budget"] == budget]
        budgets.append(
            {
                "budget": budget,
                "oversubscription": _distribution(
                    row["total_candidate_chars"] / budget for row in rows
                ),
                "arms": {
                    arm: _arm_summary(rows, arm)
                    for arm in ("session_rank", "episode_rank")
                },
                "comparisons": {
                    measure: _paired(
                        rows,
                        f"session_rank_{measure}",
                        f"episode_rank_{measure}",
                    )
                    for measure in ("any", "all")
                },
            }
        )
    return {
        "population": {
            "development_items_with_turn_evidence": len(
                {row["question_id"] for row in outcomes}
            ),
            "all_labelled_items": len(all_anchor),
        },
        "stream_anchor": stream_anchor,
        "anchor_32k_all_labelled": {
            "expected": expected_anchor,
            "observed": observed_anchor,
            "passes": True,
        },
        "cache": {"hits": cache.hits, "misses": 0, "model_calls": 0},
        "budgets": budgets,
        "outcomes": sorted(
            outcomes, key=lambda row: (row["budget"], row["question_id"])
        ),
    }


def run(
    repository_root: Path,
    locomo_dataset: Path,
    locomo_cache: Path,
    vector_manifest_path: Path,
) -> dict[str, Any]:
    spec_path = repository_root / SPEC
    if _lf_sha256(spec_path) != SPEC_LF_SHA256:
        raise RankingBudgetControlError("Control specification changed after lock")
    analysis_path = repository_root / LOCOMO_ANALYSIS
    if _sha256(analysis_path) != LOCOMO_ANALYSIS_SHA256:
        raise RankingBudgetControlError("Committed LoCoMo analysis changed")
    conversations = adapt_development(locomo_dataset)
    manifest = json.loads(vector_manifest_path.read_text(encoding="utf-8"))
    locomo = _locomo_controls(conversations, locomo_cache, manifest)
    longmemeval = _longmemeval_controls(repository_root)
    return {
        "schema": SCHEMA,
        "status": "DEVELOPMENT_CONTROLS_ONLY",
        "specification": {
            "path": SPEC.as_posix(),
            "commit": SPEC_COMMIT,
            "lf_sha256": SPEC_LF_SHA256,
        },
        "locomo": locomo,
        "longmemeval": longmemeval,
        "model_calls": 0,
        "embedding_calls": 0,
    }


def write(
    repository_root: Path,
    locomo_dataset: Path,
    locomo_cache: Path,
    vector_manifest_path: Path,
    output: Path,
) -> Path:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    output.write_text(
        json.dumps(
            run(repository_root, locomo_dataset, locomo_cache, vector_manifest_path),
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output

"""Re-measure the DR-002 rank tables under E005's committed embedding call.

DX-001's replay gate established that the query vector depends on the shape
of the embedding call, not only on the query text. The DR-002 rank tables
were computed with a differently batched call, so they are re-measured here
against E005's committed nine-query prime and any difference is reported.

Measurement only. No mechanism code is touched.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from src.analysis.e005_diversity_selection import (
    COMPONENT_ROOT,
    PRIMARY_POOL,
    Q11_TURN,
    TARGET_PROBE_TURNS,
    EmbeddingCache,
    build_pools,
    load_candidates,
    load_queries,
)
from src.analysis.e005_diversity_selection import (
    _normalize as normalize,
)
from src.analysis.e005_diversity_selection import (
    _read_csv as read_csv,
)
from src.analysis.e005_diversity_selection import (
    _write_json as write_json,
)
from src.analysis.retrieval_bakeoff_tier6_121 import (
    ATOMIC_ITEMS,
    TARGETED_ITEMS,
)
from src.memory.stm_context_builder import render_episode_element
from src.retrieval_bakeoff.embedding import CarriedEmbedder
from src.retrieval_mechanism_ledger.e005 import (
    eligible_candidates,
    relevance_vector,
    vector,
)


PUBLISHED_RANKS = COMPONENT_ROOT / "artifacts" / "e005" / "dr_002" / "selection_ranks.csv"

# DR-002 report section 3.5, as published.
PUBLISHED_GENERALITY = {
    "Q1": {"turn": 112, "top4_hits": 4, "first_hit": 1, "last_needed": 2},
    "Q2": {"turn": 113, "top4_hits": 3, "first_hit": 2, "last_needed": 2},
    "Q4": {"turn": 115, "top4_hits": 3, "first_hit": 1, "last_needed": 2},
    "Q5": {"turn": 116, "top4_hits": 1, "first_hit": 1, "last_needed": 1},
    "Q6": {"turn": 117, "top4_hits": 1, "first_hit": 1, "last_needed": 1},
    "Q7": {"turn": 118, "top4_hits": 3, "first_hit": 1, "last_needed": 1},
    "Q8": {"turn": 119, "top4_hits": 2, "first_hit": 2, "last_needed": 2},
    "Q10": {"turn": 118, "top4_hits": 2, "first_hit": 1, "last_needed": 1},
    "Q11": {"turn": 120, "top4_hits": 0, "first_hit": 5, "last_needed": 87},
}


def run_check(output_path: Path, embedding_model: Path) -> dict:
    embedder = CarriedEmbedder(embedding_model)
    embedder.assert_carried_model()
    queries = load_queries()
    cache = EmbeddingCache(embedder)
    cache.prime(queries.values())
    candidates = load_candidates()

    probes = [
        (question, turn, tuple(needles))
        for question, (turn, needles) in sorted(TARGETED_ITEMS.items())
    ]
    probes.append(
        ("Q11", Q11_TURN, tuple(needle for _d, _i, needle, _t in ATOMIC_ITEMS))
    )

    generality = []
    for question, turn, needles in probes:
        pool = eligible_candidates(candidates, probe_turn=turn)
        ordered = _ranked(pool, vector(cache(queries[turn])))
        rendered = [normalize(render_episode_element(episode)) for episode in ordered]
        measured = _probe_row(rendered, needles)
        published = PUBLISHED_GENERALITY[question]
        generality.append(
            {
                "question": question,
                "turn": turn,
                "pool": len(pool),
                **measured,
                "published": published,
                "matches_published": all(
                    measured[field] == published[field]
                    for field in ("top4_hits", "first_hit", "last_needed")
                ),
            }
        )

    q11_pool = build_pools(candidates, queries[Q11_TURN], cache(queries[Q11_TURN]))[
        PRIMARY_POOL
    ]
    ranks = _rank_map(q11_pool, vector(cache(queries[Q11_TURN])))
    published_ranks = read_csv(PUBLISHED_RANKS)
    rank_corrections = [
        {
            "step": int(row["step"]),
            "source_turn": int(row["source_turn"]),
            "published_rank": int(row["cosine_rank"]),
            "measured_rank": ranks[str(row["episode_id"])],
        }
        for row in published_ranks
        if ranks[str(row["episode_id"])] != int(row["cosine_rank"])
    ]

    result = {
        "embedding_call": "E005 committed nine-query prime",
        "generality": generality,
        "generality_conclusion_unchanged": all(
            row["last_needed"] <= 2
            for row in generality
            if row["question"] != "Q11"
        )
        and next(
            row["last_needed"] for row in generality if row["question"] == "Q11"
        )
        > 2,
        "generality_rows_matching_published": sum(
            1 for row in generality if row["matches_published"]
        ),
        "selection_rank_corrections": rank_corrections,
        "worst_fact_bearing_rank_unchanged": all(
            correction["measured_rank"] < 80
            for correction in rank_corrections
        ),
    }
    write_json(output_path, result)
    return result


def _ranked(pool: Sequence[dict], embedding: np.ndarray) -> list[dict]:
    relevance = relevance_vector(embedding, pool)
    order = sorted(
        range(len(pool)),
        key=lambda index: (
            -float(relevance[index]),
            int(pool[index]["turn_number"]),
            str(pool[index]["id"]),
        ),
    )
    return [pool[index] for index in order]


def _rank_map(pool: Sequence[dict], embedding: np.ndarray) -> dict[str, int]:
    return {
        str(episode["id"]): position
        for position, episode in enumerate(_ranked(pool, embedding), 1)
    }


def _probe_row(rendered: Sequence[str], needles: Sequence[str]) -> dict:
    hits = {
        needle: next(
            (
                position
                for position, text in enumerate(rendered, 1)
                if needle in text
            ),
            None,
        )
        for needle in needles
    }
    found = [position for position in hits.values() if position is not None]
    return {
        "top4_hits": sum(
            1
            for text in rendered[:4]
            if any(needle in text for needle in needles)
        ),
        "first_hit": min(found) if found else None,
        "last_needed": (
            max(found) if found and len(found) == len(hits) else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-measure DR-002 ranks under E005's committed embedding call."
    )
    parser.add_argument("--embedding-model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run_check(args.output.resolve(), args.embedding_model.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

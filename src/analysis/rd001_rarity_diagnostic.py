"""RD-001 rank recovery and pre-correlation measurement feasibility gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np

from src.analysis.e005_diversity_selection import (
    COMPONENT_ROOT,
    EmbeddingCache,
    load_candidates,
    load_queries,
)
from src.retrieval_bakeoff.embedding import CarriedEmbedder
from src.retrieval_mechanism_ledger.e005 import (
    eligible_candidates,
    relevance_vector,
    vector,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN = COMPONENT_ROOT / "E006_rarity_diagnostic_and_chained_retrieval.md"
DESIGN_COMMIT = "37d5bf2d"
Q11_TURN = 120
EXPECTED_POOL_SIZE = 119
EXPECTED_FACT_BEARING = 76
EXPECTED_COMMITTED_RANKS = 16
EXPECTED_PLANTS = 6
EXPECTED_VARIANTS = (
    "rarity_mean",
    "rarity_max",
    "rarity_sum_per_word",
)

COVERAGE = COMPONENT_ROOT / "artifacts" / "ar_001" / "episode_coverage.csv"
PUBLISHED_RANKS = (
    COMPONENT_ROOT / "artifacts" / "e005" / "dr_002" / "selection_ranks.csv"
)
DX001_COST = COMPONENT_ROOT / "artifacts" / "dx001" / "cost_comparison.csv"
RARITY = (
    REPO_ROOT / "experiments" / "study_009" / "analysis"
    / "rarity_signal_feasibility.csv"
)

RANK_FIELDS = (
    "cosine_rank",
    "episode_id",
    "source_turn",
    "cosine",
    "additive_chars",
    "fact_count",
    "domains",
    "items",
)
PLANT_FIELDS = (
    "plant",
    "variant",
    "source_turn",
    "episode_id",
    "cosine_rank",
    "cosine",
    "rarity_score",
    "rarity_rank",
    "episode_chars",
    "phrase_start",
    "phrase_end",
    "phrase_found",
)


def run_rd001(output_dir: Path, embedding_model: Path) -> dict:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite RD-001 output: {output_dir}")
    output_dir.mkdir(parents=True)

    inputs = (DESIGN, COVERAGE, PUBLISHED_RANKS, DX001_COST, RARITY)
    before = hash_paths(inputs)
    candidates = load_candidates()
    queries = load_queries()

    embedder = CarriedEmbedder(embedding_model)
    embedder.assert_carried_model()
    cache = EmbeddingCache(embedder)
    # E005's committed call shape primes all nine probe queries in one batch.
    cache.prime(queries.values())

    pool = eligible_candidates(candidates, probe_turn=Q11_TURN)
    ranks = rank_pool(pool, vector(cache(queries[Q11_TURN])))
    coverage = read_csv(COVERAGE)
    coverage_by_id = {row["episode_id"]: row for row in coverage}
    if len(ranks) != EXPECTED_POOL_SIZE:
        raise AssertionError(f"Expected 119 ranked episodes, found {len(ranks)}")

    rank_rows = []
    for position, (candidate, cosine) in enumerate(ranks, 1):
        episode_id = str(candidate["id"])
        row = coverage_by_id[episode_id]
        rank_rows.append(
            {
                "cosine_rank": position,
                "episode_id": episode_id,
                "source_turn": int(candidate["turn_number"]),
                "cosine": round(cosine, 9),
                "additive_chars": int(row["additive_chars"]),
                "fact_count": int(row["fact_count"]),
                "domains": row["domains"],
                "items": row["items"],
            }
        )
    write_csv(output_dir / "full_rank_inventory.csv", rank_rows, RANK_FIELDS)

    rank_by_id = {
        row["episode_id"]: int(row["cosine_rank"]) for row in rank_rows
    }
    rank_by_turn = {
        int(row["source_turn"]): row for row in rank_rows
    }
    rank_replay = committed_rank_replay(rank_by_id, rank_by_turn)
    write_json(output_dir / "rank_replay.json", rank_replay)

    rarity_rows = [
        row for row in read_csv(RARITY) if row["row_type"] == "plant"
    ]
    plant_rows = plant_inventory(rarity_rows, rank_by_turn, candidates)
    write_csv(output_dir / "plant_rank_inventory.csv", plant_rows, PLANT_FIELDS)

    feasibility = assess_feasibility(rank_rows, rarity_rows, plant_rows, rank_replay)
    write_json(output_dir / "measurement_feasibility.json", feasibility)
    write_json(
        output_dir / "source_integrity.json",
        {
            "design_commit": DESIGN_COMMIT,
            "embedding_model_sha256": embedder.model_sha256,
            "before": before,
            "after": hash_paths(inputs),
            "status": "PASS" if before == hash_paths(inputs) else "FAIL",
        },
    )
    write_report(output_dir / "RD_001_feasibility_report.md", feasibility)
    write_manifest(output_dir)
    return feasibility


def rank_pool(
    pool: Sequence[dict],
    query_embedding: np.ndarray,
) -> list[tuple[dict, float]]:
    relevance = relevance_vector(query_embedding, pool)
    order = sorted(
        range(len(pool)),
        key=lambda index: (
            -float(relevance[index]),
            int(pool[index]["turn_number"]),
            str(pool[index]["id"]),
        ),
    )
    return [(pool[index], float(relevance[index])) for index in order]


def committed_rank_replay(
    rank_by_id: dict[str, int],
    rank_by_turn: dict[int, dict],
) -> dict:
    published = read_csv(PUBLISHED_RANKS)
    checks = [
        {
            "source_turn": int(row["source_turn"]),
            "published_rank": int(row["cosine_rank"]),
            "measured_rank": rank_by_id[row["episode_id"]],
        }
        for row in published
    ]
    target = next(
        row for row in read_csv(DX001_COST) if row["role"] == "target"
    )
    target_turn = int(target["turn"])
    checks.append(
        {
            "source_turn": target_turn,
            "published_rank": int(target["cosine_rank"]),
            "measured_rank": int(rank_by_turn[target_turn]["cosine_rank"]),
        }
    )
    corrections = [
        row
        for row in checks
        if row["published_rank"] != row["measured_rank"]
    ]
    expected_correction = [
        {"source_turn": 118, "published_rank": 21, "measured_rank": 20}
    ]
    return {
        "embedding_call": "E005 committed nine-query prime",
        "checked_rank_count": len(checks),
        "expected_rank_count": EXPECTED_COMMITTED_RANKS,
        "corrections": corrections,
        "expected_corrections": expected_correction,
        "status": (
            "PASS"
            if len(checks) == EXPECTED_COMMITTED_RANKS
            and corrections == expected_correction
            else "FAIL"
        ),
    }


def plant_inventory(
    rarity_rows: Sequence[dict],
    rank_by_turn: dict[int, dict],
    candidates: Sequence[dict],
) -> list[dict]:
    candidates_by_turn = {
        int(candidate["turn_number"]): candidate for candidate in candidates
    }
    result = []
    for rarity in rarity_rows:
        turn = int(rarity["source_turn"])
        candidate = candidates_by_turn[turn]
        ranked = rank_by_turn[turn]
        phrase = rarity["span_text"]
        user_message = str(candidate["user_message"])
        phrase_start = user_message.find(phrase)
        result.append(
            {
                "plant": rarity["plant"],
                "variant": rarity["variant"],
                "source_turn": turn,
                "episode_id": str(candidate["id"]),
                "cosine_rank": int(ranked["cosine_rank"]),
                "cosine": ranked["cosine"],
                "rarity_score": rarity["score"],
                "rarity_rank": rarity["rank"],
                "episode_chars": (
                    len(user_message) + len(str(candidate["assistant_message"]))
                ),
                "phrase_start": phrase_start,
                "phrase_end": (
                    phrase_start + len(phrase) if phrase_start >= 0 else -1
                ),
                "phrase_found": phrase_start >= 0,
            }
        )
    return result


def assess_feasibility(
    rank_rows: Sequence[dict],
    rarity_rows: Sequence[dict],
    plant_rows: Sequence[dict],
    rank_replay: dict,
) -> dict:
    fact_bearing = [
        row for row in rank_rows if int(row["fact_count"]) > 0
    ]
    fact_bearing_ids = {row["episode_id"] for row in fact_bearing}
    rarity_episode_ids = {row["episode_id"] for row in plant_rows}
    overlap = fact_bearing_ids & rarity_episode_ids
    plants = {row["plant"] for row in rarity_rows}
    variants = {row["variant"] for row in rarity_rows}

    complete = (
        len(fact_bearing) == EXPECTED_FACT_BEARING
        and overlap == fact_bearing_ids
        and len(variants) == 1
    )
    if complete:
        raise AssertionError(
            "RD-001 unexpectedly became identifiable; register the statistic "
            "and confidence interval method before computing it"
        )

    return {
        "status": "STOP_MEASUREMENT_NOT_IDENTIFIABLE",
        "registered_branch": "NONE",
        "branch_explanation": (
            "Branch D assumes the registered n=16 rank limit. The full 119 ranks "
            "were recovered, but the committed rarity artifact scores only six "
            "episodes and has three variants with no registered primary or "
            "episode-level aggregation. No registered branch covers this state."
        ),
        "full_rank_count": len(rank_rows),
        "rank_replay_status": rank_replay["status"],
        "fact_bearing_episode_count": len(fact_bearing),
        "expected_fact_bearing_episode_count": EXPECTED_FACT_BEARING,
        "rarity_plant_count": len(plants),
        "expected_rarity_plant_count": EXPECTED_PLANTS,
        "rarity_variant_count": len(variants),
        "rarity_variants": sorted(variants),
        "fact_bearing_episodes_with_committed_rarity": len(overlap),
        "fact_bearing_episodes_without_committed_rarity": (
            len(fact_bearing_ids - rarity_episode_ids)
        ),
        "all_plant_phrases_found_verbatim": all(
            row["phrase_found"] for row in plant_rows
        ),
        "spearman_computed": False,
        "confidence_interval_computed": False,
        "reason_no_coefficient": (
            "Computing one would require a new rarity score for 70 episodes, "
            "choosing one of three variants, and defining an episode aggregation. "
            "All three choices are absent from the locked design."
        ),
        "part_2_authorized": False,
        "paper_must_pause": True,
        "paper_reason": (
            "PAPER-001 says the ranks and phrases needed for the correlation are "
            "already committed. RD-001 establishes that the two artifacts do not "
            "share the registered episode-level measurement unit."
        ),
    }


def write_report(path: Path, result: dict) -> None:
    lines = [
        "# RD-001 Measurement Feasibility Report",
        "",
        f"**Design anchor:** `{DESIGN_COMMIT}`",
        f"**Status:** **{result['status']}**",
        f"**Registered branch:** **{result['registered_branch']}**",
        "**Part 2:** **NOT AUTHORIZED**",
        "",
        "## Outcome",
        "",
        "The full 119-episode cosine ordering is recoverable under E005's "
        "committed nine-query embedding call, and all 16 published rank checks "
        "replay with only the already-recorded turn-118 correction from 21 to 20.",
        "",
        "The correlation is not identifiable from the promised committed "
        "artifact sets. The rank inventory contains "
        f"{result['fact_bearing_episode_count']} fact-bearing episodes, while "
        "the rarity artifact supplies scores for only "
        f"{result['fact_bearing_episodes_with_committed_rarity']} of them. It "
        f"also supplies {result['rarity_variant_count']} variants without a "
        "registered primary or episode-level aggregation.",
        "",
        "No Spearman coefficient or confidence interval was computed. Doing so "
        "would require unregistered measurement choices after the decision rule.",
        "",
        "## Decision",
        "",
        result["branch_explanation"],
        "",
        "RD-001 therefore stops as **measurement not identifiable**. This is not "
        "Branch B and does not authorize chained retrieval. PAPER-001 must pause "
        "long enough to withdraw its claim that the correlation is runnable from "
        "already-committed ranks and phrases.",
        "",
        "## Artifact Counts",
        "",
        f"- Full ranks: {result['full_rank_count']}",
        f"- Fact-bearing episodes: {result['fact_bearing_episode_count']}",
        f"- Fact-bearing episodes with committed rarity: "
        f"{result['fact_bearing_episodes_with_committed_rarity']}",
        f"- Fact-bearing episodes without committed rarity: "
        f"{result['fact_bearing_episodes_without_committed_rarity']}",
        f"- Rarity plants: {result['rarity_plant_count']}",
        f"- Rarity variants: {', '.join(result['rarity_variants'])}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict], fields: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def hash_paths(paths: Iterable[Path]) -> dict[str, str]:
    return {
        str(path.relative_to(REPO_ROOT)).replace("\\", "/"): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in paths
    }


def write_manifest(output_dir: Path) -> None:
    artifacts = {}
    for path in sorted(output_dir.iterdir()):
        if path.name == "artifact_manifest.json":
            continue
        artifacts[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(
        output_dir / "artifact_manifest.json",
        {"artifacts": artifacts, "status": "COMPLETE"},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embedding-model", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = run_rd001(args.output_dir, args.embedding_model)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

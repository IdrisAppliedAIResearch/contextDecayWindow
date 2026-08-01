"""CC-002 T3: the E005 primary result reproduces through the library import.

Replays every committed A3 selection record (132 of E005's 146
`full_eligible_store` configurations) and the primary configuration's
eight targeted-probe selections using episodic's selector, greedy frame,
and renderer, then re-measures the primary result vector:
12/17 across 4/4 domains, 16/16 targeted preserved, 31,569 chars.

Byte-identity is the bar: every payload SHA-256 must equal the committed
one. If a number moves, the extraction changed behavior and the PR does
not merge until the cause is found.

Queries are embedded under the committed batched call shape via the
harness's CarriedEmbedder - reproducing a committed number requires
reproducing its embedding call shape, not only its query text (DX-001).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from episodic._selection import (
    ClusterDiversitySelector,
    deterministic_clusters,
    select,
    vector,
)

from src.analysis.e005_diversity_selection import (
    BUDGET_CHARS,
    COMPONENT_ROOT,
    PRIMARY_POOL,
    Q11_TURN,
    EmbeddingCache,
    committed_targeted_items,
    load_candidates,
    load_queries,
    q11_availability,
    targeted_availability,
)
from src.retrieval_bakeoff.embedding import CarriedEmbedder
from src.retrieval_mechanism_ledger.e005 import eligible_candidates

PRIMARY_CONFIGURATION = "A3_l0.1_r0.0_k16"
E005_RAW = COMPONENT_ROOT / "artifacts" / "e005" / "raw"
OUTPUT = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "library_extraction"
    / "artifacts"
    / "cc002"
    / "t3_e005_replay.json"
)

EXPECTED_PRIMARY = {
    "q11_fact_count": 12,
    "q11_domain_count": 4,
    "targeted_preserved": 16,
    "serialized_chars": 31_569,
}


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _library_selector(parameters: dict, assignments) -> ClusterDiversitySelector:
    return ClusterDiversitySelector(
        lambda_=float(parameters["lambda"]),
        cost_exponent=float(parameters["r"]),
        assignments=assignments,
        cluster_count=int(parameters["k"]),
    )


def main() -> None:
    for symbol in (ClusterDiversitySelector, select, deterministic_clusters):
        module = getattr(symbol, "__module__", "")
        if not module.startswith("episodic."):
            raise AssertionError(f"{symbol.__name__} is not the library's")

    embedder = CarriedEmbedder()
    embedder.assert_carried_model()
    cache = EmbeddingCache(embedder)
    queries = load_queries()
    cache.prime(queries.values())

    candidates = load_candidates()
    by_id = {str(candidate["id"]): candidate for candidate in candidates}

    committed_q11 = [
        record
        for record in _read_jsonl(E005_RAW / "q11_selection.jsonl")
        if record["pool"] == PRIMARY_POOL and record["arm"] == "A3"
    ]
    q11_pool = eligible_candidates(candidates, probe_turn=Q11_TURN)
    q11_embedding = vector(cache(queries[Q11_TURN]))
    assignments = {
        int(k): deterministic_clusters(q11_pool, int(k))
        for k in sorted({int(record["parameters"]["k"]) for record in committed_q11})
    }

    mismatches: list[str] = []
    for record in committed_q11:
        result = select(
            candidates=q11_pool,
            query_embedding=q11_embedding,
            selector=_library_selector(
                record["parameters"],
                assignments[int(record["parameters"]["k"])],
            ),
            budget_chars=BUDGET_CHARS,
        )
        if (
            result.payload_sha256 != record["payload_sha256"]
            or result.serialized_chars != int(record["serialized_chars"])
            or list(result.selected_ids) != list(record["selected_ids"])
        ):
            mismatches.append(str(record["configuration_id"]))

    committed_targeted = [
        record
        for record in _read_jsonl(E005_RAW / "targeted_selection.jsonl")
        if record["configuration_id"] == PRIMARY_CONFIGURATION
    ]
    replayed_targeted: list[dict] = []
    for record in sorted(committed_targeted, key=lambda row: int(row["probe_turn"])):
        turn = int(record["probe_turn"])
        pool = eligible_candidates(candidates, probe_turn=turn)
        result = select(
            candidates=pool,
            query_embedding=vector(cache(queries[turn])),
            selector=_library_selector(
                record["parameters"],
                deterministic_clusters(pool, int(record["parameters"]["k"])),
            ),
            budget_chars=BUDGET_CHARS,
        )
        if result.payload_sha256 != record["payload_sha256"]:
            mismatches.append(f"{PRIMARY_CONFIGURATION}@targeted_{turn}")
        replayed_targeted.append(
            {
                "configuration_id": PRIMARY_CONFIGURATION,
                "probe_turn": turn,
                "selected_ids": list(result.selected_ids),
                "payload_sha256": result.payload_sha256,
                "serialized_chars": result.serialized_chars,
            }
        )

    primary_record = next(
        record
        for record in committed_q11
        if record["configuration_id"] == PRIMARY_CONFIGURATION
    )
    primary_metric = q11_availability(primary_record, by_id)
    targeted_metrics = targeted_availability(replayed_targeted, by_id)
    preserved = targeted_metrics[PRIMARY_CONFIGURATION]["preserved_count"]
    required = sum(
        row["committed_available"] for row in committed_targeted_items()
    )

    measured_primary = {
        "q11_fact_count": primary_metric["fact_count"],
        "q11_domain_count": primary_metric["domain_count"],
        "targeted_preserved": preserved,
        "serialized_chars": int(primary_record["serialized_chars"]),
    }
    vector_match = measured_primary == EXPECTED_PRIMARY and required == 16

    status = "PASS" if not mismatches and vector_match else "FAIL"
    payload = {
        "test": "CC-002 T3",
        "status": status,
        "selection_module": select.__module__,
        "selector_module": ClusterDiversitySelector.__module__,
        "embedding_call_shape": "committed batch via CarriedEmbedder.embed_many",
        "a3_configurations_replayed": len(committed_q11),
        "targeted_selections_replayed": len(committed_targeted),
        "payload_sha256_mismatches": mismatches,
        "primary_configuration": PRIMARY_CONFIGURATION,
        "primary_result_vector": measured_primary,
        "expected_result_vector": EXPECTED_PRIMARY,
        "targeted_required": required,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

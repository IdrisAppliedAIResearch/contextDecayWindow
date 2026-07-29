from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path

import numpy as np

from src.analysis.rendering_expansion_replay import (
    BAKEOFF_RUN,
    REPO_ROOT,
    STUDY_010_RUN,
    _read_only_connection,
    _sha256,
)
from src.analysis.study_008_replay import (
    PROBE_TURNS,
    STUDY_007_RUN,
    load_candidates as load_study_007_candidates,
    load_fact_rows,
    match_facts,
    probe_queries as study_007_probe_queries,
    stm_block_ids,
)
from src.embeddings.provider import cosine_similarity
from src.memory.arbitration import arbitrate_budgeted
from src.memory.context_builder import render_ltm_block
from src.memory.distilled_ltm_store import get_distilled_retrieval_rows
from src.memory.retrieval_budget import rendered_text
from src.retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256
from src.retrieval_bakeoff.embedding import CarriedEmbedder


B_SWEEP = (16_000, 20_000, 24_000, 28_000, 32_000, 36_000, 40_000, 48_000, 64_000)
REGISTERED_B_LTM = 32_000
REGISTERED_K_MIN = 1
AMENDMENT_COMMIT = "2d453cbe"
IMPLEMENTATION_COMMIT = "202b1883"
POST_FIX_GATE_COMMIT = "20227d59"


def generate_rederivation(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    embedding_path = Path(os.environ["CDW_EMBEDDING_MODEL_PATH"]).resolve()
    embedding_sha = _sha256(embedding_path)
    if embedding_sha != CARRIED_EMBEDDING_SHA256:
        raise AssertionError(
            f"Carried embedding SHA mismatch: {embedding_sha}"
        )
    embedder = CarriedEmbedder(embedding_path)
    embedder.assert_carried_model()

    source_paths = _source_paths()
    before = _hash_paths(source_paths)
    study_007 = _study_007_frontier(embedder)
    study_010 = _study_010_frontier(embedder)
    n_cap = _n_cap_check()
    containment = _containment_check()
    after = _hash_paths(source_paths)
    sources_unchanged = before == after

    result = {
        "record": "DR-001",
        "phase": "downstream_rederivation",
        "amendment_commit": AMENDMENT_COMMIT,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "post_fix_gate_commit": POST_FIX_GATE_COMMIT,
        "registered_b_ltm": REGISTERED_B_LTM,
        "registered_k_min": REGISTERED_K_MIN,
        "registered_budget_sweep": list(B_SWEEP),
        "embedding": {
            "path": str(embedding_path),
            "sha256": embedding_sha,
            "carried_sha256": CARRIED_EMBEDDING_SHA256,
            "provider": "CarriedEmbedder",
            "n_threads": 1,
            "generative_calls": 0,
        },
        "source_integrity": {
            "status": "PASS" if sources_unchanged else "FAIL",
            "file_count": len(source_paths),
            "tree_sha256_before": _digest_mapping(before),
            "tree_sha256_after": _digest_mapping(after),
        },
        "b_ltm": {
            "action": "KEEP",
            "value": REGISTERED_B_LTM,
            "rationale": (
                "DR-001 locks the existing context allocation; reducing it "
                "requires a separately authorized design."
            ),
            "study_007_frontier": study_007,
            "study_010_frontier": study_010,
        },
        "n_candidate_cap": n_cap,
        "packing_order": {
            "action": "FLAG_ONLY",
            "value": "N-first",
            "q4_post_fix_packing_opened": False,
            "reason": "AS-001 decision rule is not yet committed.",
        },
        "per_domain_floor": {
            "action": "KEEP",
            "value": REGISTERED_K_MIN,
            "locked_budget_status": (
                "PASS"
                if all(
                    row["floor_protected"]
                    for row in study_007
                    if row["b_ltm"] == REGISTERED_B_LTM
                )
                else "FAIL"
            ),
        },
        "containment_dedup": containment,
    }
    statuses = [
        result["source_integrity"]["status"],
        result["per_domain_floor"]["locked_budget_status"],
        containment["status"],
        n_cap["status"],
    ]
    result["status"] = "PASS" if all(item == "PASS" for item in statuses) else "FAIL"
    _write_json(output_dir / "rederivation.json", result)
    (output_dir / "rederivation_report.md").write_text(
        _report(result),
        encoding="utf-8",
        newline="\n",
    )
    return result


def _study_007_frontier(embedder: CarriedEmbedder) -> list[dict]:
    candidates = load_study_007_candidates()
    fact_rows = load_fact_rows()
    queries = study_007_probe_queries()
    query_vectors = {
        turn: embedder(queries[turn])
        for turn in PROBE_TURNS
    }
    scored = {
        turn: _score_candidates(candidates, query_vectors[turn])
        for turn in PROBE_TURNS
    }
    rows = []
    for budget in B_SWEEP:
        for turn in PROBE_TURNS:
            arbitration = arbitrate_budgeted(
                stm_candidates=[],
                ltm_candidates=scored[turn],
                stm_block_episode_ids=stm_block_ids(turn),
                ltm_budget=budget,
                ltm_k_min=REGISTERED_K_MIN,
            )
            selection = arbitration.budget
            text = "\n".join(
                rendered_text(candidate) for candidate in selection.selected
            )
            matched = match_facts(text, fact_rows)
            rows.append(
                {
                    "b_ltm": budget,
                    "turn": turn,
                    "records": len(selection.selected),
                    "serialized_chars": selection.chars_used,
                    "content_chars": sum(
                        len(rendered_text(candidate))
                        for candidate in selection.selected
                    ),
                    "block_overhead_chars": selection.block_overhead_chars,
                    "floor_per_topic": selection.floor_per_topic,
                    "floor_protected": all(
                        selection.floor_per_topic.get(topic, 0)
                        >= REGISTERED_K_MIN
                        for topic in selection.topics_present
                    ),
                    "topics_present": selection.topics_present,
                    "matched_facts": matched,
                    "domains_with_facts": sorted(
                        domain for domain, facts in matched.items() if facts
                    ),
                    "containment_drops": arbitration.containment_drops,
                    "query_sha256": _text_sha256(queries[turn]),
                    "query_vector_sha256": _vector_sha256(
                        query_vectors[turn]
                    ),
                }
            )
    return rows


def _study_010_frontier(embedder: CarriedEmbedder) -> list[dict]:
    connection = _read_only_connection(STUDY_010_RUN / "study.db")
    try:
        candidates = get_distilled_retrieval_rows(connection)
    finally:
        connection.close()
    script = json.loads(
        (
            REPO_ROOT / "experiments" / "study_010" / "script_1000.json"
        ).read_text(encoding="utf-8")
    )
    queries = {
        int(row["turn"]): str(row["user"])
        for row in script["turns"]
        if int(row["turn"]) in (999, 1000)
    }
    query_vectors = {
        turn: embedder(queries[turn]) for turn in (999, 1000)
    }
    retrieval_rows = {
        int(row["turn_number"]): row
        for row in (
            json.loads(line)
            for line in (
                STUDY_010_RUN / "logs" / "retrieval.jsonl"
            ).read_text(encoding="utf-8").splitlines()
        )
        if int(row["turn_number"]) in (999, 1000)
    }
    rows = []
    for budget in B_SWEEP:
        for turn in (999, 1000):
            scored = _score_candidates(candidates, query_vectors[turn])
            excluded = {
                str(episode["id"])
                for key in ("n_episodes", "k_episodes")
                for episode in retrieval_rows[turn].get(key, [])
            }
            arbitration = arbitrate_budgeted(
                stm_candidates=[],
                ltm_candidates=scored,
                stm_block_episode_ids=excluded,
                ltm_budget=budget,
                ltm_k_min=REGISTERED_K_MIN,
            )
            selection = arbitration.budget
            block = render_ltm_block(arbitration.episodes)
            if len(block) != selection.chars_used:
                raise AssertionError(
                    "Selection accounting differs from rendered block"
                )
            rows.append(
                {
                    "b_ltm": budget,
                    "turn": turn,
                    "records": len(selection.selected),
                    "serialized_chars": selection.chars_used,
                    "content_chars": sum(
                        len(rendered_text(candidate))
                        for candidate in selection.selected
                    ),
                    "block_overhead_chars": selection.block_overhead_chars,
                    "floor_per_topic": selection.floor_per_topic,
                    "floor_protected": all(
                        selection.floor_per_topic.get(topic, 0)
                        >= REGISTERED_K_MIN
                        for topic in selection.topics_present
                    ),
                    "containment_drops": arbitration.containment_drops,
                    "selected_episode_ids": [
                        str(candidate["id"])
                        for candidate in selection.selected
                    ],
                    "query_sha256": _text_sha256(queries[turn]),
                    "query_vector_sha256": _vector_sha256(
                        query_vectors[turn]
                    ),
                }
            )
    return rows


def _n_cap_check() -> dict:
    row = next(
        json.loads(line)
        for line in (
            BAKEOFF_RUN / "logs" / "context_match.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        if int(json.loads(line)["turn_number"]) == 115
    )
    connection = sqlite3.connect(
        f"file:{(BAKEOFF_RUN / 'study.db').as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    try:
        turn_55_id = str(
            connection.execute(
                "SELECT id FROM episodes WHERE turn_number = 55"
            ).fetchone()[0]
        )
    finally:
        connection.close()
    rank = row["n_candidate_ids"].index(turn_55_id) + 1
    return {
        "status": "PASS" if rank == 27 and rank <= 32 else "FAIL",
        "action": "KEEP",
        "value": 32,
        "turn_55_rank": rank,
        "turn_55_within_cap": rank <= 32,
        "post_fix_packing_opened": False,
    }


def _containment_check() -> dict:
    candidates = [
        {
            "id": "duplicate",
            "distilled_id": "d-duplicate",
            "topic_id": "topic",
            "topic_label": "topic",
            "similarity": 0.9,
            "user_message": "duplicate",
            "assistant_message": "content",
            "turn_number": 1,
        },
        {
            "id": "replacement",
            "distilled_id": "d-replacement",
            "topic_id": "topic",
            "topic_label": "topic",
            "similarity": 0.8,
            "user_message": "replacement",
            "assistant_message": "content",
            "turn_number": 2,
        },
    ]
    result = arbitrate_budgeted(
        stm_candidates=[],
        ltm_candidates=candidates,
        stm_block_episode_ids={"duplicate"},
        ltm_budget=16_000,
        ltm_k_min=1,
    )
    selected = [str(candidate["id"]) for candidate in result.budget.selected]
    status = (
        "PASS"
        if selected == ["replacement"] and result.containment_drops == 1
        else "FAIL"
    )
    return {
        "status": status,
        "action": "KEEP",
        "authority": "source episode identity",
        "selected_episode_ids": selected,
        "containment_drops": result.containment_drops,
    }


def _score_candidates(
    candidates: list[dict],
    query_vector: np.ndarray,
) -> list[dict]:
    scored = []
    for candidate in candidates:
        embedding = np.frombuffer(candidate["embedding"], dtype=np.float32)
        scored.append(
            {
                **candidate,
                "similarity": cosine_similarity(query_vector, embedding),
            }
        )
    scored.sort(key=lambda item: (-float(item["similarity"]), str(item["id"])))
    return scored


def _source_paths() -> list[Path]:
    return [
        STUDY_007_RUN / "study.db",
        STUDY_007_RUN / "logs" / "retrieval.jsonl",
        REPO_ROOT / "experiments" / "study_005" / "script.json",
        REPO_ROOT / "experiments" / "study_007" / "q_facts_key.md",
        STUDY_010_RUN / "study.db",
        STUDY_010_RUN / "logs" / "retrieval.jsonl",
        REPO_ROOT / "experiments" / "study_010" / "script_1000.json",
        BAKEOFF_RUN / "study.db",
        BAKEOFF_RUN / "logs" / "context_match.jsonl",
    ]


def _hash_paths(paths: list[Path]) -> dict[str, str]:
    return {
        str(path.relative_to(REPO_ROOT)): _sha256(path)
        for path in sorted(paths)
    }


def _digest_mapping(mapping: dict[str, str]) -> str:
    payload = "".join(
        f"{path}\0{digest}\n" for path, digest in sorted(mapping.items())
    )
    return _text_sha256(payload)


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _vector_sha256(vector: np.ndarray) -> str:
    return hashlib.sha256(
        np.asarray(vector, dtype=np.float32).tobytes()
    ).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _report(result: dict) -> str:
    locked_007 = [
        row
        for row in result["b_ltm"]["study_007_frontier"]
        if row["b_ltm"] == REGISTERED_B_LTM
    ]
    locked_010 = [
        row
        for row in result["b_ltm"]["study_010_frontier"]
        if row["b_ltm"] == REGISTERED_B_LTM
    ]
    lines = [
        "# DR-001 Downstream Re-Derivation",
        "",
        f"**Status:** **{result['status']}**  ",
        f"**Embedding SHA-256:** `{result['embedding']['sha256']}`  ",
        "**Generative calls:** `0`",
        "",
        "## Decisions",
        "",
        "- `B_ltm`: KEEP at 32,000 characters. The existing allocation is "
        "not tuned from post-fix outcomes.",
        "- N cap: KEEP at 32. The Q4 turn-55 episode remains rank 27 and "
        "inside the cap; post-fix Q4 packing was not opened.",
        "- N-first packing: FLAG ONLY for AS-001.",
        "- Per-domain floor: KEEP at `k_min = 1`; every topic retains its "
        "floor at the locked budget.",
        "- Containment dedup: KEEP; source-episode identity remains the "
        "authority and the synthetic invariant passes.",
        "",
        "## Locked Budget",
        "",
        "| Corpus | Turn | Records | Serialized chars | Content chars | "
        "Floor protected |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for corpus, rows in (("Study 007", locked_007), ("Study 010", locked_010)):
        for row in rows:
            lines.append(
                f"| {corpus} | {row['turn']} | {row['records']} | "
                f"{row['serialized_chars']} | {row['content_chars']} | "
                f"{'PASS' if row['floor_protected'] else 'FAIL'} |"
            )
    lines.extend(
        [
            "",
            "The complete 16k-64k frontier, selected identities, fact "
            "coverage, query hashes, and vector hashes are in "
            "`rederivation.json`.",
            "",
        ]
    )
    return "\n".join(lines)


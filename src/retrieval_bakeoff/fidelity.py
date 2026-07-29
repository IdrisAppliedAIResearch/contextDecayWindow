from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path

import numpy as np

from src.embeddings.provider import cosine_similarity
from src.memory.arbitration import arbitrate_budgeted
from src.memory.context_builder import render_ltm_block
from src.memory.distilled_ltm_store import get_distilled_retrieval_rows

from .config import REPO_ROOT
from .embedding import CarriedEmbedder


STUDY_007_RUN = (
    REPO_ROOT
    / "experiments"
    / "study_007"
    / "runs"
    / "study_007_full_001"
    / "condition_c"
)
SCRIPT_PATH = REPO_ROOT / "experiments" / "study_005" / "script.json"
PROBE_TURNS = (120, 121)


def run_fidelity_check(embedder: CarriedEmbedder | None = None) -> dict:
    provider = embedder or CarriedEmbedder()
    before = hash_tree(STUDY_007_RUN)
    candidates = _load_candidates()
    queries = _probe_queries()
    probes = []
    for turn in PROBE_TURNS:
        scored = _score_candidates(candidates, provider(queries[turn]))
        arbitration = arbitrate_budgeted(
            stm_candidates=[],
            ltm_candidates=scored,
            stm_block_episode_ids=_stm_block_ids(turn),
            ltm_budget=32_000,
            ltm_k_min=1,
        )
        replayed = render_ltm_block(arbitration.episodes)
        actual = _actual_block(turn)
        probes.append(
            {
                "turn": turn,
                "status": "PASS" if replayed == actual else "FAIL",
                "replayed_characters": len(replayed),
                "actual_characters": len(actual),
                "replayed_sha256": _text_sha(replayed),
                "actual_sha256": _text_sha(actual),
                "first_difference": _first_difference(replayed, actual),
                "selected_source_episode_ids": [
                    str(candidate["id"])
                    for candidate in arbitration.budget.selected
                ],
                "selected_source_turns": [
                    int(candidate["turn_number"])
                    for candidate in arbitration.budget.selected
                ],
                "containment_drops": arbitration.containment_drops,
            }
        )
    after = hash_tree(STUDY_007_RUN)
    changed = sorted(
        path
        for path in before.keys() | after.keys()
        if before.get(path) != after.get(path)
    )
    status = (
        "PASS"
        if all(probe["status"] == "PASS" for probe in probes) and not changed
        else "FAIL"
    )
    return {
        "test_id": "T0.3",
        "status": status,
        "historical_run": str(STUDY_007_RUN.relative_to(REPO_ROOT)),
        "script": str(SCRIPT_PATH.relative_to(REPO_ROOT)),
        "script_sha256": hashlib.sha256(SCRIPT_PATH.read_bytes()).hexdigest(),
        "model_path": str(provider.model_path),
        "model_sha256": provider.model_sha256,
        "parameters": {
            "ltm_budget": 32_000,
            "ltm_k_min": 1,
            "floor_ranking": "similarity",
            "render_mode": "episode",
        },
        "source_file_count": len(before),
        "source_tree_sha256_before": _tree_digest(before),
        "source_tree_sha256_after": _tree_digest(after),
        "changed_source_files": changed,
        "probes": probes,
    }


def hash_tree(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def extract_ltm_block(prompt: str) -> str:
    match = re.search(
        r"<retrieved_ltm(?:>.*?</retrieved_ltm>|/>)",
        prompt,
        flags=re.DOTALL,
    )
    if match is None:
        raise ValueError("Constructed prompt has no retrieved_ltm block")
    return match.group(0)


def _load_candidates() -> list[dict]:
    database = STUDY_007_RUN / "study.db"
    connection = sqlite3.connect(
        f"file:{database.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    try:
        return get_distilled_retrieval_rows(connection)
    finally:
        connection.close()


def _probe_queries() -> dict[int, str]:
    payload = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    return {
        int(row["turn"]): str(row["user"])
        for row in payload["turns"]
        if int(row["turn"]) in PROBE_TURNS
    }


def _score_candidates(
    candidates: list[dict],
    query_embedding: np.ndarray,
) -> list[dict]:
    scored = []
    for candidate in candidates:
        embedding = np.frombuffer(candidate["embedding"], dtype=np.float32)
        scored.append(
            {
                **candidate,
                "similarity": cosine_similarity(query_embedding, embedding),
            }
        )
    scored.sort(key=lambda row: (-float(row["similarity"]), str(row["id"])))
    return scored


def _stm_block_ids(turn: int) -> set[str]:
    path = STUDY_007_RUN / "logs" / "retrieval.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if int(row.get("turn_number", -1)) != turn:
            continue
        return {
            str(episode["id"])
            for name in ("n_episodes", "k_episodes")
            for episode in row.get(name, [])
        }
    raise AssertionError(f"No historical retrieval row for turn {turn}")


def _actual_block(turn: int) -> str:
    path = STUDY_007_RUN / "constructed_prompts" / f"turn_{turn:03d}.txt"
    return extract_ltm_block(path.read_text(encoding="utf-8"))


def _text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tree_digest(digests: dict[str, str]) -> str:
    payload = "".join(f"{path}\0{digest}\n" for path, digest in sorted(digests.items()))
    return _text_sha(payload)


def _first_difference(left: str, right: str) -> int | None:
    if left == right:
        return None
    for index, (left_character, right_character) in enumerate(
        zip(left, right, strict=False)
    ):
        if left_character != right_character:
            return index
    return min(len(left), len(right))

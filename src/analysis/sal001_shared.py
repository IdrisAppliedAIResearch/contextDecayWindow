from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "biological_memory"
    / "sal_001"
)
DESIGN = STUDY_ROOT / "SAL_001_PRE_REGISTRATION.md"
EXPLORATION = STUDY_ROOT / "exploration" / "SAL_001_PART1_EXPLORATION.json"
ARTIFACT_ROOT = STUDY_ROOT / "artifacts"
DEFAULT_MODEL_PATH = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--unsloth--Qwen3.6-27B-MTP-GGUF"
    / "snapshots"
    / "5cb35eb3dcbf52dbce5f87dbc64df6aaffadcace"
    / "Qwen3.6-27B-UD-Q6_K_XL.gguf"
)

DATASET_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
DATASET_BYTES = 277_383_467
MODEL_SHA256 = "f3b4a622e06e8ade06ec5c0eb9b40ed7c9bd707b5fada46c0215f4ab4a6bc32b"
MODEL_BYTES = 26_015_429_760
SEED = 5005
STRATA = (
    "single-session-user",
    "single-session-assistant",
    "single-session-preference",
    "temporal-reasoning",
    "knowledge-update",
    "multi-session",
)
HOLDOUT_START = 20  # Zero-based: registered ranks 21-30.
HOLDOUT_STOP = 30
EXPECTED_SELECTION_DIGEST = (
    "fc592afdb7c37dbb34223335e526bd3dabf14c36728d546bdacb2fda09610c36"
)
EXPECTED_COUNTS = {
    "selected_items": 60,
    "named_evidence_sessions": 95,
    "named_sessions_without_marker": 1,
    "irregular_named_sessions": 1,
    "eligible_sessions": 93,
    "eligible_exchanges": 545,
    "evidence_exchanges": 98,
    "unmarked_exchanges": 447,
    "evidence_with_any_neighbor": 97,
    "evidence_with_prior": 49,
    "evidence_with_next": 91,
    "evidence_with_both": 43,
    "auc_sessions": 92,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def write_json(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_identity(path: Path) -> dict[str, Any]:
    try:
        display_path = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        display_path = str(path.resolve())
    return {
        "path": display_path,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def session_content_sha256(messages: list[dict[str, str]]) -> str:
    pairs = [[message["role"], message["content"]] for message in messages]
    return canonical_digest(pairs)


def exchange_content_sha256(user: str, assistant: str) -> str:
    return canonical_digest([["user", user], ["assistant", assistant]])


def selection_sort_key(stratum: str, question_id: str) -> str:
    material = f"{SEED}\0{stratum}\0{question_id}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def ordered_selection_digest(question_ids: list[str]) -> str:
    return hashlib.sha256("\n".join(question_ids).encode("utf-8")).hexdigest()

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.retrieval_bakeoff.config import REPO_ROOT, SURVEY_ROOT
from src.retrieval_bakeoff.embedding import CarriedEmbedder
from src.retrieval_bakeoff.leakage import (
    assert_planted_violations,
    audit_import_graph,
)
from src.retrieval_bakeoff.tier6 import calibrate_context_match
from src.study.script_loader import script_digest


REGISTRATION_ANCHOR = "b60b7084741eb5d30298261076b4bca78abe713a"
CORPUS_ORDER_ANCHOR = "96cdb776"
CALIBRATION_PROTOCOL_ANCHOR = "032af39d"
SCRIPT_DIGEST = (
    "d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01"
)
ARM_L_PROMPTS = (
    REPO_ROOT
    / "experiments"
    / "study_007"
    / "runs"
    / "study_007_full_001"
    / "condition_c"
    / "constructed_prompts"
)
ARM_S_DATABASE = (
    REPO_ROOT
    / "experiments"
    / "study_009"
    / "runs"
    / "study_009_full_001"
    / "arm_s"
    / "study.db"
)
SCRIPT_PATH = REPO_ROOT / "experiments" / "study_005" / "script.json"
OUTPUT_PATH = (
    SURVEY_ROOT / "settings" / "tier6_context_match_settings.json"
)
MECHANISM_ENTRY = (
    REPO_ROOT / "src" / "memory" / "context_matched_stm.py"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding-model", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _assert_ready()
    source_paths = [
        ARM_S_DATABASE,
        SCRIPT_PATH,
        *(
            ARM_L_PROMPTS / f"turn_{turn:03d}.txt"
            for turn in range(92, 112)
        ),
    ]
    source_hashes_before = _hash_files(source_paths)
    embedder = CarriedEmbedder(args.embedding_model)
    embedder.assert_carried_model()
    embedder.warmup()

    static_audit = audit_import_graph([MECHANISM_ENTRY])
    with tempfile.TemporaryDirectory(prefix="tier6-leakage-") as temp:
        planted_audit = assert_planted_violations(Path(temp))
    calibration = calibrate_context_match(
        arm_l_prompt_root=ARM_L_PROMPTS,
        arm_s_database=ARM_S_DATABASE,
        script_path=SCRIPT_PATH,
        embedder=embedder,
    )
    source_hashes_after = _hash_files(source_paths)
    if source_hashes_before != source_hashes_after:
        raise RuntimeError("Tier 6 calibration changed a source artifact")
    if calibration["selected"]["match_gate_status"] != "PASS":
        raise RuntimeError("Tier 6 context-match calibration gate failed")

    payload = {
        **calibration,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "registration_anchor": REGISTRATION_ANCHOR,
        "corpus_order_anchor": CORPUS_ORDER_ANCHOR,
        "calibration_protocol_anchor": CALIBRATION_PROTOCOL_ANCHOR,
        "code_commit": _git("rev-parse", "HEAD"),
        "script_path": str(SCRIPT_PATH.relative_to(REPO_ROOT)),
        "script_sha256_post_decode_lf": SCRIPT_DIGEST,
        "arm_l_prompt_root": str(ARM_L_PROMPTS.relative_to(REPO_ROOT)),
        "arm_s_database": str(ARM_S_DATABASE.relative_to(REPO_ROOT)),
        "embedding_model_path": str(embedder.model_path),
        "embedding_model_sha256": embedder.model_sha256,
        "source_hashes_before": source_hashes_before,
        "source_hashes_after": source_hashes_after,
        "static_leakage_audit": static_audit,
        "planted_leakage_audit": planted_audit,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected": payload["selected"],
                "output": str(OUTPUT_PATH.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )
    return 0


def _assert_ready() -> None:
    if _git("status", "--porcelain"):
        raise RuntimeError("Tier 6 calibration requires a clean worktree")
    if _git("branch", "--show-current") != "retrieval-bakeoff":
        raise RuntimeError("Tier 6 calibration requires retrieval-bakeoff")
    for anchor in (
        REGISTRATION_ANCHOR,
        CORPUS_ORDER_ANCHOR,
        CALIBRATION_PROTOCOL_ANCHOR,
    ):
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", anchor, "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    if OUTPUT_PATH.exists():
        raise RuntimeError(f"Refusing to overwrite locked settings: {OUTPUT_PATH}")
    if script_digest(SCRIPT_PATH.read_text(encoding="utf-8")) != SCRIPT_DIGEST:
        raise RuntimeError("Study 009 script digest changed")


def _hash_files(paths: list[Path]) -> dict[str, str]:
    result = {}
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        result[str(path.relative_to(REPO_ROOT))] = digest.hexdigest()
    return result


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())

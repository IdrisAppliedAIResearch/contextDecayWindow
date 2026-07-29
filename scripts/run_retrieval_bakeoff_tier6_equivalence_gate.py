from __future__ import annotations

import argparse
import csv
import json
import subprocess
import tempfile
from pathlib import Path

from src.retrieval_bakeoff.config import REPO_ROOT, SURVEY_ROOT
from src.retrieval_bakeoff.embedding import CarriedEmbedder
from src.retrieval_bakeoff.leakage import (
    assert_planted_violations,
    audit_import_graph,
)
from src.retrieval_bakeoff.tier6_equivalence import (
    MAX_REPLAY_TURN,
    embed_script_turns,
    load_script_turns,
    run_equivalence_replay,
    sha256_file,
)


AMENDMENT_ANCHOR = "39ba9175"
SOURCE_DATABASE = (
    REPO_ROOT
    / "experiments/study_009/runs/study_009_full_001/arm_s/study.db"
)
SCRIPT_PATH = REPO_ROOT / "experiments/study_005/script.json"
SETTINGS_PATH = (
    SURVEY_ROOT / "settings/tier6_context_match_settings.json"
)
CORRECTED_LOCK_PATH = (
    SURVEY_ROOT / "settings/tier6_corrected_121_settings_lock.json"
)
ENGINE_PATH = REPO_ROOT / "src/memory/context_matched_stm.py"
OUTPUT_ROOT = SURVEY_ROOT / "tier6/equivalence_gate_corrected"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding-model", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    code_commit = require_ready()
    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    corrected_lock = json.loads(
        CORRECTED_LOCK_PATH.read_text(encoding="utf-8")
    )
    source_hashes_before = locked_source_hashes()

    embedder = CarriedEmbedder(args.embedding_model)
    embedder.assert_carried_model()
    embedder.warmup()
    script_turns = load_script_turns(
        SCRIPT_PATH,
        max_turn=MAX_REPLAY_TURN,
    )
    query_vectors = embed_script_turns(
        script_turns=script_turns,
        embedder=embedder,
    )
    with tempfile.TemporaryDirectory(
        prefix="tier6-equivalence-",
    ) as temporary:
        replay = run_equivalence_replay(
            source_database=SOURCE_DATABASE,
            script_path=SCRIPT_PATH,
            query_vectors=query_vectors,
            settings=settings,
            production_database=Path(temporary) / "production.db",
        )
        planted = assert_planted_violations(Path(temporary))

    source_hashes_after = locked_source_hashes()
    sources_unchanged = source_hashes_before == source_hashes_after
    static_audit = audit_import_graph([ENGINE_PATH])
    overall_status = (
        "PASS"
        if replay["status"] == "PASS"
        and sources_unchanged
        and static_audit["status"] == "PASS"
        and planted["status"] == "PASS"
        else "FAIL"
    )
    payload = {
        **replay,
        "status": overall_status,
        "amendment_anchor": AMENDMENT_ANCHOR,
        "code_commit": code_commit,
        "implementation_commit": corrected_lock[
            "implementation_commit"
        ],
        "corrected_settings_lock": str(
            CORRECTED_LOCK_PATH.relative_to(REPO_ROOT)
        ).replace("\\", "/"),
        "corrected_settings_lock_sha256": sha256_file(
            CORRECTED_LOCK_PATH
        ),
        "original_settings_path": str(
            SETTINGS_PATH.relative_to(REPO_ROOT)
        ).replace("\\", "/"),
        "original_settings_sha256": sha256_file(SETTINGS_PATH),
        "embedding_model_path": str(embedder.model_path),
        "embedding_model_sha256": embedder.model_sha256,
        "source_hashes_before": source_hashes_before,
        "source_hashes_after": source_hashes_after,
        "sources_unchanged": sources_unchanged,
        "static_leakage_audit": static_audit,
        "planted_leakage_audit": planted,
    }
    OUTPUT_ROOT.mkdir(parents=True)
    write_json(OUTPUT_ROOT / "equivalence_gate.json", payload)
    write_trace(OUTPUT_ROOT / "turn_equivalence.csv", payload)
    (OUTPUT_ROOT / "equivalence_report.md").write_text(
        render_report(payload),
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": overall_status,
                "turn_count": replay["turn_count"],
                "settings_reproduction": replay[
                    "settings_reproduction"
                ]["status"],
                "output_root": str(
                    OUTPUT_ROOT.relative_to(REPO_ROOT)
                ),
            },
            indent=2,
        )
    )
    if overall_status != "PASS":
        raise RuntimeError("Corrected Tier 6 equivalence gate failed")
    return 0


def require_ready() -> str:
    if git("status", "--porcelain"):
        raise RuntimeError(
            "Equivalence gate requires a clean committed worktree"
        )
    if git("branch", "--show-current") != "retrieval-bakeoff":
        raise RuntimeError("Equivalence gate requires retrieval-bakeoff")
    if OUTPUT_ROOT.exists():
        raise RuntimeError(f"Refusing to overwrite {OUTPUT_ROOT}")
    for path in (SETTINGS_PATH, CORRECTED_LOCK_PATH):
        if not path.is_file():
            raise FileNotFoundError(path)
        subprocess.run(
            [
                "git",
                "ls-files",
                "--error-unmatch",
                str(path.relative_to(REPO_ROOT)),
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    lock = json.loads(CORRECTED_LOCK_PATH.read_text(encoding="utf-8"))
    if lock["status"] != "LOCKED_BEFORE_CORRECTED_T6_ABLATION":
        raise RuntimeError("Corrected Tier 6 settings are not locked")
    if lock["amendment_anchor"] != AMENDMENT_ANCHOR:
        raise RuntimeError("Corrected settings use the wrong amendment")
    if lock["original_settings_sha256"] != sha256_file(SETTINGS_PATH):
        raise RuntimeError("Original Tier 6 settings hash changed")
    return git("rev-parse", "HEAD")


def locked_source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(REPO_ROOT)).replace("\\", "/"): sha256_file(path)
        for path in (
            SOURCE_DATABASE,
            SCRIPT_PATH,
            SETTINGS_PATH,
            CORRECTED_LOCK_PATH,
        )
    }


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_trace(path: Path, payload: dict) -> None:
    fields = [
        "turn_number",
        "status",
        "eligible_ids",
        "n_candidate_ids",
        "k_candidate_ids",
        "delivered_n_ids",
        "delivered_k_only_ids",
        "skipped_n_ids",
        "skipped_k_ids",
        "duplicate_ids",
        "payload_bytes",
        "payload_sha256",
        "payload_chars",
        "last_generation",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            lineterminator="\n",
        )
        writer.writeheader()
        for row in payload["turns"]:
            writer.writerow(
                {
                    "turn_number": row["turn_number"],
                    "status": row["status"],
                    **row["checks"],
                }
            )


def render_report(payload: dict) -> str:
    reproduction = payload["settings_reproduction"]
    return "\n".join(
        [
            "# Corrected Tier 6 Offline/Live Equivalence Gate",
            "",
            f"**Status:** **{payload['status']}**  ",
            f"**Code commit:** `{payload['code_commit']}`  ",
            f"**Turns replayed:** {payload['turn_count']}",
            "",
            "| Check | Result |",
            "|---|---|",
            f"| Minimal order fixture | {payload['order_fixture']['status']} |",
            f"| All 111 turn comparisons exact | {str(payload['all_turns_exact']).upper()} |",
            f"| Locked development vectors reproduced | {reproduction['status']} |",
            f"| Sources unchanged | {str(payload['sources_unchanged']).upper()} |",
            f"| Static leakage audit | {payload['static_leakage_audit']['status']} |",
            f"| Planted leakage rejection | {payload['planted_leakage_audit']['status']} |",
            "",
            "The production path used database-backed prior retrieval-event "
            "turns. The independent oracle used Amendment 007's explicit "
            "last-generation map. Ordered candidates, packed identities, "
            "payload bytes, and post-turn generation state matched on every "
            "turn.",
            "",
        ]
    )


def git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())

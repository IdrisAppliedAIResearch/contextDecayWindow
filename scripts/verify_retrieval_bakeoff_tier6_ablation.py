from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from src.memory.context_matched_stm import extract_stm_payload


REPO_ROOT = Path(__file__).resolve().parents[1]
SURVEY_ROOT = (
    REPO_ROOT / "experiments" / "surveys" / "retrieval_bakeoff"
)
TIER6_ROOT = SURVEY_ROOT / "tier6"
ABLATION_ROOT = TIER6_ROOT / "ablations"
SETTINGS_PATH = (
    SURVEY_ROOT / "settings" / "tier6_context_match_settings.json"
)
GATE_PATH = TIER6_ROOT / "ablation_gate.json"
REPORT_PATH = TIER6_ROOT / "ablation_report.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-a", required=True)
    parser.add_argument("--run-b", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.run_a == args.run_b:
        raise ValueError("Ablation reruns must have distinct run IDs")
    if GATE_PATH.exists() or REPORT_PATH.exists():
        raise RuntimeError("Refusing to overwrite Tier 6 ablation evidence")
    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    run_a = _load_run(args.run_a, settings)
    run_b = _load_run(args.run_b, settings)

    prompt_hashes_a = _prompt_hashes(run_a["output_dir"])
    prompt_hashes_b = _prompt_hashes(run_b["output_dir"])
    prompt_identity = prompt_hashes_a == prompt_hashes_b
    response_identity = (
        run_a["assistant_messages"] == run_b["assistant_messages"]
    )
    user_identity = run_a["user_messages"] == run_b["user_messages"]
    combined_prefix_sha256 = _combined_prefix_hash(
        run_a["output_dir"],
        run_a["assistant_messages"],
    )
    code_commits = [
        run_a["manifest"]["code_commit"],
        run_b["manifest"]["code_commit"],
    ]
    runtime_source_changes = _changed_paths(
        code_commits[0],
        code_commits[1],
        "src",
    )
    checks = {
        "distinct_run_ids": args.run_a != args.run_b,
        "manifest_status_complete": (
            run_a["manifest"]["status"] == "COMPLETE"
            and run_b["manifest"]["status"] == "COMPLETE"
        ),
        "same_runtime_source_tree": runtime_source_changes == [],
        "same_settings_sha256": (
            run_a["manifest"]["settings_sha256"]
            == run_b["manifest"]["settings_sha256"]
            == _sha256(SETTINGS_PATH)
        ),
        "fresh_server_per_valid_run": (
            run_a["manifest"]["server_pid"]
            != run_b["manifest"]["server_pid"]
        ),
        "same_server_build": (
            run_a["manifest"]["server_build_hash"]
            == run_b["manifest"]["server_build_hash"]
        ),
        "same_generation_model": (
            run_a["manifest"]["generation_model_sha256"]
            == run_b["manifest"]["generation_model_sha256"]
        ),
        "turn_count_35": (
            len(run_a["turn_rows"]) == len(run_b["turn_rows"]) == 35
        ),
        "prompt_count_35": (
            len(prompt_hashes_a) == len(prompt_hashes_b) == 35
        ),
        "byte_identical_prompts": prompt_identity,
        "byte_identical_user_messages": user_identity,
        "byte_identical_assistant_messages": response_identity,
        "complete_nontruncated_responses": (
            run_a["complete_nontruncated"]
            and run_b["complete_nontruncated"]
        ),
        "payload_accounting_exact": (
            run_a["payload_accounting_exact"]
            and run_b["payload_accounting_exact"]
        ),
        "payload_budget_respected": (
            run_a["payload_budget_respected"]
            and run_b["payload_budget_respected"]
        ),
        "runtime_import_boundary": (
            run_a["runtime_import_boundary"]
            and run_b["runtime_import_boundary"]
        ),
        "mechanism_sealed_before_review": (
            run_a["mechanism_sealed"] and run_b["mechanism_sealed"]
        ),
        "static_leakage_gate": (
            run_a["manifest"]["static_leakage_audit"]["status"] == "PASS"
            and run_b["manifest"]["static_leakage_audit"]["status"] == "PASS"
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    payload = {
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_ids": [args.run_a, args.run_b],
        "server_pids": [
            run_a["manifest"]["server_pid"],
            run_b["manifest"]["server_pid"],
        ],
        "code_commits": code_commits,
        "runtime_source_changes_between_runs": runtime_source_changes,
        "settings_path": str(SETTINGS_PATH.relative_to(REPO_ROOT)),
        "settings_sha256": _sha256(SETTINGS_PATH),
        "selected_settings": settings["selected"],
        "payload_budget": settings["payload_budget"],
        "checks": checks,
        "combined_seeded_prefix_sha256": combined_prefix_sha256,
        "prompt_sha256_by_turn": prompt_hashes_a,
        "run_summaries": {
            args.run_a: run_a["summary"],
            args.run_b: run_b["summary"],
        },
    }
    GATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_json(GATE_PATH, payload)
    REPORT_PATH.write_text(
        _report(payload),
        encoding="utf-8",
        newline="\n",
    )
    if status != "PASS":
        raise RuntimeError("Tier 6 ablation gate failed")
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


def _load_run(run_id: str, settings: dict) -> dict:
    manifest_path = ABLATION_ROOT / f"{run_id}_launch_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["phase"] != "ablation" or manifest["max_turns"] != 35:
        raise RuntimeError(f"{run_id} is not a registered 35-turn ablation")
    output_dir = (
        ABLATION_ROOT / run_id / "context_matched_stm"
    )
    turn_rows = _read_jsonl(output_dir / "logs" / "turns.jsonl")
    accounting_rows = _read_jsonl(
        output_dir / "logs" / "context_match.jsonl"
    )
    runtime_audit = json.loads(
        (output_dir / "runtime_audit.json").read_text(encoding="utf-8")
    )
    mechanism_seal = json.loads(
        (output_dir / "mechanism_seal.json").read_text(encoding="utf-8")
    )
    scoring_surface = json.loads(
        (output_dir / "scoring_surface.json").read_text(encoding="utf-8")
    )
    selected = settings["selected"]
    if manifest["selected_settings"]["n_cap"] != selected["n_cap"]:
        raise RuntimeError(f"{run_id} used the wrong N cap")
    if (
        manifest["selected_settings"]["k_threshold"]
        != selected["k_threshold"]
    ):
        raise RuntimeError(f"{run_id} used the wrong K threshold")

    accounting_by_turn = {
        int(row["turn_number"]): row for row in accounting_rows
    }
    payload_exact = len(accounting_rows) == 35
    payload_budget_respected = len(accounting_rows) == 35
    payload_chars = []
    for turn in range(1, 36):
        prompt_path = (
            output_dir / "constructed_prompts" / f"turn_{turn:03d}.txt"
        )
        prompt = prompt_path.read_text(encoding="utf-8")
        measured = len(extract_stm_payload(prompt))
        row = accounting_by_turn.get(turn)
        if row is None or measured != int(row["retrieval_payload_chars"]):
            payload_exact = False
            continue
        payload_chars.append(measured)
        if measured > int(settings["payload_budget"]):
            payload_budget_respected = False

    complete_nontruncated = (
        len(turn_rows) == 35
        and all(
            str(row.get("assistant_message") or "").strip()
            and int(row.get("output_tokens") or 0) < 2048
            for row in turn_rows
        )
    )
    return {
        "manifest": manifest,
        "output_dir": output_dir,
        "turn_rows": turn_rows,
        "assistant_messages": [
            str(row["assistant_message"]) for row in turn_rows
        ],
        "user_messages": [str(row["user_message"]) for row in turn_rows],
        "complete_nontruncated": complete_nontruncated,
        "payload_accounting_exact": payload_exact,
        "payload_budget_respected": payload_budget_respected,
        "runtime_import_boundary": (
            runtime_audit["forbidden_modules_loaded"] == []
        ),
        "mechanism_sealed": (
            mechanism_seal["status"] == "SEALED_BEFORE_SCORING"
        ),
        "summary": {
            "turn_count": len(turn_rows),
            "accounting_row_count": len(accounting_rows),
            "payload_char_minimum": min(payload_chars) if payload_chars else None,
            "payload_char_maximum": max(payload_chars) if payload_chars else None,
            "scoring_surface_status": scoring_surface[
                "completeness_status"
            ],
            "runtime_forbidden_modules": runtime_audit[
                "forbidden_modules_loaded"
            ],
        },
    }


def _prompt_hashes(output_dir: Path) -> dict[str, str]:
    paths = sorted((output_dir / "constructed_prompts").glob("turn_*.txt"))
    return {
        path.stem: _sha256(path)
        for path in paths
    }


def _combined_prefix_hash(
    output_dir: Path,
    assistant_messages: list[str],
) -> str:
    digest = hashlib.sha256()
    for turn, assistant_message in enumerate(assistant_messages, start=1):
        prompt_path = (
            output_dir / "constructed_prompts" / f"turn_{turn:03d}.txt"
        )
        digest.update(prompt_path.read_bytes())
        digest.update(b"\0")
        digest.update(assistant_message.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _changed_paths(
    commit_a: str,
    commit_b: str,
    pathspec: str,
) -> list[str]:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--no-renames",
            commit_a,
            commit_b,
            "--",
            pathspec,
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _report(payload: dict) -> str:
    lines = [
        "# Retrieval Bakeoff Tier 6 Ablation Report",
        "",
        f"**Status:** {payload['status']}",
        "",
        "Two independent 35-turn runs used the committed context-match settings.",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    lines.extend(
        f"| {name} | {str(value).upper()} |"
        for name, value in payload["checks"].items()
    )
    lines.extend(
        [
            "",
            "Seeded prefix SHA-256: "
            f"`{payload['combined_seeded_prefix_sha256']}`.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

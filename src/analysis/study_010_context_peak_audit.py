from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = (
    REPO_ROOT
    / "experiments"
    / "study_010"
    / "runs"
    / "study_010_full_001"
)
ASSISTANT_CUE = "\n\nAssistant:"
ARMS = ("arm_l", "arm_s")


def audit_context_telemetry(run_root: Path = RUN_ROOT) -> dict:
    inputs = _input_paths(run_root)
    hashes_before = _hash_paths(inputs)
    arms = [_audit_arm(run_root / arm) for arm in ARMS]
    hashes_after = _hash_paths(inputs)

    inputs_unchanged = hashes_before == hashes_after
    all_rows_match = all(arm["all_rows_match"] for arm in arms)
    status = "PASS" if inputs_unchanged and all_rows_match else "FAIL"
    return {
        "record": "DR-001 context-peak provenance audit",
        "status": status,
        "estimator": "len(serialized_prompt_without_assistant_cue) // 4",
        "assistant_cue": ASSISTANT_CUE,
        "assistant_cue_chars": len(ASSISTANT_CUE),
        "interpretation": (
            "The telemetry is a character-based estimate from the serialized "
            "prompt, not an exact model-tokenizer count."
        ),
        "inputs_unchanged": inputs_unchanged,
        "input_file_count": len(inputs),
        "input_tree_sha256_before": _digest_mapping(hashes_before),
        "input_tree_sha256_after": _digest_mapping(hashes_after),
        "arms": arms,
    }


def write_artifacts(result: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "context_peak_audit.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output_dir / "context_peak_audit.md").write_text(
        _render_markdown(result),
        encoding="utf-8",
        newline="\n",
    )


def _audit_arm(arm_root: Path) -> dict:
    metrics_path = arm_root / "metrics" / "context_sizes.csv"
    with metrics_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    mismatches = []
    measurements = []
    for row in rows:
        turn = int(row["turn"])
        prompt_path = arm_root / "constructed_prompts" / f"turn_{turn:03d}.txt"
        serialized_prompt = prompt_path.read_text(encoding="utf-8")
        has_expected_cue = serialized_prompt.endswith(ASSISTANT_CUE)
        estimated_prompt = (
            serialized_prompt[: -len(ASSISTANT_CUE)]
            if has_expected_cue
            else serialized_prompt
        )
        recomputed = len(estimated_prompt) // 4
        logged = int(row["estimated_tokens"])
        if not has_expected_cue or recomputed != logged:
            mismatches.append(
                {
                    "turn": turn,
                    "has_expected_cue": has_expected_cue,
                    "logged_estimated_tokens": logged,
                    "recomputed_estimated_tokens": recomputed,
                }
            )
        measurements.append(
            {
                "turn": turn,
                "logged_estimated_tokens": logged,
                "recomputed_estimated_tokens": recomputed,
                "serialized_prompt_chars": len(serialized_prompt),
                "estimated_prompt_chars": len(estimated_prompt),
            }
        )

    peak = max(measurements, key=lambda item: item["logged_estimated_tokens"])
    return {
        "arm": arm_root.name,
        "rows_checked": len(rows),
        "all_rows_match": not mismatches,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "peak": peak,
    }


def _input_paths(run_root: Path) -> list[Path]:
    paths = []
    for arm in ARMS:
        arm_root = run_root / arm
        paths.append(arm_root / "metrics" / "context_sizes.csv")
        paths.extend(sorted((arm_root / "constructed_prompts").glob("turn_*.txt")))
    return sorted(paths)


def _hash_paths(paths: list[Path]) -> dict[str, str]:
    return {
        path.relative_to(REPO_ROOT).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in paths
    }


def _digest_mapping(mapping: dict[str, str]) -> str:
    payload = json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _render_markdown(result: dict) -> str:
    lines = [
        "# Study 010 Context-Peak Provenance Audit",
        "",
        f"**Status:** {result['status']}",
        "**Scope:** committed Study 010 serialized prompts and context telemetry",
        "",
        "## Result",
        "",
        "| Arm | Rows checked | Peak turn | Serialized chars | "
        "Chars before cue | Logged estimate | Recomputed estimate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in result["arms"]:
        peak = arm["peak"]
        lines.append(
            f"| {arm['arm']} | {arm['rows_checked']} | {peak['turn']} | "
            f"{peak['serialized_prompt_chars']:,} | "
            f"{peak['estimated_prompt_chars']:,} | "
            f"{peak['logged_estimated_tokens']:,} | "
            f"{peak['recomputed_estimated_tokens']:,} |"
        )
    lines.extend(
        [
            "",
            f"All rows match: **{all(arm['all_rows_match'] for arm in result['arms'])}**.",
            f"Inputs unchanged: **{result['inputs_unchanged']}**.",
            "",
            "The runner computed telemetry from the complete constructed prompt before",
            f"appending the {len(ASSISTANT_CUE)}-character `\\n\\nAssistant:` "
            "generation cue. The logged",
            "peak therefore does not use the undercharged LTM content total.",
            "",
            "## Boundary",
            "",
            result["interpretation"],
            "This pass does not repair or excuse the separate LTM budget violation.",
            "",
            "## Integrity",
            "",
            f"- Input files: {result['input_file_count']:,}",
            f"- Input tree SHA-256 before: `{result['input_tree_sha256_before']}`",
            f"- Input tree SHA-256 after: `{result['input_tree_sha256_after']}`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            REPO_ROOT
            / "experiments"
            / "components"
            / "rendering_expansion"
            / "artifacts"
            / "context_peak_audit"
        ),
    )
    args = parser.parse_args()
    result = audit_context_telemetry()
    write_artifacts(result, args.output_dir)
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

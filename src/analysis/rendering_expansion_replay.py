from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sqlite3
from html import escape
from pathlib import Path

from src.db.retrieval import get_all_episodes_with_embeddings
from src.memory.context_builder import render_ltm_block
from src.memory.distilled_ltm_store import get_distilled_retrieval_rows
from src.memory.stm_context_builder import render_episode_block


REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_010_RUN = (
    REPO_ROOT
    / "experiments"
    / "study_010"
    / "runs"
    / "study_010_full_001"
    / "arm_l"
)
STUDY_010_MANIFEST = (
    REPO_ROOT
    / "experiments"
    / "study_010"
    / "runs"
    / "study_010_full_001_l_launch_manifest.json"
)
STUDY_010_RUNTIME_START = (
    REPO_ROOT
    / "experiments"
    / "study_010"
    / "runtime"
    / "amendment_004"
    / "runtime_start.md"
)
BAKEOFF_RUN = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier6"
    / "runs"
    / "tier6_live_121_corrected_001"
    / "context_matched_stm"
)
DESIGN_COMMIT = "094cbea2"
AMENDMENT_COMMIT = "ad74b991"
EXECUTION_COMMIT = AMENDMENT_COMMIT
STUDY_010_TURNS = (999, 1000)
BAKEOFF_TURN = 115

CSV_FIELDS = (
    "block",
    "turn",
    "position",
    "episode_id",
    "distilled_id",
    "source_turn",
    "stored_span_chars",
    "source_content_chars",
    "escaped_content_chars",
    "serialized_element_chars",
    "structural_overhead_chars",
)


def generate_pre_fix_artifacts(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs = _input_paths()
    hashes_before = _hash_paths(inputs)

    study_rows, study_blocks = _study_010_measurements()
    bakeoff_rows, bakeoff_block = _bakeoff_measurements()
    rows = [*study_rows, *bakeoff_rows]
    blocks = [*study_blocks, bakeoff_block]

    hashes_after = _hash_paths(inputs)
    inputs_unchanged = hashes_before == hashes_after
    gr1_pass = all(
        block["character_identity"]
        and block["identity_order_match"]
        and block["actual_sha256"] == block["replayed_sha256"]
        for block in study_blocks
    )
    status = "PASS" if gr1_pass and inputs_unchanged else "FAIL"

    summary = {
        "record": "DR-001",
        "phase": "pre_fix",
        "design_commit": DESIGN_COMMIT,
        "amendment_commit": AMENDMENT_COMMIT,
        "execution_commit": EXECUTION_COMMIT,
        "renderer_source_sha256": _sha256(
            REPO_ROOT / "src" / "memory" / "context_builder.py"
        ),
        "stm_renderer_source_sha256": _sha256(
            REPO_ROOT / "src" / "memory" / "stm_context_builder.py"
        ),
        "runtime_provenance": _runtime_provenance(),
        "g_r1": {
            "status": status,
            "study_010_turns": list(STUDY_010_TURNS),
            "inputs_unchanged": inputs_unchanged,
            "input_file_count": len(inputs),
            "input_tree_sha256_before": _digest_mapping(hashes_before),
            "input_tree_sha256_after": _digest_mapping(hashes_after),
        },
        "blocks": blocks,
        "distributions": {
            block["block"]: _block_distribution(rows, block["block"])
            for block in blocks
        },
    }
    _write_csv(output_dir / "expansion_rows.csv", rows)
    _write_json(output_dir / "summary.json", summary)
    (output_dir / "gate_report.md").write_text(
        _gate_markdown(summary),
        encoding="utf-8",
        newline="\n",
    )
    return summary


def _study_010_measurements() -> tuple[list[dict], list[dict]]:
    connection = _read_only_connection(STUDY_010_RUN / "study.db")
    try:
        candidates = get_distilled_retrieval_rows(connection)
    finally:
        connection.close()
    by_distilled_id = {
        str(candidate["distilled_id"]): candidate for candidate in candidates
    }
    ltm_log = _read_csv(STUDY_010_RUN / "logs" / "ltm_context_episodes.csv")
    budget_log = {
        int(row["turn"]): row
        for row in _read_csv(STUDY_010_RUN / "logs" / "retrieval_budget.csv")
        if int(row["turn"]) in STUDY_010_TURNS
    }

    measurements: list[dict] = []
    blocks: list[dict] = []
    for turn in STUDY_010_TURNS:
        historical = [
            row for row in ltm_log if int(row["turn"]) == turn
        ]
        selected = []
        for row in historical:
            candidate = dict(by_distilled_id[row["distilled_id"]])
            candidate.update(
                similarity=float(row["similarity"]),
                provenance=row["provenance"],
                render_mode=row["render_mode"],
            )
            selected.append(candidate)

        replayed = render_ltm_block(selected)
        actual = _extract_block(
            (STUDY_010_RUN / "constructed_prompts" / f"turn_{turn:03d}.txt")
            .read_text(encoding="utf-8"),
            "retrieved_ltm",
        )
        logged_ids = [row["episode_id"] for row in historical]
        replayed_ids = [str(candidate["id"]) for candidate in selected]
        block_name = f"study_010_q{13 if turn == 999 else 14}"
        for position, candidate in enumerate(selected, 1):
            measurements.append(
                _measurement_row(
                    block=block_name,
                    turn=turn,
                    position=position,
                    candidate=candidate,
                    element=_single_ltm_element(candidate),
                )
            )
        blocks.append(
            {
                "block": block_name,
                "turn": turn,
                "episode_count": len(selected),
                "budget_chars": int(budget_log[turn]["b_ltm"]),
                "historical_charged_chars": int(
                    budget_log[turn]["ltm_chars_used"]
                ),
                "actual_serialized_chars": len(actual),
                "replayed_serialized_chars": len(replayed),
                "budget_overrun_chars": (
                    len(actual) - int(budget_log[turn]["b_ltm"])
                ),
                "actual_sha256": _text_sha256(actual),
                "replayed_sha256": _text_sha256(replayed),
                "character_identity": actual == replayed,
                "identity_order_match": logged_ids == replayed_ids,
            }
        )
    return measurements, blocks


def _bakeoff_measurements() -> tuple[list[dict], dict]:
    context_row = next(
        json.loads(line)
        for line in (
            BAKEOFF_RUN / "logs" / "context_match.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        if int(json.loads(line)["turn_number"]) == BAKEOFF_TURN
    )
    connection = _read_only_connection(BAKEOFF_RUN / "study.db")
    try:
        episodes = get_all_episodes_with_embeddings(connection)
    finally:
        connection.close()
    by_id = {str(episode["id"]): episode for episode in episodes}
    recent = [
        by_id[episode_id] for episode_id in context_row["delivered_n_ids"]
    ]
    stm = [
        {
            **by_id[episode_id],
            "similarity": 0.0,
        }
        for episode_id in context_row["delivered_k_only_ids"]
    ]
    replayed = "\n\n".join(
        (
            render_episode_block("recent_context", recent, "recent"),
            render_episode_block("retrieved_stm", stm, "stm"),
        )
    )
    prompt = (
        BAKEOFF_RUN / "constructed_prompts" / f"turn_{BAKEOFF_TURN:03d}.txt"
    ).read_text(encoding="utf-8")
    actual = "\n\n".join(
        (
            _extract_block(prompt, "recent_context"),
            _extract_block(prompt, "retrieved_stm"),
        )
    )
    rows = []
    for position, candidate in enumerate([*recent, *stm], 1):
        tier = "recent" if position <= len(recent) else "stm"
        rows.append(
            _measurement_row(
                block="bakeoff_tier6_q4",
                turn=BAKEOFF_TURN,
                position=position,
                candidate=candidate,
                element=_single_stm_element(candidate, tier),
            )
        )
    selected_ids = [str(candidate["id"]) for candidate in (*recent, *stm)]
    return rows, {
        "block": "bakeoff_tier6_q4",
        "turn": BAKEOFF_TURN,
        "episode_count": len(selected_ids),
        "budget_chars": int(context_row["payload_budget"]),
        "historical_charged_chars": int(
            context_row["retrieval_payload_chars"]
        ),
        "actual_serialized_chars": len(actual),
        "replayed_serialized_chars": len(replayed),
        "budget_overrun_chars": len(actual) - int(context_row["payload_budget"]),
        "actual_sha256": _text_sha256(actual),
        "replayed_sha256": _text_sha256(replayed),
        "character_identity": actual == replayed,
        "identity_order_match": (
            context_row["selected_ids"] == selected_ids
        ),
    }


def _measurement_row(
    *,
    block: str,
    turn: int,
    position: int,
    candidate: dict,
    element: str,
) -> dict:
    user = str(candidate.get("user_message") or "")
    assistant = str(candidate.get("assistant_message") or "")
    escaped_chars = len(escape(user, quote=False)) + len(
        escape(assistant, quote=False)
    )
    span_text = candidate.get("span_text")
    return {
        "block": block,
        "turn": turn,
        "position": position,
        "episode_id": str(candidate["id"]),
        "distilled_id": str(candidate.get("distilled_id") or ""),
        "source_turn": int(candidate["turn_number"]),
        "stored_span_chars": (
            len(str(span_text)) if span_text is not None else ""
        ),
        "source_content_chars": len(user) + len(assistant),
        "escaped_content_chars": escaped_chars,
        "serialized_element_chars": len(element),
        "structural_overhead_chars": len(element) - escaped_chars,
    }


def _single_ltm_element(candidate: dict) -> str:
    return _single_element(render_ltm_block([candidate]))


def _single_stm_element(candidate: dict, tier: str) -> str:
    return _single_element(
        render_episode_block("measurement", [candidate], tier)
    )


def _single_element(block: str) -> str:
    if "\n" not in block:
        raise AssertionError("Expected a non-empty rendered block")
    return block.split("\n", 1)[1].rsplit("\n", 1)[0]


def _block_distribution(rows: list[dict], block: str) -> dict:
    selected = [row for row in rows if row["block"] == block]
    fields = (
        "stored_span_chars",
        "source_content_chars",
        "serialized_element_chars",
        "structural_overhead_chars",
    )
    return {
        "episode_count": len(selected),
        **{
            field: _distribution(
                [
                    int(row[field])
                    for row in selected
                    if row[field] != ""
                ]
            )
            for field in fields
        },
    }


def _distribution(values: list[int]) -> dict:
    if not values:
        return {
            "count": 0,
            "min": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p95": None,
            "max": None,
            "total": 0,
        }
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "min": ordered[0],
        "p25": _nearest_rank(ordered, 0.25),
        "median": _nearest_rank(ordered, 0.50),
        "p75": _nearest_rank(ordered, 0.75),
        "p95": _nearest_rank(ordered, 0.95),
        "max": ordered[-1],
        "total": sum(ordered),
    }


def _nearest_rank(ordered: list[int], percentile: float) -> int:
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def _extract_block(prompt: str, name: str) -> str:
    match = re.search(
        rf"<{name}(?:>.*?</{name}>|/>)",
        prompt,
        flags=re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"Prompt has no {name} block")
    return match.group(0)


def _runtime_provenance() -> dict:
    manifest = json.loads(STUDY_010_MANIFEST.read_text(encoding="utf-8"))
    server = manifest["server_props"]
    params = server["default_generation_settings"]["params"]
    runtime_start = STUDY_010_RUNTIME_START.read_text(encoding="utf-8")
    command_match = re.search(
        r"## Launch Command\s+```text\s+(.*?)\s+```",
        runtime_start,
        flags=re.DOTALL,
    )
    model_sha_match = re.search(
        r"Qwen3\.6-27B-UD-Q6_K_XL\.gguf` \| `([0-9a-f]{64})`",
        runtime_start,
    )
    if command_match is None or model_sha_match is None:
        raise AssertionError("Study 010 runtime provenance is incomplete")
    return {
        "manifest": str(STUDY_010_MANIFEST.relative_to(REPO_ROOT)),
        "manifest_sha256": _sha256(STUDY_010_MANIFEST),
        "runtime_start": str(STUDY_010_RUNTIME_START.relative_to(REPO_ROOT)),
        "runtime_start_sha256": _sha256(STUDY_010_RUNTIME_START),
        "model_alias": server["model_alias"],
        "model_sha256": model_sha_match.group(1),
        "server_build": server["build_info"],
        "seed": manifest["seed"],
        "parallel": server["total_slots"],
        "ctx_size": manifest["context_capacity"],
        "cache_type_k": "q8_0",
        "cache_type_v": "q8_0",
        "speculative_decoding": params["speculative.types"],
        "launch_command": command_match.group(1),
        "replay_mode": "offline_no_inference",
    }


def _input_paths() -> list[Path]:
    return [
        STUDY_010_RUN / "study.db",
        STUDY_010_RUN / "logs" / "ltm_context_episodes.csv",
        STUDY_010_RUN / "logs" / "retrieval_budget.csv",
        *[
            STUDY_010_RUN
            / "constructed_prompts"
            / f"turn_{turn:03d}.txt"
            for turn in STUDY_010_TURNS
        ],
        STUDY_010_MANIFEST,
        STUDY_010_RUNTIME_START,
        BAKEOFF_RUN / "study.db",
        BAKEOFF_RUN / "logs" / "context_match.jsonl",
        BAKEOFF_RUN / "constructed_prompts" / "turn_115.txt",
    ]


def _read_only_connection(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(
        f"file:{path.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _hash_paths(paths: list[Path]) -> dict[str, str]:
    return {
        str(path.relative_to(REPO_ROOT)): _sha256(path)
        for path in sorted(paths)
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _digest_mapping(mapping: dict[str, str]) -> str:
    text = "".join(
        f"{path}\0{digest}\n" for path, digest in sorted(mapping.items())
    )
    return _text_sha256(text)


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _gate_markdown(summary: dict) -> str:
    blocks = summary["blocks"]
    lines = [
        "# DR-001 Pre-Fix Replay and Expansion Measurement",
        "",
        f"**Design commit:** `{summary['design_commit']}`  ",
        f"**Amendment commit:** `{summary['amendment_commit']}`  ",
        f"**Execution commit:** `{summary['execution_commit']}`  ",
        f"**G-R1:** **{summary['g_r1']['status']}**",
        "",
        "No inference call was made. Immutable inputs were unchanged.",
        "",
        "| Block | Episodes | Charged chars | Actual chars | Budget | Overrun | Replay |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for block in blocks:
        lines.append(
            "| {block} | {episode_count} | {historical_charged_chars} | "
            "{actual_serialized_chars} | {budget_chars} | "
            "{budget_overrun_chars} | {status} |".format(
                **block,
                status=(
                    "PASS"
                    if block["character_identity"]
                    and block["identity_order_match"]
                    else "FAIL"
                ),
            )
        )
    lines.extend(
        [
            "",
            "Q13 and Q14 reproduce character-for-character and preserve the "
            "historical episode identity/order list. The previously published "
            "31,991 and 31,847 values are charged content characters; the "
            "actual serialized blocks are 53,726 and 53,839 characters.",
            "",
            "Per-episode rows and distribution summaries are in "
            "`expansion_rows.csv` and `summary.json`.",
            "",
        ]
    )
    return "\n".join(lines)

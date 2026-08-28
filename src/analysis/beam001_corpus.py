"""Trusted BEAM-001 source audit and one-way corpus split.

This is the only Part 1 module allowed to read the raw BEAM parquet rows. It
emits a question-only mechanism surface and a physically separate outcome
surface. Downstream mechanism code imports ``beam001_adapter`` instead.
"""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pyarrow.parquet as parquet
import tiktoken

DOMAIN = "BEAM"
SOURCE_MANIFEST = (
    Path(__file__).resolve().parents[2]
    / "experiments/comparisons/beam_001/artifacts/corpus/source_manifest.json"
)
ARTIFACT_ROOT = SOURCE_MANIFEST.parent
MECHANISM_SURFACE = ARTIFACT_ROOT / "mechanism_surface.jsonl.gz"
OUTCOME_SURFACE = ARTIFACT_ROOT / "outcome_surface.sealed.jsonl.gz"
SCHEMA_REPORT = ARTIFACT_ROOT / "schema_report.json"
SURFACE_MANIFEST = ARTIFACT_ROOT / "surface_manifest.json"
TOKENIZER_NAME = "cl100k_base"

OUTCOME_FIELDS = frozenset(
    {
        "abstention_type",
        "answer",
        "bullet_points_covered",
        "calculation_required",
        "complexity_factors",
        "compliance_indicators",
        "contradiction_type",
        "conversation_reference",
        "conversation_references",
        "conversation_sessions",
        "difficulty",
        "expected_compliance",
        "extraction_challenge",
        "ideal_answer",
        "ideal_response",
        "ideal_summary",
        "instruction_being_tested",
        "instruction_type",
        "key_elements_tested",
        "key_facts_tested",
        "non_compliance_signs",
        "ordering_tested",
        "ordering_type",
        "plan_reference",
        "potential_confusion",
        "preference_being_tested",
        "preference_type",
        "question_type",
        "reasoning_steps",
        "reasoning_type",
        "rubric",
        "sessions_required",
        "source_chat_ids",
        "summarization_type",
        "synthesis_required",
        "temporal_type",
        "tests_for",
        "tests_retention_of",
        "time_points",
        "topic_questioned",
        "total_mentions",
        "update_type",
        "why_unanswerable",
    }
)


class BeamCorpusError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_digest(*parts: bytes) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part)
    return digest.hexdigest()


def conversation_key(split: str, chat: Sequence[Any]) -> str:
    return stable_digest(DOMAIN.encode(), split.encode(), canonical_bytes(chat))


def question_key(
    conversation: str,
    category: str,
    question: str,
    occurrence_ordinal: int,
) -> str:
    return stable_digest(
        DOMAIN.encode(),
        conversation.encode(),
        category.encode(),
        question.encode("utf-8"),
        str(occurrence_ordinal).encode(),
    )


def _load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or "dataset" not in value:
        raise BeamCorpusError("Source manifest is not a BEAM-001 manifest")
    return value


def _validate_sources(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    root = Path(str(manifest["dataset"]["external_root"]))
    parquet_files: list[dict[str, Any]] = []
    for record in manifest["dataset"]["files"]:
        path = root / record["path"]
        if not path.is_file():
            raise BeamCorpusError(f"Missing source input: {path}")
        observed = sha256_file(path)
        if observed != record["sha256"]:
            raise BeamCorpusError(f"Source hash mismatch: {record['path']}")
        if str(record["path"]).endswith(".parquet"):
            parquet_files.append({**record, "absolute_path": path})
    if sum(int(item["rows"]) for item in parquet_files) != int(
        manifest["dataset"]["normal_scale_rows"]
    ):
        raise BeamCorpusError("Manifest row totals are inconsistent")
    return sorted(parquet_files, key=lambda item: str(item["split"]))


def _parse_questions(raw: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(raw, str):
        raise BeamCorpusError("probing_questions must be a Python-literal string")
    try:
        parsed = ast.literal_eval(raw)
    except (SyntaxError, ValueError) as error:
        raise BeamCorpusError("probing_questions did not parse as a literal") from error
    if not isinstance(parsed, dict):
        raise BeamCorpusError("probing_questions root must be a mapping")
    result: dict[str, list[dict[str, Any]]] = {}
    for category, items in parsed.items():
        if not isinstance(category, str) or not isinstance(items, list):
            raise BeamCorpusError("Question category shape drifted")
        if any(not isinstance(item, dict) for item in items):
            raise BeamCorpusError("Question item shape drifted")
        result[category] = items
    return result


def _distribution(values: Sequence[int]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "min": None, "p05": None, "p25": None, "median": None,
                "p75": None, "p95": None, "max": None}
    ordered = sorted(values)

    def percentile(fraction: float) -> int:
        return ordered[round((len(ordered) - 1) * fraction)]

    return {
        "n": len(ordered),
        "min": ordered[0],
        "p05": percentile(0.05),
        "p25": percentile(0.25),
        "median": percentile(0.50),
        "p75": percentile(0.75),
        "p95": percentile(0.95),
        "max": ordered[-1],
    }


def _flatten_chat(chat: Any) -> list[dict[str, Any]]:
    if not isinstance(chat, list):
        raise BeamCorpusError("chat must be a list of batches")
    flattened: list[dict[str, Any]] = []
    for batch in chat:
        if not isinstance(batch, list):
            raise BeamCorpusError("chat batch must be a list")
        for message in batch:
            if not isinstance(message, dict):
                raise BeamCorpusError("chat message must be a mapping")
            flattened.append(message)
    return flattened


def _iter_rows(files: Sequence[Mapping[str, Any]]) -> Iterable[tuple[Mapping[str, Any], int, dict]]:
    for source in files:
        rows = parquet.read_table(source["absolute_path"]).to_pylist()
        if len(rows) != int(source["rows"]):
            raise BeamCorpusError(f"Parquet row count drifted: {source['path']}")
        for row_index, row in enumerate(rows):
            yield source, row_index, row


def _audit_rows(files: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    tokenizer = tiktoken.get_encoding(TOKENIZER_NAME)
    counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    transitions: Counter[str] = Counter()
    question_categories: Counter[str] = Counter()
    question_fields: Counter[str] = Counter()
    batch_counts: list[int] = []
    message_counts: list[int] = []
    batch_message_counts: list[int] = []
    flattened_chars: list[int] = []
    flattened_tokens: list[int] = []
    scales: Counter[str] = Counter()

    for source, _row_index, row in _iter_rows(files):
        counts["conversations"] += 1
        scales[str(source["split"])] += 1
        chat = row.get("chat")
        if not isinstance(chat, list):
            counts["invalid_chat_root"] += 1
            continue
        batch_counts.append(len(chat))
        batch_message_counts.extend(len(batch) if isinstance(batch, list) else 0 for batch in chat)
        messages = _flatten_chat(chat)
        message_counts.append(len(messages))
        text_parts: list[str] = []
        roles: list[str] = []
        anchors: list[str] = []
        for message in messages:
            role = message.get("role")
            content = message.get("content")
            if not isinstance(role, str):
                counts["non_string_role"] += 1
                role = f"<{type(role).__name__}>"
            if not isinstance(content, str):
                counts["non_string_content"] += 1
            elif not content:
                counts["empty_content"] += 1
            else:
                text_parts.append(content)
            roles.append(role)
            role_counts[role] += 1
            anchor = message.get("time_anchor")
            if isinstance(anchor, str) and anchor:
                counts["timestamp_present"] += 1
                anchors.append(anchor)
            else:
                counts["timestamp_missing"] += 1
        for left, right in zip(roles, roles[1:]):
            transitions[f"{left}->{right}"] += 1
            if left == right:
                counts["consecutive_same_role"] += 1
        if roles and roles[0] == "assistant":
            counts["leading_assistant_conversations"] += 1
        if roles and roles[-1] == "user":
            counts["trailing_user_conversations"] += 1
        parsed_anchors = []
        for anchor in anchors:
            try:
                parsed_anchors.append(datetime.strptime(anchor, "%B-%d-%Y"))
            except ValueError:
                counts["timestamp_parse_failures"] += 1
        if len(parsed_anchors) == len(anchors) and any(
            right < left for left, right in zip(parsed_anchors, parsed_anchors[1:])
        ):
            counts["non_monotonic_timestamp_conversations"] += 1
        flattened = "".join(text_parts)
        flattened_chars.append(len(flattened))
        flattened_tokens.append(len(tokenizer.encode(flattened)))

        questions = _parse_questions(row.get("probing_questions"))
        for category, items in questions.items():
            question_categories[category] += len(items)
            counts["questions"] += len(items)
            for item in items:
                question_fields.update(item.keys())
                if not isinstance(item.get("question"), str):
                    counts["non_string_question"] += 1

    strict_pairs = (
        not counts["non_string_role"]
        and not counts["non_string_content"]
        and not counts["empty_content"]
        and not counts["consecutive_same_role"]
        and not counts["leading_assistant_conversations"]
        and not counts["trailing_user_conversations"]
        and set(role_counts) == {"user", "assistant"}
        and role_counts["user"] == role_counts["assistant"]
    )
    return {
        "behavioral_identity": (
            "Flatten source batches in order and admit one episode for each exact "
            "adjacent user/assistant pair, without merging, dropping or inventing content."
        ),
        "counts": dict(sorted(counts.items())),
        "scale_conversations": dict(sorted(scales.items())),
        "roles": dict(sorted(role_counts.items())),
        "role_transitions": dict(sorted(transitions.items())),
        "question_categories": dict(sorted(question_categories.items())),
        "question_field_presence": dict(sorted(question_fields.items())),
        "batch_count_distribution": _distribution(batch_counts),
        "batch_message_count_distribution": _distribution(batch_message_counts),
        "message_count_distribution": _distribution(message_counts),
        "flattened_character_distribution": _distribution(flattened_chars),
        "flattened_token_distribution": {
            "tokenizer": TOKENIZER_NAME,
            **_distribution(flattened_tokens),
        },
        "strict_lossless_pair_mapping": strict_pairs,
        "gate": "PASS" if strict_pairs else "CORPUS_ADAPTER_NOT_IDENTIFIED",
    }


def _write_gzip_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as raw_handle:
        temporary = Path(raw_handle.name)
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, mtime=0) as stream:
            for row in rows:
                stream.write(canonical_bytes(row) + b"\n")
        raw_handle.flush()
        os.fsync(raw_handle.fileno())
    temporary.replace(path)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, newline="\n"
    ) as handle:
        temporary = Path(handle.name)
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def prepare(
    *,
    manifest_path: Path = SOURCE_MANIFEST,
    mechanism_path: Path = MECHANISM_SURFACE,
    outcome_path: Path = OUTCOME_SURFACE,
    schema_path: Path = SCHEMA_REPORT,
    surface_manifest_path: Path = SURFACE_MANIFEST,
) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    files = _validate_sources(manifest)
    report = _audit_rows(files)
    _write_json(schema_path, report)
    if report["gate"] != "PASS":
        return report

    mechanism_rows: list[dict[str, Any]] = []
    outcome_rows: list[dict[str, Any]] = []
    for source, row_index, row in _iter_rows(files):
        split = str(source["split"])
        chat = row["chat"]
        conv_key = conversation_key(split, chat)
        occurrences: Counter[tuple[str, str]] = Counter()
        mechanism_questions: list[dict[str, Any]] = []
        questions = _parse_questions(row["probing_questions"])
        for category, items in questions.items():
            for item in items:
                question = item.get("question")
                if not isinstance(question, str):
                    raise BeamCorpusError("Question text must be a string")
                occurrence = occurrences[(category, question)]
                occurrences[(category, question)] += 1
                key = question_key(conv_key, category, question, occurrence)
                mechanism_questions.append(
                    {
                        "question_key": key,
                        "category": category,
                        "question": question,
                        "occurrence_ordinal": occurrence,
                    }
                )
                unknown = set(item) - OUTCOME_FIELDS - {"question"}
                if unknown:
                    raise BeamCorpusError(
                        f"Unclassified question fields for {key}: {sorted(unknown)}"
                    )
                outcome_rows.append(
                    {
                        "question_key": key,
                        "official_fields": {
                            field: item.get(field) for field in sorted(OUTCOME_FIELDS)
                        },
                    }
                )
        mechanism_rows.append(
            {
                "domain": DOMAIN,
                "split": split,
                "conversation_id": row["conversation_id"],
                "conversation_key": conv_key,
                "chat_batches": chat,
                "questions": mechanism_questions,
                "source": {
                    "dataset_revision": manifest["dataset"]["revision"],
                    "file": source["path"],
                    "file_sha256": source["sha256"],
                    "row_index": row_index,
                },
            }
        )

    if len(mechanism_rows) != report["counts"]["conversations"]:
        raise BeamCorpusError("Mechanism row count drifted")
    if len(outcome_rows) != report["counts"]["questions"]:
        raise BeamCorpusError("Outcome row count drifted")
    mechanism_keys = {
        question["question_key"]
        for row in mechanism_rows
        for question in row["questions"]
    }
    outcome_keys = {row["question_key"] for row in outcome_rows}
    if mechanism_keys != outcome_keys or len(outcome_keys) != len(outcome_rows):
        raise BeamCorpusError("Question surfaces are not a one-to-one key split")

    _write_gzip_jsonl(mechanism_path, mechanism_rows)
    _write_gzip_jsonl(outcome_path, outcome_rows)
    surface_manifest = {
        "source_manifest_sha256": sha256_file(manifest_path),
        "splitter_sha256": sha256_file(Path(__file__)),
        "mechanism_surface": {
            "path": mechanism_path.name,
            "rows": len(mechanism_rows),
            "questions": len(mechanism_keys),
            "sha256": sha256_file(mechanism_path),
        },
        "outcome_surface": {
            "path": outcome_path.name,
            "rows": len(outcome_rows),
            "sha256": sha256_file(outcome_path),
            "sealed": True,
        },
        "schema_report_sha256": sha256_file(schema_path),
        "question_key_sets_equal": True,
        "outcomes_printed": False,
    }
    _write_json(surface_manifest_path, surface_manifest)
    return surface_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=SOURCE_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=ARTIFACT_ROOT)
    args = parser.parse_args()
    root = args.output_root
    result = prepare(
        manifest_path=args.manifest,
        mechanism_path=root / MECHANISM_SURFACE.name,
        outcome_path=root / OUTCOME_SURFACE.name,
        schema_path=root / SCHEMA_REPORT.name,
        surface_manifest_path=root / SURFACE_MANIFEST.name,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("gate", "PASS") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

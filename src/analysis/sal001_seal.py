from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.analysis.sal001_shared import (
    DATASET_BYTES,
    DATASET_SHA256,
    EXPECTED_COUNTS,
    EXPECTED_SELECTION_DIGEST,
    HOLDOUT_START,
    HOLDOUT_STOP,
    SEED,
    STRATA,
    artifact_identity,
    canonical_digest,
    exchange_content_sha256,
    ordered_selection_digest,
    selection_sort_key,
    session_content_sha256,
    sha256_file,
    write_json,
)


class SAL001SealError(RuntimeError):
    pass


def _load_dataset(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise SAL001SealError(f"Dataset is absent: {path}")
    if path.stat().st_size != DATASET_BYTES:
        raise SAL001SealError("Dataset byte count differs from the registration")
    if sha256_file(path) != DATASET_SHA256:
        raise SAL001SealError("Dataset SHA-256 differs from the registration")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or len(value) != 500:
        raise SAL001SealError("Expected the 500-row cleaned LongMemEval release")
    return value


def select_holdout(
    dataset: list[dict[str, Any]], tier2_registration: dict[str, Any]
) -> tuple[list[tuple[str, int, dict[str, Any]]], dict[str, Any]]:
    by_stratum: dict[str, list[dict[str, Any]]] = {name: [] for name in STRATA}
    for row in dataset:
        question_id = str(row.get("question_id", ""))
        stratum = str(row.get("question_type", ""))
        if question_id.endswith("_abs") or stratum not in by_stratum:
            continue
        by_stratum[stratum].append(row)

    selected: list[tuple[str, int, dict[str, Any]]] = []
    reproduced: dict[str, bool] = {}
    for stratum in STRATA:
        ranked = sorted(
            by_stratum[stratum],
            key=lambda row: selection_sort_key(stratum, str(row["question_id"])),
        )
        expected_first_twenty = list(
            tier2_registration["question_ids_by_stratum"][stratum]
        )
        observed_first_twenty = [
            str(row["question_id"]) for row in ranked[:HOLDOUT_START]
        ]
        reproduced[stratum] = observed_first_twenty == expected_first_twenty
        for offset, row in enumerate(
            ranked[HOLDOUT_START:HOLDOUT_STOP], start=HOLDOUT_START + 1
        ):
            selected.append((stratum, offset, row))

    if not all(reproduced.values()):
        raise SAL001SealError("EC-001 ranks 1-20 did not reproduce")
    question_ids = [str(row["question_id"]) for _stratum, _rank, row in selected]
    digest = ordered_selection_digest(question_ids)
    if digest != EXPECTED_SELECTION_DIGEST:
        raise SAL001SealError("Held-out ranks 21-30 do not match the registration")
    return selected, {
        "seed": SEED,
        "rank_start_inclusive": HOLDOUT_START + 1,
        "rank_end_inclusive": HOLDOUT_STOP,
        "question_count": len(selected),
        "ordered_question_id_sha256": digest,
        "ec001_first_twenty_reproduced": reproduced,
    }


def _strict_exchanges(session: list[dict[str, Any]]) -> bool:
    return bool(
        session
        and len(session) % 2 == 0
        and all(
            session[index].get("role") == "user"
            and session[index + 1].get("role") == "assistant"
            for index in range(0, len(session), 2)
        )
    )


def build_sealed_artifacts(
    dataset: list[dict[str, Any]], tier2_registration: dict[str, Any]
) -> dict[str, Any]:
    selected, selection_summary = select_holdout(dataset, tier2_registration)
    scorer_sessions: list[dict[str, Any]] = []
    label_sessions: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter(selected_items=len(selected))
    seen_session_hashes: set[str] = set()

    for stratum, rank, row in selected:
        question_id = str(row["question_id"])
        selection_rows.append(
            {
                "question_id": question_id,
                "stratum": stratum,
                "stratum_rank": rank,
                "selection_key": selection_sort_key(stratum, question_id),
            }
        )
        raw_ids = row.get("haystack_session_ids")
        sessions = row.get("haystack_sessions")
        evidence_ids = row.get("answer_session_ids")
        if not (
            isinstance(raw_ids, list)
            and isinstance(sessions, list)
            and isinstance(evidence_ids, list)
            and len(raw_ids) == len(sessions)
        ):
            raise SAL001SealError(f"Malformed history arrays for {question_id}")
        evidence_id_set = set(str(value) for value in evidence_ids)
        if not evidence_id_set <= set(str(value) for value in raw_ids):
            raise SAL001SealError(f"Missing named source session for {question_id}")

        for raw_id, session in zip(raw_ids, sessions, strict=True):
            if str(raw_id) not in evidence_id_set:
                continue
            counts["named_evidence_sessions"] += 1
            if not isinstance(session, list):
                raise SAL001SealError(f"Non-list source session for {question_id}")
            marker_present = any(
                bool(turn.get("has_answer", False))
                for turn in session
                if isinstance(turn, dict)
            )
            if not marker_present:
                counts["named_sessions_without_marker"] += 1
                continue
            if not _strict_exchanges(session):
                counts["irregular_named_sessions"] += 1
                continue

            messages = [
                {"role": str(turn["role"]), "content": str(turn["content"])}
                for turn in session
            ]
            session_hash = session_content_sha256(messages)
            if session_hash in seen_session_hashes:
                raise SAL001SealError(
                    "Duplicate eligible session content would make keys ambiguous"
                )
            seen_session_hashes.add(session_hash)
            labels: list[bool] = []
            exchanges: list[dict[str, Any]] = []
            for exchange_index, source_index in enumerate(
                range(0, len(session), 2)
            ):
                user = session[source_index]
                assistant = session[source_index + 1]
                label = bool(
                    user.get("has_answer", False)
                    or assistant.get("has_answer", False)
                )
                labels.append(label)
                exchanges.append(
                    {
                        "exchange_index": exchange_index,
                        "content_sha256": exchange_content_sha256(
                            str(user["content"]), str(assistant["content"])
                        ),
                        "user": str(user["content"]),
                        "assistant": str(assistant["content"]),
                    }
                )

            counts["eligible_sessions"] += 1
            counts["eligible_exchanges"] += len(exchanges)
            counts["evidence_exchanges"] += sum(labels)
            counts["unmarked_exchanges"] += len(labels) - sum(labels)
            for index, label in enumerate(labels):
                if not label:
                    continue
                has_prior = index > 0
                has_next = index + 1 < len(labels)
                counts["evidence_with_any_neighbor"] += int(has_prior or has_next)
                counts["evidence_with_prior"] += int(has_prior)
                counts["evidence_with_next"] += int(has_next)
                counts["evidence_with_both"] += int(has_prior and has_next)
            if 0 < sum(labels) < len(labels) and len(labels) > 1:
                counts["auc_sessions"] += 1

            scorer_sessions.append(
                {
                    "session_sha256": session_hash,
                    "exchange_count": len(exchanges),
                    "exchanges": exchanges,
                }
            )
            label_sessions.append(
                {
                    "session_sha256": session_hash,
                    "stratum": stratum,
                    "labels": labels,
                }
            )

    observed = {key: int(counts[key]) for key in EXPECTED_COUNTS}
    if observed != EXPECTED_COUNTS:
        raise SAL001SealError(
            f"Registered population mismatch: {observed!r} != {EXPECTED_COUNTS!r}"
        )
    scorer_sessions.sort(key=lambda row: row["session_sha256"])
    label_sessions.sort(key=lambda row: row["session_sha256"])
    selection_rows.sort(key=lambda row: (STRATA.index(row["stratum"]), row["stratum_rank"]))

    scorer_manifest = {
        "schema": "sal001-label-free-scorer-manifest-v1",
        "dataset_sha256": DATASET_SHA256,
        "sessions": scorer_sessions,
    }
    sealed_labels = {
        "schema": "sal001-sealed-labels-v1",
        "dataset_sha256": DATASET_SHA256,
        "sessions": label_sessions,
    }
    selection_manifest = {
        "schema": "sal001-selection-v1",
        "dataset_sha256": DATASET_SHA256,
        "selection": selection_summary,
        "rows": selection_rows,
    }
    return {
        "scorer_manifest": scorer_manifest,
        "sealed_labels": sealed_labels,
        "selection_manifest": selection_manifest,
        "counts": observed,
        "digests": {
            "scorer_manifest": canonical_digest(scorer_manifest),
            "sealed_labels": canonical_digest(sealed_labels),
            "selection_manifest": canonical_digest(selection_manifest),
        },
    }


def run(
    dataset_path: Path,
    tier2_registration_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    dataset = _load_dataset(dataset_path)
    registration = json.loads(tier2_registration_path.read_text(encoding="utf-8"))
    artifacts = build_sealed_artifacts(dataset, registration)
    scorer_path = output_dir / "scorer_manifest.json"
    labels_path = output_dir / "SEALED_LABELS_DO_NOT_OPEN.json"
    selection_path = output_dir / "selection_manifest.json"
    report_path = output_dir / "seal_report.json"
    for path in (scorer_path, labels_path, selection_path, report_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite seal artifact: {path}")
    write_json(scorer_path, artifacts["scorer_manifest"])
    write_json(labels_path, artifacts["sealed_labels"])
    write_json(selection_path, artifacts["selection_manifest"])
    report = {
        "study": "SAL-001",
        "status": "PASS",
        "counts": artifacts["counts"],
        "canonical_digests": artifacts["digests"],
        "inputs": {
            "dataset": artifact_identity(dataset_path),
            "tier2_registration": artifact_identity(tier2_registration_path),
        },
        "outputs": {
            "scorer_manifest": artifact_identity(scorer_path),
            "sealed_labels": artifact_identity(labels_path),
            "selection_manifest": artifact_identity(selection_path),
        },
        "scorer_manifest_contains_labels": False,
    }
    write_json(report_path, report)
    return report


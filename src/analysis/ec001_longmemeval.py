"""EC-001 LongMemEval V1 adaptation, gates, and Tier 1 measurement.

The benchmark reference surface is split at load time:

* ``MechanismInstance`` contains only the query and verbatim exchanges.
* ``MeasurementInstance`` contains evidence labels and timestamps.

Only the former may reach ``episodic``.  Joining retrieval with evidence is
an evaluation step after the returned block and cosine ranking already exist.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
EC001_ROOT = REPO_ROOT / "experiments" / "external" / "longmemeval"
REGISTRATION = EC001_ROOT / "EC_001_longmemeval_calibration.md"
ADAPTATION_RECORD = EC001_ROOT / "EC_001_ADAPTATION_RECORD.json"
AMENDMENT_001 = (
    EC001_ROOT
    / "amendments"
    / "AMENDMENT_001_irregular_session_turns.md"
)
AMENDMENT_002 = (
    EC001_ROOT
    / "amendments"
    / "AMENDMENT_002_foreign_schema_fidelity.md"
)
AMENDMENT_003 = (
    EC001_ROOT
    / "amendments"
    / "AMENDMENT_003_incomplete_turn_labels.md"
)
AMENDMENT_004 = (
    EC001_ROOT
    / "amendments"
    / "AMENDMENT_004_scoring_protocol_reconciliation.md"
)

REGISTRATION_SHA = "b595b05e1469c67277844d4bd97f77c89a20772b"
ADAPTATION_SHA = "a65c2566e55a2063bd1904065032f86c5d0e23a9"
AMENDMENT_001_SHA = "a1dc736cece4e1aa95412c661dec94da48feaf25"
AMENDMENT_002_SHA = "befa2c41659031496127d8b2a180e3c616801d02"
AMENDMENT_003_SHA = "4ce6db743f87431248e1c6eb67d3cd3a521c5465"
AMENDMENT_004_SHA = "37864822e4c429412b81f67db8af4af804308b8f"
EXPECTED_QUESTION_COUNT = 500
QUESTION_TYPES = (
    "single-session-user",
    "single-session-assistant",
    "single-session-preference",
    "temporal-reasoning",
    "knowledge-update",
    "multi-session",
)
EXPECTED_STRATA = (*QUESTION_TYPES, "abstention")
TIMESTAMP_FORMAT = "%Y/%m/%d (%a) %H:%M"


class EC001Error(RuntimeError):
    """A fail-closed EC-001 gate."""


@dataclass(frozen=True)
class EpisodeInput:
    """One mechanism-visible user/assistant exchange."""

    turn_number: int
    user_message: str
    assistant_message: str

    @property
    def embedded_text(self) -> str:
        return (
            f"User: {self.user_message}\n"
            f"Assistant: {self.assistant_message}"
        )


@dataclass(frozen=True)
class MechanismInstance:
    """The only LongMemEval fields permitted to reach retrieval."""

    question_id: str
    question: str
    episodes: tuple[EpisodeInput, ...]


@dataclass(frozen=True)
class EvidenceTurn:
    session_id: str
    episode_turn_number: int
    role: str
    content: str
    raw_session_id: str = ""


@dataclass(frozen=True)
class SourceTurn:
    """Measurement-only provenance for one foreign source turn."""

    session_id: str
    session_turn_index: int
    episode_turn_number: int
    role: str
    content: str
    raw_session_id: str = ""


@dataclass(frozen=True)
class MeasurementInstance:
    """Reference-only labels and source provenance, never mechanism input."""

    question_id: str
    question_type: str
    is_abstention: bool
    question_date: str
    session_ids: tuple[str, ...]
    session_dates: tuple[str, ...]
    episode_session_ids: tuple[str, ...]
    answer_session_ids: tuple[str, ...]
    evidence_turns: tuple[EvidenceTurn, ...]
    raw_session_ids: tuple[str, ...] = ()
    answer_session_keys: tuple[str, ...] = ()
    source_turns: tuple[SourceTurn, ...] = ()
    irregular_session_ids: tuple[str, ...] = ()
    singleton_episode_turn_numbers: tuple[int, ...] = ()

    @property
    def stratum(self) -> str:
        return "abstention" if self.is_abstention else self.question_type


@dataclass(frozen=True)
class InstanceBundle:
    mechanism: MechanismInstance
    measurement: MeasurementInstance


@dataclass(frozen=True)
class LoadedDataset:
    source_sha256: str
    instances: tuple[InstanceBundle, ...]
    annotation_findings: tuple[dict, ...]
    adaptation_stats: dict

    @property
    def by_id(self) -> dict[str, InstanceBundle]:
        return {
            bundle.mechanism.question_id: bundle for bundle in self.instances
        }


class CachingSoloEmbedder:
    """Cache exact solo-call vectors without introducing a batch call shape."""

    def __init__(self, delegate) -> None:
        self._delegate = delegate
        self._cache: dict[str, np.ndarray] = {}

    @property
    def model_sha256(self) -> str:
        return str(self._delegate.model_sha256)

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    def __call__(self, text: str) -> np.ndarray:
        if text not in self._cache:
            vector = np.asarray(self._delegate(text), dtype=np.float32)
            self._cache[text] = vector
        return self._cache[text]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_repository_ready(*, require_clean: bool = True) -> dict:
    """Bind registrations to this branch and reject contaminated runs."""

    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != "ec/001-longmemeval":
        raise EC001Error(
            f"EC-001 must run on ec/001-longmemeval, found {branch}"
        )
    for anchor in (
        REGISTRATION_SHA,
        ADAPTATION_SHA,
        AMENDMENT_001_SHA,
        AMENDMENT_002_SHA,
        AMENDMENT_003_SHA,
        AMENDMENT_004_SHA,
    ):
        completed = subprocess.run(
            ["git", "merge-base", "--is-ancestor", anchor, "HEAD"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if completed.returncode:
            raise EC001Error(f"Required EC-001 anchor is not in HEAD: {anchor}")
    status = _git("status", "--porcelain")
    if require_clean and status:
        raise EC001Error(
            "EC-001 refuses a dirty worktree before artifact creation:\n"
            f"{status}"
        )
    return {
        "branch": branch,
        "head": _git("rev-parse", "HEAD"),
        "registration_sha": REGISTRATION_SHA,
        "adaptation_sha": ADAPTATION_SHA,
        "amendment_001_sha": AMENDMENT_001_SHA,
        "amendment_002_sha": AMENDMENT_002_SHA,
        "amendment_003_sha": AMENDMENT_003_SHA,
        "amendment_004_sha": AMENDMENT_004_SHA,
        "worktree_clean": not bool(status),
    }


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def load_adaptation_record(
    path: Path = ADAPTATION_RECORD,
) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("registration_sha") != REGISTRATION_SHA:
        raise EC001Error("Adaptation record points to the wrong registration")

    decisions = payload.get("decisions", {})
    required = {
        "session_vs_episode",
        "timestamps",
        "budget",
        "recency_window",
        "embedder",
        "abstention",
    }
    missing = sorted(required - set(decisions))
    if missing:
        raise EC001Error(f"Adaptation record is missing decisions: {missing}")

    benchmark = payload.get("benchmark", {})
    required_benchmark = {
        "dataset_commit",
        "dataset_file",
        "dataset_sha256",
        "dataset_bytes",
    }
    missing_benchmark = sorted(required_benchmark - set(benchmark))
    if missing_benchmark:
        raise EC001Error(
            f"Adaptation record is missing benchmark pins: {missing_benchmark}"
        )
    if payload.get("tier_2_subset", {}).get("status") != (
        "MUST_BE_REGISTERED_SEPARATELY_BEFORE_TIER_1"
    ):
        raise EC001Error("Tier 2 registration order is not fail-closed")
    return payload


def load_longmemeval(
    path: Path,
    *,
    expected_sha256: str | None = None,
    expected_count: int | None = EXPECTED_QUESTION_COUNT,
) -> LoadedDataset:
    """Load the pinned JSON and split mechanism fields from reference fields."""

    observed_sha256 = sha256_file(path)
    if expected_sha256 and observed_sha256 != expected_sha256:
        raise EC001Error(
            "LongMemEval dataset hash mismatch: "
            f"expected {expected_sha256}, observed {observed_sha256}"
        )
    with path.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, list):
        raise EC001Error("LongMemEval root must be a JSON list")
    if expected_count is not None and len(raw) != expected_count:
        raise EC001Error(
            f"Expected {expected_count} LongMemEval questions, found {len(raw)}"
        )

    identifiers: set[str] = set()
    bundles: list[InstanceBundle] = []
    findings: list[dict] = []
    for index, entry in enumerate(raw):
        bundle, entry_findings = _parse_instance(entry, index)
        question_id = bundle.mechanism.question_id
        if question_id in identifiers:
            raise EC001Error(f"Duplicate question_id: {question_id}")
        identifiers.add(question_id)
        bundles.append(bundle)
        findings.extend(entry_findings)

    return LoadedDataset(
        source_sha256=observed_sha256,
        instances=tuple(bundles),
        annotation_findings=tuple(findings),
        adaptation_stats=_adaptation_stats(bundles),
    )


def _parse_instance(
    entry: object,
    index: int,
) -> tuple[InstanceBundle, list[dict]]:
    if not isinstance(entry, dict):
        raise EC001Error(f"Question {index} is not an object")
    required = {
        "question_id",
        "question_type",
        "question",
        "answer",
        "question_date",
        "haystack_session_ids",
        "haystack_dates",
        "haystack_sessions",
        "answer_session_ids",
    }
    missing = sorted(required - set(entry))
    if missing:
        raise EC001Error(f"Question {index} is missing fields: {missing}")

    question_id = _required_text(entry["question_id"], "question_id", index)
    question_type = _required_text(
        entry["question_type"], "question_type", index
    )
    if question_type not in QUESTION_TYPES:
        raise EC001Error(
            f"{question_id}: unsupported question_type {question_type!r}"
        )
    question = _required_text(entry["question"], "question", index)
    question_date = _required_text(
        entry["question_date"], "question_date", index
    )
    _parse_timestamp(question_date, f"{question_id}: question_date")

    raw_session_ids = _text_list(
        entry["haystack_session_ids"],
        f"{question_id}: haystack_session_ids",
    )
    session_dates = _text_list(
        entry["haystack_dates"],
        f"{question_id}: haystack_dates",
    )
    sessions = entry["haystack_sessions"]
    if not isinstance(sessions, list):
        raise EC001Error(f"{question_id}: haystack_sessions must be a list")
    if not (len(raw_session_ids) == len(session_dates) == len(sessions)):
        raise EC001Error(
            f"{question_id}: parallel haystack arrays differ in length"
        )
    if not raw_session_ids:
        raise EC001Error(f"{question_id}: empty history")
    session_ids = tuple(
        _session_occurrence_key(raw_session_id, position)
        for position, raw_session_id in enumerate(raw_session_ids)
    )
    duplicate_raw_ids = {
        raw_session_id
        for raw_session_id, count in Counter(raw_session_ids).items()
        if count > 1
    }

    parsed_dates = [
        _parse_timestamp(value, f"{question_id}: haystack_dates")
        for value in session_dates
    ]
    answer_session_ids = _text_list(
        entry["answer_session_ids"],
        f"{question_id}: answer_session_ids",
    )
    unknown_answers = sorted(
        set(answer_session_ids) - set(raw_session_ids)
    )
    if unknown_answers:
        raise EC001Error(
            f"{question_id}: evidence sessions absent from history: "
            f"{unknown_answers}"
        )
    ambiguous_answers = sorted(
        set(answer_session_ids) & duplicate_raw_ids
    )
    if ambiguous_answers:
        raise EC001Error(
            f"{question_id}: duplicated raw evidence session ids are "
            f"ambiguous: {ambiguous_answers}"
        )
    raw_to_key = {
        raw_session_id: session_key
        for raw_session_id, session_key in zip(
            raw_session_ids,
            session_ids,
            strict=True,
        )
    }
    answer_session_keys = tuple(
        raw_to_key[raw_session_id]
        for raw_session_id in answer_session_ids
    )

    episodes: list[EpisodeInput] = []
    episode_session_ids: list[str] = []
    evidence_turns: list[EvidenceTurn] = []
    source_turns: list[SourceTurn] = []
    irregular_session_ids: list[str] = []
    singleton_episode_turn_numbers: list[int] = []
    for session_id, raw_session_id, session in zip(
        session_ids,
        raw_session_ids,
        sessions,
        strict=True,
    ):
        if not isinstance(session, list) or not session:
            raise EC001Error(f"{question_id}/{session_id}: empty session")
        parsed_session = [
            _parse_turn(
                turn,
                location=f"{question_id}/{session_id}/{turn_index}",
            )
            for turn_index, turn in enumerate(session)
        ]
        strict_pairs = (
            len(parsed_session) % 2 == 0
            and all(
                (
                    parsed_session[pair_index]["role"],
                    parsed_session[pair_index + 1]["role"],
                )
                == ("user", "assistant")
                for pair_index in range(0, len(parsed_session), 2)
            )
        )
        if not strict_pairs:
            irregular_session_ids.append(session_id)

        expected_source = [
            (turn["role"], turn["content"]) for turn in parsed_session
        ]
        reconstructed_source: list[tuple[str, str]] = []
        source_index = 0
        while source_index < len(parsed_session):
            first = parsed_session[source_index]
            if (
                first["role"] == "user"
                and source_index + 1 < len(parsed_session)
                and parsed_session[source_index + 1]["role"] == "assistant"
            ):
                adapted_turns = (
                    (source_index, first),
                    (source_index + 1, parsed_session[source_index + 1]),
                )
                source_index += 2
            else:
                adapted_turns = ((source_index, first),)
                source_index += 1

            turn_number = len(episodes) + 1
            user_message = next(
                (
                    turn["content"]
                    for _index, turn in adapted_turns
                    if turn["role"] == "user"
                ),
                "",
            )
            assistant_message = next(
                (
                    turn["content"]
                    for _index, turn in adapted_turns
                    if turn["role"] == "assistant"
                ),
                "",
            )
            episodes.append(
                EpisodeInput(
                    turn_number=turn_number,
                    user_message=user_message,
                    assistant_message=assistant_message,
                )
            )
            episode_session_ids.append(session_id)
            if len(adapted_turns) == 1:
                singleton_episode_turn_numbers.append(turn_number)
            for session_turn_index, turn in adapted_turns:
                reconstructed_source.append((turn["role"], turn["content"]))
                source_turns.append(
                    SourceTurn(
                        session_id=session_id,
                        session_turn_index=session_turn_index,
                        episode_turn_number=turn_number,
                        role=turn["role"],
                        content=turn["content"],
                        raw_session_id=raw_session_id,
                    )
                )
                if turn["has_answer"]:
                    evidence_turns.append(
                        EvidenceTurn(
                            session_id=session_id,
                            episode_turn_number=turn_number,
                            role=turn["role"],
                            content=turn["content"],
                            raw_session_id=raw_session_id,
                        )
                    )
        if reconstructed_source != expected_source:
            raise EC001Error(
                f"{question_id}/{session_id}: lossless turn adaptation failed"
            )

    mechanism = MechanismInstance(
        question_id=question_id,
        question=question,
        episodes=tuple(episodes),
    )
    measurement = MeasurementInstance(
        question_id=question_id,
        question_type=question_type,
        is_abstention=question_id.endswith("_abs"),
        question_date=question_date,
        session_ids=tuple(session_ids),
        session_dates=tuple(session_dates),
        episode_session_ids=tuple(episode_session_ids),
        answer_session_ids=tuple(answer_session_ids),
        evidence_turns=tuple(evidence_turns),
        raw_session_ids=tuple(raw_session_ids),
        answer_session_keys=answer_session_keys,
        source_turns=tuple(source_turns),
        irregular_session_ids=tuple(irregular_session_ids),
        singleton_episode_turn_numbers=tuple(
            singleton_episode_turn_numbers
        ),
    )
    findings = annotation_findings(measurement)
    adjacent_inversions = sum(
        parsed_dates[position] < parsed_dates[position - 1]
        for position in range(1, len(parsed_dates))
    )
    if adjacent_inversions:
        findings.append(
            {
                "question_id": question_id,
                "kind": "nonchronological_session_timestamps",
                "adjacent_inversions": adjacent_inversions,
            }
        )
    question_timestamp = _parse_timestamp(question_date, question_id)
    post_question_positions = [
        position
        for position, timestamp in enumerate(parsed_dates)
        if timestamp >= question_timestamp
    ]
    if post_question_positions:
        post_keys = {
            session_ids[position] for position in post_question_positions
        }
        findings.append(
            {
                "question_id": question_id,
                "kind": "session_timestamp_not_before_question",
                "session_count": len(post_question_positions),
                "answer_session_count": len(
                    post_keys & set(answer_session_keys)
                ),
            }
        )
    return InstanceBundle(mechanism, measurement), findings


def _required_text(value: object, name: str, index: int) -> str:
    if not isinstance(value, str) or not value:
        raise EC001Error(f"Question {index}: {name} must be non-empty text")
    return value


def _text_list(value: object, location: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise EC001Error(f"{location} must be a list of non-empty strings")
    return list(value)


def _parse_timestamp(value: str, location: str) -> datetime:
    try:
        return datetime.strptime(value, TIMESTAMP_FORMAT)
    except ValueError as error:
        raise EC001Error(
            f"{location}: timestamp does not match {TIMESTAMP_FORMAT!r}: "
            f"{value!r}"
        ) from error


def _parse_turn(value: object, *, location: str) -> dict:
    if not isinstance(value, dict):
        raise EC001Error(f"{location}: turn must be an object")
    role = value.get("role")
    content = value.get("content")
    if role not in ("user", "assistant"):
        raise EC001Error(
            f"{location}: unsupported role {role!r}"
        )
    if not isinstance(content, str):
        raise EC001Error(f"{location}: content must be text")
    has_answer = value.get("has_answer", False)
    if not isinstance(has_answer, bool):
        raise EC001Error(f"{location}: has_answer must be boolean")
    return {
        "role": role,
        "content": content,
        "has_answer": has_answer,
    }


def _session_occurrence_key(raw_session_id: str, position: int) -> str:
    return f"{raw_session_id}::position={position}"


def _adaptation_stats(bundles: Sequence[InstanceBundle]) -> dict:
    source_turn_count = 0
    episode_count = 0
    paired_episode_count = 0
    singleton_user_count = 0
    singleton_assistant_count = 0
    irregular_session_count = 0
    irregular_question_count = 0
    duplicate_session_occurrences = 0
    duplicate_session_questions = 0
    empty_source_turns = 0
    for bundle in bundles:
        measurement = bundle.measurement
        source_turn_count += len(measurement.source_turns)
        episode_count += len(bundle.mechanism.episodes)
        irregular_session_count += len(measurement.irregular_session_ids)
        irregular_question_count += bool(measurement.irregular_session_ids)
        raw_session_ids = measurement.raw_session_ids
        duplicates = len(raw_session_ids) - len(set(raw_session_ids))
        duplicate_session_occurrences += duplicates
        duplicate_session_questions += bool(duplicates)
        empty_source_turns += sum(
            source_turn.content == ""
            for source_turn in measurement.source_turns
        )
        source_turns_by_episode = Counter(
            source_turn.episode_turn_number
            for source_turn in measurement.source_turns
        )
        roles_by_episode: dict[int, set[str]] = defaultdict(set)
        for source_turn in measurement.source_turns:
            roles_by_episode[source_turn.episode_turn_number].add(
                source_turn.role
            )
        for episode in bundle.mechanism.episodes:
            source_count = source_turns_by_episode[episode.turn_number]
            roles = roles_by_episode[episode.turn_number]
            if source_count == 2 and roles == {"user", "assistant"}:
                paired_episode_count += 1
            elif source_count == 1 and roles == {"user"}:
                singleton_user_count += 1
            elif source_count == 1 and roles == {"assistant"}:
                singleton_assistant_count += 1
            else:
                raise EC001Error(
                    "Adaptation produced an invalid episode provenance group"
                )
    reconstructed_turn_count = (
        paired_episode_count * 2
        + singleton_user_count
        + singleton_assistant_count
    )
    if reconstructed_turn_count != source_turn_count:
        raise EC001Error(
            "Dataset-level lossless adaptation turn count failed"
        )
    return {
        "source_turns": source_turn_count,
        "episodes": episode_count,
        "paired_episodes": paired_episode_count,
        "singleton_user_episodes": singleton_user_count,
        "singleton_assistant_episodes": singleton_assistant_count,
        "irregular_session_instances": irregular_session_count,
        "questions_with_irregular_sessions": irregular_question_count,
        "duplicate_session_occurrences": duplicate_session_occurrences,
        "questions_with_duplicate_session_ids": duplicate_session_questions,
        "empty_source_turns": empty_source_turns,
        "lossless_turn_count": reconstructed_turn_count,
        "status": "PASS",
        "amendment_shas": [
            AMENDMENT_001_SHA,
            AMENDMENT_002_SHA,
            AMENDMENT_003_SHA,
        ],
    }


def annotation_findings(measurement: MeasurementInstance) -> list[dict]:
    """Mechanically audit evidence availability without changing the corpus."""

    findings: list[dict] = []
    answer_sessions = set(
        measurement.answer_session_keys
        if measurement.answer_session_keys
        else measurement.answer_session_ids
    )
    evidence_sessions = {turn.session_id for turn in measurement.evidence_turns}
    if measurement.is_abstention:
        if answer_sessions:
            findings.append(
                {
                    "question_id": measurement.question_id,
                    "kind": "abstention_has_answer_session",
                    "session_ids": sorted(answer_sessions),
                }
            )
        if evidence_sessions:
            findings.append(
                {
                    "question_id": measurement.question_id,
                    "kind": "abstention_has_answer_turn",
                    "session_ids": sorted(evidence_sessions),
                }
            )
        return findings

    if not answer_sessions:
        findings.append(
            {
                "question_id": measurement.question_id,
                "kind": "answerable_missing_answer_session",
            }
        )
    if not evidence_sessions:
        findings.append(
            {
                "question_id": measurement.question_id,
                "kind": "answerable_missing_answer_turn",
            }
        )
    missing_turn_labels = sorted(answer_sessions - evidence_sessions)
    if missing_turn_labels:
        findings.append(
            {
                "question_id": measurement.question_id,
                "kind": "answer_session_without_answer_turn",
                "session_ids": missing_turn_labels,
            }
        )
    unexpected_turn_labels = sorted(evidence_sessions - answer_sessions)
    if unexpected_turn_labels:
        findings.append(
            {
                "question_id": measurement.question_id,
                "kind": "answer_turn_outside_answer_session",
                "session_ids": unexpected_turn_labels,
            }
        )
    return findings


def turn_label_complete(measurement: MeasurementInstance) -> bool | None:
    """Whether every named answer session has a marked evidence turn."""

    if measurement.is_abstention:
        return None
    answer_sessions = set(
        measurement.answer_session_keys
        if measurement.answer_session_keys
        else measurement.answer_session_ids
    )
    evidence_sessions = {turn.session_id for turn in measurement.evidence_turns}
    return bool(answer_sessions) and answer_sessions <= evidence_sessions


def build_instrument_audit_registration(dataset: LoadedDataset) -> dict:
    """Build the measurement-only audit that must be locked before Tier 1."""

    incomplete: list[dict] = []
    for bundle in dataset.instances:
        measurement = bundle.measurement
        if measurement.is_abstention or turn_label_complete(measurement):
            continue
        answer_sessions = set(measurement.answer_session_keys)
        marked_sessions = {
            turn.session_id for turn in measurement.evidence_turns
        }
        missing_keys = sorted(answer_sessions - marked_sessions)
        raw_by_key = dict(
            zip(
                measurement.session_ids,
                measurement.raw_session_ids,
                strict=True,
            )
        )
        incomplete.append(
            {
                "question_id": measurement.question_id,
                "question_type": measurement.question_type,
                "answer_session_keys_without_turn_label": missing_keys,
                "raw_answer_session_ids_without_turn_label": [
                    raw_by_key[key] for key in missing_keys
                ],
                "marked_evidence_turn_count": len(
                    measurement.evidence_turns
                ),
            }
        )

    finding_counts = Counter(
        finding["kind"] for finding in dataset.annotation_findings
    )
    return {
        "record": "EC-001 pre-retrieval instrument audit",
        "registration_sha": REGISTRATION_SHA,
        "adaptation_sha": ADAPTATION_SHA,
        "amendment_shas": [
            AMENDMENT_001_SHA,
            AMENDMENT_002_SHA,
            AMENDMENT_003_SHA,
        ],
        "dataset_sha256": dataset.source_sha256,
        "tier_1_results_consulted": False,
        "question_count": len(dataset.instances),
        "finding_counts": dict(sorted(finding_counts.items())),
        "foreign_store_adaptation": dataset.adaptation_stats,
        "incomplete_turn_label_question_count": len(incomplete),
        "incomplete_turn_label_session_count": sum(
            len(row["answer_session_keys_without_turn_label"])
            for row in incomplete
        ),
        "incomplete_turn_labels": incomplete,
        "interpretation": {
            "marker_availability": (
                "Exact delivery of all source turns marked has_answer; not "
                "complete factual availability when turn_label_complete is "
                "false."
            ),
            "exact_gap": (
                "NOT_EVALUABLE where turn_label_complete is false."
            ),
            "session_recall": (
                "Retained as session identity only; it is not fact presence."
            ),
        },
    }


def stratum_for(measurement: MeasurementInstance) -> str:
    return measurement.stratum


def build_subset_manifest(
    dataset: LoadedDataset,
    quotas: Mapping[str, int],
    *,
    seed: int,
) -> dict:
    """Select only from ids/types, before any retrieval result can exist."""

    normalized = {str(key): int(value) for key, value in quotas.items()}
    if set(normalized) != set(EXPECTED_STRATA):
        raise EC001Error(
            "Subset quotas must name exactly these strata: "
            f"{list(EXPECTED_STRATA)}"
        )
    if any(value < 1 for value in normalized.values()):
        raise EC001Error("Every Tier 2 stratum quota must be positive")

    by_stratum: dict[str, list[str]] = defaultdict(list)
    for bundle in dataset.instances:
        by_stratum[stratum_for(bundle.measurement)].append(
            bundle.mechanism.question_id
        )

    selected: list[str] = []
    selected_by_stratum: dict[str, list[str]] = {}
    for stratum in EXPECTED_STRATA:
        available = sorted(by_stratum[stratum])
        quota = normalized[stratum]
        if quota > len(available):
            raise EC001Error(
                f"Quota {quota} exceeds {len(available)} for {stratum}"
            )
        ranked = sorted(
            available,
            key=lambda question_id: (
                hashlib.sha256(
                    f"{seed}\0{stratum}\0{question_id}".encode("utf-8")
                ).hexdigest(),
                question_id,
            ),
        )
        chosen = ranked[:quota]
        selected_by_stratum[stratum] = chosen
        selected.extend(chosen)

    return {
        "record": "EC-001 Tier 2 subset registration",
        "registration_sha": REGISTRATION_SHA,
        "adaptation_sha": ADAPTATION_SHA,
        "amendment_shas": [
            AMENDMENT_001_SHA,
            AMENDMENT_002_SHA,
            AMENDMENT_003_SHA,
        ],
        "dataset_sha256": dataset.source_sha256,
        "selection_inputs": [
            "question_id",
            "question_type",
            "question_id suffix _abs",
        ],
        "selection_algorithm": (
            "Per stratum, sort by SHA256(seed NUL stratum NUL question_id), "
            "then take the registered quota."
        ),
        "seed": seed,
        "quotas": {key: normalized[key] for key in EXPECTED_STRATA},
        "question_ids_by_stratum": selected_by_stratum,
        "question_ids": selected,
        "size": len(selected),
        "tier_1_results_consulted": False,
        "benchmark_population_counts": {
            stratum: len(by_stratum[stratum])
            for stratum in EXPECTED_STRATA
        },
        "aggregate_reporting": {
            "raw_subset_micro_average": (
                "Report and label as non-benchmark-distributed when quotas "
                "are not proportional."
            ),
            "benchmark_population_weighted_average": (
                "Post-stratify per-stratum accuracy by the verified full "
                "dataset population counts."
            ),
            "per_stratum": "Always report all seven strata.",
        },
    }


def validate_subset_manifest(
    manifest: Mapping[str, object],
    dataset: LoadedDataset,
) -> tuple[str, ...]:
    if manifest.get("registration_sha") != REGISTRATION_SHA:
        raise EC001Error("Tier 2 subset has the wrong registration anchor")
    if manifest.get("adaptation_sha") != ADAPTATION_SHA:
        raise EC001Error("Tier 2 subset predates the locked adaptation record")
    if manifest.get("amendment_shas") != [
        AMENDMENT_001_SHA,
        AMENDMENT_002_SHA,
        AMENDMENT_003_SHA,
    ]:
        raise EC001Error("Tier 2 subset predates a binding amendment")
    if manifest.get("dataset_sha256") != dataset.source_sha256:
        raise EC001Error("Tier 2 subset was selected from a different dataset")
    if manifest.get("tier_1_results_consulted") is not False:
        raise EC001Error("Tier 2 subset does not certify pre-result selection")

    forbidden_fragments = ("recall", "rank", "metric", "score", "result")
    permitted_result_key = "tier_1_results_consulted"
    for key in _all_keys(manifest):
        folded = key.casefold()
        if key != permitted_result_key and any(
            fragment in folded for fragment in forbidden_fragments
        ):
            raise EC001Error(
                f"Tier 2 subset contains a result-shaped field: {key}"
            )

    quotas = manifest.get("quotas")
    if not isinstance(quotas, dict):
        raise EC001Error("Tier 2 subset quotas are missing")
    normalized_quotas = {str(key): int(value) for key, value in quotas.items()}
    if set(normalized_quotas) != set(EXPECTED_STRATA):
        raise EC001Error("Tier 2 subset quotas do not cover every stratum")
    if any(value < 1 for value in normalized_quotas.values()):
        raise EC001Error("Tier 2 subset has a non-positive stratum quota")

    question_ids = manifest.get("question_ids")
    if not isinstance(question_ids, list) or any(
        not isinstance(value, str) for value in question_ids
    ):
        raise EC001Error("Tier 2 subset question_ids must be a string list")
    if len(set(question_ids)) != len(question_ids):
        raise EC001Error("Tier 2 subset contains duplicate question ids")
    if manifest.get("size") != len(question_ids):
        raise EC001Error("Tier 2 subset size does not match its id list")

    dataset_by_id = dataset.by_id
    unknown = sorted(set(question_ids) - set(dataset_by_id))
    if unknown:
        raise EC001Error(f"Tier 2 subset contains unknown ids: {unknown}")
    observed = Counter(
        stratum_for(dataset_by_id[question_id].measurement)
        for question_id in question_ids
    )
    if dict(observed) != normalized_quotas:
        raise EC001Error(
            f"Tier 2 subset stratum counts {dict(observed)} do not match "
            f"quotas {normalized_quotas}"
        )
    expected_population = Counter(
        stratum_for(bundle.measurement) for bundle in dataset.instances
    )
    if manifest.get("benchmark_population_counts") != {
        stratum: expected_population[stratum]
        for stratum in EXPECTED_STRATA
    }:
        raise EC001Error(
            "Tier 2 subset has incorrect benchmark population weights"
        )

    selected_findings = [
        finding
        for finding in dataset.annotation_findings
        if finding["question_id"] in set(question_ids)
        and finding["kind"] in {
            "answerable_missing_answer_session",
            "answerable_missing_answer_turn",
        }
    ]
    if selected_findings:
        raise EC001Error(
            "Tier 2 subset contains mechanically unavailable "
            f"evidence: {selected_findings}"
        )
    return tuple(question_ids)


def _all_keys(value: object) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from _all_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _all_keys(child)


def session_cosine_ranking(
    mechanism: MechanismInstance,
    measurement: MeasurementInstance,
    embedder,
) -> list[dict]:
    """Rank sessions by their best constituent episode cosine."""

    if len(mechanism.episodes) != len(measurement.episode_session_ids):
        raise EC001Error("Mechanism/measurement episode count mismatch")
    query = _unit_vector(embedder(mechanism.question))
    session_scores: dict[str, float] = {}
    for episode, session_id in zip(
        mechanism.episodes,
        measurement.episode_session_ids,
        strict=True,
    ):
        cosine = float(np.dot(query, _unit_vector(embedder(episode.embedded_text))))
        session_scores[session_id] = max(
            cosine,
            session_scores.get(session_id, float("-inf")),
        )
    session_positions = {
        session_id: position
        for position, session_id in enumerate(measurement.session_ids)
    }
    ordered = sorted(
        session_scores,
        key=lambda session_id: (
            -session_scores[session_id],
            session_positions[session_id],
            session_id,
        ),
    )
    return [
        {
            "rank": rank,
            "session_id": session_id,
            "cosine": round(session_scores[session_id], 9),
        }
        for rank, session_id in enumerate(ordered, 1)
    ]


def _unit_vector(value: object) -> np.ndarray:
    vector = np.asarray(value, dtype=np.float32)
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm else vector


def parse_delivered_block(block: str) -> dict[int, dict[str, str]]:
    """Parse the public serialized block; no store internals are inspected."""

    if not block:
        return {}
    try:
        root = ET.fromstring(f"<ec001_root>{block}</ec001_root>")
    except ET.ParseError as error:
        raise EC001Error(f"episodic returned malformed XML: {error}") from error

    delivered: dict[int, dict[str, str]] = {}
    for element in root.findall(".//episode"):
        turn_text = element.attrib.get("turn")
        try:
            turn_number = int(turn_text or "")
        except ValueError as error:
            raise EC001Error(
                f"episodic returned invalid turn attribute: {turn_text!r}"
            ) from error
        if turn_number in delivered:
            raise EC001Error(f"episodic delivered turn {turn_number} twice")
        user = element.find("user")
        assistant = element.find("assistant")
        if user is None or assistant is None:
            raise EC001Error("episodic returned an incomplete episode element")
        delivered[turn_number] = {
            "user": user.text or "",
            "assistant": assistant.text or "",
        }
    return delivered


def score_retrieval(
    measurement: MeasurementInstance,
    delivered: Mapping[int, Mapping[str, str]],
    session_ranking: Sequence[Mapping[str, object]],
) -> dict:
    """Join already-produced retrieval with held-out measurement labels."""

    delivered_turns = set(delivered)
    delivered_sessions = {
        measurement.episode_session_ids[turn_number - 1]
        for turn_number in delivered_turns
    }
    if measurement.is_abstention:
        return {
            "evidence_session_recall_any": None,
            "evidence_session_recall_all": None,
            "marker_availability_any": None,
            "marker_availability_all": None,
            "availability_any": None,
            "availability_all": None,
            "turn_label_complete": None,
            "exact_gap_evaluable": False,
            "evidence_session_ranks": [],
            "deepest_evidence_rank": None,
            "top_4_no_evidence": None,
            "component_abstention_signal": False,
            "delivered_episode_count": len(delivered_turns),
        }

    answer_sessions = set(
        measurement.answer_session_keys
        if measurement.answer_session_keys
        else measurement.answer_session_ids
    )
    recall_any = bool(delivered_sessions & answer_sessions)
    recall_all = answer_sessions <= delivered_sessions
    evidence_presence = [
        (
            turn.episode_turn_number in delivered
            and delivered[turn.episode_turn_number].get(turn.role) == turn.content
        )
        for turn in measurement.evidence_turns
    ]
    marker_availability_any = (
        any(evidence_presence) if evidence_presence else None
    )
    marker_availability_all = (
        all(evidence_presence) if evidence_presence else None
    )
    labels_complete = turn_label_complete(measurement)

    rank_by_session = {
        str(row["session_id"]): int(row["rank"]) for row in session_ranking
    }
    evidence_ranks = sorted(
        rank_by_session[session_id]
        for session_id in answer_sessions
        if session_id in rank_by_session
    )
    top_four = {
        str(row["session_id"])
        for row in session_ranking
        if int(row["rank"]) <= 4
    }
    return {
        "evidence_session_recall_any": recall_any,
        "evidence_session_recall_all": recall_all,
        "marker_availability_any": marker_availability_any,
        "marker_availability_all": marker_availability_all,
        "availability_any": marker_availability_any,
        "availability_all": marker_availability_all,
        "turn_label_complete": labels_complete,
        "exact_gap_evaluable": labels_complete is True,
        "evidence_session_ranks": evidence_ranks,
        "deepest_evidence_rank": max(evidence_ranks) if evidence_ranks else None,
        "top_4_no_evidence": not bool(top_four & answer_sessions),
        "component_abstention_signal": False,
        "delivered_episode_count": len(delivered_turns),
    }


def retrieve_tier1_instance(
    bundle: InstanceBundle,
    *,
    store_path: Path,
    embedder,
    budget_chars: int,
) -> tuple[dict, dict]:
    """Run unchanged ``episodic`` retrieval, then score outside the mechanism."""

    mechanism = bundle.mechanism
    measurement = bundle.measurement
    block, report = retrieve_block(
        mechanism,
        store_path=store_path,
        embedder=embedder,
        budget_chars=budget_chars,
    )

    delivered = parse_delivered_block(block)
    ranking = session_cosine_ranking(mechanism, measurement, embedder)
    scores = {
        "question_id": mechanism.question_id,
        "question_type": measurement.question_type,
        "stratum": measurement.stratum,
        **score_retrieval(measurement, delivered, ranking),
    }
    mechanism_log = {
        "question_id": mechanism.question_id,
        "block": block,
        "block_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
        "report": asdict(report),
        "delivered_turn_numbers": sorted(delivered),
        "session_cosine_ranking": ranking,
        "determinism_rerun": "PASS",
    }
    return scores, mechanism_log


def retrieve_block(
    mechanism: MechanismInstance,
    *,
    store_path: Path,
    embedder,
    budget_chars: int,
):
    """Mechanism boundary: this function cannot receive reference labels."""

    from episodic import EpisodeStore, EpisodicConfig

    if store_path.exists():
        raise EC001Error(f"Refusing to overwrite store: {store_path}")

    config = EpisodicConfig()
    with EpisodeStore(store_path, config=config, embedder=embedder) as store:
        for episode in mechanism.episodes:
            store.append("user", episode.user_message)
            store.append("assistant", episode.assistant_message)
        block, report = store.context(mechanism.question, budget_chars)
        prefix_block, prefix_report = store.context(
            mechanism.question,
            budget_chars,
        )

    if block != prefix_block:
        raise EC001Error(
            f"{mechanism.question_id}: byte-identical retrieval rerun failed"
        )
    report_values = asdict(report)
    prefix_values = asdict(prefix_report)
    report_values.pop("latency_ms", None)
    prefix_values.pop("latency_ms", None)
    if report_values != prefix_values:
        raise EC001Error(
            f"{mechanism.question_id}: retrieval report rerun drifted"
        )
    return block, report


def aggregate_tier1(rows: Sequence[Mapping[str, object]]) -> dict:
    """Aggregate only registered Tier 1 measurements."""

    groups: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        groups["all"].append(row)
        groups[str(row["stratum"])].append(row)

    return {
        "question_count": len(rows),
        "by_stratum": {
            stratum: _aggregate_group(group)
            for stratum, group in sorted(groups.items())
        },
        "availability_definition": (
            "Compatibility alias for marker_availability: exact has_answer "
            "turn content present in a delivered episode"
        ),
        "marker_availability_limitation": (
            "Does not certify complete factual availability when "
            "turn_label_complete is false"
        ),
        "abstention_retrieval_metrics": None,
    }


def _aggregate_group(rows: Sequence[Mapping[str, object]]) -> dict:
    def rate(field: str) -> dict | None:
        values = [row[field] for row in rows if row.get(field) is not None]
        if not values:
            return None
        successes = sum(bool(value) for value in values)
        return {
            "successes": successes,
            "denominator": len(values),
            "rate": successes / len(values),
        }

    ranks = [
        int(rank)
        for row in rows
        for rank in row.get("evidence_session_ranks", [])
    ]
    deepest = [
        int(row["deepest_evidence_rank"])
        for row in rows
        if row.get("deepest_evidence_rank") is not None
    ]
    return {
        "questions": len(rows),
        "evidence_session_recall_any": rate("evidence_session_recall_any"),
        "evidence_session_recall_all": rate("evidence_session_recall_all"),
        "marker_availability_any": rate("marker_availability_any"),
        "marker_availability_all": rate("marker_availability_all"),
        "availability_any": rate("availability_any"),
        "availability_all": rate("availability_all"),
        "turn_label_complete": rate("turn_label_complete"),
        "exact_gap_evaluable_count": sum(
            row.get("exact_gap_evaluable") is True for row in rows
        ),
        "top_4_no_evidence": rate("top_4_no_evidence"),
        "evidence_rank_distribution": sorted(ranks),
        "deepest_evidence_rank_required": max(deepest) if deepest else None,
    }


def mechanism_surface_fields() -> tuple[str, ...]:
    """Exposed for the planted leakage test."""

    return tuple(field.name for field in fields(MechanismInstance))

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

REGISTRATION_SHA = "b595b05e1469c67277844d4bd97f77c89a20772b"
ADAPTATION_SHA = "a65c2566e55a2063bd1904065032f86c5d0e23a9"
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
    for anchor in (REGISTRATION_SHA, ADAPTATION_SHA):
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

    session_ids = _text_list(
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
    if not (len(session_ids) == len(session_dates) == len(sessions)):
        raise EC001Error(
            f"{question_id}: parallel haystack arrays differ in length"
        )
    if len(set(session_ids)) != len(session_ids):
        raise EC001Error(f"{question_id}: duplicate session ids")
    if not session_ids:
        raise EC001Error(f"{question_id}: empty history")

    parsed_dates = [
        _parse_timestamp(value, f"{question_id}: haystack_dates")
        for value in session_dates
    ]
    if parsed_dates != sorted(parsed_dates):
        raise EC001Error(f"{question_id}: sessions are not chronological")

    answer_session_ids = _text_list(
        entry["answer_session_ids"],
        f"{question_id}: answer_session_ids",
    )
    unknown_answers = sorted(set(answer_session_ids) - set(session_ids))
    if unknown_answers:
        raise EC001Error(
            f"{question_id}: evidence sessions absent from history: "
            f"{unknown_answers}"
        )

    episodes: list[EpisodeInput] = []
    episode_session_ids: list[str] = []
    evidence_turns: list[EvidenceTurn] = []
    for session_id, session in zip(session_ids, sessions, strict=True):
        if not isinstance(session, list) or not session:
            raise EC001Error(f"{question_id}/{session_id}: empty session")
        if len(session) % 2:
            raise EC001Error(
                f"{question_id}/{session_id}: session does not contain "
                "complete user/assistant exchanges"
            )
        for start in range(0, len(session), 2):
            user = _parse_turn(
                session[start],
                expected_role="user",
                location=f"{question_id}/{session_id}/{start}",
            )
            assistant = _parse_turn(
                session[start + 1],
                expected_role="assistant",
                location=f"{question_id}/{session_id}/{start + 1}",
            )
            turn_number = len(episodes) + 1
            episodes.append(
                EpisodeInput(
                    turn_number=turn_number,
                    user_message=user["content"],
                    assistant_message=assistant["content"],
                )
            )
            episode_session_ids.append(session_id)
            for turn in (user, assistant):
                if turn["has_answer"]:
                    evidence_turns.append(
                        EvidenceTurn(
                            session_id=session_id,
                            episode_turn_number=turn_number,
                            role=turn["role"],
                            content=turn["content"],
                        )
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
    )
    findings = annotation_findings(measurement)
    if any(value >= _parse_timestamp(question_date, question_id)
           for value in parsed_dates):
        findings.append(
            {
                "question_id": question_id,
                "kind": "session_not_strictly_before_question",
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


def _parse_turn(
    value: object,
    *,
    expected_role: str,
    location: str,
) -> dict:
    if not isinstance(value, dict):
        raise EC001Error(f"{location}: turn must be an object")
    role = value.get("role")
    content = value.get("content")
    if role != expected_role:
        raise EC001Error(
            f"{location}: expected role {expected_role!r}, found {role!r}"
        )
    if not isinstance(content, str) or not content:
        raise EC001Error(f"{location}: content must be non-empty text")
    has_answer = value.get("has_answer", False)
    if not isinstance(has_answer, bool):
        raise EC001Error(f"{location}: has_answer must be boolean")
    return {
        "role": role,
        "content": content,
        "has_answer": has_answer,
    }


def annotation_findings(measurement: MeasurementInstance) -> list[dict]:
    """Mechanically audit evidence availability without changing the corpus."""

    findings: list[dict] = []
    answer_sessions = set(measurement.answer_session_ids)
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
    }


def validate_subset_manifest(
    manifest: Mapping[str, object],
    dataset: LoadedDataset,
) -> tuple[str, ...]:
    if manifest.get("registration_sha") != REGISTRATION_SHA:
        raise EC001Error("Tier 2 subset has the wrong registration anchor")
    if manifest.get("adaptation_sha") != ADAPTATION_SHA:
        raise EC001Error("Tier 2 subset predates the locked adaptation record")
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

    selected_findings = [
        finding
        for finding in dataset.annotation_findings
        if finding["question_id"] in set(question_ids)
        and finding["kind"] in {
            "answerable_missing_answer_session",
            "answerable_missing_answer_turn",
            "answer_session_without_answer_turn",
            "session_not_strictly_before_question",
        }
    ]
    if selected_findings:
        raise EC001Error(
            "Tier 2 subset contains mechanically unavailable or post-probe "
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
            "availability_any": None,
            "availability_all": None,
            "evidence_session_ranks": [],
            "deepest_evidence_rank": None,
            "top_4_no_evidence": None,
            "component_abstention_signal": False,
            "delivered_episode_count": len(delivered_turns),
        }

    answer_sessions = set(measurement.answer_session_ids)
    recall_any = bool(delivered_sessions & answer_sessions)
    recall_all = answer_sessions <= delivered_sessions
    evidence_presence = [
        (
            turn.episode_turn_number in delivered
            and delivered[turn.episode_turn_number].get(turn.role) == turn.content
        )
        for turn in measurement.evidence_turns
    ]
    availability_any = any(evidence_presence) if evidence_presence else None
    availability_all = all(evidence_presence) if evidence_presence else None

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
        "availability_any": availability_any,
        "availability_all": availability_all,
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
            "Exact has_answer turn content present in a delivered episode"
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
        "availability_any": rate("availability_any"),
        "availability_all": rate("availability_all"),
        "top_4_no_evidence": rate("top_4_no_evidence"),
        "evidence_rank_distribution": sorted(ranks),
        "deepest_evidence_rank_required": max(deepest) if deepest else None,
    }


def mechanism_surface_fields() -> tuple[str, ...]:
    """Exposed for the planted leakage test."""

    return tuple(field.name for field in fields(MechanismInstance))

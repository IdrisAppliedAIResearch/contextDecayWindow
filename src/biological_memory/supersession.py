from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


class SupersessionError(RuntimeError):
    pass


def content_sha256(user: str, assistant: str) -> str:
    payload = json.dumps(
        [["user", user], ["assistant", assistant]],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class LineageRecord:
    episode_sha256: str
    memory_key: str
    version: int
    supersedes: str | None
    superseded_by: str | None
    accessibility: float


class SupersessionLedger:
    """Explicit old-to-new lineage with a separate natural-retrieval gate."""

    def __init__(self) -> None:
        self._records: dict[str, LineageRecord] = {}
        self._versions: dict[str, list[str]] = {}

    def register_initial(self, memory_key: str, episode_sha256: str) -> None:
        self._validate_identity(memory_key, episode_sha256)
        if memory_key in self._versions:
            raise SupersessionError(f"Memory key already exists: {memory_key}")
        self._records[episode_sha256] = LineageRecord(
            episode_sha256=episode_sha256,
            memory_key=memory_key,
            version=1,
            supersedes=None,
            superseded_by=None,
            accessibility=1.0,
        )
        self._versions[memory_key] = [episode_sha256]

    def register_update(
        self,
        memory_key: str,
        episode_sha256: str,
        *,
        supersedes: str,
    ) -> None:
        self._validate_identity(memory_key, episode_sha256)
        if episode_sha256 in self._records:
            raise SupersessionError("Episode content identity is already registered")
        if memory_key not in self._versions:
            raise SupersessionError(f"Unknown memory key: {memory_key}")
        parent = self._records.get(supersedes)
        if parent is None:
            raise SupersessionError("Unknown supersedes parent")
        if parent.memory_key != memory_key:
            raise SupersessionError("Cross-key supersession is prohibited")
        current_sha = self._versions[memory_key][-1]
        if supersedes != current_sha or parent.superseded_by is not None:
            raise SupersessionError("Updates must supersede the unique current leaf")
        if parent.accessibility != 1.0:
            raise SupersessionError("Current parent must be naturally accessible")

        updated_parent = LineageRecord(
            **{
                **asdict(parent),
                "superseded_by": episode_sha256,
                "accessibility": 0.0,
            }
        )
        child = LineageRecord(
            episode_sha256=episode_sha256,
            memory_key=memory_key,
            version=parent.version + 1,
            supersedes=parent.episode_sha256,
            superseded_by=None,
            accessibility=1.0,
        )
        self._records[parent.episode_sha256] = updated_parent
        self._records[episode_sha256] = child
        self._versions[memory_key].append(episode_sha256)
        self.validate()

    def accessibility(self, episode_sha256: str) -> float:
        record = self._records.get(episode_sha256)
        return 1.0 if record is None else record.accessibility

    def lineage(self, memory_key: str) -> tuple[LineageRecord, ...]:
        try:
            identities = self._versions[memory_key]
        except KeyError as error:
            raise SupersessionError(f"Unknown memory key: {memory_key}") from error
        return tuple(self._records[identity] for identity in identities)

    def natural_rank(
        self,
        candidates: Iterable[Mapping[str, Any]],
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise SupersessionError("Natural retrieval limit must be positive")
        accessible = []
        seen: set[str] = set()
        for candidate in candidates:
            identity = str(candidate["episode_sha256"])
            if identity in seen:
                raise SupersessionError("Duplicate natural-retrieval candidate")
            seen.add(identity)
            access = self.accessibility(identity)
            if access == 0.0:
                continue
            if access != 1.0:
                raise SupersessionError("Accessibility must be binary in SUP-001")
            row = dict(candidate)
            row["accessibility"] = access
            row["natural_score"] = float(candidate["cosine"]) * access
            accessible.append(row)
        accessible.sort(
            key=lambda row: (
                -float(row["natural_score"]),
                str(row["episode_sha256"]),
            )
        )
        return accessible[:limit]

    def validate(self) -> dict[str, Any]:
        for key, identities in self._versions.items():
            if not identities:
                raise SupersessionError("Empty lineage")
            accessible = 0
            for index, identity in enumerate(identities):
                record = self._records.get(identity)
                if record is None or record.memory_key != key:
                    raise SupersessionError("Lineage identity/key mismatch")
                if record.version != index + 1:
                    raise SupersessionError("Lineage versions are not contiguous")
                expected_parent = identities[index - 1] if index else None
                expected_child = identities[index + 1] if index + 1 < len(identities) else None
                if record.supersedes != expected_parent or record.superseded_by != expected_child:
                    raise SupersessionError("Lineage links are not reciprocal and ordered")
                expected_access = 1.0 if expected_child is None else 0.0
                if record.accessibility != expected_access:
                    raise SupersessionError("Lineage does not have one accessible leaf")
                accessible += int(record.accessibility == 1.0)
            if accessible != 1:
                raise SupersessionError("Lineage must have exactly one accessible leaf")
        if set(self._records) != {
            identity for identities in self._versions.values() for identity in identities
        }:
            raise SupersessionError("Unreachable ledger record")
        return {
            "record_count": len(self._records),
            "lineage_count": len(self._versions),
            "accessible_count": len(self._versions),
            "silent_count": len(self._records) - len(self._versions),
        }

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema": "sup001-lineage-v1",
            "lineages": {
                key: [asdict(self._records[identity]) for identity in identities]
                for key, identities in sorted(self._versions.items())
            },
        }

    def save(self, path: Path) -> None:
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite lineage sidecar: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=True, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SupersessionLedger":
        if payload.get("schema") != "sup001-lineage-v1":
            raise SupersessionError("Unknown lineage sidecar schema")
        ledger = cls()
        lineages = payload.get("lineages")
        if not isinstance(lineages, Mapping):
            raise SupersessionError("Lineage sidecar is malformed")
        for key, rows in lineages.items():
            if not isinstance(rows, list) or not rows:
                raise SupersessionError("Serialized lineage is empty or malformed")
            identities = []
            for row in rows:
                record = LineageRecord(**row)
                if record.memory_key != key or record.episode_sha256 in ledger._records:
                    raise SupersessionError("Serialized lineage identity mismatch")
                ledger._records[record.episode_sha256] = record
                identities.append(record.episode_sha256)
            ledger._versions[str(key)] = identities
        ledger.validate()
        return ledger

    @staticmethod
    def _validate_identity(memory_key: str, episode_sha256: str) -> None:
        if not memory_key or memory_key.strip() != memory_key:
            raise SupersessionError("Memory key must be non-empty canonical text")
        if len(episode_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in episode_sha256
        ):
            raise SupersessionError("Episode identity must be lowercase SHA-256")


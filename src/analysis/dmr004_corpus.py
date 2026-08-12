"""DMR-004 query corpora: user query text and nothing else.

Every other stage in this arc reads the memory store. DMR-004 reads only what
the user typed. The corpus loader here is deliberately narrow so that the
exclusion is structural rather than a promise: it returns query strings and
content hashes, and it has no code path that can reach an answer, an evidence
marker, a haystack session, an embedding, a domain label, or a rubric.

Two sources are assembled.

**Internal.** The probe turns of the committed study scripts. These are the
queries the program has actually been scored on, so a compiler that cannot
represent them is not useful here, whatever it does elsewhere.

**LongMemEval.** The 500 question strings of `longmemeval_s_cleaned.json`.
These are natural user questions written by someone with no knowledge of this
program, which is the only defence available against a grammar that fits the
house style.

`question_type` is read for exactly one purpose: the G6 leakage check needs to
measure whether the grammar's output correlates with a benchmark label. It is
returned on a separate field that mechanism code must never accept, and
`queries_only()` exists so that mechanism-side callers cannot get it by
accident.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

CORPUS_SCHEMA = "dmr004-corpus-v1"
QUERY_ID_PREFIX = "dmr-query-v1"

DATASET_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
DATASET_BYTES = 277383467
DATASET_COMMIT = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
DEFAULT_DATASET_PATH = Path(r"C:\Users\muzaf\datasets\longmemeval\longmemeval_s_cleaned.json")

SEED = "5005"

#: Scripts whose probe turns form the internal source, with the first probe turn.
#: Studies 001-004 carry no probe marker and are excluded rather than guessed at.
INTERNAL_SCRIPTS: tuple[tuple[str, str, int], ...] = (
    ("study_005", "experiments/study_005/script.json", 112),
    ("study_010", "experiments/study_010/script_1000.json", 987),
)


class CorpusError(RuntimeError):
    pass


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def query_hash(source: str, text: str) -> str:
    """Content-addressed query identity.

    Deliberately not a path, a row number, or a benchmark id: PF5 requires that
    a comparison key survive re-extraction from a different working copy.
    """
    payload = (QUERY_ID_PREFIX + "\0" + source + "\0" + text).encode("utf-8")
    return _sha256(payload)


@dataclass(frozen=True)
class QueryRecord:
    """One user query.

    `text` is the only field mechanism code may read. `label` holds the
    benchmark's own question_type where one exists and is measurement-only;
    `origin` is a human-readable provenance string for reports.
    """

    query_id: str
    source: str
    origin: str
    text: str
    label: str | None = None

    def as_row(self) -> dict[str, object]:
        return {
            "query_id": self.query_id,
            "source": self.source,
            "origin": self.origin,
            "text": self.text,
            "label": self.label,
        }


def queries_only(records: Sequence[QueryRecord]) -> tuple[str, ...]:
    """The mechanism-side view: text, nothing else."""
    return tuple(record.text for record in records)


def load_internal(repo_root: Path) -> tuple[QueryRecord, ...]:
    records: list[QueryRecord] = []
    for source_name, relative, first_probe in INTERNAL_SCRIPTS:
        path = repo_root / relative
        if not path.is_file():
            raise CorpusError(f"internal script missing: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        turns = payload.get("turns")
        if not isinstance(turns, list):
            raise CorpusError(f"{relative}: no turns array")
        declared = payload.get("probe_turn_start")
        if declared is not None and int(declared) != first_probe:
            raise CorpusError(
                f"{relative}: probe_turn_start moved from {first_probe} to {declared}"
            )
        for turn in turns:
            index = int(turn.get("turn", 0))
            if index < first_probe:
                continue
            text = turn.get("user")
            if not isinstance(text, str) or not text.strip():
                raise CorpusError(f"{relative}: probe turn {index} has no user text")
            origin = f"{source_name}:turn_{index}"
            records.append(
                QueryRecord(
                    query_id=query_hash("internal", text),
                    source="internal",
                    origin=origin,
                    text=text,
                    label=None,
                )
            )
    if not records:
        raise CorpusError("internal source produced no probe queries")
    return tuple(records)


def load_longmemeval(dataset_path: Path | None = None, *, verify: bool = True) -> tuple[QueryRecord, ...]:
    path = dataset_path or DEFAULT_DATASET_PATH
    if not path.is_file():
        raise CorpusError(f"LongMemEval dataset missing: {path}")
    raw = path.read_bytes()
    if verify:
        if len(raw) != DATASET_BYTES:
            raise CorpusError(f"dataset size {len(raw)} != registered {DATASET_BYTES}")
        digest = _sha256(raw)
        if digest != DATASET_SHA256:
            raise CorpusError(f"dataset sha256 {digest} != registered {DATASET_SHA256}")
    items = json.loads(raw.decode("utf-8"))
    records: list[QueryRecord] = []
    for item in items:
        text = item["question"]
        records.append(
            QueryRecord(
                query_id=query_hash("longmemeval", text),
                source="longmemeval",
                origin=str(item["question_id"]),
                text=text,
                label=item.get("question_type"),
            )
        )
    return tuple(records)


def cache_path(repo_root: Path) -> Path:
    return repo_root / "experiments/components/biological_memory/dmr_004/artifacts/query_corpus.json"


def write_cache(repo_root: Path, records: Sequence[QueryRecord]) -> Path:
    """Persist the extracted queries so no later step re-reads 277 MB."""
    path = cache_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": CORPUS_SCHEMA,
        "dataset_sha256": DATASET_SHA256,
        "dataset_commit": DATASET_COMMIT,
        "internal_scripts": [list(entry) for entry in INTERNAL_SCRIPTS],
        "count": len(records),
        "queries": [record.as_row() for record in records],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def read_cache(repo_root: Path) -> tuple[QueryRecord, ...]:
    path = cache_path(repo_root)
    if not path.is_file():
        raise CorpusError(f"query corpus cache missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != CORPUS_SCHEMA:
        raise CorpusError(f"unexpected corpus schema {payload.get('schema')!r}")
    records = []
    for row in payload["queries"]:
        record = QueryRecord(
            query_id=row["query_id"],
            source=row["source"],
            origin=row["origin"],
            text=row["text"],
            label=row["label"],
        )
        expected = query_hash(record.source, record.text)
        if expected != record.query_id:
            raise CorpusError(f"cached query id {record.query_id} does not match its text")
        records.append(record)
    return tuple(records)


def load_all(repo_root: Path, dataset_path: Path | None = None) -> tuple[QueryRecord, ...]:
    return load_internal(repo_root) + load_longmemeval(dataset_path)


def corpus_digest(records: Sequence[QueryRecord]) -> str:
    """One hash over the ordered query identities, for PF1 and report headers."""
    joined = "\n".join(f"{record.source}\t{record.query_id}" for record in records)
    return _sha256(joined.encode("utf-8"))


def iter_by_source(records: Sequence[QueryRecord]) -> Iterator[tuple[str, tuple[QueryRecord, ...]]]:
    for source in ("internal", "longmemeval"):
        subset = tuple(record for record in records if record.source == source)
        if subset:
            yield source, subset

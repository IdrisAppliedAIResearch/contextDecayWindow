"""DMR-004 development/holdout split and annotation sampling.

Both are seeded content hashes over query identity, so the split survives
re-extraction from a different working copy and cannot be nudged by reordering
a file. Two independent seeds are used: one decides the split, a second decides
which queries get hand annotation, so that a query's split does not determine
its chance of being annotated.

The split is committed before any annotation exists, and the annotation is
committed before any compiler exists. That commit order is the evidence PF3
asks for; nothing here can enforce it after the fact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Sequence

from analysis import dmr004_corpus as corpus

SPLIT_SCHEMA = "dmr004-split-v1"
SPLIT_SEED = "5005"
SPLIT_DOMAIN = "dmr004-split-v1"
ANNOTATION_DOMAIN = "dmr004-annotation-v1"

#: Share of each source that becomes the development split.
DEVELOPMENT_SHARE = 0.40

#: Hand-annotation sample sizes. Chosen so that every internal query is
#: annotated - there are only 24 and they carry the imperative and
#: no-interrogative-frame shapes - and the LongMemEval remainder fills the rest.
DEVELOPMENT_SAMPLE = 120
HOLDOUT_SAMPLE = 180


def _rank(domain: str, query_id: str) -> str:
    payload = (SPLIT_SEED + "\0" + domain + "\0" + query_id).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def assign_split(records: Sequence[corpus.QueryRecord]) -> dict[str, str]:
    """Return query_id -> 'development' | 'holdout', stratified by source."""
    assignment: dict[str, str] = {}
    for _source, subset in corpus.iter_by_source(records):
        ordered = sorted(subset, key=lambda record: _rank(SPLIT_DOMAIN, record.query_id))
        cut = int(len(ordered) * DEVELOPMENT_SHARE)
        for index, record in enumerate(ordered):
            assignment[record.query_id] = "development" if index < cut else "holdout"
    return assignment


def annotation_sample(
    records: Sequence[corpus.QueryRecord], assignment: dict[str, str], split: str, size: int
) -> tuple[corpus.QueryRecord, ...]:
    """The queries a human rates, drawn on a seed independent of the split.

    Internal queries are taken whole: there are 24 of them and they carry the
    shapes LongMemEval does not have. LongMemEval fills the remainder.
    """
    members = [record for record in records if assignment[record.query_id] == split]
    internal = [record for record in members if record.source == "internal"]
    external = [record for record in members if record.source == "longmemeval"]
    external.sort(key=lambda record: _rank(ANNOTATION_DOMAIN, record.query_id))
    remaining = max(0, size - len(internal))
    chosen = internal + external[:remaining]
    return tuple(sorted(chosen, key=lambda record: _rank(ANNOTATION_DOMAIN, record.query_id)))


def build_manifest(records: Sequence[corpus.QueryRecord]) -> dict[str, object]:
    assignment = assign_split(records)
    development = annotation_sample(records, assignment, "development", DEVELOPMENT_SAMPLE)
    holdout = annotation_sample(records, assignment, "holdout", HOLDOUT_SAMPLE)
    counts: dict[str, dict[str, int]] = {}
    for source, subset in corpus.iter_by_source(records):
        counts[source] = {
            "development": sum(1 for r in subset if assignment[r.query_id] == "development"),
            "holdout": sum(1 for r in subset if assignment[r.query_id] == "holdout"),
        }
    manifest = {
        "schema": SPLIT_SCHEMA,
        "seed": SPLIT_SEED,
        "development_share": DEVELOPMENT_SHARE,
        "corpus_digest": corpus.corpus_digest(records),
        "counts_by_source": counts,
        "annotation_samples": {
            "development": {
                "size": len(development),
                "query_ids": [record.query_id for record in development],
            },
            "holdout": {
                "size": len(holdout),
                "query_ids": [record.query_id for record in holdout],
            },
        },
        "assignment": dict(sorted(assignment.items())),
    }
    serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    manifest["manifest_sha256"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return manifest


def manifest_path(repository_root: Path) -> Path:
    return (
        repository_root
        / "experiments/components/biological_memory/dmr_004/artifacts/split_manifest.json"
    )


def write_manifest(repository_root: Path) -> Path:
    records = corpus.read_cache(repository_root)
    manifest = build_manifest(records)
    path = manifest_path(repository_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def read_manifest(repository_root: Path) -> dict[str, object]:
    path = manifest_path(repository_root)
    if not path.is_file():
        raise corpus.CorpusError(f"split manifest missing: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SPLIT_SCHEMA:
        raise corpus.CorpusError(f"unexpected split schema {manifest.get('schema')!r}")
    stored = manifest.pop("manifest_sha256")
    serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    recomputed = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    if recomputed != stored:
        raise corpus.CorpusError(f"split manifest hash {recomputed} != recorded {stored}")
    manifest["manifest_sha256"] = stored
    return manifest

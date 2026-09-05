"""AV-PRE-001 - does header-stripping change what ASPECT admits?

Offline. No model generation calls. Two phases over the ten sealed HH-003
ASPECT stores:

1. **Reproduction gate.** Rebuild HH-003's ASPECT-on allocation from the sealed
   stores and gate on the sealed per-item ``payload_sha256`` plus every
   non-timing ``detail`` field, across all 1,540 items.

   The registration asked for a byte-identical ``contexts.json``. That file
   embeds ``latency_ms`` and ``search_time``, which are measured wall-clock
   values, so its file digest is reproducible only by copying it. The file is
   verified intact against the registered digest separately; the *allocation*
   is gated here on the sealed timing-free fields, which is what "nothing else
   is interpretable" was protecting.

2. **Treatment.** The same allocation with one change: the timestamp/speaker
   header is stripped from the text handed to facet extraction. Everything else
   is frozen - CC80 ranking, scores, budget, aspect_share, greedy rule, packing,
   renderer, recency. Embeddings are untouched, because ``searchable_text``
   still feeds CC80 exactly as before; only facet extraction sees stripped text.

Facet bundles are memoized per conversation. ``prepare_facets`` is a pure
function of the store, so this is identity-preserving by construction, and the
reproduction gate in phase 1 is what proves it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import episodic._retrieval as _retrieval
from analysis.hh002_dataset import Conversation, load_corpus
from analysis.hh002_run import DATASET
from analysis.hh003_arms import SharedEmbedder, stable_item_key
from episodic import EpisodeStore, EpisodicConfig
from episodic._aspect import extract_facets, facet_idf, prepare_facets
from episodic._aspect import _load_spacy_model  # noqa: PLC2701 - frozen loader
from episodic._ranking import searchable_text
from retrieval_bakeoff.embedding import CarriedEmbedder

REPO = Path(__file__).resolve().parents[2]
SEALED = REPO / "experiments/comparisons/hh_003/artifacts/run/A_EPISODIC_ASPECT"
OUT = REPO / "experiments/components/aspect_v3/artifacts/av_pre_001"

# The registered digest of the sealed ASPECT contexts artifact.
SEALED_CONTEXTS_SHA256 = (
    "119a3152c5c3c300df34930a42dbb96e2454e960e48a84de2b9964d7c254caae"
)

# The header regex from the anatomy measurement. Re-verified per conversation.
HDR = re.compile(
    r"^\s*\d{1,2}:\d{2}\s*[ap]m on \d{1,2} \w+, \d{4}\s*\|\s*[^:]{1,30}:\s*", re.M
)

# detail fields that carry measured wall-clock time and cannot reproduce.
TIMING_FIELDS = frozenset({"latency_ms"})


class AVPreError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stripped_bundle(
    episodes: Sequence[dict], model_name: str
) -> tuple[tuple[frozenset[str], ...], dict[str, float], dict[str, int]]:
    """prepare_facets, with the header removed from the text it parses.

    Mirrors ``prepare_facets`` exactly except for the ``HDR.sub`` call: same
    model, same pipe, same batch size, same extractor, same IDF.
    """
    nlp = _load_spacy_model(model_name)
    texts = [HDR.sub("", searchable_text(episode)) for episode in episodes]
    docs = nlp.pipe(texts, batch_size=64)
    facets = tuple(extract_facets(doc) for doc in docs)
    idf, families = facet_idf(facets)
    return facets, idf, families


def header_coverage(episodes: Sequence[dict]) -> dict[str, Any]:
    """Re-verify the header regex on this conversation before using it."""
    total = 0
    matched = 0
    for episode in episodes:
        for field in ("user_message", "assistant_message"):
            total += 1
            if HDR.search(str(episode[field])):
                matched += 1
    return {
        "messages": total,
        "matched": matched,
        "rate": round(matched / total, 6) if total else 0.0,
    }


class _Recorder:
    """Capture each RetrievalAllocation without altering the read path."""

    def __init__(self) -> None:
        self.last: Any = None
        self._real = _retrieval.retrieve_long_term

    def __enter__(self) -> "_Recorder":
        def wrapper(**kwargs):
            allocation = self._real(**kwargs)
            self.last = allocation
            return allocation

        _retrieval.retrieve_long_term = wrapper
        return self

    def __exit__(self, *exc: object) -> None:
        _retrieval.retrieve_long_term = self._real


class _FacetPin:
    """Pin the facet bundle a conversation's allocations use."""

    def __init__(self) -> None:
        self.bundle: Any = None
        self._real = _retrieval.prepare_facets

    def __enter__(self) -> "_FacetPin":
        def wrapper(episodes, model_name):
            if self.bundle is None:
                return self._real(episodes, model_name)
            return self.bundle

        _retrieval.prepare_facets = wrapper
        return self

    def __exit__(self, *exc: object) -> None:
        _retrieval.prepare_facets = self._real


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def run(workdir: Path, limit_conversations: int | None = None) -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    workdir.mkdir(parents=True, exist_ok=True)

    sealed_digest = _sha256_file(SEALED / "contexts.json")
    if sealed_digest != SEALED_CONTEXTS_SHA256:
        raise AVPreError(
            "sealed HH-003 ASPECT contexts.json does not match the registered "
            f"digest: {sealed_digest}"
        )
    sealed_items = json.loads(
        (SEALED / "contexts.json").read_text(encoding="utf-8")
    )["items"]

    conversations = list(load_corpus(DATASET))
    if limit_conversations:
        conversations = conversations[:limit_conversations]

    embedder = SharedEmbedder(CarriedEmbedder())
    config = EpisodicConfig(aspect_enabled=True)

    rows: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    headers: dict[str, Any] = {}
    started = time.time()

    for position, conversation in enumerate(conversations, start=1):
        source = SEALED / f"{conversation.sample_id}.db"
        target = workdir / f"{conversation.sample_id}.db"
        shutil.copyfile(source, target)

        store = EpisodeStore(target, config=config, embedder=embedder)
        try:
            episodes = store._all_episodes()  # noqa: SLF001 - frozen read path
            headers[conversation.sample_id] = header_coverage(episodes)

            bundle_v1 = prepare_facets(episodes, config.aspect_model)
            bundle_clean = stripped_bundle(episodes, config.aspect_model)

            per_item: dict[str, dict[str, Any]] = {}
            with _Recorder() as recorder, _FacetPin() as pin:
                for phase, bundle in (("v1", bundle_v1), ("clean", bundle_clean)):
                    pin.bundle = bundle
                    for question in conversation.scored_questions:
                        payload, report = store.context(question.question)
                        key = stable_item_key(conversation.sample_id, question)
                        allocation = recorder.last
                        entry = per_item.setdefault(key, {})
                        entry[phase] = {
                            "payload_sha256": hashlib.sha256(
                                payload.encode("utf-8")
                            ).hexdigest(),
                            "aspect_ids": list(allocation.aspect_ids),
                            "initial_ids": list(allocation.initial_semantic_ids),
                            "returned_ids": list(allocation.returned_semantic_ids),
                            "selected_ids": list(allocation.selected_ids),
                            "aspect_count": report.aspect_count,
                            "semantic_count": report.semantic_count,
                            "chars_delivered": report.chars_delivered,
                            "detail": {
                                field: value
                                for field, value in report.__dict__.items()
                                if field not in TIMING_FIELDS
                            },
                        }

            for key, entry in per_item.items():
                v1 = entry["v1"]
                clean = entry["clean"]
                sealed = sealed_items[key]

                # -- reproduction gate -------------------------------------
                gate_ok = v1["payload_sha256"] == sealed["detail"]["payload_sha256"]
                field_diffs = {}
                for field, value in v1["detail"].items():
                    if field in TIMING_FIELDS or field not in sealed["detail"]:
                        continue
                    expected = sealed["detail"][field]
                    observed = value
                    if isinstance(observed, tuple):
                        observed = list(observed)
                    if observed != expected:
                        field_diffs[field] = {
                            "sealed": expected,
                            "observed": observed,
                        }
                if not gate_ok or field_diffs:
                    mismatches.append(
                        {
                            "key": key,
                            "sample_id": conversation.sample_id,
                            "payload_match": gate_ok,
                            "field_diffs": field_diffs,
                        }
                    )

                # -- treatment contrast ------------------------------------
                a1 = set(v1["aspect_ids"])
                a2 = set(clean["aspect_ids"])
                rows.append(
                    {
                        "key": key,
                        "sample_id": conversation.sample_id,
                        "source_index": None,
                        "reproduced": gate_ok and not field_diffs,
                        "jaccard": _jaccard(a1, a2),
                        "added": len(a2 - a1),
                        "dropped": len(a1 - a2),
                        "aspect_count_v1": v1["aspect_count"],
                        "aspect_count_clean": clean["aspect_count"],
                        "aspect_count_delta": clean["aspect_count"]
                        - v1["aspect_count"],
                        "delivered_jaccard": _jaccard(
                            set(v1["selected_ids"]), set(clean["selected_ids"])
                        ),
                        "payload_changed": v1["payload_sha256"]
                        != clean["payload_sha256"],
                    }
                )
        finally:
            store.close()

        elapsed = time.time() - started
        print(
            f"  [{position}/{len(conversations)}] {conversation.sample_id} "
            f"items={len(conversation.scored_questions)} "
            f"mismatches={len(mismatches)} elapsed={elapsed / 60:.1f}m",
            flush=True,
        )
        (OUT / "rows.jsonl").write_text(
            "\n".join(json.dumps(row, sort_keys=True) for row in rows),
            encoding="utf-8",
        )

    return summarize(rows, mismatches, headers, sealed_digest, embedder)


def summarize(
    rows: list[dict[str, Any]],
    mismatches: list[dict[str, Any]],
    headers: dict[str, Any],
    sealed_digest: str,
    embedder: SharedEmbedder,
) -> dict[str, Any]:
    reproduced = sum(row["reproduced"] for row in rows)
    jaccards = [row["jaccard"] for row in rows]
    median = statistics.median(jaccards) if jaccards else float("nan")

    if not rows or reproduced != len(rows):
        verdict = "GATE_FAILED"
    elif median >= 0.9:
        verdict = "SELECTION_UNCHANGED"
    elif median <= 0.6:
        verdict = "SELECTION_MOVES"
    else:
        verdict = "INDETERMINATE"

    def _q(values: list[float], fraction: float) -> float:
        if not values:
            return float("nan")
        ordered = sorted(values)
        index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
        return ordered[index]

    by_conversation = {}
    for sample_id in sorted({row["sample_id"] for row in rows}):
        subset = [row for row in rows if row["sample_id"] == sample_id]
        by_conversation[sample_id] = {
            "items": len(subset),
            "reproduced": sum(row["reproduced"] for row in subset),
            "median_jaccard": round(
                statistics.median([row["jaccard"] for row in subset]), 6
            ),
            "mean_added": round(
                statistics.mean([row["added"] for row in subset]), 4
            ),
            "mean_dropped": round(
                statistics.mean([row["dropped"] for row in subset]), 4
            ),
            "mean_aspect_count_delta": round(
                statistics.mean([row["aspect_count_delta"] for row in subset]), 4
            ),
            "payloads_changed": sum(row["payload_changed"] for row in subset),
            "header": headers.get(sample_id),
        }

    return {
        "schema": "av-pre-001-v1",
        "verdict": verdict,
        "registered_read": {
            "median_jaccard>=0.9": "SELECTION_UNCHANGED - hypothesis dead",
            "median_jaccard<=0.6": "SELECTION_MOVES - proceed to three arms",
            "otherwise": "INDETERMINATE - report descriptively",
        },
        "reproduction": {
            "sealed_contexts_sha256": sealed_digest,
            "sealed_digest_matches_registration": sealed_digest
            == SEALED_CONTEXTS_SHA256,
            "items": len(rows),
            "reproduced": reproduced,
            "mismatches": len(mismatches),
            "gated_on": [
                "sealed per-item payload_sha256",
                "every sealed non-timing detail field",
            ],
            "not_gated_on": sorted(TIMING_FIELDS) + ["search_time"],
        },
        "contrast": {
            "median_jaccard": round(median, 6) if jaccards else None,
            "mean_jaccard": round(statistics.mean(jaccards), 6) if jaccards else None,
            "p10_jaccard": round(_q(jaccards, 0.10), 6),
            "p25_jaccard": round(_q(jaccards, 0.25), 6),
            "p75_jaccard": round(_q(jaccards, 0.75), 6),
            "p90_jaccard": round(_q(jaccards, 0.90), 6),
            "min_jaccard": round(min(jaccards), 6) if jaccards else None,
            "max_jaccard": round(max(jaccards), 6) if jaccards else None,
            "items_identical_admission": sum(1 for v in jaccards if v == 1.0),
            "items_payload_changed": sum(row["payload_changed"] for row in rows),
            "mean_added": round(
                statistics.mean([row["added"] for row in rows]), 4
            )
            if rows
            else None,
            "mean_dropped": round(
                statistics.mean([row["dropped"] for row in rows]), 4
            )
            if rows
            else None,
            "mean_aspect_count_v1": round(
                statistics.mean([row["aspect_count_v1"] for row in rows]), 4
            )
            if rows
            else None,
            "mean_aspect_count_clean": round(
                statistics.mean([row["aspect_count_clean"] for row in rows]), 4
            )
            if rows
            else None,
        },
        "by_conversation": by_conversation,
        "header_regex": HDR.pattern,
        "embedding_cache": {"hits": embedder.hits, "misses": embedder.misses},
        "mismatch_sample": mismatches[:10],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run AV-PRE-001")
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--conversations", type=int, default=None)
    args = parser.parse_args(argv)

    result = run(Path(args.workdir), args.conversations)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "by_conversation"},
                     indent=2, sort_keys=True))
    return 0 if result["verdict"] != "GATE_FAILED" else 1


if __name__ == "__main__":
    sys.exit(main())

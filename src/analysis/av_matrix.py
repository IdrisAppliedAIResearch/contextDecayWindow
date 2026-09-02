"""AV-MATRIX - channel decomposition at two budgets, without recency.

Six cells: {CC80, CC80+ASPECT 50/50, CC80+ASPECT+DA 50/25/25} x {16k, 32k}.

The recency block is excluded entirely. Every arm in the HH series delivers
32 positionally-selected episodes (~12k chars, 28% of the payload) outside the
retrieval budget, and no study has ever contested them. LoCoMo is a finished
transcript, so the last 32 episodes are close to an arbitrary slice. Removing
them makes CC80 the floor and lets the second-16k question be asked cleanly.

Offline only. No reader calls, no judging. Builds the allocations and reports
composition plus gold-evidence delivery.

**Evidence delivery is reported as a composition property, not an endpoint.**
This programme has established that availability does not predict reader
accuracy - it disagreed with live outcomes in both directions (TC-011/HH-003,
DA-098/HH-005), and DA-098 reached the availability ceiling and still lost.
These numbers say what is in the payload, never whether it will be answered.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import statistics
import sys
from pathlib import Path
from typing import Any, Sequence

from analysis.hh002_dataset import load_corpus
from analysis.hh002_run import DATASET
from analysis.hh003_arms import SharedEmbedder, stable_item_key
from episodic import EpisodeStore, EpisodicConfig
from episodic._aspect import aspect_spread, prepare_facets
from episodic._packing import pack_stm_payload
from episodic._ranking import rank_cc80
from episodic._render import render_stm_payload
from retrieval_bakeoff.embedding import CarriedEmbedder

REPO = Path(__file__).resolve().parents[2]
SEALED = REPO / "experiments/comparisons/hh_003/artifacts/run/A_EPISODIC_ASPECT"
OUT = REPO / "experiments/components/aspect_v3/artifacts/av_matrix"

DA_SHA256 = "f5327a9b5946f217910f2de5df222da66bda59d5f7b18267f8154763f98d44f9"
BUDGETS = (16_000, 32_000)
# The six NF-004 holdout conversations are the only ones with a DA allocation.
DA_CONVERSATIONS = frozenset(
    {"conv-26", "conv-30", "conv-43", "conv-44", "conv-49", "conv-50"}
)


class AVMatrixError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_SESSION = re.compile(r"session_(\d+)")
# The LoCoMo file NF-004 locked. DA member identities are hashes over its text,
# so a different corpus file silently produces a member map that joins to nothing.
DATASET_SHA256 = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"


def member_map(dataset_path: Path) -> dict[str, list[dict[str, str]]]:
    """Rebuild DA-098's episode-identity -> member map from the corpus.

    Reproduces ``nf004_anatomy_features._identity`` over the same candidate
    enumeration ``da006_reserved_links._member_maps`` uses, so the DA arc's
    modules (which live only on the unmerged PR #91) are not needed. Every
    identity the allocation references is asserted present by the caller.
    """
    if _sha256_file(dataset_path) != DATASET_SHA256:
        raise AVMatrixError("LoCoMo corpus differs from the NF-004 lock")
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    out: dict[str, list[dict[str, str]]] = {}
    for row in raw:
        sample_id = str(row.get("sample_id"))
        if sample_id not in DA_CONVERSATIONS:
            continue
        conversation = row["conversation"]
        ordered: list[tuple[int, str]] = []
        for key in conversation:
            match = _SESSION.fullmatch(key)
            if match:
                ordered.append((int(match.group(1)), key))
        keys = [key for _, key in sorted(ordered)]
        for session_id in keys:
            turns = conversation[session_id]
            for start in range(0, len(turns), 2):
                group = turns[start : start + 2]
                dialogue_ids = [str(turn["dia_id"]) for turn in group]
                text = "\n".join(
                    f"{turn['speaker']}: {turn['text']}" for turn in group
                )
                identity = hashlib.sha256(
                    "\0".join([sample_id, session_id, *dialogue_ids, text]).encode(
                        "utf-8"
                    )
                ).hexdigest()
                out[identity] = [
                    {
                        "dialogue_id": str(turn["dia_id"]),
                        "speaker": str(turn["speaker"]),
                        "text": str(turn["text"]),
                    }
                    for turn in group
                ]
    return out


def _channel(tag: str, blocks: list[str]) -> str:
    return f"<{tag}>\n" + "\n".join(blocks) + f"\n</{tag}>"


def _member_blocks(values: Sequence[dict[str, str]]) -> list[str]:
    return [
        f'<member index="{index}">\n{value["speaker"]}: {value["text"]}\n</member>'
        for index, value in enumerate(values, start=1)
    ]


def _derivative(
    values: Sequence[dict[str, str]], excluded: set[str], budget: int
) -> tuple[str, list[str]]:
    """HH-005's derivative packer, verbatim in behaviour, at a chosen budget."""
    admitted: list[dict[str, str]] = []
    ids: list[str] = []
    for member in values:
        dialogue_id = str(member["dialogue_id"])
        if dialogue_id in excluded or dialogue_id in ids:
            continue
        trial = admitted + [member]
        if len(_channel("derivative_context_v2", _member_blocks(trial))) > budget:
            continue
        admitted, ids = trial, ids + [dialogue_id]
    return _channel("derivative_context_v2", _member_blocks(admitted)), ids


def _semantic_then_aspect(
    episodes: Sequence[dict],
    ranking,
    order: Sequence[int],
    bundle,
    semantic_chars: int,
    aspect_chars: int,
) -> tuple[list[str], list[str]]:
    """The frozen protected-spread shape at explicit channel allowances."""
    by_id = {str(episode["id"]): index for index, episode in enumerate(episodes)}
    initial = pack_stm_payload(
        [], [episodes[index] for index in order], semantic_chars
    )
    initial_ids = list(initial.selected_ids)
    if not initial_ids or aspect_chars <= 0:
        return initial_ids, []
    facets, idf, _families = bundle
    trace = aspect_spread(
        episodes,
        facets,
        idf,
        ranking.scores,
        ranking.order,
        tuple(by_id[identifier] for identifier in initial_ids),
        aspect_chars,
    )
    admitted = set(initial_ids)
    spread = pack_stm_payload(
        [],
        [
            episodes[index]
            for index in trace.order
            if str(episodes[index]["id"]) not in admitted
        ],
        aspect_chars,
    )
    return initial_ids, list(spread.selected_ids)


def build(
    workdir: Path,
    da_path: Path,
    limit: int | None = None,
    contexts_dir: Path | None = None,
) -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    workdir.mkdir(parents=True, exist_ok=True)

    if _sha256_file(da_path) != DA_SHA256:
        raise AVMatrixError("DA-098 blind allocation differs from the HH-005 seal")

    members = member_map(DATASET)
    with gzip.open(da_path, "rt", encoding="utf-8") as handle:
        selections = {
            (str(row["sample_id"]), int(row["source_index"])): row
            for row in (json.loads(line) for line in handle)
        }
    referenced = {
        str(value[0])
        for row in selections.values()
        for value in row["arch32"]["selected_members"]
    }
    missing = referenced - set(members)
    if missing:
        raise AVMatrixError(
            f"{len(missing)} DA member identities do not join to the corpus; "
            "the rebuilt member map does not reproduce DA-098's enumeration"
        )

    conversations = list(load_corpus(DATASET))
    if limit:
        conversations = conversations[:limit]

    embedder = SharedEmbedder(CarriedEmbedder())
    config = EpisodicConfig(aspect_enabled=True)
    rows: list[dict[str, Any]] = []
    contexts: dict[str, dict[str, Any]] = {}

    for position, conversation in enumerate(conversations, start=1):
        target = workdir / f"{conversation.sample_id}.db"
        shutil.copyfile(SEALED / f"{conversation.sample_id}.db", target)
        store = EpisodeStore(target, config=config, embedder=embedder)
        try:
            episodes = store._all_episodes()  # noqa: SLF001 - frozen read path
            bundle = prepare_facets(episodes, config.aspect_model)
            # turn_number -> the two source dia_ids that formed that episode
            source_of = {
                number: tuple(
                    turn.dia_id
                    for turn in conversation.turns[start : start + 2]
                )
                for number, start in enumerate(
                    range(0, (len(conversation.turns) // 2) * 2, 2), start=1
                )
            }
            ids_of = {
                str(episode["id"]): source_of[int(episode["turn_number"])]
                for episode in episodes
            }

            for question in conversation.scored_questions:
                key = stable_item_key(conversation.sample_id, question)
                vector = embedder.embed(question.question)
                ranking = rank_cc80(
                    episodes,
                    question.question,
                    vector,
                    dense_weight=config.semantic_dense_weight,
                    bm25_k1=config.bm25_k1,
                    bm25_b=config.bm25_b,
                )
                order = ranking.order
                selection = selections.get(
                    (conversation.sample_id, int(question.source_index))
                )
                evidence = set(question.evidence)

                for budget in BUDGETS:
                    for arm in ("A_CC80", "B_CC80_ASPECT", "C_CC80_ASPECT_DA"):
                        if arm == "C_CC80_ASPECT_DA" and selection is None:
                            continue
                        if arm == "A_CC80":
                            packed = pack_stm_payload(
                                [], [episodes[i] for i in order], budget
                            )
                            sem_ids, asp_ids = list(packed.selected_ids), []
                        elif arm == "B_CC80_ASPECT":
                            sem_ids, asp_ids = _semantic_then_aspect(
                                episodes, ranking, order, bundle,
                                int(budget * 0.50), int(budget * 0.50),
                            )
                        else:
                            sem_ids, asp_ids = _semantic_then_aspect(
                                episodes, ranking, order, bundle,
                                int(budget * 0.50), int(budget * 0.25),
                            )

                        episode_ids = sem_ids + asp_ids
                        by_id = {
                            str(e["id"]): e for e in episodes
                        }
                        payload = render_stm_payload(
                            [], [by_id[i] for i in episode_ids]
                        )
                        delivered = {
                            dia
                            for identifier in episode_ids
                            for dia in ids_of[identifier]
                        }
                        da_ids: list[str] = []
                        if arm == "C_CC80_ASPECT_DA":
                            values = [
                                members[episode][member]
                                for episode, member in (
                                    (str(v[0]), int(v[1]))
                                    for v in selection["arch32"][
                                        "selected_members"
                                    ]
                                )
                            ]
                            block, da_ids = _derivative(
                                values, delivered, int(budget * 0.25)
                            )
                            payload = payload + "\n" + block
                            delivered |= set(da_ids)

                        if contexts_dir is not None:
                            cell = f"{arm}@{budget // 1000}k"
                            contexts.setdefault(cell, {})[key] = {
                                "key": key,
                                "sample_id": conversation.sample_id,
                                "source_index": int(question.source_index),
                                "category": int(question.category),
                                "question": question.question,
                                "answer": question.answer,
                                "context": payload,
                                "context_chars": len(payload),
                            }
                        rows.append(
                            {
                                "key": key,
                                "sample_id": conversation.sample_id,
                                "source_index": int(question.source_index),
                                "category": int(question.category),
                                "arm": arm,
                                "budget": budget,
                                "chars": len(payload),
                                "semantic_episodes": len(sem_ids),
                                "aspect_episodes": len(asp_ids),
                                "da_members": len(da_ids),
                                "has_evidence": bool(evidence),
                                "evidence_any": bool(evidence & delivered),
                                "evidence_all": bool(
                                    evidence and evidence <= delivered
                                ),
                            }
                        )
        finally:
            store.close()
        print(
            f"  [{position}/{len(conversations)}] {conversation.sample_id} "
            f"rows={len(rows)}",
            flush=True,
        )
        with (OUT / "rows.jsonl").open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

    if contexts_dir is not None:
        contexts_dir.mkdir(parents=True, exist_ok=True)
        for cell, items in sorted(contexts.items()):
            (contexts_dir / f"{cell}.json").write_text(
                json.dumps({"cell": cell, "items": items}, sort_keys=True),
                encoding="utf-8",
            )
            print(f"  wrote {cell}: {len(items)} contexts", flush=True)

    return summarize(rows, embedder)


def summarize(rows: list[dict[str, Any]], embedder: SharedEmbedder) -> dict[str, Any]:
    da_keys = {
        row["key"] for row in rows if row["arm"] == "C_CC80_ASPECT_DA"
    }
    cells: dict[str, Any] = {}
    for arm in ("A_CC80", "B_CC80_ASPECT", "C_CC80_ASPECT_DA"):
        for budget in BUDGETS:
            # Restrict every cell to the DA-covered population so the six
            # cells are one comparison rather than three of different size.
            subset = [
                row
                for row in rows
                if row["arm"] == arm
                and row["budget"] == budget
                and row["key"] in da_keys
            ]
            if not subset:
                continue
            scored = [row for row in subset if row["has_evidence"]]
            m = statistics.mean
            cells[f"{arm}@{budget // 1000}k"] = {
                "items": len(subset),
                "mean_chars": round(m([r["chars"] for r in subset]), 1),
                "mean_semantic_episodes": round(
                    m([r["semantic_episodes"] for r in subset]), 2
                ),
                "mean_aspect_episodes": round(
                    m([r["aspect_episodes"] for r in subset]), 2
                ),
                "mean_da_members": round(m([r["da_members"] for r in subset]), 2),
                "evidence_all_pct": round(
                    100 * sum(r["evidence_all"] for r in scored) / len(scored), 2
                ),
                "evidence_any_pct": round(
                    100 * sum(r["evidence_any"] for r in scored) / len(scored), 2
                ),
            }

    holdout = [
        row
        for row in rows
        if row["key"] not in da_keys and row["arm"] != "C_CC80_ASPECT_DA"
    ]
    bonus: dict[str, Any] = {}
    for arm in ("A_CC80", "B_CC80_ASPECT"):
        for budget in BUDGETS:
            subset = [
                r for r in holdout if r["arm"] == arm and r["budget"] == budget
            ]
            scored = [r for r in subset if r["has_evidence"]]
            if not scored:
                continue
            bonus[f"{arm}@{budget // 1000}k"] = {
                "items": len(subset),
                "evidence_all_pct": round(
                    100 * sum(r["evidence_all"] for r in scored) / len(scored), 2
                ),
            }

    return {
        "schema": "av-matrix-v1",
        "recency": "excluded from every arm",
        "population": {
            "da_covered_items": len(da_keys),
            "note": (
                "All six cells are reported on the DA-covered population. "
                "The DA-098 allocation exists only for the six NF-004 holdout "
                "conversations, which the AV plan designates as the DEVELOPMENT "
                "split, so no cell containing DA can ever be confirmed on "
                "held-out data."
            ),
        },
        "endpoint_warning": (
            "Evidence delivery is a composition property, not an endpoint. It "
            "has disagreed with live reader outcomes in both directions."
        ),
        "cells": cells,
        "non_da_conversations": bonus,
        "embedding_cache": {"hits": embedder.hits, "misses": embedder.misses},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the AV channel matrix")
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--da", required=True)
    parser.add_argument("--conversations", type=int, default=None)
    parser.add_argument("--contexts-dir", default=None)
    args = parser.parse_args(argv)
    result = build(
        Path(args.workdir),
        Path(args.da),
        args.conversations,
        Path(args.contexts_dir) if args.contexts_dir else None,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

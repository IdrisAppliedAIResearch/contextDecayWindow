"""Gold-blind frozen prompt construction for LV-007."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import spacy

from analysis.hh001_prompt import render_reader_prompt
from analysis.locomo_nf_development import sha256_file
from analysis.lv002_prompts import CLOSED_THINK_SUFFIX
from analysis.tc001_exploration import REPO_ROOT, build_episodes
from analysis.tc008_study import load_blind_manifest, load_blind_vectors
from analysis.tc009_dependency_graph_probe import BLIND
from analysis.tc011_spread import extract_facets, facet_idf
from analysis.tc013_fanout import weighted_facet_overlap
from episodic._render import render_episode_element


ARMS = ("PAIRWISE", "COMMUNITY", "COMMUNITY_QB")
ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_007"
REGISTRATION = ROOT / "LV_007_PRE_REGISTRATION.md"
PART1 = ROOT / "artifacts" / "part1_exploration.json"
PROMPTS = ROOT / "artifacts" / "preflight" / "prompts.jsonl.gz"
PROMPT_MANIFEST = ROOT / "artifacts" / "preflight" / "prompt_manifest.json"
LV005_PROMPTS = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "live_validation_005"
    / "artifacts"
    / "preflight"
    / "prompts.jsonl.gz"
)
TC014_SELECTIONS = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "tier_cost"
    / "artifacts"
    / "tc014"
    / "preflight"
    / "selections.jsonl.gz"
)
LV006_RESULT = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "live_validation_006"
    / "artifacts"
    / "result"
    / "result.json"
)

REGISTRATION_SHA256 = "2898f8cfde7b06ebfdf6638f63a1a210557f0b4cdcde232444fa46a6dd37dc9f"
PART1_SHA256 = "acd6a783a8ffd949b35ebe28788ea88a9b08de3c9b19ba7139da9547d815d78f"
LV005_PROMPTS_SHA256 = "d0a3ac38e15c1738387c9d3216de532195959dd4c8ac7515a03209bbfebe8b80"
TC014_SELECTIONS_SHA256 = "32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7"
LV006_RESULT_SHA256 = "011d0a3cf49d781f99a14327c3189b5260c1eec3e44e206ff84be8ce783f76ee"

ALPHA = 0.8
THRESHOLD = 0.04
CAP = 8
FIRST_LINE = "You are answering a question about a conversation between two people."
ORGANIZATION_NOTE = (
    "Evidence is grouped by content. Groups are ordered by direct relevance. "
    "Items within a group are in conversation order."
)


class LV007PromptError(RuntimeError):
    pass


def _read_gzip(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_gzip_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    raw = b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0) as stream:
            stream.write(raw)


def _question_before_memory(prompt: str, question: str) -> str:
    prefix = FIRST_LINE + "\n\n"
    if not prompt.startswith(prefix):
        raise LV007PromptError("reader template first line drift")
    return prefix + f"Question to answer: {question}\n\n" + prompt[len(prefix) :]


def _community_assignment(
    affinity: np.ndarray,
    *,
    threshold: float = THRESHOLD,
    cap: int = CAP,
) -> tuple[tuple[int, ...], list[dict[str, Any]]]:
    count = int(affinity.shape[0])
    if affinity.shape != (count, count) or not np.isfinite(affinity).all():
        raise LV007PromptError("invalid affinity matrix")
    groups: list[list[int]] = []
    trace: list[dict[str, Any]] = []
    for node in range(count):
        options = []
        for group_index, group in enumerate(groups):
            if len(group) >= cap:
                continue
            score = float(np.mean(affinity[node, np.asarray(group, dtype=np.int64)]))
            options.append((score, -group_index, group_index))
        winner = max(options) if options else None
        if winner is not None and winner[0] >= threshold:
            group_index = winner[2]
            groups[group_index].append(node)
            trace.append(
                {
                    "node": node,
                    "decision": "join",
                    "group": group_index,
                    "mean_affinity": winner[0],
                }
            )
        else:
            group_index = len(groups)
            groups.append([node])
            trace.append(
                {
                    "node": node,
                    "decision": "new",
                    "group": group_index,
                    "mean_affinity": None if winner is None else winner[0],
                }
            )
    emitted = [node for group in groups for node in group]
    if sorted(emitted) != list(range(count)):
        raise LV007PromptError("community assignment changed selected identities")
    return tuple(tuple(group) for group in groups), trace


def _community_block(
    records: Mapping[str, Mapping[str, Any]],
    selected_ids: Sequence[str],
    affinity: np.ndarray,
    spread_ids: Sequence[str],
) -> tuple[str, list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    raw_groups, trace = _community_assignment(affinity)
    lines = [
        "<recent_context/>",
        "",
        '<retrieved_stm organization="semantic_communities">',
        f"<organization_note>{ORGANIZATION_NOTE}</organization_note>",
    ]
    groups: list[dict[str, Any]] = []
    emitted: list[str] = []
    spread = set(spread_ids)
    for rank, raw_group in enumerate(raw_groups, start=1):
        identities = [selected_ids[index] for index in raw_group]
        identities.sort(key=lambda identity: (int(records[identity]["turn_number"]), identity))
        lines.append(f'<g rank="{rank}">')
        items = []
        for identity in identities:
            lines.append(render_episode_element(dict(records[identity])))
            emitted.append(identity)
            items.append(
                {
                    "identity": identity,
                    "turn": int(records[identity]["turn_number"]),
                    "route": "spread" if identity in spread else "semantic",
                }
            )
        lines.append("</g>")
        groups.append({"rank": rank, "items": items})
    lines.append("</retrieved_stm>")
    if len(emitted) != len(set(emitted)) or set(emitted) != set(selected_ids):
        raise LV007PromptError("community render changed selected identity set")
    return "\n".join(lines), groups, emitted, trace


def build_prompt_rows(
    *,
    forbidden_labels: Path | None = None,
    forbidden_mapping: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if forbidden_labels is not None or forbidden_mapping is not None:
        raise LV007PromptError("gold or arm mapping forbidden during prompt construction")
    anchors = {
        REGISTRATION: REGISTRATION_SHA256,
        PART1: PART1_SHA256,
        LV005_PROMPTS: LV005_PROMPTS_SHA256,
        TC014_SELECTIONS: TC014_SELECTIONS_SHA256,
        LV006_RESULT: LV006_RESULT_SHA256,
    }
    if any(sha256_file(path) != expected for path, expected in anchors.items()):
        raise LV007PromptError("registered input drift")

    prior_rows = _read_gzip(LV005_PROMPTS)
    prior = {(row["sample_id"], int(row["source_index"])): row for row in prior_rows}
    selected_rows = {
        (row["sample_id"], int(row["source_index"])): row
        for row in _read_gzip(TC014_SELECTIONS)
        if (row["sample_id"], int(row["source_index"])) in prior
    }
    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    nlp = spacy.load("en_core_web_sm")
    prepared: dict[str, tuple[dict[str, Mapping[str, Any]], np.ndarray, np.ndarray]] = {}
    for case in cases:
        episodes = build_episodes(case, vectors)
        matrix = np.stack(
            [np.asarray(episode.record["embedding"], dtype=np.float64) for episode in episodes]
        )
        matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
        docs = list(nlp.pipe([episode.pair.text for episode in episodes], batch_size=64))
        facets = tuple(extract_facets(doc) for doc in docs)
        idf, _ = facet_idf(facets)
        totals, overlap = weighted_facet_overlap(facets, idf)
        denominator = np.sqrt(np.outer(totals, totals))
        ochiai = np.divide(
            overlap,
            denominator,
            out=np.zeros_like(overlap),
            where=denominator > 0,
        )
        prepared[case.sample_id] = (
            {episode.identity: episode.record for episode in episodes},
            matrix,
            ochiai,
        )

    rows: list[dict[str, Any]] = []
    pairwise_reproductions = 0
    for key in sorted(prior):
        prior_row = prior[key]
        selection = selected_rows[key]["budgets"]["32000"]["opportunity"]
        selected_ids = list(selection["selected_ids"])
        records, matrix, ochiai = prepared[key[0]]
        all_ids = list(records)
        by_id = {identity: index for index, identity in enumerate(all_ids)}
        indices = [by_id[identity] for identity in selected_ids]
        cosine = matrix[np.ix_(indices, indices)]
        facet = ochiai[np.ix_(indices, indices)]
        affinity = ALPHA * cosine + (1.0 - ALPHA) * facet
        off_diagonal = affinity.copy()
        np.fill_diagonal(off_diagonal, np.nan)
        upper = affinity[np.triu_indices(len(selected_ids), 1)]
        all_singletons, _ = _community_assignment(
            affinity,
            threshold=float(np.nanmax(off_diagonal)) + 1e-12,
            cap=CAP,
        )
        capacity_partition, _ = _community_assignment(
            affinity,
            threshold=float(np.nanmin(off_diagonal)) - 1e-12,
            cap=CAP,
        )
        block, groups, emitted, trace = _community_block(
            records,
            selected_ids,
            affinity,
            selection["spread_ids"],
        )
        base_prompt = render_reader_prompt(prior_row["question"], block)
        community_prompt = base_prompt + CLOSED_THINK_SUFFIX
        repeated_prompt = _question_before_memory(base_prompt, prior_row["question"]) + CLOSED_THINK_SUFFIX

        pairwise = prior_row["arms"]["TEMPORAL_GUIDANCE"]
        pairwise_prompt = pairwise["prompt"]
        pairwise_block = pairwise["block"]
        pairwise_reproductions += int(
            hashlib.sha256(pairwise_prompt.encode("utf-8")).hexdigest()
            == pairwise["prompt_sha256"]
        )
        episode_hashes = {
            identity: hashlib.sha256(
                render_episode_element(dict(records[identity])).encode("utf-8")
            ).hexdigest()
            for identity in selected_ids
        }
        arms = {
            "PAIRWISE": {
                "block": pairwise_block,
                "block_chars": len(pairwise_block),
                "block_sha256": hashlib.sha256(pairwise_block.encode("utf-8")).hexdigest(),
                "prompt": pairwise_prompt,
                "prompt_chars": len(pairwise_prompt),
                "prompt_sha256": hashlib.sha256(pairwise_prompt.encode("utf-8")).hexdigest(),
                "groups": pairwise["groups"],
                "emitted_ids": list(pairwise["emitted_ids"]),
                "episode_element_sha256": episode_hashes,
            },
            "COMMUNITY": {
                "block": block,
                "block_chars": len(block),
                "block_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
                "prompt": community_prompt,
                "prompt_chars": len(community_prompt),
                "prompt_sha256": hashlib.sha256(community_prompt.encode("utf-8")).hexdigest(),
                "groups": groups,
                "emitted_ids": emitted,
                "episode_element_sha256": episode_hashes,
                "assignment_trace": trace,
                "absorbing_controls": {
                    "all_singleton_group_sizes": [len(group) for group in all_singletons],
                    "capacity_partition_group_sizes": [len(group) for group in capacity_partition],
                    "off_diagonal_min": float(np.nanmin(off_diagonal)),
                    "off_diagonal_max": float(np.nanmax(off_diagonal)),
                },
            },
            "COMMUNITY_QB": {
                "block": block,
                "block_chars": len(block),
                "block_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
                "prompt": repeated_prompt,
                "prompt_chars": len(repeated_prompt),
                "prompt_sha256": hashlib.sha256(repeated_prompt.encode("utf-8")).hexdigest(),
                "groups": groups,
                "emitted_ids": emitted,
                "episode_element_sha256": episode_hashes,
                "assignment_trace": trace,
                "absorbing_controls": {
                    "all_singleton_group_sizes": [len(group) for group in all_singletons],
                    "capacity_partition_group_sizes": [len(group) for group in capacity_partition],
                    "off_diagonal_min": float(np.nanmin(off_diagonal)),
                    "off_diagonal_max": float(np.nanmax(off_diagonal)),
                },
            },
        }
        rows.append(
            {
                "comparison_key": prior_row["comparison_key"],
                "sample_id": key[0],
                "source_index": key[1],
                "category": prior_row["category"],
                "population": prior_row["population"],
                "offline_direction": prior_row["offline_direction"],
                "question": prior_row["question"],
                "selected_ids": selected_ids,
                "spread_ids": list(selection["spread_ids"]),
                "arms": arms,
            }
        )
    if len(rows) != 17 or pairwise_reproductions != 17:
        raise LV007PromptError("prompt population or pairwise reproduction drift")
    manifest = {
        "schema": "lv007-prompt-manifest-v1",
        "rows": len(rows),
        "prompts": len(rows) * len(ARMS),
        "pairwise_reproductions": pairwise_reproductions,
        "selected_episode_occurrences": sum(len(row["selected_ids"]) for row in rows),
        "cache": reuse,
        "parser": {"spacy": spacy.__version__, "model": "en_core_web_sm"},
        "parameters": {"alpha": ALPHA, "threshold": THRESHOLD, "cap": CAP},
    }
    return rows, manifest


def freeze_prompts() -> dict[str, Any]:
    rows, manifest = build_prompt_rows()
    write_gzip_rows(PROMPTS, rows)
    manifest["prompts_sha256"] = sha256_file(PROMPTS)
    PROMPT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    print(json.dumps(freeze_prompts(), indent=2, sort_keys=True))

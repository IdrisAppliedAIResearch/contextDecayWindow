"""Gold-blind frozen prompt construction for LV-005."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.hh001_prompt import render_reader_prompt
from analysis.locomo_nf_development import sha256_file
from analysis.lv002_prompts import CLOSED_THINK_SUFFIX, build_prompt_rows as build_lv002_rows
from analysis.tc001_exploration import REPO_ROOT, build_episodes
from analysis.tc008_study import load_blind_manifest
from analysis.tc009_dependency_graph_probe import BLIND
from episodic._render import render_episode_element


ARMS = ("FLAT", "GROUPED", "GROUPED_CHRONO", "TEMPORAL_GUIDANCE")
ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_005"
REGISTRATION = ROOT / "LV_005_PRE_REGISTRATION.md"
AMENDMENT = ROOT / "amendments" / "AMENDMENT_001_EXACT_RENDER_TEXT.md"
PART1 = ROOT / "artifacts" / "part1_exploration.json"
PROMPTS = ROOT / "artifacts" / "preflight" / "prompts.jsonl.gz"
PROMPT_MANIFEST = ROOT / "artifacts" / "preflight" / "prompt_manifest.json"
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
LV002_PROMPTS = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "live_validation_002"
    / "artifacts"
    / "preflight"
    / "prompts.jsonl.gz"
)
LV004_ANSWERS = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "live_validation_004"
    / "artifacts"
    / "run"
    / "answers_repaired.jsonl"
)
LV004_RESULT = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "live_validation_004"
    / "artifacts"
    / "result"
    / "result.json"
)

REGISTRATION_SHA256 = "374e46bf357a1b964ace979c1e85f7aa848335fb9a28f5dbfdd73b858244c636"
AMENDMENT_SHA256 = "6c18da0b9ca75f96fee05bf725ebced8fcfd64a346a06d687af9534560fe7f60"
PART1_SHA256 = "aaa11a967d5bad65e07996b4040df340bbf29880002c8c370a58008f35c9ba03"
TC014_SELECTIONS_SHA256 = "32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7"
LV002_PROMPTS_SHA256 = "c01cf11a5e2750c2ed8c03e90c813af7263de8a7fd2c4b78bacb72aa1207d5d8"
LV004_ANSWERS_SHA256 = "639f789396807c89f3242bf9d4e2c05cbf5f349e444d5c1e38b54164c658aebe"
LV004_RESULT_SHA256 = "ee1d14b0a67d2150338ad0f1b0b5862dbc0dc033e9860c5fa50b4e3ba730cc0d"

NOTES = {
    "GROUPED": (
        "Evidence is grouped around query-relevant anchors. Groups are ordered "
        "by direct relevance. Within a group, a related spread item follows its "
        "query anchor."
    ),
    "GROUPED_CHRONO": (
        "Evidence is grouped around query-relevant anchors. Groups are ordered "
        "by direct relevance. Items within each group are ordered by when they "
        "appeared in the conversation."
    ),
    "TEMPORAL_GUIDANCE": (
        "Evidence is grouped around query-relevant anchors. Groups are ordered "
        "by direct relevance. Items within each group are in conversation order. "
        "Later means later in this conversation, not automatically a correction. "
        "For a current or latest question, prefer later evidence only when the "
        "text supports an update. For a historical question, use all relevant items."
    ),
}
ORGANIZATIONS = {
    "GROUPED": "related_groups",
    "GROUPED_CHRONO": "related_groups_chronological",
    "TEMPORAL_GUIDANCE": "related_groups_temporal_guidance",
}


class LV005PromptError(RuntimeError):
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


def _flat_block(records: Sequence[Mapping[str, Any]]) -> str:
    lines = ["<recent_context/>", "", "<retrieved_stm>"]
    lines.extend(render_episode_element(dict(record)) for record in records)
    lines.append("</retrieved_stm>")
    return "\n".join(lines)


def _organization(
    arm: str,
    records: Mapping[str, Mapping[str, Any]],
    selected_ids: Sequence[str],
    spread_ids: Sequence[str],
    parent_for_child: Mapping[str, str],
) -> tuple[str, list[dict[str, Any]], list[str]]:
    spread = set(spread_ids)
    semantic = [identity for identity in selected_ids if identity not in spread]
    selected = set(selected_ids)
    child_by_parent = {
        parent: child
        for child, parent in parent_for_child.items()
        if child in spread and parent in selected
    }
    if len(child_by_parent) != len(spread):
        raise LV005PromptError("selected parent-child join is not one-to-one")
    groups: list[dict[str, Any]] = []
    emitted: list[str] = []
    lines = [
        "<recent_context/>",
        "",
        f'<retrieved_stm organization="{ORGANIZATIONS[arm]}">',
        f"<organization_note>{NOTES[arm]}</organization_note>",
    ]
    for rank, parent in enumerate(semantic, start=1):
        identities = [parent]
        child = child_by_parent.get(parent)
        if child is not None:
            identities.append(child)
        if arm in ("GROUPED_CHRONO", "TEMPORAL_GUIDANCE"):
            identities.sort(key=lambda identity: (int(records[identity]["turn_number"]), identity))
        lines.append(f'<evidence_group rank="{rank}">')
        group_rows = []
        for position, identity in enumerate(identities):
            role = "related_spread" if identity in spread else "query_anchor"
            attributes = f'role="{role}"'
            temporal_role = None
            if arm == "TEMPORAL_GUIDANCE":
                if len(identities) == 1:
                    temporal_role = "only_retrieved_item"
                elif position == 0:
                    temporal_role = "earlier_in_conversation"
                else:
                    temporal_role = "later_in_conversation"
                attributes += f' temporal_role="{temporal_role}"'
            lines.append(f"<item {attributes}>")
            lines.append(render_episode_element(dict(records[identity])))
            lines.append("</item>")
            emitted.append(identity)
            group_rows.append(
                {
                    "identity": identity,
                    "role": role,
                    "temporal_role": temporal_role,
                    "turn": int(records[identity]["turn_number"]),
                }
            )
        lines.append("</evidence_group>")
        groups.append({"rank": rank, "items": group_rows})
    lines.append("</retrieved_stm>")
    if len(emitted) != len(set(emitted)) or set(emitted) != selected:
        raise LV005PromptError("organization changed the selected identity set")
    return "\n".join(lines), groups, emitted


def build_prompt_rows(*, forbidden_labels: Path | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if forbidden_labels is not None:
        raise LV005PromptError("gold-bearing corpus forbidden during prompt freeze")
    anchors = {
        REGISTRATION: REGISTRATION_SHA256,
        AMENDMENT: AMENDMENT_SHA256,
        PART1: PART1_SHA256,
        TC014_SELECTIONS: TC014_SELECTIONS_SHA256,
        LV002_PROMPTS: LV002_PROMPTS_SHA256,
        LV004_ANSWERS: LV004_ANSWERS_SHA256,
        LV004_RESULT: LV004_RESULT_SHA256,
    }
    if any(sha256_file(path) != expected for path, expected in anchors.items()):
        raise LV005PromptError("registered input drift")

    prior_rows, _ = build_lv002_rows()
    prior = {(row["sample_id"], int(row["source_index"])): row for row in prior_rows}
    selections = {
        (row["sample_id"], int(row["source_index"])): row
        for row in _read_gzip(TC014_SELECTIONS)
    }
    cases = {case.sample_id: case for case in load_blind_manifest(BLIND)}
    prepared = {}
    for sample_id, case in cases.items():
        dummy = np.zeros(1, dtype=np.float32)
        episodes = build_episodes(case, {pair.text: dummy for pair in case.pairs})
        prepared[sample_id] = {episode.identity: episode.record for episode in episodes}

    rows = []
    control_reproductions = 0
    for key, prior_row in prior.items():
        records = prepared[key[0]]
        allocation = selections[key]["budgets"]["32000"]["opportunity"]
        selected_ids = list(allocation["selected_ids"])
        selected_records = [records[identity] for identity in selected_ids]
        flat_block = _flat_block(selected_records)
        flat_sha = hashlib.sha256(flat_block.encode("utf-8")).hexdigest()
        if flat_sha != allocation["payload_sha256"] or flat_block != prior_row["arms"]["OPPORTUNITY"]["prompt"].split(
            "Here is what you remember of the conversation:\n\n", 1
        )[1].split("\n\nQuestion:", 1)[0]:
            raise LV005PromptError("FLAT payload does not reproduce LV-002")
        control_reproductions += 1
        trace = allocation["trace"]
        parent_for_child = dict(zip(trace["assigned_children"], trace["parent_for_child"], strict=True))
        arms: dict[str, Any] = {}
        for arm in ARMS:
            if arm == "FLAT":
                block, groups, emitted = flat_block, [], selected_ids
            else:
                block, groups, emitted = _organization(
                    arm, records, selected_ids, allocation["spread_ids"], parent_for_child
                )
            prompt = render_reader_prompt(prior_row["question"], block) + CLOSED_THINK_SUFFIX
            arms[arm] = {
                "block": block,
                "block_chars": len(block),
                "block_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
                "prompt": prompt,
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "selected_ids": selected_ids,
                "emitted_ids": emitted,
                "groups": groups,
                "episode_element_sha256": {
                    identity: hashlib.sha256(render_episode_element(dict(records[identity])).encode("utf-8")).hexdigest()
                    for identity in selected_ids
                },
            }
        rows.append(
            {
                **{field: prior_row[field] for field in (
                    "comparison_key", "sample_id", "source_index", "category", "population",
                    "offline_direction", "question", "question_sha256", "no_memory_prompt",
                    "no_memory_prompt_sha256",
                )},
                "arms": arms,
            }
        )
    rows.sort(key=lambda row: row["comparison_key"])
    if len(rows) != 17 or len({row["comparison_key"] for row in rows}) != 17:
        raise LV005PromptError("prompt population drift")
    manifest = {
        "schema": "lv005-prompt-manifest-v1",
        "rows": len(rows),
        "primary": sum(row["category"] != 5 for row in rows),
        "arms": list(ARMS),
        "prompts": len(rows) * len(ARMS),
        "control_reproductions": control_reproductions,
        "selected_identity_checks": len(rows) * len(ARMS),
        "anchors": {str(path): sha256_file(path) for path in anchors},
        "block_chars": {
            arm: [row["arms"][arm]["block_chars"] for row in rows] for arm in ARMS
        },
    }
    return rows, manifest


def freeze_prompts() -> dict[str, Any]:
    rows, manifest = build_prompt_rows()
    write_gzip_rows(PROMPTS, rows)
    manifest = {**manifest, "prompts_sha256": sha256_file(PROMPTS)}
    PROMPT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(freeze_prompts(), indent=2, sort_keys=True))

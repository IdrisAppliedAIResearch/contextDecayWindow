"""Gold-blind prompt construction for LV-002."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.hh001_prompt import render_reader_prompt
from analysis.locomo_nf_development import sha256_file
from analysis.tc001_exploration import REPO_ROOT, build_episodes
from analysis.tc008_study import load_blind_manifest
from analysis.tc009_dependency_graph_probe import BLIND
from episodic._render import render_stm_payload

TC_ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_002"
REGISTRATION = ROOT / "LV_002_PRE_REGISTRATION.md"
PART1 = ROOT / "artifacts" / "part1_exploration.json"
TC014_SELECTIONS = TC_ROOT / "artifacts" / "tc014" / "preflight" / "selections.jsonl.gz"
TC014_OUTCOMES = TC_ROOT / "artifacts" / "tc014" / "result" / "per_question.csv"
PROMPTS = ROOT / "artifacts" / "preflight" / "prompts.jsonl.gz"
PROMPT_MANIFEST = ROOT / "artifacts" / "preflight" / "prompt_manifest.json"
BUDGET = 32_000
REGISTRATION_SHA256 = "34ddd063b7c17873ae92b59f929bd788b7f66fb66d53c910a81d270bd619254a"
PART1_SHA256 = "f1dcd160b8cdf4e78673a9795861fc6ffa6affdc0b16f19907922f53fb082e60"
TC014_SELECTIONS_SHA256 = "32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7"
TC014_OUTCOMES_SHA256 = "ce73bfcb0b3c9a1d7d94e89023ce7ef7b9fbf928eb44a1669699ec3f37324bb0"


class LV002PromptError(RuntimeError):
    pass


def _read_gzip_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return list(map(json.loads, handle))


def write_gzip_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    raw = b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0) as stream:
            stream.write(raw)


def _payload(episodes: Sequence[Any], selected: Sequence[str]) -> str:
    by_id = {episode.identity: episode.record for episode in episodes}
    if len(selected) != len(set(selected)) or not set(selected) <= set(by_id):
        raise LV002PromptError("selected identity join failed")
    return render_stm_payload([], [by_id[identifier] for identifier in selected])


def build_prompt_rows(*, forbidden_labels: Path | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if forbidden_labels is not None:
        raise LV002PromptError("gold-bearing corpus forbidden during prompt freeze")
    anchors = {
        REGISTRATION: REGISTRATION_SHA256,
        PART1: PART1_SHA256,
        TC014_SELECTIONS: TC014_SELECTIONS_SHA256,
        TC014_OUTCOMES: TC014_OUTCOMES_SHA256,
    }
    if any(sha256_file(path) != expected for path, expected in anchors.items()):
        raise LV002PromptError("registered input drift")

    cases = load_blind_manifest(BLIND)
    prepared = {}
    questions = {}
    for case in cases:
        dummy = np.zeros(1, dtype=np.float32)
        prepared[case.sample_id] = build_episodes(
            case, {pair.text: dummy for pair in case.pairs}
        )
        questions.update(
            {
                (case.sample_id, question.source_index): question
                for question in case.questions
            }
        )
    frozen = {
        (row["sample_id"], int(row["source_index"])): row
        for row in _read_gzip_rows(TC014_SELECTIONS)
    }
    with TC014_OUTCOMES.open(encoding="utf-8", newline="") as handle:
        outcomes = list(csv.DictReader(handle))

    rows: list[dict[str, Any]] = []
    reproductions = 0
    for outcome in outcomes:
        cc80_complete = outcome[f"cc80_{BUDGET}_complete"] == "True"
        opportunity_complete = outcome[f"opportunity_{BUDGET}_complete"] == "True"
        if cc80_complete == opportunity_complete:
            continue
        key = (outcome["sample_id"], int(outcome["source_index"]))
        question = questions[key]
        episodes = prepared[outcome["sample_id"]]
        budget_row = frozen[key]["budgets"][str(BUDGET)]
        arms = {}
        for source_arm, name in (("cc80", "FULL_CC80"), ("opportunity", "OPPORTUNITY")):
            allocation = budget_row[source_arm]
            payload = _payload(episodes, allocation["selected_ids"])
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            if digest != allocation["payload_sha256"] or len(payload) != allocation["payload_chars"]:
                raise LV002PromptError("TC-014 payload reproduction failed")
            reproductions += 1
            prompt = render_reader_prompt(question.question, payload)
            arms[name] = {
                "prompt": prompt,
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "block_sha256": digest,
                "block_chars": len(payload),
                "selected_ids": list(allocation["selected_ids"]),
            }
        no_memory = render_reader_prompt(question.question, "")
        rows.append(
            {
                "comparison_key": outcome["question_id"],
                "sample_id": outcome["sample_id"],
                "source_index": int(outcome["source_index"]),
                "category": int(outcome["category"]),
                "population": outcome["population"],
                "offline_direction": "opportunity_gain" if opportunity_complete else "opportunity_loss",
                "question": question.question,
                "question_sha256": hashlib.sha256(question.question.encode("utf-8")).hexdigest(),
                "arms": arms,
                "no_memory_prompt": no_memory,
                "no_memory_prompt_sha256": hashlib.sha256(no_memory.encode("utf-8")).hexdigest(),
            }
        )
    rows.sort(key=lambda row: row["comparison_key"])
    if len(rows) != 17 or len({row["comparison_key"] for row in rows}) != 17:
        raise LV002PromptError("discordant prompt population drift")
    manifest = {
        "schema": "lv002-prompt-manifest-v1",
        "rows": len(rows),
        "primary": sum(row["category"] != 5 for row in rows),
        "adversarial": sum(row["category"] == 5 for row in rows),
        "payload_reproductions": reproductions,
        "anchors": {str(path): sha256_file(path) for path in anchors},
    }
    return rows, manifest


def freeze_prompts(output: Path = PROMPTS, manifest_path: Path = PROMPT_MANIFEST) -> dict[str, Any]:
    rows, manifest = build_prompt_rows()
    write_gzip_rows(output, rows)
    manifest = {**manifest, "prompts_sha256": sha256_file(output)}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


__all__ = [
    "LV002PromptError",
    "PROMPTS",
    "PROMPT_MANIFEST",
    "build_prompt_rows",
    "freeze_prompts",
    "write_gzip_rows",
]

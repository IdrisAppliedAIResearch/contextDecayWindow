"""Blind semantic plus DA aspect-v2 context construction for HH-005."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from analysis.da006_reserved_links import _member_maps
from analysis.da013_preflight import sha256_file
from analysis.hh002_run import _read_json, _write_json
from analysis.nf004_anatomy_features import load_blind_cases

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "experiments" / "comparisons" / "hh_005"
RUN = BASE / "artifacts" / "run"
PREFLIGHT = BASE / "artifacts" / "preflight"
ARMS = {16_000: "A_SEMANTIC_DA_V2_16K", 32_000: "A_SEMANTIC_DA_V2_32K"}
EXPECTED = 842
DATASET = Path(r"C:\Users\muzaf\Downloads\locomo10.json")
DA_SELECTION = (REPO / "experiments" / "components" / "biological_memory" /
                "da_098" / "artifacts" / "preflight" / "blind_allocations.jsonl.gz")
DA_SHA256 = "f5327a9b5946f217910f2de5df222da66bda59d5f7b18267f8154763f98d44f9"
ASPECT_CONTEXTS = (REPO / "experiments" / "comparisons" / "hh_003" /
                   "artifacts" / "run" / "A_EPISODIC_ASPECT" / "contexts.json")
ASPECT_CONTEXTS_SHA256 = "119a3152c5c3c300df34930a42dbb96e2454e960e48a84de2b9964d7c254caae"
ASPECT_PREDICTIONS = ASPECT_CONTEXTS.with_name("predictions.json")
ASPECT_JUDGEMENTS = ASPECT_CONTEXTS.with_name("judged_r1.json")
ASPECT_PREDICTIONS_SHA256 = "b71cfc7b1d855f0770e2fc8686125da1f820e879da0e166a2644c1517e423145"
ASPECT_JUDGEMENTS_SHA256 = "aefc8e91bd602c6449e0b5fa038b9c815070291b36024faecae937e46536ffc7"
EPISODE = re.compile(r'<episode turn="(\d+)">.*?</episode>', re.DOTALL)


class HH005Error(RuntimeError):
    pass


def _selections() -> dict[tuple[str, int], dict[str, Any]]:
    if sha256_file(DA_SELECTION) != DA_SHA256:
        raise HH005Error("DA-098 allocation differs")
    with gzip.open(DA_SELECTION, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    return {(str(row["sample_id"]), int(row["source_index"])): row for row in rows}


def _channel(tag: str, blocks: list[str]) -> str:
    return f"<{tag}>\n" + "\n".join(blocks) + f"\n</{tag}>"


def _pack_blocks(tag: str, blocks: list[str], budget: int) -> tuple[str, list[str]]:
    admitted: list[str] = []
    for block in blocks:
        if len(_channel(tag, admitted + [block])) <= budget:
            admitted.append(block)
    return _channel(tag, admitted), admitted


def _derivative(values: list[dict[str, str]], excluded: set[str],
                budget: int) -> tuple[str, list[str]]:
    admitted: list[dict[str, str]] = []
    ids: list[str] = []
    for member in values:
        dialogue_id = str(member["dialogue_id"])
        if dialogue_id in excluded or dialogue_id in ids:
            continue
        trial = admitted + [member]
        blocks = [f'<member index="{i}">\n{value["speaker"]}: {value["text"]}\n</member>'
                  for i, value in enumerate(trial, start=1)]
        if len(_channel("derivative_context_v2", blocks)) > budget:
            continue
        admitted, ids = trial, ids + [dialogue_id]
    blocks = [f'<member index="{i}">\n{value["speaker"]}: {value["text"]}\n</member>'
              for i, value in enumerate(admitted, start=1)]
    return _channel("derivative_context_v2", blocks), ids


def build_contexts(total_budget: int) -> dict[str, Any]:
    if total_budget not in ARMS:
        raise HH005Error("budget must be 16k or 32k")
    channel_budget = total_budget // 2
    if sha256_file(ASPECT_CONTEXTS) != ASPECT_CONTEXTS_SHA256:
        raise HH005Error("HH-003 ASPECT contexts differ")
    source = (_read_json(ASPECT_CONTEXTS) or {})["items"]
    selections = _selections()
    cases = load_blind_cases(DATASET)
    members, _ = _member_maps(DATASET, cases)
    output = {}
    for key, item in source.items():
        identity = (str(item["sample_id"]), int(item["source_index"]))
        selection = selections.get(identity)
        if selection is None:
            continue
        detail = item["detail"]
        recency_n = int(detail["recency_count"])
        semantic_n = int(detail["semantic_count"]) - int(detail["returned_semantic_count"])
        blocks = [match.group(0) for match in EPISODE.finditer(item["context"])]
        turns = [int(match.group(1)) for match in EPISODE.finditer(item["context"])]
        if len(blocks) != len(detail["delivered_episode_turns"]):
            raise HH005Error("HH-003 episode parse differs")
        recent_blocks = blocks[:recency_n]
        semantic_candidates = blocks[recency_n:recency_n + semantic_n]
        semantic_candidate_turns = turns[recency_n:recency_n + semantic_n]
        semantic, semantic_blocks = _pack_blocks("semantic_context", semantic_candidates,
                                                 channel_budget)
        recent_turns = turns[:recency_n]
        semantic_turns = [turn for turn, block in zip(semantic_candidate_turns,
                                                      semantic_candidates)
                          if block in semantic_blocks]
        if len(semantic) > channel_budget:
            raise HH005Error("protected semantic channel exceeds its budget")
        source_ids = list(detail["delivered_source_ids"])
        turn_to_source = {turn: source_ids[2 * index:2 * index + 2]
                          for index, turn in enumerate(turns)}
        excluded = {value for turn in (*recent_turns, *semantic_turns)
                    for value in turn_to_source[turn]}
        selected = [(str(value[0]), int(value[1]))
                    for value in selection["arch32"]["selected_members"]]
        values = [members[episode][member] for episode, member in selected]
        derivative, derivative_ids = _derivative(values, excluded, channel_budget)
        if excluded & set(derivative_ids) or len(derivative_ids) != len(set(derivative_ids)):
            raise HH005Error("derivative channel duplicates protected members")
        recent = _channel("recent_context", recent_blocks)
        context = "\n".join((recent, semantic, derivative))
        output[key] = {
            "key": key, "sample_id": identity[0], "source_index": identity[1],
            "category": int(item["category"]), "question": item["question"],
            "answer": item["answer"], "context": context,
            "context_chars": len(context), "units_delivered": semantic_n + len(derivative_ids),
            "search_time": 0.0,
            "detail": {"recent_turns": recent_turns, "semantic_turns": semantic_turns,
                       "total_retrieval_budget": total_budget,
                       "channel_budget": channel_budget,
                       "semantic_chars": len(semantic), "derivative_chars": len(derivative),
                       "derivative_source_ids": derivative_ids,
                       "da_allocation_sha256": DA_SHA256, "aspect_v1_included": False},
        }
    if len(output) != EXPECTED:
        raise HH005Error(f"population {len(output)}/{EXPECTED}")
    return {"schema": "hh005-contexts-v2", "arm": ARMS[total_budget],
            "retrieval_budget": total_budget, "population": EXPECTED,
            "items": dict(sorted(output.items()))}


def main() -> int:
    if sha256_file(ASPECT_PREDICTIONS) != ASPECT_PREDICTIONS_SHA256:
        raise HH005Error("HH-003 ASPECT predictions differ")
    if sha256_file(ASPECT_JUDGEMENTS) != ASPECT_JUDGEMENTS_SHA256:
        raise HH005Error("HH-003 ASPECT judgements differ")
    arms = {}
    for budget, arm in ARMS.items():
        first, second = build_contexts(budget), build_contexts(budget)
        if first != second:
            raise HH005Error("context replay differs")
        path = RUN / arm / "contexts.json"
        _write_json(path, first)
        chars = [row["context_chars"] for row in first["items"].values()]
        arms[arm] = {"contexts_sha256": sha256_file(path),
                     "context_chars": {"min": min(chars), "max": max(chars)},
                     "semantic_max": max(row["detail"]["semantic_chars"] for row in first["items"].values()),
                     "derivative_max": max(row["detail"]["derivative_chars"] for row in first["items"].values())}
    result = {"schema": "hh005-preflight-v2", "status": "PASS", "population": EXPECTED,
              "byte_identical_replay": True, "arms": arms,
              "aspect_predictions_sha256": ASPECT_PREDICTIONS_SHA256,
              "aspect_judgements_sha256": ASPECT_JUDGEMENTS_SHA256}
    _write_json(PREFLIGHT / "g0_g3.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

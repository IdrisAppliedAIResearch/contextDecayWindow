"""Oracle second-hop capacity analysis for DA-048."""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import DATASET_SHA256, identity, sha256_file

ENVELOPE_SHA256 = "e1f4ece6c1e55010ee7825a4ff8c56778834a8ae03cc6fa9eea5795a7ee0d7cc"
CONTINUATION_SHA256 = "8ea82cc737b65bf457e05bf921043907d70f0f82f0e878b340ab6c7f04c41bd3"
DA046_PATHS_SHA256 = "ec054430acce0d54c9cbbb08f63cc8fa07fb4a58fc20ca2eea68a58dff59f119"


class DA048AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _records(dataset_path: Path) -> dict[str, dict[str, Any]]:
    if sha256_file(dataset_path) != DATASET_SHA256:
        raise DA048AnalysisError("Dataset differs")
    output = {}
    for row in json.loads(dataset_path.read_text(encoding="utf-8")):
        question_id = str(row["question_id"])
        episodes: dict[str, tuple[str, str]] = {}
        gold: set[str] = set()
        for session_order, (session_id, turns) in enumerate(
            zip(row["haystack_session_ids"], row["haystack_sessions"], strict=True)
        ):
            session = identity(question_id, str(session_order), str(session_id))
            episode_order = 0
            for start in range(0, len(turns) - 1, 2):
                first, second = turns[start:start + 2]
                if first.get("role") != "user" or second.get("role") != "assistant":
                    continue
                user, assistant = str(first.get("content", "")), str(second.get("content", ""))
                episode_text = f"User: {user}\nAssistant: {assistant}"
                episode_id = identity(question_id, session, str(episode_order), "episode", episode_text)
                members = []
                for turn_offset, turn in enumerate((first, second)):
                    role = str(turn.get("role", "")).strip().capitalize()
                    text = f"{role}: {turn.get('content', '')}"
                    turn_id = identity(question_id, session, str(episode_order), str(turn_offset),
                                       str(turn["role"]), text)
                    members.append(turn_id)
                    if bool(turn.get("has_answer")):
                        gold.add(turn_id)
                episodes[episode_id] = (members[0], members[1])
                episode_order += 1
        output[question_id] = {"episodes": episodes, "gold": gold,
                               "question_type": str(row.get("question_type", "unknown"))}
    return output


def _delivered(actions: Sequence[Mapping[str, Any]], episodes: Mapping[str, Sequence[str]]) -> set[str]:
    output: set[str] = set()
    for action in actions:
        kind = str(action["kind"])
        if kind == "PAIR":
            output.update(episodes[str(action["neighbor_id"] )])
        elif kind in {"TURN", "MEMBER"}:
            output.add(episodes[str(action["neighbor_id"])][int(action["member"])])
    return output


def _paired(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    gains = sum(not row["CONTROL"] and row["TREATMENT"] for row in rows)
    losses = sum(row["CONTROL"] and not row["TREATMENT"] for row in rows)
    n = gains + losses
    tail = min(gains, losses)
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(tail + 1)) / 2**n) if n else 1.0
    return {"gains": gains, "losses": losses, "net": gains - losses,
            "ties": len(rows) - n, "discordant": n, "two_sided_exact_p": p}


def _quantile(values: Sequence[int], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def analyze(dataset_path: Path, envelope_path: Path, continuation_path: Path,
            da046_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = ((envelope_path, ENVELOPE_SHA256), (continuation_path, CONTINUATION_SHA256),
             (da046_path, DA046_PATHS_SHA256))
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA048AnalysisError("Sealed input differs")
    records = _records(dataset_path)
    envelopes = {str(row["question_id"]): row for row in _read(envelope_path)}
    continuations = {str(row["question_id"]): row for row in _read(continuation_path)}
    prior = {str(row["question_id"]): row for row in _read(da046_path)}
    rows = []
    da038_complete = 0
    for question_id in sorted(envelopes):
        envelope, stream, record = envelopes[question_id], continuations[question_id], records[question_id]
        episodes, gold = record["episodes"], record["gold"]
        direct = set().union(*(episodes[identity] for identity in envelope["direct_ids"]))
        base = (direct | _delivered(envelope["baseline_actions"], episodes)
                | _delivered(envelope["da023"]["additions"], episodes)
                | _delivered(envelope["control"]["actions"], episodes)
                | _delivered(envelope["da031_control"]["actions"], episodes)
                | _delivered(envelope["da033_control"]["actions"], episodes)
                | _delivered(envelope["da038_control"]["actions"], episodes))
        da038 = gold <= base
        da038_complete += da038
        control = bool(prior[question_id]["TREATMENT"])
        if da038 and not control:
            raise DA048AnalysisError("DA-046 control regressed below DA-038")
        missing = gold - base
        matches = []
        if not control:
            for action in stream["actions"]:
                if action["kind"] != "FRAME":
                    continue
                member_id = episodes[str(action["neighbor_id"])][int(action["member"])]
                if missing <= {member_id}:
                    matches.append(action)
        chosen = matches[0] if matches else None
        cumulative = (sum(int(action["cost"]) for action in stream["actions"]
                          if int(action["ordinal"]) <= int(chosen["ordinal"]))
                      if chosen else None)
        treatment = control or chosen is not None
        rows.append({"question_id": question_id, "question_type": record["question_type"],
                     "CONTROL": control, "TREATMENT": treatment, "da038_complete": da038,
                     "missing_members": len(missing),
                     "oracle_action": ({key: chosen[key] for key in
                                        ("ordinal", "direction", "neighbor_id", "member", "cost")}
                                       | {"temporal_distance": 2,
                                          "cumulative_chars": cumulative}
                                       if chosen else None)})
    if len(rows) != 465 or da038_complete != 232 or sum(row["CONTROL"] for row in rows) != 250:
        raise DA048AnalysisError("Frozen availability anchors differ")
    complete = {arm: sum(row[arm] for row in rows) for arm in ("CONTROL", "TREATMENT")}
    contrast = _paired(rows)
    gains = [row for row in rows if not row["CONTROL"] and row["TREATMENT"]]
    groups = {}
    for group in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == group]
        groups[group] = {"n": len(cell), "complete": {arm: sum(row[arm] for row in cell)
                                                       for arm in complete},
                         "contrast": _paired(cell)}
    nonnegative = all(group["contrast"]["losses"] == 0 for group in groups.values())
    if contrast["gains"] >= 5 and contrast["losses"] == 0 and nonnegative:
        status = "SECOND_HOP_CAPACITY_SIGNAL"
    elif contrast["gains"] >= 1 and contrast["losses"] == 0 and nonnegative:
        status = "WEAK_SECOND_HOP_CAPACITY_SIGNAL"
    else:
        status = "NO_SECOND_HOP_CAPACITY_SIGNAL"
    ordinals = [int(row["oracle_action"]["ordinal"]) for row in gains]
    costs = [int(row["oracle_action"]["cost"]) for row in gains]
    cumulative = [int(row["oracle_action"]["cumulative_chars"]) for row in gains]
    result = {"schema": "da048-directional-continuation-result-v1", "status": status,
              "population": len(rows), "da038_complete": da038_complete,
              "complete": complete, "contrast": contrast, "by_question_type": groups,
              "oracle_gains": {"n": len(gains),
                               "ordinal": {"p10": _quantile(ordinals, .1),
                                           "p50": _quantile(ordinals, .5),
                                           "p90": _quantile(ordinals, .9)},
                               "frame_chars": {"p10": _quantile(costs, .1),
                                               "p50": _quantile(costs, .5),
                                               "p90": _quantile(costs, .9)},
                               "cumulative_chars": {"p10": _quantile(cumulative, .1),
                                                    "p50": _quantile(cumulative, .5),
                                                    "p90": _quantile(cumulative, .9)}},
              "protected_payload_mutations": 0,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "evidence-aware one-frame oracle over frozen second-hop stream only"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(dataset_path: Path, envelope_path: Path, continuation_path: Path,
                 da046_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, envelope_path, continuation_path, da046_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "outcomes.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da048-result-") as directory:
        replay_result, replay_rows = analyze(dataset_path, envelope_path, continuation_path, da046_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(artifact)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
    if not identical:
        raise DA048AnalysisError("Analysis replay differs")
    return result


__all__ = ["DA048AnalysisError", "analyze", "run_analysis"]

"""Bounded replaceable parent-to-child frames for orphan residuals."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da032_audit import distribution
from analysis.da044_allocation import parse_block, render_block
from analysis.da061_bigrams import bigrams, ordered_tokens
from analysis.da073_ordered_lattice import _features, _typed_features, _unique
from analysis.da078_allocation import _protected_descriptors

FRAME_CAP = 2_048
DA083_SHA256 = "c26c814c8c8ef0528c33480767e885e018865afbe86e310e380af1d5b8cdca55"
DA079_SHA256 = "08c06d6640edd6cd4579fb350033db11b7d912e7664b6659e27d603882e60ed1"
DA078_SHA256 = "e1e0aa2674dc103e2e6b03d7ddf81b4daf2f600cb5eb9950809b6d7a2e7e96cd"
DA045_SHA256 = "ba527732771E4BCBA3D7E5B289B5CB8F3F9DAF9B53F0601ACAC293E401EF2A0A".lower()


class DA084Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _member_features(member: Mapping[str, Any], query_unigrams: Sequence[str],
                     query_bigrams: Sequence[tuple[str, str]]) -> frozenset[str]:
    output = set(_features(str(member["text"]), query_unigrams, query_bigrams))
    output.update(_typed_features(
        str(member["text"]), str(member["speaker"]).upper(),
        query_unigrams, query_bigrams,
    ))
    return frozenset(output)


def analyze(longmem_path: Path, population_path: Path, da083_path: Path,
            da079_path: Path, da078_path: Path,
            da045_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = (
        (da083_path, DA083_SHA256),
        (da079_path, DA079_SHA256),
        (da078_path, DA078_SHA256),
        (da045_path, DA045_SHA256),
    )
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA084Error("Sealed input differs")
    paths = {
        str(row["key"]): row for row in _read(da083_path)
        if row["state"] == "ORPHAN_PARENT"
    }
    residuals = {str(row["key"]): row for row in _read(da079_path)}
    selections = {str(row["question_id"]): row for row in read_gzip(da078_path)}
    streams = {str(row["question_id"]): row for row in read_gzip(da045_path)}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in paths
    }
    if not (len(paths) == len(records) == 5):
        raise DA084Error("Orphan population differs")

    rows = []
    for question_id in sorted(paths):
        residual = residuals[question_id]
        selection = selections[question_id]
        stream = streams[question_id]
        record = records[question_id]
        by_id = {
            episode.candidate.identity: episode
            for episode in record.episodes
        }
        pair_for = lambda identity: by_id[identity].members
        target = str(residual["carrier"])
        matching = [
            edge for edge in stream["baseline_actions"]
            if str(edge["neighbor_id"]) == target
        ]
        parents = _unique([str(edge["seed_id"]) for edge in matching])
        if len(parents) != 1:
            raise DA084Error("Orphan target does not have one frozen parent")
        parent = parents[0]
        direction = int(matching[0]["direction"])
        if any(int(edge["direction"]) != direction for edge in matching):
            raise DA084Error("Frozen parent direction differs")

        da038_row = {**selection, "treatment": selection["da038_control"]}
        descriptors = _protected_descriptors(da038_row, pair_for)
        for action in selection["treatment"]["actions"]:
            if action["kind"] == "MEMBER":
                descriptors.append((str(action["neighbor_id"]), (int(action["member"]),)))
        prompt_members = {
            (identity, index)
            for identity, members in descriptors
            for index in members
        }
        if any(identity == parent for identity, _ in prompt_members):
            raise DA084Error("Orphan parent is represented in DA-078")

        query_sequence = ordered_tokens(record.question)
        query_unigrams = _unique(query_sequence)
        query_bigrams = _unique(bigrams(query_sequence))
        prompt_features: set[str] = set()
        for identity, index in prompt_members:
            prompt_features.update(_member_features(
                pair_for(identity)[index], query_unigrams, query_bigrams
            ))

        sentinel = str(stream["da038_control"]["sentinel"])
        attempts = [
            ("PARENT", parent, 0),
            ("PARENT", parent, 1),
            ("CHILD", target, int(residual["required_member"])),
        ]
        actions, cumulative, peak = [], 0, 0
        parent_features: set[str] = set()
        parent_exposed = 0
        child_exposed = False
        for ordinal, (relation, identity, member_index) in enumerate(attempts, start=1):
            member = pair_for(identity)[member_index]
            block = render_block(sentinel, ordinal, member)
            if parse_block(block, sentinel) != (
                ordinal, str(member["speaker"]), str(member["text"])
            ):
                raise DA084Error("Canonical bridge decode differs")
            fits = len(block) <= FRAME_CAP
            actions.append({
                "ordinal": ordinal,
                "relation": relation,
                "episode_id": identity,
                "member": member_index,
                "kind": "FRAME" if fits else "OVERFLOW",
                "attempt_chars": len(block),
                "chars": len(block) if fits else 0,
            })
            if fits:
                cumulative += len(block)
                peak = max(peak, len(block))
                if relation == "PARENT":
                    parent_exposed += 1
                    parent_features.update(_member_features(
                        member, query_unigrams, query_bigrams
                    ))
                else:
                    child_exposed = True
        if parent_exposed == 2 and child_exposed:
            state = "COMPLETE_PARENT_BRIDGE"
        elif parent_exposed > 0 and child_exposed:
            state = "PARTIAL_PARENT_BRIDGE"
        else:
            state = "NO_PARENT_BRIDGE"
        rows.append({
            "key": question_id,
            "question_type": record.question_type,
            "blocker": str(residual["blocker"]),
            "parent": parent,
            "child": target,
            "required_child_member": int(residual["required_member"]),
            "direction": direction,
            "state": state,
            "parent_members_exposed": parent_exposed,
            "child_exposed": child_exposed,
            "parent_feature_count": len(parent_features),
            "parent_new_vs_prompt": len(parent_features - prompt_features),
            "peak_frame_chars": peak,
            "cumulative_frame_chars": cumulative,
            "prompt_char_delta": 0,
            "edge": {
                "type": "temporal_parent_child",
                "parent": parent,
                "child": target,
                "member": int(residual["required_member"]),
                "direction": direction,
            },
            "actions": actions,
        })

    states = Counter(row["state"] for row in rows)
    result = {
        "schema": "da084-orphan-parent-bridge-v1",
        "status": "POSTHOC_ORPHAN_PARENT_BRIDGE_CHARACTERIZED",
        "orphans": len(rows),
        "states": dict(states),
        "parent_members_exposed": distribution([
            row["parent_members_exposed"] for row in rows
        ]),
        "parent_new_vs_prompt": distribution([
            row["parent_new_vs_prompt"] for row in rows
        ]),
        "peak_frame_chars": distribution([row["peak_frame_chars"] for row in rows]),
        "cumulative_frame_chars": distribution([
            row["cumulative_frame_chars"] for row in rows
        ]),
        "protected_da078_mutations": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "posthoc bounded parent-child exposure only; no reader, stopping, transfer, delivery, or adoption",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                payload = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                output.write(payload.encode())


def run_analysis(longmem_path: Path, population_path: Path, da083_path: Path,
                 da079_path: Path, da078_path: Path, da045_path: Path,
                 output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(
        longmem_path, population_path, da083_path, da079_path, da078_path, da045_path
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "bridges.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da084-") as directory:
        replay_result, replay_rows = analyze(
            longmem_path, population_path, da083_path, da079_path, da078_path, da045_path
        )
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["bridges_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA084Error("DA-084 replay differs")
    return result


__all__ = ["DA084Error", "analyze", "run_analysis"]

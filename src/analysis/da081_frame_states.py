"""Evidence-blind query-feature transitions for DA-080 residual frames."""

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
from analysis.da061_bigrams import bigrams, ordered_tokens
from analysis.da073_ordered_lattice import _features, _typed_features, _unique
from analysis.da078_allocation import _protected_descriptors

DA079_SHA256 = "08c06d6640edd6cd4579fb350033db11b7d912e7664b6659e27d603882e60ed1"
DA078_SHA256 = "e1e0aa2674dc103e2e6b03d7ddf81b4daf2f600cb5eb9950809b6d7a2e7e96cd"
DA045_SHA256 = "ba527732771e4bcba3d7e5b289b5cb8f3f9daf9b53f0601acac293e401ef2a0a"


class DA081Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _member_features(member: Mapping[str, Any], query_unigrams: Sequence[str],
                     query_bigrams: Sequence[tuple[str, str]]) -> frozenset[str]:
    text = str(member["text"])
    role = str(member["speaker"]).upper()
    output = set(_features(text, query_unigrams, query_bigrams))
    output.update(_typed_features(text, role, query_unigrams, query_bigrams))
    return frozenset(output)


def analyze(longmem_path: Path, population_path: Path, da079_path: Path,
            da078_path: Path, da045_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = (
        (da079_path, DA079_SHA256),
        (da078_path, DA078_SHA256),
        (da045_path, DA045_SHA256),
    )
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA081Error("Sealed input differs")
    residuals = {str(row["key"]): row for row in _read(da079_path)}
    selections = {str(row["question_id"]): row for row in read_gzip(da078_path)}
    streams = {str(row["question_id"]): row for row in read_gzip(da045_path)}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in residuals
    }
    if not (len(residuals) == len(records) == 13 and set(residuals) <= set(streams)):
        raise DA081Error("Population differs")

    rows = []
    for question_id in sorted(residuals):
        residual = residuals[question_id]
        selection = selections[question_id]
        stream = streams[question_id]
        record = records[question_id]
        by_id = {
            episode.candidate.identity: episode
            for episode in record.episodes
        }
        pair_for = lambda identity: by_id[identity].members
        query_sequence = ordered_tokens(record.question)
        query_unigrams = _unique(query_sequence)
        query_bigrams = _unique(bigrams(query_sequence))

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
        required_key = (str(residual["carrier"]), int(residual["required_member"]))
        if required_key in prompt_members:
            raise DA081Error("Residual requirement is already in DA-078 prompt")
        prompt_features: set[str] = set()
        for identity, index in prompt_members:
            prompt_features.update(_member_features(
                pair_for(identity)[index], query_unigrams, query_bigrams
            ))
        cumulative = set(prompt_features)
        prior_signatures: Counter[frozenset[str]] = Counter()
        earlier_state_changes = 0
        frame_index = 0
        target = None
        prior_order = 0
        for action in stream["treatment"]["actions"]:
            ordinal = int(action["ordinal"])
            if ordinal <= prior_order:
                raise DA081Error("DA-045 ordinal order differs")
            prior_order = ordinal
            if action["kind"] != "FRAME":
                continue
            frame_index += 1
            identity = str(action["neighbor_id"])
            member_index = int(action["member"])
            member = pair_for(identity)[member_index]
            rendered = str(action["block"])
            expected_suffix = f"{member['speaker']}: {member['text']}"
            if not rendered.endswith(expected_suffix):
                raise DA081Error("Rendered frame source replay differs")
            signature = _member_features(member, query_unigrams, query_bigrams)
            new_at_arrival = signature - cumulative
            is_required = (identity, member_index) == required_key
            if is_required:
                if not signature:
                    state = "NO_QUERY_FEATURES"
                elif not new_at_arrival:
                    state = "REDUNDANT_AT_ARRIVAL"
                else:
                    state = "NOVEL_AT_ARRIVAL"
                target = {
                    "key": question_id,
                    "question_type": record.question_type,
                    "blocker": str(residual["blocker"]),
                    "carrier": identity,
                    "required_member": member_index,
                    "required_ordinal": ordinal,
                    "required_frame_index": frame_index,
                    "state": state,
                    "feature_count": len(signature),
                    "new_vs_prompt": len(signature - prompt_features),
                    "new_at_arrival": len(new_at_arrival),
                    "exact_signature_prior_count": prior_signatures[signature],
                    "earlier_state_change_frames": earlier_state_changes,
                    "prompt_feature_count": len(prompt_features),
                    "cumulative_feature_count_before": len(cumulative),
                }
                break
            if new_at_arrival:
                earlier_state_changes += 1
            prior_signatures[signature] += 1
            cumulative.update(signature)
        if target is None:
            raise DA081Error("Required frame is absent from sealed stream")
        rows.append(target)

    states = Counter(row["state"] for row in rows)
    result = {
        "schema": "da081-frame-state-transition-anatomy-v1",
        "status": "POSTHOC_FRAME_STATE_TRANSITIONS_CHARACTERIZED",
        "residuals": len(rows),
        "states": dict(states),
        "feature_count": distribution([row["feature_count"] for row in rows]),
        "new_vs_prompt": distribution([row["new_vs_prompt"] for row in rows]),
        "new_at_arrival": distribution([row["new_at_arrival"] for row in rows]),
        "exact_signature_prior_count": distribution([
            row["exact_signature_prior_count"] for row in rows
        ]),
        "earlier_state_change_frames": distribution([
            row["earlier_state_change_frames"] for row in rows
        ]),
        "required_frame_index": distribution([row["required_frame_index"] for row in rows]),
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "posthoc exact query-feature state anatomy only; no stopping, reader, transfer, delivery, or adoption",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                payload = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                output.write(payload.encode())


def run_analysis(longmem_path: Path, population_path: Path, da079_path: Path,
                 da078_path: Path, da045_path: Path,
                 output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(
        longmem_path, population_path, da079_path, da078_path, da045_path
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "transitions.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da081-") as directory:
        replay_result, replay_rows = analyze(
            longmem_path, population_path, da079_path, da078_path, da045_path
        )
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["transitions_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA081Error("DA-081 replay differs")
    return result


__all__ = ["DA081Error", "analyze", "run_analysis"]

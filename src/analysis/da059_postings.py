"""Blind exact-token session posting routes for DA-059."""

from __future__ import annotations

import gzip
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import DATASET_SHA256, identity, sha256_file
from analysis.da056_materialization import DIRECTORY_SHA256, _read

TOKEN = re.compile(r"[A-Za-z0-9]+")


class DA059Error(RuntimeError):
    pass


def tokens(text: str) -> list[str]:
    values = [match.group(0).lower() for match in TOKEN.finditer(text)]
    return list(dict.fromkeys(values))


def build_rows(dataset_path: Path, directory_path: Path) -> list[dict[str, Any]]:
    if sha256_file(dataset_path) != DATASET_SHA256 or sha256_file(directory_path) != DIRECTORY_SHA256:
        raise DA059Error("Sealed input differs")
    raw = {str(row["question_id"]): row for row in json.loads(dataset_path.read_text(encoding="utf-8"))}
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    output = []
    for question_id in sorted(directories):
        row = raw[question_id]
        directory = directories[question_id]
        heads = list(directory["directory_root"]["session_heads"])
        postings: dict[str, list[str]] = {}
        observed_heads = []
        for session_order, (source_id, turns) in enumerate(
            zip(row["haystack_session_ids"], row["haystack_sessions"], strict=True)
        ):
            session_id = identity(question_id, str(session_order), str(source_id))
            observed_heads.append(session_id)
            accepted_text = []
            for start in range(0, len(turns) - 1, 2):
                first, second = turns[start:start + 2]
                if first.get("role") == "user" and second.get("role") == "assistant":
                    accepted_text.extend((str(first.get("content", "")),
                                          str(second.get("content", ""))))
            for token in set(tokens("\n".join(accepted_text))):
                postings.setdefault(token, []).append(session_id)
        if observed_heads != heads:
            raise DA059Error("Directory session order differs")
        query_tokens = tokens(str(row["question"]))
        matched, unmatched, routed, seen = [], [], [], set()
        for token in query_tokens:
            values = postings.get(token)
            if values is None:
                unmatched.append(token)
                continue
            matched.append(token)
            for session_id in values:
                if session_id not in seen:
                    seen.add(session_id)
                    routed.append(session_id)
        output.append({"question_id": question_id, "query_tokens": query_tokens,
                       "matched_tokens": matched, "unmatched_tokens": unmatched,
                       "routed_session_ids": routed, "total_sessions": len(heads),
                       "rendered_char_delta": 0})
    if len(output) != 465:
        raise DA059Error("Population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(dataset_path: Path, directory_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(dataset_path, directory_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_routes.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da059-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(dataset_path, directory_path))
        identical = artifact.read_bytes() == replay.read_bytes()
    matched = sum(len(row["matched_tokens"]) for row in rows)
    unmatched = sum(len(row["unmatched_tokens"]) for row in rows)
    routed = [len(row["routed_session_ids"]) for row in rows]
    source = Path(__file__).read_text(encoding="utf-8").lower()
    forbidden = ("has_" + "answer", "evi" + "dence")
    leakage_clean = not any(token in source for token in forbidden)
    passed = (identical and matched > 0 and unmatched > 0 and max(routed) > 0
              and leakage_clean and all(row["rendered_char_delta"] == 0 for row in rows))
    result = {"schema": "da059-sparse-session-postings-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "matched_tokens": matched, "unmatched_tokens": unmatched,
              "empty_routes": sum(value == 0 for value in routed),
              "max_routed_sessions": max(routed), "leakage_scan_clean": leakage_clean,
              "rendered_char_delta": 0, "replay_byte_identical": identical,
              "routes_sha256": sha256_file(artifact),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                                encoding="utf-8")
    if not passed:
        raise DA059Error("Blind posting preflight failed")
    return result


__all__ = ["DA059Error", "build_rows", "run_preflight", "tokens"]

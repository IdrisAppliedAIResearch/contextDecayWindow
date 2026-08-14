"""NF-003 exploration: audit session-touch against answer-episode delivery.

Part 1 measured whether packing touched an annotated answer session. Once the
ranking unit becomes an episode, touching that session does not imply that the
answer-bearing episode was delivered. This module reconstructs both ranking
arms and measures both units without making embedding or model calls.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from analysis import nf002_streams
from analysis.nf003_ranking import compose_episodes, pack

SCHEMA = "nf003-surrogate-audit-v1"
PART1 = Path(
    "experiments/components/biological_memory/nf_003/artifacts/part1_record.json"
)
OUTPUT = Path(
    "experiments/components/biological_memory/nf_003/artifacts/"
    "surrogate_audit.json"
)
PART1_LF_SHA256 = "2d29387251b109f780d7a2fe86e7a1d3244eb0f5a73515b1be1d8e7dda7e506f"


class SurrogateAuditError(RuntimeError):
    pass


def _lf_sha256(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _paired(rows: Iterable[dict[str, Any]], baseline: str, treatment: str) -> dict[str, int]:
    gains = losses = ties = 0
    for row in rows:
        before = bool(row[baseline])
        after = bool(row[treatment])
        if after and not before:
            gains += 1
        elif before and not after:
            losses += 1
        else:
            ties += 1
    return {"gains": gains, "losses": losses, "ties": ties}


def evaluate(repository_root: Path) -> dict[str, Any]:
    part1_path = repository_root / PART1
    part1_sha = _lf_sha256(part1_path)
    if part1_sha != PART1_LF_SHA256:
        raise SurrogateAuditError(
            f"Part 1 artifact changed: expected {PART1_LF_SHA256}, observed {part1_sha}"
        )

    part1 = json.loads(part1_path.read_text(encoding="utf-8"))
    treatment_rows = {row["question_id"]: row for row in part1["rows"]}
    streams, anchor = nf002_streams.load_streams()
    streams_by_id = {stream.question_id: stream for stream in streams}
    items = json.loads(nf002_streams.DATASET.read_text(encoding="utf-8"))

    unknown = sorted(set(treatment_rows) - set(streams_by_id))
    if unknown:
        raise SurrogateAuditError(f"Part 1 rows absent from the baseline: {unknown[:3]}")

    rows: list[dict[str, Any]] = []
    for item in items:
        question_id = item["question_id"]
        treatment = treatment_rows.get(question_id)
        stream = streams_by_id.get(question_id)
        if treatment is None or stream is None:
            continue

        episodes = compose_episodes(item)
        session_rank = {
            candidate.session_id: candidate.rank for candidate in stream.candidates
        }
        missing_sessions = sorted(
            {episode.session_id for episode in episodes} - set(session_rank)
        )
        if missing_sessions:
            raise SurrogateAuditError(
                f"{question_id}: episodes absent from ranking: {missing_sessions[:3]}"
            )

        inherited_order = np.array(
            sorted(
                range(len(episodes)),
                key=lambda index: (
                    session_rank[episodes[index].session_id],
                    episodes[index].index,
                ),
            )
        )
        answer_sessions = set(item["answer_session_ids"])
        baseline_sessions, baseline_strict = pack(
            episodes, inherited_order, answer_sessions
        )

        rows.append(
            {
                "question_id": question_id,
                "question_type": item.get("question_type", "unknown"),
                "whole_session_candidate": nf002_streams.pack_all(stream)[0] > 0,
                "baseline_session_touch": baseline_sessions > 0,
                "baseline_answer_episode": baseline_strict > 0,
                "treatment_session_touch": treatment[
                    "episode_ranked_sessions_touched"
                ]
                > 0,
                "treatment_answer_episode": treatment[
                    "episode_ranked_episodes_delivered"
                ]
                > 0,
            }
        )

    if len(rows) != len(treatment_rows):
        raise SurrogateAuditError(
            f"joined {len(rows)} of {len(treatment_rows)} Part 1 rows"
        )

    def measure(baseline: str, treatment: str) -> dict[str, Any]:
        return {
            "baseline_hits": sum(bool(row[baseline]) for row in rows),
            "treatment_hits": sum(bool(row[treatment]) for row in rows),
            "paired": _paired(rows, baseline, treatment),
        }

    return {
        "schema": SCHEMA,
        "inputs": {
            "dataset": {
                "path": str(nf002_streams.DATASET),
                "sha256": nf002_streams.DATASET_SHA256,
            },
            "part1_artifact": {
                "path": PART1.as_posix(),
                "lf_sha256": part1_sha,
            },
            "baseline_anchor": anchor,
        },
        "population": {
            "evaluated_items": len(rows),
            "excluded_without_turn_level_flags": len(streams) - len(rows),
        },
        "session_touch_measure": measure(
            "baseline_session_touch", "treatment_session_touch"
        ),
        "strict_answer_episode_measure": measure(
            "baseline_answer_episode", "treatment_answer_episode"
        ),
        "nf002_strict_context": measure(
            "whole_session_candidate", "baseline_answer_episode"
        ),
        "surrogate_gap": {
            "baseline_session_hit_without_answer_episode": sum(
                row["baseline_session_touch"] and not row["baseline_answer_episode"]
                for row in rows
            ),
            "treatment_session_hit_without_answer_episode": sum(
                row["treatment_session_touch"] and not row["treatment_answer_episode"]
                for row in rows
            ),
        },
        "model_calls": 0,
        "embedding_calls": 0,
        "rows": sorted(rows, key=lambda row: row["question_id"]),
    }


def write(repository_root: Path) -> Path:
    output = repository_root / OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evaluate(repository_root), ensure_ascii=False, indent=1, sort_keys=True)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output

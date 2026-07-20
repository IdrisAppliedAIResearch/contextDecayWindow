"""Export the accepted Study 003 run as a deterministic web-demo replay.

The full accepted transcript remains a local, ignored execution artifact. This
script combines it with the tracked study script and canonical metric CSVs to
produce the compact JSON artifact consumed by ``demo/``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = REPO_ROOT / "experiments" / "study_003"
RAW_ROOT = STUDY_ROOT / "runs" / "study_003_full_002" / "iterative"
CANONICAL_ROOT = STUDY_ROOT / "runs" / "run_001"
SCRIPT_PATH = STUDY_ROOT / "script.json"
OUTPUT_PATH = REPO_ROOT / "demo" / "app" / "data" / "study-003-replay.json"

METRIC_FILES = (
    "K_values.csv",
    "N_values.csv",
    "consolidation_events.csv",
    "memory_store.csv",
    "model_performance.csv",
    "retrieval_events.csv",
    "rule_detection.csv",
    "topic_events.csv",
)
LTM_FILES = (
    "episode_scores.csv",
    "filter_triggers.csv",
    "merge_relabel_events.csv",
    "promotion_events.csv",
)

TOPICS = (
    {
        "id": "rules",
        "label": "Pinned rules",
        "shortLabel": "Rules",
        "turnStart": 1,
        "turnEnd": 2,
        "accent": "mint",
        "description": "Behavioral constraints retained for all 120 turns.",
    },
    {
        "id": "bridge",
        "label": "Bridge engineering",
        "shortLabel": "Bridge",
        "turnStart": 3,
        "turnEnd": 30,
        "accent": "cyan",
        "description": "Halcyon Crossing specifications and structural analysis.",
    },
    {
        "id": "renaissance",
        "label": "Renaissance art",
        "shortLabel": "Art",
        "turnStart": 31,
        "turnEnd": 60,
        "accent": "violet",
        "description": "Patronage, perspective, and the Annunciation of Forlì.",
    },
    {
        "id": "monetary",
        "label": "Monetary policy",
        "shortLabel": "Policy",
        "turnStart": 61,
        "turnEnd": 90,
        "accent": "amber",
        "description": "Taylor rules, central banking, and inflation thresholds.",
    },
    {
        "id": "marine",
        "label": "Marine biology",
        "shortLabel": "Marine",
        "turnStart": 91,
        "turnEnd": 111,
        "accent": "blue",
        "description": "Deep-sea ecology and Vampyroteuthis infernalis.",
    },
    {
        "id": "probes",
        "label": "Recall probes",
        "shortLabel": "Probes",
        "turnStart": 112,
        "turnEnd": 120,
        "accent": "rose",
        "description": "Locked questions testing early, middle, and late recall.",
    },
)

PROBE_DOMAINS = {
    112: "bridge",
    113: "bridge",
    114: "rules",
    115: "renaissance",
    116: "renaissance",
    117: "renaissance",
    118: "marine",
    119: "marine",
    120: "all",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed replay instead of replacing it.",
    )
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _as_int(value: Any, default: int = 0) -> int:
    if value in (None, "", "---"):
        return default
    return int(float(value))


def _as_float(value: Any, default: float = 0.0) -> float:
    if value in (None, "", "---"):
        return default
    return float(value)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _repair_mojibake(value: str) -> str:
    """Repair the known Windows-1252/UTF-8 round trip in raw user messages."""

    if not any(marker in value for marker in ("â", "Ã", "Â", "ð")):
        return value
    try:
        return value.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def _topic_for_turn(turn: int) -> str:
    if turn <= 2:
        return "rules"
    if turn <= 30:
        return "bridge"
    if turn <= 60:
        return "renaissance"
    if turn <= 90:
        return "monetary"
    if turn <= 111:
        return "marine"
    return "probes"


def _canonical_artifacts() -> dict[str, Path]:
    artifacts = {
        f"condition_c/metrics/{name}": CANONICAL_ROOT
        / "condition_c"
        / "metrics"
        / name
        for name in METRIC_FILES
    }
    artifacts.update(
        {
            f"ltm_analysis/{name}": CANONICAL_ROOT / "ltm_analysis" / name
            for name in LTM_FILES
        }
    )
    return artifacts


def _verify_raw_matches_canonical() -> None:
    for name in METRIC_FILES:
        raw_path = RAW_ROOT / "metrics" / name
        canonical_path = CANONICAL_ROOT / "condition_c" / "metrics" / name
        if _sha256(raw_path) != _sha256(canonical_path):
            raise ValueError(f"Raw metric does not match canonical artifact: {name}")

    for name in LTM_FILES:
        raw_path = RAW_ROOT / "ltm_analysis" / name
        canonical_path = CANONICAL_ROOT / "ltm_analysis" / name
        if _sha256(raw_path) != _sha256(canonical_path):
            raise ValueError(f"Raw LTM metric does not match canonical artifact: {name}")


def _load_canonical_metrics() -> dict[str, Any]:
    metric_root = CANONICAL_ROOT / "condition_c" / "metrics"
    ltm_root = CANONICAL_ROOT / "ltm_analysis"

    by_turn: dict[str, dict[int, dict[str, str]]] = {}
    for key, filename in (
        ("memory", "memory_store.csv"),
        ("performance", "model_performance.csv"),
        ("rules", "rule_detection.csv"),
        ("consolidation", "consolidation_events.csv"),
    ):
        rows = _load_csv(metric_root / filename)
        turn_key = "turn_number" if key in {"rules", "consolidation"} else "turn"
        by_turn[key] = {_as_int(row[turn_key]): row for row in rows}

    promotion_events = {
        _as_int(row["turn"]): row
        for row in _load_csv(ltm_root / "promotion_events.csv")
    }
    scores_by_event: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in _load_csv(ltm_root / "episode_scores.csv"):
        scores_by_event[_as_int(row["turn"])].append(row)

    return {
        **by_turn,
        "promotion": promotion_events,
        "scores": scores_by_event,
    }


def _context_entries(row: dict[str, Any]) -> list[dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for episode in [*row.get("n_episodes", []), *row.get("k_episodes", [])]:
        episode_id = episode["id"]
        existing = entries.get(episode_id)
        retrieval_type = episode.get("retrieval_type", "N")
        if existing:
            types = set(existing["retrievalType"].split("+"))
            types.update(retrieval_type)
            existing["retrievalType"] = "+".join(
                item for item in ("K", "N") if item in types
            )
            existing["similarity"] = max(
                existing["similarity"], _as_float(episode.get("sim_score"))
            )
            existing["decay"] = max(
                existing["decay"], _as_float(episode.get("decay_score"))
            )
            continue

        normalized_types = set(retrieval_type)
        entries[episode_id] = {
            "episodeId": episode_id,
            "sourceTurn": _as_int(episode["turn_number"]),
            "retrievalType": "+".join(
                item for item in ("K", "N") if item in normalized_types
            ),
            "similarity": round(_as_float(episode.get("sim_score")), 4),
            "decay": round(_as_float(episode.get("decay_score")), 4),
        }

    return sorted(entries.values(), key=lambda item: item["sourceTurn"])


def _render_replay() -> str:
    raw_log_path = RAW_ROOT / "logs" / "turns.jsonl"
    if not raw_log_path.exists():
        raise FileNotFoundError(
            "The ignored accepted transcript is not available locally: "
            f"{raw_log_path.relative_to(REPO_ROOT)}"
        )

    _verify_raw_matches_canonical()
    raw_turns = _load_jsonl(raw_log_path)
    script = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    scripted_turns = script["turns"]
    if len(raw_turns) != 120 or len(scripted_turns) != 120:
        raise ValueError("Study 003 replay requires exactly 120 turns.")

    metrics = _load_canonical_metrics()
    ltm_total = 0
    turns: list[dict[str, Any]] = []

    for expected_turn, (raw, scripted) in enumerate(
        zip(raw_turns, scripted_turns, strict=True), start=1
    ):
        if raw["turn_number"] != expected_turn or scripted["turn"] != expected_turn:
            raise ValueError(f"Out-of-order turn at position {expected_turn}.")

        repaired_raw_user = _repair_mojibake(raw["user_message"])
        if repaired_raw_user != scripted["user"]:
            raise ValueError(f"Script/raw prompt mismatch at turn {expected_turn}.")

        memory = metrics["memory"][expected_turn]
        performance = metrics["performance"][expected_turn]
        rule = metrics["rules"][expected_turn]
        consolidation = metrics["consolidation"].get(expected_turn)
        promotion = metrics["promotion"].get(expected_turn)
        promoted_details: list[dict[str, Any]] = []

        if promotion:
            promoted_details = [
                {
                    "episodeTurn": _as_int(score["episode_turn"]),
                    "weightedScore": round(_as_float(score["weighted_score"]), 3),
                    "triggerType": score["trigger_type"],
                    "triggeredFilter": score["triggered_filter"] or None,
                }
                for score in metrics["scores"][expected_turn]
                if _as_bool(score["promoted"])
            ]
            ltm_total += _as_int(promotion["episodes_promoted"])

        turn_topic = _topic_for_turn(expected_turn)
        turn_data: dict[str, Any] = {
            "turn": expected_turn,
            "phase": "probe" if expected_turn >= 112 else "conversation",
            "topic": turn_topic,
            "queryDomain": PROBE_DOMAINS.get(expected_turn, turn_topic),
            "user": scripted["user"],
            "assistant": raw["assistant_message"].strip(),
            "context": {
                "kCount": _as_int(raw["k_count"]),
                "nCount": _as_int(raw["n_count"]),
                "uniqueEpisodes": _as_int(raw["total_in_context"]),
                "estimatedTokens": _as_int(performance["estimated_tokens"]),
                "kTokenEstimate": _as_int(raw["k_token_estimate"]),
                "nTokenEstimate": _as_int(raw["n_token_estimate"]),
                "entries": _context_entries(raw),
            },
            "memory": {
                "stmEpisodes": expected_turn,
                "ltmEpisodes": ltm_total,
                "topicCount": _as_int(memory["topic_count"]),
                "ruleCount": _as_int(raw.get("rule_store_count")),
                "newTopic": _as_bool(memory["new_topic_created"]),
                "newTopicLabel": None
                if memory["new_topic_label"] == "---"
                else memory["new_topic_label"],
            },
            "performance": {
                "tokensPerSecond": round(
                    _as_float(performance["tokens_per_second"]), 2
                ),
                "timeToFirstTokenMs": round(
                    _as_float(performance["time_to_first_token"]) * 1000, 1
                ),
                "outputTokens": _as_int(performance["output_tokens"]),
            },
            "rule": {
                "detected": _as_bool(rule["contains_rule_detected"]),
                "summary": rule["rule_summary"] or None,
            },
            "consolidation": None,
            "ltmEvent": None,
        }

        if consolidation:
            turn_data["consolidation"] = {
                "topicsBefore": _as_int(consolidation["topics_before"]),
                "topicsAfter": _as_int(consolidation["topics_after"]),
                "pairsMerged": _as_int(consolidation["pairs_merged"]),
                "survivingLabels": [
                    label
                    for label in consolidation["surviving_labels"].split("|")
                    if label
                ],
                "mergedLabels": [
                    label
                    for label in consolidation["merged_labels"].split("|")
                    if label
                ],
            }

        if promotion:
            turn_data["ltmEvent"] = {
                "sourceTopic": promotion["topic"],
                "evaluated": _as_int(promotion["episodes_evaluated"]),
                "promoted": _as_int(promotion["episodes_promoted"]),
                "rate": round(_as_float(promotion["promotion_rate"]), 4),
                "ltmTotal": ltm_total,
                "episodes": promoted_details,
            }

        turns.append(turn_data)

    peak = max(turns, key=lambda item: item["context"]["estimatedTokens"])
    canonical_artifacts = _canonical_artifacts()
    payload = {
        "schemaVersion": 1,
        "study": {
            "id": "study-003",
            "title": "Selective STM-to-LTM Promotion in a Bounded Conversational Memory",
            "runId": "study_003_full_002",
            "condition": "Iterative context construction",
            "model": "Qwen3.6 27B NVFP4",
            "contextCapacity": 262144,
            "turns": 120,
            "result": "PARTIAL",
            "rubricScore": 12,
            "rubricMax": 13,
            "successBarsPassed": 2,
            "successBarsTotal": 3,
            "finalTopicCount": turns[-1]["memory"]["topicCount"],
            "ltmEvaluated": 90,
            "ltmPromoted": ltm_total,
            "peakContextTokens": peak["context"]["estimatedTokens"],
            "peakContextTurn": peak["turn"],
            "ltmWriteOnly": True,
            "acceptedRun": True,
        },
        "topics": TOPICS,
        "pinnedRules": (
            "Format technical specifications or multiple items as a numbered list.",
            "Conclude structural or engineering recommendations with a risk classification.",
        ),
        "turns": turns,
        "provenance": {
            "displayPrompts": str(SCRIPT_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
            "localTranscript": str(raw_log_path.relative_to(REPO_ROOT)).replace("\\", "/"),
            "localTranscriptSha256": _sha256(raw_log_path),
            "rawMetricsMatchCanonical": True,
            "canonicalArtifacts": {
                name: {
                    "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "sha256": _sha256(path),
                }
                for name, path in sorted(canonical_artifacts.items())
            },
            "transformations": (
                "User prompts come from the locked Study 003 script after exact comparison with the repaired raw prompt text.",
                "Assistant responses are the accepted Qwen outputs with surrounding whitespace removed; no content is summarized or rewritten.",
                "Context membership comes from the raw accepted turn log; all displayed aggregate metrics come from tracked canonical CSV artifacts.",
            ),
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _validate_committed_without_raw() -> None:
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    turns = payload.get("turns", [])
    if len(turns) != 120 or [turn["turn"] for turn in turns] != list(range(1, 121)):
        raise ValueError("Committed replay does not contain ordered turns 1–120.")

    script = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    if [turn["user"] for turn in turns] != [turn["user"] for turn in script["turns"]]:
        raise ValueError("Committed replay prompts do not match the locked script.")

    canonical = payload["provenance"]["canonicalArtifacts"]
    for name, path in _canonical_artifacts().items():
        if canonical[name]["sha256"] != _sha256(path):
            raise ValueError(f"Canonical checksum changed: {name}")

    events = [turn["turn"] for turn in turns if turn["ltmEvent"]]
    if events != [31, 61, 91]:
        raise ValueError(f"Unexpected LTM event turns: {events}")
    if turns[-1]["memory"]["ltmEpisodes"] != 21:
        raise ValueError("Final LTM count is not 21.")


def main() -> None:
    args = _parse_args()
    raw_log_path = RAW_ROOT / "logs" / "turns.jsonl"

    if args.check and not raw_log_path.exists():
        _validate_committed_without_raw()
        print("Study 003 replay matches the tracked script and canonical metrics.")
        return

    rendered = _render_replay()
    if args.check:
        with tempfile.TemporaryDirectory(prefix="study-003-replay-") as temp_dir:
            candidate = Path(temp_dir) / OUTPUT_PATH.name
            candidate.write_text(rendered, encoding="utf-8", newline="\n")
            if not OUTPUT_PATH.exists() or candidate.read_bytes() != OUTPUT_PATH.read_bytes():
                raise SystemExit(
                    "Study 003 replay is stale. Run scripts/export_build_week_demo.py."
                )
        print("Study 003 replay matches the accepted local transcript.")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()

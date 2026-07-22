"""Curated Study 005 dreaming logs and distilled-memory snapshots."""

import csv
import json
import os

from src.memory.distilled_ltm_store import get_distilled_records


class DreamAnalysisWriter:
    def __init__(self, output_dir: str):
        self._directory = os.path.join(output_dir, "dream_analysis")
        self._snapshot_directory = os.path.join(
            self._directory,
            "distilled_ltm_snapshots",
        )
        os.makedirs(self._snapshot_directory, exist_ok=True)
        self._initialize(
            "dream_events.csv",
            [
                "turn",
                "topic_id",
                "topic",
                "event_type",
                "extractor",
                "episodes_evaluated",
                "survivors",
                "records_written",
                "marker_written",
                "duplicates_collapsed",
                "inference_calls",
            ],
        )
        self._initialize(
            "episode_salience.csv",
            [
                "turn",
                "topic",
                "episode_id",
                "episode_turn",
                "salience",
                "named_entities",
                "numeric_tokens",
                "selected",
            ],
        )
        self._initialize(
            "dedup_events.csv",
            [
                "turn",
                "topic",
                "survivor_episode_id",
                "collapsed_episode_id",
            ],
        )

    def _initialize(self, filename: str, headers: list[str]) -> None:
        path = os.path.join(self._directory, filename)
        with open(path, "w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(headers)

    def write_dream(self, summary, conn) -> None:
        with open(
            os.path.join(self._directory, "dream_events.csv"),
            "a",
            newline="",
            encoding="utf-8",
        ) as handle:
            csv.writer(handle).writerow([
                summary.turn,
                summary.topic_id,
                summary.topic,
                summary.event_type,
                summary.extractor,
                summary.evaluated,
                summary.survivors,
                summary.records_written,
                summary.marker_written,
                summary.duplicates_collapsed,
                summary.inference_calls,
            ])

        selected_ids = {
            candidate.episode["id"] for candidate in summary.selected
        }
        with open(
            os.path.join(self._directory, "episode_salience.csv"),
            "a",
            newline="",
            encoding="utf-8",
        ) as handle:
            writer = csv.writer(handle)
            for candidate in summary.candidates:
                writer.writerow([
                    summary.turn,
                    summary.topic,
                    candidate.episode["id"],
                    candidate.episode["turn_number"],
                    candidate.salience,
                    candidate.named_entities,
                    candidate.numeric_tokens,
                    candidate.episode["id"] in selected_ids,
                ])

        with open(
            os.path.join(self._directory, "dedup_events.csv"),
            "a",
            newline="",
            encoding="utf-8",
        ) as handle:
            writer = csv.writer(handle)
            for candidate in summary.candidates:
                for collapsed_id in candidate.collapsed_episode_ids:
                    writer.writerow([
                        summary.turn,
                        summary.topic,
                        candidate.episode["id"],
                        collapsed_id,
                    ])

        records = []
        for record in get_distilled_records(conn):
            clean = dict(record)
            embedding = clean.pop("embedding", None)
            clean["embedding_dimensions"] = (
                len(embedding) // 4 if embedding is not None else 0
            )
            records.append(clean)
        snapshot_path = os.path.join(
            self._snapshot_directory,
            f"dream_event_{summary.turn:03d}_{summary.topic}.json",
        )
        with open(snapshot_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "turn": summary.turn,
                    "topic": summary.topic,
                    "event_type": summary.event_type,
                    "records": records,
                },
                handle,
                indent=2,
                ensure_ascii=False,
            )

"""CSV observability artifacts required for the Study 003 LTM analysis."""

import csv
import os


class LtmAnalysisWriter:
    def __init__(self, output_dir: str):
        self._directory = os.path.join(output_dir, "ltm_analysis")
        os.makedirs(self._directory, exist_ok=True)
        self._initialize("promotion_events.csv", ["turn", "topic", "episodes_evaluated", "episodes_promoted", "promotion_rate"])
        self._initialize("episode_scores.csv", ["turn", "episode_id", "episode_turn", "topic", "novelty", "repetition", "association", "emotional", "weighted_score", "promoted", "trigger_type", "triggered_filter"])
        self._initialize("filter_triggers.csv", ["turn", "episode_id", "topic", "trigger_type", "triggered_filter"])
        self._initialize("merge_relabel_events.csv", ["turn", "previous_episode_id", "current_episode_id", "previous_topic_before", "previous_topic_after", "current_topic_after", "reason"])

    def _initialize(self, filename: str, headers: list[str]) -> None:
        path = os.path.join(self._directory, filename)
        if not os.path.exists(path):
            with open(path, "w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerow(headers)

    def write_promotion(self, summary) -> None:
        with open(os.path.join(self._directory, "promotion_events.csv"), "a", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow([summary.turn, summary.topic, summary.evaluated, summary.promoted, summary.promoted / summary.evaluated if summary.evaluated else 0.0])
        with open(os.path.join(self._directory, "episode_scores.csv"), "a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            for result in summary.episode_results:
                writer.writerow([summary.turn, result.episode_id, result.turn_number, result.topic, result.novelty, result.repetition, result.association, result.emotional, result.weighted_score, result.promoted, result.trigger_type, result.triggered_filter or ""])
        with open(os.path.join(self._directory, "filter_triggers.csv"), "a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            for result in summary.episode_results:
                if result.promoted:
                    writer.writerow([summary.turn, result.episode_id, result.topic, result.trigger_type, result.triggered_filter or ""])

    def write_merge_relabel(self, turn, previous_episode_id, current_episode_id, before, after, current_after) -> None:
        with open(os.path.join(self._directory, "merge_relabel_events.csv"), "a", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow([turn, previous_episode_id, current_episode_id, before, after, current_after, "canonical topics equal after consolidation"])

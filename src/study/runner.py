import os
import time

import numpy as np

from src.db.schema import init_db
from src.embeddings.provider import embed
from src.inference.provider import (
    RESPONSE_BUDGET,
    InferenceProvider,
    detect_explicit_persistent_rule,
)
from src.db.episode import get_episode_by_id
from src.memory.dream_engine import DreamEngine
from src.memory.span_dream_engine import SpanDreamEngine
from src.memory.promotion_engine import PromotionEngine
from src.memory.retrieval_engine import RetrievalEngine
from src.memory.topic_manager import TopicManager
from src.observability.dream_analysis_writer import (
    DreamAnalysisWriter,
    SpanDreamAnalysisWriter,
)
from src.observability.observer import Observer
from src.observability.ltm_analysis_writer import LtmAnalysisWriter
from src.observability.run_config import RunConfig
from src.observability.turn_record import TurnRecord
from src.runners.compaction_runner import CompactionRunner
from src.runners.full_context_runner import FullContextRunner
from src.memory.retrieval_budget import (
    DEFAULT_K_MIN,
    FLOOR_SIMILARITY,
    RENDER_EPISODE,
)
from src.runners.iterative_runner import IterativeRunner
from src.study.script_loader import load_script
from src.study.checkpoint import restore_checkpoint, write_checkpoint
from src.study.domain_labels import (
    PROBE_TURN_END,
    PROBE_TURN_START,
    ground_truth_domain_for_turn,
)


class StudyRunner:

    CONDITION_ORDER = ["full_context", "compaction", "iterative"]
    CONDITION_OUTPUT_NAMES: dict[str, str] = {}
    RUBRIC_TURN_START = 25
    RUBRIC_TURN_END = 32
    RUBRIC_TURNS = list(range(112, 122))
    PROMOTION_TURN_END = 111
    PROBE_TURN_START = PROBE_TURN_START
    PROBE_TURN_END = PROBE_TURN_END

    def __init__(
        self,
        script_path: str,
        study_dir: str,
        run_id: str = "run_001",
        minimum_turns: int = 30,
        max_turns: int | None = None,
        memory_formation: str = "promotion",
        context_capacity: int | None = None,
        strict_monitoring: bool = False,
        expected_script_digest: str | None = None,
        ltm_budget: int | None = None,
        ltm_k_min: int = DEFAULT_K_MIN,
        ltm_floor_ranking: str = FLOOR_SIMILARITY,
        ltm_fill_cap: int | None = None,
        ltm_render_mode: str = RENDER_EPISODE,
        checkpoint_interval: int | None = None,
        resume_checkpoint: str | None = None,
        suppress_rule_detection: bool = False,
    ):
        self.ltm_budget = ltm_budget
        self.ltm_k_min = ltm_k_min
        self.ltm_floor_ranking = ltm_floor_ranking
        self.ltm_fill_cap = ltm_fill_cap
        self.ltm_render_mode = ltm_render_mode
        if memory_formation not in {"promotion", "dreaming", "span_dreaming"}:
            raise ValueError(
                f"Unsupported memory formation mode: {memory_formation}"
            )
        self._check_env_vars()
        # Study 007 Correction 1: assert the post-decode digest before any
        # inference is spent, so a mis-decoded script aborts at startup rather
        # than surfacing at analysis as it did in Study 006.
        self.script = load_script(
            script_path,
            minimum_turns=minimum_turns,
            expected_digest=expected_script_digest,
        )
        self.expected_script_digest = expected_script_digest
        self.system_prompt = self.script["system_prompt"]
        self.turns = self.script["turns"][:max_turns] if max_turns else self.script["turns"]
        self.study_name = self.script.get("study", "study_003")
        self._promotion_flush_turn = int(
            self.script.get("promotion_flush_turn", self.PROMOTION_TURN_END)
        )
        self._probe_turn_start = int(
            self.script.get("probe_turn_start", self.PROBE_TURN_START)
        )
        self._probe_turn_end = int(
            self.script.get("probe_turn_end", self.PROBE_TURN_END)
        )
        self._rubric_turns = set(
            self.script.get("rubric_turns", self.RUBRIC_TURNS)
        )
        self._emission_guard_turns = set(
            self.script.get("emission_guard_turns", [])
        )
        self.study_dir = study_dir
        self.run_id = run_id
        self.memory_formation = memory_formation
        self.context_capacity = context_capacity
        self.strict_monitoring = strict_monitoring
        self._inference_provider = InferenceProvider()
        self._rubric_data = {}
        self.checkpoint_interval = checkpoint_interval
        self.resume_checkpoint = resume_checkpoint
        self.suppress_rule_detection = suppress_rule_detection

    def _check_env_vars(self):
        required = [
            "CDW_EMBEDDING_MODEL_PATH",
        ]
        if not os.environ.get("CDW_INFERENCE_SERVER_URL"):
            required.append("CDW_INFERENCE_MODEL_PATH")
        missing = [v for v in required if not os.environ.get(v)]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"All five environment variables must be set before running the study."
            )

    def run(self) -> None:
        for condition in self.CONDITION_ORDER:
            self._run_condition(condition)

    def _run_condition(self, condition: str) -> None:
        output_name = self._condition_output_name(condition)
        output_dir = os.path.join(self.study_dir, self.run_id, output_name)
        run_config = RunConfig(
            condition=condition,
            run_id=self.run_id,
            output_dir=output_dir,
            study_dir=self.study_dir,
        )

        observer = Observer(run_config)
        resume_payload = None
        resume_checkpoint = getattr(self, "resume_checkpoint", None)
        if resume_checkpoint:
            resume_payload = restore_checkpoint(
                __import__("pathlib").Path(output_dir),
                __import__("pathlib").Path(resume_checkpoint),
            )
        else:
            observer.init_run()

        runner = self._create_runner(condition, run_config, observer)
        formation_engine = None
        formation_writer = None
        if condition == "iterative" and hasattr(runner, "_conn"):
            formation_mode = getattr(self, "memory_formation", "promotion")
            if formation_mode == "span_dreaming":
                formation_engine = SpanDreamEngine(
                    runner._conn,
                    inference_call_count=lambda: (
                        self._inference_provider.completion_count
                    ),
                )
                formation_writer = SpanDreamAnalysisWriter(output_dir)
            elif formation_mode == "dreaming":
                formation_engine = DreamEngine(
                    runner._conn,
                    inference_call_count=lambda: (
                        self._inference_provider.completion_count
                    ),
                )
                formation_writer = DreamAnalysisWriter(output_dir)
            else:
                formation_engine = PromotionEngine(
                    runner._conn,
                    self._inference_provider,
                )
                formation_writer = LtmAnalysisWriter(output_dir)
        state = resume_payload["state"] if resume_payload else {}
        completed_turn = int(resume_payload["turn"]) if resume_payload else 0
        previous_prompt = state.get("previous_prompt")
        previous_episode_id = state.get("previous_episode_id")
        previous_turn_number = state.get("previous_turn_number")
        rubric_responses = state.get("rubric_responses", [])
        condition_start = time.perf_counter()
        peak_tokens = 0
        turn_count = 0
        flush_completed = bool(state.get("flush_completed", False))
        consecutive_invalid_responses = 0
        promotion_flush_turn = getattr(
            self, "_promotion_flush_turn", self.PROMOTION_TURN_END
        )
        probe_turn_start = getattr(
            self, "_probe_turn_start", self.PROBE_TURN_START
        )
        rubric_turns = getattr(self, "_rubric_turns", set(self.RUBRIC_TURNS))

        self._print_condition_start_banner(condition)

        for turn_data in self.turns:
            turn_number = turn_data["turn"]
            if turn_number <= completed_turn:
                continue
            user_message = turn_data["user"]
            if condition == "iterative" and formation_engine:
                self._assert_flush_completed_before_turn(
                    turn_number,
                    flush_completed,
                    probe_turn_start=probe_turn_start,
                )

            constructed_prompt, record = runner.build_context(user_message, turn_number)
            context_capacity = getattr(self, "context_capacity", None)
            if (
                context_capacity
                and record.estimated_tokens > int(context_capacity * 0.8)
            ):
                raise RuntimeError(
                    f"Turn {turn_number} estimated context "
                    f"{record.estimated_tokens} exceeds 80% of "
                    f"{context_capacity}"
                )

            if condition == "iterative":
                full_prompt = f"{constructed_prompt}\n\nAssistant:"
            else:
                full_prompt = constructed_prompt

            record.constructed_prompt = full_prompt
            record.previous_context_window = previous_prompt
            record.total_turns = len(self.turns)

            suppress_rules = getattr(self, "suppress_rule_detection", False)
            result = self._inference_provider.complete(
                full_prompt,
                suppress_rule_detection=suppress_rules,
            )
            if (
                condition == "iterative"
                and not suppress_rules
                and not result.contains_rule
            ):
                fallback_rule = detect_explicit_persistent_rule(user_message)
                if fallback_rule:
                    result.contains_rule = True
                    result.rule_summary = fallback_rule
            if suppress_rules and (
                result.contains_rule or record.rule_store_count != 0
            ):
                raise RuntimeError(
                    "suppressed rule extraction produced or retained a rule"
                )
            assistant_message = result.assistant_message
            invalid_response = (
                not assistant_message.strip()
                or (result.output_tokens or 0) >= RESPONSE_BUDGET
            )
            consecutive_invalid_responses = (
                consecutive_invalid_responses + 1
                if invalid_response
                else 0
            )
            if (
                getattr(self, "strict_monitoring", False)
                and consecutive_invalid_responses >= 3
            ):
                raise RuntimeError(
                    "Three consecutive responses were empty or reached the "
                    "registered response budget"
                )

            record.tokens_per_second = result.tokens_per_second
            record.time_to_first_token = result.time_to_first_token
            record.output_tokens = result.output_tokens
            record.assistant_message = assistant_message
            record.contains_rule = result.contains_rule
            record.rule_summary = result.rule_summary

            if record.estimated_tokens > peak_tokens:
                peak_tokens = record.estimated_tokens
            turn_count += 1

            if turn_number in rubric_turns:
                rubric_responses.append({
                    "turn_number": turn_number,
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                })

            if condition == "iterative":
                previous_topic_before = None
                if previous_episode_id is not None:
                    previous_episode = get_episode_by_id(runner._conn, previous_episode_id)
                    previous_topic_before = previous_episode["topic_id"] if previous_episode else None
                pair_text = f"User: {user_message}\nAssistant: {assistant_message}"
                embedding = embed(pair_text)
                topic_embedding = embed(user_message)
                assignment = runner.on_turn_complete(
                    user_message=user_message,
                    assistant_message=assistant_message,
                    turn_number=turn_number,
                    embedding=embedding,
                    topic_embedding=topic_embedding,
                    inference_result=result,
                    ground_truth_domain=turn_data.get(
                        "ground_truth_domain",
                        ground_truth_domain_for_turn(turn_number),
                    ),
                )
                record.stored_episode_id = assignment.stored_episode_id
                record.stored_topic_label = assignment.topic_label
                record.new_topic_created = assignment.is_new_topic
                record.new_topic_label = assignment.topic_label if assignment.is_new_topic else None
                record.centroid_drift = {assignment.topic_label: assignment.centroid_drift}
                record.topic_count = runner._topic_manager.topic_count
                record.episode_count = runner._topic_manager.topic_count
                record.consolidation_occurred = assignment.consolidation is not None
                record.consolidation_result = assignment.consolidation
                if (
                    formation_engine
                    and assignment.stored_episode_id
                    and turn_number <= promotion_flush_turn
                    and turn_number
                    not in getattr(self, "_emission_guard_turns", set())
                    and previous_turn_number
                    not in getattr(self, "_emission_guard_turns", set())
                ):
                    summary = formation_engine.process_transition(
                        previous_episode_id, assignment.stored_episode_id, turn_number
                    )
                    if summary:
                        self._write_formation_summary(
                            formation_writer,
                            summary,
                            runner._conn,
                        )
                    elif (
                        getattr(self, "memory_formation", "promotion")
                        == "promotion"
                        and previous_episode_id is not None
                        and assignment.consolidation
                    ):
                        previous_after = get_episode_by_id(runner._conn, previous_episode_id)
                        current_after = get_episode_by_id(runner._conn, assignment.stored_episode_id)
                        if previous_after and current_after and previous_topic_before != previous_after["topic_id"] and previous_after["topic_id"] == current_after["topic_id"]:
                            formation_writer.write_merge_relabel(
                                turn_number, previous_episode_id, assignment.stored_episode_id,
                                previous_topic_before, previous_after["topic_id"], current_after["topic_id"],
                            )
                    if turn_number == promotion_flush_turn:
                        flush_summary = formation_engine.process_flush(
                            assignment.stored_episode_id,
                            turn_number,
                            expected_flush_turn=promotion_flush_turn,
                        )
                        if flush_summary:
                            self._write_formation_summary(
                                formation_writer,
                                flush_summary,
                                runner._conn,
                            )
                        flush_completed = True
                previous_episode_id = assignment.stored_episode_id
                previous_turn_number = turn_number
            else:
                runner.on_turn_complete(user_message, assistant_message, turn_number)

            observer.flush_turn(record)
            previous_prompt = full_prompt
            if (
                getattr(self, "checkpoint_interval", None)
                and turn_number % self.checkpoint_interval == 0
                and condition == "iterative"
            ):
                write_checkpoint(
                    __import__("pathlib").Path(output_dir),
                    runner._conn,
                    turn_number,
                    {
                        "previous_prompt": previous_prompt,
                        "previous_episode_id": previous_episode_id,
                        "previous_turn_number": previous_turn_number,
                        "rubric_responses": rubric_responses,
                        "flush_completed": flush_completed,
                    },
                )

        condition_duration = time.perf_counter() - condition_start

        self._print_condition_complete_banner(condition, turn_count, peak_tokens, condition_duration)

        if rubric_responses:
            self._write_rubric_responses(condition, rubric_responses)

    @classmethod
    def _promotion_emission_allowed(cls, turn_number: int) -> bool:
        return turn_number <= cls.PROMOTION_TURN_END

    @classmethod
    def _assert_flush_completed_before_turn(
        cls,
        turn_number: int,
        flush_completed: bool,
        probe_turn_start: int | None = None,
    ) -> None:
        first_probe = (
            cls.PROBE_TURN_START if probe_turn_start is None else probe_turn_start
        )
        if turn_number >= first_probe and not flush_completed:
            raise RuntimeError(
                "Turn 111 memory-formation flush must complete before the probe block"
            )

    def _create_runner(self, condition: str, run_config: RunConfig, observer) -> object:
        if condition == "full_context":
            return FullContextRunner(self.system_prompt)
        elif condition == "compaction":
            return CompactionRunner(self.system_prompt, inference_provider=self._inference_provider)
        elif condition == "iterative":
            db_path = os.path.join(run_config.output_dir, "study.db")
            conn = init_db(db_path)
            topic_manager = TopicManager(conn)
            retrieval_engine = RetrievalEngine(
                conn,
                embedding_provider=embed,
                system_prompt=self.system_prompt,
                ltm_source=(
                    "distilled"
                    if getattr(self, "memory_formation", "promotion")
                    in {"dreaming", "span_dreaming"}
                    else "promoted"
                ),
                # Study 007. None keeps the carried count-based policy, so every
                # prior study and the control arm are unaffected.
                ltm_budget=self.ltm_budget,
                ltm_k_min=self.ltm_k_min,
                ltm_floor_ranking=self.ltm_floor_ranking,
                ltm_fill_cap=self.ltm_fill_cap,
                ltm_render_mode=self.ltm_render_mode,
            )
            return IterativeRunner(conn, embed, topic_manager, retrieval_engine, observer)
        else:
            raise ValueError(f"Unknown condition: {condition}")

    def _write_formation_summary(self, writer, summary, conn) -> None:
        if getattr(self, "memory_formation", "promotion") in {
            "dreaming",
            "span_dreaming",
        }:
            writer.write_dream(summary, conn)
        else:
            writer.write_promotion(summary)

    def _condition_output_name(self, condition: str) -> str:
        output_names = getattr(self, "CONDITION_OUTPUT_NAMES", {})
        return output_names.get(condition, condition)

    def _print_condition_start_banner(self, condition: str) -> None:
        bar_w = 50
        cond_padded = f"  STARTING CONDITION: {condition}".ljust(bar_w)
        run_info = f"  Run: {self.run_id} | Script: {len(self.turns)} turns | Study: {self.study_name}".ljust(bar_w)
        print()
        print("\u2554" + "\u2550" * (bar_w - 2) + "\u2557")
        print("\u2551" + cond_padded + "\u2551")
        print("\u2551" + run_info + "\u2551")
        print("\u255a" + "\u2550" * (bar_w - 2) + "\u255d")
        print()

    def _print_condition_complete_banner(self, condition: str, turn_count: int, peak_tokens: int, duration: float) -> None:
        bar_w = 50
        mins, secs = divmod(duration, 60)
        duration_str = f"{int(mins)}m {int(secs)}s"
        cond_padded = f"  CONDITION COMPLETE: {condition}".ljust(bar_w)
        stats = f"  {turn_count} turns | Peak tokens: ~{peak_tokens:,} | Duration: {duration_str}".ljust(bar_w)
        print("\u2554" + "\u2550" * (bar_w - 2) + "\u2557")
        print("\u2551" + cond_padded + "\u2551")
        print("\u2551" + stats + "\u2551")
        print("\u255a" + "\u2550" * (bar_w - 2) + "\u255d")
        print()

    def _write_rubric_responses(self, condition: str, rubric_responses: list) -> None:
        output_name = self._condition_output_name(condition)
        rubric_dir = os.path.join(
            self.study_dir, self.run_id, output_name, "rubric"
        )
        os.makedirs(rubric_dir, exist_ok=True)

        rubric_path = os.path.join(rubric_dir, "responses.md")
        with open(rubric_path, "w", encoding="utf-8") as f:
            f.write(f"# Rubric Responses — {condition}\n")
            f.write(f"**Run:** {self.run_id}\n")
            f.write(f"**Condition:** {condition}\n")
            f.write(f"**Scored by:** [TO BE FILLED — Sprint 009]\n")
            f.write(f"\n---\n")

            question_labels = {
                112: "Q1: Budget Cap",
                113: "Q4: Lead Engineer + Deadline",
                114: "Q7: Formatting Rules",
                115: "Q10: CRISPR Cell Line + Expression Rate",
                116: "Q13: CRISPR Dosage",
                117: "Q16: Performance Target",
                118: "Q19: Researcher Identity",
                119: "Q22: All Numerical Values",
                120: "Q25: Final Comprehensive Check",
                121: "Q14: Second Breadth Probe",
            }

            for resp in rubric_responses:
                turn_num = resp["turn_number"]
                label = question_labels.get(turn_num, f"Turn {turn_num}")
                f.write(f"\n## Turn {turn_num} — {label}\n\n")
                f.write(f"**User:** {resp['user_message']}\n\n")
                f.write(f"**Assistant response:**\n{resp['assistant_message']}\n\n")
                f.write(f"**Score:** [  ] (1.0 / 0.5 / 0.0)\n")
                f.write(f"**Notes:**\n\n")
                f.write(f"---\n")

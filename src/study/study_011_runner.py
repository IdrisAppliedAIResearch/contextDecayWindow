"""Study 011 runner: one arm, one live run.

Subclasses the carried Tier 6 runner and reimplements ``run`` rather than
adding a hook to it, because a carried subsystem must not be altered to
make room for a new study. The turn loop below is the carried one; three
things differ and nothing else does:

* the retrieval engine is ``TierIsolationEngine``, so a tier can be off
  and the fill order can be K-first;
* the output directory is named for the arm;
* every accounting row carries the arm's declared configuration, so a log
  cannot be read as the wrong arm's.

Arm D is not run from here. Section 5 requires the control on the deployed
configuration as committed, from checked-out prior code in a separate
worktree; ``TierIsolationEngine`` refuses it.
"""

from __future__ import annotations

import time
from pathlib import Path

from src.db.episode import get_episode_by_id
from src.db.schema import init_db
from src.inference.provider import RESPONSE_BUDGET, detect_explicit_persistent_rule
from src.memory.context_matched_stm import context_match_accounting
from src.memory.topic_manager import TopicManager
from src.observability.observer import Observer
from src.observability.run_config import RunConfig
from src.runners.stm_runner import StmRunner
from src.study.checkpoint import restore_checkpoint, write_checkpoint
from src.study.domain_labels import ground_truth_domain_for_turn
from src.study.retrieval_bakeoff_tier6_runner import RetrievalBakeoffTier6Runner
from src.tier_isolation.study011 import (
    SERVED_ARMS,
    TierIsolationEngine,
    TierIsolationError,
    arm_accounting,
)


class Study011Runner(RetrievalBakeoffTier6Runner):
    def __init__(self, *, arm: str, **kwargs) -> None:
        if arm not in SERVED_ARMS:
            raise TierIsolationError(
                f"Study 011 runner serves arms {SERVED_ARMS}; got {arm!r}. "
                "Arm D runs from checked-out deployed code in a separate "
                "worktree."
            )
        super().__init__(**kwargs)
        self.arm = arm

    def run(self) -> Path:
        output_dir = Path(self.study_dir) / self.run_id / f"arm_{self.arm.lower()}"
        config = RunConfig(
            condition=f"study_011_arm_{self.arm.lower()}",
            run_id=self.run_id,
            output_dir=str(output_dir),
            study_dir=self.study_dir,
        )
        observer = Observer(config)
        resume_payload = None
        if self.resume_checkpoint:
            resume_payload = restore_checkpoint(
                output_dir,
                Path(self.resume_checkpoint),
            )
        else:
            if output_dir.exists():
                raise RuntimeError(
                    f"Refusing to overwrite Study 011 run: {output_dir}"
                )
            observer.init_run()

        accounting_path = output_dir / "logs" / "context_match.jsonl"
        if resume_payload is None:
            accounting_path.write_text("", encoding="utf-8", newline="\n")
        conn = init_db(str(output_dir / "study.db"))
        topic_manager = TopicManager(conn)
        retrieval_engine = TierIsolationEngine(
            conn,
            arm=self.arm,
            n_cap=self.n_cap,
            k_threshold=self.k_threshold,
            payload_budget=self.payload_budget,
            embedding_provider=self._embed,
            system_prompt=self.system_prompt,
        )
        runner = StmRunner(conn, self._embed, topic_manager, retrieval_engine)
        declared = arm_accounting(self.arm)

        state = resume_payload["state"] if resume_payload else {}
        completed_turn = int(resume_payload["turn"]) if resume_payload else 0
        previous_prompt = state.get("previous_prompt")
        previous_episode_id = state.get("previous_episode_id")
        rubric_responses = state.get("rubric_responses", [])
        completeness_rows = state.get("completeness_rows", [])
        consecutive_invalid = 0
        started = time.perf_counter()

        for turn_data in self.turns:
            turn_number = int(turn_data["turn"])
            if turn_number <= completed_turn:
                continue
            user_message = str(turn_data["user"])
            prompt, record = runner.build_context(user_message, turn_number)
            match_result = retrieval_engine.last_result
            if match_result is None:
                raise AssertionError("Study 011 retrieval produced no accounting")
            accounting = {
                "turn_number": turn_number,
                "arm": self.arm,
                "recency_enabled": declared["recency_enabled"],
                "k_enabled": declared["k_enabled"],
                "packing_order": declared["packing_order"],
                "n_cap": self.n_cap if declared["recency_enabled"] else 0,
                "k_threshold": (
                    self.k_threshold if declared["k_enabled"] else None
                ),
                **context_match_accounting(match_result),
            }
            self._append_jsonl(accounting_path, accounting)
            if record.estimated_tokens > int(self.context_capacity * 0.8):
                raise RuntimeError(
                    f"Turn {turn_number} estimated context "
                    f"{record.estimated_tokens} exceeds 80% of "
                    f"{self.context_capacity}"
                )

            full_prompt = f"{prompt}\n\nAssistant:"
            record.constructed_prompt = full_prompt
            record.previous_context_window = previous_prompt
            record.total_turns = len(self.turns)
            result = self._inference_provider.complete(
                full_prompt,
                suppress_rule_detection=self.suppress_rule_detection,
            )
            if self.ignore_rule_detection_result:
                result.contains_rule = False
                result.rule_summary = None
            if (
                not self.suppress_rule_detection
                and not self.ignore_rule_detection_result
                and not result.contains_rule
            ):
                fallback = detect_explicit_persistent_rule(user_message)
                if fallback:
                    result.contains_rule = True
                    result.rule_summary = fallback
            if (
                self.suppress_rule_detection
                or self.ignore_rule_detection_result
            ) and (result.contains_rule or record.rule_store_count != 0):
                raise RuntimeError(
                    "Suppressed rule extraction produced or retained a rule"
                )

            assistant_message = result.assistant_message
            invalid = (
                not assistant_message.strip()
                or (result.output_tokens or 0) >= RESPONSE_BUDGET
            )
            consecutive_invalid = consecutive_invalid + 1 if invalid else 0
            if self.strict_monitoring and consecutive_invalid >= 3:
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
            if turn_number in self.rubric_turns:
                rubric_responses.append(
                    {
                        "turn_number": turn_number,
                        "user_message": user_message,
                        "assistant_message": assistant_message,
                    }
                )
                completeness_rows.append(
                    {
                        "turn_number": turn_number,
                        "has_scoreable_answer": bool(assistant_message.strip()),
                        "output_tokens": result.output_tokens,
                        "reached_response_budget": (
                            (result.output_tokens or 0) >= RESPONSE_BUDGET
                        ),
                    }
                )

            previous_topic_before = None
            if previous_episode_id is not None:
                previous = get_episode_by_id(conn, previous_episode_id)
                previous_topic_before = previous["topic_id"] if previous else None
            pair_embedding = self._embed(
                f"User: {user_message}\nAssistant: {assistant_message}"
            )
            assignment = runner.on_turn_complete(
                user_message=user_message,
                assistant_message=assistant_message,
                turn_number=turn_number,
                embedding=pair_embedding,
                topic_embedding=self._embed(user_message),
                inference_result=result,
                ground_truth_domain=turn_data.get(
                    "ground_truth_domain",
                    ground_truth_domain_for_turn(turn_number),
                ),
            )
            record.stored_episode_id = assignment.stored_episode_id
            record.stored_topic_label = assignment.topic_label
            record.new_topic_created = assignment.is_new_topic
            record.new_topic_label = (
                assignment.topic_label if assignment.is_new_topic else None
            )
            record.centroid_drift = {
                assignment.topic_label: assignment.centroid_drift
            }
            record.topic_count = topic_manager.topic_count
            record.episode_count = turn_number
            record.consolidation_occurred = assignment.consolidation is not None
            record.consolidation_result = assignment.consolidation

            observer.flush_turn(record)
            previous_prompt = full_prompt
            previous_episode_id = assignment.stored_episode_id
            if (
                self.checkpoint_interval
                and turn_number % self.checkpoint_interval == 0
            ):
                write_checkpoint(
                    output_dir,
                    conn,
                    turn_number,
                    {
                        "previous_prompt": previous_prompt,
                        "previous_episode_id": previous_episode_id,
                        "rubric_responses": rubric_responses,
                        "completeness_rows": completeness_rows,
                    },
                )
            if (
                previous_topic_before is not None
                and assignment.consolidation is not None
            ):
                conn.commit()

        if rubric_responses:
            self._write_rubric_responses(output_dir, rubric_responses)
        conn.commit()
        conn.close()
        self._write_scoring_surface(output_dir, rubric_responses, completeness_rows)
        self._write_tier6_runtime_audit(
            output_dir,
            time.perf_counter() - started,
        )
        self._write_mechanism_seal(output_dir)
        return output_dir

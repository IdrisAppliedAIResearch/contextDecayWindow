"""Isolated runtime for Study 009 Arms S and S+D.

This module intentionally does not import the program's LTM, promotion,
dreaming, or digest modules. The digest composition is loaded dynamically only
when requested, so an Arm S process has no such module in its runtime closure.
"""

import importlib
import json
import os
import time
from pathlib import Path

from src.db.episode import get_episode_by_id
from src.db.schema import init_db
from src.embeddings.provider import embed
from src.inference.provider import (
    RESPONSE_BUDGET,
    InferenceProvider,
    detect_explicit_persistent_rule,
)
from src.memory.stm_retrieval_engine import StmRetrievalEngine
from src.memory.topic_manager import TopicManager
from src.observability.observer import Observer
from src.observability.run_config import RunConfig
from src.runners.stm_runner import StmRunner
from src.study.domain_labels import ground_truth_domain_for_turn
from src.study.script_loader import load_script
from src.study.checkpoint import restore_checkpoint, write_checkpoint


DIGEST_REBUILD_TURNS = frozenset({31, 61, 91, 111})


class Study009Runner:
    def __init__(
        self,
        script_path: str,
        study_dir: str,
        run_id: str,
        composition: str,
        max_turns: int | None = None,
        context_capacity: int = 50000,
        strict_monitoring: bool = True,
        expected_script_digest: str | None = None,
        digest_d: int = 2,
        digest_budget: int = 2500,
        inference_provider=None,
        embedding_provider=None,
        checkpoint_interval: int | None = None,
        resume_checkpoint: str | None = None,
    ):
        if composition not in {"S", "S+D"}:
            raise ValueError(f"Unsupported Study 009 composition: {composition}")
        self._check_env(inference_provider, embedding_provider)
        script = load_script(
            script_path,
            minimum_turns=30,
            expected_digest=expected_script_digest,
        )
        self.turns = (
            script["turns"][:max_turns] if max_turns else script["turns"]
        )
        self.system_prompt = script["system_prompt"]
        self.study_name = script.get("study", "study_009")
        self.study_dir = study_dir
        self.run_id = run_id
        self.composition = composition
        self.context_capacity = context_capacity
        self.strict_monitoring = strict_monitoring
        self.rubric_turns = set(script.get("rubric_turns", range(112, 122)))
        self._inference_provider = inference_provider or InferenceProvider()
        self._embed = embedding_provider or embed
        self.digest_d = digest_d
        self.digest_budget = digest_budget
        self.import_graph_at_start = sorted(
            name for name in __import__("sys").modules if name.startswith("src.")
        )
        self.checkpoint_interval = checkpoint_interval
        self.resume_checkpoint = resume_checkpoint

    @staticmethod
    def _check_env(inference_provider, embedding_provider) -> None:
        missing = []
        if embedding_provider is None and not os.environ.get(
            "CDW_EMBEDDING_MODEL_PATH"
        ):
            missing.append("CDW_EMBEDDING_MODEL_PATH")
        if (
            inference_provider is None
            and not os.environ.get("CDW_INFERENCE_SERVER_URL")
            and not os.environ.get("CDW_INFERENCE_MODEL_PATH")
        ):
            missing.append(
                "CDW_INFERENCE_SERVER_URL or CDW_INFERENCE_MODEL_PATH"
            )
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    def run(self) -> None:
        output_name = "arm_s_digest" if self.composition == "S+D" else "arm_s"
        output_dir = Path(self.study_dir) / self.run_id / output_name
        config = RunConfig(
            condition="iterative",
            run_id=self.run_id,
            output_dir=str(output_dir),
            study_dir=self.study_dir,
        )
        observer = Observer(config)
        resume_payload = None
        if self.resume_checkpoint:
            resume_payload = restore_checkpoint(
                output_dir, Path(self.resume_checkpoint)
            )
        else:
            observer.init_run()

        conn = init_db(str(output_dir / "study.db"))
        topic_manager = TopicManager(conn)
        digest = None
        digest_renderer = None
        digest_log = output_dir / "logs" / "topic_digest.jsonl"
        if self.composition == "S+D":
            digest_module = importlib.import_module("src.memory.topic_digest")
            digest = digest_module.TopicDigest(
                conn,
                embedding_provider=self._embed,
                spans_per_topic=self.digest_d,
                budget=self.digest_budget,
            )
            digest_renderer = digest_module.DigestContextRenderer(digest)
            digest_log.write_text("", encoding="utf-8")

        retrieval_engine = StmRetrievalEngine(
            conn,
            embedding_provider=self._embed,
            system_prompt=self.system_prompt,
            context_renderer=digest_renderer,
        )
        runner = StmRunner(conn, self._embed, topic_manager, retrieval_engine)

        state = resume_payload["state"] if resume_payload else {}
        completed_turn = int(resume_payload["turn"]) if resume_payload else 0
        previous_prompt = state.get("previous_prompt")
        previous_episode_id = state.get("previous_episode_id")
        rubric_responses = state.get("rubric_responses", [])
        consecutive_invalid = 0
        started = time.perf_counter()

        for turn_data in self.turns:
            turn_number = turn_data["turn"]
            if turn_number <= completed_turn:
                continue
            user_message = turn_data["user"]
            prompt, record = runner.build_context(user_message, turn_number)
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

            result = self._inference_provider.complete(full_prompt)
            if not result.contains_rule:
                fallback = detect_explicit_persistent_rule(user_message)
                if fallback:
                    result.contains_rule = True
                    result.rule_summary = fallback
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
                rubric_responses.append({
                    "turn_number": turn_number,
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                })

            previous_topic_before = None
            if previous_episode_id is not None:
                previous = get_episode_by_id(conn, previous_episode_id)
                previous_topic_before = (
                    previous["topic_id"] if previous else None
                )
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

            if digest_renderer is not None:
                self._append_digest_log(
                    digest_log,
                    {
                        "event": "render",
                        "turn": turn_number,
                        "built_at_turn": digest.frame.built_at_turn,
                        "budget": digest.budget,
                        "chars": digest_renderer.last_render.chars,
                        "span_count": digest_renderer.last_render.span_count,
                        "topics": digest_renderer.last_render.topics,
                        "containment_drops": (
                            digest_renderer.last_render.containment_drops
                        ),
                        "spans": digest_renderer.last_render.spans,
                    },
                )
                if turn_number in DIGEST_REBUILD_TURNS:
                    calls_before = self._inference_provider.completion_count
                    frame = digest.rebuild(turn_number)
                    calls_after = self._inference_provider.completion_count
                    if calls_after != calls_before:
                        raise AssertionError(
                            "Digest rebuild invoked the inference model"
                        )
                    self._append_digest_log(
                        digest_log,
                        {
                            "event": "rebuild",
                            "turn": turn_number,
                            "budget": frame.budget,
                            "span_count": len(frame.spans),
                            "serialized_chars": len(
                                digest.render().text
                            ),
                            "spans": [
                                digest._span_dict(span)
                                for span in frame.spans
                            ],
                        },
                    )

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
                    },
                )

            if (
                previous_topic_before is not None
                and assignment.consolidation is not None
            ):
                conn.commit()

        if rubric_responses:
            self._write_rubric_responses(output_dir, rubric_responses)
        self._write_runtime_audit(output_dir, time.perf_counter() - started)

    @staticmethod
    def _append_digest_log(path: Path, event: dict) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    @staticmethod
    def _write_rubric_responses(
        output_dir: Path, responses: list[dict]
    ) -> None:
        path = output_dir / "rubric" / "responses.md"
        lines = ["# Responses", ""]
        for response in responses:
            lines.extend([
                f"## Turn {response['turn_number']:03d}",
                "",
                f"**User:** {response['user_message']}",
                "",
                f"**Assistant:** {response['assistant_message']}",
                "",
            ])
        path.write_text("\n".join(lines), encoding="utf-8")

    def _write_runtime_audit(self, output_dir: Path, duration: float) -> None:
        modules = sorted(
            name for name in __import__("sys").modules if name.startswith("src.")
        )
        audit = {
            "composition": self.composition,
            "duration_seconds": duration,
            "turn_count": len(self.turns),
            "modules_at_runner_start": self.import_graph_at_start,
            "modules_at_completion": modules,
            "forbidden_modules_loaded": [
                name
                for name in modules
                if self.composition == "S"
                and (
                    "ltm" in name
                    or "digest" in name
                    or "dream" in name
                    or "promotion" in name
                )
            ],
        }
        (output_dir / "runtime_audit.json").write_text(
            json.dumps(audit, indent=2), encoding="utf-8"
        )

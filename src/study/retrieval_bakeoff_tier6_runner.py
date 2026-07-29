from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from src.db.episode import get_episode_by_id
from src.db.schema import init_db
from src.inference.provider import (
    RESPONSE_BUDGET,
    detect_explicit_persistent_rule,
)
from src.memory.context_matched_stm import (
    ContextMatchedStmRetrievalEngine,
    context_match_accounting,
)
from src.memory.topic_manager import TopicManager
from src.observability.observer import Observer
from src.observability.run_config import RunConfig
from src.runners.stm_runner import StmRunner
from src.study.checkpoint import restore_checkpoint, write_checkpoint
from src.study.domain_labels import ground_truth_domain_for_turn
from src.study.study_009_runner import Study009Runner


class RetrievalBakeoffTier6Runner(Study009Runner):
    def __init__(
        self,
        *,
        n_cap: int,
        k_threshold: float,
        payload_budget: int,
        **kwargs,
    ) -> None:
        super().__init__(composition="S", **kwargs)
        self.n_cap = n_cap
        self.k_threshold = k_threshold
        self.payload_budget = payload_budget

    def run(self) -> Path:
        output_dir = (
            Path(self.study_dir) / self.run_id / "context_matched_stm"
        )
        config = RunConfig(
            condition="tier6_context_matched_stm",
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
                    f"Refusing to overwrite Tier 6 run: {output_dir}"
                )
            observer.init_run()

        accounting_path = output_dir / "logs" / "context_match.jsonl"
        if resume_payload is None:
            accounting_path.write_text("", encoding="utf-8", newline="\n")
        conn = init_db(str(output_dir / "study.db"))
        topic_manager = TopicManager(conn)
        retrieval_engine = ContextMatchedStmRetrievalEngine(
            conn,
            n_cap=self.n_cap,
            k_threshold=self.k_threshold,
            payload_budget=self.payload_budget,
            embedding_provider=self._embed,
            system_prompt=self.system_prompt,
        )
        runner = StmRunner(
            conn,
            self._embed,
            topic_manager,
            retrieval_engine,
        )

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
                raise AssertionError("Tier 6 retrieval produced no accounting")
            accounting = {
                "turn_number": turn_number,
                "n_cap": self.n_cap,
                "k_threshold": self.k_threshold,
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
            ) and (
                result.contains_rule or record.rule_store_count != 0
            ):
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
                response = {
                    "turn_number": turn_number,
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                }
                rubric_responses.append(response)
                completeness_rows.append({
                    "turn_number": turn_number,
                    "has_scoreable_answer": bool(assistant_message.strip()),
                    "output_tokens": result.output_tokens,
                    "reached_response_budget": (
                        (result.output_tokens or 0) >= RESPONSE_BUDGET
                    ),
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
        self._write_scoring_surface(
            output_dir,
            rubric_responses,
            completeness_rows,
        )
        self._write_tier6_runtime_audit(
            output_dir,
            time.perf_counter() - started,
        )
        self._write_mechanism_seal(output_dir)
        return output_dir

    def _write_scoring_surface(
        self,
        output_dir: Path,
        responses: list[dict],
        completeness_rows: list[dict],
    ) -> None:
        expected_turns = sorted(
            turn
            for turn in self.rubric_turns
            if any(int(item["turn"]) == turn for item in self.turns)
        )
        observed_turns = [
            int(response["turn_number"]) for response in responses
        ]
        completeness_pass = (
            observed_turns == expected_turns
            and len(completeness_rows) == len(expected_turns)
            and all(
                row["has_scoreable_answer"]
                and not row["reached_response_budget"]
                for row in completeness_rows
            )
        )
        payload = {
            "run_id": self.run_id,
            "arm_label": "tier6_context_matched_stm",
            "expected_turns": expected_turns,
            "observed_turns": observed_turns,
            "completeness_status": (
                "PASS" if completeness_pass else "FAIL"
            ),
            "completeness": completeness_rows,
            "responses": responses,
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        payload["payload_sha256"] = hashlib.sha256(encoded).hexdigest()
        (output_dir / "scoring_surface.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def _write_tier6_runtime_audit(
        self,
        output_dir: Path,
        duration: float,
    ) -> None:
        modules = sorted(
            name for name in __import__("sys").modules if name.startswith("src.")
        )
        forbidden_at_completion = [
            name
            for name in modules
            if any(
                token in name
                for token in ("ltm", "digest", "dream", "promotion")
            )
        ]
        start_modules = set(self.import_graph_at_start)
        forbidden = [
            name
            for name in forbidden_at_completion
            if name not in start_modules
        ]
        audit = {
            "composition": "tier6_context_matched_stm",
            "duration_seconds": duration,
            "turn_count": len(self.turns),
            "n_cap": self.n_cap,
            "k_threshold": self.k_threshold,
            "payload_budget": self.payload_budget,
            "modules_at_runner_start": self.import_graph_at_start,
            "modules_at_completion": modules,
            "forbidden_modules_at_completion": forbidden_at_completion,
            "forbidden_modules_loaded": forbidden,
        }
        (output_dir / "runtime_audit.json").write_text(
            json.dumps(audit, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        if forbidden:
            raise RuntimeError(
                "Tier 6 runtime loaded forbidden memory-tier modules: "
                + ", ".join(forbidden)
            )

    @staticmethod
    def _write_mechanism_seal(output_dir: Path) -> None:
        excluded = {"scoring_surface.json", "mechanism_seal.json"}
        hashes = {}
        for path in sorted(output_dir.rglob("*")):
            if not path.is_file() or path.name in excluded:
                continue
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            hashes[path.relative_to(output_dir).as_posix()] = digest.hexdigest()
        aggregate = hashlib.sha256()
        for relative, digest in sorted(hashes.items()):
            aggregate.update(relative.encode("utf-8"))
            aggregate.update(b"\0")
            aggregate.update(digest.encode("ascii"))
            aggregate.update(b"\0")
        payload = {
            "status": "SEALED_BEFORE_SCORING",
            "scoring_surface": "scoring_surface.json",
            "mechanism_file_count": len(hashes),
            "mechanism_files": hashes,
            "aggregate_sha256": aggregate.hexdigest(),
        }
        (output_dir / "mechanism_seal.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    @staticmethod
    def _append_jsonl(path: Path, payload: dict) -> None:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(
                json.dumps(payload, sort_keys=True, ensure_ascii=True) + "\n"
            )

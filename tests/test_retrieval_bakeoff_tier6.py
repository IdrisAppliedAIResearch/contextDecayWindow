from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import json

import numpy as np
import pytest

from scripts.run_retrieval_bakeoff_tier6 import assert_server
from src.db.episode import store_episode
from src.db.schema import init_db
from src.inference.provider import InferenceResult
from src.memory.stm_context_builder import render_episode_block
from src.memory.context_matched_stm import (
    ContextMatchedStmRetrievalEngine,
    extract_arm_l_payload,
    extract_stm_payload,
    pack_stm_payload,
    render_stm_payload,
)
from src.study.retrieval_bakeoff_tier6_runner import (
    RetrievalBakeoffTier6Runner,
)


ROOT = Path(__file__).resolve().parents[1]


def _episode(
    episode_id: str,
    turn: int,
    *,
    text: str = "text",
    similarity: float | None = None,
) -> dict:
    episode = {
        "id": episode_id,
        "turn_number": turn,
        "topic_label": "topic",
        "user_message": f"user {text}",
        "assistant_message": f"assistant {text}",
    }
    if similarity is not None:
        episode["similarity"] = similarity
    return episode


def _unit(index: int) -> np.ndarray:
    vector = np.zeros(1_024, dtype=np.float32)
    vector[index] = 1.0
    return vector


def test_tier6_runtime_import_graph_has_no_memory_tier_modules() -> None:
    code = (
        "import sys; import src.memory.context_matched_stm; "
        "print('\\n'.join(sorted(name for name in sys.modules "
        "if name.startswith('src.'))))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    forbidden = [
        name
        for name in result.stdout.splitlines()
        if any(token in name for token in ("ltm_store", "digest", "dream", "promotion"))
    ]
    assert forbidden == []


def test_exact_payload_extractors_charge_outer_blocks_and_separators() -> None:
    recent = render_episode_block(
        "recent_context",
        [_episode("n", 1)],
        "recent",
    )
    stm = render_episode_block(
        "retrieved_stm",
        [_episode("k", 2, similarity=0.5)],
        "stm",
    )
    ltm = "<retrieved_ltm/>"
    prompt = f"system\n\n{recent}\n\n{stm}\n\n{ltm}\n\n<current_turn/>"

    assert extract_stm_payload(prompt) == f"{recent}\n\n{stm}"
    assert extract_arm_l_payload(prompt) == f"{recent}\n\n{stm}\n\n{ltm}"


def test_packer_skips_oversized_candidates_and_keeps_n_precedence() -> None:
    duplicate_n = _episode("duplicate", 1)
    duplicate_k = _episode("duplicate", 1, similarity=0.9)
    oversized = _episode("large", 2, text="x" * 2_000)
    small = _episode("small", 3, similarity=0.8)
    budget = len(render_stm_payload([duplicate_n], [small]))

    packed = pack_stm_payload(
        [duplicate_n, oversized],
        [duplicate_k, small],
        budget,
    )

    assert packed.selected_ids == ("duplicate", "small")
    assert packed.skipped_n_ids == ("large",)
    assert packed.duplicate_ids == ("duplicate",)
    assert packed.serialized_chars == budget


def test_context_matched_engine_uses_committed_character_cap(tmp_path: Path) -> None:
    conn = init_db(str(tmp_path / "tier6.db"))
    episode_ids = [
        store_episode(
            conn,
            f"user {index} " + ("x" * 200),
            f"assistant {index} " + ("y" * 200),
            _unit(index % 2),
            index + 1,
        )
        for index in range(14)
    ]
    first_two = [
        _episode(
            episode_ids[index],
            index + 1,
            text=("x" * 200),
        )
        for index in range(2)
    ]
    budget = len(render_stm_payload(first_two, []))
    engine = ContextMatchedStmRetrievalEngine(
        conn,
        n_cap=12,
        k_threshold=0.48,
        payload_budget=budget,
        embedding_provider=lambda _: _unit(0),
        system_prompt="system",
    )

    result = engine.retrieve("probe", 15)

    assert result.retrieval_payload_chars <= budget
    assert extract_stm_payload(result.constructed_prompt)
    assert result.n_candidate_count == 12
    assert result.k_candidate_count == 7
    assert result.skipped_n_ids
    assert set(result.n_episode_ids) <= set(episode_ids)


def _server_props(**overrides) -> dict:
    props = {
        "total_slots": 1,
        "build_info": "build-hash",
        "default_generation_settings": {
            "n_ctx": 50_176,
            "params": {
                "seed": 5005,
                "speculative.types": "none",
            },
        },
    }
    for key, value in overrides.items():
        if key == "n_ctx":
            props["default_generation_settings"]["n_ctx"] = value
        elif key in {"seed", "speculative.types"}:
            props["default_generation_settings"]["params"][key] = value
        else:
            props[key] = value
    return props


def test_tier6_server_guard_accepts_only_registered_runtime() -> None:
    assert_server(_server_props())
    for key, value in (
        ("seed", 1),
        ("total_slots", 2),
        ("n_ctx", 49_999),
        ("speculative.types", "draft"),
        ("build_info", ""),
    ):
        with pytest.raises(
            RuntimeError,
            match="Registered Tier 6 runtime guard failed",
        ):
            assert_server(_server_props(**{key: value}))


def test_tier6_runner_writes_accounting_and_scoring_surface(
    tmp_path: Path,
) -> None:
    class FakeInference:
        completion_count = 0

        def complete(self, prompt: str, suppress_rule_detection: bool = False):
            self.completion_count += 1
            return InferenceResult(
                assistant_message=f"deterministic response {self.completion_count}",
                tokens_per_second=10.0,
                time_to_first_token=0.01,
                output_tokens=8,
            )

    def fake_embed(text: str) -> np.ndarray:
        vector = np.zeros(1_024, dtype=np.float32)
        vector[sum(text.encode("utf-8")) % 16] = 1.0
        return vector

    runner = RetrievalBakeoffTier6Runner(
        script_path=str(ROOT / "experiments" / "study_005" / "script.json"),
        study_dir=str(tmp_path),
        run_id="fixture",
        n_cap=12,
        k_threshold=0.48,
        payload_budget=20_000,
        max_turns=2,
        expected_script_digest=(
            "d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01"
        ),
        inference_provider=FakeInference(),
        embedding_provider=fake_embed,
    )

    output_dir = runner.run()

    accounting = (
        output_dir / "logs" / "context_match.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    scoring = json.loads(
        (output_dir / "scoring_surface.json").read_text(encoding="utf-8")
    )
    audit = json.loads(
        (output_dir / "runtime_audit.json").read_text(encoding="utf-8")
    )
    seal = json.loads(
        (output_dir / "mechanism_seal.json").read_text(encoding="utf-8")
    )
    assert len(accounting) == 2
    assert scoring["completeness_status"] == "PASS"
    assert scoring["expected_turns"] == []
    assert audit["forbidden_modules_loaded"] == []
    assert seal["status"] == "SEALED_BEFORE_SCORING"
    assert "scoring_surface.json" not in seal["mechanism_files"]

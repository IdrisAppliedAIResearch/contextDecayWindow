import subprocess
import sys
from pathlib import Path

import numpy as np

from src.db.episode import store_episode
from src.db.schema import init_db
from src.memory.stm_context_builder import build_stm_context
from src.memory.stm_retrieval_engine import StmRetrievalEngine


ROOT = Path(__file__).resolve().parents[1]


def unit(index: int, dimensions: int = 4) -> np.ndarray:
    vector = np.zeros(dimensions, dtype=np.float32)
    vector[index] = 1.0
    return vector


def test_arm_s_import_graph_has_no_ltm_dream_promotion_or_digest_modules():
    code = (
        "import sys; import src.study.study_009_runner; "
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
        if any(token in name for token in ("ltm", "digest", "dream", "promotion"))
    ]
    assert forbidden == []


def test_stm_context_omits_ltm_tier_entirely():
    prompt = build_stm_context(
        system_prompt="system",
        current_user_message="current",
        recent_episodes=[{
            "id": "recent",
            "turn_number": 2,
            "topic_label": "topic_1",
            "user_message": "recent user",
            "assistant_message": "recent assistant",
        }],
        stm_episodes=[{
            "id": "stm",
            "turn_number": 1,
            "topic_label": "topic_1",
            "user_message": "retrieved user",
            "assistant_message": "retrieved assistant",
            "similarity": 0.8,
        }],
    )

    assert "<recent_context>" in prompt
    assert "<retrieved_stm>" in prompt
    assert "retrieved_ltm" not in prompt
    assert "topic_digest" not in prompt


def test_stm_retrieval_matches_hand_derived_n_plus_k_fixture(tmp_path):
    conn = init_db(str(tmp_path / "fixture.db"))
    episode_ids = [
        store_episode(conn, f"user {index}", f"assistant {index}", unit(index), index + 1)
        for index in range(4)
    ]
    query = unit(0)
    engine = StmRetrievalEngine(
        conn,
        embedding_provider=lambda _: query,
        system_prompt="system",
    )

    result = engine.retrieve("probe", 5)

    assert result.k_episode_ids == [episode_ids[0]]
    assert result.n_episode_ids == episode_ids
    assert result.retrieved_stm_episodes == []
    assert [episode["id"] for episode in result.recent_episodes] == episode_ids
    assert "<retrieved_stm/>" in result.constructed_prompt
    assert "retrieved_ltm" not in result.constructed_prompt


def test_k_only_episode_is_rendered_once_outside_recent_block(tmp_path):
    conn = init_db(str(tmp_path / "fixture.db"))
    episode_ids = []
    for index in range(11):
        embedding = unit(0) if index == 0 else unit(1)
        episode_ids.append(
            store_episode(
                conn,
                f"user {index}",
                f"assistant {index}",
                embedding,
                index + 1,
            )
        )
    conn.execute(
        "UPDATE episodes SET last_retrieved_at = "
        "'2000-01-01T00:00:00+00:00' WHERE id = ?",
        (episode_ids[0],),
    )
    conn.commit()
    engine = StmRetrievalEngine(
        conn,
        embedding_provider=lambda _: unit(0),
        system_prompt="system",
    )

    result = engine.retrieve("probe", 12)

    assert result.k_episode_ids == [episode_ids[0]]
    assert result.retrieved_stm_episodes[0]["id"] == episode_ids[0]
    assert episode_ids[0] not in {
        episode["id"] for episode in result.recent_episodes
    }
    assert result.constructed_prompt.count('turn="1"') == 1

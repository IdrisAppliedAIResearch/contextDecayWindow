from datetime import datetime, timezone

import numpy as np
import pytest

from src.db.episode import store_episode, update_episode_topic
from src.db.schema import init_db
from src.db.topic import store_topic
from src.memory.distilled_ltm_store import (
    CONTENT_STATUS,
    NO_SALIENT_FACT_STATUS,
    assert_record_faithful,
    get_distilled_record_count,
    get_distilled_records,
)
from src.memory.dream_engine import DreamEngine, calculate_salience
from src.memory.retrieval_engine import RetrievalEngine


def _unit_vector(index: int) -> np.ndarray:
    embedding = np.zeros(1024, dtype=np.float32)
    embedding[index] = 1.0
    return embedding


def _topic(conn, label: str = "topic_1") -> str:
    now = datetime.now(timezone.utc).isoformat()
    return store_topic(conn, label, _unit_vector(0), now)


def _episode(
    conn,
    topic_id: str,
    *,
    turn: int,
    user: str,
    assistant: str = "Acknowledged.",
    embedding: np.ndarray | None = None,
) -> str:
    episode_id = store_episode(
        conn,
        user,
        assistant,
        embedding if embedding is not None else _unit_vector(turn),
        turn,
        "synthetic",
    )
    update_episode_topic(conn, episode_id, topic_id)
    return episode_id


def test_study_005_schema_and_raw_store_are_permissive(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    topic_id = _topic(conn)
    episode_id = _episode(
        conn,
        topic_id,
        turn=1,
        user="got it",
        assistant="Okay.",
    )

    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(episodes)")
    }
    raw = conn.execute(
        "SELECT role, text, dreamed, topic_id FROM episodes WHERE id = ?",
        (episode_id,),
    ).fetchone()

    assert {"distilled_ltm", "dream_events"}.issubset(tables)
    assert {"role", "text", "dreamed"}.issubset(columns)
    assert raw == (
        "conversation",
        "User: got it\nAssistant: Okay.",
        0,
        topic_id,
    )


def test_salience_uses_locked_number_weight_and_junk_scores_zero():
    planted = calculate_salience(
        "Halcyon Crossing spans 847 meters under Dr. Anara Bekova."
    )
    junk = calculate_salience("got it")
    number_dense = calculate_salience("samples measured 10, 20, and 30 units")
    entity_only = calculate_salience(
        "Halcyon Crossing and Federal Reserve"
    )

    assert junk == (0, 0, 0)
    assert planted[0] == planted[1] + 2 * planted[2]
    assert number_dense[0] > entity_only[0]
    assert calculate_salience("1. First\n2. Second")[2] == 0


def test_dream_deduplicates_keeps_higher_salience_and_caps_at_three(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    topic_id = _topic(conn)
    duplicate_loser = _episode(
        conn,
        topic_id,
        turn=1,
        user="Halcyon Crossing spans 847 meters.",
        embedding=_unit_vector(0),
    )
    duplicate_winner = _episode(
        conn,
        topic_id,
        turn=2,
        user="Halcyon Crossing spans 847 meters and carries 92.4 tons.",
        embedding=_unit_vector(0),
    )
    for turn, text in (
        (3, "The Annunciation of Forli was completed in 1483."),
        (4, "Dr. Priya Mehta measured inflation at 2.3 percent."),
        (5, "Dr. Kenji Watanabe sampled depths of 600 and 900 meters."),
    ):
        _episode(
            conn,
            topic_id,
            turn=turn,
            user=text,
            embedding=_unit_vector(turn),
        )

    summary = DreamEngine(conn).process_flush(
        duplicate_winner,
        current_turn=111,
    )
    records = get_distilled_records(conn)

    assert summary.evaluated == 5
    assert summary.duplicates_collapsed == 1
    assert summary.records_written == 3
    assert len(records) == 3
    winner_record = next(
        record
        for record in records
        if record["source_episode_id"] == duplicate_winner
    )
    assert duplicate_loser in winner_record["collapsed_episode_ids"]
    assert duplicate_loser in winner_record["source_episode_ids"]
    assert all(record["salience"] >= DreamEngine.SALIENCE_FLOOR for record in records)
    assert conn.execute(
        "SELECT COUNT(*) FROM episodes WHERE dreamed = 1"
    ).fetchone()[0] == 5
    assert conn.execute(
        "SELECT COUNT(*) FROM ltm_episodes"
    ).fetchone()[0] == 0


def test_sparse_topic_writes_marker_without_forcing_junk(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    topic_id = _topic(conn)
    active_id = _episode(
        conn,
        topic_id,
        turn=1,
        user="got it",
        assistant="okay",
        embedding=_unit_vector(1),
    )
    _episode(
        conn,
        topic_id,
        turn=2,
        user="thanks",
        assistant="sure",
        embedding=_unit_vector(2),
    )
    _episode(
        conn,
        topic_id,
        turn=3,
        user="understood",
        assistant="noted",
        embedding=_unit_vector(3),
    )

    summary = DreamEngine(conn).process_flush(active_id, current_turn=111)
    records = get_distilled_records(conn)

    assert summary.marker_written is True
    assert summary.records_written == 0
    assert get_distilled_record_count(conn) == 0
    assert len(records) == 1
    assert records[0]["status"] == NO_SALIENT_FACT_STATUS
    assert records[0]["text"] is None
    assert records[0]["salience"] < DreamEngine.SALIENCE_FLOOR


def test_extractive_assertion_passes_then_trips_on_mangled_text(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    topic_id = _topic(conn)
    active_id = _episode(
        conn,
        topic_id,
        turn=1,
        user="Halcyon Crossing spans 847 meters.",
        embedding=_unit_vector(1),
    )
    _episode(
        conn,
        topic_id,
        turn=2,
        user="okay",
        embedding=_unit_vector(2),
    )
    _episode(
        conn,
        topic_id,
        turn=3,
        user="thanks",
        embedding=_unit_vector(3),
    )
    summary = DreamEngine(conn).process_flush(active_id, current_turn=111)
    distilled_id = summary.distilled_ids[0]

    assert_record_faithful(conn, distilled_id)
    conn.execute(
        "UPDATE distilled_ltm SET text = 'fabricated text' WHERE id = ?",
        (distilled_id,),
    )
    conn.commit()
    with pytest.raises(AssertionError, match="verbatim"):
        assert_record_faithful(conn, distilled_id)


def test_dream_pass_asserts_when_inference_counter_changes(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    topic_id = _topic(conn)
    active_id = _episode(
        conn,
        topic_id,
        turn=1,
        user="Halcyon Crossing spans 847 meters.",
        embedding=_unit_vector(1),
    )
    _episode(
        conn,
        topic_id,
        turn=2,
        user="okay",
        embedding=_unit_vector(2),
    )
    _episode(
        conn,
        topic_id,
        turn=3,
        user="thanks",
        embedding=_unit_vector(3),
    )
    counts = iter([10, 11])
    engine = DreamEngine(conn, inference_call_count=lambda: next(counts))

    with pytest.raises(AssertionError, match="inference model"):
        engine.process_flush(active_id, current_turn=111)

    assert get_distilled_records(conn) == []
    assert conn.execute(
        "SELECT dreamed FROM episodes WHERE id = ?",
        (active_id,),
    ).fetchone()[0] == 0


def test_transition_and_flush_cadence_guards(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    first_topic = _topic(conn, "topic_1")
    second_topic = _topic(conn, "topic_2")
    previous_id = _episode(
        conn,
        first_topic,
        turn=1,
        user="Halcyon Crossing spans 847 meters.",
        embedding=_unit_vector(1),
    )
    _episode(
        conn,
        first_topic,
        turn=2,
        user="Halcyon Crossing opened in 1957.",
        embedding=_unit_vector(3),
    )
    previous_id = _episode(
        conn,
        first_topic,
        turn=3,
        user="Halcyon Crossing carries Route 19.",
        embedding=_unit_vector(4),
    )
    current_id = _episode(
        conn,
        second_topic,
        turn=4,
        user="The Annunciation of Forli dates to 1483.",
        embedding=_unit_vector(2),
    )
    engine = DreamEngine(conn)

    transition = engine.process_transition(previous_id, current_id, 4)
    assert transition.event_type == "transition"
    assert transition.turn == 4
    with pytest.raises(ValueError, match="must run at turn 111"):
        engine.process_flush(current_id, current_turn=110)


def test_transition_skips_subminimum_topic_like_study_004(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    first_topic = _topic(conn, "topic_1")
    second_topic = _topic(conn, "topic_2")
    previous_id = _episode(
        conn,
        first_topic,
        turn=1,
        user="Read the response rules carefully.",
        embedding=_unit_vector(1),
    )
    current_id = _episode(
        conn,
        second_topic,
        turn=2,
        user="Halcyon Crossing spans 847 meters.",
        embedding=_unit_vector(2),
    )

    summary = DreamEngine(conn).process_transition(previous_id, current_id, 2)

    assert summary is None
    assert get_distilled_records(conn) == []
    assert conn.execute(
        "SELECT dreamed FROM episodes WHERE id = ?",
        (previous_id,),
    ).fetchone()[0] == 0


def test_retrieval_reads_distilled_ltm_and_renders_provenance(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    topic_id = _topic(conn)
    active_id = _episode(
        conn,
        topic_id,
        turn=1,
        user="Halcyon Crossing spans 847 meters.",
        embedding=_unit_vector(1),
    )
    _episode(
        conn,
        topic_id,
        turn=2,
        user="okay",
        embedding=_unit_vector(2),
    )
    _episode(
        conn,
        topic_id,
        turn=3,
        user="thanks",
        embedding=_unit_vector(3),
    )
    DreamEngine(conn).process_flush(active_id, current_turn=111)
    engine = RetrievalEngine(
        conn,
        embedding_provider=lambda _: _unit_vector(1),
        system_prompt="System",
        ltm_source="distilled",
    )

    result = engine.retrieve("What was the span?", turn_number=112)

    assert len(result.retrieved_ltm_episodes) == 1
    retrieved = result.retrieved_ltm_episodes[0]
    assert retrieved["id"] == active_id
    assert retrieved["distilled_id"]
    assert retrieved["dream_event"] == 111
    assert retrieved["source_turns"] == [1]
    assert 'distilled_id="' in result.constructed_prompt
    assert 'dream_event="111"' in result.constructed_prompt
    assert 'source_turns="1"' in result.constructed_prompt
    assert "promoted_at_turn=" not in result.constructed_prompt
    assert "salience=" not in result.constructed_prompt


def test_distilled_source_can_be_empty(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    engine = RetrievalEngine(
        conn,
        embedding_provider=lambda _: _unit_vector(1),
        ltm_source="distilled",
    )

    result = engine.retrieve("nothing stored", turn_number=1)

    assert result.retrieved_ltm_episodes == []
    assert "<retrieved_ltm/>" in result.constructed_prompt


def test_invalid_ltm_source_is_rejected(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    with pytest.raises(ValueError, match="Unsupported LTM source"):
        RetrievalEngine(conn, ltm_source="unknown")

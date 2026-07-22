from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from src.analysis.study_005_evaluation import (
    evaluate_bars,
    evaluate_formation,
    load_fact_key,
    validate_scores,
)
from src.db.episode import (
    get_episode_by_id,
    store_episode,
    update_episode_topic,
)
from src.db.schema import init_db
from src.db.topic import store_topic
from src.memory.distilled_ltm_store import write_distilled_record
from src.memory.dream_engine import DreamEngine


ROOT = Path(__file__).resolve().parents[1]
FACT_KEY = ROOT / "experiments" / "study_005" / "q_facts_key.md"


def _embedding(index: int) -> np.ndarray:
    result = np.zeros(1024, dtype=np.float32)
    result[index] = 1.0
    return result


def _topic(conn) -> str:
    now = datetime.now(timezone.utc).isoformat()
    return store_topic(conn, "topic_1", _embedding(0), now)


def _store(conn, topic_id: str, turn: int, user: str) -> str:
    episode_id = store_episode(
        conn,
        user,
        "Acknowledged.",
        _embedding(turn),
        turn,
        None,
    )
    update_episode_topic(conn, episode_id, topic_id)
    return episode_id


def _all_scores(value: float = 1.0) -> dict[str, float]:
    return {f"Q{index}": value for index in range(1, 15)}


def test_fact_key_loads_all_four_domains():
    targets = load_fact_key(FACT_KEY)

    assert len(targets) == 13
    assert {target.domain for target in targets} == {
        "civil engineering",
        "renaissance art",
        "monetary policy",
        "marine biology",
    }


def test_formation_harness_reports_present_and_withheld_fact(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    topic_id = _topic(conn)
    source_id = _store(
        conn,
        topic_id,
        3,
        "Halcyon Crossing has a main span of 847 meters.",
    )
    DreamEngine(conn).process_flush(source_id, current_turn=111)

    result = evaluate_formation(conn, FACT_KEY)

    assert result["per_domain"]["civil engineering"]["present"] is True
    assert result["per_domain"]["renaissance art"]["present"] is False
    assert result["domains_present"] == 1
    assert result["bar_1_pass"] is False
    assert result["faithfulness"] == 1.0
    assert result["non_content_count"] == 0


def test_non_content_record_flips_zero_non_content_clause(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    topic_id = _topic(conn)
    source_id = _store(conn, topic_id, 3, "got it")
    source = get_episode_by_id(conn, source_id)
    write_distilled_record(
        conn,
        source_episode=source,
        topic_id=topic_id,
        topic_label="topic_1",
        source_episode_ids=[source_id],
        source_turns=[3],
        collapsed_episode_ids=[],
        salience=0,
        dream_event=31,
        event_type="transition",
    )
    conn.commit()

    result = evaluate_formation(conn, FACT_KEY)

    assert result["non_content_count"] == 1
    assert result["bar_1_pass"] is False


def test_faithfulness_harness_flags_mangled_record(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    topic_id = _topic(conn)
    source_id = _store(
        conn,
        topic_id,
        3,
        "Halcyon Crossing has a main span of 847 meters.",
    )
    summary = DreamEngine(conn).process_flush(source_id, current_turn=111)
    conn.execute(
        "UPDATE distilled_ltm SET text = 'not in the source' WHERE id = ?",
        (summary.distilled_ids[0],),
    )
    conn.commit()

    result = evaluate_formation(conn, FACT_KEY)

    assert result["faithfulness"] == 0.0
    assert result["faithful_records"] == 0
    assert result["bar_1_pass"] is False


def test_bar_2_is_not_evaluable_when_formation_fails():
    formation = {"bar_1_pass": False}

    result = evaluate_bars(
        formation=formation,
        treatment_scores=_all_scores(),
        control_scores=_all_scores(),
        probe_distilled_ltm={"Q11": True, "Q14": True},
    )

    assert result["bar_1"]["status"] == "FAIL"
    assert result["bar_2"]["status"] == "NOT EVALUABLE"
    assert result["bar_2"]["pass"] is None


def test_bar_arithmetic_requires_breadth_provenance_and_categories():
    treatment = _all_scores()
    treatment["Q11"] = 0.5
    treatment["Q14"] = 1.0
    control = _all_scores()

    passed = evaluate_bars(
        formation={"bar_1_pass": True},
        treatment_scores=treatment,
        control_scores=control,
        probe_distilled_ltm={"Q11": True, "Q14": True},
    )
    missing_provenance = evaluate_bars(
        formation={"bar_1_pass": True},
        treatment_scores=treatment,
        control_scores=control,
        probe_distilled_ltm={"Q11": False, "Q14": True},
    )

    assert passed["bar_2"]["status"] == "PASS"
    assert passed["bar_3"]["status"] == "FAIL"
    assert missing_provenance["bar_2"]["status"] == "FAIL"


def test_score_validation_requires_all_fourteen_questions():
    scores = _all_scores()
    scores.pop("Q14")
    with pytest.raises(ValueError, match="Q1-Q14"):
        validate_scores(scores)

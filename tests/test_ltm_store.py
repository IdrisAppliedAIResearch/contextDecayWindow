import os
import tempfile

import numpy as np

from migrations.study_003_ltm_init import apply_migration
from src.db.schema import init_db
from src.memory.ltm_store import (
    get_ltm_centroid,
    get_ltm_episode_count,
    log_promotion_event,
    promote_episode,
)


class TestStudy003LtmStore:
    def setup_method(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.conn = init_db(self.db_path)

    def teardown_method(self):
        self.conn.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_migration_is_idempotent_and_creates_both_tables(self):
        apply_migration(self.conn)
        apply_migration(self.conn)

        tables = {
            row[0] for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"ltm_episodes", "ltm_promotion_log"}.issubset(tables)

    def test_empty_ltm_has_no_centroid_or_episodes(self):
        assert get_ltm_centroid(self.conn) is None
        assert get_ltm_episode_count(self.conn) == 0

    def test_promote_episode_stores_metadata_and_embedding(self):
        embedding = np.full(1024, 0.25, dtype=np.float32)

        row_id = promote_episode(
            self.conn, "episode-1", 31, "topic_1", "weighted_threshold", None,
            0.8, 0.4, 0.2, 0.1, 0.475, "User: test\nAssistant: response", embedding,
        )

        row = self.conn.execute(
            "SELECT episode_id, topic, trigger_type, embedding FROM ltm_episodes WHERE id = ?",
            (row_id,),
        ).fetchone()
        assert row[:3] == ("episode-1", "topic_1", "weighted_threshold")
        assert np.array_equal(np.frombuffer(row[3], dtype=np.float32), embedding)
        assert get_ltm_episode_count(self.conn) == 1

    def test_centroid_and_promotion_log_are_computed_correctly(self):
        promote_episode(
            self.conn, "episode-1", 31, "topic_1", "all_or_nothing", "novelty",
            0.95, 0.0, 0.0, 0.0, 0.3325, "first", np.ones(1024, dtype=np.float32),
        )
        promote_episode(
            self.conn, "episode-2", 31, "topic_1", "weighted_threshold", None,
            0.5, 0.5, 0.5, 0.5, 0.5, "second", np.full(1024, 3.0, dtype=np.float32),
        )
        log_promotion_event(self.conn, 31, "topic_1", 4, 2)

        centroid = get_ltm_centroid(self.conn)
        log_row = self.conn.execute(
            "SELECT turn, topic, episodes_evaluated, episodes_promoted, promotion_rate "
            "FROM ltm_promotion_log"
        ).fetchone()
        assert centroid.shape == (1024,)
        assert np.allclose(centroid, 2.0)
        assert log_row == (31, "topic_1", 4, 2, 0.5)

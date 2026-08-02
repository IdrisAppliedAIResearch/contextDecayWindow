"""CC-004 restart persistence: tests P1-P6.

The checkpoint path had run exactly once, in an incident. These turn the
properties a deployed agent actually depends on into assertions.

Kills are real. A child interpreter is started, told to append, and then
killed with no chance to clean up - `Popen.kill()` is `TerminateProcess`
on Windows and `SIGKILL` elsewhere; neither runs handlers, flushes
buffers, or closes the database. Anything that survives that survived
because SQLite put it on disk before `append()` returned, which is
precisely the durability point CC-004 requires be stated.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "episodic" / "src"))

from episodic import (  # noqa: E402
    ConfigMismatchError,
    EmbeddingDriftError,
    EpisodeStore,
    EpisodicConfig,
    StoreCorruptError,
)

EMBEDDER_SOURCE = textwrap.dedent(
    """
    import hashlib
    import numpy as np

    def embedder(text):
        seed = int.from_bytes(
            hashlib.sha256(text.encode()).digest()[:8], "big"
        )
        return np.random.default_rng(seed).standard_normal(1024).astype(
            np.float32
        )
    """
)


def embedder(text: str) -> np.ndarray:
    """Deterministic and content-derived, so it agrees across processes."""
    seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")
    return np.random.default_rng(seed).standard_normal(1024).astype(np.float32)


def config(**overrides) -> EpisodicConfig:
    base = {"recency_window_n": 4, "selector_cluster_count": 4}
    base.update(overrides)
    return EpisodicConfig(**base)


def fill(path: Path, turns: int, start: int = 0) -> None:
    store = EpisodeStore(path, config(), embedder=embedder)
    try:
        for index in range(start, start + turns):
            store.append("user", f"question {index} about topic {index % 4}")
            store.append(
                "assistant", f"answer {index} " + "detail " * (index % 5 + 1)
            )
    finally:
        store.close()


def run_child(path: Path, body: str, *, expect_kill: bool) -> None:
    """Run `body` in a child interpreter and kill it without cleanup."""
    script = (
        f"import sys; sys.path.insert(0, {str(REPO_ROOT / 'episodic' / 'src')!r})\n"
        + EMBEDDER_SOURCE
        + textwrap.dedent(
            f"""
            from episodic import EpisodeStore, EpisodicConfig
            store = EpisodeStore(
                {str(path)!r},
                EpisodicConfig(recency_window_n=4, selector_cluster_count=4),
                embedder=embedder,
            )
            """
        )
        + textwrap.dedent(body)
    )
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if expect_kill:
        # The child prints a marker once its writes are acknowledged.
        assert process.stdout is not None
        marker = process.stdout.readline()
        assert marker.strip() == "READY", f"child did not reach the marker: {marker!r}"
        process.kill()
        process.wait(timeout=30)
    else:
        process.wait(timeout=60)
        assert process.returncode == 0, process.stderr.read()


class TestP1Durability:
    """P1 - append n turns, kill, reopen: all n present and verbatim."""

    def test_acknowledged_turns_survive_a_kill(self, tmp_path):
        path = tmp_path / "store.db"
        run_child(
            path,
            """
            for index in range(8):
                store.append("user", f"question {index}")
                store.append("assistant", f"answer {index}")
            print("READY", flush=True)
            import time; time.sleep(60)
            """,
            expect_kill=True,
        )
        store = EpisodeStore(path, config(), embedder=embedder)
        try:
            rows = store._all_episodes()
            assert len(rows) == 8
            for index, row in enumerate(rows):
                assert row["user_message"] == f"question {index}"
                assert row["assistant_message"] == f"answer {index}"
                assert row["turn_number"] == index + 1
        finally:
            store.close()

    def test_turn_numbering_continues_after_a_kill(self, tmp_path):
        path = tmp_path / "store.db"
        run_child(
            path,
            """
            for index in range(5):
                store.append("user", f"q{index}")
                store.append("assistant", f"a{index}")
            print("READY", flush=True)
            import time; time.sleep(60)
            """,
            expect_kill=True,
        )
        store = EpisodeStore(path, config(), embedder=embedder)
        try:
            store.append("user", "after restart")
            store.append("assistant", "still counting")
            rows = store._all_episodes()
            assert [row["turn_number"] for row in rows] == list(range(1, 7))
        finally:
            store.close()


class TestP2ByteIdenticalContext:
    """P2 - the core guarantee: same query and budget, same block."""

    def test_block_is_byte_identical_across_restart(self, tmp_path):
        path = tmp_path / "store.db"
        fill(path, 30)

        first = EpisodeStore(path, config(), embedder=embedder)
        try:
            before, before_report = first.context("topic 2 details", 8_000)
        finally:
            first.close()

        second = EpisodeStore(path, config(), embedder=embedder)
        try:
            after, after_report = second.context("topic 2 details", 8_000)
        finally:
            second.close()

        assert before == after
        assert (
            hashlib.sha256(before.encode()).hexdigest()
            == hashlib.sha256(after.encode()).hexdigest()
        )
        assert before_report.chars_delivered == after_report.chars_delivered
        assert before_report.dropped_ids == after_report.dropped_ids

    def test_the_identical_block_is_not_empty(self, tmp_path):
        """Two empty stores also produce identical blocks (section 2.3)."""
        path = tmp_path / "store.db"
        fill(path, 30)
        store = EpisodeStore(path, config(), embedder=embedder)
        try:
            block, report = store.context("topic 2 details", 8_000)
        finally:
            store.close()

        assert report.episodes_delivered > 0
        assert "<episode" in block
        assert "question" in block and "answer" in block
        assert len(block) > 500

    def test_block_survives_a_kill_not_just_a_clean_close(self, tmp_path):
        path = tmp_path / "store.db"
        fill(path, 20)
        store = EpisodeStore(path, config(), embedder=embedder)
        try:
            before, _ = store.context("topic 1", 8_000)
        finally:
            store.close()

        run_child(
            path,
            """
            print("READY", flush=True)
            import time; time.sleep(60)
            """,
            expect_kill=True,
        )
        store = EpisodeStore(path, config(), embedder=embedder)
        try:
            after, _ = store.context("topic 1", 8_000)
        finally:
            store.close()
        assert before == after


class TestP3CrashConsistency:
    """P3 - a kill mid-append leaves no half-written turn."""

    def test_turn_is_wholly_present_or_wholly_absent(self, tmp_path):
        path = tmp_path / "store.db"
        run_child(
            path,
            """
            for index in range(6):
                store.append("user", f"q{index}")
                store.append("assistant", f"a{index}")
            store.append("user", "orphaned user message")
            print("READY", flush=True)
            import time; time.sleep(60)
            """,
            expect_kill=True,
        )
        store = EpisodeStore(path, config(), embedder=embedder)
        try:
            rows = store._all_episodes()
            assert len(rows) == 6
            for row in rows:
                assert row["user_message"]
                assert row["assistant_message"]
                assert row["embedding"]
            assert all(
                row["user_message"] != "orphaned user message" for row in rows
            )
        finally:
            store.close()

    def test_a_pending_user_message_resumes_correctly(self, tmp_path):
        """The half of a turn that is allowed to persist is the user half."""
        path = tmp_path / "store.db"
        run_child(
            path,
            """
            store.append("user", "half a turn")
            print("READY", flush=True)
            import time; time.sleep(60)
            """,
            expect_kill=True,
        )
        store = EpisodeStore(path, config(), embedder=embedder)
        try:
            assert store._all_episodes() == []
            store.append("assistant", "completed after restart")
            rows = store._all_episodes()
            assert len(rows) == 1
            assert rows[0]["user_message"] == "half a turn"
            assert rows[0]["assistant_message"] == "completed after restart"
        finally:
            store.close()

    def test_a_damaged_file_is_refused_on_open(self, tmp_path):
        path = tmp_path / "store.db"
        fill(path, 12)
        raw = bytearray(path.read_bytes())
        # Corrupt well past the header so the file still looks like a
        # database and only the integrity check can tell the difference.
        for offset in range(4_096, min(len(raw), 12_288)):
            raw[offset] = (raw[offset] + 97) % 256
        path.write_bytes(bytes(raw))

        with pytest.raises(StoreCorruptError):
            EpisodeStore(path, config(), embedder=embedder)

    def test_a_healthy_store_passes_the_integrity_check(self, tmp_path):
        path = tmp_path / "store.db"
        fill(path, 12)
        EpisodeStore(path, config(), embedder=embedder).close()


class TestP4EmbeddingSurvival:
    """P4 - stored vectors are bit-identical after a restart."""

    def test_vectors_are_bit_identical_after_restart(self, tmp_path):
        path = tmp_path / "store.db"
        fill(path, 10)

        first = EpisodeStore(path, config(), embedder=embedder)
        try:
            before = [row["embedding"] for row in first._all_episodes()]
        finally:
            first.close()

        second = EpisodeStore(path, config(), embedder=embedder)
        try:
            after = [row["embedding"] for row in second._all_episodes()]
        finally:
            second.close()

        assert before == after
        assert all(len(blob) == 1024 * 4 for blob in after)

    def test_verify_embeddings_reproduces_every_vector(self, tmp_path):
        path = tmp_path / "store.db"
        fill(path, 10)
        store = EpisodeStore(path, config(), embedder=embedder)
        try:
            summary = store.verify_embeddings()
        finally:
            store.close()
        assert summary["bit_identical"]
        assert summary["episodes_checked"] == 10
        assert summary["mismatches"] == ()

    def test_verify_embeddings_detects_a_stored_vector_that_drifted(
        self, tmp_path
    ):
        """The fault the open-time sentinel cannot see.

        The sentinel embeds one fixed string and compares it, so it
        catches a changed *embedder*. It cannot catch a stored vector that
        no longer corresponds to its own row - a bad migration, a partial
        restore, an edit through another connection. That is this check's
        job, and the two are complementary rather than redundant.
        """
        import sqlite3

        path = tmp_path / "store.db"
        fill(path, 6)

        connection = sqlite3.connect(str(path))
        try:
            connection.execute(
                "UPDATE episodes SET embedding = ? WHERE turn_number = 3",
                (np.zeros(1024, dtype=np.float32).tobytes(),),
            )
            connection.commit()
        finally:
            connection.close()

        store = EpisodeStore(path, config(), embedder=embedder)
        try:
            with pytest.raises(EmbeddingDriftError):
                store.verify_embeddings()
            summary = store.verify_embeddings(raise_on_drift=False)
            assert not summary["bit_identical"]
            assert summary["mismatches"] == (3,)
            assert summary["episodes_checked"] == 6
        finally:
            store.close()

    def test_a_changed_embedder_is_caught_at_open_by_the_sentinel(
        self, tmp_path
    ):
        """H1 still fires first, before any per-row check is reached."""
        from episodic import CallShapeError

        path = tmp_path / "store.db"
        fill(path, 4)

        def drifted(text: str) -> np.ndarray:
            return embedder(text) + np.float32(0.5)

        with pytest.raises(CallShapeError):
            EpisodeStore(path, config(), embedder=drifted)

    def test_survival_beats_rebuild(self, tmp_path):
        """Vectors live in the row, so there is no cache to rebuild."""
        path = tmp_path / "store.db"
        fill(path, 5)
        store = EpisodeStore(path, config(), embedder=embedder)
        try:
            rows = store._all_episodes()
        finally:
            store.close()
        for row in rows:
            recomputed = embedder(
                f"User: {row['user_message']}\n"
                f"Assistant: {row['assistant_message']}"
            )
            assert recomputed.tobytes() == row["embedding"]


class TestP5ConfigIntegrity:
    """P5 - reopening under a changed config raises."""

    def test_changed_config_raises(self, tmp_path):
        path = tmp_path / "store.db"
        fill(path, 4)
        with pytest.raises(ConfigMismatchError):
            EpisodeStore(path, config(recency_window_n=9), embedder=embedder)

    def test_same_config_reopens(self, tmp_path):
        path = tmp_path / "store.db"
        fill(path, 4)
        EpisodeStore(path, config(), embedder=embedder).close()

    def test_override_rebinds_deliberately(self, tmp_path):
        path = tmp_path / "store.db"
        fill(path, 4)
        store = EpisodeStore(
            path,
            config(recency_window_n=9),
            embedder=embedder,
            override_config=True,
        )
        store.close()
        EpisodeStore(path, config(recency_window_n=9), embedder=embedder).close()

    def test_config_survives_a_kill(self, tmp_path):
        path = tmp_path / "store.db"
        run_child(
            path,
            """
            store.append("user", "q")
            store.append("assistant", "a")
            print("READY", flush=True)
            import time; time.sleep(60)
            """,
            expect_kill=True,
        )
        with pytest.raises(ConfigMismatchError):
            EpisodeStore(path, config(recency_window_n=9), embedder=embedder)


class TestP6RepeatedRestart:
    """P6 - 100 restart cycles: no drift, no growth in open time."""

    def test_hundred_cycles_leave_content_and_context_unchanged(
        self, tmp_path
    ):
        path = tmp_path / "store.db"
        fill(path, 25)

        store = EpisodeStore(path, config(), embedder=embedder)
        try:
            baseline_block, _ = store.context("topic 3", 8_000)
            baseline_rows = store._all_episodes()
        finally:
            store.close()

        open_times: list[float] = []
        for _ in range(100):
            started = time.perf_counter()
            store = EpisodeStore(path, config(), embedder=embedder)
            open_times.append(time.perf_counter() - started)
            try:
                block, _ = store.context("topic 3", 8_000)
                rows = store._all_episodes()
            finally:
                store.close()
            assert block == baseline_block
            assert rows == baseline_rows

        first_ten = sum(open_times[:10]) / 10
        last_ten = sum(open_times[-10:]) / 10
        # Open cost must not scale with the number of times it has been
        # opened. The bound is deliberately loose: this catches an O(n)
        # regression, not scheduler noise on a shared machine.
        assert last_ten < max(first_ten * 5.0, 0.05), (
            f"open time grew from {first_ten * 1000:.2f}ms to "
            f"{last_ten * 1000:.2f}ms over 100 cycles"
        )

    def test_file_does_not_grow_across_restarts(self, tmp_path):
        path = tmp_path / "store.db"
        fill(path, 20)
        sizes = []
        for _ in range(25):
            EpisodeStore(path, config(), embedder=embedder).close()
            sizes.append(path.stat().st_size)
        assert len(set(sizes)) == 1, f"store size drifted across opens: {sizes}"


class TestDurabilityPointIsStated:
    """Requirement 2.2.1: the durability point is documented, not implied."""

    def test_synchronous_is_full(self, tmp_path):
        path = tmp_path / "store.db"
        store = EpisodeStore(path, config(), embedder=embedder)
        try:
            assert store._conn.execute("PRAGMA synchronous").fetchone()[0] == 2
        finally:
            store.close()

    def test_journal_mode_is_explicit(self, tmp_path):
        path = tmp_path / "store.db"
        store = EpisodeStore(path, config(), embedder=embedder)
        try:
            mode = store._conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode.lower() == "delete"
        finally:
            store.close()

    def test_the_durability_point_is_in_the_docstring(self):
        import episodic._store as module

        assert "append" in module.__doc__
        assert "on disk" in module.__doc__

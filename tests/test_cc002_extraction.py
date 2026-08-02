"""CC-002 acceptance gates that run inside the suite: T2, T5, T7.

T1 (clean-venv install), T3 (E005 replay), and T4 (render replay) run as
scripts with committed artifacts; consistency checks on those artifacts
live here so the suite fails if they drift.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from episodic import EpisodeStore, EpisodicConfig
from episodic._errors import (
    CallShapeError,
    ConfigMismatchError,
    EpisodicError,
    TurnOrderError,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "episodic" / "src" / "episodic"
CC002_ARTIFACTS = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "library_extraction"
    / "artifacts"
    / "cc002"
)

# The registered T2 vocabulary: experiment machinery the library must not
# reference, plus the measurement key the leakage protocol names.
FORBIDDEN_TOKENS = ("plant", "probe", "rubric", "scoring", "replay", "q_facts_key")

STDLIB_OK = {
    "__future__", "hashlib", "json", "os", "shutil", "sqlite3", "time", "uuid",
    "dataclasses", "datetime", "pathlib", "typing", "html",
}
THIRD_PARTY_OK = {"numpy", "llama_cpp"}


def _fake_embedder(text: str) -> np.ndarray:
    seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    return rng.standard_normal(1024).astype(np.float32)


def _config(**overrides) -> EpisodicConfig:
    base = {"recency_window_n": 2, "selector_cluster_count": 4}
    base.update(overrides)
    return EpisodicConfig(**base)


def _filled_store(path, turns: int = 6) -> EpisodeStore:
    store = EpisodeStore(path, _config(), embedder=_fake_embedder)
    for index in range(turns):
        store.append("user", f"question {index} about topic {index % 3}")
        store.append("assistant", f"answer {index} detail " * (index + 1))
    return store


# -- T2: separation is structural ---------------------------------------------


def test_t2_no_experiment_vocabulary_in_library_source() -> None:
    hits = []
    for path in sorted(PACKAGE_ROOT.glob("*.py")):
        source = path.read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_TOKENS:
            if token in source:
                hits.append(f"{path.name}: {token}")
    assert hits == []


def test_t2_import_graph_stays_inside_the_library() -> None:
    """The grep can be evaded by renaming; the import graph cannot."""
    violations = []
    for path in sorted(PACKAGE_ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level > 0:
                    continue
                names = [node.module or ""]
            else:
                continue
            for name in names:
                root = name.split(".")[0]
                if root not in STDLIB_OK | THIRD_PARTY_OK | {"episodic"}:
                    violations.append(f"{path.name}: {name}")
    assert violations == []


def test_t3_and_t4_artifacts_recorded_pass() -> None:
    for name in ("t3_e005_replay.json", "t4_render_replay.json"):
        payload = json.loads(
            (CC002_ARTIFACTS / name).read_text(encoding="utf-8")
        )
        assert payload["status"] == "PASS", name


# -- T5: the H1 sentinel fails loudly -----------------------------------------


def test_t5_call_shape_drift_fails_loudly(tmp_path) -> None:
    path = tmp_path / "store.db"
    EpisodeStore(path, _config(), embedder=_fake_embedder).close()

    def drifted(text: str) -> np.ndarray:
        return _fake_embedder(text) + np.float32(0.01)

    with pytest.raises(CallShapeError) as failure:
        EpisodeStore(path, _config(), embedder=drifted)
    message = str(failure.value)
    assert "sentinel" in message
    assert "DX-001" in message


def test_t5_same_embedder_reopens_cleanly(tmp_path) -> None:
    path = tmp_path / "store.db"
    EpisodeStore(path, _config(), embedder=_fake_embedder).close()
    EpisodeStore(path, _config(), embedder=_fake_embedder).close()


def test_config_mismatch_raises_unless_overridden(tmp_path) -> None:
    path = tmp_path / "store.db"
    EpisodeStore(path, _config(), embedder=_fake_embedder).close()

    with pytest.raises(ConfigMismatchError):
        EpisodeStore(path, _config(recency_window_n=3), embedder=_fake_embedder)

    EpisodeStore(
        path,
        _config(recency_window_n=3),
        embedder=_fake_embedder,
        override_config=True,
    ).close()
    reopened = EpisodeStore(
        path, _config(recency_window_n=3), embedder=_fake_embedder
    )
    reopened.close()


def test_h2_trimming_is_named_unsafe_and_documented() -> None:
    from episodic import _context

    with pytest.raises(EpisodicError):
        EpisodicConfig(candidate_policy="cosine_top_n")
    EpisodicConfig(candidate_policy="unsafe_cosine_top_n")
    docstring = _context._candidate_pool.__doc__
    assert "unsafe" in docstring
    assert "DR-002" in docstring


# -- store behavior ------------------------------------------------------------


def test_append_enforces_alternation(tmp_path) -> None:
    store = EpisodeStore(
        tmp_path / "store.db", _config(), embedder=_fake_embedder
    )
    store.append("user", "one")
    with pytest.raises(TurnOrderError):
        store.append("user", "two")
    store.append("assistant", "reply")
    with pytest.raises(TurnOrderError):
        store.append("assistant", "again")
    store.close()


def test_context_reports_paths_and_exact_chars(tmp_path) -> None:
    store = _filled_store(tmp_path / "store.db")
    block, report = store.context("question about topic 1", 2_000)
    store.close()

    assert report.chars_delivered == len(block)
    assert report.stm_count == 2
    assert (
        report.stm_count + report.k_count + report.coverage_count
        == report.episodes_delivered
    )
    assert report.pool_size == 6
    assert report.truncated is (report.episodes_dropped > 0)


def test_context_truncates_under_a_tight_budget(tmp_path) -> None:
    store = _filled_store(tmp_path / "store.db")
    block, report = store.context("question about topic 1", 400)
    store.close()

    assert len(block) <= 400
    assert report.truncated
    assert report.episodes_dropped > 0
    assert report.chars_wanted > report.chars_delivered


def test_context_is_pure_in_process(tmp_path) -> None:
    store = _filled_store(tmp_path / "store.db")
    first, _ = store.context("question about topic 1", 2_000)
    second, _ = store.context("question about topic 1", 2_000)
    store.close()
    assert first == second


# -- T7: purity across processes ----------------------------------------------

_T7_SCRIPT = """
import hashlib, sys
import numpy as np
from episodic import EpisodeStore, EpisodicConfig

def embedder(text):
    seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    return rng.standard_normal(1024).astype(np.float32)

store = EpisodeStore(
    sys.argv[1],
    EpisodicConfig(recency_window_n=2, selector_cluster_count=4),
    embedder=embedder,
)
for index in range(6):
    store.append("user", f"question {index} about topic {index % 3}")
    store.append("assistant", f"answer {index} detail " * (index + 1))
block, report = store.context("question about topic 1", 2000)
store.close()
digest = hashlib.sha256(block.encode("utf-8")).hexdigest()
print(digest, report.chars_delivered, report.episodes_delivered,
      report.stm_count, report.k_count, report.coverage_count)
"""


def test_t7_context_is_byte_identical_across_processes(tmp_path) -> None:
    script = tmp_path / "t7.py"
    script.write_text(_T7_SCRIPT, encoding="utf-8")
    outputs = []
    for run in ("first", "second"):
        result = subprocess.run(
            [sys.executable, str(script), str(tmp_path / f"{run}.db")],
            capture_output=True,
            text=True,
            check=True,
        )
        outputs.append(result.stdout.strip())
    assert outputs[0] == outputs[1]
    assert outputs[0]

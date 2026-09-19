"""Public release contracts, including migration and continuity opt-out."""
import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from episodic import EpisodeStore, EpisodicConfig, ConfigMismatchError, CallShapeError, EpisodicError
from episodic._timeline import select_timeline, cosine_scores


def embed(text):
    v = np.zeros(1024, dtype=np.float32)
    v[0 if 'relevant' in text or text == 'query' else 1] = 1
    return v


def populate(store, n=40):
    for i in range(1, n + 1):
        store.append('user', 'relevant <&>' if i in (1, 39) else f'other {i}')
        store.append('assistant', 'original')


def test_default_continuity_union_and_opt_out(tmp_path):
    path = tmp_path/'memory.db'
    with EpisodeStore(path, embedder=embed) as store:
        populate(store)
        before = path.read_bytes()
        block, report = store.context('query')
        assert path.read_bytes() == before
        assert report.recency_count == 32 and report.semantic_count == 1
        assert report.episodes_delivered == 33
        assert len(report.selected_ids) == len(set(report.selected_ids)) == 33
        assert block.count('<episode turn=') == 33
        assert block.index('turn="1"') < block.index('turn="9"') < block.index('turn="40"')
        assert '&lt;&amp;&gt;' in block
        assert report.budget_chars is report.retrieval_budget_chars is report.chars_available is None
        assert not report.truncated and report.shortfall_chars == 0
        assert report.episodes_dropped == 0 and not report.dropped_ids
        assert store.context('query')[0] == block
    with pytest.raises(ConfigMismatchError):
        EpisodeStore(path, EpisodicConfig(recency_window_n=0), embedder=embed)
    with EpisodeStore(path, EpisodicConfig(recency_window_n=0), embedder=embed,
                      override_config=True) as store:
        block, report = store.context('query')
        assert report.recency_count == 0 and report.episodes_delivered == 2
        assert 'turn="1"' in block and 'turn="39"' in block
    with EpisodeStore(path, EpisodicConfig(recency_window_n=0), embedder=embed) as store:
        assert store.context('query')[0] == block


def test_explicit_horizon_limits_continuity_and_protects_anchor(tmp_path):
    with EpisodeStore(tmp_path/'s.db', embedder=embed) as store:
        populate(store)
        block, report = store.context('query', through_turn=5, anchor_turn=3)
        assert report.eligible_count == report.episodes_delivered == 5
        assert report.recency_count == 5 and report.through_turn == 5
        assert 'turn="6"' not in block and report.anchor_turn == 3
    with EpisodeStore(tmp_path/'off.db', EpisodicConfig(recency_window_n=0), embedder=embed) as store:
        populate(store)
        block, report = store.context('query', through_turn=5, anchor_turn=3)
        assert report.episodes_delivered == 2 and 'turn="3"' in block
        assert store.context('query', through_turn=0)[1].episodes_delivered == 0


def test_boundary_empty_all_selected_and_no_capacity_cap(tmp_path):
    episodes = [dict(id=str(i), turn_number=i) for i in (3, 1, 2)]
    result = select_timeline(episodes, [.479999, .48, .480001], recency_window_n=0)
    assert result.selected_indices == (1, 2)
    assert select_timeline(episodes, [0, 0, 0], recency_window_n=0).selected_indices == ()
    assert select_timeline(episodes, [1, 1, 1], recency_window_n=0).selected_indices == (1, 2, 0)
    with EpisodeStore(tmp_path/'s.db', EpisodicConfig(recency_window_n=0), embedder=embed) as store:
        assert store.context('query')[1].episodes_delivered == 0
        for _ in range(40):
            store.append('user', 'relevant ' + 'x'*1000)
            store.append('assistant', 'unaltered')
        block, report = store.context('query')
        assert len(block) > 32000 and report.episodes_delivered == 40
        assert not report.truncated


@pytest.mark.parametrize('kwargs', [dict(through_turn=-1), dict(through_turn=True),
    dict(anchor_turn=99), dict(anchor_turn=3, through_turn=2), dict(anchor_turn=1.5)])
def test_invalid_boundaries_fail(tmp_path, kwargs):
    with EpisodeStore(tmp_path/'s.db', embedder=embed) as store:
        populate(store, 4)
        with pytest.raises(EpisodicError):
            store.context('query', **kwargs)


def test_incompatible_options_do_not_silently_change_policy(tmp_path):
    calls = []
    def tracked(text):
        calls.append(text)
        return embed(text)
    with EpisodeStore(tmp_path/'s.db', embedder=tracked) as store:
        initial = len(calls)
        with pytest.raises(EpisodicError, match='no character budget'):
            store.context('query', 32000)
        assert len(calls) == initial
    with EpisodeStore(tmp_path/'aspect.db', EpisodicConfig(aspect_enabled=True), embedder=embed) as store:
        with pytest.raises(EpisodicError, match='ASPECT'):
            store.context('query')


def test_old_config_reopen_and_deliberate_migration(tmp_path):
    path = tmp_path/'old.db'
    legacy = EpisodicConfig(read_policy='legacy_cc80')
    with EpisodeStore(path, legacy, embedder=embed) as store:
        populate(store)
        old_block = store.context('query', 500)[0]
    old = json.loads(legacy.to_json())
    del old['read_policy'], old['timeline_threshold']
    old_json = json.dumps(old, sort_keys=True, separators=(',', ':'))
    with sqlite3.connect(path) as db:
        db.execute("UPDATE episodic_meta SET value=? WHERE key='config'", (old_json,))
    before = path.read_bytes()
    assert EpisodicConfig.from_json(old_json).read_policy == 'legacy_cc80'
    with pytest.raises(ConfigMismatchError):
        EpisodeStore(path, embedder=embed)
    assert path.read_bytes() == before
    with EpisodeStore(path, EpisodicConfig.from_json(old_json), embedder=embed) as store:
        assert store.context('query', 500)[0] == old_block
        original = store._all_episodes()
    with pytest.raises(CallShapeError):
        EpisodeStore(path, embedder=lambda _: np.ones(1024, dtype=np.float32), override_config=True)
    assert path.read_bytes() == before
    with EpisodeStore(path, embedder=embed, override_config=True) as store:
        assert store._all_episodes() == original
        assert store.context('query')[1].read_policy == 'timeline'


def test_vector_validation_and_exact_source_comparator():
    from src.unified_memory.control import select
    rng = np.random.default_rng(5005)
    vectors = rng.normal(size=(100, 8)).astype(np.float32)
    query = vectors[0]
    episodes = [dict(id=str(i), turn_number=i, embedding=v.tobytes()) for i, v in enumerate(vectors)]
    result = select_timeline(episodes, cosine_scores(episodes, query), recency_window_n=0)
    assert {episodes[i]['id'] for i in result.selected_indices} == select([e['id'] for e in episodes], vectors, query)
    for invalid in (np.zeros(8), np.full(8, np.nan), np.ones(7), np.ones((2, 4))):
        with pytest.raises(EpisodicError):
            cosine_scores(episodes, invalid)
    with pytest.raises(EpisodicError):
        select_timeline(episodes + [episodes[0]], [1]*101)


def test_activation_follows_committed_parity():
    root = Path(__file__).resolve().parents[1]
    evidence = json.loads((root/'experiments/components/episodic_chat/timeline_artifacts/parity.json').read_text())
    assert evidence['status'] == 'PASS' and evidence['mismatches'] == 0
    assert evidence['E_timelines'] + evidence['E_prefixes'] + evidence['LoCoMo_selections_and_adapter_payloads'] == 2306
    assert evidence['selector_sha256'] == hashlib.sha256((root/'episodic/src/episodic/_timeline.py').read_bytes()).hexdigest()

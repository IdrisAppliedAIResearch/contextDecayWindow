"""Offline adoption gate. No inference or answer labels are consumed."""
from pathlib import Path
import gzip
import hashlib
import json
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / 'timeline_artifacts'
BASE = ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts'
PATHS = {
    'sources': ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs/sources.json',
    'curves': ROOT / 'experiments/probes/retrieval_score_curves/artifacts/curves.json',
    'blind': BASE / 'blind.json',
    'misses': BASE / 'post_review_reader/transformations.json',
    'preserved': BASE / 'prefix_106_reader/transformations.json',
    'locomo': ROOT / 'experiments/locomo_relevance_timeline/artifacts/selections.jsonl.gz',
    'adapter': ROOT / 'experiments/locomo_relevance_timeline/artifacts/adapter.jsonl.gz',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='utf8') as f:
            return [json.loads(line) for line in f]
    return json.loads(path.read_text(encoding='utf8'))


def distribution(values):
    return dict(zip(('min', 'p25', 'median', 'p75', 'max'),
                    np.percentile(values, [0, 25, 50, 75, 100]).tolist()))


def load():
    return {k: read(p) for k, p in PATHS.items()}


def save(name, value):
    OUT.mkdir(exist_ok=True)
    value['input_sha256'] = {k: sha(p.read_bytes()) for k, p in PATHS.items()}
    value['git_head'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    value['script_sha256'] = sha(Path(__file__).read_bytes())
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')


def explore():
    d = load()
    e = [r for r in d['blind'] if r['study'] == 'E']
    assert len(e) == 192 and len(d['locomo']) == 1986
    curves = {r['id']: r for r in d['curves'] if r['study'] == 'E'}
    for r in e:
        c = curves[r['id']]
        chosen = {k for k, s in zip(c['ids'], c['cosine']) if s >= .48} | set(r['anchors'])
        expected = [k for _, k in sorted(zip(c['turns'], c['ids'])) if k in chosen]
        assert expected == r['arms']['ANCHORED']['ids']
    for r in d['locomo']:
        assert r['cutoff'] is None
        assert [k for k, s in zip(r['ids'], r['scores']) if s >= .48] == r['selected']
    save('part1.json', {
        'status': 'PASS', 'E_count': len(e), 'LoCoMo_count': len(d['locomo']),
        'E_selected': distribution([len(r['arms']['ANCHORED']['ids']) for r in e]),
        'E_chars': distribution([len(r['arms']['ANCHORED']['context']) for r in e]),
        'LoCoMo_selected': distribution([len(r['selected']) for r in d['locomo']]),
        'LoCoMo_empty': sum(not r['selected'] for r in d['locomo']),
        'LoCoMo_full': sum(len(r['selected']) == len(r['ids']) for r in d['locomo']),
        'prefix_count': len(d['misses']) + len(d['preserved']),
        'identity': 'All raw cosine >=.48 records, plus explicit E anchors; no cap; original source order.',
        'feedback': 'None: output is not fed back into selection. Public store purity tested at activation.',
        'continuity': 'Historical rows disable continuity; default union is separately tested, not scored.',
        'model_calls': 0,
    })


def parity():
    from episodic._timeline import select_timeline
    from episodic._render import render_stm_payload
    assert read(OUT / 'part1.json')['status'] == 'PASS'
    d = load()
    histories = {r['id']: r['episodes'] for r in d['sources']}
    curves = {r['id']: r for r in d['curves'] if r['study'] == 'E'}
    blind = {r['id']: r for r in d['blind'] if r['study'] == 'E'}
    checked = []

    def check(r, expected, context, cutoff=None):
        episodes = histories[r['history']]
        c = curves[r['id']]
        assert [e['id'] for e in episodes] == c['ids']
        anchor = next((e['turn_number'] for e in episodes if e['id'] in r['anchors']), None)
        result = select_timeline(episodes, c['cosine'], recency_window_n=0,
                                 anchor_turn=anchor, through_turn=cutoff)
        actual = [episodes[i]['id'] for i in result.selected_indices]
        payload = render_stm_payload([], [episodes[i] for i in result.selected_indices])
        assert actual == expected and payload == context
        assert result == select_timeline(episodes, c['cosine'], recency_window_n=0,
                                         anchor_turn=anchor, through_turn=cutoff)
        checked.append([r['id'], cutoff, actual, sha(payload.encode())])

    for r in blind.values():
        check(r, r['arms']['ANCHORED']['ids'], r['arms']['ANCHORED']['context'])
    for row in d['misses'] + d['preserved']:
        check(blind[row['id']], row['kept'], row['context'], row['anchor'])
    adapters = {r['id']: r for r in d['adapter']}
    for row in d['locomo']:
        episodes = [dict(id=k, turn_number=i) for i, k in enumerate(row['ids'])]
        result = select_timeline(episodes, row['scores'], recency_window_n=0)
        actual = [episodes[i]['id'] for i in result.selected_indices]
        payload = '\n'.join(adapters[k]['element'] for k in actual)
        assert actual == row['selected'] and sha(payload.encode()) == row['block_sha256']
        checked.append([row['key'], None, actual, sha(payload.encode())])

    # Same count / wrong identity cannot pass the equality predicate.
    def matches(ids, payload, expected_ids, expected_sha):
        return ids == expected_ids and sha(payload.encode()) == expected_sha
    assert not matches(['wrong'], 'ok', ['right'], sha(b'ok'))
    assert not matches(['right'], 'changed', ['right'], sha(b'ok'))
    assert matches(['right'], 'ok', ['right'], sha(b'ok'))
    assert len(checked) == 2306
    save('parity.json', {'status': 'PASS', 'E_timelines': 192, 'E_prefixes': 128,
        'LoCoMo_selections_and_adapter_payloads': 1986, 'mismatches': 0,
        'trace_digest': sha(json.dumps(checked, separators=(',', ':')).encode()),
        'negative_identity_and_payload_controls': True, 'model_calls': 0,
        'scope': 'Continuity off; LoCoMo checks retained adapter payloads, not the public episode renderer.',
        'selector_sha256': sha((ROOT/'episodic/src/episodic/_timeline.py').read_bytes())})


if __name__ == '__main__':
    {'explore': explore, 'parity': parity}[sys.argv[1]]()

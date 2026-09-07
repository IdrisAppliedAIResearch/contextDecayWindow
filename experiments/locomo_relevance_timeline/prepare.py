"""Label-blind LoCoMo relevance timeline construction and reproduction gates."""
import ast
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from collections import Counter
from types import SimpleNamespace
from xml.sax.saxutils import escape, quoteattr

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
P = Path(__file__).resolve().parent
OUT = P / 'artifacts'
CONTROL = Path('C:/Users/muzaf/contextDecayWindow-locomo-timeline-control')
sys.path.insert(0, str(CONTROL / 'src'))
sys.path.insert(0, str(CONTROL / 'episodic/src'))
from analysis import lv009_exploration as prior
from analysis.hh001_prompt import render_reader_prompt
from episodic._render import render_stm_payload


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(value.encode('utf8')).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)


def committed(path):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    expected = subprocess.check_output(['git', 'show', 'HEAD:' + rel], cwd=ROOT)
    assert expected.replace(b'\r\n', b'\n') == Path(path).read_bytes().replace(b'\r\n', b'\n'), rel


def parser():
    path = CONTROL / 'experiments/study_D/temporal.py'
    tree = ast.parse(path.read_text(encoding='utf8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'temporal_order')
    env = {'re': re}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), env)
    return env['temporal_order']


route_query = parser()


def select(records, scores, question):
    assert len(records) == len(scores) and len({r['id'] for r in records}) == len(records)
    assert np.isfinite(scores).all()
    order = sorted(range(len(records)), key=lambda i: (-scores[i], records[i]['turn_number'], records[i]['id']))
    _, route = route_query(records, question, SimpleNamespace(order=order))
    anchors = route.get('anchors', []) if route['reason'] == 'anchored' else []
    chosen = {i for i, score in enumerate(scores) if score >= .48} | set(anchors)
    cutoff = None
    if anchors and re.search(r'\bbefore\b', question, re.I):
        assert len(anchors) == 1
        cutoff = records[anchors[0]]['turn_number']
        chosen = {i for i in chosen if records[i]['turn_number'] <= cutoff}
    chosen = sorted(chosen, key=lambda i: (records[i]['turn_number'], records[i]['id']))
    return chosen, route, cutoff


def fixtures():
    rs = [dict(id=str(i), turn_number=i, user_message=t) for i, t in enumerate([
        '"Atlas" moved.', 'The "Review" meeting happened.', '"Atlas" moved again.'])]
    assert select(rs, [.48, .479, .481], 'Where?')[0] == [0, 2]
    assert select(rs, [0, 0, 0], 'Where?')[0] == []
    assert select(rs, [1, 1, 1], 'Where?')[0] == [0, 1, 2]
    assert select(rs, [1, 0, 1], 'Where was "Atlas" before "Review"?')[0] == [0, 1]
    assert select(rs, [1, 0, 1], 'Where was "Atlas" after "Review"?')[0] == [0, 1, 2]
    assert select(rs, [0, 0, 0], 'Where was "Missing" before "Review"?')[1]['reason'] == 'missing_subject'
    ambiguous = rs + [dict(id='3', turn_number=3, user_message='The "Review" event.')]
    assert select(ambiguous, [0]*4, 'Where was "Atlas" before "Review"?')[1]['reason'] == 'ambiguous_or_missing_anchor'
    many = [dict(id=str(i), turn_number=i, user_message='x'*1000) for i in range(200)]
    assert len(select(many, [1]*200, 'Where?')[0]) == 200
    assert select(rs, [.48, .479, .481], 'Where?')[0] == [0, 2]
    try:
        prior.assert_no_label_fields({'answer': 'planted forbidden value'})
    except prior.LV009ExplorationError:
        pass
    else:
        raise AssertionError('label sentinel accepted')
    return {'boundary_empty_full_no_cap_anchor_routes_stateless': True, 'label_sentinel': True}


def e_replay():
    base = ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts'
    histories = {h['id']: h for h in read(ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs/sources.json')}
    blind = {r['id']: r for r in read(base/'blind.json') if r['study'] == 'E'}
    curves = {r['id']: r for r in read(ROOT/'experiments/probes/retrieval_score_curves/artifacts/curves.json') if r['study'] == 'E'}
    rows = read(base/'post_review_reader/transformations.json') + read(base/'prefix_106_reader/transformations.json')
    assert len(rows) == len({r['id'] for r in rows}) == 128
    for row in rows:
        b = blind[row['id']]
        records = histories[b['history']]['episodes']
        chosen, route, cutoff = select(records, curves[row['id']]['cosine'], b['query'])
        assert [records[i]['id'] for i in chosen] == row['kept']
        assert render_stm_payload([], [records[i] for i in chosen]) == row['context']
    return {'prefix_reproductions': 128, 'identity_and_payload': True}


def main():
    committed(__file__)
    committed(P/'IMPLEMENTATION_PLAN.md')
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=CONTROL, text=True).strip().startswith('87c8ab37')
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=CONTROL, text=True).strip()
    assert Path(prior.__file__).resolve().is_relative_to(CONTROL)
    checks = fixtures() | e_replay()
    cases = prior.load_blind_cases()
    # Cache binaries are intentionally untracked; use original immutable files.
    prior.DEV_CACHE = ROOT / prior.DEV_CACHE.relative_to(CONTROL)
    prior.HOLDOUT_CACHE = ROOT / prior.HOLDOUT_CACHE.relative_to(CONTROL)
    vectors, caches = prior.load_full_vectors(cases)
    raw = read(prior.DATASET_PATH)
    source = {r['sample_id']: r['conversation'] for r in raw}
    outputs, selections, adapters = [], [], []
    routes, categories = Counter(), Counter()
    extras = Counter()
    for case in cases:
        conv = source[case.sample_id]
        conv_hash = digest(json.dumps(conv, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
        records = [dict(id=p.identity, turn_number=i, user_message=p.text) for i, p in enumerate(case.pairs)]
        matrix = np.asarray([vectors[p.text] for p in case.pairs], dtype=np.float64)
        matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
        occurrences = Counter()
        elements = []
        for pair in case.pairs:
            date = str(conv.get(pair.session_id + '_date_time', ''))
            turns = {t['dia_id']: t for t in conv[pair.session_id]}
            members = [turns[k] for k in pair.dialog_ids]
            assert pair.text == '\n'.join(f"{t['speaker']}: {t['text']}" for t in members)
            extras.update(k for t in members for k in t if k not in {'speaker', 'text', 'dia_id'})
            element = f'<record session={quoteattr(pair.session_id)} date={quoteattr(date)} dialogue_ids={quoteattr(" ".join(pair.dialog_ids))}>\n{escape(pair.text)}\n</record>'
            elements.append(element)
            adapters.append(dict(id=pair.identity, conversation=case.sample_id, session=pair.session_id, date=date, dialogue_ids=pair.dialog_ids, text=pair.text, text_sha256=digest(pair.text), element=element))
        for q in case.questions:
            # Category stays in measurement metadata only, never select() or key.
            qhash = digest(conv_hash + '\0' + q.question)
            ordinal = occurrences[qhash]
            occurrences[qhash] += 1
            key = digest(qhash + '\0' + str(ordinal))
            v = np.asarray(vectors[q.question], dtype=np.float64)
            scores = matrix @ (v / np.linalg.norm(v))
            chosen, route, cutoff = select(records, scores, q.question)
            assert chosen == select(records, scores, q.question)[0]
            block = '\n'.join(elements[i] for i in chosen)
            prompt = render_reader_prompt(q.question, block)
            common = dict(key=key, historical_key=q.comparison_key, conversation=case.sample_id, source_index=q.source_index, ordinal=ordinal, question=q.question, category=q.category)
            outputs.append(dict(common, text=prompt, text_sha256=digest(prompt)))
            selections.append(dict(key=key, ids=[p.identity for p in case.pairs], scores=scores.tolist(), selected=[case.pairs[i].identity for i in chosen], route=route, cutoff=cutoff, block_sha256=digest(block)))
            routes[route['reason']] += 1
            categories[q.category] += 1
    assert len(outputs) == len({r['key'] for r in outputs}) == 1986
    assert categories == {1:282, 2:321, 3:96, 4:841, 5:446}
    outputs.sort(key=lambda r:r['key'])
    calibration = {r['key'] for case in cases for r in sorted([r for r in outputs if r['conversation']==case.sample_id], key=lambda r:r['key'])[:2]}
    outputs.sort(key=lambda r:(r['key'] not in calibration, r['key']))
    assert len(calibration)==20
    OUT.mkdir(exist_ok=True)
    prior._write_gzip_rows(OUT/'prompts.jsonl.gz', outputs)
    prior._write_gzip_rows(OUT/'selections.jsonl.gz', selections)
    prior._write_gzip_rows(OUT/'adapter.jsonl.gz', adapters)
    paths = [prior.DATASET_PATH, prior.DEV_CACHE, prior.HOLDOUT_CACHE, prior.DEV_VECTOR_MANIFEST, prior.HOLDOUT_VECTOR_MANIFEST, Path(prior.__file__), CONTROL/'experiments/study_D/temporal.py', CONTROL/'src/analysis/hh001_prompt.py', Path(__file__), P/'IMPLEMENTATION_PLAN.md']
    save(OUT/'part1.json', dict(status='PASS', checks=checks, population=1986, categories=dict(categories), routes=dict(routes), active_cutoffs=sum(r['cutoff'] is not None for r in selections), caches=caches, candidate_count=len(adapters), omitted_metadata_counts=dict(extras), selection_counts=sorted(len(r['selected']) for r in selections), prompt_chars=sorted(len(r['text']) for r in outputs), calibration=sorted(calibration), hashes={str(p):sha(p) for p in paths}, outputs={n:sha(OUT/n) for n in ['prompts.jsonl.gz','selections.jsonl.gz','adapter.jsonl.gz']}, llm_calls=0))
    print(json.dumps(dict(population=len(outputs), routes=dict(routes), min_selected=min(len(r['selected']) for r in selections), max_selected=max(len(r['selected']) for r in selections), max_chars=max(len(r['text']) for r in outputs), omitted=dict(extras))))


if __name__ == '__main__':
    main()

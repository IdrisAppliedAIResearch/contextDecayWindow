"""AF-PRE-001 Part 1a: sealed PURE/ORACLE replay and 17-anchor characterization.

Re-executes the sealed selector from temporal_da_fusion/relevance.py against the
sealed score curves and labels, reproduces the sealed summary by identity, and
characterizes the 17 before-question anchors that PURE drops. Writes only
exploration artifacts; seals nothing; reads no model.
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROBE = ROOT / 'experiments/probes/temporal_da_fusion'
CURVES = ROOT / 'experiments/probes/retrieval_score_curves/artifacts/curves.json'
INPUTS = ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs'
SEALED = PROBE / 'relevance_artifacts'
OUT = HERE / 'part1_artifacts'

sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(PROBE))
from relevance import select, THRESHOLD  # sealed selector, unmodified

BEFORE = ['straight', 'irrelevant', 'future', 'proposal']


def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def sha_candidates(p):
    # Identity seal: the gate-recorded hash must equal either the raw disk bytes
    # (sealed on this Windows checkout) or the committed blob (LF-normalized).
    import hashlib
    import subprocess
    rel = Path(p).resolve().relative_to(ROOT).as_posix()
    return {hashlib.sha256(Path(p).read_bytes()).hexdigest(),
            hashlib.sha256(subprocess.check_output(['git', 'show', f'HEAD:{rel}'], cwd=ROOT)).hexdigest()}


def main():
    gate = read(SEALED / 'gate.json')
    for path, want in gate['inputs'].items():
        p = Path(path)
        if not p.is_absolute(): p = ROOT / p
        assert want in sha_candidates(p), f'sealed input drifted: {path}'
    assert THRESHOLD == 0.48
    curves = [r for r in read(CURVES) if r['study'] == 'E']
    labels = read(INPUTS / 'labels.json')
    traces = {r['history']: r['trace'] for r in read(INPUTS / 'traces_sealed.json')}
    blind = {r['id']: r for r in read(SEALED / 'blind.json')}
    rows = [r for r in read(SEALED / 'diagnostic_rows.json') if r['study'] == 'E']
    assert len(curves) == 192
    findings = {'threshold': THRESHOLD, 'histories': [], 'before_rows': 0,
                'pure_complete': 0, 'anchored_complete': 0, 'misses': []}
    for c in curves:
        by = {i: (t, k) for k, i, t in zip(c['ids'], c['ids'], c['turns'])}
        assert len(set(c['ids'])) == len(c['ids'])
        anchors = blind[c['id']]['anchors']
        route_anchors = traces[c['history']]['prior']['route'].get('anchors', [])
        assert anchors == [c['ids'][i] for i in route_anchors]
        pure = select(c['ids'], c['turns'], c['cosine'])
        anchored = select(c['ids'], c['turns'], c['cosine'], anchors)
        gold = set(labels[c['id']]['gold_ids'])
        cosine = dict(zip(c['ids'], c['cosine']))
        for arm, chosen in (('PURE', pure), ('ANCHORED', anchored)):
            sealed = next(r for r in rows if r['id'] == c['id'] and r['arm'] == arm)
            assert sealed['complete'] == (bool(gold) and gold.issubset(set(chosen))), (c['id'], arm)
        if c['type'] in BEFORE:
            findings['before_rows'] += 1
            findings['pure_complete'] += gold.issubset(set(pure))
            findings['anchored_complete'] += gold.issubset(set(anchored))
            for a in anchors:
                if a not in set(pure):
                    meta = labels[c['id']]['rationale']
                    target_id = next(i for i, t in zip(c['ids'], c['turns']) if t == meta['target'])
                    findings['misses'].append(dict(id=c['id'], history=c['history'], type=c['type'],
                                                   anchor=a[:8], anchor_cosine=round(cosine[a], 4),
                                                   anchor_turn=by[a][0], target_turn=meta['target'],
                                                   target_cosine=round(cosine[target_id], 4),
                                                   later_turn=meta['later']))
        findings['histories'].append(dict(id=c['id'], type=c['type'], n=len(pure),
                                          anchor_exceptions=sum(a not in set(pure) for a in anchors)))
    assert findings['before_rows'] == 128
    summary = read(SEALED / 'summary.json')
    assert findings['pure_complete'] == summary['E/before/PURE']['complete'] == 111, findings
    assert findings['anchored_complete'] == summary['E/before/ANCHORED']['complete'] == 128, findings
    assert len(findings['misses']) == 17
    findings['miss_type_counts'] = dict(Counter(m['type'] for m in findings['misses']))
    findings['miss_anchor_turn_range'] = [min(m['anchor_turn'] for m in findings['misses']),
                                          max(m['anchor_turn'] for m in findings['misses'])]
    findings['miss_anchor_cosine_range'] = [min(m['anchor_cosine'] for m in findings['misses']),
                                            max(m['anchor_cosine'] for m in findings['misses'])]
    OUT.mkdir(exist_ok=True)
    (OUT / 'part1a_replay.json').write_text(json.dumps(findings, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in findings.items() if k not in ('histories', 'misses')}, indent=1))


if __name__ == '__main__':
    main()

"""AF-PRE-001 Part 1e: LoCoMo pool feasibility — deterministic anchor gold from evidence annotations.

Gold rule (registered): for a primary question (categories 1-4) with >=1
evidence dia_id, the anchor pair is the dialogue pair whose dia_id equals the
earliest evidence id; multi-evidence rule: any pair containing an evidence turn
counts. This script counts, per category, how many questions yield (a) exactly
one introducing pair, (b) evidence spread over multiple pairs, (c) zero
evidence. Items with zero evidence cannot define anchor gold and are excluded.
No models; no sealing.
"""
import json
import random
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'part1_artifacts'
DATASET = Path(r'C:\Users\muzaf\Downloads\locomo10.json')
SEED = 20260920
SAMPLE_N = 120


def main():
    data = json.loads(DATASET.read_text(encoding='utf-8'))
    stats = Counter()
    eligible = []
    for conv in data:
        sample_id = conv.get('sample_id', conv.get('conversation_id', 'unknown'))
        turns = {}
        for key, value in conv['conversation'].items():
            if key.startswith('session_') and isinstance(value, list):
                for t in value:
                    turns[t['dia_id']] = t
        for i, q in enumerate(conv['qa']):
            cat = str(q.get('category', '?'))
            if cat not in {'1', '2', '3', '4'}:
                stats[f'cat{cat}_excluded'] += 1
                continue
            ev = q.get('evidence') or []
            if not ev:
                stats[f'cat{cat}_no_evidence'] += 1
                continue
            missing = [e for e in ev if str(e) not in turns]
            if missing:
                stats[f'cat{cat}_evidence_not_in_dialogue'] += 1
                continue
            intro = sorted({str(e) for e in ev}, key=lambda e: (int(e.split(':')[0][1:]), int(e.split(':')[1])))
            stats[f'cat{cat}_evidence_turns_{min(len(intro), 5)}'] += 1
            eligible.append(dict(sample_id=sample_id, qid=f'{sample_id}:{i}', question=q['question'], cat=cat,
                                 evidence=intro, gold_anchor_earliest=intro[0],
                                 gold_anchor_latest=intro[-1], texts=len(intro)))
    stats['eligible_total'] = len(eligible)
    stats['multi_evidence'] = sum(r['texts'] > 1 for r in eligible)
    rng = random.Random(SEED)
    sample = rng.sample(eligible, SAMPLE_N) if len(eligible) >= SAMPLE_N else eligible
    stats['sample_taken'] = len(sample)
    stats['sample_by_cat'] = dict(Counter(r['cat'] for r in sample))
    stats['sample_by_conv'] = dict(Counter(r['sample_id'] for r in sample))
    stats['sample_earliest_ne_latest'] = sum(r['gold_anchor_earliest'] != r['gold_anchor_latest'] for r in sample)
    OUT.mkdir(exist_ok=True)
    (OUT / 'part1e_locomo_pool.json').write_text(json.dumps(
        dict(stats=dict(stats), seed=SEED, sample=sample), indent=2), encoding='utf-8')
    print(json.dumps(dict(stats), indent=1))


if __name__ == '__main__':
    main()

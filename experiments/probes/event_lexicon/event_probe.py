"""AF-PRE-002 Part 1: lexical event-marker probe. Rule and bars registered in
AF_PRE_002_PLAN.md (commit 5205a3f3) before this file ran anything.
Pure regex; no model loads; no LLM readers."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'experiments/probes/bert_anchor'))
import arms  # noqa: E402
from score_sample120 import wilson, mcnemar_exact  # noqa: E402

BERT_DIR = ROOT / 'experiments/probes/bert_anchor'
E_INPUTS = ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs'
OUT = HERE / 'artifacts'

FAMILIES = {
    'EVENT_NOUN': [
        'meetings?', 'wedding', 'engagement', 'trip', 'vacation', 'holiday', 'honeymoon',
        'party', 'concert', 'game', 'match', 'tournament', 'race', 'marathon', 'show',
        'performance', 'festival', 'ceremony', 'graduation', 'birthday', 'anniversary',
        'dinner', 'lunch', 'breakfast', 'picnic', 'interview', 'conference', 'workshop',
        'reunion', 'events?', 'visit', 'audition', 'exhibition', 'launch', 'opening',
        'premiere', 'move', 'surgery', 'class'],
    'TAKE_PLACE': ['took place', 'held at', 'occurred', 'happened', 'scheduled', 'hosted'],
    'MOTION': [
        'went', r'go(es|ing)?\b', 'gone', 'traveled', 'traveling', 'flew', r'fly\b',
        'drove', r'drive\b', 'rode', 'arrived', 'left', 'departed', 'off to', 'headed to',
        'visited', 'visiting', 'dropped by', 'stopped by'],
    'ATTEND': ['attended', 'attending', 'participated', 'participating', 'joined',
               'signed up', 'registered', 'enrolled'],
    'STATE_CHANGE': [
        'married', 'engaged', 'graduated', 'retired', 'hired', 'fired', 'adopted',
        'bought', 'sold', 'purchased', 'opened', 'closed', 'launched', 'started',
        'finished', 'completed', 'quit', 'resigned', 'promoted', 'moved', 'relocated',
        'welcomed', 'released', 'premiered', 'debuted', 'won', 'lost', 'founded', 'set up'],
    'ANNOUNCE': [
        'just got', 'just booked', 'just finished', 'just started', 'just bought',
        'just adopted', 'guess what', 'big news', 'excited to announce', "can't wait to share"],
    'TEMPORAL_SHIFT': [
        r'last (week|month|year|weekend|night|summer|spring|fall|winter|monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
        'ago', 'yesterday', 'the day before', 'back in', 'previously',
        r'a few (days|weeks|months) (back|ago)'],
}
COMPILED = {fam: [re.compile(r'\b(?:' + p + r')\b', re.IGNORECASE) for p in pats]
            for fam, pats in FAMILIES.items()}


def family_count(text):
    return sum(1 for fam, rxes in COMPILED.items() if any(r.search(text) for r in rxes))


def families_hit(text):
    return [fam for fam, rxes in COMPILED.items() if any(r.search(text) for r in rxes)]


def top1(scores, ids):
    best = max(scores)
    tie = [i for i, s in enumerate(scores) if s == best]

    def key(i):
        head = ids[i]
        if ':' in head and head.split(':')[0][1:].isdigit():
            return (0, int(head.split(':')[0][1:]), int(head.split(':')[1]))
        return (1, i, i)
    return ids[sorted(tie, key=key)[0]]


def s1_e_gaps():
    curves = [r for r in json.loads((ROOT / 'experiments/probes/retrieval_score_curves/artifacts/curves.json').read_text(encoding='utf-8'))
              if r['study'] == 'E' and r['type'] in ('straight', 'irrelevant', 'future', 'proposal')]
    blind = {r['id']: r for r in json.loads((ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json').read_text(encoding='utf-8'))}
    sources = {h['id']: h for h in json.loads((E_INPUTS / 'sources.json').read_text(encoding='utf-8'))}
    gaps = [c for c in curves if blind[c['id']]['arms']['PURE']['anchor_exceptions']]
    assert len(gaps) == 17
    hits, rows = 0, []
    for c in gaps:
        eps = sources[c['history']]['episodes']
        anchor = blind[c['id']]['arms']['ANCHORED']['anchor_exceptions'][0]
        texts = [e['user_message'] + '\n' + e['assistant_message'] for e in eps]
        ids = [e['id'] for e in eps]
        qnames = re.findall(r'"([^"]+)"', c['query'])
        cands = [(sum(1 for n in qnames if n in t), family_count(t), i)
                 for i, t in enumerate(texts) if family_count(t) >= 1]
        pred = None
        if cands:
            best = max(cands)[:2]
            tied = [i for m, fc, i in cands if (m, fc) == best]
            pred = ids[min(tied)]
        hits += int(pred == anchor)
        if pred != anchor:
            rows.append(dict(id=c['id'], pred=pred, anchor=anchor,
                             anchor_text=texts[ids.index(anchor)][:100]))
    return dict(gaps=17, recovered=hits, misses=rows)


def s2_s3():
    pool = json.loads((BERT_DIR / 'part1_artifacts/part1e_locomo_pool.json').read_text(encoding='utf-8'))['sample']
    convs = arms.load_conversations(r'C:\Users\muzaf\Downloads\locomo10.json')
    anchor_ev = anchor_n = non_ev = non_n = 0
    ev_only = hybrid = bm = 0
    fam_anchor = {f: 0 for f in FAMILIES}
    fam_non = {f: 0 for f in FAMILIES}
    cat = {}
    per_item = {}
    for cid in sorted({it['sample_id'] for it in pool}):
        turns = convs[cid]
        ids = [i for i, _ in turns]
        texts = [t for _, t in turns]
        fcs = [family_count(t) for t in texts]
        fams = [families_hit(t) for t in texts]
        bm25 = arms.BM25(texts)
        for it in [x for x in pool if x['sample_id'] == cid]:
            gi = ids.index(it['gold_anchor_earliest'])
            q = it['question']
            s_bm = bm25.score(q)
            s_hy = [s * (1 + fc) for s, fc in zip(s_bm, fcs)]
            p_bm, p_hy, p_ev = top1(s_bm, ids), top1(s_hy, ids), ids[max(range(len(fcs)), key=lambda i: (fcs[i], -i))]
            bm += int(p_bm == it['gold_anchor_earliest'])
            hybrid += int(p_hy == it['gold_anchor_earliest'])
            ev_only += int(p_ev == it['gold_anchor_earliest'])
            c = cat.setdefault(it['cat'], dict(n=0, bm=0, hy=0, anchor_ev=0))
            c['n'] += 1
            c['bm'] += int(p_bm == it['gold_anchor_earliest'])
            c['hy'] += int(p_hy == it['gold_anchor_earliest'])
            c['anchor_ev'] += int(fcs[gi] >= 1)
            per_item[it['qid']] = dict(bm=p_bm == it['gold_anchor_earliest'],
                                       hy=p_hy == it['gold_anchor_earliest'])
    # clean non-anchor event counting (single pass, correct)
    anchor_ev = anchor_n = non_ev = non_n = 0
    fam_anchor = {f: 0 for f in FAMILIES}
    fam_non = {f: 0 for f in FAMILIES}
    for cid in sorted({it['sample_id'] for it in pool}):
        turns = convs[cid]
        ids = [i for i, _ in turns]
        texts = [t for _, t in turns]
        fcs = [family_count(t) for t in texts]
        fams = [families_hit(t) for t in texts]
        golds = {ids.index(it['gold_anchor_earliest']) for it in pool if it['sample_id'] == cid}
        for i, fc in enumerate(fcs):
            if i in golds:
                anchor_n += 1
                anchor_ev += int(fc >= 1)
                for f in fams[i]:
                    fam_anchor[f] += 1
            else:
                non_n += 1
                non_ev += int(fc >= 1)
                for f in fams[i]:
                    fam_non[f] += 1
    a_rate, n_rate = anchor_ev / anchor_n, non_ev / non_n
    b_only = sum(1 for q in per_item if per_item[q]['hy'] and not per_item[q]['bm'])
    h_only = sum(1 for q in per_item if not per_item[q]['hy'] and per_item[q]['bm'])
    return dict(
        s2=dict(anchor_event_rate=round(a_rate, 4), nonanchor_event_rate=round(n_rate, 4),
                difference_pp=round(100 * (a_rate - n_rate), 1),
                anchor_n=anchor_n, per_family_anchor=fam_anchor, per_family_nonanchor=fam_non),
        s3=dict(bm25=bm, hybrid=hybrid, event_only=ev_only, n=len(pool),
                wilson_bm25=wilson(bm, len(pool)), wilson_hybrid=wilson(hybrid, len(pool)),
                net_hybrid_minus_bm25=b_only - h_only, ce_only=b_only, bm25_only=h_only,
                p=round(mcnemar_exact(b_only, h_only), 6)),
        per_category={str(k): v for k, v in sorted(cat.items())})


def main():
    OUT.mkdir(exist_ok=True)
    s1 = s1_e_gaps()
    rest = s2_s3()
    report = dict(s1=s1, **rest)
    (OUT / 'event_probe_results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()

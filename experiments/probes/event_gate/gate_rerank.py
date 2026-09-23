"""AF-PRE-004: event-gated retrieval. Registered in AF_PRE_004_PLAN.md (c4d3aa18).

Pool = BM25 top-20 union (event-regex family_count>=1 AND entity-in-turn), cap 30.
Rerank arms P1 zero-shot CE, P2 fine-tuned CE, P3 BM25-in-pool. Serial GPU, no readers.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (str(ROOT), str(ROOT / 'experiments/probes/bert_anchor'),
          str(ROOT / 'experiments/probes/event_lexicon'),
          str(ROOT / 'experiments/probes/ft_unified')):
    sys.path.insert(0, p)
import arms  # noqa: E402
import event_probe  # noqa: E402
from score_sample120 import wilson, mcnemar_exact  # noqa: E402

BERT_DIR = ROOT / 'experiments/probes/bert_anchor'
E_INPUTS = ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs'
FT_CKPT = ROOT / 'experiments/probes/ft_unified/artifacts/ckpt'
ART = HERE / 'artifacts'
LOCOMO = r'C:\Users\muzaf\Downloads\locomo10.json'
STOP = {'What', 'When', 'Where', 'Who', 'Whose', 'Which', 'How', 'Why', 'Does', 'Did',
        'Is', 'Are', 'Was', 'Were', "What's", "Who's", 'Their', 'His', 'Her'}


def entities(q):
    ents = set(re.findall(r'"([^"]+)"', q))
    for m in re.finditer(r'[A-Z][A-Za-z0-9.\-]*(?: [A-Z][A-Za-z0-9.\-]*)*', q):
        s = m.group(0)
        if s not in STOP and len(s) > 1:
            ents.add(s)
    return sorted(ents)


def pool_ids(query, texts, ids, bm25):
    s = bm25.score(query)
    A = sorted(range(len(texts)), key=lambda i: -s[i])[:20]
    ents = [e.lower() for e in entities(query)]
    E = [i for i, t in enumerate(texts)
         if event_probe.family_count(t) >= 1 and any(e in t.lower() for e in ents)][:30]
    P = sorted(set(A) | set(E))
    return P, len(E)


def main():
    ART.mkdir(exist_ok=True)
    import torch
    pool120 = json.load(open(BERT_DIR / 'part1_artifacts/part1e_locomo_pool.json', encoding='utf-8'))['sample']
    bm_ref = json.load(open(BERT_DIR / 'part1_artifacts/sample120_results.json', encoding='utf-8'))['per_item']['BM25']
    convs = arms.load_conversations(LOCOMO)
    srcs = {h['id']: h for h in json.load(open(E_INPUTS / 'sources.json', encoding='utf-8'))}
    blind = {r['id']: r for r in json.load(open(ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json', encoding='utf-8'))}
    gaps = [r for r in blind.values() if r['study'] == 'E' and r['type'] in ('straight', 'irrelevant', 'future', 'proposal')
            and r['arms']['PURE']['anchor_exceptions']]

    def e_texts(eps):
        return [e['user_message'] + '\n' + e['assistant_message'] for e in eps]

    work = []
    for cid in sorted({it['sample_id'] for it in pool120}):
        turns = convs[cid]
        ids = [i for i, _ in turns]
        texts = [t for _, t in turns]
        bm = arms.BM25(texts)
        for it in [x for x in pool120 if x['sample_id'] == cid]:
            P, nev = pool_ids(it['question'], texts, ids, bm)
            work.append(dict(key=it['qid'], q=it['question'], pool=P, ids=ids, texts=texts,
                             gold=it['gold_anchor_earliest'], nev=nev))
    for g in gaps:
        eps = srcs[g['history']]['episodes']
        texts, ids = e_texts(eps), [e['id'] for e in eps]
        bm = arms.BM25(texts)
        P, nev = pool_ids(g['query'], texts, ids, bm)
        work.append(dict(key='E:' + g['id'][:12], q=g['query'], pool=P, ids=ids, texts=texts,
                         gold=blind[g['id']]['arms']['ANCHORED']['anchor_exceptions'][0], nev=nev, is_e=True))

    def score_arm(name, scorer):
        res = {}
        for w in work:
            sub = [w['texts'][i] for i in w['pool']]
            sc = scorer(w['q'], sub)
            pred = w['ids'][w['pool'][max(range(len(sc)), key=lambda i: (sc[i], -i))]]
            res[w['key']] = pred == w['gold']
        return res

    out = {}
    # P3: BM25-in-pool (deterministic, no model)
    def p3_scorer_factory():
        def s(q, sub):
            bm = arms.BM25(sub)
            return bm.score(q)
        return s
    out['P3'] = score_arm('P3', p3_scorer_factory())

    tokn, model = arms.load_ce()
    out['P1'] = score_arm('P1', lambda q, sub: arms.ce_scores(tokn, model, q, sub))
    del model
    torch.cuda.empty_cache()

    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    ft_tok = AutoTokenizer.from_pretrained(FT_CKPT)
    ft_model = AutoModelForSequenceClassification.from_pretrained(FT_CKPT).to('cuda').eval()

    def ft_scorer(q, sub):
        outs = []
        with torch.no_grad():
            for a in range(0, len(sub), 256):
                ch = sub[a:a + 256]
                enc = ft_tok([q] * len(ch), ch, padding=True, truncation=True,
                             max_length=256, return_tensors='pt').to('cuda')
                outs += ft_model(**enc).logits[:, 0].tolist()
        return outs
    out['P2'] = score_arm('P2', ft_scorer)
    del ft_model
    torch.cuda.empty_cache()

    def summarize(res):
        e_k = sum(v for k, v in res.items() if k.startswith('E:'))
        s_items = {k: v for k, v in res.items() if not k.startswith('E:')}
        s_k = sum(s_items.values())
        bm_only = sum(1 for k in s_items if bm_ref[k] and not s_items[k])
        ft_only = sum(1 for k in s_items if s_items[k] and not bm_ref[k])
        return dict(event=f'{e_k}/17', sample=s_k, n_sample=120, wilson=wilson(s_k, 120),
                    net_vs_bm25=ft_only - bm_only, p=round(mcnemar_exact(ft_only, bm_only), 6))

    summary = {arm: summarize(res) for arm, res in out.items()}
    p1 = summary['P1']
    e_ok = p1['event'].startswith(('16', '17'))
    verdict = ('PASS-GATE' if e_ok and p1['net_vs_bm25'] >= 10 and p1['p'] < .05 else
               'CARRIES' if e_ok and p1['net_vs_bm25'] > 0 else 'DEAD')
    nev_stats = {w['key']: w['nev'] for w in work}
    report = dict(summary=summary, verdict=verdict,
                  pool_event_counts=dict(median_nev=sorted(nev_stats.values())[len(nev_stats) // 2],
                                         zero_nev=sum(1 for v in nev_stats.values() if v == 0),
                                         n=len(nev_stats)))
    (ART / 'gate_rerank_results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()

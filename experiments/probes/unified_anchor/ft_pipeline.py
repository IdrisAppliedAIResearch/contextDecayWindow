"""AF-PRE-005: pipeline-matched fine-tune + event gate. Plan: AF_PRE_005_PLAN.md (9018e653).

build: sample2.json (frozen first) then pool-matched pairs2.json; asserts disjoint.
train: frozen AF-PRE-003 config; only the task contract differs (select within pool).
eval:  E gaps + sample2 (+ sample-120 secondary); arms per plan. No LLM readers.
"""
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (str(ROOT), str(ROOT / 'experiments/probes/bert_anchor'),
          str(ROOT / 'experiments/probes/event_lexicon')):
    sys.path.insert(0, p)
import arms  # noqa: E402
import event_probe  # noqa: E402
from score_sample120 import wilson, mcnemar_exact  # noqa: E402

BERT_DIR = ROOT / 'experiments/probes/bert_anchor'
E_INPUTS = ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs'
ART = HERE / 'artifacts'
CKPT = ART / 'ckpt2'
LOCOMO = r'C:\Users\muzaf\Downloads\locomo10.json'
SEED = 20260920
SEED2 = 20260921
STOP = {'What', 'When', 'Where', 'Who', 'Whose', 'Which', 'How', 'Why', 'Does', 'Did',
        'Is', 'Are', 'Was', 'Were', "What's", "Who's", 'Their', 'His', 'Her'}


def entities(q):
    ents = set(re.findall(r'"([^"]+)"', q))
    for m in re.finditer(r'[A-Z][A-Za-z0-9.\-]*(?: [A-Z][A-Za-z0-9.\-]*)*', q):
        s = m.group(0)
        if s not in STOP and len(s) > 1:
            ents.add(s)
    return sorted(ents)


def pool_ids(query, texts, bm25):
    s = bm25.score(query)
    A = sorted(range(len(texts)), key=lambda i: -s[i])[:20]
    ents = [e.lower() for e in entities(query)]
    E = [i for i, t in enumerate(texts)
         if event_probe.family_count(t) >= 1 and any(e in t.lower() for e in ents)][:30]
    return sorted(set(A) | set(E)), s


def e_texts(eps):
    return [e['user_message'] + '\n' + e['assistant_message'] for e in eps]


def gap_items():
    blind = {r['id']: r for r in json.load(open(ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json', encoding='utf-8'))}
    return [r for r in blind.values() if r['study'] == 'E'
            and r['type'] in ('straight', 'irrelevant', 'future', 'proposal')
            and r['arms']['PURE']['anchor_exceptions']]


def eligible_all():
    raw = json.load(open(LOCOMO, encoding='utf-8'))
    convs = arms.load_conversations(LOCOMO)
    out = []
    for conv in raw:
        cid = conv['sample_id']
        ids = {i for i, _ in convs[cid]}
        for i, q in enumerate(conv['qa']):
            cat = str(q.get('category'))
            if cat not in {'1', '2', '3', '4'}:
                continue
            ev = [d for d in q.get('evidence', []) if d in ids]
            if not ev:
                continue
            gold = sorted(ev, key=lambda d: (int(d.split(':')[0][1:]), int(d.split(':')[1])))[0]
            out.append(dict(sample_id=cid, qid=f'{cid}:{i}', question=q['question'],
                            cat=cat, gold=gold))
    return out


def build():
    ART.mkdir(exist_ok=True)
    sample1 = {it['qid'] for it in json.load(open(BERT_DIR / 'part1_artifacts/part1e_locomo_pool.json', encoding='utf-8'))['sample']}
    elig = eligible_all()
    rest = [e for e in elig if e['qid'] not in sample1]
    rng = random.Random(SEED2)
    by_cat = {}
    for e in rest:
        by_cat.setdefault(e['cat'], []).append(e)
    quota = {}
    for cat, items in by_cat.items():
        quota[cat] = round(120 * len(items) / len(rest))
    while sum(quota.values()) != 120:
        cat = max(by_cat, key=lambda c: len(by_cat[c]) - quota[c] * len(rest) / 120)
        quota[cat] += 1 if sum(quota.values()) < 120 else -1
    sample2 = []
    for cat, k in sorted(quota.items()):
        poolc = sorted(by_cat[cat], key=lambda e: e['qid'])
        rng.shuffle(poolc)
        sample2 += poolc[:k]
    s2_ids = {e['qid'] for e in sample2}
    (ART / 'sample2.json').write_text(json.dumps(sample2, indent=1), encoding='utf-8')

    gaps = {g['id'] for g in gap_items()}
    train_pool = [e for e in elig if e['qid'] not in sample1 and e['qid'] not in s2_ids]
    convs = arms.load_conversations(LOCOMO)
    lc, lc_skip = [], 0
    for cid in sorted({e['sample_id'] for e in train_pool}):
        turns = convs[cid]
        ids = [i for i, _ in turns]
        texts = [t for _, t in turns]
        bm = arms.BM25(texts)
        for e in [x for x in train_pool if x['sample_id'] == cid]:
            P, s = pool_ids(e['question'], texts, bm)
            gi = ids.index(e['gold'])
            if gi not in P:
                lc_skip += 1
                continue
            negs = sorted([i for i in P if i != gi], key=lambda i: -s[i])[:6]
            lc.append(dict(qid=e['qid'], q=e['question'], pos=texts[gi],
                           negs=[texts[i] for i in negs]))
    srcs = {h['id']: h for h in json.load(open(E_INPUTS / 'sources.json', encoding='utf-8'))}
    curves = [c for c in json.load(open(ROOT / 'experiments/probes/retrieval_score_curves/artifacts/curves.json', encoding='utf-8'))
              if c['study'] == 'E']
    ec, ec_skip = [], 0
    for c in curves:
        if c['id'] in gaps:
            continue
        m = re.search(r'before "([^"]+)"', c['query'])
        if not m:
            ec_skip += 1
            continue
        eps = srcs[c['history']]['episodes']
        texts = e_texts(eps)
        hit = [i for i, t in enumerate(texts) if ('"' + m.group(1) + '"') in t and 'took place' in t.lower()]
        if len(hit) != 1:
            ec_skip += 1
            continue
        P, s = pool_ids(c['query'], texts, arms.BM25(texts))
        pos = hit[0]
        if pos not in P:
            ec_skip += 1
            continue
        negs = sorted([i for i in P if i != pos], key=lambda i: -s[i])[:6]
        ec.append(dict(qid='E:' + c['id'][:12], q=c['query'], pos=texts[pos],
                       negs=[texts[i] for i in negs]))
    rows_e = ec * 3
    tids = {r['qid'] for r in lc} | {r['qid'] for r in rows_e}
    assert not (tids & sample1) and not (tids & s2_ids), 'contamination'
    assert not (tids & {'E:' + g['id'][:12] for g in gap_items()}), 'gap contamination'
    (ART / 'pairs2.json').write_text(json.dumps(dict(e=rows_e, locomo=lc)), encoding='utf-8')
    print(dict(sample2=len(s2_ids), s2_by_cat={c: sum(1 for e in sample2 if e['cat'] == c) for c in sorted(quota)},
               lc_train=len(lc), lc_skip=lc_skip, e_train=len(ec), e_skip=ec_skip, e_rows=len(rows_e)))


def train():
    import torch
    from torch.utils.data import DataLoader, Dataset
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
    random.seed(SEED)
    torch.manual_seed(SEED)
    data = json.loads((ART / 'pairs2.json').read_text(encoding='utf-8'))
    rows = data['e'] + data['locomo']

    class DS:
        def __len__(self):
            return len(rows)

        def __getitem__(self, i):
            return rows[i]

    tokn = AutoTokenizer.from_pretrained(arms.CE_REPO, revision=arms.CE_REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(arms.CE_REPO, revision=arms.CE_REVISION).to('cuda')
    dl = DataLoader(DS(), batch_size=16, shuffle=True, collate_fn=lambda b: b)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01)
    steps = 3 * len(dl)
    sch = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    model.train()
    for ep in range(3):
        tot = 0.0
        for batch in dl:
            pairs, counts = [], []
            for row in batch:
                cand = [row['pos']] + row['negs']
                counts.append(len(cand))
                pairs += [(row['q'], c) for c in cand]
            enc = tokn([p[0] for p in pairs], [p[1] for p in pairs], padding=True,
                       truncation=True, max_length=256, return_tensors='pt').to('cuda')
            flat = model(**enc).logits[:, 0]
            k = max(counts)
            logits = flat.new_full((len(batch), k), float('-inf'))
            off = 0
            for bi, c in enumerate(counts):
                logits[bi, :c] = flat[off:off + c]
                off += c
            loss = torch.nn.functional.cross_entropy(logits, torch.zeros(len(batch), dtype=torch.long, device='cuda'))
            opt.zero_grad()
            loss.backward()
            opt.step()
            sch.step()
            tot += loss.item()
        print(f'epoch {ep} loss {tot / len(dl):.4f}', flush=True)
    CKPT.mkdir(exist_ok=True)
    model.save_pretrained(CKPT)
    tokn.save_pretrained(CKPT)
    print('saved', CKPT)


def evaluate():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    new_tok = AutoTokenizer.from_pretrained(CKPT)
    new_model = AutoModelForSequenceClassification.from_pretrained(CKPT).to('cuda').eval()
    zs_tok, zs_model = None, None

    def scores(model, tok, q, texts):
        outs = []
        with torch.no_grad():
            for a in range(0, len(texts), 256):
                ch = texts[a:a + 256]
                enc = tok([q] * len(ch), ch, padding=True, truncation=True,
                          max_length=256, return_tensors='pt').to('cuda')
                outs += model(**enc).logits[:, 0].tolist()
        return outs

    def top1(sc, sub_ids):
        best = max(sc)
        return sub_ids[sc.index(best)]

    def run_surface(items, arm):
        hits = {}
        for it in items:
            turns = convs[it['sample_id']]
            ids = [i for i, _ in turns]
            texts = [t for _, t in turns]
            bm = arms.BM25(texts)
            P, _ = pool_ids(it['question'], texts, bm)
            if arm == 'BM25':
                sc = bm.score(it['question'])
                pred = ids[max(range(len(sc)), key=lambda i: (sc[i], -i))]
            elif arm == 'gated_newFT':
                pred = top1(scores(new_model, new_tok, it['question'], [texts[i] for i in P]), [ids[i] for i in P])
            elif arm == 'ungated_newFT':
                pred = top1(scores(new_model, new_tok, it['question'], texts), ids)
            elif arm == 'gated_zsCE':
                nonlocal zs_tok, zs_model
                if zs_model is None:
                    zs_tok, zs_model = arms.load_ce()
                pred = top1(arms.ce_scores(zs_tok, zs_model, it['question'], [texts[i] for i in P]), [ids[i] for i in P])
            hits[it['qid']] = pred == it['gold']
        return hits

    raw2 = json.load(open(ART / 'sample2.json', encoding='utf-8'))
    sample2 = [dict(sample_id=e['sample_id'], qid=e['qid'], question=e['question'], gold=e['gold']) for e in raw2]
    pool120 = json.load(open(BERT_DIR / 'part1_artifacts/part1e_locomo_pool.json', encoding='utf-8'))['sample']
    sample1 = [dict(sample_id=it['sample_id'], qid=it['qid'], question=it['question'],
                    gold=it['gold_anchor_earliest']) for it in pool120]
    convs = arms.load_conversations(LOCOMO)
    srcs = {h['id']: h for h in json.load(open(E_INPUTS / 'sources.json', encoding='utf-8'))}
    blind = {r['id']: r for r in json.load(open(ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json', encoding='utf-8'))}
    e_items = []
    for g in gap_items():
        eps = srcs[g['history']]['episodes']
        e_items.append(dict(sample_id='E', qid='E:' + g['id'][:12], question=g['query'],
                            gold=blind[g['id']]['arms']['ANCHORED']['anchor_exceptions'][0],
                            _texts=e_texts(eps), _ids=[e['id'] for e in eps]))

    def run_e(arm):
        hits = 0
        for it in e_items:
            texts, ids = it['_texts'], it['_ids']
            bm = arms.BM25(texts)
            P, _ = pool_ids(it['question'], texts, bm)
            if arm == 'gated_newFT':
                pred = top1(scores(new_model, new_tok, it['question'], [texts[i] for i in P]), [ids[i] for i in P])
            else:
                pred = top1(scores(new_model, new_tok, it['question'], texts), ids)
            hits += int(pred == it['gold'])
        return hits

    def mcn(ref, arm):
        b = sum(1 for k in arm if arm[k] and not ref[k])
        c = sum(1 for k in arm if not arm[k] and ref[k])
        return b - c, mcnemar_exact(b, c)

    bm2 = run_surface(sample2, 'BM25')
    g2 = run_surface(sample2, 'gated_newFT')
    u2 = run_surface(sample2, 'ungated_newFT')
    z2 = run_surface(sample2, 'gated_zsCE')
    g1 = run_surface(sample1, 'gated_newFT')
    e_ok = run_e('gated_newFT')
    e_un = run_e('ungated_newFT')
    netg, pg = mcn(bm2, g2)
    netu, pu = mcn(bm2, u2)
    pass_bar = e_ok >= 15 and netg >= 10 and pg < .05
    verdict = 'PASS' if pass_bar else ('SIGNAL' if e_ok >= 15 and netg > 0 else 'DEAD')
    out = dict(
        sample2=dict(bm25=sum(bm2.values()), gated_newFT=sum(g2.values()), ungated_newFT=sum(u2.values()),
                     gated_zsCE=sum(z2.values()), n=120,
                     wilson_gated=wilson(sum(g2.values()), 120),
                     gated_net=netg, gated_p=round(pg, 6), ungated_net=netu, ungated_p=round(pu, 6)),
        sample1_secondary=dict(bm25=29, gated_newFT=sum(g1.values())),
        e_gaps=dict(gated_newFT=e_ok, ungated_newFT=e_un, n=17),
        verdict=verdict)
    (ART / 'results.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    {'build': build, 'train': train, 'eval': evaluate}[sys.argv[1]]()

"""AF-PRE-007: RLHF (surrogate-human feedback) vs RLCD (contrast pairs, Amendment 001).

Plan 4c865d3e + AMENDMENT_001_rlcd_fidelity.md (900ff9ef). Arms share RM recipe +
REINFORCE machinery; differ only in preference source. R = AF-PRE-005 ckpt2.
"""
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (str(ROOT), str(ROOT / 'experiments/probes/bert_anchor'),
          str(ROOT / 'experiments/probes/unified_anchor')):
    sys.path.insert(0, p)
import arms  # noqa: E402
import ft_pipeline  # noqa: E402
from score_sample120 import wilson, mcnemar_exact  # noqa: E402

ART = HERE / 'artifacts'
R_CKPT = ROOT / 'experiments/probes/unified_anchor/artifacts/ckpt2'
UA_ART = ROOT / 'experiments/probes/unified_anchor/artifacts'
BERT_DIR = ROOT / 'experiments/probes/bert_anchor'
LOCOMO = r'C:\Users\muzaf\Downloads\locomo10.json'
SEED = 20260920
NPREFS = 40
BATCH = 32
STEPS = 200
TOPK = 5
BETA = 0.1
PL = '\nWhich turn best answers the question above?'
ML = '\nWhich turn least answers the question above?'


def load_r():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(R_CKPT)
    model = AutoModelForSequenceClassification.from_pretrained(R_CKPT).to('cuda').eval()
    return model, tok, torch


def scores(model, tok, q, texts):
    import torch
    outs = []
    with torch.no_grad():
        for a in range(0, len(texts), 256):
            ch = texts[a:a + 256]
            enc = tok([q] * len(ch), ch, padding=True, truncation=True,
                      max_length=512, return_tensors='pt').to('cuda')
            outs += model(**enc).logits[:, 0].tolist()
    return outs


def train_items():
    s1 = {it['qid'] for it in json.load(open(BERT_DIR / 'part1_artifacts/part1e_locomo_pool.json', encoding='utf-8'))['sample']}
    s2 = {e['qid'] for e in json.load(open(UA_ART / 'sample2.json', encoding='utf-8'))}
    convs = arms.load_conversations(LOCOMO)
    out = []
    for e in ft_pipeline.eligible_all():
        if e['qid'] in s1 | s2:
            continue
        turns = convs[e['sample_id']]
        texts = [t for _, t in turns]
        ids = [i for i, _ in turns]
        P, _ = ft_pipeline.pool_ids(e['question'], texts, arms.BM25(texts))
        if e['gold'] not in {ids[i] for i in P}:
            continue
        out.append(dict(qid=e['qid'], question=e['question'], gold=e['gold'],
                        ids=ids, texts=texts, pool=P))
    return out


def dump():
    ART.mkdir(exist_ok=True)
    r_model, r_tok, _ = load_r()
    items = train_items()
    rows = []
    for it in items:
        s = scores(r_model, r_tok, it['question'], it['texts'])
        order = sorted(range(len(it['texts'])), key=lambda i: -s[i])
        rows.append(dict(qid=it['qid'], a=order[0], b=order[1],
                         gap=s[order[0]] - s[order[1]], ids=it['ids'], texts=it['texts'],
                         question=it['question']))
    rows.sort(key=lambda r: r['gap'])
    sel = rows[:NPREFS]
    rng = random.Random(SEED)
    locked, review = [], ['# AF-PRE-007 Arm H feedback: judge each pair (A or B). '
                          'Gold is hidden; order is randomized.\n']
    for r in sel:
        flip = rng.random() < .5
        ai, bi = (r['a'], r['b']) if not flip else (r['b'], r['a'])
        locked.append(dict(qid=r['qid'], gold=r['ids'][r['a']],
                           A=r['ids'][ai], B=r['ids'][bi]))
        rev = '\n'.join(r['texts'][max(0, ai - 1):ai])
        revb = '\n'.join(r['texts'][max(0, bi - 1):bi])
        review.append(f"\n## {r['qid']}\nQ: {r['question']}\n"
                      f"A: [preceding: {rev[-160:] if rev else '—'}] {r['texts'][ai]}\n"
                      f"B: [preceding: {revb[-160:] if revb else '—'}] {r['texts'][bi]}\n")
    (ART / 'pairs_locked.json').write_text(json.dumps(locked), encoding='utf-8')
    (ART / 'review.md').write_text('\n'.join(review), encoding='utf-8')
    print(dict(pairs=len(sel), min_gap=round(sel[0]['gap'], 3), max_gap=round(sel[-1]['gap'], 3)))


def build_c():
    ART.mkdir(exist_ok=True)
    r_model, r_tok, _ = load_r()
    pairs = []
    for it in train_items():
        sp = scores(r_model, r_tok, it['question'] + PL, it['texts'])
        sm = scores(r_model, r_tok, it['question'] + ML, it['texts'])
        c, rj = max(range(len(sp)), key=lambda i: sp[i]), max(range(len(sm)), key=lambda i: sm[i])
        if c != rj:
            pairs.append(dict(qid=it['qid'], q=it['question'],
                              chosen=it['texts'][c], rejected=it['texts'][rj],
                              gold=it['gold'], cid=it['ids'][c], rid=it['ids'][rj]))
    (ART / 'rlcd_pairs.json').write_text(json.dumps(pairs), encoding='utf-8')
    gold_ch = sum(1 for p in pairs if p['cid'] == p['gold'])
    print(dict(pairs=len(pairs), chosen_is_gold=f'{gold_ch}/{len(pairs)}'))


def train_prefmodel(pairs, name):
    import torch
    model, tok, _ = load_r()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-5)
    rng = random.Random(SEED)
    for ep in range(3):
        rng.shuffle(pairs)
        tot = 0.0
        for p in pairs:
            enc = tok([p['q']] * 2, [p['chosen'], p['rejected']], padding=True,
                      truncation=True, max_length=512, return_tensors='pt').to('cuda')
            s = model(**enc).logits[:, 0]
            loss = -torch.nn.functional.logsigmoid(s[0] - s[1])
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item()
        print(f'{name} pm epoch {ep} loss {tot / len(pairs):.4f}', flush=True)
    model.eval()
    return model


def reinforce(rm, name):
    import torch
    from torch import nn
    pol, tok, _t = load_r()
    ref, _t2, _t3 = load_r()
    for p_ in ref.parameters():
        p_.requires_grad_(False)
    opt = torch.optim.AdamW(pol.parameters(), lr=1e-5)
    items = train_items()
    rng = random.Random(SEED)
    _t.manual_seed(SEED)
    for st in range(STEPS):
        opt.zero_grad()
        batch = rng.sample(items, BATCH)
        tot = 0.0
        for it in batch:
            P = it['pool']
            ptexts = [it['texts'][i] for i in P]
            lg = pol(**tok([it['question']] * len(P), ptexts, padding=True,
                           truncation=True, max_length=512, return_tensors='pt').to('cuda')).logits[:, 0]
            k = min(TOPK, len(P))
            topv, topi = torch.topk(lg, k)
            probs = torch.softmax(topv, dim=0)
            with torch.no_grad():
                rl = rm(**tok([it['question']] * k, [ptexts[i] for i in topi], padding=True,
                              truncation=True, max_length=512, return_tensors='pt').to('cuda')).logits[:, 0]
                adv = (rl - rl.mean()) / (rl.std() + 1e-6)
                rlg = ref(**tok([it['question']] * k, [ptexts[i] for i in topi], padding=True,
                                truncation=True, max_length=512, return_tensors='pt').to('cuda')).logits[:, 0]
            a = torch.multinomial(probs, 1)
            kl = (probs * (torch.log_softmax(topv, 0) - torch.log_softmax(rlg, 0))).sum()
            tot = tot - torch.log(probs[a]) * adv[a].detach() + BETA * kl
        (tot / len(batch)).backward()
        opt.step()
        if st % 25 == 0:
            print(f'{name} step {st} obj {float(tot / len(batch)):.4f}', flush=True)
    out = ART / name
    out.mkdir(exist_ok=True)
    pol.save_pretrained(out)
    tok.save_pretrained(out)
    print('saved', out)


def eval_all():
    ART.mkdir(exist_ok=True)
    r_model, r_tok, _ = load_r()

    def load_ck(path):
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        m = AutoModelForSequenceClassification.from_pretrained(path).to('cuda').eval()
        return m, AutoTokenizer.from_pretrained(path)

    arms_by = {'R': (r_model, r_tok)}
    for nm in ('ckptH', 'ckptC'):
        if (ART / nm).exists():
            arms_by[nm] = load_ck(ART / nm)
    convs = arms.load_conversations(LOCOMO)
    pool120 = json.load(open(UA_ART / 'sample2.json', encoding='utf-8'))
    hits = {nm: {'u': {}, 'g': {}} for nm in arms_by}
    for it in pool120:
        turns = convs[it['sample_id']]
        ids = [i for i, _ in turns]
        texts = [t for _, t in turns]
        P, _ = ft_pipeline.pool_ids(it['question'], texts, arms.BM25(texts))
        for nm, (m, tk) in arms_by.items():
            s = scores(m, tk, it['question'], texts)
            hits[nm]['u'][it['qid']] = ids[max(range(len(s)), key=lambda i: s[i])] == it['gold']
            sg = scores(m, tk, it['question'], [texts[i] for i in P])
            hits[nm]['g'][it['qid']] = [ids[i] for i in P][max(range(len(sg)), key=lambda i: sg[i])] == it['gold']

    e_items = ft_pipeline.gap_items()
    srcs = {h['id']: h for h in json.load(open(ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs/sources.json', encoding='utf-8'))}
    blind = {r['id']: r for r in json.load(open(ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json', encoding='utf-8'))}
    e_hits = {}
    for nm, (m, tk) in arms_by.items():
        eg = eu = 0
        for g in e_items:
            eps = srcs[g['history']]['episodes']
            texts = [e['user_message'] + '\n' + e['assistant_message'] for e in eps]
            ids = [e['id'] for e in eps]
            gold = blind[g['id']]['arms']['ANCHORED']['anchor_exceptions'][0]
            P, _ = ft_pipeline.pool_ids(g['query'], texts, arms.BM25(texts))
            sg = scores(m, tk, g['query'], [texts[i] for i in P])
            eg += int([ids[i] for i in P][max(range(len(sg)), key=lambda i: sg[i])] == gold)
            su = scores(m, tk, g['query'], texts)
            eu += int(ids[max(range(len(su)), key=lambda i: su[i])] == gold)
        e_hits[nm] = dict(gated=eg, ungated=eu, n=17)

    ref_u = hits['R']['u']
    out = dict(sample2={}, e_gaps=e_hits)
    for nm in arms_by:
        b = sum(1 for k in ref_u if hits[nm]['u'][k] and not ref_u[k])
        c = sum(1 for k in ref_u if not hits[nm]['u'][k] and ref_u[k])
        net = b - c
        pval = mcnemar_exact(b, c) if nm != 'R' else 1.0
        eu = sum(hits[nm]['u'].values())
        verdict = None if nm == 'R' else (
            'PASS' if net >= 5 and pval < .05 and e_hits[nm]['gated'] == 17 and e_hits[nm]['ungated'] == 17 else
            'SIGNAL' if net > 0 and e_hits[nm]['gated'] == 17 and e_hits[nm]['ungated'] == 17 else 'DEAD')
        out['sample2'][nm] = dict(ungated=eu, gated=sum(hits[nm]['g'].values()), n=120,
                                  wins=b, losses=c, net=net, p=round(pval, 6),
                                  wilson=wilson(eu, 120), verdict=verdict)
    (ART / 'results.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'dump':
        dump()
    elif cmd == 'build_c':
        build_c()
    elif cmd == 'train_h':
        import pickle
        locked = json.load(open(ART / 'pairs_locked.json', encoding='utf-8'))
        labels = json.load(open(ART / 'rl_labels.json', encoding='utf-8'))
        items = {it['qid']: it for it in train_items()}
        pairs = []
        for lc in locked:
            lab = labels[lc['qid']]
            cand = 'chosen' if lab == 'A' else 'rejected'
            pick = lc['A'] if lab == 'A' else lc['B']
            other = lc['B'] if lab == 'A' else lc['A']
            it = items[lc['qid']]
            pairs.append(dict(qid=lc['qid'], q=it['question'],
                              chosen=it['texts'][it['ids'].index(pick)],
                              rejected=it['texts'][it['ids'].index(other)],
                              gold=lc['gold'], cid=pick))
        gold_agree = sum(1 for p in pairs if p['cid'] == p['gold'])
        (ART / 'human_pairs.json').write_text(json.dumps(
            dict(pairs=pairs, gold_agreement=f'{gold_agree}/{len(pairs)}'), indent=2), encoding='utf-8')
        print('surrogate label gold-agreement:', gold_agree, '/', len(pairs))
        rm = train_prefmodel(pairs, 'H')
        reinforce(rm, 'ckptH')
    elif cmd == 'train_c':
        pairs = json.load(open(ART / 'rlcd_pairs.json', encoding='utf-8'))
        rm = train_prefmodel(pairs, 'C')
        reinforce(rm, 'ckptC')
    elif cmd == 'eval':
        eval_all()

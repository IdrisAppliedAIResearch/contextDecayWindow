"""AF-PRE-003: unified fine-tuned cross-encoder (user's proposal under test).

Registered in AF_PRE_003_PLAN.md (commit 3ec83128) before this file scored anything.
build: pairs from E event anchors (x4) + LoCoMo answer turns; eval items excluded.
train: frozen config, pinned MiniLM CE, pairwise CE loss, final checkpoint.
eval:  17 E gaps + sample-120 vs registered bars. No LLM readers. GPU-serial.
"""
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments/probes/bert_anchor'))
import arms  # noqa: E402
from score_sample120 import wilson, mcnemar_exact  # noqa: E402

BERT_DIR = ROOT / 'experiments/probes/bert_anchor'
E_INPUTS = ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs'
ART = HERE / 'artifacts'
CKPT = ART / 'ckpt'
SEED = 20260920
LOCOMO = r'C:\Users\muzaf\Downloads\locomo10.json'


def e_texts(eps):
    return [e['user_message'] + '\n' + e['assistant_message'] for e in eps]


def gap_items():
    blind = json.load(open(ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json', encoding='utf-8'))
    return [r for r in blind if r['study'] == 'E'
            and r['type'] in ('straight', 'irrelevant', 'future', 'proposal')
            and r['arms']['PURE']['anchor_exceptions']]


def top1(scores, ids):
    best = max(scores)
    tie = [i for i, s in enumerate(scores) if s == best]

    def key(i):
        head = ids[i]
        if ':' in head and head.split(':')[0][1:].isdigit():
            return (0, int(head.split(':')[0][1:]), int(head.split(':')[1]))
        return (1, i, i)
    return ids[sorted(tie, key=key)[0]]


def build():
    ART.mkdir(exist_ok=True)
    srcs = {h['id']: h for h in json.load(open(E_INPUTS / 'sources.json', encoding='utf-8'))}
    curves = [c for c in json.load(open(ROOT / 'experiments/probes/retrieval_score_curves/artifacts/curves.json', encoding='utf-8'))
              if c['study'] == 'E']
    gaps = {g['id'] for g in gap_items()}
    e_pairs, e_skipped = [], 0
    for c in curves:
        if c['id'] in gaps:
            continue
        m = re.search(r'before "([^"]+)"', c['query'])
        if not m:
            e_skipped += 1
            continue
        eps = srcs[c['history']]['episodes']
        texts = e_texts(eps)
        hit = [i for i, t in enumerate(texts)
               if ('"' + m.group(1) + '"') in t and 'took place' in t.lower()]
        if len(hit) != 1:
            e_skipped += 1
            continue
        pos = hit[0]
        bm = arms.BM25(texts).score(c['query'])
        negs = [i for i in sorted(range(len(texts)), key=lambda i: -bm[i]) if i != pos][:3]
        e_pairs.append(dict(qid='E:' + c['id'][:12], q=c['query'],
                            pos=texts[pos], negs=[texts[i] for i in negs]))
    e_rows = e_pairs * 4

    raw = json.load(open(LOCOMO, encoding='utf-8'))
    sample = json.load(open(BERT_DIR / 'part1_artifacts/part1e_locomo_pool.json', encoding='utf-8'))['sample']
    sample_qids = {it['qid'] for it in sample}
    convs = arms.load_conversations(LOCOMO)
    lc_pairs = []
    for conv in raw:
        cid = conv['sample_id']
        turns = convs[cid]
        ids = [i for i, _ in turns]
        texts = [t for _, t in turns]
        bm25 = arms.BM25(texts)
        for i, q in enumerate(conv['qa']):
            qid = f'{cid}:{i}'
            if str(q.get('category')) not in {'1', '2', '3', '4'} or qid in sample_qids:
                continue
            ev = [d for d in q.get('evidence', []) if d in ids]
            if not ev:
                continue
            gold = sorted(ev, key=lambda d: (int(d.split(':')[0][1:]), int(d.split(':')[1])))[0]
            s = bm25.score(q['question'])
            negs = [j for j in sorted(range(len(texts)), key=lambda j: -s[j]) if ids[j] != gold][:3]
            qt = set(arms.tok(q['question']))
            used = {gold} | {ids[j] for j in negs}
            echo = max((j for j in range(len(texts)) if ids[j] not in used),
                       key=lambda j: len(qt & set(arms.tok(texts[j]))), default=None)
            if echo is not None and len(qt & set(arms.tok(texts[echo]))) > 0:
                negs = negs[:3] + [echo]
            lc_pairs.append(dict(qid=qid, q=q['question'],
                                 pos=texts[ids.index(gold)], negs=[texts[j] for j in negs[:4]]))
    train_ids = {p['qid'] for p in e_rows} | {p['qid'] for p in lc_pairs}
    gap_pref = {'E:' + g['id'][:12] for g in gap_items()}
    assert not (train_ids & sample_qids), 'contamination: sample qid in training'
    assert not (train_ids & gap_pref), 'contamination: E gap in training'
    (ART / 'pairs.json').write_text(json.dumps(dict(e=e_rows, locomo=lc_pairs)), encoding='utf-8')
    print(dict(e_unique=len(e_pairs), e_rows=len(e_rows), e_skipped=e_skipped,
               locomo=len(lc_pairs), excluded=len(sample_qids) + len(gaps)))


def train():
    import torch
    from torch.utils.data import DataLoader, Dataset
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

    random.seed(SEED)
    torch.manual_seed(SEED)
    data = json.loads((ART / 'pairs.json').read_text(encoding='utf-8'))
    rows = data['e'] + data['locomo']

    class PairDS(Dataset):
        def __len__(self):
            return len(rows)

        def __getitem__(self, i):
            return rows[i]

    tokn = AutoTokenizer.from_pretrained(arms.CE_REPO, revision=arms.CE_REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(arms.CE_REPO, revision=arms.CE_REVISION)
    dev = 'cuda'
    model.to(dev)
    dl = DataLoader(PairDS(), batch_size=16, shuffle=True, collate_fn=lambda b: b)
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
                       truncation=True, max_length=256, return_tensors='pt').to(dev)
            flat = model(**enc).logits[:, 0]
            k = max(counts)
            logits = flat.new_full((len(batch), k), float('-inf'))
            off = 0
            for bi, c in enumerate(counts):
                logits[bi, :c] = flat[off:off + c]
                off += c
            loss = torch.nn.functional.cross_entropy(
                logits, torch.zeros(len(batch), dtype=torch.long, device=dev))
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

    tokn = AutoTokenizer.from_pretrained(CKPT)
    model = AutoModelForSequenceClassification.from_pretrained(CKPT).to('cuda').eval()

    def ce(text_q, texts):
        outs = []
        with torch.no_grad():
            for a in range(0, len(texts), 256):
                chunk = texts[a:a + 256]
                enc = tokn([text_q] * len(chunk), chunk, padding=True, truncation=True,
                           max_length=256, return_tensors='pt').to('cuda')
                outs += model(**enc).logits[:, 0].tolist()
        return outs

    srcs = {h['id']: h for h in json.load(open(E_INPUTS / 'sources.json', encoding='utf-8'))}
    blind = json.load(open(ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json', encoding='utf-8'))
    blind = {r['id']: r for r in blind if r['study'] == 'E'}
    ev_e = 0
    e_rows = []
    for g in gap_items():
        eps = srcs[g['history']]['episodes']
        anchor = blind[g['id']]['arms']['ANCHORED']['anchor_exceptions'][0]
        texts, ids = e_texts(eps), [e['id'] for e in eps]
        pred = top1(ce(g['query'], texts), ids)
        ev_e += int(pred == anchor)
        e_rows.append(dict(id=g['id'], hit=pred == anchor))

    pool = json.load(open(BERT_DIR / 'part1_artifacts/part1e_locomo_pool.json', encoding='utf-8'))['sample']
    prev = json.load(open(BERT_DIR / 'part1_artifacts/sample120_results.json', encoding='utf-8'))
    bm_hits = prev['per_item']['BM25']
    convs = arms.load_conversations(LOCOMO)
    n = 0
    ev_s = 0
    per_item = {}
    cat = {}
    for cid in sorted({it['sample_id'] for it in pool}):
        turns = convs[cid]
        ids = [i for i, _ in turns]
        texts = [t for _, t in turns]
        for it in [x for x in pool if x['sample_id'] == cid]:
            pred = top1(ce(it['question'], texts), ids)
            hit = pred == it['gold_anchor_earliest']
            ev_s += int(hit)
            n += 1
            per_item[it['qid']] = hit
            c = cat.setdefault(it['cat'], dict(n=0, ft=0, bm=0))
            c['n'] += 1
            c['ft'] += int(hit)
            c['bm'] += int(bm_hits[it['qid']])
    ft_only = sum(1 for q in per_item if per_item[q] and not bm_hits[q])
    bm_only = sum(1 for q in per_item if not per_item[q] and bm_hits[q])
    p = mcnemar_exact(ft_only, bm_only)
    pass_event = ev_e >= 15
    pass_answer = ev_s >= 29 and (ft_only - bm_only) >= 0
    strong = pass_event and (ft_only - bm_only) >= 10 and p < .05
    verdict = ('STRONG' if strong else
               'CONSOLIDATION_WINS' if (pass_event and pass_answer) else
               'INTERFERENCE' if (pass_event != pass_answer) else 'FAIL')
    out = dict(e_gaps=dict(top1=ev_e, n=17, rows=e_rows),
               sample120=dict(ft=ev_s, bm25_reference=sum(bm_hits.values()), n=n,
                              wilson_ft=wilson(ev_s, n), ft_only=ft_only, bm25_only=bm_only,
                              net=ft_only - bm_only, p=round(p, 6)),
               per_category=cat,
               bars=dict(pass_event=pass_event, pass_answer=pass_answer, strong=strong),
               verdict=verdict)
    (ART / 'ft_ce_results.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    {'build': build, 'train': train, 'eval': evaluate}[sys.argv[1]]()

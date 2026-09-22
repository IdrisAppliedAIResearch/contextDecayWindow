"""AF-READ-002: chronological anchor builder under fixed budgets.

Plan f75f590d-lineage: AF_READ_002_PLAN.md (locked) + AMENDMENT_001 (ring unit =
deployed adapter element). Arms: B_ANCHOR8K (window around gate-selected seed,
<=8k chars), C_ANCHOR8K_CC80 (that block + legacy CC80 pack <=8k, merged
chronological <=16k); A_DEPLOYED reused byte-identically from AF-READ-001.

build   GPU/offline: seeds, windows, CC80 via episodic library, contexts (gold-free)
pilot   server: calibration + 10x2 readers + estimate
full    server: 120x2 readers, committed before gold opens
judge   PF-J reuse validation, then blind 3-pass judge of B/C
score   offline: reuse A votes, McNemar, disposition
status  offline: counts
"""
import json
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import af_read001 as R  # noqa: E402

from analysis.hh001_prompt import render_reader_prompt, render_judge_prompt, blinded_surface  # noqa: E402
from episodic._config import EpisodicConfig  # noqa: E402
from episodic._retrieval import retrieve_long_term  # noqa: E402
from score_sample120 import mcnemar_exact  # noqa: E402

OUT = HERE / 'artifacts' / 'af_read002'
AF1 = HERE / 'artifacts'
CAP_B = CAP_CC80 = 8000
CAP_C_TOTAL = 16000
CACHE_DBs = ('experiments/external/locomo/artifacts/locomo_dev_embeddings.db',
             'experiments/components/biological_memory/nf_004/artifacts/nf004_holdout_embeddings.db')
ARMS = ('B_ANCHOR8K', 'C_ANCHOR8K_CC80')
ROOT = R.ROOT


def vector_cache():
    vecs = {}
    for rel in CACHE_DBs:
        con = sqlite3.connect(str(ROOT / rel))
        for text, blob in con.execute('select text, embedding from cache'):
            vecs.setdefault(text, bytes(blob))
    return vecs


def load_world():
    af1 = R.load(AF1 / 'contexts.json')
    prim = [i for i in af1['items'] if i['kind'] == 'primary']
    prompts = {(r['conversation'], r['source_index']): r
               for r in R.rows_gz(R.T_LRT / 'prompts.jsonl.gz')}
    sels = {r['key']: r for r in R.rows_gz(R.T_LRT / 'selections.jsonl.gz')}
    byconv = {}
    for r in R.rows_gz(R.T_LRT / 'adapter.jsonl.gz'):
        byconv.setdefault(r['conversation'], []).append(r)
    srcs = {c['sample_id']: c for c in json.load(open(R.LOCOMO, encoding='utf-8'))}
    return af1, prim, prompts, sels, byconv, srcs


def seed_bm25(question, srcs, cid, turn_ids):
    texts = []
    for k, v in srcs[cid]['conversation'].items():
        if k.startswith('session_') and isinstance(v, list):
            texts += [t['text'] for t in v]
    import arms
    sc = R.arms.BM25(texts).score(question)
    bi = max(range(len(sc)), key=lambda i: (sc[i], -i))
    return turn_ids[bi]


def grow_window(elements, seed_idx, cap):
    lo = hi = seed_idx
    grow_hi = grow_lo = True
    join = lambda a, b: '\n'.join(e['element'] for e in elements[a:b + 1])
    while grow_hi or grow_lo:
        moved = False
        if grow_hi and hi + 1 < len(elements) and len(join(lo, hi + 1)) <= cap:
            hi += 1
            moved = True
        elif grow_hi:
            grow_hi = False
        if grow_lo and lo - 1 >= 0 and len(join(lo - 1, hi)) <= cap:
            lo -= 1
            moved = True
        elif grow_lo:
            grow_lo = False
        if not moved:
            break
    return lo, hi


def cc80_select(eps, question, qvec, cfg):
    return retrieve_long_term(episodes=eps, query_text=question,
                              query_embedding=qvec, budget=CAP_CC80, config=cfg)


def build():
    af1, prim, prompts, sels, byconv, srcs = load_world()
    vecs = vector_cache()
    import af_ft001 as F
    tokn, model, _tau = F._loader('V2', 20261011)
    cfg = EpisodicConfig(read_policy='legacy_cc80', recency_window_n=0)
    items = []
    for it in prim:
        cid, sidx = it['qid'].split(':')[0], int(it['qid'].split(':')[1])
        qa = srcs[cid]['qa'][sidx]
        q = qa['question']
        prow = prompts[(cid, sidx)]
        sel = sels[prow['key']]
        els = byconv[cid]
        assert sel['ids'] == [e['id'] for e in els], f'PF2 ids drift {it["qid"]}'
        turn_ids = [t['dia_id'] for k, v in srcs[cid]['conversation'].items()
                    if k.startswith('session_') and isinstance(v, list) for t in v]
        if it['gate'] == 'anchor':
            seed_turn, seed_src = it['anchor_turn'], 'v2'
        else:
            seed_turn, seed_src = seed_bm25(q, srcs, cid, turn_ids), 'bm25'
        hits = [j for j, e in enumerate(els) if seed_turn in e['dialogue_ids']]
        assert len(hits) == 1, f'seed element ambiguity {it["qid"]}'
        lo, hi = grow_window(els, hits[0], CAP_B)
        block_b = '\n'.join(e['element'] for e in els[lo:hi + 1])
        assert len(block_b) <= CAP_B and block_b
        eps = [dict(id=e['id'], turn_number=j, user_message=e['text'],
                    assistant_message='', searchable_text=e['text'],
                    embedding=vecs[e['text']])
               for j, e in enumerate(els)]
        assert q in vecs, f'query vector missing {it["qid"]}'
        alloc = cc80_select(eps, q, vecs[q], cfg)
        replay = cc80_select(eps, q, vecs[q], cfg)
        assert alloc.selected_ids == replay.selected_ids, f'CC80 not deterministic {it["qid"]}'
        rank_pos = {els[idx]['id']: r for r, idx in enumerate(alloc.ranking.order)}
        cc80_ids = [i for i in alloc.selected_ids]
        anchor_ids = [e['id'] for e in els[lo:hi + 1]]
        anchor_ids = [e['id'] for e in els[lo:hi + 1]]
        chosen = set(anchor_ids) | set(cc80_ids)
        removable = [i for i in cc80_ids if i not in anchor_ids]
        dropped = 0
        block_c = '\n'.join(e['element'] for e in els if e['id'] in chosen)
        while len(block_c) > CAP_C_TOTAL and removable:
            worst = max(removable, key=lambda i: rank_pos[i])
            removable.remove(worst)
            chosen.discard(worst)
            dropped += 1
            block_c = '\n'.join(e['element'] for e in els if e['id'] in chosen)
        assert len(block_c) <= CAP_C_TOTAL
        items.append(dict(qid=it['qid'], cat=str(qa.get('category')),
                          seed_turn=seed_turn, seed_src=seed_src,
                          anchor_lo=lo, anchor_hi=hi, n_anchor=len(anchor_ids),
                          n_cc80=len(cc80_ids), n_cc80_dropped=dropped,
                          pnull=it['pnull'], gate=it['gate'],
                          block_b=block_b, b_sha=R.sha_text(render_reader_prompt(q, block_b)),
                          block_c=block_c, c_sha=R.sha_text(render_reader_prompt(q, block_c))))
    # PF6: V2 replay identity on 5 items (stored anchor_turn == fresh argmax)
    for it in [i for i in prim if i['gate'] == 'anchor'][:5]:
        cid, sidx = it['qid'].split(':')[0], int(it['qid'].split(':')[1])
        qa = srcs[cid]['qa'][sidx]
        texts = [t['text'] for k, v in srcs[cid]['conversation'].items()
                 if k.startswith('session_') and isinstance(v, list) for t in v]
        sc = F._score(tokn, model, qa['question'], texts)
        assert turn_ids_of(srcs, cid)[max(range(len(sc)), key=lambda i: (sc[i], -i))] == it['anchor_turn']
    gold = R.load(AF1 / 'gold.json')
    R.save(OUT / 'contexts.json', dict(
        plan='AF-READ-002 + AMENDMENT_001', cap_b=CAP_B, cap_cc80=CAP_CC80,
        cap_c_total=CAP_C_TOTAL,
        inputs=dict(af1_contexts=R.sha(AF1 / 'contexts.json'),
                    adapter=R.sha(R.T_LRT / 'adapter.jsonl.gz'),
                    selections=R.sha(R.T_LRT / 'selections.jsonl.gz')),
        items=items))
    R.save(OUT / 'gold.json', {it['qid']: gold[it['qid']] for it in items})
    import statistics
    R.save(OUT / 'build_report.json', dict(
        items=len(items),
        seed_src={s: sum(1 for i in items if i['seed_src'] == s) for s in ('v2', 'bm25')},
        block_b_chars=dict(min=min(len(i['block_b']) for i in items),
                           median=statistics.median(len(i['block_b']) for i in items),
                           max=max(len(i['block_b']) for i in items)),
        block_c_chars=dict(min=min(len(i['block_c']) for i in items),
                           median=statistics.median(len(i['block_c']) for i in items),
                           max=max(len(i['block_c']) for i in items)),
        cc80_dropped_total=sum(i['n_cc80_dropped'] for i in items),
        embedding_calls=0))
    print(json.dumps(json.loads((OUT / 'build_report.json').read_text(encoding='utf-8')), indent=1))


def turn_ids_of(srcs, cid):
    return [t['dia_id'] for k, v in srcs[cid]['conversation'].items()
            if k.startswith('session_') and isinstance(v, list) for t in v]


# ---------------------------------------------------------------- reader

def _prepare_natives(items):
    nf = OUT / 'natives.json'
    natives = R.load(nf) if nf.exists() else {}
    dirty = 0
    for it in items:
        for key, text in (('b_native', it['block_b']), ('c_native', it['block_c'])):
            qk = f"{it['qid']}|{key}"
            if qk in natives:
                continue
            src = it['block_b'] if key == 'b_native' else it['block_c']
            p = R.native(render_reader_prompt(_Q(it['qid']), src))
            natives[qk] = p
            dirty += 1
            if dirty % 20 == 0:
                R.save(nf, natives)
    R.save(nf, natives)
    for it in items:
        it['b_native'] = natives[f"{it['qid']}|b_native"]
        it['c_native'] = natives[f"{it['qid']}|c_native"]


_QMAP = None


def _Q(qid):
    global _QMAP
    if _QMAP is None:
        _QMAP = {}
        for c in json.load(open(R.LOCOMO, encoding='utf-8')):
            for i, qa in enumerate(c['qa']):
                _QMAP[f"{c['sample_id']}:{i}"] = qa['question']
    return _QMAP[qid]


def _run_reader(limit):
    ctx = R.load(OUT / 'contexts.json')
    folder = OUT / 'reader'
    process = R.launch(folder)
    try:
        if not (folder / 'calibration.json').exists():
            R.calibrate(folder)
        _prepare_natives(ctx['items'])
        durations = []
        todo = ctx['items'][:limit] if limit else ctx['items']
        for i, it in enumerate(todo):
            for arm, native_key, sha_key in (('B_ANCHOR8K', 'b_native', 'b_sha'),
                                             ('C_ANCHOR8K_CC80', 'c_native', 'c_sha')):
                path = folder / f'{arm}__{R.fname(it["qid"])}.json'
                if path.exists():
                    try:
                        json.loads(path.read_text(encoding='utf-8'))
                        continue
                    except Exception:
                        path.unlink()
                prompt = it[native_key]
                assert R.sha_text(render_reader_prompt(_Q(it['qid']),
                                                       it['block_b'] if arm == 'B_ANCHOR8K' else it['block_c'])) == it[sha_key]
                start = time.time()
                response = R.req('completion', dict(R.BASE, prompt=prompt))
                el = time.time() - start
                R.save(path, dict(arm=arm, qid=it['qid'], response=response,
                                  seconds=round(el, 2), prompt_sha256=R.sha_text(prompt),
                                  nonempty=R.final_text(response) != '',
                                  stop_type=response.get('stop_type'),
                                  tokens_in=response.get('tokens_evaluated')))
                durations.append(el)
                print(f'{arm} {i + 1}/{len(todo)} {el:.1f}s', flush=True)
        if limit:
            import statistics
            mean = statistics.mean(durations) if durations else 0.0
            remaining = len(ctx['items']) * 2 - len(durations)
            R.save(OUT / 'pilot.json', dict(status='PASS', calls=len(durations),
                                            mean_seconds=round(mean, 2),
                                            estimated_remaining_hours=round(mean * remaining / 3600, 2)))
            R.commit([OUT / 'pilot.json'],
                     'AF-READ-002 pilot: calibration passed, 10x2 answers, estimate frozen')
        else:
            hashes = {p.name: R.sha(p) for p in folder.glob('*.json')
                      if '__' in p.stem and '.pending' not in p.name and '.failed' not in p.name}
            n = len(ctx['items']) * 2
            R.save(OUT / 'reader_complete.json', dict(status='PASS' if len(hashes) == n else 'INCOMPLETE',
                                                      calls=len(hashes), expected=n, hashes=hashes))
            if len(hashes) == n:
                R.commit([OUT / 'reader_complete.json'],
                         'AF-READ-002 reader answers frozen before gold opens')
    finally:
        R.stop(process, folder)


def pilot():
    _run_reader(10)


def full():
    _run_reader(None)
    print('READERS DONE')


# ---------------------------------------------------------------- judge

def _af1_correct_a():
    surface = R.load(AF1 / 'blind_surface.json')
    mapping = R.load(AF1 / 'blind_map.json')
    votes = {}
    for p in (AF1 / 'judges').glob('*.json'):
        rec = R.load(p)
        if 'blind_id' in rec:
            v, _ = R.parse_judge_verdict(R.final_text(rec['response']))
            votes.setdefault(rec['blind_id'], []).append(v)
    out = {}
    for x in surface:
        m = mapping[x['blind_id']]
        if m['arm'] == 'A_DEPLOYED' and votes.get(x['blind_id']):
            vs = votes[x['blind_id']]
            out[m['comparison_key']] = (int(sum(vs) * 2 > len(vs)), x['answer'])
    return out


def judge():
    rc = R.load(OUT / 'reader_complete.json')
    assert rc['status'] == 'PASS'
    gold = R.load(OUT / 'gold.json')
    ctx = R.load(OUT / 'contexts.json')
    a_info = _af1_correct_a()
    folder = OUT / 'judges'
    process = R.launch(folder)
    try:
        # PF-J: replay 5 A-arm judge passes, majority must equal stored A verdict
        pfj = {q: v for q, v in a_info.items() if q in gold}
        assert len(pfj) >= 5, 'PF-J pool too small'
        checked = 0
        for qid, (correct_a, ans) in list(pfj.items())[:5]:
            jp = R.native(R.render_judge_prompt(_Q(qid), gold[qid], ans))
            vs = []
            for seed in R.JUDGE_PASSES:
                v, r = R.parse_judge_verdict(R.final_text(R.req(
                    'completion', dict(R.BASE, prompt=jp, seed=seed, temperature=.2, top_p=.9))))
                vs.append(v)
            maj = int(sum(vs) * 2 > len(vs))
            assert maj == correct_a, f'PF-J mismatch {qid}: {vs} vs {correct_a}'
            checked += 1
        R.save(OUT / 'pfj.json', dict(status='PASS', checked=checked))
        answers = []
        for it in ctx['items']:
            for arm in ARMS:
                rec = R.load(OUT / 'reader' / f'{arm}__{R.fname(it["qid"])}.json')
                answers.append(dict(comparison_key=it['qid'], arm=arm, replicate=0,
                                    question=_Q(it['qid']), gold=gold[it['qid']],
                                    answer=R.final_text(rec['response'])))
        surface, mapping = blinded_surface(answers)
        R.save(OUT / 'blind_surface.json', surface)
        R.save(OUT / 'blind_map.json', mapping)
        R.commit([OUT / 'blind_surface.json', OUT / 'pfj.json'],
                 'AF-READ-002 blind surface frozen after answers; PF-J passed (A votes reused)')
        if not (OUT / 'reader' / 'calibration.json').exists():
            R.calibrate(OUT / 'reader')
        for i, x in enumerate(surface):
            for seed in R.JUDGE_PASSES:
                path = folder / f'{x["blind_id"]}_{seed}.json'
                if path.exists():
                    continue
                jp = R.native(R.render_judge_prompt(x['question'], x['gold'], x['answer']))
                response = R.req('completion', dict(R.BASE, prompt=jp, seed=seed,
                                                    temperature=.2, top_p=.9))
                R.save(path, dict(blind_id=x['blind_id'], seed=seed, response=response))
            if i % 25 == 0:
                print(f'judge {i + 1}/{len(surface)}', flush=True)
    finally:
        R.stop(process, folder)
    R.save(OUT / 'judge_complete.json', dict(status='PASS'))
    R.commit([OUT / 'judge_complete.json'], 'AF-READ-002 judge votes frozen')


# ---------------------------------------------------------------- score

def score():
    ctx = R.load(OUT / 'contexts.json')
    surface = R.load(OUT / 'blind_surface.json')
    mapping = R.load(OUT / 'blind_map.json')
    votes = {}
    for p in (OUT / 'judges').glob('*.json'):
        rec = R.load(p)
        if 'blind_id' in rec:
            v, _ = R.parse_judge_verdict(R.final_text(rec['response']))
            votes.setdefault(rec['blind_id'], []).append(v)
    correct = {'A_DEPLOYED': {}, 'B_ANCHOR8K': {}, 'C_ANCHOR8K_CC80': {}}
    for x in surface:
        m = mapping[x['blind_id']]
        vs = votes.get(x['blind_id'], [])
        if vs:
            correct[m['arm']][m['comparison_key']] = int(sum(vs) * 2 > len(vs))
    a_map = {q: v[0] for q, v in _af1_correct_a().items()}
    ids = sorted(set(a_map) & set(correct['B_ANCHOR8K']))
    correct['A_DEPLOYED'] = {q: a_map[q] for q in ids}

    def mcn(ca, cb):
        w = sum(1 for q in ids if ca[q] and not cb[q])
        l = sum(1 for q in ids if not ca[q] and cb[q])
        return dict(n=len(ids), wins=w, losses=l, net=w - l, p=round(mcnemar_exact(w, l), 5))

    def mean_tokens(arm):
        vals = []
        for it in ctx['items']:
            if arm == 'A_DEPLOYED':
                p = AF1 / 'reader' / f'A_DEPLOYED__{R.fname(it["qid"])}.json'
            else:
                p = OUT / 'reader' / f'{arm}__{R.fname(it["qid"])}.json'
            vals.append(R.load(p).get('tokens_in') or 0)
        import statistics
        return round(statistics.mean(vals), 1)

    tok = {arm: mean_tokens(arm) for arm in correct}
    c = mcn(correct['C_ANCHOR8K_CC80'], correct['A_DEPLOYED'])
    b = mcn(correct['B_ANCHOR8K'], correct['A_DEPLOYED'])
    summary = dict(
        plan='AF-READ-002 + AMENDMENT_001',
        correct=dict(A_DEPLOYED=sum(correct['A_DEPLOYED'].values()),
                     B_ANCHOR8K=sum(correct['B_ANCHOR8K'].values()),
                     C_ANCHOR8K_CC80=sum(correct['C_ANCHOR8K_CC80'].values())),
        mcnemar_C_vs_A=c, mcnemar_B_vs_A=b,
        mean_tokens_in=tok,
        seed_src={s: sum(1 for i in ctx['items'] if i['seed_src'] == s) for s in ('v2', 'bm25')},
        cc80_dropped_total=sum(i['n_cc80_dropped'] for i in ctx['items']),
        disposition=dict(
            IMPROVES=c['net'] > 0 and c['p'] < .05,
            WORKS=c['net'] >= -4 and c['p'] > .05 and tok['C_ANCHOR8K_CC80'] <= .60 * tok['A_DEPLOYED'],
            SIGNAL=c['net'] >= -8 or b['net'] >= -8,
            DEAD=c['net'] < -8 and b['net'] < -8),
        by_category={str(k): {arm: sum(v[q] for q in v if _cat(ctx, q) == str(k))
                              for arm, v in correct.items()}
                     for k in sorted({_cat(ctx, q) for q in ids})})
    R.save(OUT / 'results.json', dict(summary=summary))
    R.commit([OUT / 'results.json'], 'AF-READ-002 scored results')
    print(json.dumps(summary, indent=1))


_CATMAP = None


def _cat(ctx, qid):
    global _CATMAP
    if _CATMAP is None:
        _CATMAP = {i['qid']: i['cat'] for i in ctx['items']}
    return _CATMAP[qid]


def status():
    folder = OUT / 'reader'
    done = len([p for p in folder.glob('*.json') if '__' in p.stem]) if folder.exists() else 0
    print(json.dumps(dict(reader_files=done, targets=240,
                          judge_files=len(list((OUT / 'judges').glob('*.json'))) if (OUT / 'judges').exists() else 0)))


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    {'build': build, 'pilot': pilot, 'full': full, 'judge': judge,
     'score': score, 'status': status}[sys.argv[1]]()

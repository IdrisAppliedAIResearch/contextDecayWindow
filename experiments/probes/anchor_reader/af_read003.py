"""AF-READ-003: scale the frozen AF-READ-002 arms to the full LoCoMo dev main.

Plan: AF_READ_003_PLAN.md (locked e51d1907). n=1,420 new main cat-1-4 questions
(everything except the 120 AF-READ-001 primaries); 002 verdicts reused only in
the pooled secondary. Builders, seeds, budgets, server, judge are the 002
objects imported here — no reimplementation of any frozen mechanism.

build    GPU/offline: contexts (gold-free), H120 replay asserts, zero embed calls
pilot    server: calibration + 10x3 readers + estimate
full     server: 1,420x3 readers, hashes committed before gold opens
judge    server: blind 3-pass judge of all three arms (new items, no reuse)
score    offline: McNemar, registered dispositions, CI label, secondaries
status   offline: counts
"""
import json
import math
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import af_read001 as R  # noqa: E402
import af_read002 as T  # noqa: E402

from analysis.hh001_prompt import render_reader_prompt, blinded_surface  # noqa: E402
from episodic._config import EpisodicConfig  # noqa: E402
from score_sample120 import mcnemar_exact  # noqa: E402

OUT = HERE / 'artifacts' / 'af_read003'
AF1 = HERE / 'artifacts'
AF2 = HERE / 'artifacts' / 'af_read002'
TAU = 0.2
ARMS = ('A_DEPLOYED', 'B_ANCHOR8K', 'C_ANCHOR8K_CC80')
WORKS_MARGIN = -48
DEAD_MARGIN = -94
ROOT = R.ROOT


def _logsum(k0, n, p):
    def logpmf(j):
        return (math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1)
                + j * math.log(p) + (n - j) * math.log1p(-p))
    lps = [logpmf(j) for j in range(n + 1)]
    m = max(lps[k0:])
    ge = m + math.log(sum(math.exp(lp - m) for lp in lps[k0:]))
    m = max(lps[:k0 + 1])
    le = m + math.log(sum(math.exp(lp - m) for lp in lps[:k0 + 1]))
    return le, ge


def clopper_pearson(k, n, alpha):
    """Exact binomial interval; (0, 1) endpoints handled by convention.
    alpha is the ONE-SIDED tail (pass .025 for a two-sided 95% interval)."""
    la = math.log(alpha)
    if k == 0:
        lo = 0.0
    else:
        a, b = 0.0, 1.0
        for _ in range(80):
            p = (a + b) / 2
            if _logsum(k, n, p)[1] > la:
                b = p
            else:
                a = p
        lo = (a + b) / 2
    if k == n:
        hi = 1.0
    else:
        a, b = 0.0, 1.0
        for _ in range(80):
            p = (a + b) / 2
            if _logsum(k, n, p)[0] > la:
                a = p
            else:
                b = p
        hi = (a + b) / 2
    return lo, hi


def delta_ci(wc, wa, n):
    """Conservative interval for p_C - p_A from paired counts: difference of
    one-sided exact Clopper-Pearson bounds (tail .05 each; registered in
    AF_READ_003_PLAN.md as the CI_NONINFERIOR anchor; coverage is conservative)."""
    lo_c, _ = clopper_pearson(wc, n, .05)
    _, hi_a = clopper_pearson(wa, n, .05)
    _, hi_c = clopper_pearson(wc, n, .05)
    lo_a, _ = clopper_pearson(wa, n, .05)
    return lo_c - hi_a, hi_c - lo_a


# ---------------------------------------------------------------- build

def build():
    _af1, _prim, prompts, sels, byconv, srcs = T.load_world()
    af1 = R.load(AF1 / 'contexts.json')
    p120 = {i['qid'] for i in af1['items'] if i['kind'] == 'primary'}
    desc = {i['qid'] for i in af1['items'] if i['kind'] == 'descriptive'}
    af2 = {i['qid']: i for i in R.load(AF2 / 'contexts.json')['items']}
    nat = {(r['conversation'], r['source_index']): r
           for r in R.rows_gz(R.T_LRT / 'native_prompts.jsonl.gz')}
    vecs = T.vector_cache()
    tokn, model, tau = R.F._loader('V2', 20261011)
    cfg = EpisodicConfig(read_policy='legacy_cc80', recency_window_n=0)

    conv = {}
    for cid, c in srcs.items():
        turns, els = [], byconv[cid]
        for k, v in c['conversation'].items():
            if k.startswith('session_') and isinstance(v, list):
                turns += [t['dia_id'] for t in v]
        texts = [t['text'] for k, v in c['conversation'].items()
                 if k.startswith('session_') and isinstance(v, list) for t in v]
        conv[cid] = dict(turns=turns, texts=texts, bm=R.arms.BM25(texts),
                         sel=[e['id'] for e in els])

    main = [(cid, i) for cid in srcs for i, qa in enumerate(srcs[cid]['qa'])
            if str(qa.get('category')) in {'1', '2', '3', '4'}]
    pop = [k for k in sorted(main) if f'{k[0]}:{k[1]}' not in p120]
    items, gold = [], {}
    seed_check = 0
    for n, (cid, sidx) in enumerate(pop):
        qid = f'{cid}:{sidx}'
        qa = srcs[cid]['qa'][sidx]
        q = qa['question']
        assert qa.get('answer') is not None, f'no gold {qid}'
        row = nat[(cid, sidx)]
        a_shell = 'full'
        if R.HEAD in row['text']:
            assert R.render_reader_prompt(
                q, row['text'].split(R.HEAD, 1)[1]
                .rsplit(f'\n\nQuestion: {q}', 1)[0]) == row['text'], f'A shell drift {qid}'
        else:
            # 2/1986 frozen deployed rows: empty timeline union -> no-record render
            assert R.render_reader_prompt(q, '') == row['text'], f'A empty-shell drift {qid}'
            a_shell = 'empty_union'
        assert row['prompt'].endswith('\n\n</think>\n\n'), f'thinking suffix {qid}'
        cw = conv[cid]
        prow = prompts[(cid, sidx)]
        sel = sels[prow['key']]
        assert sel['ids'] == cw['sel'], f'PF2 selection drift {qid}'
        els = byconv[cid]
        sc = R.F._score(tokn, model, q, cw['texts'])
        ai = max(range(len(sc)), key=lambda i: (sc[i], -i))
        P, _ = R.pool_ids(q, cw['texts'], cw['bm'])
        pnull = R.F._pnull([sc[i] for i in P], tau)
        if pnull < TAU:
            seed_turn, seed_src = cw['turns'][ai], 'v2'
        else:
            sc_bm = cw['bm'].score(q)
            bi = max(range(len(sc_bm)), key=lambda i: (sc_bm[i], -i))
            seed_turn, seed_src = cw['turns'][bi], 'bm25'
            if seed_check < 5:
                assert T.seed_bm25(q, srcs, cid, cw['turns']) == seed_turn, f'BM25 seed drift {qid}'
                seed_check += 1
        hits = [j for j, e in enumerate(els) if seed_turn in e['dialogue_ids']]
        assert len(hits) == 1, f'seed element ambiguity {qid}'
        lo, hi = T.grow_window(els, hits[0], T.CAP_B)
        block_b = '\n'.join(e['element'] for e in els[lo:hi + 1])
        assert len(block_b) <= T.CAP_B and block_b
        eps = [dict(id=e['id'], turn_number=j, user_message=e['text'],
                    assistant_message='', searchable_text=e['text'],
                    embedding=vecs[e['text']]) for j, e in enumerate(els)]
        assert q in vecs, f'query vector missing {qid}'
        alloc = T.cc80_select(eps, q, vecs[q], cfg)
        replay = T.cc80_select(eps, q, vecs[q], cfg)
        assert alloc.selected_ids == replay.selected_ids, f'CC80 not deterministic {qid}'
        rank_pos = {els[idx]['id']: r for r, idx in enumerate(alloc.ranking.order)}
        cc80_ids = [i for i in alloc.selected_ids]
        anchor_ids = [e['id'] for e in els[lo:hi + 1]]
        chosen = set(anchor_ids) | set(cc80_ids)
        removable = [i for i in cc80_ids if i not in anchor_ids]
        dropped = 0
        block_c = '\n'.join(e['element'] for e in els if e['id'] in chosen)
        while len(block_c) > T.CAP_C_TOTAL and removable:
            worst = max(removable, key=lambda i: rank_pos[i])
            removable.remove(worst)
            chosen.discard(worst)
            dropped += 1
            block_c = '\n'.join(e['element'] for e in els if e['id'] in chosen)
        assert len(block_c) <= T.CAP_C_TOTAL
        items.append(dict(qid=qid, subset='af1_descriptive' if qid in desc else 'never_run',
                          cat=str(qa.get('category')), a_shell=a_shell,
                          seed_turn=seed_turn,
                          seed_src=seed_src, anchor_lo=lo, anchor_hi=hi,
                          n_anchor=len(anchor_ids), n_cc80=len(cc80_ids),
                          n_cc80_dropped=dropped, pnull=round(pnull, 6),
                          gate='anchor' if pnull < TAU else 'fallback',
                           a_native=row['prompt'], a_sha=R.sha_text(row['prompt']),
                           block_b=block_b, b_sha=R.sha_text(render_reader_prompt(q, block_b)),
                           block_c=block_c, c_sha=R.sha_text(render_reader_prompt(q, block_c))))
        gold[qid] = str(qa['answer'])
        if n % 100 == 0:
            print(f'build {n}/{len(pop)}', flush=True)

    # PF6: the frozen 002 builder path reproduces 002 block SHAs byte-identically
    replay = []
    for qid, want in list(af2.items())[:5]:
        cid = qid.split(':')[0]
        sidx = int(qid.split(':')[1])
        qa = srcs[cid]['qa'][sidx]
        q = qa['question']
        els = byconv[cid]
        if want['seed_src'] == 'v2':
            sc = R.F._score(tokn, model, qa['question'], conv[cid]['texts'])
            ai = max(range(len(sc)), key=lambda i: (sc[i], -i))
            seed_turn = conv[cid]['turns'][ai]
        else:
            seed_turn = T.seed_bm25(qa['question'], srcs, cid, conv[cid]['turns'])
        assert seed_turn == want['seed_turn'], f'PF6 seed drift {qid}'
        lo, hi = T.grow_window(els, [j for j, e in enumerate(els)
                                     if seed_turn in e['dialogue_ids']][0], T.CAP_B)
        bb = '\n'.join(e['element'] for e in els[lo:hi + 1])
        assert R.sha_text(R.render_reader_prompt(q, bb)) == want['b_sha'], f'PF6 block_b drift {qid}'
        eps = [dict(id=e['id'], turn_number=j, user_message=e['text'],
                    assistant_message='', searchable_text=e['text'],
                    embedding=vecs[e['text']]) for j, e in enumerate(els)]
        al = T.cc80_select(eps, q, vecs[q], cfg)
        rp = {els[idx]['id']: r for r, idx in enumerate(al.ranking.order)}
        chosen = set(e['id'] for e in els[lo:hi + 1]) | set(al.selected_ids)
        removable = [i for i in al.selected_ids if i not in {e['id'] for e in els[lo:hi + 1]}]
        bc = '\n'.join(e['element'] for e in els if e['id'] in chosen)
        while len(bc) > T.CAP_C_TOTAL and removable:
            worst = max(removable, key=lambda i: rp[i])
            removable.remove(worst)
            chosen.discard(worst)
            bc = '\n'.join(e['element'] for e in els if e['id'] in chosen)
        assert R.sha_text(R.render_reader_prompt(q, bc)) == want['c_sha'], f'PF6 block_c drift {qid}'
        replay.append(qid)

    R.save(OUT / 'contexts.json', dict(
        plan='AF_READ_003_PLAN.md (e51d1907)', tau=TAU, cap_b=T.CAP_B,
        cap_cc80=T.CAP_CC80, cap_c_total=T.CAP_C_TOTAL,
        inputs=dict(af1_contexts=R.sha(AF1 / 'contexts.json'),
                    af2_contexts=R.sha(AF2 / 'contexts.json'),
                    adapter=R.sha(R.T_LRT / 'adapter.jsonl.gz'),
                    selections=R.sha(R.T_LRT / 'selections.jsonl.gz'),
                    native_prompts=R.sha(R.T_LRT / 'native_prompts.jsonl.gz')),
        items=items))
    R.save(OUT / 'gold.json', gold)
    bb = [len(i['block_b']) for i in items]
    bc = [len(i['block_c']) for i in items]
    R.save(OUT / 'build_report.json', dict(
        items=len(items),
        a_shell={s: sum(1 for i in items if i['a_shell'] == s)
                 for s in ('full', 'empty_union')},
        subset={s: sum(1 for i in items if i['subset'] == s)
                for s in ('never_run', 'af1_descriptive')},
        seed_src={s: sum(1 for i in items if i['seed_src'] == s) for s in ('v2', 'bm25')},
        block_b_chars=dict(min=min(bb), median=statistics.median(bb), max=max(bb)),
        block_c_chars=dict(min=min(bc), median=statistics.median(bc), max=max(bc)),
        cc80_dropped_total=sum(i['n_cc80_dropped'] for i in items),
        pf6_replay=dict(items=replay, status='PASS'),
        embedding_calls=0))
    print(json.dumps(json.loads((OUT / 'build_report.json').read_text(encoding='utf-8')),
                     indent=1))


# ---------------------------------------------------------------- reader

def _Q(qid):
    return T._Q(qid)


def _prepare_natives(items):
    nf = OUT / 'natives.json'
    natives = R.load(nf) if nf.exists() else {}
    dirty = 0
    for it in items:
        for key in ('b_native', 'c_native'):
            qk = f"{it['qid']}|{key}"
            if qk in natives:
                continue
            src = it['block_b'] if key == 'b_native' else it['block_c']
            natives[qk] = R.native(render_reader_prompt(_Q(it['qid']), src))
            dirty += 1
            if dirty % 20 == 0:
                R.save(nf, natives)
    R.save(nf, natives)
    for it in items:
        it['b_native'] = natives[f"{it['qid']}|b_native"]
        it['c_native'] = natives[f"{it['qid']}|c_native"]


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
            for arm, native_key, sha_key in (
                    ('A_DEPLOYED', 'a_native', 'a_sha'),
                    ('B_ANCHOR8K', 'b_native', 'b_sha'),
                    ('C_ANCHOR8K_CC80', 'c_native', 'c_sha')):
                path = folder / f'{arm}__{R.fname(it["qid"])}.json'
                if path.exists():
                    try:
                        json.loads(path.read_text(encoding='utf-8'))
                        continue
                    except Exception:
                        path.unlink()
                prompt = it[native_key]
                if arm == 'A_DEPLOYED':
                    assert R.sha_text(prompt) == it[sha_key]
                else:
                    assert R.sha_text(render_reader_prompt(
                        _Q(it['qid']),
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
                if i % 25 == 0:
                    print(f'{arm} {i + 1}/{len(todo)} {el:.1f}s', flush=True)
        if limit:
            mean = statistics.mean(durations) if durations else 0.0
            remaining = len(ctx['items']) * 3 - len(durations)
            R.save(OUT / 'pilot.json', dict(status='PASS', calls=len(durations),
                                            mean_seconds=round(mean, 2),
                                            estimated_remaining_hours=round(mean * remaining / 3600, 2)))
            R.commit([OUT / 'pilot.json'],
                     'AF-READ-003 pilot: calibration passed, 10x3 answers, estimate frozen')
        else:
            hashes = {p.name: R.sha(p) for p in folder.glob('*.json')
                      if '__' in p.stem and '.pending' not in p.name
                      and '.failed' not in p.name}
            n = len(ctx['items']) * 3
            R.save(OUT / 'reader_complete.json',
                   dict(status='PASS' if len(hashes) == n else 'INCOMPLETE',
                        calls=len(hashes), expected=n, hashes=hashes))
            if len(hashes) == n:
                R.commit([OUT / 'reader_complete.json'],
                         'AF-READ-003 reader answers frozen before gold opens')
    finally:
        R.stop(process, folder)


def pilot():
    _run_reader(10)


def full():
    _run_reader(None)
    print('READERS DONE')


# ---------------------------------------------------------------- judge

def judge():
    rc = R.load(OUT / 'reader_complete.json')
    assert rc['status'] == 'PASS'
    gold = R.load(OUT / 'gold.json')
    ctx = R.load(OUT / 'contexts.json')
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
    R.commit([OUT / 'blind_surface.json'],
             'AF-READ-003 blind surface frozen after answers (all three arms new)')
    folder = OUT / 'judges'
    process = R.launch(folder)
    try:
        if not (folder / 'calibration.json').exists():
            R.calibrate(folder)
        for i, x in enumerate(surface):
            for seed in R.JUDGE_PASSES:
                path = folder / f'{x["blind_id"]}_{seed}.json'
                if path.exists():
                    continue
                jp = R.native(R.render_judge_prompt(x['question'], x['gold'], x['answer']))
                response = R.req('completion', dict(R.BASE, prompt=jp, seed=seed,
                                                    temperature=.2, top_p=.9))
                R.save(path, dict(blind_id=x['blind_id'], seed=seed, response=response))
            if i % 50 == 0:
                print(f'judge {i + 1}/{len(surface)}', flush=True)
    finally:
        R.stop(process, folder)
    R.save(OUT / 'judge_complete.json', dict(status='PASS'))
    R.commit([OUT / 'judge_complete.json'], 'AF-READ-003 judge votes frozen')


# ---------------------------------------------------------------- score

def _votes(base):
    votes = {}
    for p in (base / 'judges').glob('*.json'):
        rec = R.load(p)
        if 'blind_id' in rec:
            v, _ = R.parse_judge_verdict(R.final_text(rec['response']))
            votes.setdefault(rec['blind_id'], []).append(v)
    return votes


def _correct(base):
    surface = R.load(base / 'blind_surface.json')
    mapping = R.load(base / 'blind_map.json')
    votes = _votes(base)
    out = {}
    for x in surface:
        m = mapping[x['blind_id']]
        vs = votes.get(x['blind_id'], [])
        if vs:
            out.setdefault(m['arm'], {})[m['comparison_key']] = int(sum(vs) * 2 > len(vs))
    return out


def _mcn(ca, cb, ids):
    w = sum(1 for q in ids if cb[q] and not ca[q])
    l = sum(1 for q in ids if ca[q] and not cb[q])
    return dict(n=len(ids), wins=w, losses=l, net=w - l, p=round(mcnemar_exact(w, l), 5))


def score():
    ctx = {i['qid']: i for i in R.load(OUT / 'contexts.json')['items']}
    corr = _correct(OUT)
    ids = sorted(set(corr['A_DEPLOYED']) & set(corr['B_ANCHOR8K'])
                 & set(corr['C_ANCHOR8K_CC80']))
    c = _mcn(corr['A_DEPLOYED'], corr['C_ANCHOR8K_CC80'], ids)
    b = _mcn(corr['A_DEPLOYED'], corr['B_ANCHOR8K'], ids)
    dlo, dhi = delta_ci(c['wins'], c['losses'], len(ids))
    tok = {}
    for arm in ARMS:
        tok[arm] = round(statistics.mean(
            (R.load(OUT / 'reader' / f'{arm}__{R.fname(q)}').get('tokens_in') or 0)
            for q in ids), 1)
    abst = {a: 0 for a in ARMS}
    mapping = R.load(OUT / 'blind_map.json')
    for x in R.load(OUT / 'blind_surface.json'):
        if 'NOT ENOUGH INFORMATION' in (x.get('answer') or '').upper():
            abst[mapping[x['blind_id']]['arm']] += 1
    summary = dict(
        plan='AF_READ_003_PLAN.md (e51d1907)', population='new', n=len(ids),
        correct={a: sum(corr[a][q] for q in ids) for a in ARMS},
        mcnemar_C_vs_A=c, mcnemar_B_vs_A=b,
        delta_C_vs_A_prop_ci=[round(dlo, 5), round(dhi, 5)],
        mean_tokens_in=tok, abstentions=abst,
        disposition=dict(
            IMPROVES=c['net'] > 0 and c['p'] < .05,
            WORKS=c['net'] >= WORKS_MARGIN and c['p'] > .05
            and tok['C_ANCHOR8K_CC80'] <= .60 * tok['A_DEPLOYED'],
            DEAD=c['net'] < DEAD_MARGIN and b['net'] < DEAD_MARGIN,
            CI_NONINFERIOR=dlo > -.0333),
        by_gate={g: dict(n=sum(1 for q in ids if ctx[q]['gate'] == g),
                         **{a: sum(corr[a][q] for q in ids if ctx[q]['gate'] == g)
                            for a in ARMS}) for g in ('anchor', 'fallback')},
        by_subset={s: dict(n=sum(1 for q in ids if ctx[q]['subset'] == s),
                           **{a: sum(corr[a][q] for q in ids if ctx[q]['subset'] == s)
                              for a in ARMS})
                   for s in ('never_run', 'af1_descriptive')},
        by_category={k: dict(n=sum(1 for q in ids if ctx[q]['cat'] == k),
                             **{a: sum(corr[a][q] for q in ids if ctx[q]['cat'] == k)
                                for a in ARMS})
                     for k in sorted({ctx[q]['cat'] for q in ids})})
    # pooled secondary: 002 items (known verdicts) + new
    c2 = _correct(AF2)
    a1 = T._af1_correct_a()
    ids2 = sorted(set(c2['B_ANCHOR8K']) & set(c2['C_ANCHOR8K_CC80']) & set(a1))
    pooled = {arm: dict() for arm in ARMS}
    for q in ids2:
        pooled['A_DEPLOYED'][q] = a1[q][0]
        pooled['B_ANCHOR8K'][q] = c2['B_ANCHOR8K'][q]
        pooled['C_ANCHOR8K_CC80'][q] = c2['C_ANCHOR8K_CC80'][q]
    for arm in ARMS:
        pooled[arm].update({q: corr[arm][q] for q in ids})
    pid = sorted(pooled['A_DEPLOYED'])
    summary['pooled_secondary'] = dict(
        n=len(pid),
        correct={a: sum(pooled[a][q] for q in pid) for a in ARMS},
        mcnemar_C_vs_A=_mcn(pooled['A_DEPLOYED'], pooled['C_ANCHOR8K_CC80'], pid),
        mcnemar_B_vs_A=_mcn(pooled['A_DEPLOYED'], pooled['B_ANCHOR8K'], pid))
    R.save(OUT / 'results.json', dict(summary=summary))
    R.commit([OUT / 'results.json'], 'AF-READ-003 scored results')
    print(json.dumps(summary, indent=1))


def status():
    print(json.dumps(dict(
        reader_files=len([p for p in (OUT / 'reader').glob('*.json') if '__' in p.stem]),
        targets=len(R.load(OUT / 'contexts.json')['items']) * 3
        if (OUT / 'contexts.json').exists() else 0,
        judge_files=len(list((OUT / 'judges').glob('*.json')))
        if (OUT / 'judges').exists() else 0)))


if __name__ == '__main__':
    {'build': build, 'pilot': pilot, 'full': full, 'judge': judge,
     'score': score, 'status': status}[sys.argv[1]]()

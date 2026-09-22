"""AF-READ-001: reader arm — V2 gated anchor vs deployed timeline (plan f75f590d).

build    GPU, no server: V2 argmax/P(null), windows, arm contexts (gold-free prompts)
pilot    server: calibration gates + 10x3 readers + wall-clock estimate
full     server: all 240x3 readers; raw answers committed before gold opens
judge    server: blind judge passes (3x primary, 1x descriptive); gold opens here
score    offline: McNemar, budget table, tau sweep; writes results.json
status   offline: progress counts

Plan governs all parameters; this file must not diverge from it silently.
"""
import gzip
import hashlib
import json
import os
import re
import socket
import statistics
import subprocess
import sys
import time
import traceback
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (str(ROOT), str(ROOT / 'experiments/probes/bert_anchor'),
          str(ROOT / 'experiments/probes/unified_anchor'),
          str(ROOT / 'experiments/probes/anchor_ft'), str(ROOT / 'src')):
    sys.path.insert(0, p)

import arms  # noqa: E402
import af_ft001 as F  # noqa: E402
from ft_pipeline import pool_ids, LOCOMO  # noqa: E402
from analysis.hh001_prompt import (render_reader_prompt, render_judge_prompt,  # noqa: E402
                                   parse_judge_verdict, blinded_surface)

OUT = HERE / 'artifacts'
T_LRT = ROOT / 'experiments/locomo_relevance_timeline/artifacts'
LAUNCH = ROOT / 'experiments/study_E/artifacts/confirmation/restart005/launch.json'
PORT, CONTEXT = 8099, 40960
TAU, WINDOW, SEED_V2 = 0.2, 2, 20261011
ARMS = ('A_DEPLOYED', 'B_ANCHOR', 'C_GATE')
PILOT_N, JUDGE_PASSES = 10, (9100, 9101, 9102)
BASE = dict(seed=5005, temperature=.6, top_p=.95, top_k=20, min_p=0, repeat_penalty=1,
            presence_penalty=0, cache_prompt=False, reasoning_format='none',
            n_predict=4096, id_slot=0)
HEAD = '\n\nHere is what you remember of the conversation:\n\n'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha_text(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def save(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding='utf-8')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def fname(s):
    return s.replace(':', '_').replace('/', '_')


def req(route, data=None):
    r = urllib.request.Request(f'http://127.0.0.1:{PORT}/{route}',
                               data=None if data is None else json.dumps(data).encode('utf8'),
                               headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(r, timeout=600) as f:
        return json.load(f)


def commit(paths, message):
    subprocess.run(['git', 'add', *[str(v) for v in paths]], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['git', 'commit', '-m', message], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL)


def rows_gz(p):
    with gzip.open(p, 'rt', encoding='utf8') as f:
        return [json.loads(l) for l in f]


def final_text(response):
    return (response.get('content') or '').strip()


# ------------------------------------------------------------------ build

def build():
    b = load(F.ART / 'build2.json')
    srcs = {c['sample_id']: c for c in json.load(open(LOCOMO, encoding='utf-8'))}
    v2_raw = load(F.ART / 'results.json')['raw_per_item']['V2'][str(SEED_V2)]
    nat = {(r['conversation'], r['source_index']): r
           for r in rows_gz(T_LRT / 'native_prompts.jsonl.gz')}
    tokn, model, tau = F._loader('V2', SEED_V2)

    conv_turns = {}
    for cid, c in srcs.items():
        turns = []
        for k, v in c['conversation'].items():
            if k.startswith('session_') and isinstance(v, list):
                date = c['conversation'].get(f'{k}_date_time', '')
                turns += [dict(id=t['dia_id'], text=t['text'], speaker=t.get('speaker', '?'),
                               session=k, date=date) for t in v]
        conv_turns[cid] = turns

    held = set(b['heldout'])
    sample2 = {it['qid'] for it in json.load(open(F.ART5 / 'sample2.json', encoding='utf-8'))}
    items, gold = [], {}
    for qid in sorted(held | sample2):
        cid, sidx = qid.split(':')[0], int(qid.split(':')[1])
        qa = srcs[cid]['qa'][sidx]
        row = nat[(cid, sidx)]
        assert qa.get('answer') is not None, f'no gold answer for {qid}'
        kind = 'primary' if qid in held else 'descriptive'
        turns = conv_turns[cid]
        texts = [t['text'] for t in turns]
        sc = F._score(tokn, model, qa['question'], texts)
        ai = max(range(len(sc)), key=lambda i: (sc[i], -i))
        turn_ids = [t['id'] for t in turns]
        gset = {d for d in qa.get('evidence', []) if d in set(turn_ids)}
        if kind == 'primary' and v2_raw.get(qid, {}).get('any') is not None:
            assert int(turn_ids[ai] in gset) == v2_raw[qid]['any'], f'PF2 drift {qid}'
        P, _ = pool_ids(qa['question'], texts, arms.BM25(texts))
        pnull = F._pnull([sc[i] for i in P], tau)
        lo, hi = max(0, ai - WINDOW), min(len(turns), ai + WINDOW + 1)
        segs, cur = [], []
        for t in turns[lo:hi]:
            if cur and cur[-1]['session'] != t['session']:
                segs.append(cur)
                cur = []
            cur.append(t)
        if cur:
            segs.append(cur)
        block = '\n\n'.join(
            f'<record session="{s[0]["session"]}" date="{s[0]["date"]}" '
            f'dialogue_ids="{" ".join(t["id"] for t in s)}">\n'
            + '\n'.join(f'{t["speaker"]}: {t["text"]}' for t in s) + '\n</record>'
            for s in segs)
        prompt_b = render_reader_prompt(qa['question'], block)
        # same instruction shell as the frozen deployed prompts (PF2 shell identity)
        a_text = row['text']
        assert render_reader_prompt(
            qa['question'], a_text.split(HEAD, 1)[1].rsplit(f'\n\nQuestion: {qa["question"]}', 1)[0]
        ) == a_text, f'shell identity failed {qid}'
        assert row['prompt'].endswith('\n\n</think>\n\n')
        items.append(dict(qid=qid, kind=kind, cat=str(qa.get('category')),
                          a_prompt=a_text, b_prompt=prompt_b,
                          a_sha=sha_text(a_text), b_sha=sha_text(prompt_b),
                          a_native_sha=sha_text(row['prompt']),
                          a_native=row['prompt'],
                          anchor_turn=turn_ids[ai], anchor_sc=round(sc[ai], 4),
                          pnull=round(pnull, 6), block_chars=len(block),
                          gate='anchor' if pnull < TAU else 'fallback'))
        gold[qid] = str(qa['answer'])
    save(OUT / 'contexts.json', dict(plan='f75f590d', tau=TAU, window=WINDOW, seed_v2=SEED_V2,
                                     inputs=dict(build2_sha=sha(F.ART / 'build2.json'),
                                                 native_prompts_sha=sha(T_LRT / 'native_prompts.jsonl.gz'),
                                                 v2_ckpt=sha(F.ART / f'ckpt_V2_{SEED_V2}' / 'model.safetensors')),
                                     items=items))
    save(OUT / 'gold.json', gold)
    print(json.dumps(dict(items=len(items),
                          gate_anchor=sum(1 for i in items if i['gate'] == 'anchor'),
                          gold=len(gold)), indent=1))


# ------------------------------------------------------------------ server

def launch(folder):
    folder.mkdir(parents=True, exist_ok=True)
    with socket.socket() as s:
        assert s.connect_ex(('127.0.0.1', PORT)) != 0, 'PORT_IN_USE — stop any running reader server first'
    command = list(load(LAUNCH)['command'])
    # this build logs model placement only at verbosity >= 4 (see unified_contextual_memory/transport.py)
    command += ['--log-verbosity', '4']
    for flag, value in [('--port', str(PORT)), ('--parallel', '1'), ('--ctx-size', str(CONTEXT))]:
        command[command.index(flag) + 1] = value
    assert command[command.index('--reasoning') + 1] == 'off'
    assert command[command.index('--reasoning-budget') + 1] == '0'
    env = os.environ.copy()
    env['PATH'] = ('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/x64;'
                   'C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.6/bin;') + env['PATH']
    err = folder / 'server.err'
    err_offset = err.stat().st_size if err.exists() else 0
    process = subprocess.Popen(command, env=env, stdout=(folder / 'server.out').open('ab'),
                               stderr=err.open('ab'),
                               creationflags=subprocess.CREATE_NO_WINDOW)
    save(folder / 'launch.json', dict(pid=process.pid, command=command,
                                      server_sha256=sha(command[0]), started=time.time()))
    try:
        for _ in range(300):
            assert process.poll() is None, 'SERVER_EXIT'
            try:
                props = req('props')
                break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError('SERVER_TIMEOUT')
        assert props['total_slots'] == 1
        assert re.search(r'offloaded (\d+)/\1 layers',
                         err.read_bytes()[err_offset:].decode('utf-8', errors='replace')), 'NOT_FULLY_OFFLOADED'
        save(folder / 'props.json', props)
        return process
    except BaseException:
        process.terminate()
        process.wait(timeout=20)
        raise


def stop(process, folder):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    save(folder / 'stopped.json', dict(pid=process.pid, exit_code=process.returncode,
                                       time=time.time()))


def native(text):
    prompt = req('apply-template', dict(messages=[dict(role='user', content=text)],
                                        add_generation_prompt=True,
                                        chat_template_kwargs={'enable_thinking': False},
                                        reasoning_effort='none'))['prompt']
    assert prompt.endswith('\n\n</think>\n\n'), 'THINKING_SUFFIX'
    return prompt


def calibrate(folder):
    prompt = native('What is 17 + 28? Answer only the number.')
    answers = [req('completion', dict(BASE, prompt=prompt, n_predict=64)) for _ in range(2)]
    assert final_text(answers[0]) == final_text(answers[1]) == '45', 'READER_CAL'
    fixtures = [('Where did Jo move?', 'Paris', '', False),
                ('What did Jo buy?', 'a red bicycle', 'A bike that is red.', True),
                ('Where did Jo move?', 'Paris', 'Rome', False),
                ('When did Jo move?', 'May 2024', 'May 2023', False),
                ('Where did Jo move?', 'Paris', 'Jo moved to Rome, not Paris.', False)]
    for i, (q, g, a, expected) in enumerate(fixtures):
        jp = native(render_judge_prompt(q, g, a))
        for seed in JUDGE_PASSES:
            v, r = parse_judge_verdict(final_text(req(
                'completion', dict(BASE, prompt=jp, seed=seed, temperature=.2, top_p=.9))))
            assert v == expected and r, f'JUDGE_CAL case {i} seed {seed}'
    save(folder / 'calibration.json', dict(status='PASS', thinking=False, code=sha(__file__)))


# ------------------------------------------------------------------ reader

def _prepare_natives(ctx_items):
    """Template all arm prompts through the live server, asserting PF6 identity for arm A."""
    nf = OUT / 'natives.json'
    natives = load(nf) if nf.exists() else {}
    dirty = 0
    for it in ctx_items:
        for key, text, expected in (('a_native', it['a_prompt'], it['a_native_sha']),
                                    ('b_native', it['b_prompt'], None)):
            qk = f'{it["qid"]}|{key}'
            if qk in natives:
                continue
            p = native(text)
            if expected is not None:
                assert sha_text(p) == expected, f'arm-A prompt drift {it["qid"]}'
            else:
                it['b_native_sha'] = sha_text(p)
                natives[f'{it["qid"]}|b_native_sha'] = sha_text(p)
            natives[qk] = p
            dirty += 1
            if dirty % 20 == 0:
                save(nf, natives)
    save(nf, natives)
    for it in ctx_items:
        it['a_native'] = natives[f'{it["qid"]}|a_native']
        it['b_native'] = natives[f'{it["qid"]}|b_native']
        it.setdefault('b_native_sha', natives[f'{it["qid"]}|b_native_sha'])


def _reader_calls(items, folder, limit=None):
    durations = []
    todo = items if limit is None else items[:limit]
    for i, it in enumerate(todo):
        for arm in ARMS:
            path = folder / f'{arm}__{fname(it["qid"])}.json'
            if path.exists():
                try:
                    json.loads(path.read_text(encoding='utf-8'))
                    continue
                except Exception:
                    path.unlink()
            use_b = arm in ('B_ANCHOR',) or (arm == 'C_GATE' and it['gate'] == 'anchor')
            prompt = it['b_native'] if use_b else it['a_native']
            p_sha = it['b_native_sha'] if use_b else it['a_native_sha']
            assert sha_text(prompt) == p_sha
            pending = folder / (path.stem + '.pending.json')
            save(pending, dict(arm=arm, qid=it['qid'], started=time.time()))
            start = time.time()
            try:
                response = req('completion', dict(BASE, prompt=prompt))
                elapsed = time.time() - start
                save(path, dict(arm=arm, qid=it['qid'], kind=it['kind'], gate=it['gate'],
                                response=response, seconds=round(elapsed, 2),
                                prompt_sha256=p_sha,
                                nonempty=final_text(response) != '',
                                stop_type=response.get('stop_type'),
                                tokens_in=response.get('tokens_evaluated'),
                                tokens_out=response.get('tokens_predicted')))
                pending.unlink(missing_ok=True)
                durations.append(elapsed)
                print(f'{arm} {i + 1}/{len(todo)} {elapsed:.1f}s', flush=True)
            except Exception as e:
                save(folder / (path.stem + '.failed.json'), dict(arm=arm, qid=it['qid'],
                                                                 error=repr(e),
                                                                 traceback=traceback.format_exc()))
                pending.unlink(missing_ok=True)
                print(f'FAILED {arm} {it["qid"]}: {e!r}', flush=True)
    return durations


def _run_reader(limit):
    ctx = load(OUT / 'contexts.json')
    folder = OUT / 'reader'
    process = launch(folder)
    try:
        if not (folder / 'calibration.json').exists():
            calibrate(folder)
        _prepare_natives(ctx['items'])
        items = sorted(ctx['items'], key=lambda x: (x['kind'] != 'primary', x['qid']))
        durations = _reader_calls(items, folder, limit)
        if limit is not None:
            mean = statistics.mean(durations) if durations else 0.0
            remaining = len(items) * len(ARMS) - len(durations)
            save(OUT / 'pilot.json', dict(status='PASS', calls=len(durations),
                                          mean_seconds=round(mean, 2),
                                          estimated_remaining_hours=round(mean * remaining / 3600, 2)))
            commit([OUT / 'pilot.json'],
                   'AF-READ-001 pilot: calibration gates passed, 10x3 answers captured, wall-clock estimate frozen')
        else:
            hashes = {p.name: sha(p) for p in folder.glob('*.json')
                      if '__' in p.stem and '.pending' not in p.name and '.failed' not in p.name}
            n_expected = len(ctx['items']) * len(ARMS)
            save(OUT / 'reader_complete.json', dict(status='PASS' if len(hashes) == n_expected
                                                    else 'INCOMPLETE',
                                                    calls=len(hashes), expected=n_expected,
                                                    hashes=hashes))
            if len(hashes) == n_expected:
                commit([OUT / 'reader_complete.json'],
                       'AF-READ-001 reader answers frozen and committed before gold opens')
            else:
                print(f'INCOMPLETE: {len(hashes)}/{n_expected} — re-run full to resume')
    finally:
        stop(process, folder)


def pilot():
    _run_reader(PILOT_N)


def full():
    _run_reader(None)
    print('READERS DONE — next: judge phase (gold opens only now)')


# ------------------------------------------------------------------ judge

def judge():
    ctx = load(OUT / 'contexts.json')
    rc = load(OUT / 'reader_complete.json')
    assert rc['status'] == 'PASS', 'readers incomplete'
    gold = load(OUT / 'gold.json')
    kind = {it['qid']: it['kind'] for it in ctx['items']}
    qtext = {}
    for c in json.load(open(LOCOMO, encoding='utf-8')):
        for i, qa in enumerate(c['qa']):
            qtext[f"{c['sample_id']}:{i}"] = qa['question']
    answers = []
    for it in ctx['items']:
        for arm in ARMS:
            p = OUT / 'reader' / f'{arm}__{fname(it["qid"])}.json'
            rec = json.loads(p.read_text(encoding='utf-8'))
            answers.append(dict(comparison_key=it['qid'], arm=arm, replicate=0,
                                question=qtext[it['qid']], gold=gold[it['qid']],
                                answer=final_text(rec['response'])))
    surface, mapping = blinded_surface(answers)
    save(OUT / 'blind_surface.json', surface)
    save(OUT / 'blind_map.json', mapping)
    commit([OUT / 'blind_surface.json'],
           'AF-READ-001 blind evaluation surface frozen (gold opened only post-answers)')
    folder = OUT / 'judges'
    process = launch(folder)
    try:
        if not (OUT / 'reader' / 'calibration.json').exists():
            calibrate(OUT / 'reader')
        for i, x in enumerate(surface):
            qid = mapping[x['blind_id']]['comparison_key']
            passes = JUDGE_PASSES if kind[qid] == 'primary' else JUDGE_PASSES[:1]
            for seed in passes:
                path = folder / f'{x["blind_id"]}_{seed}.json'
                if path.exists():
                    continue
                jp = native(render_judge_prompt(x['question'], x['gold'], x['answer']))
                start = time.time()
                response = req('completion', dict(BASE, prompt=jp, seed=seed,
                                                  temperature=.2, top_p=.9))
                save(path, dict(blind_id=x['blind_id'], seed=seed, response=response,
                                seconds=round(time.time() - start, 2)))
            if i % 25 == 0:
                print(f'judge {i + 1}/{len(surface)}', flush=True)
    finally:
        stop(process, folder)
    save(OUT / 'judge_complete.json', dict(status='PASS',
                                           hashes={p.name: sha(p) for p in folder.glob('*.json')
                                                   if p.stem != 'calibration'}))
    commit([OUT / 'judge_complete.json'], 'AF-READ-001 judge votes frozen')


# ------------------------------------------------------------------ score

def score():
    sys.path.insert(0, str(ROOT / 'experiments/probes/unified_anchor'))
    from score_sample120 import mcnemar_exact
    ctx = load(OUT / 'contexts.json')
    surface = load(OUT / 'blind_surface.json')
    mapping = load(OUT / 'blind_map.json')
    meta = {it['qid']: it for it in ctx['items']}
    votes = {}
    for p in (OUT / 'judges').glob('*.json'):
        rec = json.loads(p.read_text(encoding='utf-8'))
        if 'blind_id' not in rec:
            continue
        v, _ = parse_judge_verdict(final_text(rec['response']))
        votes.setdefault(rec['blind_id'], []).append(v)
    correct = {}
    for x in surface:
        m = mapping[x['blind_id']]
        vs = votes.get(x['blind_id'], [])
        if vs:
            correct[(m['comparison_key'], m['arm'])] = int(sum(vs) * 2 > len(vs))

    def arm_correct(arm, kinds):
        return {q: correct[(q, arm)] for (q, a) in correct
                if a == arm and meta[q]['kind'] in kinds}
    ac = {arm: arm_correct(arm, ('primary',)) for arm in ARMS}

    def mcn(a, barm):
        ids = sorted(set(ac[a]) & set(ac[barm]))
        w = sum(1 for q in ids if ac[a][q] and not ac[barm][q])
        l = sum(1 for q in ids if not ac[a][q] and ac[barm][q])
        return dict(n=len(ids), wins=w, losses=l, net=w - l, p=round(mcnemar_exact(w, l), 5))
    summary = dict(
        plan='f75f590d',
        arm_correct_primary={arm: sum(ac[arm].values()) for arm in ARMS},
        arm_correct_descriptive={arm: sum(arm_correct(arm, ('descriptive',)).values())
                                 for arm in ARMS},
        mcnemar_C_vs_A=mcn('C_GATE', 'A_DEPLOYED'),
        mcnemar_B_vs_A=mcn('B_ANCHOR', 'A_DEPLOYED'),
        gate_counts=dict(anchor=sum(1 for q in ac['A_DEPLOYED'] if meta[q]['gate'] == 'anchor'),
                         fallback=sum(1 for q in ac['A_DEPLOYED'] if meta[q]['gate'] == 'fallback')),
        by_category={str(c): {arm: sum(ac[arm][q] for q in ac[arm] if meta[q]['cat'] == c)
                              for arm in ARMS}
                     for c in sorted({meta[q]['cat'] for q in ac['A_DEPLOYED']})})
    # PF9 assertion: every C-vs-A discordance is carried by an anchored item
    bad = [q for q in set(ac['C_GATE']) & set(ac['A_DEPLOYED'])
           if ac['C_GATE'][q] != ac['A_DEPLOYED'][q] and meta[q]['gate'] == 'fallback']
    summary['pf9_fallback_discordances'] = len(bad)
    tokens = {arm: [] for arm in ARMS}
    for it in ctx['items']:
        for arm in ARMS:
            p = OUT / 'reader' / f'{arm}__{fname(it["qid"])}.json'
            if p.exists():
                tokens[arm].append(json.loads(p.read_text(encoding='utf-8')).get('tokens_in') or 0)
    summary['budget'] = {
        arm: dict(median_prompt_chars=statistics.median(
            [len(i['a_prompt']) if arm != 'B_ANCHOR' else i['block_chars'] for i in ctx['items']]),
            mean_tokens_in=round(statistics.mean(tokens[arm]), 1) if tokens[arm] else None)
        for arm in ARMS}
    taus = {}
    for t in (0.05, 0.1, 0.2, 0.4, 0.6):
        w = l = 0
        for q in sorted(set(ac['A_DEPLOYED']) & set(ac['B_ANCHOR'])):
            chosen = ac['B_ANCHOR'][q] if meta[q]['pnull'] < t else ac['A_DEPLOYED'][q]
            w += int(chosen and not ac['A_DEPLOYED'][q])
            l += int(not chosen and ac['A_DEPLOYED'][q])
        taus[str(t)] = w - l
    summary['tau_sweep_net_vs_A'] = taus
    c = summary['mcnemar_C_vs_A']
    summary['disposition'] = dict(WORKS=c['net'] >= 8 and c['p'] < .05, SIGNAL=c['net'] >= 4)
    ev = {}
    for con in json.load(open(LOCOMO, encoding='utf-8')):
        for j, qa in enumerate(con['qa']):
            ev[f"{con['sample_id']}:{j}"] = set(qa.get('evidence', []))
    pr = [it for it in ctx['items'] if it['kind'] == 'primary']

    def sacc(arm, rows):
        xs = [correct[(it['qid'], arm)] for it in rows if (it['qid'], arm) in correct]
        return f'{sum(xs)}/{len(xs)}'
    strat = {}
    for name, rows in (
            ('anchor_in_evidence', [i for i in pr if i['anchor_turn'] in ev.get(i['qid'], set())]),
            ('anchor_off_evidence', [i for i in pr if i['anchor_turn'] not in ev.get(i['qid'], set())]),
            ('gated_to_anchor', [i for i in pr if i['gate'] == 'anchor']),
            ('multi_evidence', [i for i in pr if len(ev.get(i['qid'], set())) >= 2])):
        strat[name] = dict(n=len(rows), **{arm: sacc(arm, rows) for arm in ARMS})
    gated_rows = [i for i in pr if i['gate'] == 'anchor']
    gw = sum(1 for i in gated_rows if correct[(i['qid'], 'C_GATE')] and not correct[(i['qid'], 'A_DEPLOYED')])
    gl = sum(1 for i in gated_rows if not correct[(i['qid'], 'C_GATE')] and correct[(i['qid'], 'A_DEPLOYED')])
    summary['guardrail_diagnostic'] = strat
    summary['mcnemar_C_vs_A_gated'] = dict(n=len(gated_rows), wins=gw, losses=gl, net=gw - gl,
                                           p=round(mcnemar_exact(gw, gl), 5))
    save(OUT / 'results.json', dict(summary=summary))
    commit([OUT / 'results.json'], 'AF-READ-001 scored results')
    print(json.dumps(summary, indent=1))


def status():
    folder = OUT / 'reader'
    done = len([p for p in folder.glob('*.json') if '__' in p.stem
                and '.pending' not in p.name and '.failed' not in p.name]) if folder.exists() else 0
    print(json.dumps(dict(
        reader_files=done, targets=240 * len(ARMS),
        failed=len(list(folder.glob('*.failed.json'))) if folder.exists() else 0,
        pending=len(list(folder.glob('*.pending.json'))) if folder.exists() else 0,
        judge_files=len(list((OUT / 'judges').glob('*.json'))) if (OUT / 'judges').exists() else 0)))


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    {'build': build, 'pilot': pilot, 'full': full, 'judge': judge,
     'score': score, 'status': status}[sys.argv[1]]()

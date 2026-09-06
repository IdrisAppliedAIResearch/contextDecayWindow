"""Fixed competing-update histories and offline readiness; no reader calls."""
import concurrent.futures
import copy
import hashlib
import html
import json
import random
import re
import time
from pathlib import Path

import numpy as np
from corpus import VALUES, identity, make_session
from mechanism import build
from prepare_dev import init, emb
from analysis.hh001_prompt import render_reader_prompt
from episodic._render import render_stm_payload

P = Path(__file__).resolve().parent / 'artifacts/amendment003/development'


def save(name, value):
    path = P / name
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def generate(seed):
    source, base_labels, _ = make_session(seed)
    histories, labels, ledgers = [], {}, []
    for index, query in enumerate(source['probes']):
        label = copy.deepcopy(base_labels[query['id']])
        meta = label['rationale']
        subject = meta['subject']
        marker = f'"{subject}"'
        updates = [e['turn_number'] for e in source['episodes']
                   if e['user_message'].splitlines()[0].startswith(
                       f'The equipment supplier for {marker}' if query['type'] == 'absent'
                       else f'The delivery location for {marker} is now')]
        early = min(updates)
        keep = {early, meta['target'], meta['near'], meta['anchor'], meta['later']}
        assert len(keep) == 5
        rng = random.Random(seed * 10 + index)
        episodes = []
        idmap = {}
        for old in source['episodes']:
            episode = copy.deepcopy(old)
            turn = episode['turn_number']
            if turn <= 108 and turn not in keep:
                _, note = episode['user_message'].split('\n', 1)
                if query['type'] == 'absent':
                    head = f'The equipment supplier for {marker} had a routine review. No delivery location is specified in this record.'
                elif turn < meta['target']:
                    head = f'The delivery location for {marker} is now the {rng.choice(VALUES)}. This replaces its previous location.'
                else:
                    head = f'The team reviewed delivery records for {marker}. This review made no change to its delivery location.'
                episode['user_message'] = head + '\n' + note
                episode['id'] = identity({k: v for k, v in episode.items() if k != 'id'})
            if turn > 108 or turn in keep:
                assert episode == old
            idmap[old['id']] = episode['id']
            episodes.append(episode)
        label['gold_ids'] = [idmap[x] for x in label['gold_ids']]
        pattern = re.compile(r'^The delivery location for "' + re.escape(subject) + r'" is now the (\w+)\.')
        parsed = [(e['turn_number'], m.group(1)) for e in episodes
                  if (m := pattern.match(e['user_message']))]
        eligible = [x for x in parsed if query['type'] == 'latest' or x[0] < meta['anchor']]
        assert (max(eligible)[1] if eligible else "I don't know") == label['answer']
        by_id = {e['id']: e for e in episodes}
        assert all(by_id[x]['turn_number'] < 109 for x in label['gold_ids'])
        # Independent ledger expectation: extra updates precede target; the
        # retained target/later must still determine the query's active value.
        if query['type'] != 'absent':
            expected_turn = meta['later'] if query['type'] == 'latest' else meta['target']
            assert max(eligible)[0] == expected_turn
        history_id = f"session-{seed}-{query['type']}"
        histories.append(dict(id=history_id, group=f'session-{seed}', episodes=episodes, probes=[query]))
        labels[query['id']] = label
        ledgers.extend(dict(history=history_id, subject=subject, turn=t, value=v, effective=True) for t, v in parsed)
    return histories, labels, ledgers


def main():
    assert not P.exists(), 'Never overwrite an existing capture.'
    import subprocess
    root = Path(__file__).resolve().parents[2]
    for folder, prefix in [('contextDecayWindow-study-E-control', '05ef90e2'), ('contextDecayWindow-study-D-control', '5ebda1ef')]:
        folder = root.parent / folder
        assert subprocess.check_output(['git', '-C', str(folder), 'rev-parse', 'HEAD'], text=True).strip().startswith(prefix)
        assert not subprocess.check_output(['git', '-C', str(folder), 'status', '--porcelain'], text=True).strip()
    histories, labels, ledger = [], {}, []
    for seed in range(93201, 93205):
        hs, ls, lg = generate(seed)
        histories.extend(hs); labels.update(ls); ledger.extend(lg)
    assert len(histories) == len(labels) == 24 and all(len(h['episodes']) == 140 for h in histories)
    P.mkdir(parents=True)
    save('sources.json', histories); save('labels.json', labels); save('ledger.json', ledger)
    save('source_gate.json', dict(status='PASS', groups=4, histories=24, sources=3360,
                                 references_checked=24, all_required_before_109=True,
                                 retained_event_heads_and_continuity_unchanged=True))
    texts = sorted({e['user_message'] + '\n' + e['assistant_message'] for h in histories for e in h['episodes']}
                   | {q['query'] for h in histories for q in h['probes']})
    started = time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=8, initializer=init) as pool:
        results = list(pool.map(emb, texts))
    assert len({r[2] for r in results}) == 1
    array = np.vstack([r[1] for r in results])
    np.savez(P / 'vectors.npz', vectors=array)
    save('vector_manifest.json', dict(texts=texts, file_sha256=hashlib.sha256((P / 'vectors.npz').read_bytes()).hexdigest(),
         sentinel=results[0][2], calls=len(texts)+8, pids=sorted({r[3] for r in results}),
         cpu_seconds=sum(r[4] for r in results), wall_seconds=time.monotonic()-started))
    vectors = dict(zip(texts, array)); rows, prompts = [], []
    for history in histories:
        episodes = [dict(e, embedding=vectors[e['user_message']+'\n'+e['assistant_message']]) for e in history['episodes']]
        by_id = {e['id']: e for e in episodes}
        query = history['probes'][0]
        c0, c1, trace = build(episodes, query['query'], vectors[query['query']])
        assert (c0, c1) == build(episodes, query['query'], vectors[query['query']])[:2]
        label = labels[query['id']]
        def available(block):
            return any(all(html.escape(text, quote=False) in block for text in group)
                       for group in label['sufficient_sets'])
        oracle = render_stm_payload([], [by_id[x] for x in label['gold_ids']]) if label['gold_ids'] else ''
        for arm, block in [('C0', c0), ('C1', c1), ('ORACLE', oracle), ('NULL', '')]:
            prompts.append(dict(id=query['id'], session=history['group'], history=history['id'], type=query['type'],
                                arm=arm, query=query['query'], reference=label['answer'],
                                prompt=render_reader_prompt(query['query'], block)+'\n<think>\n</think>\n'))
        rows.append(dict(session=history['group'], history=history['id'], type=query['type'], changed=c0!=c1,
                         C0=available(c0), C1=available(c1), trace=trace))
    save('prompts.json', prompts); save('rows.json', rows)
    primary = [r for r in rows if r['type'] not in ['latest', 'absent']]
    active = [r for r in rows if r['type'] != 'latest']
    unchanged_latest = all(not r['changed'] for r in rows if r['type'] == 'latest')
    active_ok = all(r['changed'] and not r['trace']['unchanged'] for r in active)
    complete = sum(r['C0'] for r in primary)
    ready = 0 < complete < 16 and unchanged_latest and active_ok
    gate = dict(status='PASS' if ready else 'INSTRUMENT_NOT_READY', C0_primary_complete=complete,
                C1_primary_complete=sum(r['C1'] for r in primary), primary_count=16,
                non_before_identical=unchanged_latest, all_before_and_absence_active=active_ok,
                eligible_counts=[len(r['trace']['route']['eligible']) for r in active],
                complete_evidence_gains=sum(not r['C0'] and r['C1'] for r in primary),
                complete_evidence_losses=sum(r['C0'] and not r['C1'] for r in primary), reader_authorized=ready,
                no_treatment_gain_gate=True)
    save('readiness_gate.json', gate)
    save('manifest.json', {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(P.iterdir()) if f.is_file()})
    print(json.dumps(gate), flush=True)


if __name__ == '__main__':
    main()

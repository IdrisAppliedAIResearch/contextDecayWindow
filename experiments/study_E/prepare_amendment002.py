"""Run the fixed Amendment 002 variant; never overwrite an existing capture."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

import prepare_dev
from corpus import make_session as original
from corpus_shared_dispatch import make_session

P = Path(__file__).resolve().parent / 'artifacts/amendment002/development'


def save(name, value):
    path = P / name
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def verify_source(seed):
    session, labels, ledger = make_session(seed)
    base, base_labels, base_ledger = original(seed)
    assert ledger == base_ledger
    assert session['probes'] == base['probes']
    assert len(session['episodes']) == 140
    for episode, old in zip(session['episodes'], base['episodes']):
        assert episode['user_message'].splitlines()[0] == old['user_message'].splitlines()[0]
        assert episode['assistant_message'] == old['assistant_message']
        if episode['turn_number'] > 108:
            assert episode == old
        else:
            assert episode['user_message'].startswith(old['user_message'] + '\nThe dispatch audit for ')
    by_id = {e['id']: e for e in session['episodes']}
    for query in session['probes']:
        label = labels[query['id']]
        meta = label['rationale']
        pattern = re.compile(r'The delivery location for "' + re.escape(meta['subject']) + r'" is now the (\w+)\.')
        changes = [(e['turn_number'], match.group(1)) for e in session['episodes']
                   if (match := pattern.search(e['user_message']))
                   and (query['type'] == 'latest' or e['turn_number'] < meta['anchor'])]
        expected = max(changes)[1] if changes else "I don't know"
        assert expected == label['answer'] == base_labels[query['id']]['answer']
        assert all(by_id[x]['turn_number'] < 109 for x in label['gold_ids'])
    return dict(seed=seed, sources=140, questions=6, gold_source_check=True,
                neutral_only_revision=True, continuity_unchanged=True)


def main():
    assert not P.exists(), 'Preserve all prior captures; do not rerun into this directory.'
    root = Path(__file__).resolve().parents[2]
    for folder, prefix in [('contextDecayWindow-study-E-control', '05ef90e2'),
                           ('contextDecayWindow-study-D-control', '5ebda1ef')]:
        folder = root.parent / folder
        assert subprocess.check_output(['git', '-C', str(folder), 'rev-parse', 'HEAD'], text=True).strip().startswith(prefix)
        assert not subprocess.check_output(['git', '-C', str(folder), 'status', '--porcelain'], text=True).strip()
    checks = [verify_source(seed) for seed in range(93101, 93105)]
    # Reuse the already tested single-text embedding/prompt preparation path.
    # Its fixed 93001..93004 loop maps explicitly to this amendment's new seeds.
    prepare_dev.P = P
    prepare_dev.make_session = lambda seed: make_session(seed + 100)
    prepare_dev.main()
    save('source_gate.json', dict(status='PASS', checks=checks))
    rows = json.loads((P / 'rows.json').read_text())
    primary = [r for r in rows if r['type'] in ['straight', 'irrelevant', 'future', 'proposal']]
    active = [r for r in rows if r['type'] != 'latest']
    prior_rows = json.loads((P.parents[1] / 'part1/development/rows.json').read_text())
    current_eligible = [len(r['trace']['route']['eligible']) for r in active]
    prior_eligible = [len(r['trace']['route']['eligible']) for r in prior_rows if r['type'] != 'latest']
    invariant = all(not r['changed'] for r in rows if r['type'] == 'latest')
    active_check = all(r['changed'] and not r['trace']['unchanged'] for r in active)
    n_complete = sum(r['C0'] for r in primary)
    ready = invariant and active_check and 0 < n_complete < len(primary)
    gate = dict(status='PASS' if ready else 'INSTRUMENT_NOT_READY',
                C0_primary_complete=n_complete, C1_primary_complete=sum(r['C1'] for r in primary),
                primary_count=len(primary), non_before_identical=invariant,
                all_before_and_absence_active=active_check,
                eligible_counts=current_eligible, prior_eligible_counts=prior_eligible,
                complete_evidence_gains=sum(not r['C0'] and r['C1'] for r in primary),
                complete_evidence_losses=sum(r['C0'] and not r['C1'] for r in primary),
                reader_authorized=ready, no_treatment_gain_gate=True)
    save('readiness_gate.json', gate)
    save('manifest.json', {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in sorted(P.iterdir()) if path.is_file()})
    print(json.dumps(gate))


if __name__ == '__main__':
    main()

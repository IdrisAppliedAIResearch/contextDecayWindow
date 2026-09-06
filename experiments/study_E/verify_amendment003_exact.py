"""Correct the inherited text-only surrogate using exact temporal carriers."""
import hashlib
import html
import json
from pathlib import Path

P = Path(__file__).resolve().parent / 'artifacts/amendment003/development'


def read(name):
    return json.loads((P/name).read_text(encoding='utf-8'))


def save(name, value):
    assert not (P/name).exists()
    (P/name).write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')


def main():
    labels = read('labels.json')
    prompts = {(r['history'], r['arm']): r for r in read('prompts.json')}
    rows = read('rows.json')
    mismatches = []
    for row in rows:
        trace = row['trace']
        for arm, selected in [('C0', trace['prior']['selected_ids']),
                              ('C1', trace.get('selected_ids', trace['prior']['selected_ids']))]:
            prompt = prompts[(row['history'], arm)]
            label = labels[prompt['id']]
            required = set(label['gold_ids'])
            exact = bool(required) and required.issubset(selected)
            if exact:
                assert any(all(html.escape(s, quote=False) in prompt['prompt'] for s in group)
                           for group in label['sufficient_sets'])
            if exact != row[arm]:
                mismatches.append(dict(history=row['history'], arm=arm, text_only=row[arm], exact=exact))
            row[arm] = exact
    primary = [r for r in rows if r['type'] not in ['latest','absent']]
    active = [r for r in rows if r['type'] != 'latest']
    complete = sum(r['C0'] for r in primary)
    unchanged = all(not r['changed'] for r in rows if r['type']=='latest')
    active_ok = all(r['changed'] and not r['trace']['unchanged'] for r in active)
    ready = 0 < complete < 16 and unchanged and active_ok
    gate = dict(status='PASS' if ready else 'INSTRUMENT_NOT_READY', measurement='exact required source identities in final pack',
                C0_primary_complete=complete, C1_primary_complete=sum(r['C1'] for r in primary), primary_count=16,
                non_before_identical=unchanged, all_before_and_absence_active=active_ok,
                complete_evidence_gains=sum(not r['C0'] and r['C1'] for r in primary),
                complete_evidence_losses=sum(r['C0'] and not r['C1'] for r in primary),
                reader_authorized=ready, no_treatment_gain_gate=True, text_only_mismatches=mismatches,
                supersedes_for_authorization='readiness_gate.json (text-only surrogate invalid)',
                source_sha256=hashlib.sha256((P/'sources.json').read_bytes()).hexdigest(),
                prompts_sha256=hashlib.sha256((P/'prompts.json').read_bytes()).hexdigest())
    save('rows_exact.json', rows)
    save('readiness_gate_exact.json', gate)
    print(json.dumps(gate), flush=True)


if __name__ == '__main__':
    main()

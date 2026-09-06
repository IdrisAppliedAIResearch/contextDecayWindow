"""Persist authorized blind judgments; analyze only after their commit."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

P = Path(__file__).resolve().parent / 'artifacts/part1/reader'
ROOT = Path(__file__).resolve().parents[2]

def read(name):
    return json.loads((P / name).read_text(encoding='utf-8'))

def digest(name):
    return hashlib.sha256((P / name).read_bytes()).hexdigest()

def save(name, value):
    path = P / name
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')

def committed(name):
    path = P / name
    blob = subprocess.check_output(['git', 'show', 'HEAD:' + path.relative_to(ROOT).as_posix()], cwd=ROOT)
    assert blob.replace(b'\r\n', b'\n') == path.read_bytes().replace(b'\r\n', b'\n')

if sys.argv[1] == 'resolve':
    committed('scores.json')
    committed('pending_adjudication.json')
    pending = read('pending_adjudication.json')
    # Explicit manual decisions, in the committed blind packet's order.
    decisions = [
        ('The depot.', 'Explicit final depot matches reference; explanation is not used as the answer.', False),
        ('Answer: the depot', 'Explicit final depot matches reference.', False),
        ('Answer: The depot.', 'Final depot explicitly supersedes the opening hangar; credit final answer, flag initial contradiction.', True),
        ('Answer: The office', 'Final office explicitly corrects the opening depot assertion.', True),
        ('Answer: The hangar', 'Final hangar explicitly corrects the opening depot assertion.', True),
        ('Answer: The laboratory.', 'Explicit final laboratory matches reference.', False),
        ('Answer: The studio.', 'Explicit final studio matches reference.', False),
        ('I don know.', 'Unambiguous abstention with a missing t/apostrophe; semantically correct, not exact-format compliant.', False),
        ('Answer: The office.', 'Final office explicitly corrects the opening studio assertion.', True),
        ('Answer: the hangar', 'Final hangar explicitly corrects the opening depot assertion.', True),
        ('The laboratory', 'Explicit final laboratory matches reference.', False),
        ('The laboratory', 'Explicit final laboratory matches reference.', False),
        ('Answer: The studio', 'Explicit final studio matches reference.', False),
        ('Answer: the laboratory', 'Explicit final laboratory matches reference.', False),
        ('Answer: the laboratory', 'Explicit final laboratory matches reference.', False),
        ('**Answer:** The office.', 'Explicit final office corrects the opening studio assertion; final commitment is distinct from explanatory steps.', True),
        ('Answer: The depot.', 'Final depot explicitly corrects the opening hangar assertion.', True),
    ]
    assert len(pending) == len(decisions) == 17
    judgments = []
    for item, (evidence, rationale, corrected) in zip(pending, decisions):
        assert item['response'].rstrip().endswith(evidence)
        judgments.append(dict(blind_id=item['blind_id'], score=1, evidence=evidence,
                              rationale=rationale, initial_wrong_assertion=corrected,
                              reviewer='single agent; user-authorized; no human audit'))
    by_id = {row['blind_id']: row for row in judgments}
    resolved = []
    for row in read('scores.json'):
        if row['score'] is None:
            resolved.append(by_id[row['blind_id']])
        else:
            resolved.append(dict(row, initial_wrong_assertion=False, reviewer='frozen mechanical parser'))
    assert len(resolved) == 32 and all(row['score'] in (0, 1) for row in resolved)
    save('agent_adjudications.json', judgments)
    save('scores_resolved.json', resolved)
    save('scoring_gate_resolved.json', dict(status='PASS_WITH_SCORING_DEVIATION', count=32,
         pending=0, agent_adjudications=17, scores_sha256=digest('scores_resolved.json'),
         amendment='AMENDMENT_001_development_agent_adjudication.md'))
    print('17 adjudications persisted; no arm mapping opened.')
elif sys.argv[1] == 'analyze':
    for name in ['complete.json', 'scores_resolved.json', 'scoring_gate_resolved.json', 'agent_adjudications.json']:
        committed(name)
    gate = read('scoring_gate_resolved.json')
    assert gate['status'] == 'PASS_WITH_SCORING_DEVIATION' and gate['pending'] == 0
    assert digest('scores_resolved.json') == gate['scores_sha256']
    assert digest('responses.jsonl') == read('complete.json')['responses_sha256']
    scores = {r['blind_id']: r for r in read('scores_resolved.json')}
    mapping = read('mapping.json')
    out = {}
    for kind in ['straight', 'irrelevant', 'future', 'proposal', 'latest', 'absent']:
        out[kind] = {}
        for arm in ['C0', 'C1']:
            rows = [scores[r['blind_id']] for r in mapping if r['type'] == kind and r['arm'] == arm]
            if rows:
                out[kind][arm] = dict(n=len(rows), correct=sum(r['score'] for r in rows),
                                     initial_wrong_assertions=sum(r['initial_wrong_assertion'] for r in rows))
    primary = {}
    for arm in ['C0', 'C1']:
        values = [out[k][arm] for k in ['straight', 'irrelevant', 'future', 'proposal']]
        primary[arm] = {key: sum(v[key] for v in values) for key in ['n', 'correct', 'initial_wrong_assertions']}
    result = dict(status='DEVELOPMENT_ONLY', by_type=out, primary=primary,
                  scoring='User-authorized single-agent exception adjudication; no human audit',
                  confirmation='NOT REGISTERED OR RUN; apply Part 1 reader gate')
    save('descriptive_result_resolved.json', result)
    print(json.dumps(result, indent=2))
else:
    raise ValueError('Expected resolve or analyze')

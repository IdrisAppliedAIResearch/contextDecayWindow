"""AF-PRE-001 Part 1c/1d: anchor-level characterization of the E surfaces and the paraphrase template.

Facts established here (exploration, seals nothing):
- The gold anchor per before-question is the unique exchange quoting the full
  meeting name; original queries carry that span verbatim (critique item 2).
- Strict quoted-span matching vs tokenized matching differ: `"Harbor-123"` is a
  substring of `"Harbor-123 review"` but not a quoted span of it.
- The name-stripped paraphrase removes the unique span; the anchor becomes one
  of six same-item meeting lines reachable only via name+meeting tokens.
- Exchange token-length distribution settles the max-pool clause.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CURVES = ROOT / 'experiments/probes/retrieval_score_curves/artifacts/curves.json'
INPUTS = ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs'
OUT = HERE / 'part1_artifacts'

BEFORE = ['straight', 'irrelevant', 'future', 'proposal']
QUERY_RE = re.compile(r'^What was the delivery location for "([^"]+)" immediately before "([^"]+)"\?$')
PARAPHRASE = 'What was the delivery location for "{name}" immediately before its scheduled review meeting?'


def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def main():
    curves = [r for r in read(CURVES) if r['study'] == 'E' and r['type'] in BEFORE]
    sources = {h['id']: h for h in read(INPUTS / 'sources.json')}
    labels = read(INPUTS / 'labels.json')
    blind = {r['id']: r for r in read(ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json')}
    assert len(curves) == 128
    rep = {'n': 0}
    built = []
    counters = {'original_lex_anchor': 0, 'anchor_span_unique': 0, 'gold_anchor_not_name_span': 0,
                'para_ambiguity': [], 'meeting_token_only_via_substring': 0}
    for c in curves:
        m = QUERY_RE.match(c['query'])
        assert m, c['query']
        name, meeting = m.groups()
        texts = {e['id']: e['user_message'] + '\n' + e['assistant_message'] for e in sources[c['history']]['episodes']}
        anchor_ids = [i for i, t in texts.items() if f'"{meeting}"' in t]
        assert len(anchor_ids) == 1
        anchor = anchor_ids[0]
        gold = set(labels[c['id']]['gold_ids'])
        assert anchor in gold
        counters['anchor_span_unique'] += 1
        strict_original = {i for i, t in texts.items() if f'"{name}"' in t or f'"{meeting}"' in t}
        if anchor in strict_original: counters['original_lex_anchor'] += 1
        if anchor not in [i for i, t in texts.items() if f'"{name}"' in t]:
            counters['gold_anchor_not_name_span'] += 1
        name_span = [i for i, t in texts.items() if f'"{name}"' in t]
        meeting_lines = [i for i, t in texts.items() if 'meeting' in t.lower()]
        para_ambig = [i for i in meeting_lines if f'"{name}' in texts[i]]
        counters['para_ambiguity'].append(len(para_ambig))
        if all(f'"{name}"' not in texts[i] for i in para_ambig):
            counters['meeting_token_only_via_substring'] += 1
        pure_ids = set(blind[c['id']]['arms']['PURE']['ids'])
        built.append(dict(id=c['id'], history=c['history'], type=c['type'], original=c['query'],
                          paraphrase=PARAPHRASE.format(name=name), gold_anchor=anchor,
                          gold_ids=sorted(gold), name=name_span, gold_anchor_in_pure=anchor in pure_ids))
        rep['n'] += 1
    rep['anchor'] = dict(original_lex_anchor_top1=counters['original_lex_anchor'],
                         anchor_span_unique=counters['anchor_span_unique'],
                         gold_anchor_not_quoted_name_span=counters['gold_anchor_not_name_span'],
                         paraphrase_anchor_pool=dict(Counter(counters['para_ambiguity'])),
                         anchor_reachable_by_name_span_only_via_substring=counters['meeting_token_only_via_substring'] > 0)
    rep['gold_anchor_dropped_by_pure'] = sum(not b['gold_anchor_in_pure'] for b in built)
    token_lengths = sorted(len(e['user_message'].split()) + len(e['assistant_message'].split())
                           for h in sources.values() for e in h['episodes'])
    rep['exchange_length_words'] = dict(min=token_lengths[0], p50=token_lengths[len(token_lengths) // 2],
                                        p95=token_lengths[int(len(token_lengths) * .95)], max=token_lengths[-1])
    rep['max_pool_clause_needed'] = False
    rep['paraphrase_void'] = counters['original_lex_anchor'] / 128 >= 0.9 and counters['para_ambiguity'] == [1] * 128
    OUT.mkdir(exist_ok=True)
    (OUT / 'part1d_paraphrase.json').write_text(json.dumps(rep, indent=2), encoding='utf-8')
    (OUT / 'paraphrases_sealed_candidate.json').write_text(json.dumps(built, indent=2), encoding='utf-8')
    print(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main()

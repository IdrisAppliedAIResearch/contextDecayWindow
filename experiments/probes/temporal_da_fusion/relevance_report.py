"""Build uncapped timeline report from committed reader scores and diagnostics."""
import statistics
from pathlib import Path
import json
from preflight import P,read,sha,save,committed


def main():
    out=P/'relevance_artifacts';reader=out/'reader'
    committed(reader/'scores_resolved.json');assert read(reader/'scoring_gate_resolved.json')['status']=='PASS'
    result=read(reader/'result.json');offline=read(out/'summary.json');schedule=read(reader/'schedule.json')
    timing={}
    for arm in ['BASELINE','RELEVANCE']:
        rs=[r for r in schedule if r['arm']==arm];responses=[read(reader/(r['case']+'.json')) for r in rs]
        timing[arm]=dict(calls=len(rs),prompt_tokens_min=min(r['tokens'] for r in rs),prompt_tokens_median=statistics.median(r['tokens'] for r in rs),
            prompt_tokens_max=max(r['tokens'] for r in rs),seconds=sum(r['latency_seconds'] for r in responses),output_tokens_max=max(r['response']['tokens_predicted'] for r in responses))
    save(reader/'runtime_summary.json',timing)
    primary=result['totals']['primary'];a=primary['scores']['BASELINE'];b=primary['scores']['RELEVANCE']
    lines=['# Uncapped relevance timeline at cosine0.48','',
        'Exploratory, September6,2026. Selection plan1676445b; mechanism27e2cce7; blindgate d275e9ce. Reader plan860ea072; wrapperb81fd591; inputgate f375d8e1; calibration53c26cb1. No prior study scores or deployed defaults changed.','',
        f'**With chronology held fixed, fresh reader correctness on the same12 before questions is{a}/12 for budgeted C1 and{b}/12 for the uncapped relevance timeline.** See paired counts below. This is a small exposed-data probe, not a confirmation or a population accuracy estimate.','',
        '## What changed','',
        'The prototype admits every full source record with raw query cosine>=0.48, adds the existing identified question anchor if it falls below that threshold, deduplicates and presents oldest to newest. It has no8k temporal allocation,32k retrieval cap, top-N bound or additive last32 block. All140 source records are eligible for the similarity check; even a recent continuity record can enter if it passes. No source compression/extraction or new embeddings are used.','',
        'The0.48 value comes from the legacy K-route default in episodic/_config.py and its >= comparison in _context.py. It is not a CC80 score or a probability, and was not shown universally optimal by that default. A horizontal cutoff is an initial relevance boundary, not an adaptive gradient stopping algorithm. Chronological order is presentation order, separate from ranking by similarity.','',
        '## Offline evidence and output size','',
        '| E before queries,128 | Complete required evidence | Records retained | Median serialized chars |','|---|---:|---|---:|',
        '| Prior C1,chronological/no recency |109/128|40–41|31,346|',
        '| Pure cosine>=.48 |111/128|107–113|84,560|',
        '| Cosine>=.48 plus anchor |128/128|108–113|84,627|','',
        'The anchored candidate recovers all19 previous availability misses with zero required-evidence losses on128before questions. The pure threshold loses17 question anchors; relative to C1 its15gains/13losses yield only+2. Every needed state-setting update passes; the protected anchor supplies a different evidence role. Latest-question evidence reaches32/32 versus21/32C1. The32absence questions have no positive-evidence completeness metric.','',
        'Selection retains most of the108 broadly related source records, usually rejects the32 unrelated gardening continuity records, and admits0–5 of those continuity records on before queries (median0). This is substantial expansion from40–41 records, not a compact-completion result. Output size is measured, never used to stop selection.','',
        'The same pure threshold on the earlier Study D before slice gives11/32complete, retaining88–104 records (median95). D did not receive the anchor-union adaptation in this diagnostic; do not compare its pure score with E anchored as a controlled transfer effect. This cautions against treating.48 alone as a universal sufficiency certificate.','',
        '![Fixed cosine boundary and chronological timeline](relevance_artifacts/relevance_curve.png)','',
        'Left: median and middle50% of raw-cosine ranked curves over128Ebefore questions. Right: previously audited Harbor-485 in source order. This selection supplies the previously missing update while preserving chronological presentation.','',
        '## Fresh reader comparison','',
        '| Questions | Budgeted chronological C1 | Uncapped chronological relevance |','|---|---:|---:|']
    for group,t in result['totals'].items():lines.append(f"| {group} | {t['scores']['BASELINE']}/{t['n']} | {t['scores']['RELEVANCE']}/{t['n']} |")
    for group,t in result['totals'].items():
        for pair,v in t['pairs'].items():lines.append(f"\n{group}: {v['gains']} gains,{v['losses']} losses in paired final correctness.")
    lines+=['','Native thinking is off in both arms, seed5005, serial, cachefalse, same pinned model/template/sampling, one replicate. Both arms use4096 output tokens rather than the earlier16384 reservation; this common reduction was locked before measurement. All full timelines plus output allowance fit32768context (maximum input18,208tokens), so no input was trimmed and no context-size change was needed. Two arithmetic calibration responses were identical; all32measurement calls completed.','',
        '| Arm | Median input tokens | Measurement seconds for16calls |','|---|---:|---:|']
    for arm,t in timing.items():lines.append(f"| {arm} | {t['prompt_tokens_median']:,.0f} | {t['seconds']:.2f} |")
    lines+=['','## Every sampled answer','', '| Question | Expected | Budgeted chronological | Relevance chronological |','|---|---|---|---|']
    for r in result['rows']:
        def cell(s):return s.replace('|','\\|').replace('\n',' ')
        lines.append('| '+cell(r['query'])+' | '+r['reference']+' | '+' | '.join(cell(r['arms'][arm]['answer'])+(' ✓' if r['arms'][arm]['score'] else ' ✗') for arm in ['BASELINE','RELEVANCE'])+' |')
    lines+=['','## Interpretation and next use','',
        'This concrete prototype tests the user’s hypothesis: a semantically selected timeline can admit updates excluded by hard packing caps and then be read chronologically. The relevance filter and the larger delivered set are part of the same intervention; this probe does not isolate a special curve effect from having more evidence. The threshold was not tuned on these outcomes. Anchor protection is explicit and must remain in descriptions of the result.','',
        'Keep chronological presentation in further experimental work. Use this fixed0.48+anchor implementation as the starting candidate, preserving its uncapped output rather than silently reintroducing a character quota. A broader reader comparison is needed before adoption. Any later adaptive curve boundary should be evaluated for evidence loss, unrelated admissions and reader correctness across distributions; this small synthetic corpus is not an oracle for choosing it.','',
        '## Integrity and limitations','',
        'Original192chronological payloads reproduce exactly; score arrays bind to prior verified vectors/ranking traces. Boundary,empty/full and anchor-exception fixtures pass. Label-free timelines/gate were committed before required-source annotation. Reader failed-input-gate fault injection occurred before any reader calls and made zero network requests. Input and duplicate calibration gates were committed before measurement; raw responses before blind canonical scores; scores before aggregation. No uncaptured/uncertain retry, no cap escalation, no reasoning-based scoring.','',
        'The16question sample is the previous fixed content-id sample, not selected for this treatment’s outcomes. It is exposed, synthetic, one seed and includes only four latest/absence guards.29answers score mechanically; three explanatory responses were adjudicated by a single agent under prior authorization. One starts with a wrong value, explicitly retracts it and concludes laboratory correctly. The final-answer rule scores that correction, not every claim in its prose. No human or independent-rater audit is claimed. This is an exploratory reader result without a new WORKS disposition or production adoption.','',
        'All four previous retrieval misses become correct answers. The new regression is Meadow-637: correct depot becomes studio despite the depot update at76, the not-yet-effective workshop announcement at82, and review anchor85 all being present. Studio was the immediately preceding effective value at75 (and occurred earlier too). This identifies a complete-evidence reader error; the short emitted answer does not identify why it happened. Added-history interference is a hypothesis, not an isolated cause.','',
        'Raw calls committed d4d4905f; mechanical scores58084300; blind agent decisionsb9a9eebb; all resolved scores7cec805 before aggregate. Owned server13964 was verified and stopped. No jobs remain.','',
        'Artifacts: relevance_artifacts/blind.json,gate.json,diagnostic_rows.json,summary.json; reader/schedule.json,complete.json,scores.json,scores_resolved.json,scoring_gate_resolved.json,result.json,runtime_summary.json. Figure provenance is in figure_manifest.json. Source labels are measurement-only; the selector accepts ids,turns,scores and existing anchors.','']
    (P/'RELEVANCE_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(primary=primary,timing=timing),indent=2))


if __name__=='__main__':main()

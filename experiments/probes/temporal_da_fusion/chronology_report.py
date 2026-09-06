"""Compile verified reader and layout diagnostics after committed scores."""
import json
import statistics
from chronology import OUT,P,I,read,sha,save,committed,ARMS


def main():
    committed(OUT/'scores.json');assert read(OUT/'scoring_gate.json')['status']=='PASS'
    result=read(OUT/'result.json');contexts=read(OUT/'contexts.json');schedule=read(OUT/'schedule.json')
    labels=read(I/'labels.json');by={r['id']:r for r in contexts}
    extras={}
    for arm in ARMS:
        rs=[r for r in schedule if r['arm']==arm];captures=[read(OUT/(r['case']+'.json')) for r in rs]
        extras[arm]=dict(context_chars_median=statistics.median(len(r['contexts'][arm]) for r in contexts),
            context_words_median=statistics.median(len(r['contexts'][arm].split()) for r in contexts),
            prompt_tokens_median=statistics.median(r['tokens'] for r in rs),
            seconds=sum(r['latency_seconds'] for r in captures),
            output_tokens_total=sum(r['response']['tokens_predicted'] for r in captures))
    availability=[]
    for r in result['rows']:
        gold=set(labels[r['id']]['gold_ids']);complete=bool(gold) and gold.issubset(by[r['id']]['selected_ids'])
        availability.append(dict(id=r['id'],type=r['type'],applicable=bool(gold),complete=complete))
    save('layout_and_availability.json',dict(arms=extras,availability=availability))
    lines=['# Same retrieval, recency removed, chronological reader probe','',
        'Exploratory, September 6, 2026. Plan c9158936; code9ea35762; input gate5c6d3306; calibration618b85ab. Native thinking off; one fresh seed per arm;16 fixed questions;48 measurement calls plus two arithmetic calibration calls. No original study scores or deployed defaults changed.','',
        'All192 source contexts were checked offline. ORIGINAL exactly reproduces C1; NO_RECENT removes the additive32 exchanges; CHRONO_NO_RECENT sorts the same selected retrieved records oldest to newest after removal. No replacement records or extra retrieval were introduced. The empty recent-context marker remains, without any recent exchanges.','',
        '## Final-answer results','', '| Sample | Original | No recent | No recent, chronological |','|---|---:|---:|---:|']
    for group,t in result['totals'].items():
        lines.append('| '+group+' | '+' | '.join(f"{t['scores'][a]}/{t['n']}" for a in ARMS)+' |')
    lines+=['','Pairs separate removal from ordering; chronological-with-recency was not tested.','']
    for group,t in result['totals'].items():
        for pair,v in t['pairs'].items():lines.append(f"- {group}, {pair}: {v['gains']} gains, {v['losses']} losses.")
    lines+=['','## Size and runtime','', '| Arm | Median context chars, all192 | Median prompt tokens, sample | Measurement seconds |','|---|---:|---:|---:|']
    for a,e in extras.items():lines.append(f"| {a} | {e['context_chars_median']:,.0f} | {e['prompt_tokens_median']:,.0f} | {e['seconds']:.2f} |")
    lines+=['','All full prompts fit the fixed32768 context plus16384 output allowance. Every measurement completed with EOS, nonempty final and no native thinking block. Native-off baseline prompts match the saved Study E native template on16/16, and two calibration outputs match exactly.','',
        '## Every sampled question','', '| Question | Gold | Original | No recent | Chronological | Evidence complete |','|---|---|---|---|---|---|']
    for r,av in zip(result['rows'],availability):
        def cell(s):return s.replace('|','\\|').replace('\n',' ')
        lines.append('| '+cell(r['query'])+' | '+r['reference']+' | '+' | '.join(cell(r['arms'][a]['answer'])+(' ✓' if r['arms'][a]['score'] else ' ✗') for a in ARMS)+' | '+('yes' if av['complete'] else 'no' if av['applicable'] else 'not applicable')+' |')
    lines+=['','## Interpretation limits','',
        'The sample uses the first three content ids in each of four before conditions and the first two latest/absence ids, without filtering by correctness or completeness. It is16 exposed synthetic questions, not a heldout population estimate. One seed does not characterize reader variance. Four guards are too few to establish safety. The comparison concerns the C1 baseline, not the fusion variants.','',
        'Native thinking was kept off consistently under the standing test rule. These results cannot be compared causally with the earlier thinking-on probe, which selected failures and changed the native system prefix. Availability is identical across these presentation arms; final-answer changes are reader outcomes under a joint input intervention, not improved retrieval.','',
        'Canonical final answers are scored under the frozen Study E grammar. Reasoning-only output is not awarded credit. Raw responses, per-item scores, gates, selection and all transformed contexts are retained in chronology_artifacts. No human or independent-rater audit is claimed.','',
        'Original study registrations, answers, source data, retrieval code and production defaults remain unchanged. This exploratory probe tests the user-requested presentation without a new success disposition.','']
    path=P/'CHRONOLOGY_REPORT.md';assert not path.exists();path.write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(extras=extras,availability=availability),indent=2))


if __name__=='__main__':main()

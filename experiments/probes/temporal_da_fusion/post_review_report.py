"""Summarize only committed resolved prefix-ablation scores."""
import statistics
from preflight import P,read,sha,committed,save
O=P/'relevance_artifacts/post_review_reader'
def main():
    committed(O/'scores_resolved.json')
    assert sha(O/'scores_resolved.json')==read(O/'scoring_gate_resolved.json')['scores_sha256']
    scores={x['blind_id']:x for x in read(O/'scores_resolved.json')}
    mapping=read(O/'mapping.json')
    old={x['id']:x for x in read(P/'relevance_artifacts/full_e_reader/result.json')['rows']}
    rows=[dict(id=m['id'],type=m['type'],**scores[m['blind_id']],old_answer=old[m['id']]['answer']) for m in mapping]
    transformations=read(O/'transformations.json')
    raw=[read(O/(m['case']+'.json')) for m in mapping]
    stats=dict(n=22,recovered=sum(x['score'] for x in rows),
        remaining_wrong=sum(not x['score'] for x in rows),seconds=sum(x['latency_seconds'] for x in raw),
        output_tokens=sum(x['response']['tokens_predicted'] for x in raw),
        retained_min=min(len(x['kept']) for x in transformations),retained_max=max(len(x['kept']) for x in transformations),
        removed_min=min(len(x['removed']) for x in transformations),removed_max=max(len(x['removed']) for x in transformations))
    save(O/'result.json',dict(stats=stats,rows=rows))
    lines=['# Post-review removal reader probe','','Plan5085934f; implementation82d82e90; inputgatee4038d78; calibration915cb214. Failure-selected diagnostic, no production change.','',
        f"Removing post-review records recovers **{stats['recovered']}/22** previously wrong answers; **{stats['remaining_wrong']}** remain wrong.",'',
        'Each treatment retains exactly the already retrieved records through the existing selector-identified review anchor. No gold labels choose the cutoff; no preceding selected record is changed or newly admitted. Full original native prompts reproduce22/22. The review itself remains. Same native-off Qwen reader,HH001,seed5005,serial/cachefalse,4096 output,32768 context and sampling.','',
        f"Retained records range{stats['retained_min']}–{stats['retained_max']}; removed records range{stats['removed_min']}–{stats['removed_max']}. All22 responses complete. Measurement takes{stats['seconds']:.1f}seconds and generates{stats['output_tokens']}output tokens.",'',
        'All source evidence was already present in the original wrong prompts. Recoveries show sensitivity to the removed later history under this intervention. Shorter input and removal of specific distractors are bundled; no internal reasoning cause is identified. These22 are selected failures and the original arm is historical rather than a fresh repeated control. Do not extrapolate this recovery rate to all questions or claim broader generalization.','',
        'All22 answers scored canonically; no prose adjudication was needed. No human or three-pass audit. Raw captures were committed before scores, resolved scores before this report. Negative input gate and parser fixtures and duplicate arithmetic45 calibration preceded inference.','',
        '| Question | Gold | Original wrong answer | Prefix answer | Correct |','|---|---|---|---|---|']
    for x in rows:
        esc=lambda s:s.replace('|','/').replace('\n',' ')
        lines.append('| '+' | '.join([esc(x['query']),x['reference'],esc(x['old_answer']),esc(x['answer']),str(x['score'])])+' |')
    lines+=['','Full artifacts: [reader directory](relevance_artifacts/post_review_reader). No changes to prior scores or retrieval defaults.','']
    (P/'POST_REVIEW_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(stats)
if __name__=='__main__':main()

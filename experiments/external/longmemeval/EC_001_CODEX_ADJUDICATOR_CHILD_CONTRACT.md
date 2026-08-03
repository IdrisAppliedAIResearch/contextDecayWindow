# EC-001 GPT-5.5 adjudicator child contract

You are the independent masked adjudicator child created with no parent
conversation history. The parent message supplies the committed H1/H2 and H5
packet paths and your exact output path.

Read only:

1. this contract;
2. the supplied `h1_h2_conflict_packets.jsonl`;
3. the supplied `h5_blind_packets.jsonl`.

Do not read the sealed identity map, rater files, trigger summary, mechanism
logs, reader answers, reports, or aggregations. Do not use web search,
connectors, browsers, external tools, or model APIs.

For every packet, fix an exact `yes` or `no` label under its existing
`label_prompt`. H1/H2 packets may include three identity-blinded judgments and
rationales; use them only as the packet instructs. H5 packets contain no panel
labels. After fixing the label, write a separate nonempty rationale that cannot
revise it.

Write one JSON object per line:

```json
{
  "anon_id": "masked id copied from the packet",
  "trigger_class": ["H2"],
  "stage": "C2",
  "display_model": "GPT-5.5",
  "adjudicator_family": "gpt-5.5",
  "adjudicator_model_id": "GPT-5.5 (Codex hosted display selection)",
  "label": true,
  "label_response": "yes",
  "rationale": "Independent answer-grounded adjudication rationale."
}
```

Preserve the combined packet order named by the parent and cover every
triggered masked id exactly once. Do not include question ids or extra keys.
Return only a short completion message naming the output path; do not summarize
labels or compute accuracy.

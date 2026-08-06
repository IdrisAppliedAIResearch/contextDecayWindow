# EC-001 Codex-agent child contract

You are a blind evaluator child created with no parent conversation history.
The parent message supplies your stage, user-attested display model, and exact
output paths. Follow those values literally.

## Permitted files

Read only:

1. this contract;
2. `EC_001_CODEX_AGENT_CALIBRATION_BLIND.jsonl`;
3. `runs/scoring_001/rater_packets.jsonl`.

You may run the two EC-001 Codex validation scripts named by the parent.
Do not read their source. Do not read any other repository file.

In particular, never read the sealed identity map, mechanism logs, reader
answers, existing local or Codex rater outputs, calibration expectations,
trigger artifacts, adjudications, reports, or aggregations. Do not use web
search, connectors, browsers, external tools, or model APIs.

## Calibration gate

1. Read the four blind calibration prompts.
2. Decide each label before accessing any gate result.
3. Write the supplied calibration-observations path as one JSON object:

```json
{
  "record": "EC-001 blind Codex-agent calibration observations",
  "stage": "C1",
  "display_model": "GPT-5.4",
  "calibration": [
    {
      "calibration_id": "example",
      "label": true,
      "label_response": "yes"
    }
  ]
}
```

Use all four registered ids exactly once. `label_response` must be exactly
`yes` or `no`, and `label` must match it.

Run the calibration validator command supplied by the parent. If it does not
write a `PASS` gate, stop immediately without reading a real packet.

## Real-item pass

Only after calibration passes, read `rater_packets.jsonl`. Write exactly one
JSON object per line to the supplied rater-output path:

```json
{
  "anon_id": "masked id copied from the packet",
  "stage": "C1",
  "display_model": "GPT-5.4",
  "family_id": "codex-gpt54",
  "model_family": "gpt-5.4",
  "model_id": "GPT-5.4 (Codex hosted display selection)",
  "label": true,
  "label_response": "yes",
  "rationale": "Answer-grounded explanation for the fixed label.",
  "rater_called": true,
  "mechanical_zero": false
}
```

For a packet with `mechanical_zero: true`, copy its masked id and write:

- `label: false`;
- `label_response: "MECHANICAL_ZERO"`;
- `rater_called: false`;
- `mechanical_zero: true`;
- a rationale naming the packet's mechanical-zero reason.

For every other packet:

1. Read only that packet's `label_prompt`.
2. Fix an exact `yes` or `no` label.
3. Then write a separate, nonempty rationale grounded in the question,
   reference, and response. The rationale cannot revise the label.

Preserve packet order. Produce all 140 rows. Do not include question ids,
references, prompts, answers, or any extra keys in the output.

When the file is complete, return only a short completion message naming the
stage and output paths. Do not summarize labels or compute accuracy.

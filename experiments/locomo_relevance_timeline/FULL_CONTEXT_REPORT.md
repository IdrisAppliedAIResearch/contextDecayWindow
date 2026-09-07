# LoCoMo timeline applicability and full-context check

**Inference paused; no reader accuracy result.** Implementation plan4193702b; size-check plan66e5f3e6; raw size results c3555066. September7,2026.

The carried temporal parser returns unsupported for all1,986 questions. Its quoted-name/meeting-or-event grammar does not activate on this natural question population. Thus the proposed arm currently tests cosine>=.48 plus chronological full-pair presentation, with zero protected anchors or before cutoffs. This is an applicability limitation of this parser, not evidence that LoCoMo lacks temporal questions or that a natural anchor resolver cannot work.

All128 E prefix selections and payloads replay exactly. Cached vectors cover all inputs; no embedding calls. Two full-population native tokenizer passes reproduce the same prompts. Initial32768 context fails the longest33841-token input plus4096 output. Common40960 context fits, with the original failed fit preserved.40,960 is allocation, not input consumption.

## Exact matched input sizes

The comparison uses all1,986 raw occurrences, identical questions, HH001/native templates, source dates/dialogue IDs and pair formatting. Full context includes every pair of the corresponding conversation. Both sides omit the separate image-caption/image metadata omitted by the carried adapter. Selected native prompts reproduce1,986/1,986 exactly. No generation requests; token comparison took118.20seconds excluding startup.

| Input measure | Selected timeline | Full conversation |
|---|---:|---:|
| Median tokens, all1,986 |8,494|36,048|
| 95th percentile |26,226|38,001|
| Maximum |33,841|38,014|
| Median tokens, primary1,540 |8,786|36,047|

These are marginal distributions; dividing their medians does not give the median paired ratio. Per-question retained share has median26.44% overall and27.00% on the primary population. Aggregate selected/full input ratio is31.16%, a68.84% token reduction across all requests. Median paired saving is23,781tokens.

92/1,986 (4.63%) retain at least80% of full input;46 (2.32%) at least90%;15 (0.76%) at least95%. All46 near-90% cases belong to the primary population (46/1,540,2.99%). Two questions select no records.

The longest selected case is conv-50, key dfea07b0a10f1f073767597ea6592a935ad309ed7f163c4f8bbf59d5b8091ca0:33,841 selected versus34,259 full tokens,98.78% retained, only418tokens saved. It selects288 of292pairs. The concern about near-full context is accurate for this case, but it is not typical of the corpus.

Temporal category2 has321questions, median selected5,525tokens, median paired retained share17.30%, and zero supported anchors. Selection size reduction cannot establish answer sufficiency or correctness.

## Decision

Keep full inference paused for discussion of what the test should establish. A run now could estimate the reader accuracy of the uncapped chronological relevance filter on LoCoMo. It could not test transfer of E's before-anchor cutoff, which motivated the strongest recent result. The size check does not by itself justify delaying on the basis that the arm generally supplies full context; its typical reduction is substantial. Nor does it establish resource scaling beyond this fixed corpus.

The next useful design step is to determine whether natural temporal questions and their source histories support a label-free anchor/boundary operation, with source-order versus event-time safety characterized before implementing a replacement. Do not silently add a resolver or fit a cutoff to these questions. Alternatively, deliberately retain the narrower relevance-only LoCoMo question. No choice is made by this report.

Implementation is preserved but unregistered and not yet fully validated. There are no measurement answers or scores, and no active inference/monitoring hooks. All tokenizer servers were stopped by their owned-process cleanup. Earlier studies and PR96 remain unchanged; no production adoption.

Artifacts: artifacts/part1.json; artifacts/fit/fit.json; artifacts/fit40960/fit.json; artifacts/full_context_check/results.json (all per-question counts and category/conversation distributions), launch/props/logs/stopped manifests. HANDOFF.md preserves remaining implementation work.

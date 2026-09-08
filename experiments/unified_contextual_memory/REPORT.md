# Unified memory exploratory paired subset

C0 384/566; C1 399/566. Difference 2.65 percentage points; descriptive conversation-cluster 95% interval [0.53, 4.53]. 27 gains, 12 losses.

Generation was stopped at the user's request before scoring. This is a nonrandom completed-pair subset of previously exposed LoCoMo; the full registered comparison is not completed and no full-population WORKS disposition is claimed. Same native-thinking-off reader, shared source/captions/chronology, three same-model votes and a separate blinded adjudication. No human audit, transfer, or component-attribution claim. Annotation availability is diagnostic, not sufficiency.

[Results](artifacts/subset/results.json), [question/gold/answer diagnostics](artifacts/subset/diagnostics.jsonl.gz), [scope amendment](AMENDMENT_002_PAIRED_SUBSET.md).

## Verified exploratory signal

Independent reconstruction from all sealed reader/judge hashes reproduces the scores, the 20,000-resample interval and evidence cross-tabs exactly ([audit](artifacts/subset/audit.json)). The 741 completed pairs contain 566 primary category 1–4 questions and 175 separately reported adversarial questions.

| Measure | Direct C0 | Combined C1 |
|---|---:|---:|
| Primary answers correct | 384/566 (67.84%) | 399/566 (70.49%) |
| Three-pass majority sensitivity | 383/566 | 399/566 |
| All annotated evidence delivered, among 565 annotated questions | 493/565 | 516/565 |
| Wrong despite all annotated evidence delivered | 124 | 127 |
| Exact abstention on separate adversarial set | 149/175 | 155/175 |

The primary endpoint follows the separate blinded adjudication pass; it changed two unique judge items from three-pass majority. Both scoring readings have a similar positive aggregate difference. These are correlated same-model judgments, not human-validated correctness.

| Category | C0 | C1 | Net correct |
|---|---:|---:|---:|
| 1 | 41/88 | 39/88 | -2 |
| 2 | 60/123 | 69/123 | +9 |
| 3 | 6/29 | 6/29 | 0 |
| 4 | 277/326 | 285/326 | +8 |

Six conversations improve, three tie, and one regresses. Per-conversation intervals in the raw summary collapse to their point estimate because each such bootstrap has one cluster; they are not meaningful within-conversation uncertainty estimates. The aggregate ten-conversation interval is the reported descriptive interval.

All-annotation delivery improves on 23 questions with zero losses. Of these 23, seven answers change wrong-to-correct, ten remain wrong, five remain correct, and one changes correct-to-wrong. Of the 27 answer gains overall, 18 already had all annotated evidence in both arms, seven gained annotation completeness, and two remained annotation-incomplete. Ten of the twelve answer losses also had all annotated evidence in both arms.

This supports a modest answer-level signal for the combined configuration on this subset. It does not establish that annotation recovery alone explains the gain, that extra context is always useful, or that max-product decay is the right stopping law. Both arms already share chronological presentation and captions; this comparison cannot attribute improvement to chronology, caption repair, or one added component. The direct route is preserved, but additional material can still accompany reader regressions.

The full-corpus run remains stopped. No production adoption, full-population WORKS claim, or fresh-transfer conclusion follows. The next discussion should examine the gains and losses and whether the current multiplicative rule excludes necessary links; further inference needs a concrete agreed scope.

Post-result diagnosis: [Probe001](PROBE_001_REPORT.md) identifies restrictive composed-path exclusions and concrete bidirectional scoring concerns, including inconsistent date formatting and list completeness. The locked scores above remain unchanged; the15-answer margin should not be treated as precise pending a separate scoring audit.

# Errata

## Scoring Integrity Audit (2026-07-26)

**Headline change:** Study 001 changes from VALIDATED to PARTIAL.

The scoring-integrity audit found 19 changed scores across Studies 001-009.
Original response and score artifacts remain unchanged. Corrected item-level values,
rationales, provenance, totals, reliability measures, and cascade verdicts are in
`experiments/audits/scoring_integrity/`.

Most consequential corrections:

- Study 002 C: 13.0 -> 8.5. Q11: 1.0 -> 0.0 (`NO_ANSWER`).
- Study 003 accepted: 12.0 -> 11.5; literal Bar 2 remains FAIL.
- Study 009 S: 10.5 -> 9.0; L remains 12.0, so the null-test gap is 3.0.
- Study 001 iterative: 9.0 -> 8.0; compaction: 3.5 -> 2.5; Bar 2 changes to FAIL.

The first 81-item Layer 2 attempt is invalidated by
`AMENDMENT_003_study003_cross_references.md`. The final results use the replacement
79-item sequence only.

## Study 010 LTM Budget Accounting (2026-07-29)

**Headline change:** the published Q13/Q14 LTM character values were charged
content estimates, not serialized block lengths.

Study 010 reported 31,991 and 31,847 LTM characters at Q13 and Q14 and described
them as near-saturation of `B_ltm = 32,000`. DR-001 replayed both committed
blocks character-for-character. Their actual serialized lengths were 53,726 and
53,839 characters, exceeding the nominal budget by 21,726 and 21,839, or 67.9%
and 68.2%. The budget was violated, not saturated.

The old budget authority counted source user/assistant text but omitted
per-episode tags, metadata, and separators. The historical values and run
artifacts remain unchanged. Their classification is corrected here, and the
compact-store scaling conclusion derived from the undercharged values is
withdrawn. Scores and fact-delivery findings do not change because the model
received the recorded blocks, but they describe a budget-noncompliant arm.

DR-001 replaces the renderer with compact, content-identical episode elements
and charges exact complete-block cost. The same historical identity sets render
to 37,619 and 37,545 characters, still above 32,000; production re-selection at
the locked budget admits 69 and 71 episodes. See
`experiments/components/rendering_expansion/`.

The separate reported context peak survives audit. All 2,000 Study 010 rows
recompute from the committed serialized prompts under the registered
`characters // 4` estimator; L peaks at 27,154 and S at 17,541. These are
character-based estimates, not exact model-tokenizer counts. See
`experiments/components/rendering_expansion/artifacts/context_peak_audit/`.


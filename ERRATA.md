# Errata

## Scoring Integrity Audit (2026-07-26)

**Headline change:** Study 001 changes from VALIDATED to PARTIAL.

The scoring-integrity audit found 19 changed scores across Studies 001-009.
Original response and score artifacts remain unchanged. Corrected item-level values,
rationales, provenance, totals, reliability measures, and cascade verdicts are in
`experiments/audits/scoring_integrity/`.

Most consequential corrections:

- Study 002 C: 13.0 -> 8.5. Q11: 1.0 -> 0.0 (`NO_ANSWER`).
- Study 002 A: 8.0 -> 5.5.
- Study 003 accepted: 12.0 -> 11.5; literal Bar 2 remains FAIL.
- Study 009 S: 10.5 -> 9.0; L remains 12.0, so the null-test gap is 3.0.
- Study 001 iterative: 9.0 -> 8.0; compaction: 3.5 -> 2.5; Bar 2 changes to FAIL.

The first 81-item Layer 2 attempt is invalidated by
`AMENDMENT_003_study003_cross_references.md`. The final results use the replacement
79-item sequence only.

The residual-error figure is extrapolated rather than observed: 3 disagreements
in a 26-item control sample (11.54%) projected over 143 unreviewed items gives
16.5 expected errors, reported informally as about 20. Study 010 was outside
the audit; its exploratory scores are not directly comparable to the corrected
Studies 001-009 series.

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

## Retrieval Bakeoff Q4 Cosine and Seal Provenance (2026-07-29)

**Headline change:** the published turn-55/Q4-query cosine changes from
0.16612689197063446 to 0.12042197585105896.

AS-001 reconstructed the turn-55 episode from the committed turn log. Its
embedding is byte-identical to the original local database vector, and the
exact committed turn-115 query yields 0.12042197585105896. The old value has no
committed generating code. Both values remain below the registered K threshold
of 0.48, so K-ineligibility, scores, and the Q4 exclusion verdict do not change.

The audit also found that the corrected Tier 6 mechanism seal lists `study.db`,
but `*.db` is ignored and that file was never committed or placed in Git LFS.
The seal was computed over mixed LF/CRLF working-tree representations. All 264
tracked mechanism files match their seal entries under exact canonical LF or
deterministic CRLF materialization, with no content mismatch; the missing
database means the historical seal cannot establish a complete committed
265-file mechanism tree.

AS-001 does not use the ignored database. It reconstructs candidate identity,
order, topic, and source text from committed logs, reproduces the historical
15-episode/59,708-character payload and SHA-256 exactly, and records the seal
limitation. See `experiments/components/q4_packing/`.

## AS-001 Decision Rule Invalidation (2026-07-29)

**Headline change:** the emitted `PRIMACY MECHANISM LIVE` verdict is withdrawn.

AS-001 opened `S' = 9` at 32k and 16 at 64k, versus 15 episodes in the
historical 59,708-character payload. Its rule assumed compact rendering could
recover slots; it had no interpretation for exact charging reducing them.
Branch A required `S' >= 29` at 32k, while Branch D labeled every failure to
reach rank 27 as a primacy mechanism. The rule could not distinguish a separate
primacy mechanism from the joint effects of rank, greedy N-first packing, and
budget.

This issue was raised after output, so Decision 001 invalidates the
interpretation rather than retroactively amending the locked rule. The original
analysis artifacts remain unchanged as diagnostics. A post-result exact
reachability calculation finds rank 27 first enters at 108,432 characters.
AS-001 does not authorize a pinned tier or an architecture study.


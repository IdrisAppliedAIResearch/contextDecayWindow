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


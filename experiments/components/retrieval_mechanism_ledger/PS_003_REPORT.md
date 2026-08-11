# PS-003 - Ambiguous Natural-Language Cue Resolution

**Pre-registration commit:** `63a0937bc303ee9eac595a84fb3780d12ebe6500`
**Pre-registration SHA-256:** `32CFE67EEF9B21478FAA40352C8D607E1FA6CF417BA9F89063F2B046306405A0`
**Part 1 authorization:** `d77109bd`
**Implementation:** `1a40655f`
**First-process artifact:** `fac01c42`
**Two-process determinism:** `2f370013`
**Final-design lock:** `4f5cdc4a`
**Part 2 authorization:** `bca34385`
**Preflight artifact:** `7e26e443`
**Measurement artifact:** `0535d7e1`
**Amendment 009:** `0e277b07`
**Date:** August 11, 2026
**Disposition:** `LOOKUP_BINDING_INSUFFICIENT`
**Outcome ceiling:** `CHARACTERIZED`

## Outcome

PS-003 tested whether one deterministic ambiguity resolver could reject unsafe
PS-002 mixed cues while preserving eight independently certified one-memory
outputs for every sealed natural-language query.

The mechanical repair passed. All four label-blind cells emitted eight unique
stored identities for all 24 queries. The registered selection rule chose five
probes with four swaps per non-base probe. That cell accepted all 192 outputs in
197 attempts while rejecting three cyclic families, one spurious family, and
one disagreeing family. The exact PS-002 cycle and spurious base cues were
encountered, rejected, and emitted no identity.

The relevance claim failed. G1 and G2 passed, but G3 required at least 9/12
lookup facts and at least 2/3 per domain. The resolver delivered 7/12, with:

| Domain | PS-003 | Required |
|---|---:|---:|
| Structural | 2/3 | 2/3 |
| Art | 2/3 | 2/3 |
| Monetary | 1/3 | 2/3 |
| Marine | 2/3 | 2/3 |

Direct cosine top-eight, PS-002's strongest cell, and PS-003 all delivered the
same 7/12 lookup facts with the same domain distribution. PS-003 therefore
improved output safety but did not improve evidence binding.

The binding disposition is `LOOKUP_BINDING_INSUFFICIENT`. G4, G5, chained and
enumeration stress measurement, answer generation, scoring, ablation, and live
evaluation were not reached.

## Part 1 characterization

The new component retained PS-002's fixed `M=4`, `TAU=0.025` semantic mixture.
For each proposed output it recalled the base cue plus deterministic local
boundary perturbations. An output was accepted only if every probe converged to
the same exact new PS-001 stored code. A failed family emitted nothing and
inhibited only the carried highest-support candidate. Each query had a fixed
eight-output target and 16-attempt ceiling; no cosine or majority-vote fallback
existed.

| Cell `(P, S)` | Attempts | Probe recalls | Rejected families | Max attempts/query | Eligible |
|---|---:|---:|---:|---:|---|
| `(3, 1)` | 194 | 582 | 2 | 10 | Yes |
| `(3, 4)` | 196 | 588 | 4 | 11 | Yes |
| `(5, 1)` | 194 | 970 | 2 | 10 | Yes |
| `(5, 4)` | 197 | 985 | 5 | 12 | Yes |

The selected `(5, 4)` cell's rejected attempts comprised three cycle outcomes,
one spurious outcome, and one disagreement. Across individual probe terminals,
there were nine cycles, five spurious terminals, 971 stored terminals, and zero
runtime guards. Every cue and terminal retained exactly 41 active units.

Two fresh processes reproduced mechanism digest
`7FC45BC03FE51C053FA20E561BF028F8F1DC52D8678271AA35AFA090580394FD`
and canonical artifact-sequence digest
`5A4E27F5B27424426FED798BA331B4875695A5506EC262355AB4F86DDA2DECB1`
byte-for-byte.

## Preflight and gates

PF1-PF10 passed before relevance output. The preflight reproduced all 985
selected-cell probes exactly, re-established PS-001 and PS-002 identities,
verified all 28 registered facts in eligible earlier source turns, retained all
four controls, and proved with a planted bad digest that label parsing was
short-circuited before the reader was called.

| Stage | Result |
|---|---|
| Pre-registration and Part 1 authorization | PASS |
| Label-blind four-cell exploration | PASS |
| Two-process deterministic comparison | PASS |
| Final-design lock and Part 2 authorization | PASS |
| PF1-PF10 | PASS |
| G1 carried mechanism identity | PASS |
| G2 safe ambiguity resolution | PASS |
| G3 lookup binding | **FAIL - 7/12; monetary 1/3** |
| G4 cosine differentiation | NOT REACHED |
| G5 bounded output | NOT REACHED |
| Chained/enumeration stress measurement | NOT REACHED |
| Answers, scoring, ablation, live run | NOT AUTHORIZED |

## Interpretation

The result closes the narrow PS-002 safety gap. A local unanimous-probe rule can
reject the observed spurious and cyclic cue families and continue to eight safe
one-memory outputs under a fixed attempt bound.

It does not close the semantic gap. The resolver's extra attempts walk farther
through the same cosine-ordered candidate stream, and the final lookup evidence
is identical to direct cosine and PS-002. Basin consensus answers whether an
output is stable under these local code perturbations; it does not answer
whether the attractor contains the query's required fact.

This result must not be summarized as successful natural-language retrieval.
The all-query mechanical property passed, but the first relevance bar failed.
No answer was generated, so the effect on answer score remains unmeasured.

## Advancement

PS-003 does not authorize a live run. The next unresolved property is semantic
differentiation, especially the monetary-domain misses, not attractor safety.
Any follow-up would need a new prospective component that can change which
evidence is selected rather than only certify or retry the existing cosine-led
outputs. It must retain the direct-cosine control and cannot reopen PS-003.

## Verification

The PS-003 focused component, exploration, preflight, and measurement tests pass
`26/26`. The complete repository suite passes `1509/1509` in 100.33 seconds in
the Amendment 009 mixed-representation environment. The complete PS-001 LF
evidence tree was temporarily overlaid, then all 57 primary files were restored
with zero hash mismatches. `git diff --check`, the targeted conflict-marker
scan, carried PS-001/PS-002 source hashes, and the AGENTS digest cap pass.

## Evidence

- Design: `PS_003_AMBIGUOUS_CUE_RESOLUTION.md`
- Part 1 authorization: `PS_003_AUTHORIZATION.md`
- Part 1 artifacts: `artifacts/ps003_exploration/part1_process_1/`
- Determinism: `artifacts/ps003_exploration/two_process_determinism.json`
- Final design: `PS_003_FINAL_DESIGN.md`
- Part 2 authorization: `PS_003_PART2_AUTHORIZATION.md`
- Preflight: `artifacts/ps003_preflight/preflight.json`
- Ordered measurement: `artifacts/ps003_measurement/measurement.json`
- Amendment 009: `amendments/AMENDMENT_009_ps003_newline_anchor.md`
- Closeout verification: `artifacts/ps003_closeout/verification.json`

## Amendments and ERRATA

Amendment 009 (`0e277b07`) resolves a verification-only newline contradiction:
PS-001 requires the LF form of its exploration evidence while the primary
Windows checkout and original PS-003 table bind CRLF. PS-003 now accepts only
those two raw hashes and still requires the exact parsed PS-001 mechanism
digest. No mechanism, parameter, gate, label, criterion, or result changed.

One pre-output implementation defect used the wrong EpisodePopulation field
name; commit `d2d1af2a` corrected it. The failed run wrote no artifact. No
previously published number changes, so `ERRATA.md` is unchanged.

## Pull request

Study PR: [#48](https://github.com/IdrisAppliedAIResearch/contextDecayWindow/pull/48)

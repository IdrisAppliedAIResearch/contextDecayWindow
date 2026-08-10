# Retrieval Mechanism Ledger Closeout

**Status:** CLOSED; extended through E006 Part 2 Rev 5
**Date:** 2026-08-10
**Scope:** Offline retrieval mechanisms after the retrieval bakeoff
**Prospective design anchors:** `b42f4f81` (ledger and E002 protocol);
`fd880d88` (E001 protocol and dispositions)
**Post-hoc bar-audit anchors:** `b48e7501` (AR-001 protocol);
`15cdb177` (AR-001 implementation)

## Outcome

E002 mechanical query segmentation was killed. Its exhaustive 992-cell sweep
peaked at 10/17 Q11 items across 3/4 domains while preserving 14/16 targeted
items. The unchanged same-budget baseline delivered 6/17; the registered
historical hurdle was 13/17. The hurdle came from a 60,285-character Q11
payload under Tier 6's 60,595-character cap, 1.884 times E002's enforced
32,000-character budget. At matched budget, segmentation added four items over
the unchanged selector, a 66.7% improvement. The registered KILL is unchanged.

E001 attention-derived term selection was also killed for its narrow F2
diagnostic. The pinned Qwen3.6-27B NF4 capture calibrated 266 retrieval heads
from 32 deterministic cases. Across 714 sweep rows and 335 unique cues, no cue
reached K=0.48. The corrected full-query baseline was cosine 0.120421976 at
descriptive similarity rank 24/114. The best all-head cue reached 0.210318044
at rank 20/114. This is the best found across 335 cues, not a ceiling on
sharper head selection.

E003 late interaction remains not authorized. E001 was Q4-only and cannot
provide the prospective breadth bound, storage multiplier, exact-budget
policy, and no-regression test required to open E003.

AR-001 subsequently checked whether E002's 14/17 bar existed under exact
accounting. Dynamic programming over all 17-bit coverage states found an exact
minimum of 5,058 serialized characters across five episodes for at least
14/17. The full 17/17 frontier point costs 7,592 characters. The bar is
therefore achievable with 26,942 characters of headroom; F1 is a selection and
ranking problem under the registered availability measure, not a capacity
impossibility at 32,000 characters.

Four of the five exact-threshold episodes are prior probe answers at turns 112,
113, 115, and 118. They are valid under E002's locked `source_turn < 120`
eligibility rule, but this makes AR-001 a bound on the registered store measure,
not a plant-source-only sensitivity result.

## Integrity

- E002 mechanism seal, leakage audit, source integrity, and raw rerun
  determinism passed.
- E001 used model revision
  `6a9e13bd6fc8f0983b9b99948120bc37f49c13e9`, eager full attention, NF4
  4-bit double quantization, and BF16 compute.
- E001 captured all 16 full-attention layers and 24 heads per layer. Its
  calibration and Q4 rerun hashes were identical.
- E001 source seal, planted leakage rejection, Track 1 reference SHA, model
  manifest, execution SHA, and source-integrity checks passed.
- Two launch attempts stopped before model loading: one lacked the repository
  on global Python's `PYTHONPATH`; one compared the registered short Track 1
  SHA literally with its full SHA. Both implementation issues were corrected
  and committed before the authoritative `capture_001` run.

## Interpretation

Mechanical query splitting did not reach a hurdle established under a larger,
now non-production payload regime, but at the same enforced 32,000-character
budget it raised availability from 6/17 to 10/17. F1 remains open, with
segmentation the best matched-budget improvement tested in this ledger.
AR-001 rules out serialized capacity as the reason E002 stopped at 3/4
domains: complete standalone domain payloads cost 826 characters for civil,
3,182 for art, 2,913 for monetary, and 824 for marine. Art is the most
expensive domain, but all 17 facts fit together at 7,592 characters.

Generator-attention term selection did not restore the buried Q4 identity
bundle to K eligibility. Its 266/384 selected full-attention heads (69.3%) are
not discriminating relative to Wu et al.'s reported under-5% sparsity, which
is consistent with the best cue coming from the all-head arm. F2 is closed as
a program disposition and E003 is not authorized for the identity case, but
0.210318044 is not reported as a mathematical family ceiling.

The baseline correction from 0.166126892 to 0.120421976 is traceable to the
existing `ERRATA.md`: AS-001 reconstructed the exact committed turn-55 episode
and turn-115 query, reproduced the stored embedding, and found that the old
number had no committed generating code. The correction changes neither
K-ineligibility nor the E001 outcome.

`LITERATURE_LANDSCAPE.md` now records the carried HippoRAG disposition,
LoCoMo/LongMemEval adoption decision, and paper-positioning call.
`LITERATURE_SCAN.md` remains the companion candidate-mechanism scan.

## EC-001 external path disposition

The post-run EC-001 retrieval-path diagnostic resolves an apparent conflict
between pooled median evidence-session rank 2 and 23.2% any-session recall.
The rank is measurement-only; the component thresholds and packs exchanges.
Evidence is in the top four on 401/470 questions, but only 96 of those retrieve
any evidence session. K has a candidate on 232/500 questions, while a
non-recency K exchange survives packing on only 20. Every block is truncated;
the median is 16 recency, 0 K, and 1 coverage exchange. Of 109 session hits, 91
come from recency and 18 from all non-recency paths.

This is a post-hoc diagnosis, not a counterfactual parameter test. It identifies
N-first exact-budget exhaustion as the dominant observed delivery gate and
`K = 0.48` as an additional category-specific gate. It does not authorize
retuning either.

## EC-002 packing counterfactual

EC-002 turns the packing diagnosis into a same-store counterfactual. Holding
the vectors, candidate sets, `K = 0.48`, selector, and 32,000-character budget
fixed, it changes only exact packing order from recency-first to K-first.
Any-session recall rises from 109/470 to 261/470, with 152 paired gains and no
losses. Exact-turn-any availability rises from 79/470 to 196/470, with 119
gains and two losses. Delivered K episodes rise from 26 to 476 while all 500
blocks remain truncated.

Packing priority is therefore a confirmed causal gate for recovered EC-001
items. It does not close the residual 209/470 any-session misses, identify the
remaining threshold/granularity losses, or authorize a live production change.

EC-001 also closes the reason to build F3 at component level. The component
emits 0 absence signals on 500 questions, while the fixed reader scores 17/20
abstention items. F3 is retired as a component requirement, not marked solved:
the detector remains absent, and reader compensation is measured for only one
reader, prompt, seed, and 20-item subset.

## E006 chained retrieval

E006 Part 2 Rev 5 completes the Q11-only zero-call chained-retrieval path after
Rev 2 stopped in Preflight and Rev 3/Rev 4 stopped at independent derivation
gates. The corrected recursive Gram equation matches the unchanged vector route
in all 12 PF11 cells at maximum error `9.5e-15`. PF1-PF10 pass, including exact
X0 reproduction, 12/12 single-shot controls, and 48/48 absorbing-state checks.

Across the fixed 48-cell grid, single-shot `top_m` reaches 3/17, D1 reaches
7/17, and D2/D3 reach 9/17. The kill against X0's 6/17 does not fire. However,
the best chain cells consider 15-20 candidates and select 12 episodes versus
X0's 8, miss all four art facts, and remain below E005's 12/17. This is
`CHARACTERIZED` availability on one probe, not better-ranking evidence.

The eight targeted probes have no committed full cosine traces, so no targeted
no-regression arm exists. No answer was generated or scored, and no live run,
promotion, or adoption is authorized. See `E006_PART2_REV5_REPORT.md` and
`artifacts/e006_rev5_s4/results.json`.

## Verification

The 19 focused E001/E002 tests pass. On 2026-07-31 the permanently failing
historical Tier 6 seal test was resolved without changing its verifier, seal,
or artifacts: it now asserts the two documented strict newline mismatches
(`logs/context_match.jsonl` and `runtime_audit.json`) and separately requires
the authorized canonical/mixed 265-file seal to pass. The full suite now
passes 760/760. AR-001's exact solver matches exhaustive subset enumeration on
a synthetic corpus; its additive cost matches the complete production
renderer, and an independent output-directory rerun was byte-identical across
all seven artifacts.

## Evidence

- E002 design: `E002_segmented_query_protocol.md`
- E002 result: `artifacts/e002/E002_report.md`
- E002 interpretation: `E002_POSTHOC_INTERPRETATION.md`
- E001 design: `E001_attention_term_selection_protocol.md`
- E001 capture: `artifacts/e001/capture_001/capture_manifest.json`
- E001 result: `artifacts/e001/analysis_001/E001_report.md`
- Literature: `LITERATURE_SCAN.md`
- Program landscape: `LITERATURE_LANDSCAPE.md`
- Q11 achievability design: `AR_001_Q11_ACHIEVABILITY_PROTOCOL.md`
- Q11 achievability result: `artifacts/ar_001/AR_001_report.md`
- E006 Rev 5 design: `E006_PART2_REV5_chained_retrieval.md`
- E006 Rev 5 result: `E006_PART2_REV5_REPORT.md`
- E006 Rev 5 artifacts: `artifacts/e006_rev5_s4/`

Design and disposition commits precede implementation and output. E002 output
is anchored by `dfdb257e`; E001 capture by `dbbf7617`; E001 analysis by
`2ba4dd99`; AR-001 result by `cb696c7f`.

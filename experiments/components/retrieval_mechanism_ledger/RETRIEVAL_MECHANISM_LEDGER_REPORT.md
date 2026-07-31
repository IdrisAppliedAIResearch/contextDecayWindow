# Retrieval Mechanism Ledger Closeout

**Status:** CLOSED
**Date:** 2026-07-30
**Scope:** Offline query-representation mechanisms after the retrieval bakeoff
**Prospective design anchors:** `b42f4f81` (ledger and E002 protocol);
`fd880d88` (E001 protocol and dispositions)

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

## Verification

The 19 focused E001/E002 tests pass. On 2026-07-31 the permanently failing
historical Tier 6 seal test was resolved without changing its verifier, seal,
or artifacts: it now asserts the two documented strict newline mismatches
(`logs/context_match.jsonl` and `runtime_audit.json`) and separately requires
the authorized canonical/mixed 265-file seal to pass. The full suite now
passes 755/755.

## Evidence

- E002 design: `E002_segmented_query_protocol.md`
- E002 result: `artifacts/e002/E002_report.md`
- E002 interpretation: `E002_POSTHOC_INTERPRETATION.md`
- E001 design: `E001_attention_term_selection_protocol.md`
- E001 capture: `artifacts/e001/capture_001/capture_manifest.json`
- E001 result: `artifacts/e001/analysis_001/E001_report.md`
- Literature: `LITERATURE_SCAN.md`
- Program landscape: `LITERATURE_LANDSCAPE.md`

Design and disposition commits precede implementation and output. E002 output
is anchored by `dfdb257e`; E001 capture by `dbbf7617`; E001 analysis by
`2ba4dd99`.

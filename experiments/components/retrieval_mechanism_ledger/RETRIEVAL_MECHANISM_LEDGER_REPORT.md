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
historical hurdle was 13/17.

E001 attention-derived term selection was also killed for its narrow F2
diagnostic. The pinned Qwen3.6-27B NF4 capture calibrated 266 retrieval heads
from 32 deterministic cases. Across 714 sweep rows and 335 unique cues, no cue
reached K=0.48. The corrected full-query baseline was cosine 0.120421976 at
descriptive similarity rank 24/114. The best all-head cue reached 0.210318044
at rank 20/114.

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

Mechanical query splitting did not solve breadth, and generator-attention term
selection did not restore the buried Q4 identity bundle to K eligibility.
These results kill the tested mechanisms, not the entire query-representation
family. Multi-vector late interaction remains untested, but this ledger does
not authorize its implementation.

The unresolved reference to `LITERATURE_LANDSCAPE.md` Section 7 remains a
source gap: no such file exists in the repository or beside the supplied
ledger. The independent primary-literature scan is complete in
`LITERATURE_SCAN.md`.

## Verification

The 19 focused E001/E002 tests pass. The full suite reports 753 passes and one
failure in the historical strict Tier 6 seal test. That test sees the two
newline-representation mismatches prospectively documented in Amendments 001
and 002 (`logs/context_match.jsonl` and `runtime_audit.json`); it reports all
265 files with no missing or extra paths. The authorized canonical/mixed seal
passes. The carried historical verifier and test were not changed after these
results.

## Evidence

- E002 design: `E002_segmented_query_protocol.md`
- E002 result: `artifacts/e002/E002_report.md`
- E001 design: `E001_attention_term_selection_protocol.md`
- E001 capture: `artifacts/e001/capture_001/capture_manifest.json`
- E001 result: `artifacts/e001/analysis_001/E001_report.md`
- Literature: `LITERATURE_SCAN.md`

Design and disposition commits precede implementation and output. E002 output
is anchored by `dfdb257e`; E001 capture by `dbbf7617`; E001 analysis by
`2ba4dd99`.

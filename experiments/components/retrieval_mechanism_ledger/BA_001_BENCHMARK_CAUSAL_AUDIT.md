# BA-001 - Retrieval Benchmark Causal Audit

**Type:** Pre-registered offline postmortem and causal audit
**Date:** August 11, 2026
**Status:** PRE-REGISTERED - NOT RUN
**Branch:** `study/ba-001-benchmark-causal-audit`
**Base commit:** `b7e9994a`
**Outcome ceiling:** `CHARACTERIZED`
**Model-generation calls authorized:** 0
**Embedding calls authorized:** 0
**Live runs authorized:** 0

## 0. Question and boundary

Why did E006 chained retrieval raise Q11 availability from the deployed X0
reference's 6/17 to 9/17, yet still retrieve 0/4 art facts and remain below
E005's 12/17? Was the gain evidence discovery, packing, or candidate volume?
Why does the art domain appear to fail in broad recall even though prior targeted
art questions were sometimes answered correctly?

This is a post-result audit of committed artifacts. It does not design or adopt
a new retrieval component. It may identify a mechanically testable opportunity,
but it cannot promote that opportunity, score a generated answer, or establish
that a biological mechanism improves an artificial memory.

The reference model is
`HYPOTHETICAL_001_MECHANICAL_BIOLOGICAL_MEMORY_MODEL.md`. Its principles are
used only to define the implementation-gap inventory in Section 4. They are not
evidence that any missing mechanism would work.

## 1. Frozen evidence

All hashes are SHA-256 over raw bytes. Any mismatch stops the audit.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Biological reference | 17,186 | `DB61A0DEA104627F4E47C1D0352EC00EC1FCDBDA58FA090C13E6629887BD0665` |
| E006 mechanism source | 5,801 | `12281717DD9AB64D4BAB4743B9595617978FEE383A81A59FFB9E344A88FA8B8D` |
| E006 Rev5 design | 8,953 | `6A674682DD60370631CAA834DE43FE07E59F2E0683E2D0C435DFC1003CEBE444` |
| E006 Rev5 parameter lock | 1,592 | `82EE2663FD4E8D01BDBA1B0779112E3D465F217B68619F807D531B41E8321139` |
| E006 Rev5 results | 306,894 | `BBEAE9CC6CB6EF830EF8CFEB7D4FE9F8BD710361927AC6ED1816DFAE1C86EC00` |
| E006 P3 final design | 5,637 | `50DC8F74EA08CD41A92E8DD40360496A79BFCCB7C2F11DA8C424A192F8227030` |
| E006 P3 parameter lock | 1,906 | `8F50DA0C78ABC3BCE3A338B9A83E906B10D9C3F2A57376C45D3D2E83D1F6E879` |
| E006 P3 results | 741,804 | `5A6B8A6731B813E0BF63071838D1B14CEAF41362D6548C0BCED9777E2BBE49EF` |
| Q11 full-rank inventory | 10,642 | `8D6F9EEE6EBE232608981AAC0C0D4816EAEC4710AE551DB028AE0B323253AC03` |
| Tier 2 evaluation rows | 674,786 | `4DD8AECC17B8F21D7F5DBCD2EE40249532662205D5A262F7180452D2587E8E50` |
| Holdout queries | 4,231 | `AE950FDA20DCE9F519F31EE2670A815A5599648CAB618D42309DB7E3F23D36F4` |
| Holdout answer key | 9,832 | `2D43A31D3C04F4AD690FF2910ABDE71F508A3F6CE776545A9F2B16F90FAE5320` |
| Corrected historical study database | 1,978,368 | `5DA47EA3FC2C8E3DCC50FA380FF65202D82557905D9976117E9E5D82E55C1C41` |

Historical score files may be used only for the explicitly non-causal reader
contrast in Section 8. Their hashes must be added to the generated input
manifest before the contrast executes.

## 2. Preflight Part 1 - Exploration

Exploration was completed before this design was locked. It inspected mechanism
source and label-sealed selection traces first, then opened committed Q11
measurement artifacts.

### 2.1 Behavioral identities

1. **E006 mean-context chain:** iterative pseudo-relevance feedback. At each
   depth it retrieves unseen episodes by cosine to a cue made from the original
   query and the mean of prior hits. It does not traverse stored episode edges.
2. **E006 P3 A0:** fixed-query retrieval over the same store and candidate
   quota, followed by the exact compact packer.
3. **E006 P3 A1:** the E006 mean-context chain under the same candidate quota
   and exact packer.
4. **E006 P3 A2:** query-anchored local-frontier propagation over a cosine
   graph. It is not temporal adjacency, learned co-replay connectivity, or an
   accessibility-gated storage substrate.
5. **Q11 availability:** the union of registered rubric facts found in the
   selected payload. It is not answer correctness or reader use.
6. **Art failure:** 0/4 registered art facts in a Q11 payload. It is not a claim
   that art was absent from storage or impossible to answer when directly cued.

### 2.2 Observed distributions

- E006 Rev5 spans 48 locked cells. Candidate counts rise from 3-5 at depth 0,
  to 6-10 at depth 1, 9-15 at depth 2, and 12-20 at depth 3. The maximum rises
  to 9/17 at depth 2 and then plateaus.
- At the registered matched-volume cell `D=2,m=5`, A0 and A1 each admit 15
  candidates and each candidate set contains 9/17 facts across 3/4 domains.
  A0 packs 7/17; A1 packs 9/17. A2 admits 15 candidates but only 5/17 facts,
  all civil.
- The best A1 trace admits turns `114,1,2,43,3`, then `54,84,113,27,45`, then
  `112,110,78,26,28`. Generic art turns 43, 45, and 54 enter; registered art
  fact sources do not.
- In the Q11 full ranking, art-bearing source turns rank 27, 30, and 87. Turn
  55, the only single episode containing all four registered art facts, ranks
  87. Its cosine is 0.1091.
- In the sealed 24-query Tier 2 corpus, raw whole-episode dense retrieval scores
  0.8750 lookup, 0.5938 chained, and 0.1875 enumeration recall. Span-dense
  retrieval scores 0.7500, 0.5938, and 0.6458 respectively.

### 2.3 Degenerate and absorbing behavior

- The E006 `seen` exclusion forces a new nonempty `top_m` while unseen episodes
  remain. More depth therefore guarantees more candidates; it does not certify
  a better cue.
- E006 Rev5 found no repeated hit set or fixed point in 48/48 feedback cells,
  but final-cue cosine remained 0.8818-0.9982. The chain moves without escaping
  the original semantic neighborhood.
- P3 A2's local graph collapses to the civil neighborhood at the primary cell.
  Graph traversal can therefore be active while breadth is false.
- Q11's binary breadth score can remain zero after a payload rises from 6/17 to
  13/17 correctly attributable facts. Fact availability can improve while the
  study score remains unchanged.

These observations define the tests below. No threshold was selected by
searching post-lock outputs.

## 3. Preflight Part 2 - Checklist

The implementation must emit `preflight.json`. No diagnostic output may be
written unless every item below passes in order.

| Check | Required executed evidence |
|---|---|
| PF1 | Recompute every Section 1 hash, byte count, parseability, and row/cell count. |
| PF2 | AST/source checks and artifact checks reproduce every identity in Section 2.1. Names alone do not pass. |
| PF3 | A planted bad hash and a planted label-read-before-selection attempt both stop before diagnostic output. |
| PF4 | Reproduce the known primary counts 15 candidates for A0/A1/A2, candidate facts 9/9/5, and packed facts 7/9/5. Every disposition is executable on a synthetic fixture. |
| PF5 | Episode comparisons use canonical content SHA-256. Turn numbers are coordinates only, never identity keys. |
| PF6 | Reproduce E006's best 9/17 payload identity and P3's primary A0/A1/A2 candidate, selection, and payload digests. Reproduce all registered Tier 2 aggregate values exactly. |
| PF7 | Reproduce all 48 E006 feedback traces and the registered P3 absorbing-state evidence. Demonstrate that depth increases candidate count on the real Q11 trace. |
| PF8 | State the limit: one Q11 trace plus 24 frozen holdout queries can identify this trace's mechanics, not population performance or a live-answer effect. |
| PF9 | Emit a surrogate table showing which claims can pass while discovery, delivery, reader use, correctness, or historical truth is false. |
| PF10 | Emit `live_run_authorized=false`, `answer_correctness_evaluated=false`, and `outcome_ceiling=CHARACTERIZED`. |

## 4. Diagnostic D0 - Biological implementation-gap inventory

The audit maps the actual E006 source to the reference principles. Each entry is
one of `IMPLEMENTED`, `PARTIAL`, or `ABSENT`, with source-line and executable
behavioral evidence.

The following criteria are locked:

| Reference mechanism | `IMPLEMENTED` requires |
|---|---|
| P1 tag decay | Per-episode tag state set uniformly at write and expired by time. |
| P2 symmetric capture | An independent event modifies episodes on both temporal sides without reading their content. |
| P3 retroactive selection | A later event changes earlier episodes' consolidation state. |
| P4 sequential/recombinant replay | Stored sequences and prior structure jointly alter connectivity offline. |
| P5 storage/retrieval separation | Episode connectivity and accessibility are independent persisted quantities. |
| P6 competitive plasticity | Retrieval strengthens selected items and suppresses cue competitors. |
| P7/P9 update lineage | Contradiction creates a lineage trace and changes retrievability without deleting content. |
| P8 transformation | Consolidation lowers episode detail accessibility while strengthening extractive gist. |
| P10 fast/slow stores | Mechanically separate episodic and semantic stores with transfer. |

An iterative cue or a cosine graph is not sufficient for P4 or P5. The D0
result is descriptive and cannot itself explain benchmark performance.

## 5. Diagnostic D1 - Matched-volume chain decomposition

Primary cell: P3 `D=2,m=5`, exactly 15 candidates, 32,000-character budget.

For A0 fixed query and A1 mean-context chain, measure:

- candidate identity set;
- selected identity sequence;
- candidate and packed facts by domain;
- exact packed characters; and
- facts lost only at packing.

Primary disposition, first matching:

1. `CHAIN_DISCOVERY_GAIN`: A1 candidate facts exceed A0 candidate facts.
2. `CHAIN_PACKING_ONLY_GAIN`: candidate facts are equal and A1 packed facts
   exceed A0 packed facts.
3. `CHAIN_NO_GAIN`: neither candidate nor packed facts increase.
4. `CHAIN_REGRESSION`: A1 has fewer candidate facts than A0.

The outcome is based on fact identities, not only counts. Equal counts with
different facts must be reported and cannot be called equivalent discovery.

## 6. Diagnostic D2 - Temporal-adjacency opportunity ceiling

This is an oracle ceiling, not a retrieval arm. It asks whether the missing art
source is mechanically adjacent to episodes the best E006 chain already found.

Start from the fixed 15-candidate identity set for
`D2_m5_wq0.3_rho0.5`. For each candidate, add eligible stored episodes whose
source-turn coordinate differs by at most `r`, using locked radii `r=1` primary
and `r=2` sensitivity. Deduplicate by content SHA-256. Do not rank or pack.

Report newly reachable source identities, facts, and domains; the shortest
candidate-to-source turn path; and whether turn 55 becomes reachable.

- `ADJACENCY_OPPORTUNITY_PRESENT`: `r=1` adds at least one missing art fact.
- `ADJACENCY_OPPORTUNITY_ABSENT`: `r=1` adds no missing art fact.

This can establish only reachability opportunity. Because labels are used to
measure the expanded set and no budgeted selector is run, it cannot establish
that adjacency retrieval would select, deliver, or improve an answer.

## 7. Diagnostic D3 - Representation and objective decomposition

Recompute the committed Tier 2 results for corpus `c121_l` from row-level data.
Compare M2 raw whole-episode dense retrieval with M5 span-dense retrieval under
the already committed 32,000-character budget.

Report macro fact recall by query class (`lookup`, `chained`, `enumeration`),
per-domain recall, exact query-level gains/losses/ties, and selected character
counts. No new representations or queries may be introduced.

- `ENUMERATION_GRANULARITY_GAP`: M5 enumeration recall exceeds M2 enumeration
  recall and the gain is positive on at least one query identity.
- `NO_ENUMERATION_GRANULARITY_GAP`: otherwise.

This contrast identifies an association between a registered span
representation and enumeration availability on the frozen corpus. It does not
identify user-only encoding, causal fact dilution, or a live-answer benefit.

## 8. Diagnostic D4 - Art storage, cueing, and reader evidence

D4 separates three questions that prior summaries conflated:

1. **Stored:** do registered art facts exist in eligible source episodes?
2. **Broadly cued:** do they enter Q11 candidates and the packed payload?
3. **Used by a reader:** when directly delivered, are targeted art answers
   correct without unsupported substitutions?

D4 may compare committed corrected Study 007 and Study 009 L targeted art
scores with LV-001's committed absent-art payload and generated answers. The
comparison must list model/run/arm differences and is always labeled
`CROSS_RUN_CONFOUNDED`.

The strongest allowed conclusions are:

- `STORED_BUT_NOT_BROADLY_CUED` if art facts exist in eligible episodes but the
  best E006 chain has 0/4 art candidate facts.
- `DIRECT_CUE_RECALL_OBSERVED` if a committed, audited evidence-present run
  scores all targeted art criteria correctly.
- `PRIOR_CONFLICT_NOT_IDENTIFIED` unconditionally for the hypothesis that the
  model's pretrained art knowledge caused substitution. The repository has no
  matched reader experiment varying only evidence wording, and no independently
  adjudicated historical-truth variable.

No cross-run score difference is causal evidence.

## 9. Ordered execution and stopping

1. Verify the design SHA and Section 1 inventory.
2. Run Preflight PF1-PF10. Stop on any failure.
3. Seal all candidate, selection, and payload identities for D1 and D2 before
   loading any fact key or evaluation labels.
4. Run D0 and D1.
5. Run D2 only if D1 reproduces the fixed best-chain candidate set exactly.
6. Run D3 only if the Tier 2 aggregate reproduction is exact.
7. Run D4 only after all historical score hashes are recorded in the manifest.
8. Emit one deterministic result tree, CSV tables, a manifest, and a report.
9. Run the focused tests twice in separate processes and require byte-identical
   result digests.

No failed gate may be bypassed by omitting the affected diagnostic. The study
stops with the gate failure and reports no downstream result.

## 10. Interpretation rules

The primary result is D1's first-matching disposition. D0, D2, D3, and D4 are
separate characterized findings and must not be combined into a synthetic score.

Forbidden conclusions include:

- chained retrieval works live;
- temporal adjacency would improve Q11;
- the biological architecture is validated;
- art is inherently difficult for the model;
- pretrained knowledge caused the art substitutions;
- a zero Q11 score means zero recall; or
- any offline fact count is an answer-correctness result.

## 11. Predictions

Written before implementation and execution:

1. D0 will mark every biological mechanism except a weak resemblance to
   sequential cue updating as absent; E006 has no separate storage substrate.
2. D1 will yield `CHAIN_PACKING_ONLY_GAIN`: A0 and A1 will expose the same 9/17
   candidate facts, while A1 packs 9/17 versus A0's 7/17.
3. D2 will yield `ADJACENCY_OPPORTUNITY_PRESENT` because candidate turn 54 is
   adjacent to the all-four-art source at turn 55.
4. D3 will yield `ENUMERATION_GRANULARITY_GAP`; span-dense enumeration recall
   will exceed raw whole-episode dense recall, while lookup will not improve.
5. D4 will show art facts stored but not broadly cued, and at least one audited
   direct-cue run with correct targeted art recall. Prior-conflict causality will
   remain unidentified.

## 12. Deliverables and closeout

Implementation begins only after this file is committed. Required outputs:

- `src/analysis/ba001_benchmark_causal_audit.py`;
- focused tests under `tests/`;
- `artifacts/ba001/preflight.json`;
- `artifacts/ba001/results.json`;
- `artifacts/ba001/*.csv` diagnostic tables;
- `artifacts/ba001/manifest.json`;
- `BA_001_REPORT.md` with this design's full commit SHA in its header; and
- closeout updates to root `README.md` and `AGENTS.md`.

The report must distinguish measurement from interpretation and retain the
`CHARACTERIZED` ceiling even if every prediction is correct.

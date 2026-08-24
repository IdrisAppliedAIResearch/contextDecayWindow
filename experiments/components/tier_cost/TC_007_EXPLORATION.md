# TC-007 Preflight — protected spread beside ranked dense retrieval

**Status:** `PREFLIGHT PART 1 AND PF1-PF10 PASS — REGISTRATION MAY PROCEED`  
**Date:** August 23, 2026  
**Artifacts:** `artifacts/tc007/preflight/`

## Behavioral identity

Dense ranks every LoCoMo adjacent-turn pair by descending carried float32
cosine. Shipped A3 greedily combines nonnegative relevance with a 0.1 bonus for
the first admission from each of 16 deterministic clusters. Pure facility
location (`A2_r0.0`) greedily represents the whole candidate store without a
query-relevance term. TC-007 gives dense a solo-accounted half, then admits
distinct spread candidates against a solo-accounted half, renders once, and
returns all actual merged slack to dense.

The facility arm is the committed E005 `A2_r0.0`: it is the unmixed facility
objective and E005's raw fact-count leader. No TC-007 result or sweep selected
it. A3 is the shipped `A3_l0.1_r0.0_k16` configuration.

## What the real traces did

- TC-003 C5 reproduced at 16k as floors/ranked `718/748` and at 32k as
  `806/811`.
- All 2,613 TC-005 dense payloads at 8k, 16k, and 32k reproduced by identity
  and byte digest.
- Both spread routes admitted distinct candidates on 871/871 questions at both
  budgets. Proposal ownership would suppress spread on 871/871 because every
  complete ranking proposes the full store; admission ownership does not.
- At 16k, A3 admitted a median 27 distinct spread candidates and facility 27;
  at 32k the medians were 55 and 50. Both protected halves bound on every real
  question.
- Wrapper savings and skip-on-overflow slack left a median 118-119 characters
  after the initial merge. Dense reclaimed a median one additional candidate.
- No payload exceeded its exact 16k or 32k limit and no identity serialized
  twice.

Dense-only 1% budget shams fix the practical bands before treatment outcomes:

| Budget | Combined complete | Breadth complete | Targeted complete |
|---:|---:|---:|---:|
| 16,000 | 2 | 0 | 2 |
| 32,000 | 0 | 0 | 0 |

## Degenerate and positive controls

Constructed controls demonstrate unique spread admission, displacement of the
only planted targeted carrier, no spread candidates with complete slack return,
all proposals overlapping, all proposals outside initial dense admissions,
oversized candidates, and a budget below the empty-wrapper cost. Real traces
cover no returned admission, one and two returned admissions, full proposal
overlap, both routes binding, and every spread proposal class remaining
available until admission-resolved dedup.

## PF1-PF10

- **PF1:** TC-003 and TC-005 committed inputs are hash-identified in
  `tc007_preflight_part1.json`; 871 questions, 1,365 candidate pairs across four
  conversations, two budgets, two spread routes, and 3,484 trace rows exist.
- **PF2:** the behavioral identity above is executed in the trace artifact; all
  named phases, ownership rules, selectors, and budgets are observed.
- **PF3:** the registered runner must require a clean, committed G0 before its
  worker can generate outcome rows; this is tested in implementation.
- **PF4:** `tc007_preflight_pf4_reachability.json` shows treatment, control,
  signal, neutral, and targeted-guardrail branches reachable in every cell.
- **PF5:** comparison uses question and candidate content identities only.
- **PF6:** TC-003 C5 and TC-005 dense reproduce as listed above.
- **PF7:** the allocator has no feedback and is a pure function of frozen
  orders, identities, and budgets; fresh-process identity remains a run gate.
- **PF8:** all 871 unique offline questions are used. This detects availability
  differences but cannot detect reader use; no live 120-turn claim is made.
- **PF9:** more sessions/clusters can pass without required evidence; complete
  evidence can pass without reader use; proposal ownership can relabel rather
  than add; a full budget can hide half-budget inefficiency.
- **PF10:** availability is not an answer verdict. TC-006 remains required
  before adoption.

The preflight opened no aggregate A3/facility evidence contrast. Evidence was
used only for the frozen population counts, historical reproductions, and the
dense-only sham bands. Treatment outcomes remain for the registered run.

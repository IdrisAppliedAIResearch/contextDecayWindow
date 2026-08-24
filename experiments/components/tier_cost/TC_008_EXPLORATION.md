# TC-008 Preflight — relevance-gated source-session spread

**Status:** `PREFLIGHT PART 1 AND PF1-PF10 PASS — REGISTRATION MAY PROCEED`  
**Date:** August 23, 2026  
**Artifacts:** `artifacts/tc008/preflight/`

## Behavioral identity

`A_SPLIT_SESSION` uses TC-007's carried allocator and the carried A3 greedy
objective, `max(float32 dense cosine, 0) + 0.1 * novelty`, but novelty is the
first selector admission from a source conversation session rather than an
embedding cluster. Dense and session routes receive equal solo allowances;
actual admissions are deduplicated, serialized once, and all slack returns to
dense.

The grouping key is the corpus `session_id`, assigned stable integers in source
session order. The treatment is not a round-robin session floor: relevance
still participates in every spread choice, and only the first selected member
of each session receives the `0.1` bonus.

## What the real traces did

- All 3,484 TC-007 control/A3 question-budget selections and payload digests
  reproduced exactly.
- Session spread differs from both dense and A3 on 871/871 questions at both
  budgets. It binds on 871/871 and has zero budget violations.
- At 16k, session spread represents a median 30 sessions versus 24 for dense
  and 24 for A3. It adds a median 14 sessions beyond the initial relevance
  allowance and admits a median 27 protected candidates.
- At 32k, it represents a median 30 sessions versus 29 for dense and 29 for A3;
  it adds a median 7 sessions and admits a median 55 protected candidates.
- At 16k, candidates added only by treatment have median dense rank 77; dense
  candidates displaced only by treatment have median rank 47. At 32k those
  medians are 131 and 104. The mechanism therefore creates both a real breadth
  opportunity and a real semantic displacement risk.
- Exact payload sizes stay at or below their budgets. Median treatment payload
  size is 15,975 characters at 16k and 31,975 at 32k.

The 70,736-row mechanism trace records each protected admission's candidate,
source session, dense relevance, novelty bonus, marginal objective, and whether
the bonus marked a new session in selector order. It contains no treatment
evidence labels or outcomes.

## Frozen practical bands and PF4

Dense-only plus/minus 1% budget shams fix these bands before treatment outcomes:

| Budget | Breadth share questions | Breadth identities | Breadth complete | Combined complete | Targeted complete |
|---:|---:|---:|---:|---:|---:|
| 16,000 | 0 | 0 | 0 | 2 | 2 |
| 32,000 | 0 | 0 | 0 | 1 | 0 |

The family contains six directional cells: breadth evidence share, combined
complete delivery, and targeted complete delivery at two budgets. Works alpha
is `0.01/6 = 0.0016666666666666668`; signal alpha is
`0.10/6 = 0.016666666666666666`. With 44 breadth questions, ten all-favourable
discordances clear works and six clear signal. PF4 demonstrates session-works,
dense-works, signal, guardrail-failure and neutral branches can all fire.

## Degenerate and positive controls

- With `lambda=0`, the selector reduces to descending nonnegative dense
  relevance with stable source ties.
- When every candidate has one session, exactly one novelty bonus fires.
- A constructed second session with slightly lower relevance overtakes a
  redundant same-session candidate, proving the grouping can change order.
- On real traces the treatment differs from A3 on every question at both
  budgets, so source sessions and embedding clusters are not behaviorally
  interchangeable.
- The selector and allocator are pure and have no feedback or absorbing state.
  The complete 1,742 question-budget replay is deterministic.

## PF1-PF10

- **PF1:** Corpus SHA-256 is
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`;
  cache SHA-256 is
  `2ba617018a1b043bf439bb50e756191d8141fb7ca01a2e4a68c9eb822eba26f8`.
  The artifact identifies the TC-007 outputs and all three mechanism-source
  hashes. Population is 871 questions and 1,365 candidates in four conversations.
- **PF2:** The behavioral identity above is executed across every real trace;
  the admission ledger records the named relevance and session-novelty terms.
- **PF3:** The registered runner must require a clean, committed G0 and produce
  selections before importing or joining treatment evidence.
- **PF4:** `tc008_preflight_pf4_reachability.json` makes every inferential and
  stop branch achievable, including both guardrail directions.
- **PF5:** Questions and candidates use stable content identities plus frozen
  duplicate ordinals; no paths, timestamps or generated ids are comparison keys.
- **PF6:** All 3,484 TC-007 control/A3 payloads reproduce by ordered identity and
  byte digest.
- **PF7:** There is no feedback. The selector and allocator are pure functions;
  fresh-process byte identity remains a run gate.
- **PF8:** The full 871-question offline replay can detect availability changes,
  not reader use, answer quality, enterprise transfer or an optimal budget.
- **PF9:** More represented sessions, session touch and evidence share can all
  rise without a correct answer. Complete and targeted guardrails are joint;
  a later reader study is still necessary.
- **PF10:** TC-008 does not generate answers or authorize adoption. The selected
  contexts are intended to support separately registered reader validation.

The evidence-blind source audit passed on the allocator, selector and deployed
selection primitive. A planted `evidence_key/q_facts_key` import was detected.
The replay used 2,247 cache hits, zero misses, zero embedding calls and zero
LLM/generative calls.

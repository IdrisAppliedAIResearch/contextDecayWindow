# TC-007 Pre-Registration — ranked dense retrieval beside protected spread

**Status:** `PRE-REGISTERED — OFFLINE AVAILABILITY STUDY`  
**Date locked:** August 23, 2026  
**Design and Preflight commit:** `14ae420d04edc4d43e5cd512a8de3559ab32d08e`  
**Preflight Part 1 SHA-256:** `b54f98b7a3c61f2968f2fdc5a15d9efb5ef4f39aadb5062132d1885a8aac018a`  
**Preflight PF4 SHA-256:** `ab559ede686cd41c80a2f8f0748f8ca90c8d18237a616607fe94a8a2eb73f63e`  
**Preflight trace SHA-256:** `fc3deb4e3d228c3f0b0696a52b5c676f3a1c818da9af9efb02a3f59e17094443`

This file is the authoritative parameter source and is immutable after this
commit. A genuine correction requires a standalone amendment. No observed
treatment result may change an arm, budget, population, endpoint, band, alpha,
guardrail, tie-break, or disposition below.

## 1. Question and claim boundary

Holding LoCoMo candidates, adjacent-turn-pair granularity, dense relevance
order, embeddings, renderer, skip-on-overflow policy, exact total budget, and
evidence measurement fixed, does an admission-resolved 50/50 allocator binding
dense relevance beside shipped A3 or pure facility-location spread deliver more
complete evidence than giving dense relevance the entire budget, while also
improving breadth and avoiding a demonstrated targeted regression?

This is offline evidence availability. It cannot establish reader accuracy,
production adoption, unseen-corpus transfer, an optimal spread share, or an
adaptive enterprise budget. TC-006 remains required before a reader claim.

## 2. Frozen population and inputs

- Corpus SHA-256:
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- Development conversations: `conv-41`, `conv-42`, `conv-47`, `conv-48`.
- Candidate unit: the same 1,365 adjacent-turn pairs used by TC-001 through
  TC-005, with content-derived identities and unchanged text/vectors.
- Unique questions: 871. Eligible: 868. Ineligible: 3.
- Targeted: 704 eligible questions whose evidence is confined to one pair in
  one session.
- Breadth: 44 eligible questions whose evidence spans at least three sessions.
- Other eligible: 120.
- Question comparison key: content SHA-256 plus frozen duplicate ordinal.
  Generated ids, paths, and timestamps are forbidden keys.

## 3. Frozen routes

### Relevance

`DENSE` is TC-005's selected fallback: descending carried normalized float32
query/candidate matrix product, with `(session_order, pair_order)` ties. It ranks
the complete store and has no threshold or top-k cut.

### Spread

- `A3`: shipped `A3_l0.1_r0.0_k16`; nonnegative dense relevance plus `0.1`
  for the first admission from each of 16 deterministic clusters, cost exponent
  zero, with carried greedy ties.
- `FACILITY`: committed E005 `A2_r0.0`; pure facility-location marginal gain
  over the complete store, cost exponent zero, with carried greedy ties.

`A2_r0.0` is frozen because it is the unmixed facility objective and E005's raw
fact-count leader. No LoCoMo evidence outcome or TC-007 sweep selected it.

## 4. Allocator contract — TC-007's single new component

For total `B in {16_000, 32_000}`, each initial solo allowance is exactly
`H=B/2`, hence 8,000 or 16,000 characters.

1. Produce complete dense and spread orders without evidence labels.
2. Dense traverses its order and admits what fits `H`, charged as a solo
   retrieved-STM payload.
3. Spread traverses its complete order, skips identities already **admitted**
   by dense, and admits distinct candidates fitting its own solo `H`.
4. A candidate dense ranked but did not admit remains available to spread.
5. Merge initial admissions in phase order, serialize once, and deduplicate by
   stable candidate content identity.
6. Dense resumes its unchanged order and fills every candidate that fits the
   actual remaining total capacity. Unused spread allowance and wrapper savings
   therefore return to dense.
7. Each identity serializes once, is owned by its admitting phase, and is
   charged to `initial_relevance`, `protected_spread`, or `returned_relevance`.
8. Exact serialized payload length, including wrappers and separators, must not
   exceed `B`; candidates are skipped on overflow and never truncated.

Proposal overlap never establishes ownership. Relevance has first claim only
on what fits its initial half. Role order is architectural and is not permuted.

## 5. Arms

| Arm | Frozen behavior | Role |
|---|---|---|
| `A_RELEVANCE_FULL` | dense receives full `B` | binding control |
| `A_SPLIT_A3` | allocator with A3 protected spread | treatment 1 |
| `A_SPLIT_FACILITY` | allocator with facility protected spread | treatment 2 |
| `A_SHAM` | same phases, no spread admissions; all slack returns to dense | G0 cost control |

TC-003 `A_FLOORS_DUAL`/`A_DUAL_RANKED` and TC-005 `A_DENSE` are reproduction
anchors, not additional inferential arms. No recency, BM25, RRF, chunking,
query expansion, new embedder, or reader is included.

## 6. Endpoints and rows

The measured boolean is **complete required-evidence delivery**: every candidate
carrying resolved required evidence is serialized. Any-evidence and required
fact count are descriptive.

Each treatment-budget cell has three registered reads:

1. `combined`: complete delivery over all 868 eligible questions;
2. `breadth`: complete delivery over the 44 breadth questions; and
3. `targeted`: complete delivery over the 704 targeted questions.

Every row records complete route orders and digests; proposal overlap; initial
dense admissions/spend; spread duplicate skips, admissions/spend, and binding;
returned dense admissions; admission owner/phase; exact wrappers, separators,
candidate costs and total; selected/dropped identities and reasons; session and
cluster concentration; evidence delivered by route; and final payload digest.

## 7. Paired tests, bands, and multiplicity

There are 12 directional cells: two treatments x two budgets x three registered
reads. Each reports treatment-only gains, control-only losses, ties, net
`gains-losses`, and exact one-sided sign-test tails in both directions.

- Works alpha: `0.01 / 12 = 0.0008333333333333334`.
- Carries-signal alpha: `0.10 / 12 = 0.008333333333333333`.
- A direction clears only when net is **strictly greater** than its practical
  band and its one-sided p-value is at or below the applicable alpha.
- Dense-only 1% budget shams froze the bands:

| Budget | Combined | Breadth | Targeted |
|---:|---:|---:|---:|
| 16,000 | 2 | 0 | 2 |
| 32,000 | 0 | 0 | 0 |

A budget cell jointly works only when the treatment direction clears the works
bar on both `combined` and `breadth`, and the adverse dense direction does not
clear the targeted works bar. This prevents session/cluster spread, aggregate
gain, or breadth gain alone from passing.

A targeted guardrail fires only when dense clears both the registered targeted
band and works alpha. An unresolved negative net is reported but is not called
a demonstrated targeted regression.

## 8. Per-treatment dispositions

Apply in order, separately to A3 and facility.

1. `TREATMENT_WORKS`: the joint works condition passes at both budgets.
2. `CONTROL_WORKS`: the treatment did not work and dense clears the works bar
   on combined complete delivery at both budgets, or the targeted guardrail
   fires at both budgets.
3. `TREATMENT_CARRIES_SIGNAL`: neither works branch fired; at least one budget
   clears treatment signal bars on both combined and breadth; at the other
   budget neither combined nor breadth net is below its negative practical
   band; and no targeted works guardrail fires.
4. `CONTROL_CARRIES_SIGNAL`: symmetric combined-plus-breadth signal rule in the
   dense direction, or one targeted works guardrail with no opposite treatment
   works cell.
5. `MIXED_OR_NO_DIFFERENCE`: every remaining pattern.

The lower tier is successor evidence only. It cannot authorize adoption.

If at least one treatment works, the architecture disposition is
`PROTECTED_SPREAD_WORKS`. If both work, freeze the one with larger summed
combined net; then larger summed breadth net; then fewer summed targeted losses;
then A3. If neither works, no split architecture is selected and dense remains
the fallback. A carries-signal arm may be named for follow-up but cannot select.

## 9. G0 — binding before outcomes

G0 must be committed before outcome generation and must pass:

1. this file is committed and byte-identical to its registered SHA-256;
2. all three Preflight artifacts match their header hashes;
3. TC-003 C5 reproduces `718/748` at 16k and `806/811` at 32k;
4. all 2,613 TC-005 dense payloads reproduce by identity and digest;
5. the final mechanism is identical to the committed Preflight mechanism on all
   3,484 real treatment-budget traces;
6. `A_SHAM` is byte-identical to `A_RELEVANCE_FULL` on every question/budget;
7. both treatment routes are active and bind on a real trace, positive controls
   gain unique spread and displace targeted evidence, and all PF4 branches remain
   reachable;
8. mechanism source cannot import/read evidence, answer, rubric, or key files;
   a planted violation proves the audit can fail;
9. cache misses and LLM/generative calls are zero; embedding calls are reported
   separately under the programme's model-free terminology;
10. source hashes, one-thread settings, and a passing full suite are recorded.

Any failure stops as `INSTRUMENT_FAILURE`; treatment outcomes are not generated.

## 10. Registered run

After committed G0, compute the control and both treatments for all 871 unique
questions at both budgets. Generate question-level outputs before aggregate
analysis. Two fresh worker processes must produce identical ordered identities,
attributions, payloads, outcomes, and file digests. Reject cache misses, budget
overruns, duplicate keys, unregistered arms/budgets, dirty worktree, source
drift, or nondeterminism.

This full-population offline replay is the registered ablation. No live 120-turn
run is authorized. The report must state availability only, name every works and
signal margin, state whether spread added evidence or merely displaced it, and
freeze contexts for a separately registered TC-006 reader validation.

## 11. Surrogates and exclusions

Session count, cluster count, spread spend, candidate count, character fill,
any-evidence, and complete evidence can all pass without improving an answer.
Complete combined delivery can rise while breadth falls; breadth can rise by
sacrificing direct questions; ownership can relabel a shared set rather than add
one. None of those surrogates overrides the joint rule.

Conversely, a useful reader effect could exist without clearing this availability
bar. TC-007 does not test that possibility. It also does not select an enterprise
budget, compare spread shares, tune selectors, or change the deployed read path.

## 12. Execution and closeout order

1. Commit this registration alone and record its SHA-256.
2. Implement registered G0/run code and tests without changing carried routes.
3. Commit passing G0.
4. Run and commit question-level artifacts, then aggregate verdicts.
5. Report with registration commit and SHA-256 in the header.
6. Update README, AGENTS digest (<=400 characters), roadmap, dependency log,
   memory, and ERRATA only if a published number changes.
7. Update and push the TC-007 PR. Do not start TC-006.

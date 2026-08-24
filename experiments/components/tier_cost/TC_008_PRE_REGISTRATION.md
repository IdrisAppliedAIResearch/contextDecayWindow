# TC-008 Pre-Registration — relevance-gated source-session spread

**Status:** `PRE-REGISTERED — OFFLINE AVAILABILITY STUDY`
**Date locked:** August 23, 2026
**Design and Preflight commit:** `bc85dfa7b42a7ca1e5784a434fd9eea2a7e7d4b6`
**Preflight Part 1 SHA-256:** `dab50e1a3935d63755824c8d7ea9f7bb9f57263422338f227eeea44ca6a0f971`
**Preflight PF4 SHA-256:** `b3de97b6ad905c0a9311f0dae2a03f407003f50139ff5594d0422f0ac7b79711`
**Preflight allocation trace SHA-256:** `d678d873f9a939b0265c4b7ed1875ce81627531b7eadc2e008468af21208d27b`
**Preflight mechanism trace SHA-256:** `2ac5f84c84284ee75bc1cd3b4d3bf4645947979f623006be6beb75f5db7066dd`

This file is the authoritative parameter source and is immutable after this
commit. Any genuine correction requires a standalone amendment. No treatment
outcome may change an arm, population, endpoint, band, alpha, guardrail,
tie-break or disposition below.

## 1. Question and claim boundary

Holding LoCoMo candidates, embeddings, dense ranking, exact budgets, TC-007's
50/50 allocator, renderer, admission-resolved deduplication and slack return
fixed, does replacing A3's embedding-cluster novelty with query-relevant source
session novelty improve delivery of distributed breadth evidence without a
demonstrated loss of dense semantic retrieval?

This is an offline availability study. It does not generate answers, establish
reader accuracy, select a production budget, authorize adoption, or claim
transfer beyond the frozen LoCoMo development set. Its purpose is to freeze a
candidate context architecture for separately registered reader validation.

## 2. Frozen inputs and population

- Corpus SHA-256:
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- Conversations: `conv-41`, `conv-42`, `conv-47`, `conv-48`.
- Candidate unit: the same 1,365 adjacent-turn pairs used by TC-001 through
  TC-007, with unchanged content-derived identities, text and vectors.
- Questions: 871 unique; 868 eligible; 3 ineligible.
- Targeted: 704 eligible questions whose required evidence is confined to one
  pair in one source session.
- Breadth: 44 eligible questions whose required evidence spans at least three
  source sessions. Other eligible: 120.
- Question comparison key: content SHA-256 plus frozen duplicate ordinal.
  Candidate comparison key: stable content identity. Paths, timestamps and
  generated ids are forbidden comparison keys.

## 3. Frozen common route and allocator

`DENSE` ranks the complete candidate store by descending normalized float32
query/candidate matrix product, with `(session_order, pair_order)` ties. There
is no similarity threshold and no top-k cut.

For `B in {16_000, 32_000}` exact serialized characters, TC-007's allocator is
unchanged:

1. Dense and spread each receive an initial solo-accounted allowance `B/2`.
2. Dense admits fitting candidates in dense order.
3. Spread admits fitting candidates in its own order, skipping identities
   actually admitted by dense. A dense proposal that did not fit remains
   available to spread.
4. Initial admissions merge in phase order, serialize once and deduplicate by
   candidate content identity.
5. Dense resumes its unchanged order and consumes all actual remaining total
   capacity. Unused spread allowance and wrapper savings return to dense.
6. Candidates are skipped on overflow, never truncated. Each identity renders
   once and exact payload length may not exceed `B`.

## 4. Arms and the single changed component

| Arm | Frozen behavior | Role |
|---|---|---|
| `A_DENSE_FULL` | Dense receives the complete budget | binding control |
| `A_SPLIT_SESSION` | 50/50 dense plus source-session spread | treatment |
| `A_SPLIT_A3` | TC-007 50/50 dense plus 16-cluster A3 | descriptive reference |

`A_SPLIT_SESSION` uses the carried A3 objective with only its grouping input
changed. For candidate `i`, dense cosine `s_i`, selected set `S`, and source
session `g_i`:

`gain(i | S) = max(s_i, 0) + 0.1 * 1[g_i not represented in S]`

Cost exponent remains zero. Source session ids receive stable integer labels in
source session order. The selector emits a full deterministic permutation;
the unchanged allocator consumes it. The novelty term fires in selector order,
not allocator-admission order. No session floor, round robin, adaptive share,
query classifier, chunking, summary, BM25, RRF, adjacency, new embedder or
reader is included.

`A_SPLIT_A3` is not an inferential arm and adds no multiplicity cell. It is
reported only to determine whether source-session grouping changes the pattern
observed under TC-007's embedding clusters.

## 5. Frozen endpoints

Treatment is compared pairwise with `A_DENSE_FULL` at each budget.

### Primary breadth endpoint

For each of the 44 breadth questions, compute the exact count and share:

`delivered required candidate identities / all required candidate identities`

A question is favourable to treatment when its delivered required-identity
count is larger under treatment, adverse when smaller, and tied otherwise.
The paired read reports favourable questions, adverse questions, ties, net,
and exact one-sided sign-test tails in both directions. It also reports the sum
of treatment-only required identities, control-only required identities and
their identity net. A larger share caused only by a smaller denominator is
impossible because the denominator is frozen per question.

### Joint guardrails

- `breadth_complete`: all required candidate identities delivered on each of
  the same 44 questions; practical noninferiority only.
- `combined_complete`: complete evidence delivery on all 868 eligible questions.
- `targeted_complete`: complete evidence delivery on the 704 targeted questions.

Complete endpoints report treatment-only gains, control-only losses, ties, net
and exact one-sided sign-test tails. Any-evidence, represented sessions,
required-session touch, candidate count, character spend and admission owner
are descriptive only.

## 6. Bands, multiplicity and budget-cell decisions

There are six directional inferential cells: breadth share, combined complete
and targeted complete at two budgets. Each cell reports both directional tails.

- Works alpha: `0.01 / 6 = 0.0016666666666666668`.
- Carries-signal alpha: `0.10 / 6 = 0.016666666666666666`.
- A direction clears only when its net is strictly greater than the applicable
  practical band and its one-sided sign-test p-value is at or below alpha.

Dense-only plus/minus 1% budget shams froze the bands:

| Budget | Breadth share questions | Breadth identity net | Breadth complete | Combined complete | Targeted complete |
|---:|---:|---:|---:|---:|---:|
| 16,000 | 0 | 0 | 0 | 2 | 2 |
| 32,000 | 0 | 0 | 0 | 1 | 0 |

At one budget, `SESSION_BREADTH_WORKS` requires all of:

1. treatment clears the breadth-share question works bar;
2. breadth required-identity net is strictly greater than its band;
3. breadth-complete net is at least the negative breadth-complete band;
4. dense does not clear the combined-complete works bar; and
5. dense does not clear the targeted-complete works bar.

`SESSION_BREADTH_SIGNAL` substitutes signal alpha in item 1 and retains items
2-5. A `DENSE_GUARDRAIL_FIRE` occurs when dense clears either combined or
targeted complete at works alpha. A `DENSE_BREADTH_WORKS` cell is the exact
directional mirror of items 1-3 and does not require a guardrail.

PF4 shows that with 44 breadth questions, ten all-favourable discordances clear
works and six clear signal at the frozen zero question band. Every benefit,
harm, guardrail, noninferiority and neutral branch is mechanically reachable.

## 7. Study disposition

Apply in order:

1. `SESSION_SPREAD_WORKS`: `SESSION_BREADTH_WORKS` passes at both budgets.
2. `DENSE_WORKS`: session does not work, and either `DENSE_BREADTH_WORKS`
   passes at both budgets or `DENSE_GUARDRAIL_FIRE` occurs at both budgets.
3. `SESSION_SPREAD_CARRIES_SIGNAL`: neither works branch fired; session breadth
   signal passes at least one budget; at the other budget breadth question
   net, breadth identity net and breadth-complete net are all nonnegative; and
   no dense guardrail fires at either budget.
4. `DENSE_CARRIES_SIGNAL`: the exact breadth-signal mirror of item 3, or one
   dense guardrail fires without an opposite session-works cell.
5. `MIXED_OR_NO_DIFFERENCE`: every remaining pattern.

Only `SESSION_SPREAD_WORKS` freezes treatment contexts as the preferred TC-008
input to a later reader study. A carries-signal result supports follow-up but
does not select an architecture. No disposition changes deployed code.

## 8. Registered diagnostics and attribution

For every question, budget and arm, preserve complete route orders/digests,
initial allowances and admissions, spread novelty/objective trace, actual
duplicate skips, slack return, admission owners, exact serialized costs,
selected/dropped identities, payload digest, represented source sessions and
dense ranks of treatment additions/displacements.

After formal outcomes are written, report:

- breadth gains/losses by LoCoMo category;
- which required identities and source sessions were added or displaced;
- whether gains are unique to session grouping, shared with A3, or already
  available under A3;
- direct-question losses and whether they arise from the protected half or the
  session novelty order; and
- every disagreement between identity share and complete evidence.

These diagnostics explain the registered result; they cannot override it.

## 9. G0 — binding before outcomes

G0 must be committed before treatment outcomes and must pass:

1. this file is committed and byte-identical to its recorded SHA-256;
2. the four Preflight artifacts match the hashes in this header;
3. all 3,484 TC-007 control/A3 question-budget selections and payload digests
   reproduce exactly;
4. final session-treatment selections and payload digests match all 1,742
   evidence-blind Preflight allocation traces;
5. the 70,736-row mechanism trace matches the final selector's relevance,
   novelty, session and objective fields;
6. the treatment is active and binding on real traces, exact budgets hold, and
   PF4 branches remain reachable;
7. selection completes before evidence is imported or joined, mechanism source
   cannot read evidence/answer/rubric/key artifacts, and a planted violation
   proves the audit can fail;
8. cache misses and LLM/generative calls are zero; embedding calls are reported
   separately under the programme's model-free terminology;
9. frozen source hashes, one-thread environment and a passing full suite are
   recorded; and
10. two fresh worker processes reproduce ordered identities and payload digests
    exactly on a deterministic prefix.

Any failure stops as `INSTRUMENT_FAILURE`; treatment outcomes are not produced.

## 10. Registered run

After committed G0, generate all three arms for all 871 unique questions at both
budgets. The worker must first serialize and freeze arm selections without
loading treatment evidence, then a separate measurement phase joins frozen
evidence by stable identity. Question-level output is written before aggregate
comparisons.

Two fresh complete worker processes must produce identical ordered identities,
payloads, outcomes and file digests. Reject cache misses, budget overruns,
duplicate keys, unregistered arms/budgets, source drift, dirty launch state or
nondeterminism. Use explicit UTF-8, deterministic gzip headers, one thread and
no inference server.

The report states availability only, lists every works/signal/guardrail margin,
and preserves the selected contexts. It must not generate or score answers.

## 11. Surrogate audit and exclusions

Session count can rise while required evidence falls. Required-session touch
can rise while a necessary fact is absent. Evidence share can rise without
complete evidence, and complete evidence can still fail at the reader. A
protected route can relabel ownership without changing the selected set. All
are reported, none substitutes for the joint rule.

Conversely, the reader could use a partial or differently phrased context that
this exact-identity availability endpoint misses. TC-008 does not test that
possibility. It also does not optimize the 50/50 share, compare budgets outside
16k/32k, test chunking, or select an enterprise policy.

## 12. Execution and closeout order

1. Commit this registration alone and record its SHA-256.
2. Implement registered G0/run code and tests without changing carried routes.
3. Commit passing G0 before outcome generation.
4. Run and commit question-level artifacts before aggregate interpretation.
5. Report with registration commit and SHA-256 in the header.
6. Update README, AGENTS digest (at most 400 characters), roadmap, dependency
   log and memory; update ERRATA only if a published number changes.
7. Push and open the TC-008 PR stacked on TC-007. Do not start reader answers.

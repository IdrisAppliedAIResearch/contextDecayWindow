# TC-009 Pre-Registration — dynamic session exposure penalty

**Status:** `PRE-REGISTERED — OFFLINE AVAILABILITY STUDY`
**Date locked:** August 23, 2026
**Design and Preflight commit:** `09c7153e22cb22cb5f3a24d8eb2ae3241d8a547c`
**Preflight Part 1 SHA-256:** `c1e92a879152edfdef0ba870b78e43f03c87959d82bd8d8b181ba3c288634e08`
**Preflight PF4 SHA-256:** `844d67a1eacd63d7090169dcef56e1efc87408fd20b72c3518dbe4c994ef4b9a`
**Preflight allocation trace SHA-256:** `d30715b2e644f45c0b0efc0b268bf05fcefaccdf56bb4fc729245216c71d5651`
**Preflight admitted-step trace SHA-256:** `148481de267e28bbec667558763266614b8de643f495b302e5cd5ddf38fb9848`
**Preflight full-order trace SHA-256:** `de56dc5ef827edc8c4919f5a15bde62fc5c2c618e84430c17aadcaffa1f68347`

This file is the authoritative parameter source and is immutable after this
commit. Any genuine correction requires a standalone amendment. No treatment
outcome may change an arm, penalty, population, endpoint, band, alpha,
guardrail, tie-break or disposition below.

## 1. Question and claim boundary

Holding LoCoMo candidates, embeddings, dense ranking, exact budgets, TC-007's
50/50 allocator, renderer, admission-resolved deduplication and slack return
fixed, does a cumulative session exposure penalty improve distributed breadth
evidence while allowing semantically strong sessions to win repeatedly and
without a demonstrated loss of dense retrieval?

This is offline evidence availability. It does not generate answers, establish
reader accuracy, choose an enterprise budget or optimal penalty, authorize
adoption, or claim transfer beyond the frozen LoCoMo development set.

## 2. Frozen inputs and population

- Corpus SHA-256:
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- Conversations: `conv-41`, `conv-42`, `conv-47`, `conv-48`.
- Candidates: the same 1,365 adjacent-turn pairs used by TC-001 through TC-008,
  with unchanged content identities, text and vectors.
- Questions: 871 unique; 868 eligible; 3 ineligible.
- Targeted: 704 eligible questions whose required evidence lies in one pair in
  one session.
- Breadth: 44 eligible questions whose required evidence spans at least three
  sessions. Other eligible: 120.
- Selection uses TC-008's committed label-blind question key. Measurement uses
  content SHA-256 plus frozen duplicate ordinal. Candidate comparison uses
  content identity. Paths, timestamps and generated ids are forbidden keys.

## 3. Frozen common route and allocator

`DENSE` ranks the complete store by descending normalized float32
query/candidate matrix product with `(session_order, pair_order)` ties. There is
no threshold or top-k cut.

For total `B in {16_000, 32_000}` exact serialized characters:

1. Dense and spread each receive initial solo allowance `B/2`.
2. Dense admits fitting candidates in dense order.
3. Spread admits fitting distinct candidates in its order, skipping identities
   actually admitted by dense. A dense proposal that did not fit remains
   available to spread.
4. Initial admissions merge in phase order and serialize once.
5. Dense resumes its unchanged order and consumes every fitting candidate from
   actual remaining capacity. Wrapper savings and unused spread allowance
   return to dense.
6. Candidates are skipped on overflow, never truncated; payload length may not
   exceed `B`.

## 4. Dynamic session mechanism and arms

For candidate `i`, raw dense cosine `s_i`, source session `g_i`, and selected
set `S`, the binding spread order greedily maximizes:

`score(i | S) = s_i - 0.03 * count(j in S where g_j = g_i)`

Every session competes through its highest-cosine remaining candidate. After a
pick, only that session's count increments, then every nonempty session competes
again. The same session may win consecutive slots. Ties use frozen
`(session_order, pair_order, candidate_identity)` order. The selector must emit
a complete permutation.

`0.03` is fixed from the author-approved architecture before Preflight. It is
not selected from a sweep. `lambda=0` must reduce exactly to dense order, but is
a G0 control, not an arm.

| Arm | Frozen behavior | Role |
|---|---|---|
| `A_DENSE_FULL` | Dense receives complete budget | binding control |
| `A_SPLIT_DYNAMIC` | 50/50 dense plus cumulative session penalty | treatment |
| `A_SPLIT_SESSION` | TC-008 one-time source-session novelty | descriptive reference |
| `A_SPLIT_A3` | TC-007 embedding-cluster A3 | descriptive reference |

The reference arms add no multiplicity cells and cannot select an architecture.
No adaptive share, floor, quota, round robin, query classifier, reader,
chunking, summary, BM25, RRF, adjacency or new embedding is included.

## 5. Frozen endpoints

Treatment is compared pairwise with `A_DENSE_FULL` at each budget.

### Primary breadth endpoint

For each of 44 breadth questions, compute:

`delivered required candidate identities / all required candidate identities`

A question favours treatment when its delivered required-identity count is
larger, favours dense when smaller, and ties otherwise. Report both directional
exact one-sided sign-test tails, question gains/losses/net, and summed required-
identity gains/losses/net.

### Joint guardrails

- `breadth_complete`: all required identities delivered on the 44 breadth
  questions; practical noninferiority only.
- `combined_complete`: complete delivery on all 868 eligible questions.
- `targeted_complete`: complete delivery on the 704 targeted questions.

Any-evidence, represented sessions, concentration, session touch, selected
count, character spend and admission owner are descriptive only.

## 6. Bands, multiplicity and budget decisions

There are six directional inferential cells: breadth share, combined complete
and targeted complete at two budgets. Each reports both directional tails.

- Works alpha: `0.01 / 6 = 0.0016666666666666668`.
- Signal alpha: `0.10 / 6 = 0.016666666666666666`.
- A direction clears only when net is strictly greater than its practical band
  and its one-sided sign-test p-value is at or below alpha.

Hash-verified dense-only one-percent shams freeze:

| Budget | Breadth questions | Breadth identity net | Breadth complete | Combined complete | Targeted complete |
|---:|---:|---:|---:|---:|---:|
| 16,000 | 0 | 0 | 0 | 2 | 2 |
| 32,000 | 0 | 0 | 0 | 1 | 0 |

At one budget, `DYNAMIC_BREADTH_WORKS` requires all of:

1. dynamic clears the breadth-question works bar;
2. breadth identity net is strictly greater than its band;
3. breadth-complete net is at least the negative breadth-complete band;
4. dense does not clear combined complete at works alpha; and
5. dense does not clear targeted complete at works alpha.

`DYNAMIC_BREADTH_SIGNAL` substitutes signal alpha in item 1 and retains items
2-5. `DENSE_GUARDRAIL_FIRE` means dense clears either complete guardrail at
works alpha. `DENSE_BREADTH_WORKS` is the directional mirror of items 1-3.

PF4 shows ten all-favourable breadth discordances clear works and six clear
signal. Every benefit, harm, guardrail, noninferiority and neutral branch is
reachable.

## 7. Study disposition

Apply in order:

1. `DYNAMIC_SPREAD_WORKS`: `DYNAMIC_BREADTH_WORKS` passes at both budgets.
2. `DENSE_WORKS`: dynamic does not work, and either `DENSE_BREADTH_WORKS`
   passes at both budgets or `DENSE_GUARDRAIL_FIRE` occurs at both budgets.
3. `DYNAMIC_SPREAD_CARRIES_SIGNAL`: neither works branch fired; dynamic breadth
   signal passes at least one budget; at the other budget breadth question net,
   breadth identity net and breadth-complete net are nonnegative; and no dense
   guardrail fires at either budget.
4. `DENSE_CARRIES_SIGNAL`: the exact breadth-signal mirror of item 3, or one
   dense guardrail fires without an opposite dynamic-works cell.
5. `MIXED_OR_NO_DIFFERENCE`: every remaining pattern.

Only `DYNAMIC_SPREAD_WORKS` freezes dynamic contexts as the preferred reader
input. A signal result cannot select an architecture. No disposition changes
deployed code.

## 8. Diagnostics and predecessor attribution

Preserve complete orders and digests, every dynamic count/penalty/score state,
initial allowances, actual admissions, duplicate skips, slack return, owners,
serialized costs, selected/dropped identities, payload digest, represented
sessions, concentration, and dense ranks of additions/displacements.

After formal outcomes are committed, report:

- breadth gains/losses by category and required source session;
- evidence identities added and displaced;
- whether each disagreement is unique to dynamic exposure, shared with TC-008
  session novelty, shared with A3, or common to fixed 50/50 protection;
- targeted losses and their dense ranks; and
- disagreements between identity share and complete evidence.

These diagnostics explain but cannot override the registered result.

## 9. G0 — binding before outcomes

G0 must be committed before treatment outcomes and pass:

1. this file is committed and byte-identical to its recorded SHA-256;
2. all five Preflight artifacts match this header;
3. all 5,226 TC-008 dense/A3/session selections and payload digests reproduce;
4. final dynamic payloads match all 1,742 evidence-blind allocation traces;
5. all 296,166 full-order and 69,961 admitted-step state fields match the final
   selector;
6. `lambda=0` reduces to dense on all 871 questions, repeat wins occur before
   full session coverage on all real traces, feedback terminates, both halves
   bind and exact budgets hold;
7. selection completes before evidence import/join, the committed blind
   manifest contains no answer/evidence keys, mechanism source cannot read
   measurement artifacts, and a planted violation fails;
8. cache misses and LLM/generative calls are zero; embedding calls are reported
   separately under programme model-free terminology;
9. frozen source hashes, one-thread settings and a passing full suite are
   recorded; and
10. two fresh worker processes reproduce a deterministic prefix exactly.

Any failure stops as `INSTRUMENT_FAILURE`; outcomes are not produced.

## 10. Registered run

After committed G0, generate all four arms for all 871 unique questions at both
budgets. Freeze label-blind selections to bytes before importing or joining
evidence. Then measure by stable identity. Commit question-level artifacts
before opening aggregate results.

Two fresh complete workers must produce identical ordered identities, payloads,
outcomes and file digests. Reject cache misses, budget overruns, duplicate keys,
unregistered arms/budgets, dirty launch state, source drift or nondeterminism.
Use explicit UTF-8, deterministic gzip, one thread and no inference server.

The report states availability only and does not generate or score answers.

## 11. Surrogate audit and exclusions

Lower concentration, more sessions, repeated-session wins and spread ownership
can all increase while required evidence falls. Evidence share can improve
without completeness, and complete evidence can fail at the reader. None
substitutes for the joint rule.

Conversely, a reader may use partial evidence this identity endpoint misses.
TC-009 does not test that possibility, tune lambda, optimize the 50/50 share,
test other budgets, or select enterprise policy.

## 12. Execution and closeout

1. Commit this registration alone and record its SHA-256.
2. Implement G0/run code and tests without changing carried routes.
3. Commit passing G0 before outcomes.
4. Commit question-level artifacts before aggregate interpretation.
5. Report with registration and artifact anchors.
6. Update README, AGENTS digest, roadmap, dependency log and memory; ERRATA only
   if a prior published number changes.
7. Push and open TC-009 stacked on TC-008. Do not start reader answers.

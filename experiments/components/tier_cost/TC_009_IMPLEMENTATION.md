# TC-009 Implementation Document — dynamic session exposure penalty

**Document type:** Prospective implementation design
**Status:** `PREFLIGHT PASS — PRE-REGISTRATION NEXT — NO RUN AUTHORIZED`
**Date:** August 23, 2026
**Arc:** Tier-cost successor to TC-008
**Predecessors:** TC-005, TC-007, TC-008

## 0. Decision in plain language

Keep TC-008's dual-route architecture. Dense semantic retrieval receives the
same protected half, the spread route receives the other half, duplicates merge
once, and unused spread capacity returns to dense. Replace only the spread
ranking rule.

Every source session competes through its strongest remaining candidate. After
a candidate is selected, every remaining candidate from that session receives
one additional `0.03` penalty. The session can still win the next slot when its
next candidate remains strongest after the penalty. Penalties accumulate rather
than firing only once.

This is not a floor, quota, round robin, or one-time novelty reward.

## 1. Single new component

For candidate `i`, raw dense cosine `s_i`, source session `g_i`, and already
selected set `S`, freeze:

`score(i | S) = s_i - 0.03 * count(j in S where g_j = g_i)`

At each step, select the remaining candidate with the highest adjusted score.
Ties use frozen source `(session_order, pair_order, candidate_identity)` order.
Then increment only the selected candidate's session count and recompute.

Because every remaining member of a session has the same exposure penalty, the
highest-cosine remaining candidate is that session's representative in each
global contest. A session can win consecutive slots. With `lambda=0`, the full
order must reduce byte-for-byte to dense cosine order. With only one session,
all remaining candidates receive the same accumulated penalty and the order
also stays dense.

The registered candidate lambda is `0.03`, taken from the architecture agreed
with the author before Preflight. Preflight may characterize it but may not tune
or replace it.

## 2. Frozen common architecture and arms

- `A_DENSE_FULL`: full-budget dense control.
- `A_SPLIT_DYNAMIC`: TC-007's exact 50/50 allocator with the dynamic penalty
  order; binding treatment.
- `A_SPLIT_SESSION`: TC-008's one-time source-session bonus; descriptive
  predecessor reference.
- `A_SPLIT_A3`: TC-007's embedding-cluster A3; descriptive reference.

Total budgets remain 16,000 and 32,000 exact serialized characters. Initial
allowances remain 8,000 and 16,000. Dense ranking, candidates, embeddings,
renderer, skip-on-overflow packer, admission-resolved deduplication, ownership,
slack return, evidence labels and LoCoMo population remain unchanged.

No adaptive budget, reader, query classifier, chunker, session summary, BM25,
RRF, adjacency, new embedding or penalty sweep is in scope.

## 3. Proposed measurement

Carry TC-008's primary paired breadth endpoint:

`delivered required candidate identities / required candidate identities`

It may pass only jointly with breadth-complete noninferiority and combined plus
targeted complete-evidence guardrails. Dense-only one-percent budget shams size
practical bands before treatment outcomes. Required-session touch, represented
sessions, concentration and selected count are diagnostics only.

The binding contrast is dynamic penalty versus full-budget dense. TC-008
session novelty and TC-007 A3 are descriptive attribution references and do not
add multiplicity cells.

No answer generation is authorized. TC-009 reports availability before the
programme returns to reader results.

## 4. Preflight Part 1

Run all 871 unique questions at both budgets without joining dynamic-treatment
evidence outcomes. Record:

1. exact reproduction of all 5,226 TC-008 dense/A3/session question-budget
   selections and payload digests;
2. every dynamic selection step's raw cosine, session count before selection,
   accumulated penalty, adjusted score and source session;
3. represented-session and per-session admission-count distributions;
4. dense ranks of dynamic-only admissions and dense-only displacements;
5. consecutive same-session wins, returns to a previously selected session,
   maximum accumulated penalties and whether any session monopolizes a trace;
6. allowance binding, duplicate skips, slack return, exact payload cost and
   budget compliance;
7. `lambda=0` exact dense-order identity on every real question and exact dense
   behavior for a one-session constructed trace;
8. positive controls where a penalized session still wins again and where a
   competing session overtakes after enough accumulated exposure;
9. dense-only sham bands and PF4 reachability for every proposed branch; and
10. evidence-blind source audit plus a planted violation.

Stop before registration if the treatment is inert on all real traces, violates
the exact budget, fails the zero-lambda identity, or is behaviorally a hard
one-per-session floor.

## 5. Preflight checklist

- **PF1 Inputs:** hash and count corpus, cache, TC-008 run artifacts, allocator
  source and dynamic-selector source.
- **PF2 Identity:** prove that each pick adds exactly one `0.03` penalty to its
  session and that every session continues competing afterward.
- **PF3 Ordering:** final G0 and selection freezing must execute before evidence
  import or treatment measurement.
- **PF4 Reachability:** demonstrate benefit, harm, signal, guardrail,
  noninferiority and neutral branches on the measured populations.
- **PF5 Keys:** content identities plus frozen duplicate ordinal; no generated
  ids, timestamps or paths.
- **PF6 Anchor:** reproduce all 5,226 TC-008 dense/A3/session payloads by ordered
  identity and byte digest.
- **PF7 Feedback:** the selector has within-query feedback. Replay every real
  trace, record the count state after every step, and prove finite termination
  at a complete permutation.
- **PF8 Length:** the full 871-question replay can detect availability changes,
  not reader use, enterprise transfer or optimal lambda.
- **PF9 Surrogates:** lower session concentration or more represented sessions
  can pass while required evidence falls. Only the registered evidence endpoint
  and guardrails decide.
- **PF10 Live requirement:** availability cannot authorize adoption. Reader
  validation remains separately registered work.

## 6. Execution order

1. Commit this design before mechanism code.
2. Implement and commit Preflight Part 1 plus PF4 artifacts.
3. Commit the standalone pre-registration alone.
4. Implement registered G0/run code and tests.
5. Commit passing G0 before outcomes.
6. Commit question-level outputs before aggregate interpretation.
7. Report, update README/AGENTS/roadmap/dependency log/memory, push, and open a
   TC-009 PR stacked on TC-008.

Reader answers are not started by this document.

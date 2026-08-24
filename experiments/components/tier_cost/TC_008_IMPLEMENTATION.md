# TC-008 Implementation Document — relevance-gated session spread

**Document type:** Prospective implementation design  
**Status:** `PREFLIGHT PASS — PRE-REGISTRATION NEXT — NO RUN AUTHORIZED`
**Date:** August 23, 2026  
**Arc:** Tier-cost successor to TC-007  
**Predecessors:** TC-003, TC-005, TC-007, NF-003/004/007, TA-001

## 0. Decision in plain language

Keep dense semantic retrieval and TC-007's exact 50/50 allocator. Replace only
the spread grouping dimension.

TC-007's A3 route grants a `0.1` novelty bonus to the first candidate from each
of 16 embedding clusters. TC-008 grants the same bonus to the first candidate
from each real conversation session. Candidate relevance, cost exponent,
greedy selector, renderer, deduplication, ownership, slack return, total
budgets, relevance route and packer remain unchanged.

The hypothesis is not that more represented sessions are automatically useful.
It is that query-relevant session novelty aligns better with LoCoMo's distributed
evidence than embedding-cluster novelty, without sacrificing the dense route's
direct-question behavior.

## 1. Single new component

For candidates `i` with dense cosine `s_i` and session assignment `g_i`, the
spread selector uses the carried A3 marginal objective:

`gain(i | S) = max(s_i, 0) + 0.1 * 1[g_i not represented in S]`

The only changed input is `g_i`: content-derived embedding-cluster ids become
frozen corpus session ids. Stable integer assignments follow source session
order. The selector emits a complete deterministic permutation; TC-007's
allocator consumes it unmodified.

No adaptive budget, query classifier, answer reader, chunker, session summary,
BM25 fusion, temporal adjacency, or new embedding is in scope.

## 2. Frozen arms

- `A_DENSE_FULL`: TC-007 full-budget dense control.
- `A_SPLIT_A3`: TC-007 50/50 dense plus embedding-cluster A3 reference.
- `A_SPLIT_SESSION`: identical allocator with session assignments substituted
  into the carried A3 objective.

Total budgets remain 16,000 and 32,000 exact serialized characters. Initial
allowances remain 8,000 and 16,000. Unused spread allowance and wrapper savings
return to dense. Candidate identities, text, vectors and evidence labels remain
the frozen four-conversation LoCoMo development set.

## 3. Measurement selected after Preflight

TC-007's all-or-nothing complete-evidence endpoint remains for continuity, but
it cannot be the only breadth read: two TC-007 breadth misses gained a required
evidence pair without becoming complete.

The primary paired breadth endpoint is computed after selection:

`delivered required candidate identities / required candidate identities`

It may pass only jointly with combined and targeted complete-evidence
guardrails and breadth-complete noninferiority. The 1% dense-budget shams fix
the practical bands. There are six directional inferential cells: breadth
share, combined complete and targeted complete at each budget. Works alpha is
`0.01/6`; signal alpha is `0.10/6`. Required-session touch and total selected
session count remain diagnostics; neither can certify useful spread because
TC-007 facility location increased global session coverage while losing answer
evidence.

No answer generation is authorized. TC-008 freezes an availability contrast so
the programme can return to reader answers later.

## 4. Preflight Part 1 — exploration before lock

Preflight must run the mechanism on all 871 unique questions at both budgets
without opening treatment evidence outcomes. It records:

1. exact reproduction of TC-007 dense and A3 payload identities/digests;
2. stable session assignment identity and session-count distributions;
3. full name-to-behavior traces showing relevance, novelty bonus, objective
   gain, selected session and whether it was newly covered;
4. selected distinct-session distributions for dense, A3 and session spread;
5. dense-rank distributions of session-spread admissions and displacements;
6. allowance binding, duplicate skips, slack return, payload cost and budget
   compliance;
7. real-trace degeneracies: one-session data reduces session novelty to one
   bonus, and `lambda=0` reduces the order to nonnegative dense relevance with
   stable ties;
8. positive controls where session assignments alter selection and a negative
   control where all candidates share one session;
9. sham-derived practical bands and PF4 reachability for every proposed bar;
10. the evidence-blind import boundary and a planted violation.

If the session treatment is inert on all real traces, violates the budget, or
cannot be separated behaviorally from embedding clusters, TC-008 stops before
pre-registration.

## 5. Preflight checklist

- **PF1 Inputs:** hash and count corpus, vector cache, TC-007 run artifacts,
  allocator source and selector source.
- **PF2 Identity:** prove that `session` means source session id and that the
  novelty bonus fires once per represented session.
- **PF3 Ordering:** run G0 and source-hash checks before any evidence join.
- **PF4 Reachability:** demonstrate every works, signal, guardrail and stop
  branch against measured populations and positive controls.
- **PF5 Keys:** content hashes plus duplicate ordinal; no generated ids or paths.
- **PF6 Anchor:** reproduce all 3,484 TC-007 control/A3 question-budget payloads
  by identity and digest.
- **PF7 Absorbing state:** no feedback; prove pure replay on all 1,742 treatment
  budget traces.
- **PF8 Length:** the full 871-question offline replay is the ablation; it can
  detect availability changes, not reader use or enterprise transfer.
- **PF9 Surrogates:** represented sessions, session-touch, spread spend and
  evidence share can all rise without a correct answer. Complete and targeted
  guardrails remain joint requirements; reader value remains untested.
- **PF10 Live requirement:** availability cannot authorize adoption. Reader
  validation remains separately registered work.

## 6. Execution order

1. Commit this design before mechanism code.
2. Implement and commit Preflight Part 1 plus PF4 artifacts.
3. Write and commit the standalone pre-registration alone.
4. Implement registered G0/run code and tests.
5. Commit passing G0 before outcomes.
6. Run and commit question-level outputs before aggregate interpretation.
7. Report, update README/AGENTS/roadmap/dependency log/memory, and open the
   TC-008 PR stacked on TC-007.

TC-006 and reader answers are not started by this document.

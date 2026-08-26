# TC-013 — CC80-parent ASPECT fan-out probe

**Type:** registered lightweight offline evidence-availability probe  
**Status:** pre-registration; not yet runnable  
**Date:** 2026-08-25  
**Authorization:** user requested frozen-corpus CC80 retrieval followed by one
ASPECT attempt from every admitted CC80 result

## 1. Question and boundary

Does replacing TC-011's single global ASPECT walk with independent one-child
ASPECT fan-out from every protected-half CC80 admission preserve semantic
retrieval while improving spread evidence?

This is a label-blind selection and offline LoCoMo development availability
probe. It makes no embedding or answer-model calls and cannot establish reader
accuracy, transfer, production adoption, or an optimal budget share.

## 2. Frozen inputs and controls

Use TC-011's frozen corpus, 1,365 candidates, carried vectors, CC80 orders and
scores, deterministic facets, exact renderer, containment deduplication,
skip-on-overflow packer, eligible population, and 16,000/32,000-character
budgets without change. The binding baseline is full-budget CC80. Frozen
TC-011 global static ASPECT is a descriptive control.

## 3. Treatment

For total budget `B`, pack unchanged CC80 under solo allowance `H=B/2`. Every
admitted CC80 identity becomes one parent, in CC80 admission order. For each
parent exactly once:

1. Seed the frozen TC-011 ASPECT coverage state from that parent alone.
2. Consider every candidate except all CC80 parents and children already
   proposed by earlier parents.
3. Apply TC-011's unchanged candidate relevance, IDF facet marginal, exact
   additive-cost normalization and deterministic CC80-rank tie-break.
4. Propose the greatest positive-marginal candidate, or no child if none has a
   positive marginal.

Thus each parent gets one attempt and at most one unique proposed child. A
proposal is not guaranteed admission: the unchanged protected allocator packs
the proposed-child order under solo `H`, merges CC80 then admitted children,
and returns unused space and wrapper savings only to unchanged CC80 order. No
identity serializes twice and total serialized length cannot exceed `B`.

There is no parent-count cap, beam, retry after capacity rejection, coefficient
sweep, new parser, new embedder, query expansion, reranker, or recursive child.

## 4. Endpoints and interpretation

Against full CC80, report complete-evidence totals and paired gains/losses for
combined, targeted, breadth and other populations at both budgets. Also report
breadth required-identity gains/losses, conversation nets, zero/partial/
complete states, parent/proposed/admitted/returned counts, no-child attempts,
duplicate prevention, exact characters and payload digests. Report the same
complete-evidence totals for frozen global static ASPECT.

This diagnostic has no adoption bar or frozen disposition. Any observed gain
is a within-development availability signal only; full CC80 remains fallback.

## 5. Preflight — binding before labels open

- **PF1:** hash and count the registration, corpus, blind manifest, vector
  cache, CC80 source, TC-011 control selections and labels; reject missing or
  empty inputs.
- **PF2:** reproduce all frozen full CC80 and global static-ASPECT selected
  identities and payload digests at both budgets before treatment inference.
- **PF3:** write and hash treatment selections before opening label-bearing
  evidence; a planted early-label argument must fail.
- **PF4:** there is no decision threshold. Synthetic candidates must reach a
  child, no-positive-child, duplicate-exclusion and capacity-rejection state.
- **PF5:** use content identities only and reject missing or duplicate joins.
- **PF6:** control reproduction is by exact identity sequence and payload
  digest, not count.
- **PF7:** on every real question-budget trace prove each parent is attempted
  once, proposed children are unique, excluded identities never re-enter, and
  capacity cannot reopen after allocation.
- **PF8:** four development conversations can detect within-corpus availability
  changes but not transfer or reader effects.
- **PF9:** one proposed child per semantic parent can pass while evidence
  breadth is false; proposal count, facet marginal and identity diversity are
  not endpoints.
- **PF10:** availability only; no answer or reader run is authorized.

Preflight and the outcome must use the existing cache read-only with zero cache
misses, embedding calls and LLM/generative calls.


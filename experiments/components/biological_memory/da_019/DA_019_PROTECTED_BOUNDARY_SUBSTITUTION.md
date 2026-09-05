# DA-019 Protected Boundary Substitution

**Status:** `POST-OUTCOME CROSS-CORPUS EXPLORATION PROTOCOL`
**Date:** August 30, 2026
**Parent:** DA-018 result commit `2965b78b`
**Standing:** evidence-blind suffix-substitution study on spent NF-004 and LongMemEval
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can a single structurally protected substitution at the linked-capacity boundary
improve either strongest corpus-specific pack without globally replacing its
useful carrier order?

DA-018 showed that local frozen-query utility cannot safely reorder the whole
linked suffix. DA-019 preserves the parent order and allocation exactly, then
permits at most one post-pack exchange.

## 2. Locked Controls

- **NF-004:** exact DA-010 benefit order, role-pattern direct rendering and
  pair-then-turn payload, 970 complete; direct 935; one-hop ceiling 986.
- **LongMemEval:** exact DA-016 phrase-coded temporal order and pair-then-turn
  payload, 188 complete; direct 164; one-hop ceiling 250.

All direct identities, codecs, dictionaries, member choices, edge orders,
budgets and baseline actions remain fixed. DA-017 is excluded because its
phrase-link NF transfer missed its registered bar.

## 3. Fixed Boundary Rule

After the complete baseline allocation:

1. Let the incumbent be the **last admitted linked action** (`PAIR` or `TURN`).
   If none exists, retain control.
2. Remove only that action in a shadow replay. Preserve every direct payload
   and every earlier linked action in its original order and materialization.
3. Traverse baseline `SKIP` actions in their original order. Duplicate neighbor
   identities and the incumbent identity are ineligible.
4. Materialize each candidate under the parent's unchanged rule: complete pair
   if it fits after removal, otherwise the parent's fixed singleton member.
5. Admit the first candidate satisfying all three guards:
   - **exact fit:** rebuilt total is at most 16,000 characters;
   - **lexical preservation:** every original-question token uniquely supplied
     by the incumbent relative to direct plus earlier linked payloads is also
     present in the candidate payload;
   - **semantic dominance:** candidate cosine to the original question is at
     least the incumbent payload's cosine to the original question.
6. If none qualifies, return the byte-identical baseline. At most one exchange
   is allowed; no later repacking, refill or second swap occurs.

Cosines are the exact frozen DA-003 values on NF-004 and sealed-cache values on
LongMemEval. Tokenization and IDF are inherited, although the guard is set
containment and does not use an IDF coefficient. Phrase dictionaries remain
direct-derived and immutable.

The rule uses no answer, evidence identity, outcome, category, conversation
identity, fitted label, threshold, blend, model, new embedding or tuning.

## 4. Endpoint and Decision

Primary endpoint is exact complete evidence delivery. Report per corpus:
complete items, gains/losses against control and direct, exact paired test,
group cells, eligible and executed substitutions, rejection reasons, incumbent
and candidate action/cost/rank distributions, changed dialogue identities and
exact causal accounting.

Report `PROTECTED_BOUNDARY_SUBSTITUTION_SIGNAL` only if treatment has at least
one gain, zero losses, and no negative conversation/question-type cell on both
corpora. If the blind rule executes zero substitutions on either corpus, stop
before evidence access as `BOUNDARY_GUARD_INERT`. Otherwise a one-corpus gain is
descriptive only and the cross-corpus status is
`NO_PROTECTED_BOUNDARY_SUBSTITUTION_SIGNAL`.

## 5. Preflight

- **PF1 Inputs:** seal and reproduce DA-010 and DA-016 blind/control artifacts,
  populations, edges, codecs and exact baseline actions.
- **PF2 Identity:** test last-admission selection, shadow removal, candidate
  order, pair fallback, unique-token preservation, cosine tie, exact rebuild,
  duplicate rejection and one-swap cap.
- **PF3 Ordering:** commit protocol, then blind substitutions before evidence.
- **PF4 Reachability:** require executed swaps on both corpora plus observed
  fit, lexical, semantic and duplicate rejections. Otherwise stop unopened.
- **PF5 Keys:** preserve corpus, question, edge, seed, neighbor, member, action,
  token, cosine, cost and rejection keys.
- **PF6 Reproduction:** require exact baseline action bytes and 16k charging;
  direct identities may never differ.
- **PF7 Determinism:** require byte-identical blind and opened replay.
- **PF8 Length:** process all 1,098 and 465 questions and all baseline skips.
- **PF9 Surrogate audit:** lexical/semantic dominance does not prove evidence
  preservation; spent-corpus availability is not reader value.
- **PF10 Live boundary:** no reader, latency, deployment or adoption claim.

Stop on hash/cache miss, fresh model/embedding call, control drift, direct or
earlier-link mutation, undercharge, more than one swap, nondeterminism,
incomplete population or unexplained outcome. No post-result guard relaxation.


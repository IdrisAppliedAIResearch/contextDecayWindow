# DA-025 LongMem Atomic Backreference Additions

**Status:** `COMPLETE; NO_LONGMEM_ATOMIC_ADDITION_SIGNAL`
**Date:** August 30, 2026
**Parent:** DA-024 result commit `63d4c2dd`
**Standing:** evidence-blind additive-member study on spent LongMemEval
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can deterministic atomic member attempts recover DA-024's wrong-frozen-member
residuals without risking the strongest immutable baseline?

DA-024 finds 20/48 LongMem residual misses in the other member of an exposed
pair, versus 17 prior-consumption, 6 initial-size and 5 conjunction cases.

## 2. Locked Population and Control

Use all 465 DA-023 LongMem questions. Reproduce direct 164, DA-016 immutable
baseline 188, DA-023 backreference treatment 202 and one-hop ceiling 250.
DA-023's prefix, baseline backreference renderer, baseline identities/order and
16k budget remain fixed.

## 3. Fixed Treatment

Replay DA-023 additive traversal in the exact temporal edge order. For each
baseline-skipped neighbor:

1. Attempt the complete pair exactly as DA-023.
2. On pair overflow, attempt both members independently in DA-013's frozen
   lexical member order: the existing fallback member first, then the other.
3. Charge each member against the current exact backreference history and role
   state. An admitted first member enters history before the second is encoded.
4. Continue after every overflow. Never retry a dialogue identity already in
   the immutable baseline or admitted additions.

No answer, evidence, outcome, question type, fitted label, threshold or sweep
enters member order or admission. The treatment may alter DA-023 additions but
cannot remove any DA-016 immutable baseline payload.

## 4. Gates and Decision

Before evidence access commit all actions, both member costs, history updates
and final charges. Require positive second-member attempts and admissions,
pair/member/skip actions, allocation differences from DA-023, exact baseline
decode, <=16k cost and byte-identical replay. Otherwise stop unopened.

After a pass, report exact delivery, gains/losses against DA-023 and DA-016,
question-type cells, wrong-member rescues, trades, costs/ranks and causal
accounting. Report `LONGMEM_ATOMIC_ADDITION_SIGNAL` only if treatment gains at
least five over DA-023, loses zero to DA-023 and every type is nonnegative.
Otherwise report `NO_LONGMEM_ATOMIC_ADDITION_SIGNAL`. Any DA-016 baseline loss
is a causal stop.

## 5. Preflight

- Verify DA-023/024 and DA-013 member-order/source hashes.
- Test pair-first behavior, two-member order, dynamic second-member encoding,
  dialogue deduplication, overflow continuation and rejected-history exclusion.
- Commit protocol, then blind actions before evidence.
- Process all 465 questions and every DA-023 additive opportunity.
- Require byte-identical blind/open replay and exact 164/188/202/250 anchors.
- Availability is not reader use; no live/adoption claim.

Stop on hash/control/decode drift, baseline mutation, undercharge,
nondeterminism, incomplete population or unexplained outcome. Do not tune order,
reserve capacity, skip the first member, alter the codec or add a third pass.

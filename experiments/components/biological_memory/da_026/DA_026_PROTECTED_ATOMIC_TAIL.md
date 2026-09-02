# DA-026 Protected Atomic Tail

**Status:** `COMPLETE; PROTECTED_ATOMIC_TAIL_SIGNAL`
**Date:** August 30, 2026
**Parent:** DA-025 result commit `bf3e181f`
**Standing:** evidence-blind additive study on spent LongMemEval
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can DA-025's useful alternate-member operation recover evidence when every
DA-023 strongest-order admission is immutable and atomic members may consume
only the residual tail?

DA-025 reaches 211 but trades 17 gains for 8 losses. Fifteen of 20 audited
wrong-member residuals are rescued. This study tests the operation without the
unsafe pair-first substitution policy.

## 2. Locked Population and Control

Use all 465 DA-023 LongMem questions at 16,000 characters. Reproduce direct
164, DA-016 188, DA-023 202 and one-hop ceiling 250. Freeze DA-023's prefix,
renderer, direct payloads, additive actions, identities, order, exact charges,
role state and backreference history.

## 3. Fixed Treatment

1. Replay every admitted DA-023 pair or singleton in its original order.
2. Mark both members of an admitted pair and the selected member of an admitted
   singleton as present. A skipped neighbor contributes no present member.
3. After the complete replay, traverse DA-023's original edge list once in its
   original order. For each neighbor, attempt each missing member in frozen
   lexical member order.
4. Encode each attempted member against the current treatment history and role
   state. Admit it only if its exact incremental charge fits the remaining
   16,000-character budget. Continue after overflow.
5. Never remove, replace, reorder, re-encode or recharge a DA-023 payload.

Question text may enter only through the already frozen DA-023 edge order. No
answer, evidence identity, outcome, question type, fitted feature, threshold,
model, embedding or sweep enters admission.

## 4. Gates

Before evidence access, commit every DA-023 replay identity and charge, every
atomic attempt/admission/overflow, final charge and decoded payload identity.
Require:

- 465 complete questions and exact control hashes;
- byte-identical DA-023 prefix and admitted payload sequence;
- treatment charge <=16,000 for every question;
- positive atomic attempts, admissions and overflows;
- exact decoding and byte-identical blind replay;
- zero model, embedding and cache calls.

Stop unopened on any immutable-prefix mutation, undercharge, duplicate identity,
hash drift, nondeterminism or incomplete population.

## 5. Outcomes and Disposition

After gate passage, measure exact complete evidence delivery and paired
gains/losses against DA-023 and DA-016. Report question-type cells, DA-024
wrong-member rescues, admitted-member costs, edge positions and residual slack.

Report `PROTECTED_ATOMIC_TAIL_SIGNAL` if treatment gains at least five over
DA-023, loses zero and every question type is nonnegative. Report
`WEAK_PROTECTED_ATOMIC_TAIL_SIGNAL` if it gains two to four, loses zero and
every type is nonnegative. Otherwise report `NO_PROTECTED_ATOMIC_TAIL_SIGNAL`.
Any DA-023 loss is a causal-accounting stop, not an outcome.

Availability is not reader use. LongMem is spent; no reader, fresh-transfer,
runtime or adoption claim follows. Do not alter traversal, reserve capacity,
codec, member order or budget after registration.

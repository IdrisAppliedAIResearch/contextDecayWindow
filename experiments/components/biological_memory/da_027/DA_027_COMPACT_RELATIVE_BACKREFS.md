# DA-027 Compact Relative Backreferences

**Status:** `STOPPED AT BLIND NO-EXPANSION GATE`
**Date:** August 30, 2026
**Parents:** DA-023 result `f964b68d`; DA-026 result `adf81349`
**Standing:** evidence-blind structural-capacity study on spent NF-004 and LongMemEval
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can a denser exact pointer representation add usable capacity without changing
the strongest evidence identities or order?

DA-023 stores every copied span as decimal absolute coordinates:
`~r{member},{start},{length}~`. This pays repeated digits and punctuation for a
dependency that is naturally relative to the current history. DA-024 shows
that 7/10 NF residuals and 17/48 LongMem residuals are blocked by prior
additive consumption. DA-026 shows that strictly post-control additions can
gain without loss.

## 2. Locked Populations and Controls

Use all 1,098 NF-004 questions and all 465 LongMem questions at 16,000
characters. Reproduce DA-023 complete delivery 976 NF and 202 LongMem, direct
935/164, and one-hop ceilings 986/250.

Freeze every DA-023 decoded payload identity and payload order. Freeze its
direct candidates, baseline actions, additive traversal, temporal directions,
member fallback, role renderer, budget and all corpus joins.

## 3. Compact Relative Codec

For a reference emitted with `h` prior members and absolute source member `m`,
encode the positive backward distance `h-m`, source start and span length as
uppercase base-36 integers:

`{prefix}q{distance}.{start}.{length}{prefix}`

The collision-free prefix is chosen exactly as in DA-023, extended until both
`prefix+r` and `prefix+q` are absent from all candidate text. Integers have no
leading zero. Decoder recovery is `m = h-distance`; distance must be in
`[1,h]`, start nonnegative and length positive/in-bounds.

Greedy span choice remains longest match, then lowest absolute member/start.
A reference is emitted only when its compact textual code is shorter than its
literal span. No dictionary, learned code, evidence label or external store is
available to the decoder.

## 4. Immutable Allocation

1. Encode every DA-023 admitted payload in its exact existing identity/order
   with the compact codec. Decode and byte-compare every member.
2. The compact charge must not exceed DA-023's charge for any question.
3. Only after the full DA-023 sequence is encoded, traverse remaining DA-023
   skipped neighbors in the original order.
4. Attempt the frozen full pair, then its frozen member, exactly as DA-023.
   Admit only if the exact compact incremental charge fits. Continue on
   overflow. Never reconsider an identity already present.
5. Do not use DA-026 atomic alternates in the primary treatment; this isolates
   representation from member policy. A later composition requires a new lock.

Thus treatment may add payloads but cannot remove, replace or reorder any
strongest-control evidence.

## 5. Blind Gates

Before evidence access commit codec vectors, decoded payload hashes, compact
charges and all actions. Require:

- exhaustive boundary tests for base-36 and relative-index decoding;
- malformed, forward, zero-distance and out-of-bounds references rejected;
- exact decode on every immutable and added member;
- every DA-023 identity/order retained on all 1,563 questions;
- compact charge <= DA-023 charge question-wise and <=16,000 final;
- positive savings, pair admissions, member admissions and overflows in each
  corpus; median immutable savings >=64 characters in each corpus;
- byte-identical replay and zero model, embedding and cache calls.

Stop unopened on any identity/order mutation, expansion, undercharge, hash
drift, nondeterminism or incomplete population.

## 6. Outcomes and Disposition

After gate passage report exact complete delivery, gains/losses against DA-023,
conversation/type cells, residual-blocker rescues, decisive costs/positions,
savings and remaining ceiling gap.

Report `COMPACT_RELATIVE_DELIVERY_SIGNAL` if NF gains at least five and LongMem
gains at least five, both lose zero and every conversation/type is
nonnegative. Report `PARTIAL_COMPACT_RELATIVE_SIGNAL` if either corpus gains at
least two with zero losses and all of its groups nonnegative. Otherwise report
`NO_COMPACT_RELATIVE_DELIVERY_SIGNAL`. Any DA-023 loss is a causal stop.

These are spent exact-availability outcomes. The compact syntax has no reader,
latency, fresh-transfer or adoption claim. Do not tune radix, separators,
distance convention, traversal, member policy or budget after registration.

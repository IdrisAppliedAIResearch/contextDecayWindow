# DA-028 Shortest Exact Codec

**Status:** `COMPLETE; PARTIAL_SHORTEST_EXACT_CODEC_SIGNAL`
**Date:** August 30, 2026
**Parent:** DA-027 mechanical stop commit `dac6b47b`
**Standing:** evidence-blind structural-capacity study on spent NF-004 and LongMemEval
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can exact question-wise codec selection reclaim relative-pointer savings without
ever expanding or displacing the strongest DA-023 pack?

DA-027's compact relative codec passes its codec gates but fails when forced on
all rows. DA-023 itself already selects a renderer by exact charge and retains
the prior control on 16/465 LongMem rows. The architectural correction is to
treat reversible representations as alternatives, not a universal format.

## 2. Locked Inputs and Codecs

Use the same 1,098 NF-004 and 465 LongMem questions, 16,000-character budget,
DA-023 identity/order control, direct 935/164, DA-023 delivery 976/202 and
one-hop ceilings 986/250.

Codec A is the exact frozen DA-023 renderer and charge. Codec B is DA-027's
registered compact relative base-36 codec without modification. Both decode to
the identical ordered payload members.

## 3. Selection and Allocation

1. Compute both exact immutable charges without evidence.
2. Select compact only when its charge is strictly lower. On equality or
   expansion, retain DA-023 and its exact bytes/charge.
3. If DA-023 is retained, make no new admission. This isolates additions to
   capacity actually created by the compact codec.
4. If compact is selected, traverse only DA-023 remaining `SKIP` actions in
   their frozen order. Attempt full carrier then frozen member exactly as
   DA-023; continue after overflow.
5. Never remove, replace, reorder or change the member policy of a DA-023
   admission. DA-026 alternate-member completion is excluded from the primary
   arm and requires a later composition lock.

The selector sees only exact serialized lengths. It cannot see question text,
similarity, answer, evidence identity, outcome, type, conversation or fitted
features.

## 4. Blind Gates

Before outcomes, commit both charges, selected codec, immutable order hash,
all additions and final charge. Require:

- all DA-027 codec tests and corpus/hash joins pass;
- every DA-023 decoded identity/order retained on all 1,563 questions;
- selected immutable charge <= DA-023 question-wise, with ties retaining A;
- positive compact and retained-control rows in LongMem, and positive compact
  rows in NF;
- positive strict savings, pair admissions, member admissions and overflows in
  both corpora; median selected savings >=64 characters in both corpora;
- final charge <=16,000, byte-identical replay and zero calls.

Stop unopened on any expansion, mutation, undercharge, nondeterminism or
incomplete population.

## 5. Outcomes and Disposition

After a pass report exact complete delivery, gains/losses against DA-023,
conversation/type cells, codec cells, DA-024 blocker rescues, decisive costs,
positions, savings and remaining ceiling gap.

Report `SHORTEST_EXACT_CODEC_SIGNAL` if NF and LongMem each gain at least five,
lose zero and every group is nonnegative. Report
`PARTIAL_SHORTEST_EXACT_CODEC_SIGNAL` if either corpus gains at least two with
zero losses and all of its groups nonnegative. Otherwise report
`NO_SHORTEST_EXACT_CODEC_SIGNAL`. Any DA-023 loss is a causal stop.

Spent exact availability is not reader use. No latency, fresh-transfer or
adoption claim follows. Do not tune codecs, tie policy, traversal, fallback,
member policy or budget after registration.

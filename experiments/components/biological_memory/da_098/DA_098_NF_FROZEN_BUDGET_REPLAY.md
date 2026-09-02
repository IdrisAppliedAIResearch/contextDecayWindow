# DA-098 NF Frozen 16k/32k Budget Replay

**Status:** `COMPLETE; FROZEN_BUDGET_REPLAY_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-035 result and NF-004 secondary-budget control
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Does the strongest protected NF architecture retain an advantage over pair
ranking when the budget rises from 16,000 to 32,000 characters, and does it
close the observed 986-versus-1,024 gap without displacement?

## Population And Controls

Use all 1,098 primary NF-004 holdout questions and the sealed LoCoMo corpus,
vector cache, NF-004 outcomes and DA-035 blind allocation.

- `PAIR_16`: frozen NF-004 pair-rank pack; must reproduce 935.
- `PAIR_32`: frozen NF-004 pair-rank 32k pack; must reproduce 1,024.
- `ARCH_16`: frozen DA-035 protected sentinel+atomic allocation; must reproduce
  986 and its complete decoded identity/member order byte-for-byte.

No cache miss, new embedding, model call, score, rerank, threshold, sweep,
evidence marker or outcome may enter allocation.

## Nested 32k Architecture

Start `ARCH_32` with the complete decoded `ARCH_16` member sequence and order.
Reconstruct and verify its exact DA-035 sentinel charge. No existing member may
be removed, replaced, reordered or recharged under another codec.

Compute the unchanged NF-004 own-pair cosine order from the sealed cache. Visit
every candidate in that order. For each member absent from `ARCH_16`, attempt it
independently in source member order using DA-035's exact sentinel and role
cost. Admit on fit under 32,000 characters; on overflow skip and continue.
Never retry a member. Existing members are identity-deduplicated.

This is a nested budget replay: the verified 16k architecture is the immutable
prefix, and only the additional 16k capacity is opened. It is not a from-scratch
32k retuning or a claim that this prefix is globally optimal at 32k.

## Gates And Measures

Before outcomes require exact 1,098 joins, `PAIR_16/32` identity reproduction,
exact `ARCH_16` decode/order/charge, positive 32k admissions and overflows,
<=32,000 characters, no duplicates, byte-identical replay and zero calls.

After the blind artifact is committed, report complete evidence for all four
arms; paired gains/losses; conversation cells; overlap of the 38
`PAIR_32`-over-`ARCH_16` items; admitted member counts/cost/rank; final charge;
and remaining misses by addressability versus fit.

Report `FROZEN_BUDGET_REPLAY_SIGNAL` descriptively if `ARCH_32 >= PAIR_32`,
`ARCH_32` has zero losses versus `ARCH_16`, and every conversation is
nonnegative versus `PAIR_32`. Otherwise report `NO_FROZEN_BUDGET_REPLAY_SIGNAL`.

This is spent-corpus exact availability only. No reader, runtime, fresh
transfer, production or adoption claim.

## Result

The controls reproduce exactly: `PAIR_16=935`, `PAIR_32=1,024`, and
`ARCH_16=986`. The immutable-prefix `ARCH_32` reaches 1,068/1,098, gaining
82/losing 0 versus `ARCH_16` and gaining 44/losing 0 versus `PAIR_32`
(`p=1.14e-13`). Every conversation is nonnegative versus `PAIR_32`, so the
registered disposition is `FROZEN_BUDGET_REPLAY_SIGNAL`.

The prior 986-versus-1,024 difference of 38 was a net score gap, not 38
discordant items. `PAIR_32` had 57 rescues over `ARCH_16`, while `ARCH_16` had
19 in the other direction. `ARCH_32` recovers all 57 and preserves all 19.

Across the population, 209,257 additional members fit at p50 cost 78 chars and
p50 pair rank 119; final charge p50 is 31,995 chars. Thirty misses remain and
all are exact fit overflow. This shows continued availability from protected
capacity, but the volume of admitted members also confirms that much of the
mechanism is broad compressed exposure rather than selective stopping.

DA-101 separately validates exact Python allocation runtime at first-pass
p50/p95/max 59.9/76.9/85.9 ms and double-replay wall time 153.4 seconds. Reader
interpretation of the sentinel representation remains untested.

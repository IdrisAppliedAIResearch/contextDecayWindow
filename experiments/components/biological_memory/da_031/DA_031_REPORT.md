# DA-031 Self-Delimiting Varint Relative Pointers Report

**Status:** `PARTIAL_VARINT_RELATIVE_SIGNAL`
**Date:** August 30, 2026
**Protocol commit:** `eb7bfc1f`
**Codec commit:** `9bc50d7c`
**Blind allocation commit:** `f22fcb96`
**Standing:** spent cross-corpus exact-availability result

## Result

Self-delimiting varint pointers produce the strongest protected NF result in
this exploration while adding three LongMem completions.

| Corpus | DA-028 | DA-031 | Gains | Losses | Exact p |
|---|---:|---:|---:|---:|---:|
| NF-004 | 977 | **983** | **6** | 0 | .03125 |
| LongMemEval | 208 | **211** | 3 | 0 | .25 |

NF clears its >=2 bar, but LongMem does not clear the registered >=5 joint bar,
so the result is `PARTIAL_VARINT_RELATIVE_SIGNAL`. Every conversation and
question type is nonnegative.

## What Changed

Varint encoding removes coordinate separators and uses self-delimiting
five-bit groups. It is strictly shorter than DA-028 on all 1,098 NF questions
and 463/465 LongMem questions; two LongMem rows retain DA-028 exactly. Median
additional savings are 1,066 NF and 889 LongMem characters.

Those bytes fund 2,443 NF and 513 LongMem frozen-order additions. NF gains map
exactly to all five DA-029 prior-consumption residuals plus its one conjunction.
LongMem gains one initial-size, one prior-consumption and one wrong-member item.

This is stronger evidence for the upstream architecture hypothesis than a
substitution score would provide. The selected evidence identities/order remain
fixed; only the coordinate representation becomes denser. NF's delayed carriers
then enter without displacing anything.

## Ceiling

NF is now 983/986 on the one-hop-reachable ceiling. Its three remaining cases
were DA-029 wrong-member residuals unless their status changed under the new
arrival states. LongMem remains 39 below 250 and continues to have mixed
dependency blockers.

The next step is a residual audit, not immediate atomic composition. DA-030
showed that members fitting at carrier arrival may no longer fit after a fully
protected suffix. The audit must measure varint arrival and final states before
selecting the next representation.

Blind allocation SHA-256 is
`84c56868ce44a8349a0eee5fccdf5e1c5dde45aff28f17059470558125d25b57`;
outcomes replay byte-identically at
`f6e245412c8a9f6d0a9ff2705cc419a0e18de410fa90bce031490c1069fdb4d2`.
There were zero model, embedding and cache calls. No reader/runtime/adoption
claim follows.


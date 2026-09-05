# DA-030 Compact Plus Protected Atomic Composition Report

**Status:** `PARTIAL_COMPACT_ATOMIC_SIGNAL`
**Date:** August 30, 2026
**Protocol commit:** `e1f9e651`
**Blind allocation commit:** `672e5f36`
**Standing:** spent cross-corpus exact-availability result

## Result

Protected atomic completion composes with shortest-codec capacity on LongMem,
but not NF.

| Corpus | DA-028 | DA-030 | Gains | Losses | Exact p |
|---|---:|---:|---:|---:|---:|
| NF-004 | 977 | 977 | 0 | 0 | 1.0 |
| LongMemEval | 208 | **213** | 5 | 0 | .0625 |

All five LongMem gains are DA-029 wrong-frozen-member residuals. Knowledge
update gains one, multi-session two, preference one and single-session-user
one. Every group is nonnegative. LongMem clears its +5/zero-loss component;
NF misses the +2 bar, so the registered disposition is partial.

## Mechanism

DA-030 freezes the complete DA-028 state, then admits 567 NF and 742 LongMem
missing members. Median member costs are 80 and 115 characters. No strongest
payload is changed, and zero losses are structural.

The NF null resolves an apparent tension in DA-029. DA-029 called three NF
items wrong-member cases because the required member fit at that carrier's
original arrival. DA-030's stronger protection rule attempts it only after the
entire DA-028 suffix is fixed. By then the capacity has been consumed. Thus the
remaining NF problem is not identifying the alternate member; it is preserving
enough representation capacity through the full dependency sequence.

## Next Boundary

Local substitutions remain unjustified. They can recover earlier members only
by risking later evidence, which DA-025 already demonstrated. The safe path is
additional exact representation compression or an explicit dereferenceable
dependency interface. A denser self-delimiting pointer code is the next
self-contained test; external-store pointers would require a reader/tool
contract and cannot be credited as prompt evidence yet.

Blind allocation SHA-256 is
`cd69a0887cf2564d5929b7ee34947568f579327f86224ab9a88b1f77b0e52c2a`;
outcomes replay byte-identically at
`1bf2e3042f491ebd4565a86fc92d3794c38430c92cc813ec1bd24d64b00373fa`.
There were zero model, embedding and cache calls. No adoption follows.


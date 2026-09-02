# DA-033 LongMem Varint Plus Protected Atomic Tail Report

**Status:** `LONGMEM_VARINT_ATOMIC_SIGNAL`
**Date:** August 30, 2026
**Protocol commit:** `1c821f1e`
**Blind allocation commit:** `fe5adeb7`
**Standing:** spent LongMem exact-availability result

## Result

Protected atomic completion after the complete varint pack raises LongMem
delivery from 211 to 222 with eleven gains and zero losses.

| Control | Treatment | Gains | Losses | Exact p |
|---:|---:|---:|---:|---:|
| 211 | **222** | **11** | 0 | .0009766 |

Every question type is nonnegative: knowledge update gains four, multi-session
two, preference three, single-session-user one and temporal reasoning one.

## Mechanism

The blind allocator reconstructs and freezes every DA-031 payload, selected
codec and exact charge before attempting any missing member. It admits 842
members afterward at median cost 113 characters and median carrier position 3.
Zero losses are structural.

Nine completions are DA-032 wrong-frozen-member residuals. Two more complete
multi-carrier conjunctions because their missing members can be accumulated in
the protected tail. This is the clearest demonstration in the sequence that
capacity and dependency representation are complementary:

- varint coordinates preserve more capacity through the ordered pack;
- atomic member identities avoid paying for an unnecessary carrier half;
- immutable replay prevents either mechanism from displacing prior evidence.

LongMem now reaches 222/250 of its one-hop ceiling, 58 above direct delivery
164 and 34 above DA-016's 188. Remaining misses still require a fresh residual
audit before another composition.

Blind allocation SHA-256 is
`22b918036e5ecbd00c0cc032eef61f587b02c1c347505d458b310cd34a961d8e`;
outcomes replay byte-identically at
`cd02a10856d84780ec31834e9bfb096409f60a908e702f315190f452f12b097b`.
There were zero model, embedding and cache calls. Reader use, runtime and fresh
transfer remain unvalidated; no adoption follows.


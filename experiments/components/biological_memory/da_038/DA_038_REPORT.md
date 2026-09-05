# DA-038 Report

## Verdict

`PROTECTED_DA033_SENTINEL_SIGNAL`

Exact sentinel re-encoding of the complete DA-033 pack raises LongMem complete
evidence delivery from 222 to 232. There are 10 gains, zero losses, and a paired
exact p-value of .001953125. Every question type is nonnegative.

| Control | Treatment | Gains | Losses | One-hop ceiling |
|---:|---:|---:|---:|---:|
| 222 | **232** | **10** | **0** | 250 |

## Mechanism

The blind codec selects sentinel on 453/465 questions and saves 739 characters
at the median while preserving every DA-033 identity and member position. Only
after that immutable sequence does the treatment append fitting atomic members.
It admits 1,749 members at median cost 141 characters.

The ten gains resolve six DA-036 initial-size blockers, three prior atomic
consumption blockers, and the sole multi-carrier conjunction. This confirms
that stronger exact representation and atomic dependency identity compose when
the strongest existing order, rather than only its earlier prefix, is protected.

DA-037's independent reallocation produced 9 gains and 1 loss. DA-038 freezes
that lost DA-033 member before re-encoding, then recovers 10 gains with no
losses. The difference is protection of the established tail, not rescoring.

## Boundary

Eighteen frozen one-hop-reachable misses remain. This is still exact evidence
availability on a spent corpus; sentinel reader behavior, runtime and fresh
transfer are unvalidated.

Blind allocation SHA-256 is
`7758e13562c536fd5123583ccbf0082fd8f3315ddf29a68d74f10f12ee42703e`;
outcomes replay byte-identically at
`639b693b925ee7e92e5fef57276f2403f62e7834b9b69dfd1a991e5c1b1c9232`.
Model, embedding and cache calls: zero.

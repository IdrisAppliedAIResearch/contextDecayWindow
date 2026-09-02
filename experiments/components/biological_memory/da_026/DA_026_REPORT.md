# DA-026 Protected Atomic Tail Report

**Status:** `PROTECTED_ATOMIC_TAIL_SIGNAL`
**Date:** August 30, 2026
**Protocol commit:** `e0c7e812`
**Blind allocation commit:** `5ca10a2c`
**Standing:** spent LongMem exact-availability result

## Result

Replaying DA-023 completely before admitting any missing atomic member raises
complete evidence delivery from 202 to 207 with five gains and zero losses.
This clears the registered +5/zero-loss bar; every question type is
nonnegative. The paired two-sided exact p-value is .0625.

| Arm | Complete | Gain vs DA-023 | Loss vs DA-023 |
|---|---:|---:|---:|
| Direct | 164 | - | - |
| DA-016 | 188 | - | - |
| DA-023 immutable control | 202 | - | - |
| DA-026 protected atomic tail | **207** | **5** | **0** |

Knowledge update gains three, while multi-session and single-session-user gain
one each. Four of the five gains occur among DA-024's 20 wrong-frozen-member
residuals. Temporal reasoning, which lost five items under DA-025, is unchanged.

## Mechanism

The contrast with DA-025 identifies what did what:

- atomic members expose useful evidence hidden in the unselected half of a
  linked pair;
- pair-first allocation recovered more of it but reassigned the existing
  additive suffix, producing 17 gains and 8 losses;
- immutable replay removes that reassignment and retains 5 protected gains.

The blind allocator admits 574 missing members after the complete DA-023 pack
and skips 11,602 that do not fit. Median admitted cost is 109 characters and
median final slack is 31 characters. Gain questions finish with median 23
characters free. This is narrow recovery of fragmented residual capacity, not
unbounded token expansion: the strongest evidence order and 16k cap are fixed.

## Boundary

The policy is structurally zero-loss for exact availability because it never
removes, replaces, reorders or re-encodes a DA-023 payload. It remains a spent
corpus result, and the backreference syntax has no live-reader or runtime
validation. The remaining LongMem gap is 43 to the one-hop ceiling of 250.

Blind allocation SHA-256 is
`33faa3dd3f5efbe60eae62fea64bd1ad77771768177d3a8b9362662a86c190f7`;
outcomes replay byte-identically at
`a04e936a9cabeb3ab16265dbc5e9c23186f66f8cbe3a4a36f6b4690e0ed9f1c7`.
There were zero model, embedding and cache calls. No adoption follows.


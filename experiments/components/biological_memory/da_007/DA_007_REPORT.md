# DA-007 Immutable Direct-Prefix Reserve Report

**Status:** `NO_PROTECTED_CAPACITY_SIGNAL`
**Protocol commit:** `ea29c8f9`
**Blind-selection commit:** `e59c9e3e`
**Standing:** post-outcome representation diagnostic on spent NF-004 LoCoMo
**Calls:** 0 embedding, 0 model, 0 cache access
**Date:** August 29, 2026

## Result

Immutable direct-prefix reservation fixes DA-006's causal ambiguity, but no
tested reserve repays its evidence cost:

| Arm | Link gains | Suffix losses | Net |
|---|---:|---:|---:|
| `PAIR_R256` | 10 | 73 | **-63** |
| `TURN_R256` | 30 | 73 | **-43** |
| `PAIR_R512` | 43 | 123 | **-80** |
| `TURN_R512` | 35 | 123 | **-88** |
| `PAIR_R1024` | 48 | 220 | **-172** |
| `TURN_R1024` | 35 | 220 | **-185** |
| `PAIR_R2048` | 45 | 456 | **-411** |
| `TURN_R2048` | 33 | 456 | **-423** |

Every gain is carried by the linked dialogue payload. Every loss is carried by
the explicitly dropped direct suffix. No core identity reroutes. All arms are
`NO_PROTECTED_CAPACITY_SIGNAL`.

## Compact Turns

Compact turns help only when the reserve is tight. At 256 characters they fit
on 13,142 blind edges versus 6,863 for full pairs and produce 30 gains versus
10. Direct comparison has 24 turn-only complete actions and 4 pair-only.

At 512 characters, full pairs overtake turns: 43 gains versus 35, with 12
pair-only complete and 4 turn-only. At 1024 and 2048, fit is no longer the
constraint; the full pair preserves both possible evidence-bearing members and
wins 13-0 and 12-0 on exact discordances.

Lexical turn choice therefore trades coverage for compactness. It is useful at
the smallest reserve, but not sufficient to overcome the reservation cost.

## Why Reservation Loses

The direct tail is not expendable. `TURN_R256`, the least harmful arm, is
positive in five conversations but loses 48 actions in `conv-44` and 25 in
`conv-43`, producing net -43 overall. This mirrors the earlier warning that
tail position does not certify absence of evidence.

Reservation is also frequently wasted. `TURN_R256` has median total evidence
characters 15,674 and median unused reserve 222 characters. Larger reserves
waste more: `PAIR_R1024` has median unused reserve 878. A fixed reserve removes
direct content even when a link is already represented, does not fit, or uses
only a fraction of the allocation.

DA-004's nine downstream-carried gains are retained by no arm. They were
packing side effects, not evidence in the linked neighbor. `PAIR_R1024`
recovers all 48 genuine neighbor-carried DA-004 benefits, but incurs 220 suffix
losses.

## Consequence

Hard global reservation is closed for this representation. The useful pieces
are narrower:

1. DA-004 can rank likely benefit before admission;
2. compact turns improve very small link payloads;
3. unconditional capacity removal is too expensive and too often unused;
4. direct suffix position cannot serve as an evidence-protection rule.

The unresolved architecture needs capacity that is created only when justified
without pre-dropping evidence, such as a separately compacted direct rendering
whose evidence preservation is validated independently. Combining a tuned
DA-004 benefit threshold with eviction on this spent corpus is not authorized.

## Integrity and Boundary

All 26,100 blind rows replayed byte-identically. The join reproduced
935/1,098 direct complete items and exact DA-004 labels. Result SHA-256 is
`55ec8a6500d187070174a297c2be3911a71c4155afe8ee309bdcf8fc5fb88a62`.

No reserve, renderer, gate, reader, implementation change, or adoption is
authorized.

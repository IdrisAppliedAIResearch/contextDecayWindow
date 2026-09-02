# DA-001 Light Linked-Context Exploration Report

**Status:** `LOCAL_LINK_SIGNAL`; full-event expansion regresses
**Standing:** post-outcome descriptive exploration on spent NF-004 LoCoMo
**Protocol commit:** `1c0f9543`
**Blind-selection commit:** `1181e24d`
**Population:** 1,098 primary questions; 188 NF-004 discordances
**Calls:** 0 embedding, 0 model, 0 cache misses
**Date:** August 29, 2026

## Result

Explicit temporal links recover exact evidence that direct pair ranking misses.
Every fixed one-hop arm improves complete-evidence delivery over NF-004's direct
935/1,098 baseline:

| Arm | Complete | Gains | Losses | Net | Median linked chars | Median displaced |
|---|---:|---:|---:|---:|---:|---:|
| `DIRECT` | 935 | 0 | 0 | 0 | 0 | 0 |
| `TEMPORAL_1` | 950 | 17 | 2 | **+15** | 471 | 0 |
| `TEMPORAL_2` | 951 | 21 | 5 | **+16** | 897 | 2 |
| `TEMPORAL_4` | 956 | 27 | 6 | **+21** | 1,718 | 3 |
| `TEMPORAL_8` | 959 | 38 | 14 | **+24** | 3,281 | 7 |
| `TEMPORAL_16` | 963 | 51 | 23 | **+28** | 6,243 | 14 |

All 154 treatment-only and control-only outcomes across these five arms have
the expected causal accounting: every gain's missing evidence entered through
a link, and every loss's formerly delivered evidence was displaced by linked
content. This is not a session-touch surrogate.

The result is not uniform across conversations. Net changes for seed counts
1/2/4/8/16 are:

| Conversation | T1 | T2 | T4 | T8 | T16 |
|---|---:|---:|---:|---:|---:|
| `conv-26` | +7 | +6 | +6 | +11 | +11 |
| `conv-30` | +1 | +2 | +3 | +3 | +3 |
| `conv-43` | +4 | +4 | +6 | +7 | +12 |
| `conv-44` | **-1** | **-1** | **-1** | **-2** | **-7** |
| `conv-49` | +2 | +3 | +5 | +5 | +9 |
| `conv-50` | +2 | +2 | +2 | 0 | 0 |

The whole matrix is descriptive. No seed count is selected, and the monotonic
aggregate should not hide `conv-44`'s monotonic regression.

## Full Event Expansion

Expanding an entire source session is too blunt:

| Arm | Complete | Gains | Losses | Net | Median linked chars | Median displaced |
|---|---:|---:|---:|---:|---:|---:|
| `EVENT_1` | 939 | 21 | 17 | +4 | 2,576 | 7 |
| `EVENT_2` | 939 | 32 | 28 | +4 | 4,733 | 13 |
| `EVENT_4` | 918 | 44 | 61 | **-17** | 8,536 | 23 |
| `EVENT_8` | 858 | 50 | 127 | **-77** | 14,187 | 39 |
| `EVENT_16` | 845 | 49 | 139 | **-90** | 14,470 | 41 |

`EVENT_8` recovers 47/48 original session-inheritance rescues, showing that the
needed derivative context is usually present in the source session. But it
retains only 14/140 original pair-ranking gains. By `EVENT_16`, it retains 2.
Recovering context by loading the event reproduces the old failure: context
capture displaces directly relevant facts.

## Interpretation

The fact/context disconnect is visible under a minimal linked representation.
The direct fact proxy often needs nearby source context, and one temporal hop
can supply it cheaply. The useful relation is local: predecessor/successor, not
unconditional event membership.

This narrows the upstream architecture hypothesis:

1. keep small units directly addressable;
2. retain typed links to derivative context;
3. expand links locally and account for what they displace;
4. do not render an entire event merely because one member matched.

The exploration does not identify when expansion is safe. NF-004's earlier 58
evidence-blind features failed cross-conversation prediction, and `conv-44`
regresses here under every arm. Tuning a gate on these outcomes would reuse the
spent holdout. A successor needs a fresh corpus or a new prospective information
signal tied to query obligations.

## Preflight and Integrity

The label-blind stage generated all 11 orders for 1,104 questions twice with
byte-identical compressed SHA-256
`76f537ca26ee6e6212cdf0669c19e5c59fb291aed9007cddb0a1d0d6cc7ae831`.
Traversal tests enforce session boundaries, graph-distance order,
deduplication, singleton behavior, direct suffix order, and `m=0` identity.
Every cache lookup hit; no call was made.

After the blind artifact was committed, the label join exactly reproduced
NF-004's 935 direct complete deliveries and original 140 pair gains, 48 session
rescues, and 910 concordances. Result SHA-256 is
`1003b3d83221997ec7b05eb31abaf8f2127268e09b7c4321734595b42d7c4e49`.

## Boundary

Adjacent-turn pairs and source sessions are proxies, not a completed fact/event
data architecture. This does not test atomic extraction, entity links,
supersession links, temporal reasoning, rendering, or reader use. It authorizes
no selector, implementation change, live run, or adoption.

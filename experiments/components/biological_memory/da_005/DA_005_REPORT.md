# DA-005 Structural Displacement Guard Report

**Status:** `STOPPED_AT_PF4`; hard protection is vacuous
**Protocol commit:** `f7873bd`
**Standing:** label-blind preflight on spent NF-004 LoCoMo
**Calls:** 0 embedding, 0 model, 0 cache access
**Date:** August 29, 2026

## Stop

Preflight PF4 failed before evidence labels were opened. Of 26,100 blind edge
actions, **zero** can add any candidate while displacing zero direct candidates.
`COUNT_0`, the only guard safe by construction at exact evidence availability,
therefore admits nothing.

| Guard | Blind admissions |
|---|---:|
| `OPEN` | 14,064 |
| `COUNT_0` | **0** |
| `COUNT_1` | 4,285 |
| `COUNT_2` | 11,127 |
| `COUNT_4` | 14,025 |
| `CHARS_256` | 3,395 |
| `CHARS_512` | 11,888 |
| `CHARS_1024` | 14,062 |
| `DUAL_1_512` | 4,146 |

The fixed direct pack leaves no usable headroom. Every nontrivial link action
must replace at least one directly selected candidate. Caps above zero may
reduce the blast radius, but they cannot protect evidence structurally because
the single displaced candidate may be required.

## Consequence

No evidence join or benefit/harm table was run. Under the current whole-pair
representation and fixed 16k budget, hard displacement protection and useful
link admission are mutually exclusive.

The next mechanism must create headroom rather than merely ration displacement.
The two concrete options are:

1. shrink linked payloads to query-relevant atomic turns or spans while keeping
   direct evidence units intact;
2. compact or reserve the direct representation prospectively, then spend only
   that independently created capacity on links.

Both change the representation or budget allocation and require a new
registration. This stop authorizes no guard, threshold, reader, or adoption.

Blind decision artifact SHA-256 is
`534c3285b2aa42657785742a64ca1b5e80bca1645b402380ce13a4cfc23a8ab4`.

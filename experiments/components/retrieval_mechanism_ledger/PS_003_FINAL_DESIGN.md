# PS-003 Final Design Lock

**Date:** August 11, 2026
**Pre-registration commit:** `63a0937bc303ee9eac595a84fb3780d12ebe6500`
**Pre-registration SHA-256:** `32CFE67EEF9B21478FAA40352C8D607E1FA6CF417BA9F89063F2B046306405A0`
**Part 1 artifact commit:** `fac01c426370fc7fc2be8644804190632c0bf782`
**Part 1 exploration SHA-256:** `9C1E2D08D92374EB6C51834B295FB5DB041E24C3D837C5ECCDDC49195A483CA6`
**Selected-cell deterministic digest:** `70B23E1D5B06AF7EC1DA797DCA829CE6248A5816D2F8AB6D31518CB02A2C985B`
**Two-process comparison commit:** `2f370013e9f6d6c37cc7e684a7b2210d7980f696`
**Two-process mechanism digest:** `7FC45BC03FE51C053FA20E561BF028F8F1DC52D8678271AA35AFA090580394FD`
**Canonical artifact-sequence digest:** `5A4E27F5B27424426FED798BA331B4875695A5506EC262355AB4F86DDA2DECB1`
**Label status:** UNOPENED
**Part 2 status:** AWAITING SEPARATE AUTHOR AUTHORIZATION

## Selected cell

The mechanical Section 5 rule selects:

```text
P = 5 probes
S = 4 swaps per non-base probe
TARGET_OUTPUTS = 8
ATTEMPT_BUDGET = 16
SUPPORT_WIDTH = 4
TEMPERATURE = 0.025
```

All four cells were eligible. The selected cell is the eligible cell with the
greatest swap count and then greatest probe count. It accepted 192 unanimous
outputs in 197 attempts, rejected three cyclic families, one spurious family,
and one disagreement, and used at most 12 attempts for any query. Both exact
PS-002 unsafe base cues were encountered, rejected, and emitted no identity.

## Unchanged Part 2 gates

No threshold or ordering changes from the locked pre-registration:

1. G1 requires exact PS-001 and PS-002 identities and 119/119 fixed points.
2. G2 requires the selected cell to retain every mechanical eligibility rule
   and pass PF7 replay.
3. G3 requires at least 9/12 lookup facts and at least 2/3 in every domain.
4. G4 requires at least direct-cosine top-eight lookup +2 with no domain loss.
5. G5 requires exactly eight unique identities for every query with no
   label-dependent retry.

The first matching registered disposition remains binding. Chained and
enumeration measurements remain non-gating stress tests and cannot rescue G3 or
G4.

## Authorization boundary

This lock was produced from committed label-blind artifacts only. It contains no
answer-key facts, source turns, domains, required terms, relevance counts, or
scores. Measurement code may not be implemented or run until the author grants
separate Part 2 authorization bound to this file's committed identity.

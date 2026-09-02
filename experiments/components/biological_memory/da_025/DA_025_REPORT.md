# DA-025 LongMem Atomic Backreference Additions Report

**Status:** `NO_LONGMEM_ATOMIC_ADDITION_SIGNAL`
**Date:** August 30, 2026
**Protocol commit:** `89ab1b15`
**Blind allocation commit:** `230b45bf`
**Standing:** spent LongMem exact-availability result

## Result

Pair-first atomic fallback raised complete evidence delivery from DA-023's 202
to 211, but did so by trading 17 gains for 8 losses. It therefore failed the
registered zero-loss and every-type-nonnegative bars. DA-023 remains the
strongest protected order.

| Arm | Complete | Gain vs DA-023 | Loss vs DA-023 |
|---|---:|---:|---:|
| Direct | 164 | - | - |
| DA-016 | 188 | - | - |
| DA-023 | 202 | - | - |
| DA-025 | **211** | 17 | 8 |

The paired two-sided exact p-value is .108. Against the immutable DA-016
baseline, DA-025 is +23/0, so the loss mechanism is wholly within the additive
suffix rather than the protected direct and linked payloads.

## Mechanism

The atomic representation is useful but the pair-first order is unsafe. It
rescues 15/20 DA-024 wrong-frozen-member residuals with zero losses inside that
audited subset. Across the full population, however, admitting pairs and other
members changes which DA-023 suffix members survive.

Knowledge update is +7/-1 and multi-session +6/-1, while temporal reasoning is
+1/-5. Gains and losses are both tail events: median remaining capacity is 23
characters for gain questions and 21.5 for loss questions. Median final use is
15,970/16,000 characters overall.

This identifies the useful operation and the failed policy separately:

- alternate atomic members carry real evidence;
- attempting them before preserving DA-023's suffix reassigns scarce capacity;
- evidence-blind local cost cannot certify that reassignment as harmless.

The next protected test must replay DA-023 byte-for-byte, then attempt alternate
members only in residual capacity. It may add evidence but cannot substitute
for any strongest-order admission.

Blind allocation SHA-256 is
`2ce54a9c4bec30046eaa583eb543af6e4050c0c790258878aa797f691292aa14`;
outcomes replay byte-identically at
`5c4589ed041eb0c0649879aacd2a5c42514d89c20c2951d9818df36f1674ac69`.
There were zero model, embedding and cache calls. No adoption follows.


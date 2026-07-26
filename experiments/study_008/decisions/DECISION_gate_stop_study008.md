# Decision — STOP at Study 008 Joint Replay Gates

**Tasks:** S8-T-011 through S8-T-014
**Date:** July 26, 2026
**Status:** BINDING STOP

## Decision

Do not run the 35-turn ablations or any full Study 008 arm.

No swept `c_fill` from 1 through 50 satisfies Gate 2 and Gate 3 jointly at the
locked `B_ltm = 32,000` and `k_min = 1`.

## Evidence

- Arm A replay reproduces both accepted Study 007 probe blocks byte-for-byte.
- Study 007's 271 preserved artifacts remain hash-identical before and after
  each replay.
- Before Amendment 001, content-only span charging admitted nearly the entire
  store and made targeted majority impossible in C/D.
- Amendment 001 corrected the accounting to exact serialized span-element cost
  without changing any gate criterion.
- After the correction, Arm C passes every targeted fixture but never reaches
  fact-aware four-domain coverage at both breadth probes.
- Arm B reaches fact-aware four-domain coverage at both probes only at
  `c_fill = 1`, where it fails targeted preservation.
- Arm B passes targeted preservation from `c_fill = 5` onward, where it misses
  monetary coverage at Q11.
- Arm D reaches targeted preservation only at `c_fill = 50`; at that value both
  span arms still miss art facts at the breadth probes.

The conjunction is therefore empty:

| Region | Breadth gate | Targeted gate | Joint verdict |
|---|---|---|---|
| `c_fill = 1` | B passes 4/4 | B/D fail | STOP |
| `c_fill = 5..40` | No arm passes both probes | A/B/C pass targeted; D fails | STOP |
| `c_fill = 50` | No arm passes both probes | All arms pass targeted | STOP |

## Interpretation boundary

This is a pre-run design result. It does not evaluate rubric Bars 0–3, Factors F
or R on generated answers, P2–P5, or any live-run outcome. P1 alone is
adjudicated because Gate 1 directly tested it.

The evidence shows that the registered floor/fill policy cannot simultaneously
buy fact-aware breadth and preserve targeted allocation under the fixed budget
and bare-span rendering. Continuing would require a new policy level, such as
minimal surrounding context, query-adaptive allocation, or formation-side
per-domain guarantees. Those are new study designs, not blocker amendments to
this factorial.

## Authorization

The preregistration requires STOP when the gates do not pass jointly. The study
author's amendment authority permits good-faith blocker corrections, not
post-hoc criterion softening or an unregistered third factor. Amendment 001
corrected the one demonstrated accounting defect; the corrected gates still
fail, so STOP is mandatory.

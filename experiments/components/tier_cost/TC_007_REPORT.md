# TC-007 Report — protected spread against full-budget relevance

**Standing:** `REGISTERED-OFFLINE`  
**Status:** `COMPLETE`  
**Pre-registration:** `TC_007_PRE_REGISTRATION.md`  
**Pre-registration commit:** `afb7564369e3f76970b5c637f9eb6faf7706db61`  
**Pre-registration SHA-256:** `0e2d26d741e1947e1b39478db1d61ac7aa18c15ce0dc4d9f397de4babb892fd9`  
**Final G0 commit:** `028f67d4a30b1aa7ba37c5e0ec9824e8af083f2a`  
**Run-artifact commit:** `2f2924282b7578f33dc639dbe6d3535bfc5f995f`  
**Date:** 2026-08-23

## Verdict

The fixed 50/50 relevance/spread architecture does not beat full-budget dense
retrieval under the registered joint rule. Neither spread treatment improves
both combined and breadth complete-evidence delivery at both budgets while
protecting targeted questions.

> **Disposition: `NO_SPLIT_SELECTED`; frozen fallback: `A_RELEVANCE_FULL`.**

The A3 spread route is close to dense at 32k, but it loses at 16k and does not
improve breadth completeness. Its disposition is `MIXED_OR_NO_DIFFERENCE`.
The facility-location route is worse at both budgets and receives
`CONTROL_WORKS`.

In plain terms: reserving half the context for broad coverage did not buy more
complete outlier answers. A3 sometimes found evidence dense missed, especially
at 32k, but the reservation also removed dense evidence. Facility location
removed substantially more than it added.

## Registered complete-evidence contrasts

The family contains 12 directional tests. Works alpha is `.01/12 =
.0008333333`; signal alpha is `.10/12 = .0083333333`. The practical bands are
2/0/2 for combined/breadth/targeted at 16k and zero at 32k.

| Spread arm | Budget | Population | Dense | Split | Gains | Losses | Net | Split p | Dense p | Reading |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| A3 | 16k | Combined | 749 | 739 | 3 | 13 | -10 | .9979 | .01064 | Neither signal direction clears |
| A3 | 16k | Breadth | 16 | 13 | 0 | 3 | -3 | 1.000 | .1250 | Neither signal direction clears |
| A3 | 16k | Targeted | 643 | 637 | 2 | 8 | -6 | .9893 | .05469 | Guardrail does not fire |
| A3 | 32k | Combined | 810 | 812 | 4 | 2 | +2 | .3438 | .8906 | Neither signal direction clears |
| A3 | 32k | Breadth | 27 | 27 | 0 | 0 | 0 | 1.000 | 1.000 | Exact tie |
| A3 | 32k | Targeted | 680 | 681 | 1 | 0 | +1 | .5000 | 1.000 | Guardrail passes |
| Facility | 16k | Combined | 749 | 692 | 7 | 64 | -57 | 1.000 | 6.30e-13 | Dense clears works |
| Facility | 16k | Breadth | 16 | 9 | 1 | 8 | -7 | .9980 | .01953 | Direction adverse; alpha not cleared |
| Facility | 16k | Targeted | 643 | 603 | 4 | 44 | -40 | 1.000 | 7.57e-10 | Targeted guardrail fires |
| Facility | 32k | Combined | 810 | 774 | 10 | 46 | -36 | 1.000 | 6.23e-7 | Dense clears works |
| Facility | 32k | Breadth | 27 | 20 | 1 | 8 | -7 | .9980 | .01953 | Direction adverse; alpha not cleared |
| Facility | 32k | Targeted | 680 | 657 | 6 | 29 | -23 | 1.000 | 5.84e-5 | Targeted guardrail fires |

A3 fails the joint rule at both budgets: the 16k combined and breadth directions
are adverse, while 32k breadth is a tie. Facility fails it decisively and loses
combined and targeted delivery in the dense direction at both budgets. Thus no
treatment is eligible for the registered architecture-selection tiebreaker.

## Did spread add evidence or only relabel it?

Spread did add some evidence dense omitted; it was not merely an ownership
relabel. Every treatment-only evidence identity came through the spread route.
The relevant question is whether those additions exceeded displacement.

| Arm | Budget | New evidence ids vs dense | Dense evidence ids lost | Net evidence ids |
|---|---:|---:|---:|---:|
| A3 | 16k | 5 | 14 | -9 |
| A3 | 32k | 7 | 3 | +4 |
| Facility | 16k | 9 | 80 | -71 |
| Facility | 32k | 17 | 63 | -46 |

For the 44 breadth questions alone, A3 adds/loses 1/4 evidence identities at
16k and 2/1 at 32k. That raises breadth any-evidence delivery from 41 to 42 at
16k and from 41 to 43 at 32k, but complete delivery moves 16 to 13 and 27 to
27. The route finds occasional outliers without assembling more complete
multi-item answers.

The facility route adds/loses 3/21 breadth evidence identities at 16k and 6/22
at 32k. Its diversity objective is active, but the protected share spends too
much budget away from query evidence.

These counts also answer the ownership surrogate: spread evidence in a selected
block is not automatically incremental. A3 owns 88/86 evidence identities over
all eligible questions at 16k/32k, but only 5/7 are treatment-only relative to
dense. Ownership count would therefore overstate the mechanism's gain.

## Budget and packing

All arms fill the same total character ceiling. Mean payloads over 868 eligible
questions are 15,965/31,965 characters for dense, 15,965/31,964 for A3, and
15,964/31,965 for facility. This is not a slack-budget result.

Mean delivered candidates at 16k/32k are 54.16/108.60 for dense,
54.72/109.28 for A3, and 53.99/104.58 for facility. Counts are diagnostics,
not endpoints: A3 can deliver slightly more candidates while complete breadth
falls, and facility can deliver roughly the same count at 16k while losing 57
complete questions.

## Integrity and execution

Final G0 ran before the accepted outcomes. It reproduced TC-003 C5 at
`718/748` and `806/811`, all 2,613 TC-005 dense payloads, 3,484 treatment-budget
Preflight traces, and 1,742 sham payloads. The leakage audit and planted
violation passed. The full suite passed with 2,198 tests.

Two earlier outcome attempts stopped without persisting or aggregating results.
The first exposed wall-clock metadata in a gzip header; the second exposed an
internal `eligible`/`combined` label mismatch. Both harness repairs were
committed, the earlier G0 artifacts were left immutable, and final G0 was rerun
against the repaired source before the accepted run. No arm, budget, endpoint,
bar, or disposition rule changed.

Two fresh accepted-run workers produced identical identities, attributions,
payloads, outcomes, and file digests:

- `per_question.csv`: `af8af14b52828ff9e3bd3f061d7ad77ef19fa4cd5e2fcb1b44881343567425ec`
- `diagnostics.jsonl.gz`: `660ae5531277030a3c806668135415971a9038c17bb4737cbd7f69b315c626a3`

The run used 2,247 cached vectors with zero misses, zero embedding calls, and
zero LLM/generative calls. Under this programme's terminology it is model-free:
embedding models are reported separately and are not counted as LLM calls.

Primary artifacts:

- `artifacts/tc007/preflight/tc007_preflight_part1.json`
- `artifacts/tc007/preflight/tc007_preflight_pf4_reachability.json`
- `runs/tc007/g0_final/g0_reproduction.json`
- `runs/tc007/run/per_question.csv`
- `runs/tc007/run/diagnostics.jsonl.gz`
- `runs/tc007/run/summary.json`
- `runs/tc007/run/verdict.json`
- `runs/tc007/run/determinism.json`

## Claim boundary and handoff

This is evidence availability on an already-used LoCoMo development corpus. It
does not test reader accuracy, prove that 50/50 is globally wrong, choose an
enterprise budget, tune the spread share, or show that another coverage
objective cannot work. It tests the frozen A3 and facility orders under the
fixed 50/50 allocation the user asked about.

The result freezes dense full-budget retrieval for any later reader comparison.
TC-006 is not started here. Its reader, contexts, prompt, scorer, schedule, and
fact-use bars still require their own Preflight and standalone registration.

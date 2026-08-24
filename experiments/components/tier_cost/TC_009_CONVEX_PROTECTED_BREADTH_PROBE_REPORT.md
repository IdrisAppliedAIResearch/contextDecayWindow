# TC-009 convex relevance with protected breadth — report

**Status:** `NO_POSITIVE_SIGNAL`; descriptive feasibility diagnostic  
**Design commit:** `1efec148`  
**Implementation and Preflight commit:** `d2a7e2f8`  
**Date:** 2026-08-23

## Result

The 50/50 protected architecture works at 32k but not at 16k. At 32k it
restores all four breadth questions lost by full-budget convex fusion while
retaining eight of convex fusion's nine combined gains over dense. At 16k the
reservation takes too much relevance capacity and falls below dense on breadth.

| Budget | Arm | Combined complete | Targeted complete | Breadth complete |
|---:|---|---:|---:|---:|
| 16k | Full dense | 749 | 643 | 16 |
| 16k | Full CC80 | **771** | **666** | **17** |
| 16k | Dense + A3 50/50 | 739 | 637 | 13 |
| 16k | CC80 + A3 50/50 | 757 | 653 | 14 |
| 32k | Full dense | 810 | 680 | **27** |
| 32k | Full CC80 | **819** | **689** | 24 |
| 32k | Dense + A3 50/50 | 812 | 681 | **27** |
| 32k | CC80 + A3 50/50 | 818 | 686 | **27** |

At 32k, treatment versus dense is 9 gains/1 loss combined, 6/0 targeted, 0/0
breadth complete and +1 breadth identity. All four conversation nets are
nonnegative. Against full CC80, protected A3 recovers the four prior enumeration
losses—Maria's friends, John's causes, Joanna's screenplays, and John/James
meeting plans—but loses CC80's Deborah-activities breadth gain. The result ties
dense breadth at 27 rather than exceeding it.

At 16k, treatment versus dense is 20/12 combined and 16/6 targeted, but breadth
is 1/3 with -2 identities and one conversation regresses. Relative to full
CC80, protection costs 14 combined and 13 targeted completions. The frozen
two-budget rule therefore returns `NO_POSITIVE_SIGNAL`.

## Interpretation

The two components are compatible when the budget is large enough. CC80 is
better than dense inside the identical split: treatment beats dense+A3 by 18
combined questions at 16k and 6 at 32k. A3 also repairs CC80's specific 32k
enumeration failures. The problem is the fixed share, not an inherent conflict
between score fusion and protected breadth.

“50/50” means two solo allowances before deduplication and relevance-only slack
return; it does not guarantee the final payload is half relevance and half
spread. Median treatment admissions are 25 relevance + 28 spread + 1 returned
at 16k and 52 + 57 + 1 at 32k.

The observed budget interaction does not authorize changing the share after
seeing results. A lower or budget-dependent protection share would be a new
factor and requires a separate registered test.

## Integrity and boundary

Label-blind Preflight froze all treatment contexts before opening predecessor
outcomes, reproduced 6,968 accepted TC-007 and convex-probe order/payload
checks, and showed nonempty A3 admissions on 871/871 questions at both budgets.
It used 2,236 cache hits, zero misses, zero embedding calls and zero LLM calls.
Outcome used sealed selections with zero ranking or model calls.

Availability only on used LoCoMo development data. No architecture selection,
share tuning, TC-010, deployment, or reader answers are authorized.

The final repository suite is 2,242 passed.

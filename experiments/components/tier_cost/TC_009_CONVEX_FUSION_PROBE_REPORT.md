# TC-009 normalized convex-fusion probe — report

**Status:** `NO_POSITIVE_SIGNAL`; descriptive feasibility diagnostic  
**Design commit:** `7ee6badb`  
**Implementation and Preflight commit:** `ca85b048`  
**Date:** 2026-08-23

## Result

Normalized score fusion is substantially better than TC-005's rank-only RRF
and improves dense retrieval on combined and targeted questions at both
budgets. It nevertheless fails the frozen positive rule because 32k breadth
complete delivery regresses.

| Budget | Arm | Combined complete | Targeted complete | Breadth complete |
|---:|---|---:|---:|---:|
| 16k | Dense | 749 | 643 | 16 |
| 16k | RRF | 755 | 657 | 13 |
| 16k | 80/20 convex | **771** | **666** | **17** |
| 32k | Dense | 810 | 680 | **27** |
| 32k | RRF | 804 | 682 | 18 |
| 32k | 80/20 convex | **819** | **689** | 24 |

Against dense, convex fusion has 30 gains/8 losses at 16k and 18/9 at 32k
combined. Targeted is 26/3 and 11/2. Every conversation has a positive combined
net at both budgets. Breadth identities are +5 at 16k and neutral, +6/-6, at
32k. However, 32k breadth complete is 1 gain/4 losses, which fires the sole
failed clause. RRF cannot rescue that contrast and is itself worse than convex
fusion by 16 and 15 combined complete questions at 16k/32k.

## What happened

The scholarly hypothesis is supported narrowly: score distances contain useful
information that RRF throws away. Query-wise min-max normalization followed by
a semantic-heavy 80/20 mixture improves direct evidence ranking consistently.
It is a better candidate for a **semantic arm** than TC-005's RRF order.

It is not a complete replacement for dense. Post-outcome inspection shows all
four 32k breadth losses are enumeration questions: where Maria made friends;
causes John supports; how many screenplays Joanna wrote; and places/events
where John and James planned to meet. Each loses one of several required
carriers. The sole gain asks for Deborah's activities besides yoga and adds the
fifth required carrier.

This is the same architectural boundary seen elsewhere in the arc: improving
query-focused ranking does not automatically preserve multi-session
enumeration.

## Integrity and boundary

Label-blind exploration established nonzero dense and BM25 ranges on 871/871
questions. The treatment changes all 871 full orders and nearly every packed
selected set, so it is not a tie-break. Preflight froze and hashed treatment
selections before opening TC-005's label-bearing artifact, then reproduced all
3,484 accepted dense/RRF order-and-payload checks. It used 2,236 sealed cache
hits, zero misses, zero embedding calls, and zero LLM/generative calls. Outcome
used the sealed selections with zero cache, BM25, embedding, or LLM calls.

This is availability only on used LoCoMo development data. It supports future
consideration of normalized convex fusion inside a separately protected
semantic arm; it does not establish the coefficient, select an architecture,
authorize TC-010, or run reader answers.

The final repository suite is 2,241 passed.

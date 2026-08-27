# TC-013 CC80-parent ASPECT fan-out — report

**Status:** `CHARACTERIZED`; budget-specific offline availability signal  
**Design commit:** `4835c606`  
**Registration SHA-256:** `52f4ccdd3ee1f261a80fb2eb6b27953b896c712d63c5d817a6b0415b8fd4d8b9`  
**Preflight commit:** `6a161e07`  
**Outcome commit:** `6767d6de`  
**Date:** 2026-08-25

## Result

The proposed fan-out is meaningfully better than TC-011's global static
ASPECT, and at 32k it produces the first protected-ASPECT result in this arc
that slightly exceeds full-budget CC80 while preserving targeted completeness.
The gain does not transfer to 16k.

| Budget | Arm | Combined | Targeted | Breadth | Other |
|---:|---|---:|---:|---:|---:|
| 16k | Full CC80 | **771** | **666** | **17** | 88 |
| 16k | Global static ASPECT | 749 | 645 | 15 | 89 |
| 16k | CC80-parent fan-out | 763 | 654 | 16 | **93** |
| 32k | Full CC80 | 819 | **689** | 24 | **106** |
| 32k | Global static ASPECT | 810 | 680 | 23 | 107 |
| 32k | CC80-parent fan-out | **821** | **689** | **26** | **106** |

Against full CC80 at 32k, fan-out has 16 complete gains and 14 losses overall,
5/3 on breadth, 6/6 on targeted, and 5/5 on other questions. Breadth required
identities gain 12 and lose 6. Conversation nets are `+2`, `+3`, `-2`, `-1`,
so the small aggregate gain is not conversation-consistent.

At 16k the same mechanism has 16 gains and 24 losses overall. Targeted is
6/18, breadth 2/3, and other 8/3. The semantic cost is therefore concentrated
in direct questions even though the other population improves.

Against global static ASPECT, fan-out improves combined completeness by 14 at
16k and 11 at 32k. It improves targeted by 9 at both budgets and breadth by 1
and 3. Making every semantic result its own local parent is safer than one
global facet-coverage walk on this development corpus.

## What “one child per CC80 result” did

Every CC80 item admitted under the semantic half received exactly one
singleton-seeded ASPECT proposal attempt in CC80 order. All attempts found a
positive, unique child:

- 16k: median 25 parents/proposals, 22 children admitted, 3 rejected by the
  protected half, and 1 CC80 item returned through slack;
- 32k: median 52 parents/proposals, 46 children admitted, 6 rejected by the
  protected half, and 1 CC80 item returned through slack.

Thus “one attempt per parent” is exact, while “one serialized child per parent”
is not possible under the fixed 50/50 character allowance. Capacity binds on
722/871 traces at 16k and 784/871 at 32k.

Each child uses TC-011's unchanged query CC80 relevance and IDF-weighted facet
marginal, but seeds covered facets from only its own CC80 parent. All CC80
parents and previously proposed children are excluded globally. Children do
not recurse.

## Integrity and boundary

Preflight reproduced 3,484 frozen full-CC80 and global-static-ASPECT selected
identity sequences and payload digests. It recorded 2,236 cache hits, zero
misses, zero embedding calls and zero LLM/generative calls. Focused TC-010,
TC-011 and TC-013 tests pass 8/8.

This is a development-corpus availability signal, not an answer result or an
adoption decision. The treatment has no registered decision bar, is negative
at 16k, and its 32k gain is small and inconsistent across conversations. Full
CC80 remains the fallback. A reader run, transfer claim, share tuning, parent
ordering change or deployment change requires separate authorization.


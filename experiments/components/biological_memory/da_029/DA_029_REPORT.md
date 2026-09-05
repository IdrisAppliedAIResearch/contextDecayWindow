# DA-029 Compact Residual Dependency Audit Report

**Status:** `COMPLETE; MIXED RESIDUAL BLOCKERS`
**Date:** August 30, 2026
**Protocol commit:** `a8d0c689`
**Standing:** spent evidence-aware causal audit

All 51 ceiling-reachable residuals after DA-028 classify without an unaccounted
case.

| Blocker | NF-004 | LongMemEval |
|---|---:|---:|
| Wrong frozen member | 3 | 24 |
| Prior compact consumption | 5 | 10 |
| Multi-carrier conjunction | 1 | 5 |
| Initial compact size | 0 | 3 |

Neither corpus has a class at the registered 60% dominance threshold. LongMem
wrong-member cases are close at 24/42 (57.1%); NF prior consumption is 5/9
(55.6%). There is no shared dominant successor.

The audit explains DA-028's asymmetric conversion. Compact savings reduce
LongMem prior-consumption blockers from 17 to 10, but expose wrong-member choice
as the largest residual. NF still reaches the right carrier too late in five
cases: median initial slack is 598.5 characters, but median arrival slack has
fallen to 38 against median required cost 105.

The next strongest protected composition is mechanical: freeze the complete
DA-028 compact pack, then apply DA-026's missing-member tail. It targets the 27
wrong-member residuals without changing codec choice, carrier order or any
existing admission. The 15 prior-consumption cases and six conjunctions remain
a separate dependency-architecture problem.

Classification artifact SHA-256 is
`2bd5cbea6702a8714928a69b30fba02c054bf7229e141568540f1964716b9029`.
Replay is byte-identical; there were zero model, embedding and cache calls. No
intervention or adoption follows.


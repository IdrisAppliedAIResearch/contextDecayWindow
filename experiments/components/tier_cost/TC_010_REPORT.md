# TC-010 relevance-qualified bottom spread — report

**Status:** `NO_SPLIT_SELECTED`; registered offline availability  
**Design commit:** `0225d8c8`  
**Registration SHA-256:** `307b781e6aeda103446a1aa4c03d9650a431cfc88f7c2994291e23ba85b99388`  
**Preflight commit:** `cf52bfaf`  
**Outcome commit:** `e9246166`  
**Date:** 2026-08-23

## Result

Relevance-qualified bottom spread does not improve frozen CC80. At 16k it
diversifies enough to displace useful semantic evidence. At 32k its top-quarter
pool mostly contains candidates full-budget CC80 already retrieves, so it
collapses to nearly the same selected set and cannot add breadth.

| Budget | Arm | Combined | Targeted | Breadth |
|---:|---|---:|---:|---:|
| 16k | Full CC80 | **771** | **666** | **17** |
| 16k | Qualified bottom 50/50 | 752 | 653 | 13 |
| 16k | Prior CC80+A3 50/50 | 757 | 653 | 14 |
| 16k | Literal global bottom 50/50 | 706 | 623 | 8 |
| 32k | Full CC80 | **819** | **689** | 24 |
| 32k | Qualified bottom 50/50 | 818 | 688 | 24 |
| 32k | Prior CC80+A3 50/50 | 818 | 686 | **27** |
| 32k | Literal global bottom 50/50 | 771 | 666 | 17 |

Against full CC80, qualified bottom has 12 gains and 31 losses at 16k
(net -19), including breadth 0/4 and targeted 7/20. Every conversation net is
negative. At 32k it has zero gains and one targeted loss; breadth identities
are exactly unchanged. Neither registered budget cell passes, so the frozen
disposition is `NO_SPLIT_SELECTED` and full CC80 remains the fallback.

The literal bottom control is decisively worse. Qualified bottom beats it with
46 gains/0 losses at 16k and 47/0 at 32k; breadth is 5/0 and 7/0. Globally least
relevant candidates are not useful spread.

## Why

At 16k, full CC80 selects a median 52 candidates and qualified bottom selects
53, but their sets differ by median 32 identities. Qualified spread pulls in a
median 16 candidates that full CC80 would not fit. Those swaps add five and
lose eight breadth evidence identities. Least redundancy inside the top quarter
is active, but it is still a weaker value signal than CC80 rank.

At 32k, full CC80 and qualified bottom both select median 107 candidates. Their
selected sets are byte-identical by identity on 765/871 questions and have
median symmetric difference zero. The entire qualified pool is already inside
full CC80's selected set on 841/871 questions. Reordering those candidates
cannot add missing evidence; unused spread capacity returns a median 23
candidates to CC80.

The fixed 25% qualification therefore lands on opposite sides of the same
boundary:

- at 16k it reaches beyond what full CC80 fits and damages relevance;
- at 32k it stays inside what full CC80 fits and adds no new information.

Compared with prior A3, qualified bottom is five combined and one breadth
completion worse at 16k. At 32k combined ties, but qualified trades A3's three
extra breadth completions for two targeted completions. The new spread rule is
not a better 50/50 architecture.

## Integrity and boundary

Preflight froze 871 question contexts before outcome labels opened, reproduced
3,484 predecessor CC80/CC80+A3 payloads, checked 80,721 recurrence states and
used 2,236 cache hits with zero misses. There were zero embedding or LLM calls;
the sealed outcome used zero ranking or model calls.

This closes only the fixed top-25%, minimum-maximum-cosine, 50/50 route on these
used LoCoMo development conversations. It does not establish that every
relevance-qualified diversity rule fails and does not authorize post-result
pool/share tuning or reader answers.

The final repository suite is 2,248 passed.

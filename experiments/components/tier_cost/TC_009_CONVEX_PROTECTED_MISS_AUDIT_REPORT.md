# TC-009 convex plus protected-breadth miss audit — report

**Status:** `POSTHOC_DESCRIPTIVE`  
**Design commit:** `c5f87c49`  
**Preflight commit:** `c5b2bfca`  
**Date:** 2026-08-23

## Plain finding

The improvement over dense mostly came from the 80/20 dense/BM25 relevance
ranking, not from protected spread. The remaining failures split cleanly:

- direct questions miss because their one evidence carrier still ranks outside
  the context;
- breadth questions usually retrieve some evidence but fail to collect every
  carrier, especially when the carriers live in different sessions.

This is not primarily a “why”, date, or location wording problem. It is a
tail-ranking problem for direct lookup and a set-completion problem for breadth.

## Total misses

| Budget | Complete | Missed | Targeted | Other | Breadth | Zero evidence | Partial evidence |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 16k | 757/868 | **111** | 51 | 30 | 30 | 54 | 57 |
| 32k | 818/868 | **50** | 18 | 15 | 17 | 19 | 31 |

All 50 questions missed at 32k were already missed at 16k. Increasing the
budget rescued 61 questions and introduced zero new misses.

At 32k, all 18 targeted misses have zero evidence delivered. Conversely, all
15 `other` misses and 16 of 17 breadth misses are partial: the system found at
least one correct carrier, just not the whole required set. The same split is
already visible at 16k: all 51 targeted misses are zero-evidence, while 57 of
60 non-targeted misses are partial.

## Why CC80+A3 increased over dense

| Budget | Gains | Losses | Net | CC80-only association | A3-only | Both controls | Combination-only |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 16k | 20 | 12 | +8 | **17** | 2 | 1 | 0 |
| 32k | 9 | 1 | +8 | **6** | 1 | 2 | 0 |

“Association” asks which frozen control shares the treatment's complete result;
it is diagnostic, not causal. At both budgets no gain exists only in the
combination. Most gains are present in full-budget CC80 and absent in dense+A3.

The carrier ranks make the mechanism concrete. For gained questions, median
required-carrier rank changes from dense 67 to CC80 14 at 16k, while A3 stays
67. At 32k it changes from dense 130.5 to CC80 28, versus A3 103.5. The
treatment admits 25 of 27 gained carriers through initial CC80 relevance at
16k and 10 of 12 at 32k; protected spread admits only two at each budget.

So the +8 net at each budget is chiefly better semantic ordering. Protected A3
is useful as a guard at 32k—it repairs CC80's known breadth losses—but it is not
the source of most wins over dense.

## Common themes in what remains

Carrier structure is the strongest repeated pattern:

| Evidence structure | Population | 16k miss rate | 32k miss rate |
|---|---:|---:|---:|
| One carrier, one session | 704 | 51/704 = 7.2% | 18/704 = **2.6%** |
| Multiple carriers, one session | 38 | 9/38 = 23.7% | 6/38 = **15.8%** |
| Multiple sessions | 126 | 51/126 = 40.5% | 26/126 = **20.6%** |

At 32k, needing multiple sessions is about eight times as failure-prone as a
single-carrier lookup. Registered breadth remains the hardest population:
17/44 missed (38.6%), compared with 15/120 other (12.5%) and 18/704 targeted
(2.6%).

The LoCoMo strata agree. At 32k, category 3 multi-hop misses 13/42 (31.0%) and
category 1 single-hop misses 16/107 (15.0%), while category 2 temporal is 4/143
(2.8%) and category 4 open-domain is 12/386 (3.1%). The label and the carrier
structure are not independent, so this is characterization rather than a new
cause claim.

Question wording is a weaker moderator. Enumeration questions miss 8/98 at
32k (8.2%) and quantity questions 2/24 (8.3%), above the overall 5.8%, but far
below the multi-session rate. Temporal, location, and causal flags are not the
dominant residual. Persistent examples instead show two families:

- aggregation across the conversation: recipes Joanna made, people Maria met
  while volunteering, activities with church friends, James's pets' tricks,
  Deborah's gifts and activities;
- isolated tail facts: Maria's May dinner companion, Nate's visited state,
  Joanna's gaming-room lighting, James's board game, and Jolene's September
  location.

For the 50 persistent misses, the 142 required carriers have median ranks
dense 116, CC80 101, and A3 116.5. The treatment admits 49 through relevance
and 17 through spread but leaves **76 absent**. The issue is therefore not that
spread never contributes; it contributes 17 carriers, but it does not reliably
complete the required set.

## Boundary and artifacts

This is evidence availability on four already-used LoCoMo development
conversations. The text flags overlap, control associations are not causal, and
no answer model was run. It cannot select a new share or architecture.

- Full question audit: `artifacts/tc009_convex_protected_miss_audit/result/questions.csv`
- Per-carrier ranks and phases: `artifacts/tc009_convex_protected_miss_audit/result/evidence_detail.csv`
- Aggregate result: `artifacts/tc009_convex_protected_miss_audit/result/result.json`
- Preflight: `artifacts/tc009_convex_protected_miss_audit/preflight/preflight.json`

Preflight reproduced all 24 parent summaries, verified 868 unique question
joins and the four frozen input hashes, and made zero embedding or LLM calls.
The audit also made zero ranking, embedding or LLM calls.
The final repository suite is 2,246 passed.

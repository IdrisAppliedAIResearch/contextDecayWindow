# DR-002 Candidate-Pool Prior Diagnostic

**Decision rule commit:** `fd53591f`
**Frozen configuration:** A3, `lambda = 0.1`, `r = 0.0`, `k = 16`, budget 32,000,
same store, same renderer, same carried embedding model
**Verdict:** **COSINE ORDERING IS THE WRONG PRIOR**

## 1. Read-out: the frozen configuration across pools

Not a prospective test. See the contamination disclosure in
`../../E005_DR_002_pool_prior_diagnostic.md`.

| Pool | Cand. | Q11 | Dom | civil | art | mon | marine | Chars | Eps | Oracle | Targeted |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| full eligible store | 119 | **12/17** | **4/4** | 5 | 2 | 1 | 4 | 31,569 | 15 | 4/5 | 16/16 |
| cosine top-100 | 100 | 9/17 | 3/4 | 5 | 0 | 1 | 3 | 31,950 | 11 | 0/5 | - |
| deployed N-cap union K | 34 | 5/17 | 2/4 | 4 | 0 | 1 | 0 | 31,250 | 12 | 1/5 | - |

Widening the pool from the deployed 34 to the full 119, with everything else
frozen, moves the same configuration from **5/17 across 2/4 domains to 12/17
across 4/4 domains**, and oracle overlap from 1/5 to 4/5. The pool is binding on
both axes, facts and domains, not one.

**Brittleness worth recording:** dropping only the 19 lowest-cosine episodes to
form the top-100 pool costs three facts, the entire art domain, and *all* oracle
overlap - even though four of the five oracle episodes are still inside that
pool. A3's cluster structure is computed over the pool, so removing tail
episodes reshuffles the objective rather than merely removing options. The
objective is sensitive to pool composition in a way the pool size alone does not
predict.

## 2. Registered test: cosine ranks of the winning selections

Pool 119, in selection order. Rank is over all 119 eligible episodes by Q11
cosine.

| Step | Turn | Rank/119 | Cosine | Chars | Q11 items contributed |
|---:|---:|---:|---:|---:|---|
| 1 | 114 | 1 | 0.5371 | 768 | - |
| 2 | 43 | 4 | 0.4009 | 4,217 | - |
| 3 | 1 | 2 | 0.4973 | 897 | - |
| 4 | 2 | 3 | 0.4930 | 364 | - |
| 5 | 78 | 9 | 0.3032 | 4,170 | - |
| 6 | 110 | 10 | 0.2999 | 4,472 | marine x3 |
| 7 | 27 | 11 | 0.2851 | 3,000 | civil x2 |
| 8 | 3 | 5 | 0.3767 | 593 | civil x3 |
| 9 | 54 | 6 | 0.3652 | 4,425 | - |
| 10 | 84 | 7 | 0.3490 | 5,473 | monetary x1 |
| 11 | 118 | 21 | 0.2231 | 773 | marine x4 |
| 12 | 113 | 14 | 0.2640 | 358 | civil x3 |
| 13 | 115 | **50** | 0.1546 | 597 | **art x1** |
| 14 | 112 | 22 | 0.2227 | 417 | civil x3 |
| 15 | 116 | **86** | 0.1088 | 994 | **art x2** |

- Fact-bearing selections: **9 of 15**. Their ranks: 5, 7, 10, 11, 14, 21, 22,
  **50**, **86**.
- **Worst fact-bearing rank: 86.**
- Fact-bearing selections beyond the deployed cap of 34: **2**.
- **The four highest-cosine episodes in the store contribute zero Q11 facts.**
  Ranks 1, 2, 3 and 4 are all factually empty for this probe.
- **Both art contributors sit in the tail**, at ranks 50 and 86. Art has no
  representative anywhere in the top 34, which is exactly why the deployed pool
  returns art 0/4 and cannot reach four domains at any setting.

Registered rule: *any fact-bearing selection at cosine rank 80 or worse means
cosine ordering is the wrong prior for breadth.* Rank 86 is fact-bearing and
carries two of the four art items. **The rule fires.**

The failure is not that the ordering is noisy. It is anti-correlated at the top:
the most query-similar episodes are the least informative, and one of the two
domains that decides the surrogate gate is reachable only past rank 50.

### 2.1 Oracle reachability - post-hoc lens, pre-committed threshold

The rank threshold that decides this diagnostic was committed at `fd53591f`
before any rank was computed. The oracle-reachability reading below is applied
afterwards and is interpretation, not a registered test.

One prediction available before the ranks were opened was that A3 would
concentrate in the top ~30, finding the shallow oracle episodes and missing the
deep ones, which would make cosine a soft prior the selector mostly obeys.

**That is not what happened.** AR-001's five oracle episodes sit at ranks 14, 21,
22, 86 and 112. A3 recovered **14, 21, 22 and 86** - including the deep one - and
missed only rank **112**, the deepest.

So A3 does reach past the prior when its objective rewards doing so; the
objective partially compensates for a bad ordering. What it did not reach is the
single deepest episode, turn 90, which carries four monetary items. That is
precisely why monetary is A3's weakest domain at 1/4 while every other domain is
at or near complete.

The refined reading: **cosine ordering is actively wrong rather than merely
weak, and a set-level objective can climb out of it partway but not all the
way.** Both conclusions point at pool construction, and the second one bounds how
much of the gap a better selector alone could recover.

## 3. CC-001 wall clock and scaling

Selection cost only. Query and episode vectors are already resident, so
embedding is excluded throughout. Median of 25 timed runs per point.

**Correction to the first measurement.** An initial run reported 1.28 ms at
pool 119 against 0.45 ms at pool 34. Those figures timed the **greedy loop
only** - cluster construction was built outside the timed region. The
decomposition below reproduces them exactly in the `greedy` column and shows
that clustering, not the greedy loop, is the dominant term. Total per-selection
cost at pool 119 is **4.76 ms, not 1.28 ms.**

| Cand. | Cluster setup | Greedy loop | **Total** | us/cand | Steps | us/cand/step |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 0.559 ms | 0.302 ms | **0.862 ms** | 43.07 | 11 | 1.373 |
| 34 | 0.802 ms | 0.468 ms | **1.269 ms** | 37.33 | 14 | 0.982 |
| 50 | 1.190 ms | 0.582 ms | **1.772 ms** | 35.44 | 12 | 0.970 |
| 75 | 2.278 ms | 0.800 ms | **3.078 ms** | 41.05 | 12 | 0.889 |
| 100 | 2.920 ms | 1.003 ms | **3.923 ms** | 39.23 | 11 | 0.912 |
| 119 | 3.483 ms | 1.273 ms | **4.756 ms** | 39.96 | 15 | 0.713 |

**Per-candidate cost is flat at 35-43 microseconds across a 6x range in pool
size.** Total grew 5.52x for 5.95x the candidates, an empirical exponent of
**0.96 - linear.** Clustering accounts for roughly 73% of the total at n = 119.

The `us/cand/step` column separates the two effects: it falls from 1.37 to 0.71
as the pool grows, because the greedy loop length is set by the character
budget, not by pool size. More candidates cost more per pass but do not buy more
passes.

**Projection for CC-001, with its limit stated.** At a flat ~40 us per candidate
the A3 path projects to roughly **40 ms at 1,000 candidates and 400 ms at
10,000**, assuming Lloyd iteration counts stay bounded, which is not established
beyond n = 119 and should be re-measured before being relied on.

**The scaling wall is not on the A3 path.** A3 uses query relevance plus cluster
assignments and never materializes the pairwise similarity matrix. A1 and A2 do.
That matrix is measured here at 0.291 ms for n = 119 and is O(n^2) in both time
and memory: naively extrapolated it is about 2 seconds and roughly 800 MB of
float64 at n = 10,000. **If a coverage selector is deployed at scale it should be
A3-shaped, or A1/A2 need a blocked or approximate similarity structure.** That is
a CC-001 design input, not a result of this diagnostic.

No threshold was registered and none is applied. At this store size the
pre-filter buys 3.49 ms and costs two domains.

## 3.5 Generality check - the bad prior is query-type-specific

Added because the rank-86 result invites a stronger reading than it supports:
that every mechanism in this program ran downstream of a broken candidate
ordering. **Measured, that reading is false.**

Same store, same embedder, same eligibility rule. For each probe, the cosine
rank at which the *last* still-needed target item first appears:

| Probe | Turn | Top-4 carry a target item | First hit | **Last needed item** |
|---|---:|---:|---:|---:|
| Q1 | 112 | 4/4 | 1 | **2** |
| Q2 | 113 | 3/4 | 2 | **2** |
| Q4 | 115 | 3/4 | 1 | **2** |
| Q5 | 116 | 1/4 | 1 | **1** |
| Q6 | 117 | 1/4 | 1 | **1** |
| Q7 | 118 | 3/4 | 1 | **1** |
| Q8 | 119 | 2/4 | 2 | **2** |
| Q10 | 118 | 2/4 | 1 | **1** |
| **Q11** | **120** | **0/4** | **5** | **87** |

On every targeted probe cosine ordering places **every needed item inside rank
2**. It is not merely adequate there, it is near-optimal, which is why targeted
recall runs at 60/60 and why all 137 no-regression-passing E005 configurations
preserve 16/16 without effort.

Q11 is the only probe where the ordering fails, and it is the only enumeration
probe. This is a sharper, quantified form of what the ledger already records:
**K-collapse is query-type-specific, not a scale failure.**

The defensible claim is therefore narrow: *mechanisms aimed at breadth ran
downstream of a candidate ordering that is anti-correlated at the top for
enumeration queries.* It unifies the F1 failures. It does not explain
formation-side failures, which ran at write time upstream of any retrieval
filter; it does not explain Study 003's promotion route, which was
arithmetically unreachable; it does not explain Study 007, where the model used
all 10 delivered facts and seven required facts were absent from the store; and
it is contradicted by bakeoff Tier 3, whose routing *oracle* assumed perfect
selection and still ceilinged at 6.09%, and by widened raw STM, which delivered
6/6 formation-blind facts with no selection filter at all.

## 4. Boundary

One probe, one store, one frozen configuration. Availability and cost only.
Timings are measured from 20 to 119 episodes on one machine and are single-run
medians, not a benchmark; the linear fit is supported only over that range. No
answer-correctness claim, no general breadth claim, no live run authorized.

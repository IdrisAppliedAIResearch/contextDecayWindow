# DX-001 Part 2 - Disposition

**Status:** CLOSED - **NO CHANGE.** F.6 fires.
**Registration:** `a30d3bcca53248fe75b7901c2ff74a8aa28f5e1a`
**Part 1 attribution:** `0620c459` - M2+M3+M4, M1 refuted
**Evidence:** `artifacts/dx001/DX_001_report.md`, `artifacts/dx001/dx001_results.json`

Part 2 was conditional on Part 1 naming a mechanism that a fix could act on.
Part 1 named three, and none of them is actionable inside E005. No parameter
was changed, no arm was re-run, and no committed E005 result was re-scored.

## 1. Why no branch was taken

The binding rule registered at F.1 is that a fix must be justified by a reason
that would have applied without knowing turn 90 exists. That rule is not the
obstacle here. The obstacle is stronger: **no setting in the registered space
recovers the episode at all**, so there is nothing to justify.

| Branch | Mechanism | Fires | Why it is not taken |
|---|---|---|---|
| A | M1 cluster collision | **No** | Refuted. Turn 90's k=16 cluster (20 members) is never occupied by any selection, so the diversity term was payable in full at all 15 greedy steps. It still lost by 0.169. Changing k has no defect to repair, and a principled derivation of k - legitimate on its own terms per F.2 - would not touch this miss |
| B | M2 cost discount | Yes | `r` moves the target's best rank from 16 to 8 to 4 as it goes 0 to 0.5 to 1.0, so cost normalization is the only lever that moves it materially. It never reaches rank 1 in any of 132 A3 walks, and 0 of 146 configurations select it. A lever that cannot reach the outcome is not a fix |
| C | M3 relevance floor | Yes | **Escalate, do not implement** (F.4). This is the decisive mechanism and it is an objective change, not a parameter change |
| D | M4 budget exhaustion | Yes | Converges with B per F.5. The run terminated on budget with 431 characters left and 104 unselected candidates, the cheapest costing 1,439. A marginal-gain termination rule would stop the selector *earlier*; it subtracts episodes rather than adding this one |

## 2. The decisive finding

To win at its best step turn 90 needed a query cosine of **0.225**. It has
**0.056**. Twenty of the 119 episodes clear that bar; the episode would have to
be a *different episode by cosine*, not a better-weighted one.

This is why B and D cannot work. Both re-weight or re-time a competition that
turn 90 loses on the relevance term by a factor of four. The diversity term at
its registered maximum, `lambda = 1.0`, adds 1.0 and still leaves it at rank 4
rather than rank 1 - and that configuration is not gate-passing for other
reasons.

**The miss is not a pool problem.** DR-002 established that the candidate pool
is binding for domains and facts, and it is - widening 34 to 119 moved the same
configuration from 5/17 at 2/4 domains to 12/17 at 4/4. Turn 90 is *inside* the
119. Pool construction, however well done, does not recover it. The two findings
are complementary, not competing: the pool decides what can be seen, the
objective decides what is worth taking, and each has now been shown to bind on a
different part of the gap.

## 3. F.6 conditions, as measured

| Condition | Fires |
|---|---|
| Part 1 cannot distinguish mechanisms | No - attribution is M2+M3+M4 with M1 refuted |
| The only recovering configurations lose art, a targeted item, or total facts | Vacuous - there are no recovering configurations |
| The required justification cannot be stated without reference to turn 90 | **Yes** |
| Branch C is reached | **Yes** |

Two conditions fire. F.6 is satisfied and its instruction is followed.

## 4. What ships

`A3_l0.1_r0.0_k16` at the full 119-episode pool, unchanged:

- **12/17 Q11 items across 4/4 domains**
- **16/16 targeted items preserved**
- 31,569 of 32,000 serialized characters, 15 episodes
- 4 of the oracle's 5 episodes

**Characterized limitation, recorded rather than repaired:** turn 90, monetary
domain, 4 items, cosine rank 112 of 119, serialized cost 2,862 characters. It is
the entire remaining gap to the oracle's 15/17 and the reason monetary sits at
1/4. Its exclusion is now explained, reproducible, and bounded: no configuration
in the registered space selects it, and the shortfall is 0.169 of cosine
relevance at the deciding step.

A documented limitation with an identified cause is a shippable state. A
parameter tuned to a single test case is not.

## 5. F.7 acceptance bars

No fix was implemented, so **no bar is claimed as passed**. Recording them as
"passed" against an unchanged configuration would be exactly the kind of
surrogate this program guards against: the bars certify that a change is safe,
and there is no change.

| Bar | Status |
|---|---|
| B1 Targeted 16/16 | Not claimed - unchanged from E005 |
| B2 Domains 4/4 | Not claimed - unchanged from E005 |
| B3 Q11 >= 12/17 | Not claimed - unchanged from E005 |
| B4 Budget <= 32,000 | Not claimed - unchanged from E005 |
| B5 Justification | **Cannot be satisfied.** No mechanism-based change reaches the outcome |
| B6 Latency | Unchanged; DR-002's ~40 us/candidate envelope stands |
| B7 No re-run of a locked artifact | **Honoured.** The diagnostic reproduced 146 of 146 committed payload hashes and changed none |

## 6. Registered predictions, settled

F.8 was committed before Part 1 ran so it could be wrong on the record. It was,
in the most useful way.

| Prediction | Outcome |
|---|---|
| Most likely mechanism M1, with M3 contributing | **Wrong.** M1 does not fire at all; M3 is decisive |
| No configuration selected turn 90 (~65% confidence) | **Held.** 0 of 146 |
| Outcome 13/17 | **Wrong.** No change; 12/17 stands |
| ~30% probability F.6 fires and the answer is no change | **Fired** |

The M1 prediction was reasonable and specific - k=16 over a four-domain store
does give roughly four clusters per domain - and it is wrong for an
informative reason. Turn 90's cluster is not merely unoccupied by a competitor;
it is a 20-episode cluster that **no selection ever enters**. The diversity term
was offering full credit for it at every step and no episode in that cluster was
relevant enough to collect.

## 7. Escalation: E006, proposed and unauthorized

Branch C's remedy is a new objective, which per F.4 is a new ledger entry with
its own scan, kill condition and arm set. **This document proposes it and does
not authorize it.**

What such a study would have to change: the relevance term. Query-episode cosine
is the term turn 90 fails, and DR-002 already established that on this probe the
ordering is anti-correlated at the top - the four highest-cosine episodes carry
zero Q11 items. An objective that could take turn 90 would have to score an
episode by something other than similarity to the query: information density per
serialized character, coverage of an answer space rather than of an embedding
space, or an explicit enumeration mode. Each of those is a distinct study, and
each carries the same hazard this diagnostic was built around - the desired
answer is known in advance.

Two constraints any such design inherits:

1. **The bound is small.** DR-002 measured how much a better selector alone can
   recover, and the answer was "partway." A3 already reaches four of five oracle
   episodes including one at rank 86.
2. **Availability is not correctness.** Everything in E005, DR-002 and DX-001 is
   offline availability. The prior-answer hazard is untouched and no live run is
   authorized.

## 8. Reproduction hazard found in passing - a CC-001 input

The Part 1 replay gate failed on its first attempt. The cause was not the
mechanism: the Q11 query had been embedded on its own rather than in E005's
committed nine-query batch, and the carried embedder returns a measurably
different vector for it - cosine agreement 0.999837, largest component
difference 0.217 - which flips 6 of 146 committed payloads.

The primary configuration is not among the six, so no E005 or DR-002 conclusion
moves. One published number does: DR-002's step-11 cosine rank for turn 118 is
corrected from 21 to 20. Recorded in `ERRATA.md` with the re-measurement in
`artifacts/e005/dr_002/generality_batched.json`, which reproduces all nine rows
of the DR-002 generality table exactly.

The transferable lesson is a component contract item: **reproducing a retrieval
result requires reproducing the embedding call shape, not only the query text.**
A replay harness that re-embeds one query at a time will not reproduce a system
that embedded them in batches, and the difference is large enough to change
selections.

## Boundary

One episode, one probe, one store, availability only. No answer-correctness
claim. No live run is authorized by this diagnostic or by its disposition.

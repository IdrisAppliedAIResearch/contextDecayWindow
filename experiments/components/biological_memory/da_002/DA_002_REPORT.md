# DA-002 Linked-Context Mechanism Decomposition Report

**Status:** `CUE_TRANSFER_WITH_BUDGET_DISPLACEMENT`
**Standing:** post-outcome descriptive reanalysis on spent NF-004 LoCoMo
**Protocol commit:** `d6ee1f93`
**Blind-provenance commit:** `727ceb06`
**Population:** 1,098 primary questions; 11 fixed DA-001 arms
**Calls:** 0 embedding, 0 model, 0 cache misses
**Date:** August 29, 2026

## Mechanism

DA-001's gains are rank transfer. A query retrieves a highly ranked pair, and
that pair acts as a seed which inserts its immediate predecessor or successor
ahead of the neighbor's own cosine position. The neighbor then carries the
missing evidence into the exact 16k pack.

For temporal expansion, gained evidence has median direct cosine rank
117/117/120/112.5/113 at `m=1/2/4/8/16`, while its emitting seed has median
rank 1/1/1/2/4. The evidence sits a median 60/54/51/43.5/43.5 ranks beyond the
number of candidates selected by `DIRECT`. Median seed-minus-evidence cosine
is .27/.24/.21/.17/.16. This is not a marginal reorder near the pack boundary:
a strong direct cue is carrying much weaker evidence past dozens of candidates.

The relation is directionally ordinary. At `m=1`, seven gain carriers are
previous pairs and ten are next pairs; across depth, neither direction
dominates. The signal is local association, not a predecessor-only or
successor-only rule.

## Cost

The losses are byte-budget displacement. At `m=1`, the two lost evidence
carriers sit at median percentile .98 of their original direct packs. At
`m=2` and `m=4`, the loss frontier remains at .97 and .96. Shallow expansion
therefore removes evidence that was already barely fitting.

As more links are admitted, the frontier moves inward. At temporal `m=16`, the
median lost carrier is at percentile .86. Full-event expansion is much more
aggressive: its median loss frontier moves from .91 at `m=1`, to .61 at `m=4`,
and .41 at `m=8`. The architecture is not confusing relevant with irrelevant
content at selection time; it is spending enough budget on associated content
to evict increasingly central direct evidence.

## Local Versus Event

Immediate temporal links capture most of the useful event signal at far lower
cost. At `m=1`, all 17 temporal gains are also event gains. Full-event traversal
adds four gains, but also 15 losses not caused by temporal traversal. At `m=4`,
it adds 17 event-only gains and 56 event-only losses. At `m=16`, it adds 13 and
120 respectively.

The extra event-only gains are not generally very deep: their median graph
distance is 3 to 3.5. Nevertheless, importing every path member needed to
reach them is expensive. This explains DA-001's shape: linked locality carries
the benefit; unconditional event closure carries the regression.

| Depth | Temporal gain/loss | Event gain/loss | Event-only gains | Event-only losses |
|---:|---:|---:|---:|---:|
| 1 | 17 / 2 | 21 / 17 | 4 | 15 |
| 2 | 21 / 5 | 32 / 28 | 11 | 23 |
| 4 | 27 / 6 | 44 / 61 | 17 | 56 |
| 8 | 38 / 14 | 50 / 127 | 17 | 116 |
| 16 | 51 / 23 | 49 / 139 | 13 | 120 |

## Trajectories

Temporal behavior is stable once it appears. Of 1,098 items, 1,022 always tie,
51 enter a persistent gain state, 23 enter a persistent loss state, and only
two losses later recover. No temporal gain later reverts. This means the rising
aggregate is mostly additional reachable items appearing as seed depth grows,
not the same items repeatedly changing sides.

Event behavior is substantially less stable: 49 persistent gains, 138
persistent losses, three gains that revert, 11 losses that recover, one item
with multiple loss/tie reversals, and 896 always tied. Deeper traversal changes
large portions of the pack rather than adding a controlled local supplement.

## Why Conversation 44 Reverses

Conversation 44 exhibits the same mechanism, but its opportunity/cost balance
is unfavorable. At temporal `m=1`, its sole gain is a 165-character next pair
at direct rank 198, emitted by the rank-1 seed and inserted at selected position
3. It was 126 ranks beyond the direct selected count: a clear cue-transfer
rescue.

The same arm loses two complete items. Their evidence was at direct ranks 57
and 66, but at the .983 and .971 selected percentiles: both were at the pack's
tail and were displaced by only 433-487 linked characters. Thus conversation
44 does not refute the link mechanism. It has one reachable rescue and two
fragile direct deliveries at the first depth; by `m=16` it has one gain and
eight losses. The other five conversations pool to 16 gains and no losses at
`m=1`.

## Architectural Reading

The useful primitive is not a linked list that should be traversed wholesale.
It is an addressable evidence unit with a cheap, typed local edge. Retrieval
can use a strong fact as a cue for weakly query-matching derivative context,
but expansion must remain budget-accounted because every edge admission has an
opportunity cost.

This supports four descriptive design properties:

1. preserve atomic units so facts remain directly rankable;
2. retain typed local provenance links between related units;
3. let a retrieved unit nominate nearby context without inheriting a whole event;
4. charge linked material against the same exact packing budget before rendering.

It does not identify an evidence-blind gate for when to follow an edge. The
earlier NF-004 anatomy analysis found no stable selector, and this reanalysis
uses the same spent corpus. Adjacency is also only a provenance relation, not
proof of semantic dependence or reader value.

## Open Ceiling and Gating Questions

The temporal net curve is monotonic over the measured sweep, but it is not
linear in seed count. Net gains at `m=1/2/4/8/16` are +15/+16/+21/+24/+28.
Because each step doubles the number of eligible direct seeds, the marginal
net return per newly enabled seed is 15, 1, 2.5, .75, and .5 respectively.
This is diminishing return, not evidence of an unbounded linear trend.

The ceiling was not measured. At `m=16`, new reachable rescues still exceed
new displacement losses, so the observed sweep ends before the crossover.
The natural descriptive ceiling is where the next seeds expose no additional
missing evidence, or where their rescues are balanced by the direct evidence
their linked bytes displace. Locating that crossover on this spent corpus
would be diagnostic only and could not select a production depth.

The 16k evidence budget remains fixed. Increasing `m` does not enlarge the
context window: it changes its composition. More linked bytes enter, while
lower-priority direct candidates leave. Incremental gains arise because newly
eligible seeds reveal previously unreachable adjacent evidence; incremental
losses arise because those admissions consume the same fixed budget. The open
architectural problem is an evidence-blind rule that can estimate this local
rescue-versus-displacement trade before evidence labels or outcomes are known.

## Integrity

Blind provenance reproduced all 12,144 selected identity digests and replayed
byte-identically before evidence was joined. The joined analysis reproduced
DA-001's complete gain/loss matrix and NF-004's 935 direct complete deliveries
over all 1,098 primary items. No embedding or model call was made.

The result summary SHA-256 is
`220a125f1660178987b1dd00323b07f6c53311648b8e13c117e7561bfa51fd29`;
the item-mechanism artifact SHA-256 is
`fb6d92fb413c96ea433c2d2de4437b849b0be22c9344d2c4bb274e3b5eb8ac5d`.

This is a mechanism explanation, not a new outcome test. It authorizes no
selector, tuned depth, reader claim, implementation change, or adoption.

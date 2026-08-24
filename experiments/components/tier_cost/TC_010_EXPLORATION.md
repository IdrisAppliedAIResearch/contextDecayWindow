# TC-010 qualified bottom-spread exploration

**Type:** Preflight Part 1; label-blind  
**Date:** 2026-08-23  
**Population:** 871 unique LoCoMo development questions

## Behavioral identity

The proposed route first gives frozen CC80 relevance half the character budget.
Spread then considers only the top `ceil(25%)` of that same CC80 order and
greedily chooses the candidate with the lowest maximum pairwise embedding
cosine to anything already selected. Ties prefer better CC80 rank. Spread may
spend at most the other half; unused capacity returns to CC80.

“Bottom” therefore means bottom redundancy inside a relevance-qualified pool.
It does not mean bottom query relevance. The negative control literally
reverses the complete CC80 order.

## Real-trace behavior

Run against the hash-locked blind manifest and vector cache: 2,236 cache hits,
zero misses, zero embedding calls and zero LLM calls.

| Budget/arm | Initial CC80 median | Spread median | Returned CC80 median | Total median | Spread CC80-rank median | Sessions median |
|---|---:|---:|---:|---:|---:|---:|
| 16k qualified | 25 | 26 | 1 | 53 | 59 | 23 |
| 16k global bottom | 25 | 24 | 1 | 50 | 330 | 24 |
| 32k qualified | 52 | 33 | 23 | 107 | 69 | 29 |
| 32k global bottom | 52 | 47 | 1 | 102 | 317 | 29 |

Every route admits nonempty spread on 871/871 questions. Qualified candidates
remaining after initial relevance range 43–71 at 16k (median 60) and 12–51 at
32k (median 33). At 32k the qualified pool is usually exhausted before the
spread allowance, so median 23 candidates return through relevance. This is
the allocator's registered relevance-only slack return, not a final 50/50
composition guarantee.

Qualified spread candidates stay within CC80 ranks 20–89 at 16k and 39–89 at
32k. Global-bottom admissions reach rank 355 and have medians 330/317. Thus the
control is genuinely anti-relevant and the treatment never becomes global
bottom retrieval.

The qualified greedy recurrence's chosen maximum redundancy spans
`.458–.964` at 16k and `.499–.964` at 32k, with medians `.762/.772`. The
mechanism is active rather than tied or constant. Its absorbing state is pool
exhaustion: after every qualified candidate has been ordered, spread cannot
admit outside the top quarter and only CC80 slack return can continue. This
state occurs on all 871 complete ordering traces and is budget-visible at 32k.

Session count is not used as an objective or endpoint. The treatment's 23/29
median represented sessions shows that least redundancy is not a disguised
session floor and does not certify evidence breadth.

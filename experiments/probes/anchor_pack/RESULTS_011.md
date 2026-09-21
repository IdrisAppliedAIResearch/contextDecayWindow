# AF-PRE-011 RESULTS — what retrieval looks like when an anchor builds the pack

Plan `23684595`, geometry preflight `2466c6dc`. Zero model calls, zero reader calls: packs are built
from turn sets and measured for annotated-evidence availability at matched character budgets.
Positive control passed (`ORACLE_EVIDENCE` delivered its own turn set on 585/585 feasible
arm×budget rows).

## any / all annotated evidence delivered, of 120 items (median pack size in chars)

| arm | 500 | 1,000 | 2,000 | 4,000 | 8,000 |
|---|---|---|---|---|---|
| `BM25` broad (control) | 48 / 40 | 57 / 47 | 63 / 53 | 78 / 67 | 87 / 75 |
| `ANCHOR` (ckpt2 top-1 alone, **163 ch**) | 66 / 51 | 66 / 51 | 66 / 51 | 66 / 51 | 66 / 51 |
| `ANCHOR_W2` (±2 of anchor, 724 ch) | 9 / 9 ¹ | 67 / 52 | 78 / 60 | 78 / 60 | 78 / 60 |
| `ANCHOR_W4` (±4, 1253 ch) | 0 / 0 ¹ | 11 / 10 | 82 / 63 | 82 / 63 | 82 / 63 |
| `ANCHOR_FILL` (anchor ±1 then BM25, full budget) | 51 / 41 | 76 / 60 | 83 / 68 | 87 / 73 | 93 / 79 |
| `ORACLE_W2` (**gold**±2, 691 ch) | 24 / 21 ¹ | 109 / 83 | 120 / 92 | 120 / 92 | 120 / 92 |
| `ORACLE_EVIDENCE` (evidence only, 190 ch) | 107 / 107 | 119 / 119 | 119 / 119 | 120 / 120 | 120 / 120 |

¹ feasibility, not failure: a ±2 window does not fit 500 chars on 99/120 items (only 21 items are
feasible in both arms), so those cells are not comparable — the budget, not the mechanism, excluded
them.

## The two results

**1. The anchor turn alone is the most character-efficient pack found.** 163 characters deliver
annotated evidence on **66/120** items — BM25 needs **more than 2,000 characters** (12× the context)
to reach the same any-evidence count, and 2,000 is where it is still behind (63). Complete evidence
is roughly a tie at 2,000 (51 vs 53). One correctly chosen turn out-delivers a page of
query-similarity retrieval, because in LoCoMo the answer-bearing mention is a single turn:
`ORACLE_EVIDENCE` costs a **median 190 characters** and delivers complete evidence on 119/120 at
500.

**2. Anchor geometry beats broad retrieval only in the tight regime, and the crossover is real.**
Paired on items feasible in both arms, Δ complete-evidence (`ANCHOR_W2` − `BM25`):
**+4 at 500, +12 at 1,000, +7 at 2,000, −7 at 4,000, −15 at 8,000** → registered disposition
**ANCHOR_GEOMETRY_CARRIES** (fired on +12 at 1,000, n = 106). Above ~4,000 characters, buying more
turns by similarity beats buying locality around one turn — which is AF-PRE-010's result seen from
the other side: at a generous budget the anchor is irrelevant, and it is generous, not small, that
makes it so.

The crossover the previous probe asked for: reaching **70/120** any-evidence costs
**BM25 4,000 chars**, `ANCHOR_W2` **2,000**, `ANCHOR_FILL` **1,000**.

## The result that matters more than the registered one

`ANCHOR_FILL` (anchor ±1 first, then fill by BM25) **never loses**: paired against BM25-only it is
15 gains / 2 losses at 1,000, 16/1 at 2,000, 6/0 at 4,000, 4/0 at 8,000 (exact McNemar
p = .0023 / .0003 / .031 / .125 — descriptive, not a registered statistic). Seeding the pack with the
anchor and letting similarity fill the rest dominates pure similarity packing at every budget in
this set. That is a *composition* result, and it survives the regime where anchor geometry alone
loses.

**Anchor choice vs anchor geometry, separated.** `ORACLE_W2` costs 691 chars and delivers
any-evidence on **120/120** with complete evidence on 92 (the geometry ceiling PF4 predicted, since
28 items' evidence spans a median 30,630 chars). The reranker's own `ANCHOR_W2` at the same size
gets 78/60. Restricted to the 64 AF-PRE-009 misses, at 1,000 chars: the reranker's window delivers
complete evidence on **8**, a gold-centered window on **39**. So the headroom is not in widening
windows — it is 31 items of *anchor selection*, and it dwarfs anything the geometry or the budget
changes.

## Limits and things that could mislead

- **Inherited correctness.** `ANCHOR` arms deliver complete evidence on 51/56 hits but 0–15/64
  misses: most of the anchor's delivery value is items the reranker already got right. The oracle
  rows exist to keep that visible; the anchor-arm numbers are not a claim about selection quality.
- **Feasibility asymmetry at 500 chars** (21/120 comparable) makes the 500-char cells weak; the
  registered disposition was decided at 1,000 (106 comparable). Windows are never truncated — a
  pack that doesn't fit is infeasible, counted, and excluded from its own denominator.
- **The broad baseline is BM25**, not the cosine pair-rank the product uses; crossover budgets are
  indicative. Committed cosine reference points sit at 16k/32k (NF-004), an order of magnitude
  above the regime where the anchor wins.
- **Availability, not correctness.** Delivery is not answerability: answer-bearing delivery at 2,000
  chars tops out at 43 for `ANCHOR_FILL` and 53 even for `ORACLE_EVIDENCE`, consistent with
  AF-PRE-009's finding that 32 items have no turn containing the answer value. No reader ran, so no
  claim transfers to answer accuracy — and HH-004 warns that evidence ceilings may not transfer at
  all.
- ±k locality is an assumption; the arc's temporal-adjacency results (TA-001, DA-001) say it is
  corpus-specific. k was swept, not tuned to the winner.

**Next, if this is to become product work:** the cheap, high-headroom move is not a better packer,
it is a better anchor — the 31-item gap on the misses between the reranker's window and a
gold-centered one is where the delivery lives, and the successor should target anchor *selection*
at ≤1k-char packs and be measured on the same paired, matched-budget delivery criterion.

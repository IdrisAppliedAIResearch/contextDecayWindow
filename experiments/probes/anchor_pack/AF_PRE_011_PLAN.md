# AF-PRE-011 (registered before code runs, 2026-09-21): anchor-centered packs vs broad-budget packs

**Question.** AF-PRE-010 (`dd0e947e`) found that at the 32k budget the deployed pack already
contains the anchor turn on 61 of the 64 reranker misses — top-1 anchor selection buys nothing when
the context is that generous. The live question is the crossover: **at what context size does
building the pack around an anchor beat building it around query similarity?** This probe measures
delivery (evidence availability), not answer correctness.

**Hypotheses (both registered, neither assumed).** H1 — at small budgets, anchor-centered geometry
beats query-similarity packing, because one turn's local context is cheap and BM25 must buy
topical matches across the whole conversation. H2 — anchor geometry hits a hard ceiling on the 28
multi-evidence items whose evidence span is a median **30,630** chars (`2466c6dc`), so it can never
reach complete evidence on them at any small budget and broad packing wins there from above.

## Input (committed, read-only) and reused instruments

- `unified_anchor/artifacts/sample2.json` (frozen 120) and `miss_audit/artifacts/e5_subpartition.json`
  (`88669824`) for `pred` (the ckpt2 anchor), `gold`, `ev_ids`; reproduction of the 120/56 split is
  asserted before any arm runs.
- `arms.BM25` and `arms.load_conversations` — imported, not reimplemented (PF2).
- `ft_pipeline.eligible_all` evidence resolution — imported.
- Reference points, not rebuilt: NF-004 `P_PAIR_RANK` @16k/32k (cosine pair-rank delivery on 63 of
  these items) and the AF-PRE-010 D-product numbers. No embeddings, no model, no reader: **this
  probe makes zero inference calls of any kind.**

## Arms (pack = set of turns rendered chronologically; cost = rendered chars incl. `Speaker: `)

| arm | selection rule | status |
|---|---|---|
| `BM25` | turns ordered by BM25 score of the question, packed until budget | broad control |
| `ANCHOR` | only the ckpt2 top-1 turn | minimal anchor |
| `ANCHOR_W1` / `ANCHOR_W2` / `ANCHOR_W4` | contiguous turns `[a-k, a+k]` around the **ckpt2** anchor | anchor geometry |
| `ANCHOR_FILL` | anchor ±1 first, then BM25 order until the budget fills | composition |
| `ORACLE_W2` | window centered on the **gold** turn | upper bound, non-deployable |
| `ORACLE_EVIDENCE` | exactly the annotated evidence turns | delivery ceiling, non-deployable |

Budgets: **500 / 1,000 / 2,000 / 4,000 / 8,000 chars** (32k is excluded: AF-PRE-010 showed delivery
is automatic there). A fixed-order pack that exceeds its budget is **infeasible** for that item:
counted and excluded from the denominator, never truncated (truncation would silently change the
arm). All comparisons use the **matched-feasible** items — items feasible in both arms being
compared — so a difference can never come from a shrinking denominator.

## Measures (mechanical; same frozen rules as AF-PRE-009/010)

`any_evidence`, `all_evidence` (annotated evidence turns present), `answer_bearing` (frozen
answer-presence rule), mean chars used, feasible count. Reported over all 120, and separately for
the 56 hits / 64 misses because `ANCHOR` arms inherit the reranker's correctness by construction:
for the 56 hits the anchor *is* the gold, so a pooled anchor-arm win is partly inherited signal.
`ORACLE_W2` separates geometry from selection: if `ORACLE_W2` ≫ `ANCHOR_W2`, the loss is anchor
*choice*; if they are close, the loss is the geometry.

## Registered dispositions (fixed now, before any arm runs)

Δ(budget) = `all_evidence(ANCHOR_W2)` − `all_evidence(BM25)` on matched-feasible items.

- **ANCHOR_GEOMETRY_CARRIES** if Δ ≥ +10 items at ≥1 budget.
- **NO_GEOMETRY_BENEFIT** if Δ ≤ 0 at every budget.
- **MIXED** otherwise (reported with the margin, the budget, and the successor it justifies).

Also registered, as the number the question actually asks for: the **crossover budget** — the
smallest budget at which each of `BM25`, `ANCHOR_W2`, `ORACLE_W2` reaches 70/120 `any_evidence`
(PF4: `ANCHOR`'s own any-evidence ceiling is 90/120, so 70 is reachable for the anchor arms and
BM25's top-20 pool recall of gold is 72/120, so 70 is reachable for it too; both sides of the
comparison can exist).

## Preflight (`PREFLIGHT.md` §4)

- **PF1 inputs:** sample2 120 (`a237be71`), audit 120/56 asserted (`88669824`), LoCoMo 10
  conversations (1,527 eligible cat-1–4), `arms.BM25` imported. Geometry and char counts measured
  at `2466c6dc`: median turn 110 chars, p90 219, `turns_fitting` 4/8/16/32/65 at
  500/1k/2k/4k/8k, gold ±4 window covers all evidence on 92/120, multi-evidence span median 30,630.
- **PF2 mechanism identity:** the anchor is the committed ckpt2 top-1 (`pred`), the same object
  AF-PRE-009 audited; the broad order is `arms.BM25.score`, the arc's registered lexical scorer.
  Neither is re-simulated. `ORACLE_*` arms are labeled non-deployable and are never compared as
  product results.
- **PF3 gate ordering:** the 120/56 assertion and the infeasibility computation run before any
  arm-vs-arm difference is written; a failed assertion writes nothing.
- **PF4 reachability:** anchor geometry's `all_evidence` ceiling is 92/120 (28 items' spans exceed
  every registered budget) so NO_GEOMETRY_BENEFIT and ANCHOR_GEOMETRY_CARRIES are both possible;
  90/120 single-evidence items make `ANCHOR` non-degenerate; multi-evidence items make it capable
  of failing; crossover target 70/120 reachable on both sides.
- **PF5 comparison keys:** `sample_id:qa_index` throughout; packs are turn-id sets, so an arm's
  output is a set identity, not a count.
- **PF6 reproduction anchor:** the item/hit split must equal the audit's (120 items, 56 hits);
  `ORACLE_EVIDENCE` must score `all_evidence` = 120/120 by construction, which is the arm-builder's
  positive control — if it does not, the packer is broken and nothing is reported.
- **PF7 absorbing states:** n/a — no feedback loop, single pass.
- **PF8 adequacy:** detects whether an anchor-centered *set* contains the annotated evidence at a
  given char cost; cannot detect whether a reader could use it (NF-005/NF-006 dilution, HH-004
  ceiling-without-transfer), cannot detect rendering or ordering effects, and treats all evidence
  turns as equally needed.
- **PF9 surrogate audit:** `all_evidence` can be 1 while the item is unanswerable (missing
  derivation, AF-PRE-009 X1: 32 misses have the answer value in no turn), and 0 while a reader
  could still answer from a paraphrase. Both arms inherit the same annotation, so the comparison is
  fair between arms but is not a correctness measure. Residual recorded.
- **PF10 live evaluation:** delivery is availability, not a verdict. No reader runs here; nothing
  in this probe is a product or adoption claim, and the broad arm is BM25, not the cosine pair-rank
  the product ranks with, so crossover budgets are **indicative** and are reported beside the two
  committed cosine reference points (NF-004 @16k/32k).

## Limits (pre-stated)

Anchors come from ckpt2, which was trained on this dataset's split as registered in AF-PRE-005;
`ANCHOR` arms therefore also measure inherited correctness and are decomposed by hit/miss. Windows
assume the relevant context is contiguous in time — the arc's own temporal-adjacency results
(TA-001, DA-001) say that assumption is corpus-specific, so ±k is a parameter swept, not tuned to
the winner. No new training, no new annotation, no model calls, no reader calls.

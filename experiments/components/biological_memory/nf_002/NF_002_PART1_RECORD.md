# NF-002 Part 1 — Novelty Under a Binding Budget

**Status:** `PART 1 COMPLETE — NOTHING REGISTERED, NOTHING CLAIMED`
**Predecessor:** `../nf_001/NF_001_PART1_RECORD.md`
**Artifact:** `artifacts/part1_record.json`
**Corpus:** LongMemEval, 470 answerable items, committed EC-002 session ranking
**Model calls:** 0
**Date:** August 12, 2026

Nothing here is a result. `AGENTS.md` §9.4 is explicit that a reading applied to
a number already on the table is rescue, not research, so everything below
exists to set bars in a registration that does not yet exist.

## 1. Reproduction anchor

Reconstructing the session order from EC-002's committed ranking and joining it
to the dataset's `answer_session_ids` reproduces EC-002's
`evidence_session_ranks` **exactly on all 470 answerable items**. The 30 items
it does not reproduce are the `_abs` abstention stratum, which EC-002 also
excluded when it reported on 470.

## 2. The instrument NF-001 lacked

| | NF-001 | NF-002 |
|---|---|---|
| streams | 16 | 470 |
| candidates per stream | 32–35 | 38–62 |
| oversubscription | **1.0×** — everything fit | **14.5×** median |
| degenerate arm | `NEVER_STOP` was optimal | cannot fit; truncation is forced |

NF-001 stopped because taking everything cost nothing. Here the budget removes
about 93% of each stream, so a candidate taken displaces one not taken. The
question changes with it: not *when to stop* but *what to skip*.

## 3. The novelty filter recovers nothing

Same ranking, same 32,000-char budget, any-evidence recall on 470 items:

| arm | any evidence | all evidence |
|---|---|---|
| `shortest_first` (key-blind cost control) | 39 (8.3%) | 35 (7.4%) |
| **`rank_order` sessions — baseline** | **380 (80.9%)** | **210 (44.7%)** |
| novelty floor 0.05 – 0.30 | 380 (80.9%) | 210 (44.7%) |
| novelty floor 0.50 | 380 (80.9%) | 195 (41.5%) |
| novelty floor 0.70 | 374 (79.6%) | 135 (28.7%) |
| `oracle` ceiling | 470 (100%) | 341 (72.6%) |

**Zero of the 90-item headroom.** Every floor from 0.05 to 0.50 returns exactly
the baseline; above 0.50 it degrades. The filter does change behaviour — median
candidates taken falls from 8 to 4 — but the freed budget buys longer
candidates and no additional evidence.

This is a mechanism result, not an instrument artifact, and the distinction
§9.2 demands is answerable here: the instrument discriminates. It separates
`shortest_first` at 8.3% from rank order at 80.9% from the oracle at 100%, and
it penalises high floors. It could have shown a gain. There was none to show.

## 4. Why: the misses are cost skips, not ranking failures

Of the 90 items where rank order finds no evidence:

- **1** has its evidence ranked deeper than anything that fit.
- **89** have evidence *within reach* — median rank **7** — skipped because the
  session did not fit at the moment it was considered.

Evidence sessions run 13,000–23,000 characters against a 32,000 budget. Ranks 1
to 6 consume it first, the evidence session overflows, and `skip_on_overflow`
walks past it to smaller, lower-ranked material. Novelty cannot repair that: a
stale candidate skipped frees a few thousand characters, and the evidence needs
fifteen thousand contiguous.

Every key-blind repacking of the same ranking lands in the same place —
`stop_at_first_overflow` 377, `top_k_by_rank` 323 to 379, baseline 380. The
deployed policy is already the best of them. **Packing order is exhausted on
this ranking.**

## 5. What did move: the unit

Same ranking, same budget, same skip-on-overflow policy, episodes instead of
sessions as the candidate unit:

| | any evidence | all evidence |
|---|---|---|
| sessions | 380 (80.9%) | 210 (44.7%) |
| **episodes** | **396 (84.3%)** | **261 (55.5%)** |
| paired | **22 gains, 6 losses, net +16** | +51 |

A session that does not fit is skipped whole. Its episodes are small enough to
fit individually, and one of them may be the evidence.

**The six losses are the part that matters.** TA-001 and SR-001 both died on
losses rather than on net, and a finer unit lets many small fragments from
irrelevant sessions crowd in. SR-001 is the nearest prior: source-grouped
*spans* on the internal corpus, which failed at 0 gains and 2 losses. This is a
different unit on a different corpus and it is not the same test, but any
registration has to gate on losses and say why it expects a different outcome.

## 6. What a registration would have to fix

1. **Primary arm is granularity, not novelty.** Novelty is a measured null on
   470 items and belongs in the report as one.
2. **Two tiers, per §9.3.** A bar for *this works* and a separate lower bar for
   *carries signal worth a successor*, both numeric, both fixed before the run,
   both reachable in each direction under PF4.
3. **A no-regression bar on losses**, not just on net, with the 6 observed
   losses as the reachability evidence.
4. **A sealed split.** Everything above is development. The 470 items are the
   whole answerable set, so a confirmatory arm needs either a registered
   holdout carved from it or a different corpus.
5. **The §9.4 mirror on every bar:** can this gate fail while the property it
   certifies is true?

## 7. Standing

Novelty-floor filtering under a binding budget is a **measured null** on 470
real questions, and NF-001's suggestive +0.56 does not survive contact with an
instrument that can price displacement.

The granularity observation is **unregistered exploration**. It is not a result,
it is a reason to write a registration.

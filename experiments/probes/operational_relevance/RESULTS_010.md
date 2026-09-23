# AF-PRE-010 RESULTS — the 64 anchor misses cost the deployed pack almost nothing

Plan `674d6db3`, preflight `38e46b20`. Zero model calls, zero reader calls: the probe reads
committed pack artifacts and asks what the deployed context actually contained on the items
AF-PRE-009 called errors.

**Instrument gate passed cleanly.** Delivered-turn identity recovered from rendered pack text
reproduced D-comp's own `units_delivered` on **842/842 items with zero error** (the PF4 estimate
of ±1 was pessimistic), so "was this turn in the pack?" is an exact question here, not an
approximation. PF6 join check on the NF-004 arms reproduced the preflight counts exactly
(33/23 of 36).

## The number that matters

| D-product = episodic read path, 32k, 120/120 items | misses (64) | hits (56) |
|---|---|---|
| ≥1 annotated evidence turn delivered | 62/64 | 56/56 |
| **all annotated evidence turns delivered** | **55/64 (85.9%)** | 56/56 (100%) |
| **the gold anchor turn itself delivered** | **61/64 (95.3%)** | 56/56 |
| a turn containing the answer value delivered | 26/64 | 33/56 |
| `silent` (all evidence **or** answer-bearing delivered) | **56/64 = 87.5%** | 56/56 |

**Disposition: OPERATIONAL_SILENT** (registered bar ≥ 0.80; observed 0.875).
**`cost_set` = 8** items — misses where the pack contained neither complete evidence nor any
answer-bearing turn (cat-1 3, cat-3 3, cat-4 2). The registered pilot threshold was 10, so the
**reader pilot is not registerable** and no inference budget is spent.

D-ranked (NF-004 `P_PAIR_RANK`, 63/120 items, its own committed flags): misses deliver all
evidence 23/36 (16k) and 29/36 (32k) vs hits 27/27; `SOURCE_ORDER` 11/36. Same direction, smaller
pack.

## What this means for the arc

**At the budget the product runs at, the reranker's top-1 disagreement with LoCoMo is nearly
free.** On 61 of the 64 misses the anchor turn it failed to select was *already sitting in the
delivered context*. The 56/120 metric was measuring a decision the deployed system never has to
make: it does not pick one turn, and at 32k it can afford to carry the earliest mention along with
everything else. So AF-PRE-005's 56/120 is a **non-operational metric**: report it as a
characterization of what a 6-layer cross-encoder learns about earliest-mention, and stop treating
it as a product number. What survives as product-facing from this arc is the E-gap result (17
anchor exchanges absent from retrieved context, 17/17 recovered by the event rule, held while the
reranker trained on it).

**And the reverse reading is the useful one.** Delivery is what makes anchor ranking *worth*
anything when delivery is not automatic — 23/36 at `P_PAIR_RANK` 16k, 11/36 at source order. The
question the arc should ask next is not "can the reranker pick the anchor" but **"at what context
budget does picking the anchor start buying evidence?"** — a budget-sweep successor, offline, no
reader, on the same keys.

## Reported against me, not smoothed

- **The hits control disagrees with its own registered threshold.** The gap between hits and
  misses on complete-evidence delivery is 12.5 points, below the registered 15-point bar, so the
  registered rule says "unrelated". Fisher exact on the same table gives **p = .0034** (any
  evidence p = .498, answer-bearing p = .067). The p-value is driven by a degenerate reference cell
  (every hit delivered), and a 15-point bar on n = 64 against a 100% reference was badly calibrated
  — PF4 checked that both directions were *reachable*, not that the bar was *sensitive*. That is a
  protocol lesson, not a licence: the disposition is not reopened, because it rests on
  `silent_rate` = 0.875 and on `cost_set` = 8 (a count), neither of which the p-value touches.
- `silent` means **no measurable delivery cost**, never "no answer cost". HH-004 is the program's
  precedent that a mechanical evidence ceiling did not transfer to answer accuracy, and NF-005/006
  show delivered evidence gets diluted. A reader could still fail on all 55 delivered items.
- The episodic arm renders consolidated blocks, so recovered delivery is a **lower bound** and
  87.5% understates silence. Direction is stated; magnitude is not corrected.
- 8 of 64 is not a null: it is the exact set the arc would fight for if the budget were cut, and it
  is where the 10-item power floor lives.
- Coverage: D-product 120/120 (10 conversations); D-ranked 63/120 (6 conversations) and it shares a
  retrievability signal with the reranker, so its larger hits/misses gap is partly selection, not
  mechanism. The adopted 0.3.0 timeline composition has no per-item LoCoMo pack artifact at all, so
  nothing here speaks to it. Characterization only; no reader, no adoption.

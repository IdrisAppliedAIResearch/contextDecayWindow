# Study 006 — LTM Analysis (S6-T-020)

**Observational only. No pass/fail interpretation; the bars are scored in
`experiments/study_006/evaluation/`.**

## Span inventory

| Dream event | Domain | Episodes | Spans | Eligible | Survivors | Records |
|---:|---|---:|---:|---:|---:|---:|
| 31 | civil_engineering | 30 | 798 | 320 | 319 | 50 |
| 61 | renaissance_art | 30 | 817 | 386 | 386 | 50 |
| 91 | monetary_policy | 30 | 827 | 372 | 372 | 50 |
| 111 | marine_biology | 21 | 551 | 159 | 159 | 50 |
| **total** | | **111** | **2,993** | **1,237** | **1,236** | **200** |

Eligibility removed 1,756 of 2,993 spans (58.7%). Dedup at 0.95 cosine collapsed
exactly **one** span across the entire run — near-duplicate sentences are rare at
this granularity, where Study 005's whole-turn dedup had more to collapse.

## Compression and context

| Measure | Study 006 treatment | Same-seed control | Study 005 (reference) |
|---|---:|---:|---:|
| Distilled records | 200 | 12 | 12 |
| Distilled characters | 29,214 | 49,785 | 49,785 |
| Compression (% of raw) | **6.55%** | 11.04% | 10.81% |
| Peak context | **12,169** | 16,171 | 16,171 |

The treatment stores 17× more records in 0.59× the characters, and its peak
context is 25% *lower* than the control's. Span selection is materially more
compact than whole-turn selection.

## Source composition

163 assistant records / 37 user records (81.5% / 18.5%).

The 1.5× user weight is a tiebreaker, not a dominance rule, and behaves as
pre-registered: the store is still majority assistant content, because terse
model-generated specification rows are genuinely dense. What changed relative to
Study 005 is that user-planted facts are now selected *as well as* the dense
assistant rows rather than being crowded out by them.

## Density profile

Median selected density 0.30; median selected span length 22 words. The selection
therefore sits well away from both failure modes: it is not dominated by 4-word
fragments (which the eligibility floor excludes) nor by 60-word run-ons.

## Formation by fact

| Domain | Facts present | Of |
|---|---:|---:|
| civil_engineering | 5 | 5 |
| renaissance_art | 1 | 3 |
| monetary_policy | 1 | 3 |
| marine_biology | 1 | 3 |

`art_pigment`, `art_patron_role`, `monetary_taylor`, `monetary_fed`,
`marine_photophores` and `marine_feeding` were not selected. Every one of these
was predicted unreachable by the replay gate and recorded in Amendment 001 §7
before the run. Q5 depends on `art_pigment` and Q8 on `marine_photophores`, and
both scored below full credit in the treatment — the predicted consequence.

## Rank movement for the Study 005 near-misses

Measured on the replay of the same store; the live run reproduces the same
selection.

| Domain | Source turn | Study 005 rank | Study 006 rank | Selected |
|---|---:|---:|---:|---|
| renaissance_art | 55 | 18 of 30 | 29 of 393 | yes |
| renaissance_art | 56 | 30 of 30 | 101 of 393 | no |
| renaissance_art | 60 | 19 of 30 | 171 of 393 | no |
| marine_biology | 100 | 11 of 21 | **1 of 177** | yes |
| marine_biology | 101 | 15 of 21 | 31 of 177 | yes |
| marine_biology | 102 | 18 of 21 | 14 of 177 | yes |

Four of the six are now selected; marine turn 100 moved from 11th of 21 turns to
1st of 177 spans.

## Breadth retrieval anatomy — the central observation

The distilled store and what actually reached the model at the two breadth probes
are not the same thing, and the gap is the finding of this study.

**What each store contains** (planted terms present in distilled records):

| Domain | Treatment store | Control store |
|---|---|---|
| civil | Halcyon, 847, S460ML, Bekova, 92.4 | Halcyon, 847, S460ML, Bekova, 92.4 |
| art | Annunciation, Melozzo, della Rovere, 1483 | della Rovere |
| monetary | Priya Mehta, reverse repurchase, 2.3%, Federal Reserve | Federal Reserve, Taylor |
| marine | Vampyroteuthis, Watanabe, marine snow, photophore | Vampyroteuthis, Watanabe, marine snow |

**What reached the constructed context at Q11 (turn 120):**

| Domain | Treatment | Control |
|---|---|---|
| civil | Halcyon | Halcyon, 847, S460ML, Bekova, 92.4 |
| art | — | della Rovere |
| monetary | — | Federal Reserve, Taylor |
| marine | — | marine snow |

**The treatment built a strictly richer store and retrieved strictly less from
it.** Its store is the first in this program to contain planted content from all
four domains; at the breadth probe it surfaced one term from one domain, while the
control surfaced all four domains from a poorer store.

The mechanism is a granularity/budget mismatch that the study did not anticipate.
Retrieval returns a fixed *number* of LTM items — 4 for the treatment, 5 for the
control at turn 120. Under whole-turn selection each item is an entire turn
carrying many facts across a domain, so five items give broad coverage. Under span
selection each item is a single sentence, so four items give four sentences, and
the top-ranked spans by similarity to a breadth query cluster in one topic.

Making each record ~17× smaller in information content while leaving the retrieval
budget expressed as a count of records is what converted a formation success into
a retrieval regression.

This is exactly the risk Amendment 001 §7 recorded before the run: *"A 200-record
store is ~17× larger than Study 005's 12. Retrieval and arbitration were exercised
at 12 records. Their behaviour at 200 is untested... This could help breadth or
hurt precision."* It hurt.

The read path was out of scope for Study 006 by pre-registration and was not
modified. This observation is the specification for the next study.

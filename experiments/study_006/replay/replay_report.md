# Study 006 — Retrospective Replay Gate (S6-T-011 / S6-T-012)

**Date:** July 25, 2026
**Pre-registration SHA:** `5def302`
**Replay input:** `experiments/study_005/runs/study_005_full_001/condition_c/study.db`
**Segmenter:** `spacy:en_core_web_sm:3.8.0:sentencizer`
**NER extractor:** `spacy:en_core_web_sm:3.8.0:ner`

## Verdict

> ## GATE FAILED — 0 of 4 domains formed.
> The pre-registration is explicit: **"If the gate fails: do not run."**
> S6_006 (ablation), S6_007 (both arms), and S6_008 (scoring) are blocked.

| Gate criterion | Required | Observed | Result |
|---|---|---|---|
| Rubric-critical plant selected per domain | 4 of 4 | **0 of 4** | **FAIL** |
| Non-content spans among selected | 0 | 0 | PASS |
| Selected records verbatim at recorded offsets | 100% | 100% | PASS |
| Study 005 near-miss ranks recorded | required | recorded below | PASS |

The two mechanical criteria pass cleanly. The selection criterion — the entire
point of Study 006 — fails completely.

## Read-only compliance

271 Study 005 artifacts were SHA-256 hashed before and after the replay and were
byte-identical. The database was opened through SQLite's `mode=ro` URI. Nothing
was written back into Study 005; all output is under
`experiments/study_006/replay/`.

## What the replay did

Each of Study 005's four dream events was reconstructed from the preserved store:
the same topic, the same episode snapshot. Reconstruction was verified against
Study 005's own logged `episodes_evaluated` — 30 / 30 / 30 / 21 — and matched
exactly at every event.

| Dream event | Domain | Episodes | Spans | Eligible | After dedup |
|---:|---|---:|---:|---:|---:|
| turn 31 | civil_engineering | 30 | 798 | 320 | 319 |
| turn 61 | renaissance_art | 30 | 780 | 393 | 393 |
| turn 91 | monetary_policy | 30 | 839 | 327 | 317 |
| turn 111 | marine_biology | 21 | 594 | 177 | 177 |

## Why it failed

**Density normalization replaced Study 005's long-span bias with an equal and
opposite short-span bias.**

Study 005 ranked whole turns by absolute entity+numeric counts, so long verbose
answers won by accumulating incidental content over length. Study 006 divides by
word count — and the spans that win are now the shortest ones. The top-ranked
selections on real data are terse assistant label:value rows:

| Selected span | Words | Density | Salience |
|---|---:|---:|---:|
| `Tensile Strength: 620–780 MPa` | 4 | 1.250 | 1.250 |
| `Yield Strength: ≥ 460 MPa` | 5 | 0.800 | 0.800 |
| `**Habitat Depth Range:** 600 to 900 meters` | 7 | 0.857 | 0.857 |
| `**Outcome:** The bubble burst in 2000–2001.` | 6 | 0.833 | 0.833 |

A four-word specification row reaches a density no ordinary sentence can match.
The planted facts are ordinary prose sentences of 10–30 words scoring 0.3–0.6,
and they sit mid-pack.

This shape is guaranteed rather than incidental: the study script's own standing
rule requires the assistant to answer in numbered lists with specifications, so
every assistant turn emits exactly the terse label:value rows that dominate a
density ranking.

### Plant rank by domain

`rank` is the position of the best span satisfying that plant key row, among all
surviving candidates for its dream event.

| Domain | Fact | Rank | Of | Percentile |
|---|---|---:|---:|---:|
| civil_engineering | civil_span | **6** | 319 | 1.9% |
| civil_engineering | civil_project | 12 | 319 | 3.8% |
| civil_engineering | civil_steel | 14 | 319 | 4.4% |
| civil_engineering | civil_load | 25 | 319 | 7.8% |
| civil_engineering | civil_engineer | 42 | 319 | 13.2% |
| renaissance_art | art_identity | **29** | 393 | 7.4% |
| renaissance_art | art_patron_role | 205 | 393 | 52.2% |
| renaissance_art | art_pigment | 288 | 393 | 73.3% |
| monetary_policy | monetary_threshold | **34** | 317 | 10.7% |
| monetary_policy | monetary_fed | 48 | 317 | 15.1% |
| monetary_policy | monetary_taylor | 74 | 317 | 23.3% |
| marine_biology | marine_identity | **8** | 177 | 4.5% |
| marine_biology | marine_photophores | 56 | 177 | 31.6% |
| marine_biology | marine_feeding | 89 | 177 | 50.3% |

Every plant key row is matched by at least one span. **The plant key is sound and
the segmentation is sound; the ranking is what fails.** The best plant in each
domain ranks 6th, 29th, 34th and 8th against a cap of C = 3.

**To form 4 of 4 domains under this policy the cap would have to be C = 34.**

## The structural cause: cap versus candidate pool

The pre-registration carried **C = 3 unchanged from Study 005** while changing the
selection unit from turns to spans. That is the defect.

Study 005 chose 3 records from ~30 episodes — a **top-10%** requirement. Study 006
chooses 3 records from 177–393 spans — a **top-1%** requirement. Moving to span
granularity multiplied the candidate pool roughly tenfold and left the cap fixed,
so the selection problem became about ten times *harder*, not easier.

Seen in that light the policy is not simply failing. Measured by percentile the
plants moved substantially in the right direction:

| Domain | Study 005 rank | Study 006 rank | 005 pct | 006 pct |
|---|---:|---:|---:|---:|
| renaissance_art (turn 55) | 18 of 30 | 29 of 393 | 60% | 7.4% |
| renaissance_art (turn 56) | 30 of 30 | 101 of 393 | 100% | 25.7% |
| renaissance_art (turn 60) | 19 of 30 | 171 of 393 | 63% | 43.5% |
| marine_biology (turn 100) | 11 of 21 | **1** of 177 | 52% | 0.6% |
| marine_biology (turn 101) | 15 of 21 | 31 of 177 | 71% | 17.5% |
| marine_biology (turn 102) | 18 of 21 | 14 of 177 | 86% | 7.9% |

Five of the six pre-registered near-misses improved sharply in percentile terms,
and marine turn 100 went from 11th of 21 turns to **1st of 177 spans**. The
direction of the correction is right. The magnitude is insufficient against a cap
that was never rescaled for the new granularity.

## Parameters ruled out as the cause

Both knobs the pre-registration permits re-deriving from replay evidence were
swept. Neither changes the verdict.

**Coverage floor F** — flat across the whole range. F governs only whether records
are written at all, never their order, so it cannot promote a plant into the top 3.

| F | 0.05 | 0.10 | 0.125 | 0.15 | 0.175 | 0.20 | 0.25 | 0.30 |
|---|---|---|---|---|---|---|---|---|
| Domains formed | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 |

**Eligibility lower bound** — the bound exists specifically to "prevent fragment
gaming". Raising it from the pre-registered 4 words as far as 16 improves plant
ranks only marginally and never forms a single domain.

| Min words | 4 | 6 | 8 | 10 | 12 | 14 | 16 |
|---|---|---|---|---|---|---|---|
| Domains formed | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 |
| Best civil rank | 6 | 4 | 8 | 7 | 5 | 4 | 4 |
| Best art rank | 29 | 29 | 28 | 28 | 26 | 25 | 24 |
| Best monetary rank | 36 | 36 | 35 | 34 | 34 | 33 | 31 |
| Best marine rank | 8 | 8 | 6 | 6 | 6 | 6 | 6 |

**F remains unlocked.** S6-T-013 cannot be completed: the pre-registration forbids
locking F on anything other than replay evidence, and replay shows F is not the
operative parameter.

## A correction made during this task

The first replay produced spans such as `"Tensile Strength: 620–780 MPa\n    3."`
— not sentences. Sentence segmenters treat a numbered-list ordinal as terminal
punctuation, so the ordinal of list item *n+1* was absorbed into item *n*'s span,
and `count_numeric_tokens` counted that borrowed ordinal as a fact because its
marker-stripping regex requires trailing whitespace that end-of-span does not
provide.

Segmentation now splits on line boundaries first and drops leading list markers by
advancing offsets, never by rewriting text, so offsets remain exact. That first
run reported 1 of 4 domains formed; the single "formed" domain was civil, carried
by the malformed span `"Project Name: Halcyon Crossing\n2."`. **That 1/4 was
spurious** — a formation credited to a span containing a leaked ordinal. The
corrected figure is 0 of 4.

## What this does not show

The replay validates against data the policy was designed after, and cannot
establish generalization. Its pre-registered role is narrower and is exactly what
happened here: it prevented spending a live run on a policy that provably cannot
work.

Note also that the adversarial fixture (S6_004) **passes** — the Study 006 policy
selects a short dense plant over long diffuse decoys carrying higher absolute
counts, and the Study 005 policy does not. The fixture tests the failure *shape*
in isolation, with six spans in one topic. Replay tests it at real scale, with
~800 spans per event. Both results are valid and they are not in conflict: the
mechanism works as designed, and is then swamped by the volume of terse
model-generated spans that real output contains. The fixture was necessary and is
not sufficient — which is itself a finding worth carrying into the report.

## Status

- S6-T-011 harness: **complete**, read-only compliance verified.
- S6-T-012 gate: **FAILED** at 0 of 4 domains.
- S6-T-013 lock F: **blocked** — F is not the operative parameter.
- S6_006 onward: **blocked** by the pre-registered stop condition.

Proceeding requires a policy revision that is not derivable from the two locked
documents, and therefore requires an explicit decision before any further work.

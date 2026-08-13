# NF-002 Pre-Registration — Candidate Granularity Under a Binding Budget

**Document type:** Locked pre-registration
**Status:** `LOCKED — CHARACTERIZATION ONLY, SEE DEVIATION 001`
**Part 1 record:** `NF_002_PART1_RECORD.md`, committed at `2b1c20ee`
**Deviation:** `amendments/DEVIATION_001_holdout_observed_before_registration.md`
**Corpus:** LongMemEval, 470 answerable items, committed EC-002 session ranking
**Model calls:** 0
**Date:** August 12, 2026

## 0. What this registration is not

The holdout counts were observed before these bars were written. Deviation 001
records it. **NF-002 therefore cannot produce a confirmatory result and its
highest available disposition is `CHARACTERIZED`.** The bars below are binding
on the reading, not on the world.

They are still worth locking. A registered statistic and a registered loss bar
stop a favourable number from being talked upward, which is the whole function
they serve here.

## 1. Hypothesis

Under a budget that truncates, the candidate **unit** — not the ranking, not the
packing order, not marginal novelty — is what determines whether evidence
reaches the reader. A session that overflows is skipped whole; its episodes fit
individually, and one of them may be the evidence.

## 2. What Part 1 established, and what it killed

- Marginal novelty filtering recovers **0** of the 90-item headroom at every
  floor from 0.05 to 0.50, and does harm above it. This is a **measured null**
  on 470 items and is reported as one.
- **89 of 90** misses have evidence within reach at median rank 7, skipped on
  cost. Only 1 is a ranking failure.
- Every key-blind repacking of the ranking lands at 377–380 against a baseline
  of 380. Packing order is exhausted.

## 3. The arms

Identical ranking, identical 32,000-character budget, identical
skip-on-overflow policy. The **only** difference is the unit.

| Arm | Unit |
|---|---|
| `A0` baseline | session |
| `A1` treatment | episode |

Controls, all computed and reported: `shortest_first` (key-blind cost gaming),
`oracle` (ceiling, measurement only), and the novelty floors from Part 1.

## 4. Registered statistic

**Paired discordant counts with a one-sided exact binomial sign test**, on
`any_evidence` — whether at least one evidence session reaches the reader.

Only items where the two arms disagree contribute. A base rate cannot carry it,
a degenerate arm cannot win it, and it is the correct test for paired binary
outcomes on the same items. Reported alongside, never able to pass anything:
net item counts, `all_evidence`, and per-stratum breakdowns.

## 5. Two tiers, fixed before the run

Per `AGENTS.md` §9.3.

| Disposition | Condition |
|---|---|
| **WORKS** | gains ≥ 2 × losses **and** p ≤ 0.05 |
| **CARRIES SIGNAL** | gains > losses **and** p ≤ 0.20, and not WORKS |
| **NULL** | gains ≤ losses, or p > 0.20 |

Both thresholds are numeric, both are fixed here, and neither may move.

### Reachability, both directions (PF4)

On the 285-item holdout the maximum reachable gain is bounded by the 90-item
baseline miss set, so double-digit gains are attainable; and a null is
attainable, since a unit change that does nothing yields 0 discordant pairs.
Development is 8 gains / 0 losses, p = 0.0039 — which reaches WORKS. A
hypothetical 6 gains / 6 losses reaches NULL. Both tiers are reachable in both
directions.

### The §9.4 mirror: can this gate fail while the property is true?

**Yes, and it is the main risk.** With ~20 discordant pairs, an effect that is
real but modest can miss p ≤ 0.05 on sampling alone: 14 gains against 6 losses
gives p = 0.058 and would land in CARRIES SIGNAL rather than WORKS on a
difference of one item. The `CARRIES SIGNAL` tier exists precisely so that
outcome is reported as signal instead of being rounded to a null. The report
must state the discordant-pair count next to every p value so the reader can
see the power available.

## 6. The loss bar is the safety gate

`gains ≥ 2 × losses` is not decoration. TA-001 died at 2 gains against 6 losses
and SR-001 at 0 gains against 2 losses; both were net-negative mechanisms that a
net-only bar would have argued about. A finer unit admits fragments from
irrelevant sessions, so losses are the expected failure mode and they are gated
directly.

## 7. Parameters, each justified

| Parameter | Value | Why |
|---|---|---|
| budget | 32,000 chars | the program's carried delivery control since Study 007; unchanged so the arms differ only in unit |
| ranking | EC-002's committed session cosine order | frozen upstream artifact, reproduced exactly on all 470 items before use |
| split | 40/60 stratified by `question_type`, seed `5005` | strata keep every question type in both halves; the seed is the program-wide constant |
| packing policy | skip-on-overflow | EC-002's own policy, and Part 1 showed it is the best of the key-blind alternatives |
| evidence unit | session-level `any_evidence` | the committed EC-002 measurement, so the anchor holds |

Nothing is inherited unexamined. `min_event_size` carried unchecked through
three DMR stages and became the binding constraint nobody had tested.

## 8. Decision

**WORKS** — the unit is the operative variable under a binding budget, on a
development characterization. Not a confirmation. A successor gets a
confirmatory registration on an untouched corpus.

**CARRIES SIGNAL** — same, weaker; the successor is still justified and the
report says the effect was not separable from sampling at this power.

**NULL** — granularity joins novelty as a measured null, packing and unit are
both exhausted on this ranking, and the remaining lever is the ranking itself.

No disposition authorizes retrieval changes, an ablation, a live run, or
adoption. This is 470 offline items against a frozen ranking, and nothing in it
touches a reader.

## 9. Preflight

**State:** `NOT RUN`. Executed and committed before the gates.

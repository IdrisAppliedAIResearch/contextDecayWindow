# Amendment 001 — Phase 2 Report

## The Band Is 3.0

**Amendment:** `../amendments/AMENDMENT_001_determinism_and_noise_band.md`, authorized 2026-08-09
**Decision rule:** `DECISION_RULE.md`, committed `c07e1e27` **before any replicate ran**,
LF digest `d412f8e0f713887bf8765a4c4075458c3bc74a54560e0a26dc46761f921c8e83`, pinned in
`src/analysis/amendment_001_noise_band.py` — a mismatch voids the verdict
**Evidence:** `band_verdict.json`, `evaluation/`, `run_manifest.json`, `runs/`
**Verdict:** **> 1.5 — nothing below about three points is interpretable**

---

## 1. Result

Five replicates of Arm D, the deployed configuration. Identical corpus, settings, seed
and standing runtime at temp 1, run back to back in one server process (PID 29344),
control isolation PASS on each, engine digest `041aaa94` matching Study 011's committed
Arm D on all five.

| Replicate | Total /13 |
|---|---:|
| `study_011_noise_band_d_01` | **11.0** |
| `study_011_noise_band_d_02` | 8.0 |
| `study_011_noise_band_d_03` | 8.0 |
| `study_011_noise_band_d_04` | 8.0 |
| `study_011_noise_band_d_05` | 8.0 |

**Band (max − min): 3.0.** Standard deviation 1.34, *with the caveat the rule attaches
to it: n = 5 estimates a standard deviation poorly, and §4.3 does not read it.*

Study 011's committed Arm D scored **8.0**.

## 2. This is not a spread. It is a switch.

**Five runs, two distinct answer trajectories.** Replicates 2 through 5 are
byte-identical to each other across all 121 turns. Replicate 1 differs from them at
turn 1 and never re-converges.

Turn 1's prompt is byte-identical in all five, 757 bytes, `ea8bd59b`. Replicate 1
answers in **343 characters**; replicates 2–5 answer in **80**; the two diverge at
**character 79**. Those are, digest for digest, the two responses whose disagreement
Study 011 recorded and this amendment was raised over — `265ddd79` and `9675ab02`.

The only thing that distinguishes replicate 1 is that it met an empty server slot. Every
later run met a slot holding its predecessor's last prompt.

**So the instrument is bimodal, not noisy.** Each mode is exactly reproducible: three
consecutive byte-identical 121-turn reruns is the standing rule's *byte-identical seeded
prefix rerun*, satisfied in full, between runs that share process state.

**What produced the switch is not identified here**, and no mechanism is claimed. What is
established is that it exists, that it is worth 3.0 points on a 13-point rubric, and that
it is invisible to a study that runs one arm once.

## 3. Where the points moved

| Question | Replicate 1 | Replicates 2–5 | Range |
|---|---:|---:|---:|
| Q1 early numerical | 1.0 | 0.5 | 0.5 |
| Q2 early entity | 1.0 | 0.0 | 1.0 |
| Q4 middle multi-fact | 1.0 | 0.0 | 1.0 |
| Q8 photophore location | 1.0 | 0.5 | 0.5 |
| Nine other questions | — | — | **0.0** |

**Spread across the rubric, not parked in one item.** §4.2.4 asks for this distinction
because a band carried by one question is a statement about that question and a band
across four is a statement about the instrument. This is the second.

The four that move are all *fact-delivery* questions. The nine that do not include every
binary bleed, disambiguation and rule-compliance probe.

## 4. Rater disagreement, kept separate

| Replicate | Items | Unanimous | Split | Mean rater spread/item |
|---|---:|---:|---:|---:|
| `run_beta` (= replicate 1) | 13 | 12 | 0 | 0.038 |
| the other four | 13 each | 13 each | 0 | 0.000 |

64 of 65 items unanimous across three raters, zero splits. **The 3.0 is run-to-run
variation, not raters reading one answer two ways.** §4.2.5 requires these kept apart and
they are; pooling them would have let near-total rater agreement read as instrument
stability.

**Rater family departure, disclosed in the decision rule before the measurement rather
than after it:** three distinct models, one family — `claude-opus-5`, `claude-sonnet-5`,
`claude-haiku-4-5-20251001`. Shared-family bias inflates apparent agreement, and inflated
agreement **understates** a band. 64 of 65 unanimous should be read with that attached.

## 5. Applied uniformly, in whichever direction it points

One expression over every scored gap §2 of the amendment names. No result is exempted for
being one the program would prefer to keep.

| Result | Gap | Exceeds 3.0? | Re-read as |
|---|---:|---|---|
| Study 009 same-seed contrast, S vs L | 3.0 | no | **NOT DEMONSTRATED** |
| LV-001 targeted regression | −2.0 | no | **NOT DEMONSTRATED** |
| Study 011 B1, C vs D | −1.0 | no | **NOT DEMONSTRATED** |
| The corrected treatment series, 8.5 → 12.0 | 3.5 | yes | not excluded by the band |

The last row is not a promotion. **Exceeding the band is not being demonstrated** — it is
only not being excluded by this measurement.

The first row is the arc's cleanest architectural number, and it is the one this costs
most.

### 5.1 How far the band transfers, stated in both directions

§5 of the amendment required this to be stated wherever the band is cited, so it is
stated here rather than at the end.

**Against transfer:** the band is measured on one configuration, one corpus, one seed,
one machine. Its composition is one cold-start run against four warm-start runs, and
**all four of Study 011's live arms ran 5th through 8th in a single server process** —
every one of them warm. The cold/warm switch that produces this band therefore does not
distinguish A, B, C and D from each other.

**That is not a rescue and is not used as one.** §1.2 is binding: B1 fired, Arm C scored
7.0 against Arm D's 8.0, the correction is not adopted, and no part of this measurement
may be cited toward adopting K-first packing. §4.3's reading is applied as committed.
What the observation does is bound what the band licenses — it is a limitation on
transferability, recorded because the surrogate audit demanded it, and it applies to
every row of the table above equally.

**For transfer, and this is the sharper half:** Study 009's 3.0 has *less* protection
than Study 011's −1.0, not more. Arm S ran on 2026-07-26 at 21:19; Arm L is the preserved
Study 007 condition-C artifact from 16:36 the same day, a separate launch hours earlier.
Neither manifest records a server PID at all. The process state of the two arms in the
arc's cleanest contrast is **uncontrolled and unknowable from the committed artifacts**.

## 6. What this does not establish

- **What produced the switch.** Cold versus warm slot state is where it appears; the
  mechanism is not identified and is not guessed at.
- **That the band is 3.0 for any other arm, corpus, budget or machine.** It is measured
  on Arm D and applied elsewhere by assumption, which is an assumption.
- **That five runs bound the true spread.** Two distinct outcomes from five runs is a
  loose bound. A third mode would not have shown up here.
- **That any re-read result is false.** "Not demonstrated" is not "refuted." Study 009's
  3.0 may well be real; this study cannot tell, and neither could the one that reported it.

## 7. What is untouched

Every offline, deterministic result. Gate outcomes, delivery counts, character
accounting, packing measurements, EC-002's 152 gains and zero losses, IC-001's zero K
episodes at 8 of 8 probes, and Arm D's per-question identity to Arm A with byte-identical
windows at turns 117, 118 and 119. Those are identity and count comparisons, not score
comparisons, and this band does not touch them.

The N-tier findings are untouched for the same reason: they are replays against committed
logs, not scores.

## 8. Non-rescue clause, binding

**B1 fired. Arm C scored 7.0 against Arm D's 8.0. The packing correction is not adopted.
That verdict is final.** This band may not be cited in support of any adoption decision
for K-first packing. Any future adoption requires a new study with its own
pre-registration and its own bar.

The clause and §4.3's table are mirrors: neither direction gets special treatment. The
band dissolved this study's own kill in the same commit that it dissolved the arc's
headline architectural contrast.

# Study 007 — Targeted-Retrieval Fixture (S7_004)

**Status:** PASS at `B_ltm = 32,000`, `k_min = 1`
**Tasks:** S7-T-012 (author), S7-T-013 (run and evaluate)
**Fixture:** `tests/targeted_retrieval_fixture.json` — committed before the calibration sweep
**Binding amendment:** `amendments/AMENDMENT_002_floor_cost_criterion.md`
**Raw data:** `experiments/study_007/replay/calibration_sweep.json`

---

## 1. What this fixture is for

The diversity floor's risk is the mirror image of the breadth failure: budget
reserved for other domains is budget not spent on the asked-about one. Study 006
lost breadth by over-concentrating; a floor that over-corrects would lose
targeted recall the same way, and Bar 2 would catch it only after a full run.

Eight narrowly targeted queries, two per domain, phrased like the Cat 1–3 rubric
questions rather than like the breadth probes. They run against Study 006's
preserved distilled store, read-only.

`art_targeted_2` deliberately targets `art_pigment`, a plant known to be
unformed, so the fixture also exercises the case where the queried domain is
thin in the store.

## 2. Results at the locked parameters

| Query | Domain | Own-domain share | Majority | Top span present | Chars lost | Bound | Bounded |
|---|---|---:|---|---|---:|---:|---|
| civil_targeted_1 | civil | 0.567 | ✓ | ✓ | 12,809 | 19,527 | ✓ |
| civil_targeted_2 | civil | 0.608 | ✓ | ✓ | 11,382 | 18,053 | ✓ |
| art_targeted_1 | art | 0.721 | ✓ | ✓ | 9,084 | 15,078 | ✓ |
| art_targeted_2 | art | 0.695 | ✓ | ✓ | 9,173 | 15,497 | ✓ |
| monetary_targeted_1 | monetary | 0.587 | ✓ | ✓ | 11,210 | 16,420 | ✓ |
| monetary_targeted_2 | monetary | 0.622 | ✓ | ✓ | 11,108 | 18,180 | ✓ |
| marine_targeted_1 | marine | 0.551 | ✓ | ✓ | 14,746 | 19,496 | ✓ |
| marine_targeted_2 | marine | 0.525 | ✓ | ✓ | 13,317 | 21,357 | ✓ |

**Criterion 1 — majority to the queried domain:** PASS, 8 of 8. Minimum share
0.525, maximum 0.721.

**Criterion 2 — the domain's top-similarity span present:** PASS, 8 of 8.
Including `art_targeted_2`, whose domain is thin: the floor guarantees its
inclusion, which is the mechanism working as intended.

**Criterion 3 — bounded floor cost:** PASS, 8 of 8 under the amended
character-expressed bound. Every query loses substantially less than the bound
allows; the tightest margin is `marine_targeted_1` at 76% of its bound.

## 3. The pre-registered slot form, and why it was replaced

Under the pre-registered form — *"loses no more than `k_min × (|T| − 1)` slots"*
— the two marine queries fail, at 4 slots against a bound of 3:

| Query | Slots lost | Slot bound | Held |
|---|---:|---:|---|
| civil_targeted_1 / _2 | 3 / 3 | 3 | ✓ |
| art_targeted_1 / _2 | 2 / 2 | 3 | ✓ |
| monetary_targeted_1 / _2 | 3 / 3 | 3 | ✓ |
| **marine_targeted_1 / _2** | **4 / 4** | 3 | ✗ |

The floor spent exactly its 3 permitted other-domain slots. Those episodes
average 4,048 characters; marine's average 3,673. So 12,145 characters of floor
displaced **3.31** marine slots — and 3.31 costs a fourth.

The criterion counted a ratio of episode sizes, not the floor's behaviour. It is
unsatisfiable for any domain whose episodes run smaller than the others', at
every budget where the floor binds — and passes at `B_ltm = 64,000` only because
the budget grows large enough that nothing is displaced at all.

Amendment 002 re-derives it in characters plus one record of bin-packing slack.
Worst overshoot of the character term alone, across the whole sweep, is 1,946
characters — 31% of one maximum record, consistent with discreteness rather than
with the floor overspending. Both forms are computed and reported for every
query in `calibration_sweep.json`.

## 4. Interaction with the replay gate

The two gates pull against each other exactly as the pre-registration
anticipated, and the sweep quantifies the tension:

| `B_ltm` | `k_min` | Four-domain (replay) | Own-domain share (fixture) |
|---:|---:|---|---:|
| 24,000 | 2 | ✓ | 0.215 ✗ |
| 28,000 | 2 | ✓ | 0.182 ✗ |
| 32,000 | 2 | ✓ | 0.158 ✗ |
| **32,000** | **1** | **✓** | **0.525 ✓** |

Any `k_min ≥ 2` at four topics reserves 6 other-domain episodes — roughly 24,000
characters — which is a majority of any budget this study can afford. The
fixture is what rules those configurations out, and it did so before a run was
spent. That is the fixture earning its place.

The pre-registration's remedy was applied in its stated order: `B_ltm` was
raised first, to 140,000 characters at `k_min = 2`, and the majority criterion
still does not hold there. Only then was `k_min` reduced.

## 5. Out-of-sample status

The fixture was authored and committed **before** the calibration sweep and was
not modified by it. Unlike `B_ltm` and `k_min`, which were calibrated on the
replay, the fixture constrains those parameters rather than being fitted to
them — it is the one offline check that is not circular.

Its limit: it uses the same store as the replay. The live run remains the only
fully out-of-sample evidence.

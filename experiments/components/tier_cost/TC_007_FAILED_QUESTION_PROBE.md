# TC-007 exploratory probe — why flat retrieval misses LoCoMo questions

**Status:** `EXPLORATION ONLY — POST-TC-001/003/004 — NO BAR, VERDICT, OR RUN AUTHORIZATION`  
**Date:** August 23, 2026  
**Question:** Why did the 16,000-character flat ranked arm fail complete-evidence delivery on 119 of 868 evaluable LoCoMo questions?

## 1. Frozen inputs

| Input | SHA-256 |
|---|---|
| TC-001 16k per-question rows | `df15e8e5d4a24ebfd963ec1978d48dce4be755921bf84fac5115bd4b8fffc7c9` |
| TC-001 32k per-question rows | `dd1017e0ccd9d7f6e8913fcbdb20092eec3d3074f13289276b7c70cfc81fd23c` |
| TC-003 16k per-question rows | `d4c80e8324c9db303b0df24e5a3ca095a377edff61f7158ee6541dfd9c0766d5` |
| TC-004 ordered-split outcomes | `26fe2a66b0814dae1546ae6b26dc3705d44065f87f4892893890b24fb0ba452c` |
| LoCoMo corpus | `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4` |

No embeddings or generations were called. The probe joins committed records by
stable question identity and reads the corpus only to count the sessions and
adjacent-turn pairs containing registered evidence.

## 2. What failed

At 16,000 characters, flat best-first retrieval delivered complete evidence for
749 of 868 evaluable questions and failed 119:

- **67** received none of their required evidence;
- **52** received some but not all required evidence;
- **59** failures required one evidence episode;
- **60** required two or more evidence episodes.

Every failed question had required evidence in the candidate store. This is a
delivery failure, not a formation or label-join failure.

## 3. The strongest moderator is evidence spread

| Registered evidence shape | Questions | Flat failures | Failure rate |
|---|---:|---:|---:|
| One adjacent-turn pair in one session | 704 | 61 | **8.7%** |
| At least three sessions | 44 | 28 | **63.6%** |
| Other multi-pair, fewer than three sessions | 120 | 30 | **25.0%** |

The 119 failures span sessions as follows: 71 require one session, 20 require
two, and **28 require three or more**. Those 28 are 23.5% of failures but only
5.1% of the evaluable population.

This supports TC-007's selected workload split. It does not prove that coverage
will repair the misses: multi-session obligation is a moderator, not a causal
mechanism.

## 4. Failure decomposition

The following hierarchy is descriptive and mutually exclusive:

| Probe outcome | Questions | Interpretation |
|---|---:|---|
| Recovered by flat retrieval at 32k | **61** | Primarily a 16k rank/packing boundary |
| Still failed at 32k, recovered by TC-004's full embedding-localized split at 16k | **11** | Consistent with information dilution inside parent pairs; representation and packing both changed |
| Recovered by neither | **47** | Evidence remains too weakly ranked for these tested remedies, or requires a different retrieval cue/objective |

The rank distributions agree with that reading. For the 61 budget-sensitive
questions, the median worst required-evidence cosine rank is **76**. For the 58
that still fail at 32k, it is **194**. Across all 119 failures, the median worst
rank sits **53 positions beyond** the number of units the 16k arm delivered.

The TC-004 split result is not an isolated causal estimate. Full splitting
rescued 33 of the 119 misses but reduced overall complete delivery from 749 to
687. Only 11 rescues were not also explained by doubling the budget. TC-004's
registered `NO_PREDICTIVE_SIGNAL` therefore remains binding.

## 5. Existing protected A3 coverage does not solve the set

TC-003 already supplies the nearest existing 16k character-budget probe: a dual
K/coverage arm with equal floors. Among the 119 flat misses it recovered **9**:

- 7 of the 61 budget-sensitive failures;
- 1 of the 11 localization-only failures; and
- 1 of the 47 unresolved failures.

But isolated rescues hide displacement. Across all 44 questions requiring
evidence from at least three sessions:

| Arm | Complete evidence |
|---|---:|
| Flat ranked | **16/44** |
| Dual ranked | **16/44** |
| Equal-floor dual A3 | **14/44** |

The equal-floor arm rescued four breadth misses while losing six breadth
questions flat already passed. Its nine total rescues carried evidence through K
on all nine; only one also used coverage. The old result therefore provides no
evidence that A3 coverage, as previously combined, repairs LoCoMo's spread
failures.

TC-007 is not an exact rerun: it uses per-conversation token percentiles,
semantic ownership of shared candidates, slack return, and a second carried
facility-location treatment. Nevertheless, the A3 treatment must be described
as a transfer/reproduction of a previously negative mechanism family, not as an
untested solution.

## 6. Plain finding

Flat retrieval fails LoCoMo for three related reasons:

1. **Budget boundary:** 61/119 failures are recovered by doubling the budget.
2. **Evidence localization:** 11 additional failures are consistent with useful
   text being diluted inside the ranked pair, although full splitting is harmful
   overall.
3. **Weak or distributed cue:** 47 survive both probes, and questions requiring
   evidence across at least three sessions fail 7.3 times as often as single-pair
   questions (63.6% versus 8.7%).

The probe supports testing protected spread, but it also supplies a hard warning:
the existing equal-floor A3 mechanism already traded breadth wins for more
breadth losses. TC-007 must beat flat on the combined paired endpoint; counting
coverage admissions, represented sessions, or rescued failures alone could pass
while retrieval is worse.

## 7. Limits

- LoCoMo and all compared artifacts are spent; this is characterization.
- The 16k/32k probes use characters, while TC-007 proposes token percentiles.
- Evidence presence is not reader use.
- Session count is structural spread, not proof of topical diversity.
- The facility-location protected arm has not been run on this population.
- No causal claim separates rank from exact packing inside the 61 budget-sensitive
  cases.


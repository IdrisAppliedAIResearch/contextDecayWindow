# DMR-001C Report - Sealed Confirmation of the Relative Drift Rule

**Pre-registration:** `DMR_001C_PRE_REGISTRATION.md`, committed alone at
`b839f8fd` with no file under `src/` or `tests/`
**Mechanism:** `AdaptiveEventContextFormer`, frozen at DMR-001B's anchor
`ad6f9451…c5ecc5e6`. Nothing was swept, selected, or tuned.
**Corpus:** 50 LongMemEval haystacks, 11,453 episodes, 2,128 real session seams
**Disposition:** `NO_BOUNDARY_EVIDENCE` - **G5 FAIL**, G1 to G4 pass

## 1. Result: the transfer claim holds, the boundary claim does not

| Gate | | |
|---|---|---|
| G1 Integrity | PASS | |
| G2 Partition | PASS | the former never saw a session change |
| G3 Nondegeneracy | PASS | 0 singletons, 0 capped closures |
| **G4 Stability** | **PASS** | p95/p05 fire-rate ratio **1.67x** across 50 streams |
| **G5 Boundary evidence** | **FAIL** | macro F1 0.387 against `C_PERIODIC_4`'s 0.606 |

## 2. What was confirmed

**G4 is the claim DMR-001B earned the right to test, and it holds on unseen
real conversation.** Per-stream adaptive fire rate ranged 3.41% to 7.35% across
50 independent haystacks, p05 to p95 of 3.83% to 6.38%, a ratio of **1.67x**.

For contrast, DMR-001's fixed threshold swung 10x between two synthetic scripts
and died entirely on one of them. The relative bar carries its operating point
onto a corpus built from a different benchmark, with real multi-session
structure, without a single parameter being touched.

The former was blind throughout: one stream token per haystack, so the
hard-boundary predicate never fired once in 11,453 episodes. Every boundary was
detected, none was handed over.

## 3. What failed, and the shape of the failure

| Arm | Precision | Recall | F1 |
|---|---|---|---|
| **T_ADAPT** | **0.837** | 0.253 | 0.387 |
| `C_PERIODIC_2` | 0.370 | 0.998 | 0.540 |
| **`C_PERIODIC_4`** | 0.527 | 0.713 | **0.606** |
| `C_PERIODIC_5` | 0.541 | 0.588 | 0.563 |
| `C_PERIODIC_6` | 0.578 | 0.524 | 0.549 |
| `C_PERIODIC_8` | 0.523 | 0.358 | 0.425 |
| `C_PAIR` | 0.186 | 1.000 | 0.313 |

G5 failed by 0.219. Fixed chopping every four episodes beat the detector.

The reason is recall, not accuracy. **The rule's precision is 0.837 against a
base rate of 0.186** - it is right about 84% of the boundaries it claims, and
its per-stream precision never fell below 0.556 on any of the 50 streams
(median 0.857, maximum 1.000). No control comes close; the best periodic
precision is 0.578.

But it fires on about 5% of episodes where seams occur on 18.6%, so it
recovers only a quarter of them. `min_event_size` is 5 and the median source
session is about 6 exchanges, so the rule structurally cannot claim seams that
fall closer together than 5 episodes.

**This was recorded before the run.** Registration section 2.2 states the
`min_event_size` ceiling on recall as a known property, and section 5 states
that G5 "is expected to be the harder of the two on this corpus." The
pre-registration called this correctly; the gate did what it was written to do.

## 4. A registration defect to carry forward

F1 against a dense-boundary corpus rewards frequent firing almost mechanically.
`C_PERIODIC_2` fires on half of all episodes and takes 0.998 recall; `C_PAIR`
fires on everything and takes 1.000. With seams every 5.4 episodes and a
tolerance of plus or minus 1, an ignorant chopper collects most of them.

Choosing macro F1 as G5's statistic therefore measured firing frequency as much
as boundary skill, on a corpus whose base rate was known and recorded before
the run. That is a poorly chosen statistic, and it is a defect in this
registration.

**It is not being re-scored.** The gate failed on the statistic it registered.
The precision result in section 3 is reported as characterization and is
explicitly not a substituted criterion. Any successor must register a statistic
that is not inflated by base rate - a precision-at-matched-firing-rate
comparison, or agreement scored against a fixed budget of claims - and must do
so before seeing a result.

## 5. Standing

DMR-001C is confirmatory in construction: the rule was frozen and committed
before this dataset existed on the machine, the corpus overlaps no previous
study's slice, and the registration commit contains no implementation file -
the corrective practice `DEVIATION_001` named, verified with `git show --stat`.

What that buys:

- **The stability property is confirmed.** A relative drift bar transfers where
  an absolute one does not. This is now shown on 50 real conversations, not two
  synthetic scripts.
- **The boundary claim is refuted on this corpus.** The rule is a precise but
  recall-starved detector, and against dense boundaries it loses to fixed
  chopping on the registered statistic.

DMR-002 remains blocked. Nothing here authorizes a retrieval claim, a reader
call, an ablation, a live run, a promotion, or an adoption. No parameter may be
retuned in response to this failure; section 8 of the registration forbids it
and a successor needs its own design.

## 6. What a successor would have to change

Not the threshold - that is settled. Two things:

1. **`min_event_size` is the binding constraint on recall**, and it was carried
   unchanged from DMR-001 without ever being tested against a corpus whose
   sessions are short. A successor that wants recall must treat it as a free
   parameter with its own justification, not an inheritance.
2. **The measurement**, per section 4.

## 7. Artifacts

| Artifact | Path |
|---|---|
| Dataset | `C:\Users\muzaf\datasets\longmemeval\longmemeval_s_cleaned.json`, sha256 `d6f21ea9…78c3a442`, verified |
| Corpus lock | `artifacts/dmr001c_corpus/corpus_lock.json` |
| Pre-registration | `DMR_001C_PRE_REGISTRATION.md` |
| Gate report | `artifacts/dmr001c_gates/gate_report.json` |
| Mechanism (unmodified) | `src/biological_memory/adaptive_event_context.py` |
| Tests | `tests/test_dmr001c_sealed_holdout.py` |

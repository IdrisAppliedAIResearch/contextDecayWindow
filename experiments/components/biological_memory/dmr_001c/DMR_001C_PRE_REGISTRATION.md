# DMR-001C - Sealed Confirmation of the Relative Drift Rule

**Type:** Pre-registered confirmatory holdout test
**Date:** August 12, 2026
**Branch:** `study/dmr-001b-adaptive-drift-formation`
**Status:** PRE-REGISTERED - NO IMPLEMENTATION IN THIS COMMIT
**Mechanism under test:** `AdaptiveEventContextFormer`, frozen at DMR-001B's
design anchor `ad6f9451a1be1519820a18f1ac1dae5dbc9ce38819671c8537061a6dc5ecc5e6`
**Corpus lock:** `artifacts/dmr001c_corpus/corpus_lock.json`, digest
`97507ddea1fc354edf92a8eae537e28c037d0286af704afeec23cff09f586ff4`, committed
at `dd621bef`

## 1. Why this one can be confirmatory

DMR-001B could not be. Both its corpora had been read by DMR-001, its locked
cell was selected from a sweep on the same data, and `DEVIATION_001` recorded
that its component was written before its registration.

None of that applies here:

- **The rule is frozen.** Every parameter was locked in DMR-001B and committed
  at `74690eda`, before this dataset existed anywhere on this machine. Nothing
  is swept, selected, or tuned in DMR-001C.
- **The corpus is new to the mechanism.** No DMR study has read LongMemEval.
  Ranks 31-40 per stratum overlap neither EC-001's registered ranks 1-20 nor
  SAL-001's 21-30.
- **This registration contains no implementation file.** Verified with
  `git show --stat` before committing, which is the corrective practice
  `DEVIATION_001` names.

The only thing DMR-001C may do is run the frozen rule once and report.

## 2. What changes, and what does not

| | DMR-001B | DMR-001C |
|---|---|---|
| Rule | percentile 0.975, window 16, warmup 16, min 5, cap 128 | **identical** |
| Corpus | 2 synthetic scripts, both already read | 50 LongMemEval haystacks, unread |
| Boundaries annotated | 96 scripted topic changes | **2,128 real session seams** |
| Session token | one per source conversation | **one per haystack** |
| Streams | 3 families | **50 independent streams** |

### 2.1 The former is blind to the seams

Each haystack is an ordered assembly of genuinely distinct conversations. The
former receives **one** stream token for the whole haystack, so the
hard-boundary predicate can never fire. Every boundary it opens is one the
drift rule detected. Source-session indices are measurement only and are never
passed to the mechanism.

This is a stricter test than either predecessor, where session changes were
handed to the former for free.

### 2.2 Known properties of the corpus, recorded before the run

Structural facts established at corpus lock. None is an outcome.

- 50 streams, 11,453 episodes, 2,178 source sessions, 2,128 seams.
- Episodes per stream: minimum 203, median 231, maximum 266.
- The seam base rate is 2,128 / 11,453 = **18.6%**, far higher than the
  synthetic corpora's 2.6%. A boundary detector firing at random will therefore
  score much better here than there, and section 4's controls exist because of
  it.
- `min_event_size` is 5 and the median source session is about 6 exchanges, so
  the rule structurally cannot recover seams that fall closer together than 5
  episodes. This is a known ceiling on recall, not a defect discovered later.
- 186 irregular sessions are excluded and reported, never repaired.
- `single-session-preference` holds only 30 items in the benchmark, all
  consumed by EC-001 and SAL-001, so it is absent from this slice. DMR-001C
  reads no answers, so strata serve topical diversity only.

## 3. Measures

- **Per-stream adaptive fire rate**: adaptive boundaries divided by episodes,
  for each of the 50 streams.
- **Stability**: the ratio of the 95th to the 5th percentile of that
  distribution. This generalizes DMR-001B's two-family swing to 50 independent
  observations and needs no annotation at all.
- **Agreement**: tolerance-1 precision, recall, and F1 against seams, computed
  per stream and macro-averaged over streams. Streams, not episodes, are the
  replication unit.
- **Event size** distribution, singleton fraction, and capped-closure count.
- Every boundary decision with its causal input hashes.

## 4. Arms

| Arm | Rule |
|---|---|
| `T_ADAPT` | The frozen DMR-001B rule |
| `C_PAIR` | Every episode its own event |
| `C_PERIODIC_k` | Every k-th episode, `k` in 2, 4, 5, 6, 8, 16, 32 |

`C_PERIODIC_5` and `C_PERIODIC_6` are included deliberately: the median source
session is about 6 exchanges, so fixed chopping near that period is the
strongest naive competitor this corpus admits. A treatment that cannot beat it
has not earned a boundary claim, however good its raw F1 looks against an
18.6% base rate.

There is no `C_SESSION` arm. The former is blind to sessions, so a
session-boundary control would be an oracle rather than a competitor; the seam
set is the annotation, not an arm.

## 5. Binding gates

Stop at the first failure.

| Gate | Binding bar | Failure disposition |
|---|---|---|
| **G1 Integrity** | Dataset hash, corpus digest, and cache coverage reproduce; two fresh processes give identical snapshot digests; malformed and acausal inputs raise; no import path from the mechanism to keys, rubrics, readers, packers, or scorers; no generation call; the DMR-001B design anchor is unchanged | `INTEGRITY_STOP` |
| **G2 Partition** | Every episode in exactly one event at one position; positions contiguous from 0; append order preserved | `PARTITION_VIOLATION` |
| **G3 Nondegeneracy** | Macro singleton fraction <= 0.20; capped closures == 0 across the corpus; the claimed-boundary set is not identical to `C_PAIR` or any `C_PERIODIC_k` on any stream | `DEGENERATE_FORMATION` |
| **G4 Stability** | The p95/p05 ratio of per-stream fire rate is <= 2.0, and no stream records zero adaptive boundaries | `NO_TRANSFER` |
| **G5 Boundary evidence** | Macro F1 at tolerance 1 exceeds the best `C_PERIODIC_k` macro F1 by at least 0.05, and macro precision is at least 0.30 | `NO_BOUNDARY_EVIDENCE` |

G4 is the claim DMR-001B earned the right to test and is the primary gate. G5
is secondary and is expected to be the harder of the two on this corpus, for
the base-rate and `min_event_size` reasons in section 2.2.

### 5.1 Reachability

No treatment value is known, which is what makes this a holdout. Reachability
is therefore mechanical rather than empirical, and is demonstrated on synthetic
fixtures in preflight:

- Fire rate lies in [0, 1] and the p95/p05 ratio is >= 1 by construction, so
  the 2.0 bar is attainable and a rule with unstable firing exceeds it.
- Macro F1 spans [0, 1]; a fixture whose boundaries equal the seams reaches
  1.0, and one that never fires reaches 0.
- Precision 0.30 is attainable: `C_PAIR` alone reaches 0.186 on this corpus's
  base rate, so a bar of 0.30 requires genuine selectivity.
- Failure is reachable: DMR-001's fixed rule is not run here, but its swing on
  the synthetic corpora was 9x to infinite against this same statistic.

## 6. Preflight

PF1-PF10 execute into `artifacts/dmr001c_preflight/preflight.json`. PF3 must
show this registration commit contains no file under `src/` or `tests/`, which
is the check `DEVIATION_001` failed. PF7 must re-prove the feedback loop
non-absorbing on this corpus: the rule's own boundaries change which drifts
enter its history, and that has only ever been shown on two synthetic scripts.

## 7. Surrogate audit

| Observed pass | Property that can remain false | Control or residual |
|---|---|---|
| Low p95/p05 ratio | The rule transfers generally | 50 streams from one benchmark, partly synthetic in construction |
| High F1 against seams | Real event structure was found | The 18.6% base rate flatters any frequent firer; the periodic arms bound this |
| Beats periodic controls | The boundaries are useful | No retrieval is measured; usefulness remains DMR-002's question |
| Seams are real | Seams are event boundaries a person would mark | A haystack is an assembly, so a seam is a real conversation change but not a natural continuous experience |
| Cap never binds | Event size is controlled | Shown on this corpus only |

## 8. Exclusions

No answer, evidence marker, question text, or date is read by any mechanism or
measurement path in this study. No retrieval, ranking, packing, reader call,
ablation, live run, promotion, or adoption. Neither `event_context.py` nor
`adaptive_event_context.py` is modified. A failed gate is a completed negative
result, and no parameter may be retuned in response to one.

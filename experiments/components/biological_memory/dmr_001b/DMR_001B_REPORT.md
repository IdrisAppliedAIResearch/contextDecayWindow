# DMR-001B Report - Adaptive Drift Event Formation

**Pre-registration:** `DMR_001B_PRE_REGISTRATION.md`, SHA-256 (LF-normalized)
`ad6f9451a1be1519820a18f1ac1dae5dbc9ce38819671c8537061a6dc5ecc5e6`, committed
at `74690eda`
**Predecessor:** DMR-001, stopped at G3, `DEGENERATE_FORMATION`
**Disposition:** `ADAPTIVE_FORMATION_TRANSFERS_OFFLINE` - G1 to G5 all pass
**Outcome ceiling:** `CHARACTERIZED`. **This does not unblock DMR-002.**
**Deviation:** `DEVIATION_001_implementation_preceded_registration.md`

## 1. Result

| Gate | | |
|---|---|---|
| G1 Integrity | PASS | |
| G2 Partition | PASS | |
| G3 Nondegeneracy | PASS | cap never bound, 0 singletons |
| G4 Transfer stability | PASS | all five percentile cells inside 2.0x |
| G5 Improvement over predecessor | PASS | worst family 0.487 against 0.419 |

| Family | Events | Fire rate | Capped | P | R | F1 |
|---|---|---|---|---|---|---|
| 1,000-turn | 65 | 3.15% | **0** | 0.462 | 0.789 | 0.583 |
| 121-turn | 90 | 4.49% | **0** | 0.433 | 0.557 | 0.487 |
| 30-turn | 2 | 3.33% | **0** | 0.500 | 0.200 | 0.286 |

## 2. What was fixed

**The transfer failure.** DMR-001's fixed threshold moved its operating point
by 10x between corpora. Every percentile in the registered grid holds inside
2.0x:

| Percentile | Swing |
|---|---|
| 0.80 | 1.48x |
| 0.85 | 1.59x |
| 0.90 | 1.61x |
| 0.95 | 1.65x |
| 0.975 | 1.42x |

This is the primary gate and it is deliberately about the rule family rather
than the locked cell. One cell can be cherry-picked; five spanning the grid
cannot. The predecessor's fixed rule fails the same bar at 9x to infinity, so
the gate discriminates.

**The cap capture.** DMR-001 had 70.3% of its holdout events closed by the size
cap. Here the cap is 128 and **never bound once** across 3,724 episodes; the
largest event was 84. The guard is inert, which is what a guard should be.

## 3. What was not fixed, and one honest trade

**Precision is still poor**: 0.462 and 0.433. Roughly half of claimed
boundaries are not annotated ones. Nothing here makes the detector accurate; it
makes it stable.

**The 1,000-turn family got worse.** Under identical claims-only accounting the
predecessor scored 0.733 there against this rule's 0.583. The improvement is on
the *worst* family (0.419 to 0.487) and on cap independence, not everywhere.
G5's bar was written on the worst family precisely because a rule that wins on
one corpus and collapses on another is the failure being fixed - but the trade
should not be reported as a clean win.

**A degenerate input is reachable and no bar detects it.** Found by the test
suite, not by the preflight: on a stream with no drift variance, `drift >= the
97.5th percentile of drift` is true as soon as the history is warm, so the rule
fires whenever `min_event_size` is met. This is correct per the registered
`>=` comparison and is the price of removing the absolute constant - with no
scale of its own, the rule has nothing to say about a stream with no variance.
Neither corpus reaches it. A real conversation of near-identical turns would,
and PF7 did not catch it because PF7 runs on real data. Recorded, not repaired:
changing the comparison after results is not available.

## 4. The accounting change, and the obligation it creates

Not counting cap closures as boundary claims lifted the predecessor's measured
1,000-turn F1 from 0.393 to 0.733 and its precision from 0.297 to 1.000. That
is a large effect from a record-type change alone, and it is honest **only if
downstream honors it**.

Any stage consuming this map must refuse to treat a `capped` chunk as a
detected event. With the cap inert there are currently no such chunks, so the
obligation costs nothing today - but it must be carried into DMR-002 or the
precision figure becomes fiction.

## 5. Standing

Two independent reasons this is not confirmatory:

1. **No sealed holdout.** Both corpora were read by DMR-001. Under arc
   invariant 7 they are development sets. The locked cell was selected from the
   Part 1 sweep on the same data, so its own numbers are fitted.
2. **DEVIATION_001.** The component was written before the pre-registration and
   both were committed together, so git order cannot demonstrate the design was
   fixed first. PF3 reports FAILED rather than being redefined. The specific
   hazard - back-filling a design to match an observed outcome - did not occur,
   because no gate result existed when either file was written and the
   parameters came from the committed Part 1 artifact. A reader is still
   entitled to discount the ordering guarantee.

## 6. What this licenses

One thing: **seeking a sealed corpus** on which the relative rule could be
confirmed. The swing statistic is the reason to bother - it is measurable on
any new corpus without annotations, gets stronger as corpora are added, and
directly tests the property that failed.

It does not license DMR-002, any retrieval or reader claim, an ablation, a live
run, a promotion, or an adoption. DMR-001's stop stands; the arc remains
blocked at stage 1.

## 7. Artifacts

| Artifact | Path |
|---|---|
| Part 1 sweep, 100 configurations | `exploration/DMR_001B_PART1_EXPLORATION.json` |
| Pre-registration | `DMR_001B_PRE_REGISTRATION.md` |
| Design lock | `DMR_001B_FINAL_DESIGN.json` |
| Deviation record | `DEVIATION_001_implementation_preceded_registration.md` |
| Preflight PF1-PF10 | `artifacts/dmr001b_preflight/preflight.json` |
| Gate report | `artifacts/dmr001b_gates/gate_report.json` |
| Component | `src/biological_memory/adaptive_event_context.py` |
| Verification contract | `tests/test_dmr001b_adaptive_event_context.py` |

# DMR-001B - Adaptive Drift Event Formation

**Type:** Pre-registered write-path diagnostic
**Date:** August 12, 2026
**Branch:** `study/dmr-001b-adaptive-drift-formation`
**Status:** PRE-REGISTERED - NO IMPLEMENTATION IN THIS COMMIT
**Predecessor:** DMR-001, stopped at G3, `DEGENERATE_FORMATION`
**Part 1 record:** `exploration/DMR_001B_PART1_EXPLORATION.json`
**Corpus:** DMR-001's lock, unchanged, digest
`be939cbebc0e9e9f33906ffc92047e114372852bbc578bb4376efd0e061d3bf9`
**Outcome ceiling:** `CHARACTERIZED`. **This study cannot unblock DMR-002.**

## 1. What this study can and cannot be

Both corpora were read by DMR-001. Under the arc's non-negotiable invariant 7,
existing known corpora are diagnostic development sets and confirmatory claims
require a newly locked sealed holdout. There is no sealed holdout here and none
is manufactured.

So DMR-001B asks one question, and it is not "is this good":

> Does making the boundary bar relative to the conversation's own recent drift
> remove the cross-corpus transfer failure that stopped DMR-001, without
> reintroducing degeneracy?

A pass licenses one thing: seeking a sealed corpus on which the rule could be
confirmed. It does not license DMR-002, a retrieval claim, a reader call, an
ablation, or an adoption.

## 2. The one component

`src/biological_memory/adaptive_event_context.py`,
`AdaptiveEventContextFormer`. DMR-001's `event_context.py` is not modified; its
float32 arithmetic, normalization, and vector hashing are imported so a
comparison cannot turn on numerics.

Two changes from DMR-001, and nothing else.

### 2.1 The bar is relative

```text
history      = the last `history_window` drift values observed in this session
threshold_t  = percentile(sorted(history), drift_percentile)   when |history| >= warmup
             = infinity                                        otherwise
adaptive     = n_(t-1) >= min_event_size and |history| >= warmup and d_t >= threshold_t
```

Drift history resets at a session boundary. Drift scale is a property of one
conversation; carrying it across a session would reintroduce exactly the
transfer failure being fixed.

Percentile interpolation is implemented in the component rather than taken from
a library, so a NumPy or SciPy convention change cannot silently move a
boundary.

### 2.2 Cap closures are typed, not claimed

```text
capped       = n_(t-1) >= max_event_size
new_event    = hard or adaptive or capped
claims_boundary = reason in {stream_start, hard, adaptive}
```

The cap still closes an event, so the partition shape is unchanged and this is
not a second component. What changes is the record: a cap closure is typed
`capped` and is **not** counted as a boundary the mechanism asserts. DMR-001
scored 52 arbitrary cuts as if its detector had claimed them, which dropped its
measured precision from 1.000 to 0.297.

**This is honest accounting only if downstream honors it.** Any stage that
consumes this map must refuse to treat a `capped` chunk as a detected event.
That is an obligation on DMR-002, recorded here so it cannot be forgotten.

### 2.3 Locked parameters

| Parameter | Value | Basis |
|---|---|---|
| `drift_percentile` | `0.975` | Section 3 selection rule |
| `history_window` | `16` | Section 3 selection rule |
| `warmup` | `16` | Fixed at the window; the rule may not fire on a partial history |
| `min_event_size` | `5` | Carried unchanged from DMR-001 |
| `max_event_size` | `128` | Author decision, August 12 2026. A never-should-fire guard: the largest event any relative configuration produced in Part 1 was 98, and the locked cell produced 77 |
| `rho` | `0.5` | Carried unchanged from DMR-001 |
| `boundary_tolerance` | `1` | Carried unchanged |

## 3. Selection rule, and the fact that it ran on this data

Applied to the Part 1 sweep, stated before the gates:

> Among percentile cells at `warmup` 16, choose the lowest fire-rate swing
> between the two substantive families. Break ties within 0.15x by the highest
> worst-family claimed-boundary F1.

Swings were 1.30x at window 64, 1.41x at 32, and 1.42x at 16; all three fall
inside 0.15x of the minimum, so the tie-break applies and window 16 wins on
worst-family F1 (0.487 against 0.409 and 0.386).

**This selection ran on the same corpora the gates run on.** The locked cell's
own numbers are therefore fitted, not validated, and section 5's G4 is written
to be about the rule *family* rather than the selected cell for that reason.

The 30-episode session is excluded from the swing statistic and from the
worst-family statistic. It holds 5 annotated boundaries and its F1 is identical
at 0.286 across every relative configuration, so it carries no signal and would
otherwise dominate a worst-of ranking with noise. It is still formed, still
reported, and still bound by G1, G2 and G3.

## 4. Arms

| Arm | Rule |
|---|---|
| `T_ADAPT` | The locked rule in section 2 |
| `T_DMR001` | DMR-001's fixed rule, threshold 0.70, cap 32, scored under the same claims-only accounting |
| `C_SESSION` | Session boundaries only |
| `C_PAIR` | Every episode its own event |
| `C_PERIODIC_k` | Session starts plus every k-th episode, k in 2, 4, 8, 16, 32, 64 |

`T_DMR001` is the point of the study. Without it, an improvement claim has no
referent.

## 5. Binding gates

Stop at the first failure. Evaluated on all three families unless stated.

| Gate | Binding bar | Failure disposition |
|---|---|---|
| **G1 Integrity** | Two fresh processes give identical snapshot digests; the corpus replays to the committed digest; malformed and acausal inputs raise; no import path from the mechanism to keys, rubrics, readers, packers, or scorers; no generation call; the design anchor matches the pre-registration on disk | `INTEGRITY_STOP` |
| **G2 Partition** | Every episode in exactly one event at one position; positions contiguous from 0; no event spans two sessions; append order preserved | `PARTITION_VIOLATION` |
| **G3 Nondegeneracy** | Singleton fraction <= 0.20; the cap never binds, so capped closures == 0 on every family; the claimed-boundary set is not identical to `C_PAIR`, `C_SESSION`, or any `C_PERIODIC_k` | `DEGENERATE_FORMATION` |
| **G4 Transfer stability** | For **every** percentile in the registered grid 0.80, 0.85, 0.90, 0.95, 0.975 at the locked window, the fire-rate swing between the two substantive families is <= 2.0x, and no family records zero adaptive fires | `NO_TRANSFER` |
| **G5 Improvement over the predecessor** | Under identical claims-only accounting at tolerance 1, `T_ADAPT`'s worst substantive-family F1 >= `T_DMR001`'s, and `T_ADAPT`'s capped fraction is lower on every family | `NO_IMPROVEMENT` |

G4 is the primary gate and is deliberately about the rule family, not the
locked cell. A single cell can be cherry-picked; five cells spanning the grid
cannot be, and DMR-001's fixed rule fails this same test at 9x to infinity.

### 5.1 Reachability

| Bar | Part 1 value | Reachable |
|---|---|---|
| Swing <= 2.0x, all five percentile cells | 1.48, 1.59, 1.61, 1.65, 1.42 | yes |
| No family with zero adaptive fires | minimum 2.54% | yes |
| Capped closures == 0 | largest event 77 against a cap of 128 | yes |
| Singleton fraction <= 0.20 | 0.000 | yes |
| Worst-family F1 >= predecessor | 0.487 against 0.419 | yes |

Failure is reachable: DMR-001's fixed rule scores 9.0x to infinite swing on the
same statistic, and at threshold 0.75 with no cap it produces a single event
spanning all 1,000 turns.

## 6. Preflight

Part 1 is committed at `exploration/DMR_001B_PART1_EXPLORATION.json`, 100
configurations, two-process identical. PF1-PF10 execute into
`artifacts/dmr001b_preflight/preflight.json`. PF7 owes an absorbing-state proof
this design needs and DMR-001 did not: the rule's own boundaries change which
drifts enter its history, which changes the threshold, which changes later
boundaries. That feedback loop must be shown non-absorbing on the 1,000-turn
stream.

## 7. Surrogate audit

| Observed pass | Property that can remain false | Control or residual |
|---|---|---|
| Low swing | The rule transfers | Two corpora, both synthetic, both already read. Swing on a third corpus is unknown and is the whole point of seeking one |
| Claims-only precision rises | The mechanism improved | It partly reflects not scoring cap closures. With the cap inert there are none, but the accounting change must be honored downstream or the number is fiction |
| Worst-family F1 beats DMR-001 | The boundaries are better | Agreement is measured against a scripted topic schedule, not human judgment |
| Cap never binds | Event size is controlled | It is controlled on these two corpora; a corpus with lower drift variance could still reach 128 |
| Nondegeneracy passes | The partition is useful | No retrieval is measured here at all |

## 8. Exclusions

No retrieval, ranking, packing, reader call, ablation, live run, promotion, or
adoption. No answer is scored. `event_context.py` is not modified. A failed
gate is a completed negative result.

# DMR-001 Report - Online Event-Context Formation

**Pre-registration:** `DMR_001_PRE_REGISTRATION.md`, SHA-256 (LF-normalized)
`f563b6c5f9a98413b3a00135600f6d4dc3f9203242190d30c2bf0b2e03d28c41`, committed
at `33ed8c5d`
**Design lock:** `DMR_001_FINAL_DESIGN.json`
**Branch:** `study/dmr-001-event-context-formation`
**Date:** August 12, 2026
**Disposition:** `DEGENERATE_FORMATION` - **G3 FAIL, stopped at G3**
**Outcome ceiling honored:** CHARACTERIZED. No retrieval, reader, ablation,
live run, promotion, or adoption occurred.

## 1. Result

The locked online drift rule does not produce a usable event substrate.

| Gate | Outcome |
|---|---|
| G1 Integrity | PASS |
| G2 Partition | PASS |
| G3 Nondegeneracy | **FAIL** |
| G4 Boundary evidence | not evaluated |
| G5 Context separation | not evaluated |

Because DMR-001 stops, **DMR-002 through DMR-006 are blocked**: the arc has no
validated event substrate to build on.

## 2. What failed

Two G3 checks failed. They are not equally sound and are reported separately.

### 2.1 The decisive failure: the size cap does the partitioning

On the 2,000-episode holdout, 52 of 74 events close because `max_event_size`
binds. Forced fraction **0.703** against a bar of **0.35** that PF4 verified
reachable at 0.005 on development.

The forced boundary was registered as "a safety bound, not a scientific event
claim". On the holdout it is the primary partitioner, which makes the formed
partition fixed 32-chunking wearing the mechanism's name. That is exactly the
degeneracy G3 exists to catch.

### 2.2 The unsound failure: a bar PF4 never checked

Development largest-event share **0.767** against a bar of **0.25**. One event
held 23 of the 30 episodes in the shortest selected session.

PF4 verified the singleton and forced-fraction bars reachable and never
verified this one. It is unreachable by construction: with `max_event_size` 32,
any session shorter than 128 episodes violates a 25% share the moment a single
event reaches the cap, and 15 of the 17 selected sessions are shorter than
that. The bar is a preflight defect.

**The defect is recorded, not repaired.** The bar is not loosened after seeing
the result, and the disposition does not depend on it: the holdout
forced-fraction check fails independently, so G3 fails and the disposition is
`DEGENERATE_FORMATION` with or without this check.

## 3. Why it failed

Post-stop characterization
(`artifacts/dmr001_gates/post_stop_characterization.json`, descriptive only).

**The drift predicate is precise when it fires and it barely fires.**

| Split | Drift boundaries | Matched | Drift precision | Forced boundaries | Matched |
|---|---|---|---|---|---|
| Development | 176 | 41 | 0.233 | 1 | 0 |
| Holdout | 20 | 20 | **1.000** | 52 | **0** |

On the holdout every one of the 20 drift boundaries landed on an annotated
boundary within tolerance, and not one of the 52 forced boundaries did.

**The drift statistic has no transferable scale.**

| Split | Drift median | p95 | max | Eligible episodes at or above 0.70 |
|---|---|---|---|---|
| Development | 0.602 | 0.877 | 0.988 | 178 / 961 (18.5%) |
| Holdout | 0.362 | 0.626 | 0.799 | 20 / 1,703 (1.2%) |

The locked threshold of 0.70 sits above the holdout's 95th percentile. The same
number that fires on nearly a fifth of eligible development episodes fires on
one in eighty-five holdout episodes. A threshold calibrated on one conversation
does not carry to another, and when it under-fires the safety cap silently
takes over.

This is the mechanism's failure, not the corpus's bad luck: the rule offers no
way to know, online and label-blind, which regime it is in.

## 4. What passed

**G1 Integrity.** Two fresh processes produced identical snapshot digests. The
frozen corpus replayed to the committed digest
`be939cbebc0e9e9f33906ffc92047e114372852bbc578bb4376efd0e061d3bf9`. Every
registered malformed or acausal input raised. A clean interpreter importing the
mechanism reaches only `src.biological_memory`; no key, rubric, reader, packer,
or scorer is on any import path, and the module makes no completion, chat, or
response call. The design anchor still matches the pre-registration on disk.

**G2 Partition.** All 3,724 episodes appear exactly once, positions are
contiguous from zero in every event, no event spans two sessions, and event
order is append order.

**PF1-PF10 all pass** (`artifacts/dmr001_preflight/preflight.json`). PF2 is
worth naming: the locked component and the Part 1 exploratory implementation
were written independently and agree on every decision, drift value, event
position, prototype hash, and context hash across 1,724 development
episodes - 0 mismatches.

## 5. Post-stop, descriptive only

G4 and G5 were computed but **not evaluated as gates**, and must not be cited
as results. Both would have cleared their bars:

- G4: holdout T_EVENT F1 0.393 at tolerance 1, against C_SESSION 0.100 and the
  best periodic control 0.114; recall 0.579, precision 0.297.
- G5: holdout context AUC 0.970 against a raw-vector control of 0.900; every
  session at or above 0.970.

Reading these as a partial success would be a mistake, and the post-stop table
in section 3 is why. T_EVENT's F1 advantage comes almost entirely from its 20
drift boundaries and 1 hard boundary; the 52 forced boundaries contributed
nothing. A boundary-agreement score can look good while 70% of the formed
events are arbitrary - which is the surrogate PF9 predicted and G3 caught.

## 6. Registered revisions and their residuals

Three revisions to the implementation specification were forced by Part 1 and
recorded in the pre-registration rather than by editing the spec.

1. **Episode identity carries stream position.** 1,995 of 3,724 episodes are
   exact content duplicates, so text alone cannot satisfy the schema's
   `UNIQUE`.
2. **The session token is minted by the corpus lock.** First episodes are not
   unique across the corpus. Residual: in this offline replay the token derives
   from the session's complete content, so `event_id` inherits a whole-session
   content dependency. It does not depend on future members *of the event* and
   never mutates, but a live session-token mint is not demonstrated.
3. **Boundary annotation is corpus provenance.** No human annotators are
   available and the spec forbids a model judge, so the committed
   `ground_truth_domain` schedule is the annotation. Residual: G4 would have
   certified agreement with a scripted topic schedule, not psychological
   validity.

## 7. Limitations

- **The corpus is synthetic.** Both scripts are internal study corpora. The
  1,000-turn endurance script has only 156 distinct user-plus-assistant pairs
  across 1,000 episodes: roughly 11 substantive turns per topical block plus
  about 70 exact repeats of a "stay within the X thread" filler prompt. This
  was not previously recorded anywhere in the program and it shapes every
  holdout number here.
- **The holdout is not two independent conversations.** Its two realizations
  share all user text and differ only in assistant text.
- **One platform.** Every reduction routes through `math.fsum` rather than
  BLAS, which removes the usual cross-platform hazard, but no second platform
  was executed and no cross-platform claim is made.
- **No retrieval verdict of any kind.** DMR-001 measured formation only.
- **A preflight defect shipped.** See section 2.2. PF4 checked bar
  reachability for some G3 bars and not others.

## 8. What this does and does not license

DMR-001 stops. Per the governing design's section 12, the arc records that
deterministic embedding-change event formation is not a valid substrate on this
evidence. The biological event-segmentation literature is untouched; this
engineering translation of it is rejected.

Do not retune the threshold, widen the tolerance, change the aggregator, or
swap the corpus and rerun. Any successor is a new design with its own
pre-registration, and it must confront the finding in section 3: an absolute
drift threshold is not a transferable quantity. A rule that adapted to the
stream's own drift distribution, or that removed the size cap's ability to
masquerade as a boundary, would be a different mechanism and a new study.

## 9. Artifacts

| Artifact | Path |
|---|---|
| Corpus lock | `artifacts/dmr001_corpus/corpus_lock.json` |
| Part 1 exploration | `exploration/DMR_001_PART1_EXPLORATION.json` |
| Pre-registration | `DMR_001_PRE_REGISTRATION.md` |
| Design lock | `DMR_001_FINAL_DESIGN.json` |
| Preflight PF1-PF10 | `artifacts/dmr001_preflight/preflight.json` |
| Gate report | `artifacts/dmr001_gates/gate_report.json` |
| Post-stop characterization | `artifacts/dmr001_gates/post_stop_characterization.json` |
| Component | `src/biological_memory/event_context.py` |
| Verification contract | `tests/test_dmr001_event_context.py` |
| Study harness tests | `tests/test_dmr001_study.py` |

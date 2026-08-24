# TC-004 Exploration — selective splitting can be tested without opening the transfer result

**Status:** `PREFLIGHT PART 1 + PF4 COMPLETE — DESIGN NOT LOCKED — NO STUDY IMPLEMENTATION`
**Date:** August 22, 2026
**Artifacts:** `artifacts/tc004/preflight/tc004_preflight_part1.json`,
`artifacts/tc004/preflight/tc004_locomo_split_inventory.json`
**Calls:** zero embedding calls, zero generation calls, zero cache misses

**Author clarification:** “Model-free refers to no LLM calls, we don't count
the embedding model as a model in this context.” The embedding-localization
score governs the proposed registration; the lexical score is an ablation.

## Behavioral identity

A split replaces one aggregate candidate and its aggregate cosine with its exact
source turns, each independently ranked, then lets split children and unsplit
parents compete in one skip-on-overflow character pack. It does not duplicate
the parent, truncate either child, or reduce the stored text by declaration.

The author clarified after the first exploration commit that **“model-free” in
this arc means no LLM calls; the embedding model does not count as a model in
this context.** The proposed score is therefore `embedding_localization_gain`:
maximum child/query embedding cosine minus parent/query embedding cosine.
Parent character length is the required baseline. A lowercase token-count
version remains an ablation, not the proposed mechanism.

## Part 1 proof of mechanism on LongMemEval

The exact NF-005 population supplies 465 questions, 106,412 parent episodes,
and 212,824 source-turn occurrences. The mixed-store implementation reproduces
both committed endpoints:

| Granularity | Any exact evidence | All exact evidence |
|---|---:|---:|
| no parents split | 351 / 465 | 201 / 465 |
| every parent split | 461 / 465 | 454 / 465 |

The any-evidence contrast is 110 gains and 0 losses. All stores exceed the
32,000-character budget. Zero-split and all-split selections converge exactly
across every policy, so differences between them arise only in which parents a
policy splits.

### The predictor-level endpoint

A parent is labelled beneficial only when replacing that parent alone changes
its question from no exact evidence delivered to some exact evidence delivered.
There are 213 such parent/query cases across 110 questions; 19 replacements are
harmful. Average precision is computed within each question, because the policy
ranks candidates within a store rather than calibrating scores across stores.

| Split-order score | Mean AP | vs length, questions better / worse | Mean AP delta |
|---|---:|---:|---:|
| parent length | .053 | — | — |
| lexical localization gain | .233 | 77 / 33 | +.180 |
| embedding localization gain | .542 | 101 / 9 | +.489 |
| maximum child embedding cosine | .509 | 102 / 8 | +.456 |

Both deterministic statistics beat length on this development population. The
embedding score is the stronger and author-consistent mechanism; the lexical
score's one-sided exact sign *p* is 1.65 × 10⁻⁵. These are exploratory numbers,
not TC-004 results or bars.

### The operational-store check

Candidate-level AP can pass while false-positive splits of distractors damage
the packed store. The artifact therefore applies each policy to every candidate
at matched split rates. Lexical localization beats length by 30–32 questions at
1–5% split rates and by 13 at 20%, is nearly tied at 30%, then loses by 12 at
50% and 9 at 75%. The statistic is useful as a selective rule, not as evidence
that more splitting is always better.

The proposed embedding localization score beats length by 75–76 questions at
1–5% and by 39 at 20%. The lexical ablation is weaker at every selective rate.

## Unopened LoCoMo transfer population

The roadmap's second qualifying corpus provides a clean prospective transfer of
the mechanism without claiming a sealed corpus. The four development
conversations contain 871 unique nonduplicate questions with resolved evidence,
1,365 adjacent-pair parents, and 1,297 two-turn parents that can actually split.
Parent text has median 237 characters; child text has median 114.

The lexical ablation is nonconstant over 285,185 question/parent cases.
Its median is .0087, p10 is −.0245, and p90 is .0551. Sixty-eight singleton
pairs cannot split and remain parents under every policy.

The transfer outcome is not open. Of 2,660 unique child texts, only the 68
singleton texts already exist in the retained development cache; **2,592 child
vectors are absent**. A LoCoMo pair-to-turn study can therefore lock its
statistic, endpoint, bars, exact renderer, budget, and vector-capture contract
before the treatment rankings can exist.

## PF4

The exact mixed renderer reduces to committed `A_FLAT` with zero splits on all
868 complete-evidence questions at both 16,000 and 32,000 characters. This
caught and corrected one pre-lock float32 call-shape mismatch: row-wise dot
products can reorder a near tie relative to the carried matrix-vector call.

With child scores set only as an oracle positive control—not as the proposed
predictor—99 primary-budget questions can express a beneficial one-parent
split and 749 can express a harmful one. At 32,000 the corresponding counts are
44 and 810. The `WORKS` example (6 gains/0 losses, one-sided *p*=.015625),
`CARRIES_SIGNAL` example (4/1, *p*=.1875), and no-signal example (1/1,
*p*=.75) are all mechanically reachable. Actual child vectors, benefit labels,
predictor AP, and direction remain unopened.

## Degenerate states and surrogate audit

- There is no feedback and therefore no absorbing retrieval state.
- Zero and full splitting erase every policy difference; neither can test a
  selector.
- Singleton parents cannot express the treatment and must not count as
  predictor trials.
- Lexical score ties exist and require a frozen source-order tie-break.
- Candidate-only precision can pass while the full-store policy loses; a
  registered operational availability check is required.
- Exact evidence delivery can pass while the reader cannot use it. TC-004 can
  establish availability prediction only; TC-006 owns the reader.
- Pair-to-turn splitting changes semantic localization, rank unit, renderer
  overhead, and packing granularity together. It does not identify raw length
  as the sole cause.

## Recommended registration, not yet locked

Use LoCoMo development for a `REGISTERED-OFFLINE` transfer characterization:

1. Parent candidates are the committed adjacent pairs; children are their exact
   speaker-labelled dialogue turns. Singleton parents remain unsplit.
2. The proposed score is `embedding_localization_gain`; the control is parent
   length. Both are computed before candidate ranking and neither reads
   evidence. `lexical_localization_gain` is a descriptive ablation.
3. New child vectors are captured only after registration with the pinned
   exact-solo embedder, sealed, and reopened read-only. Unsplit parents use the
   retained pair vectors; split children use their own vectors.
4. The predictor endpoint is within-question average precision for beneficial
   leave-one-parent-out splits versus length. The operational check applies both
   policies to the complete store at matched split effort, so distractor cost
   remains visible.
5. Carry `A_FLAT`, `A_DUAL`, and `A_DUAL_RANKED` unchanged and descriptively, as
   roadmap §1.1 requires. No standing-arm contrast is needed to answer the
   predictor question.

The author's instruction to begin TC-004 and subsequent definition of
“model-free” authorize the embedding-based mechanism. PF4 and the registration
still precede treatment-vector capture and any outcome.

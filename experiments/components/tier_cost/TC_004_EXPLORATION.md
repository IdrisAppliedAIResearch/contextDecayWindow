# TC-004 Exploration — selective splitting can be tested without opening the transfer result

**Status:** `PREFLIGHT PART 1 COMPLETE — DESIGN NOT LOCKED — NO STUDY IMPLEMENTATION`
**Date:** August 22, 2026
**Artifacts:** `artifacts/tc004/preflight/tc004_preflight_part1.json`,
`artifacts/tc004/preflight/tc004_locomo_split_inventory.json`
**Calls:** zero embedding calls, zero generation calls, zero cache misses

## Behavioral identity

A split replaces one aggregate candidate and its aggregate cosine with its exact
source turns, each independently ranked, then lets split children and unsplit
parents compete in one skip-on-overflow character pack. It does not duplicate
the parent, truncate either child, or reduce the stored text by declaration.

The proposed literal model-free score is `lexical_localization_gain`: maximum
child/query lowercase token-count cosine minus parent/query lowercase
token-count cosine. It has no learned weights, vocabulary, corpus statistic, or
model call. Parent character length is the required baseline.

An embedding localization score — maximum child/query embedding cosine minus
parent/query embedding cosine — is also characterized. It is deterministic and
available from retained vectors on LongMemEval, but it is not “model-free.” A
registration using it would have to change the roadmap's name rather than
silently treating “no new call” as “no model.”

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

The literal model-free statistic beats length on this development population:
one-sided exact sign *p* = 1.65 × 10⁻⁵. That number is exploratory, not a
TC-004 result and not a bar.

### The operational-store check

Candidate-level AP can pass while false-positive splits of distractors damage
the packed store. The artifact therefore applies each policy to every candidate
at matched split rates. Lexical localization beats length by 30–32 questions at
1–5% split rates and by 13 at 20%, is nearly tied at 30%, then loses by 12 at
50% and 9 at 75%. The statistic is useful as a selective rule, not as evidence
that more splitting is always better.

The embedding localization score is stronger, beating length by 75–76 questions
at 1–5% and by 39 at 20%. That difference is descriptive because the literal
model-free and embedding-conditioned questions are different mechanisms.

## Unopened LoCoMo transfer population

The roadmap's second qualifying corpus provides a clean prospective transfer of
the mechanism without claiming a sealed corpus. The four development
conversations contain 871 unique nonduplicate questions with resolved evidence,
1,365 adjacent-pair parents, and 1,297 two-turn parents that can actually split.
Parent text has median 237 characters; child text has median 114.

The literal lexical score is nonconstant over 285,185 question/parent cases.
Its median is .0087, p10 is −.0245, and p90 is .0551. Sixty-eight singleton
pairs cannot split and remain parents under every policy.

The transfer outcome is not open. Of 2,660 unique child texts, only the 68
singleton texts already exist in the retained development cache; **2,592 child
vectors are absent**. A LoCoMo pair-to-turn study can therefore lock its
statistic, endpoint, bars, exact renderer, budget, and vector-capture contract
before the treatment rankings can exist.

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
2. The proposed score is literal `lexical_localization_gain`; the control is
   parent length. Both are computed before ranking and neither reads evidence.
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

This is a recommendation from exploration, not authorization to choose the
corpus, endpoint, effect bar, or lower disposition. Those remain author choices
before PF4 and pre-registration.

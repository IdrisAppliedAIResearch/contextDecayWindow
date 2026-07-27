# Scoring Integrity Audit - Locked Pre-Registration

**Program:** contextDecayWindow  
**Type:** remediation audit, outside the study numbering  
**Locked:** 2026-07-26  
**Trigger:** `experiments/study_009/analysis/breadth_regression_audit.md`

## Purpose

Audit every scored arm in Studies 001-009 for answer completeness, mechanical
fact support, score/rationale consistency, and downstream verdict impact. Original
artifacts are preserved. Corrections are additive and versioned.

The rubric, scripts, and preserved conversational data are out of scope for
modification. No model inference against the study runtime is permitted. Nothing
under `experiments/study_010/` may be read, written, hashed, contacted, restarted,
or reconfigured.

## Scope

Layer 1 includes every scored arm with preserved answers and committed scores:

- Study 001: iterative, full-context, compaction; reported separately because its
  rubric differs.
- Study 002: iterative (C), full-context (A), compaction (B).
- Study 003: accepted run.
- Study 004: treatment and v3 control.
- Study 005: treatment and promotion control.
- Study 006: treatment and control.
- Study 007: treatment and control.
- Study 009: L and S.

Study 008 produced no scores and is out of scope. Study 010 is wholly excluded.

## Ordering Lock

1. Commit this methodology, variants, seeds, rater configuration, calibration
   cases, and decision record.
2. Commit Q11/Q14 guidance derived from locked criteria only.
3. Open preserved answers and run Layer 1; commit its outputs.
4. Prepare and commit a sealed, anonymized Layer 2 corpus mapping.
5. Run three blind AI passes and commit them before unsealing.
6. Compute and commit H1-H5 triggers.
7. Run independent clean-context adjudication for H4/H5 before revealing AI or
   Layer 1 evidence; adjudicate H1-H3 with conflicts visible.
8. Unseal, cascade corrections, publish errata, and install enforcement.

The audit designer knew the triggering Study 002 C Q11 defect from the diagnostic
that caused this audit. That prior knowledge is disclosed, not treated as blind.
Variants, guidance, sampling, and the blind rater packets are fixed independently
of preserved answer wording.

## Layer 1

For every expected scored item, record:

- artifact readability and SHA-256 before and after;
- empty/whitespace-only status;
- reasoning-block balance;
- whether scoreable content exists outside reasoning blocks;
- generation-cap or mid-sentence truncation indicators;
- `NO_ANSWER` classification;
- per-fact normalized string presence using the committed variants;
- original score and rationale availability;
- flags:
  - F1: score above zero on `NO_ANSWER` or truncated output;
  - F2: rationale claims a fact absent from mechanical evidence;
  - F3: rationale claims domain coverage contradicted by evidence;
  - F4: score contradicts the rubric threshold;
  - F5: rationale missing.

Only content outside a reasoning block is scoreable. `NO_ANSWER` scores 0.0.
Truncation at a probe is a protocol deviation and is never scored around.

## Layer 2

The AI rater receives only anonymized item ID, scoreable answer text, question,
locked criteria, and the precommitted guidance. It never receives arm/study
identity, prior score/rationale, Layer 1 output, or mechanism logs.

Three independent clean-context passes use shuffled orders. Every pass returns a
score and answer-grounded rationale. Self-disagreement triggers adjudication.

The corpus contains every F1-F5 item, every Q11/Q14 item, and a deterministic 15%
sample of otherwise unflagged items.

## Adjudication Triggers

- H1: AI conflicts with Layer 1.
- H2: three AI passes disagree.
- H3: AI differs from the original by at least 0.5.
- H4: every Q11/Q14 item.
- H5: deterministic 10% sample of self-consistent items where AI and original
  agree.

For H4/H5, adjudication occurs in clean context before AI scores or Layer 1
evidence are revealed. For H1-H3, the conflict is visible.

### Authorized Amendment: Adjudicator Class

The author explicitly authorized a clean-context subagent as adjudicator on
2026-07-26. This is an independent AI adjudicator, not a human, and reports must
not call it human. This amends the draft's human-adjudicator requirement while
retaining blinding, independent-before-reveal ordering, written rationales, and
adjudicator precedence. The residual limitation is reported prominently.

## Fixed Decisions

- H5 rate: 10%.
- AI pass count: 3.
- H3 threshold: absolute delta >= 0.5.
- Unflagged control rate: 15%.
- Control seed: `sia-control-2026-07-26-v1`.
- H5 seed: `sia-h5-2026-07-26-v1`.
- Study 001 included in Layer 1 and reported separately.
- Study 002 A/B included in Layer 1 and routed to Layer 2 when selected or flagged.
- Escalate to full re-score when the control-sample disagreement rate is at least
  half the flagged-set disagreement rate.
- Study 003 Bar 2: the literal `overall >= 13.0` governs. Corrected-baseline
  non-regression is reported separately and cannot alter the verdict.

## Cascade

Corrected values use precedence: independent adjudicator, then three-pass AI
consensus, then original. Recompute every per-arm total, category subtotal,
cross-study score reference, confirmatory bar, and headline verdict.

Study 003 remains FAIL on literal Bar 2 if its score remains below 13.0 even when
it equals a corrected Study 002 baseline. This deliberately rejects the more
favorable post-hoc intent reading. The ambiguity demonstrates why cross-study
references must cite an artifact SHA and be recomputed when that artifact changes.

## Publication

- Never overwrite original score or response artifacts.
- Publish corrected scores alongside originals with provenance.
- Add correction banners to affected reports while preserving original claims.
- Index every correction and changed verdict in root `ERRATA.md`.
- Report gaps rather than estimate missing evidence.

## Acceptance

- 100% Layer 1 coverage or explicit gaps.
- Pre-answer commit ordering preserved.
- Calibration gate passed, including `NO_ANSWER = 0`.
- Three-pass consistency and all trigger counts reported.
- Every H4/H5 item independently adjudicated before reveal.
- Every corrected score records its basis.
- All bars and cross-study references recomputed.
- Completeness and rationale-consistency checks enforced by tested tooling.


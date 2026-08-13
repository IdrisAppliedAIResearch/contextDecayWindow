# Ranking and Budget Development Control Plan

**Document type:** Pre-outcome control specification
**Status:** `LOCK BEFORE IMPLEMENTATION OR OUTCOMES`
**Corpora:** LoCoMo development; exhausted LongMemEval development
**Model calls:** 0 planned
**Embedding calls:** 0 planned
**Date:** August 13, 2026

## 1. Questions

This plan answers three development-only questions before any LoCoMo holdout
registration is written:

1. Does source-order packing match LoCoMo's high 32k ranked baseline, making the
   apparent ranking effect a slack-budget artifact?
2. At what budget is LoCoMo's session-ranked baseline discriminating rather
   than near ceiling?
3. Does the sign of ranking granularity vary with the store-to-budget
   oversubscription ratio on LoCoMo or LongMemEval development?

No result from these controls receives a study disposition. Every cell is
reported; no budget is selected and then described as if fixed prospectively.

## 2. Frozen arms

All arms use identical adjacent-turn pair candidates and exact candidate-text
character costs. Odd final turns remain singleton candidates. Packing is
skip-on-overflow: a candidate that does not fit is skipped and scanning
continues.

LoCoMo arms:

- `SOURCE`: pairs in corpus source order; no query or vector affects order.
- `SESSION_RANK`: every pair inherits the maximum pair cosine in its session;
  ties break by session and within-session source order.
- `PAIR_RANK`: each pair uses its own query cosine; ties break by source order.

LongMemEval arms:

- `SESSION_RANK`: every answer-episode candidate inherits its committed EC-002
  session rank, exactly as the deployed NF-002 middle corner.
- `EPISODE_RANK`: each episode uses its frozen NF-003 exact-solo query cosine.

The LongMemEval control uses only NF-002's original stratified development
assignment and only items with turn-level `has_answer` evidence. Its holdout is
already exhausted, but is excluded because the moderator question is explicitly
development-only and does not need another posthoc full-corpus reading.

## 3. Frozen budget grids

LoCoMo characters:

```text
4,000  8,000  12,000  16,000  20,000  24,000  28,000
32,000  40,000  48,000  56,000  64,000  80,000  96,000
```

LongMemEval characters:

```text
8,000  16,000  24,000  32,000  40,000  48,000
64,000  80,000  96,000
```

The grids were fixed before either control outcome was computed. They span
strong truncation through budgets at or above the largest LoCoMo development
conversation and near the median LongMemEval episode store. Each row reports
the distribution of `total_candidate_chars / budget`; interpretation uses that
relative binding ratio, not the absolute character value alone.

## 4. Measures

Primary diagnostic: **all exact evidence pairs delivered**, on canonical unique
QA records whose complete evidence list resolves to candidate identities.

Secondary diagnostics:

- any exact evidence pair delivered;
- paired gains, losses, and ties for `PAIR_RANK` against `SESSION_RANK`;
- both ranked arms against `SOURCE` on LoCoMo;
- delivered-candidate and packed-character distributions;
- median and p10/p90 oversubscription ratio;
- per-conversation signs on LoCoMo;
- the exact one-sided paired sign-test p value, descriptive only.

The LoCoMo 32k row must reproduce 773/868 for `SESSION_RANK` and 826/868 for
`PAIR_RANK` on all-evidence, plus 820/871 and 855/871 on any-evidence. A failure
blocks interpretation. LongMemEval's 32k all-labelled row must reproduce
388/465 and 351/465 before the development subset is read.

## 5. Interpretation fixed before outcomes

- If `SOURCE` is within five all-evidence hits of `SESSION_RANK` at 32k, call
  the LoCoMo ranked baseline **non-discriminating at 32k**. This is a diagnostic
  label, not a study bar.
- A budget is **off ceiling** when `SESSION_RANK` all-evidence delivery is
  between 60% and 85%, inclusive. Report every such budget; do not optimize
  among them on treatment effect.
- A directional crossover exists only if the paired net sign differs at two or
  more adjacent grid points on each side. A one-cell sign change is reported as
  unstable, not as a moderator.
- A cross-corpus binding-ratio scope condition is supportable only if both
  corpora show the same sign ordering over overlapping p10-p90
  oversubscription ranges. Otherwise registration is corpus-specific.

These definitions characterize whether a registration is worth writing. They
do not become its confirmatory bars automatically.

## 6. Preflight

**PF1 - Inputs.** LoCoMo is the 2,805,274-byte file at SHA-256
`79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`;
the development split is four locked conversations, 882 source QA records and
871 canonical unique records. Its vector cache is bound by file and content
hash in `development_vector_manifest.json`. LongMemEval is the 500-item cleaned
file at SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`;
470 answerable streams reproduce the committed ranking and 465 have turn-level
flags.

**PF2 - Mechanism identity.** LoCoMo's two ranked arms already reproduce the
committed development artifact. `SOURCE` is defined by candidate source
position and must be invariant to permuting query vectors. LongMemEval's
session-rank arm reproduces the strict audit and its episode-rank arm reproduces
NF-003 Part 1.

**PF3 - Gate ordering.** Implementation must hard-code this specification's
commit SHA and refuse to run if the file changes. Both 32k reproduction anchors
execute before any sweep row is returned.

**PF4 - Reachability.** The grids include budgets below median evidence cost and
budgets that admit nearly or literally the full store. Hits and misses are both
reachable; a source-order null, either ranking direction, and no crossover are
all representable. The 60%-85% diagnostic interval is not guaranteed to contain
a grid point; finding none is an instrument result and does not authorize grid
tuning.

**PF5 - Stable keys.** LoCoMo uses canonical QA content SHA-256 and removes
duplicate ordinals above zero. Dialogue evidence uses source `dia_id`. The three
malformed all-evidence records are excluded mechanically. LongMemEval uses its
source `question_id` and NF-002's hash-defined split.

**PF6 - Reproduction anchor.** The LoCoMo and LongMemEval 32k totals in §4 must
reproduce by identity before any new cell is emitted. A second complete run must
be byte-identical.

**PF7 - Absorbing state.** None of the arms has feedback or recurrent state.
The degenerate states are budget below every evidence candidate, budget above
the whole store, inherited-score tie plateaus, and source-order independence
from the query; each receives a test.

**PF8 - Length adequacy.** This is not a short ablation. It evaluates all 871
unique LoCoMo development questions and the complete eligible LongMemEval
development split at every fixed budget. It can detect budget-dependent
availability signs but cannot measure reader correctness or transfer.

**PF9 - Surrogate audit.** Source order can score well because answers are
positionally skewed, not because it ranks relevance. Any-evidence can pass with
an incomplete answer. All-evidence is stricter availability but can still pass
while a reader answers incorrectly. No endpoint certifies answer quality.

**PF10 - Live evaluation.** Any successor registration must separately state a
live answer-quality stage. These controls authorize neither inference nor
adoption.

## 7. Stop conditions

Stop without registration if either 32k anchor fails, the source-order arm is
not query-independent, the cache records a miss, any model/embedding call
occurs, or the run cannot reproduce byte-identically. Holdout code remains
absent until a later registration commit.

# BEAM-001 Amendment 009 - Five-hour confirmatory sample

**Status:** authorized prospective runtime redesign; optimized run not started  
**Date:** 2026-08-28  
**Amends:** `BEAM_001_PRE_REGISTRATION.md` and Amendments 006-008  
**Audit anchor:** `3b36c864`

## 1. Trigger and stopped state

The owner stopped the 1,800-question census because its 226.2M charged reader
tokens projected beyond the acceptable runtime for a confirmatory test. The
detached process was terminated and every submitted Batch job was checked.
Thirty jobs were terminal `failed`; all failed during validation with zero
requests completed and zero Batch tokens used. The failure was an upload race:
Batch creation began before the uploaded input file became accessible to the
organization. Six earlier synchronous reader pilot responses exist, with zero
judgments. Their two question keys do not enter the optimized sample and the
responses are excluded from every endpoint.

The stopped census receives no result or post-stop score. Its artifacts remain
under `artifacts/live/`. The optimized run uses a new namespace and new request
domains so no stopped job or answer can be adopted accidentally.

## 2. Resource objective

The optimized comparison must fit the empirical HH API envelope of four to five
hours without changing a selected prompt. HH-002's ledger records 64,551,127
charged tokens over a 5.7269-hour submission span. The fixed optimized reader
schedule charges 56,649,073 tokens, 87.8% of that volume, before the much smaller
judge stage.

Five hours from the first optimized reader submission is a hard runtime cap.
At the cap, the driver stops queue refill, cancels every nonterminal optimized
batch, preserves completed rows and disposes `RUNTIME_BUDGET_EXCEEDED` without
scoring. It does not drop pending rows, extend the cap or interpret a partial
population.

## 3. Fixed balanced sample

Retain all 90 conversations and select exactly five of each conversation's 20
questions, for 450 questions and 1,350 three-arm reader calls. Selection uses no
answer, rubric text, ideal response, evidence label, payload score, prompt
length, pilot response or model output.

Let categories be the ten observed category names in lexicographic order. Sort
conversations by `conversation_key` within each scale. For zero-based
conversation index `i`, select the five consecutive cyclic category indices
beginning at `i + offset`, where offsets are:

- `100K`: 0;
- `500K`: 0; and
- `1M`: 5.

Within each selected category, choose the one of its two questions with minimum
SHA-256 of `"beam001-optimized-sample-v1" || NUL || question_key`. Hash ties are
impossible because question keys are unique; any duplicate selection stops.

The resulting fixed balance is:

- 90/90 conversations, five questions each;
- 100 questions from 100K and 175 each from 500K and 1M;
- 45 questions in every category; and
- within 100K, ten per category; across 500K plus 1M, 35 per category.

The two 35-conversation strata are complementary by category. Individual
scale-category cells range from 15 to 20 and are reported rather than weighted
or repaired.

## 4. Frozen API population and cost

The selected reader prompts are the exact existing official-template prompts
over the exact Part 1 payload seal. No truncation, summarization, repacking,
short-context arm, output-cap change or prompt edit is permitted.

Preflight fixes:

- 450 questions;
- 1,350 reader calls;
- 53,884,273 exact reader input tokens;
- 56,649,073 charged reader tokens including the fixed 2,048-token maxima;
- median reader prompt 38,598 tokens and p95 49,559;
- 1,373 official rubric criteria across selected questions;
- 4,119 criterion judge calls across three arms; and
- 5,469 successful optimized calls before retries.

Any count or token mismatch stops before submission. The six excluded pilot
calls are historical transport diagnostics, not part of these totals.

## 5. Transport repair

Synchronous reader smoke is already satisfied by the six valid excluded pilot
responses. The optimized reader stage begins directly with Batch requests. The
two-judgment synchronous smoke after the complete answer seal remains binding
and is included in the 4,119 judgments.

For every Batch job:

1. upload the immutable JSONL bytes;
2. retrieve the file until status is `processed` and organization access is
   confirmed;
3. stop on file status `error`, `deleted` or five minutes without readiness;
4. only then create the Batch job;
5. bind batch id, input file id and body digest durably; and
6. allow at most one identical resubmission after a terminal batch failure.

The previous shared scheduler's unbounded terminal requeue is forbidden. The
optimized schedule retains 600,000 charged tokens per job, 2,000 lines per job
and a 1,900,000-token aggregate in-flight target. Queue refill occurs only after
a terminal job is collected or its one retry is recorded.

## 6. Confirmatory endpoint

The independent unit remains conversation (`n=90`). Question score remains the
mean of official criterion scores. Optimized conversation score is the mean of
the five selected question scores. Because every category has 45 questions and
every conversation has five, the overall question mean, category macro mean and
conversation mean remain equal.

The primary T1-C0 estimator, 1,000,000-draw paired sign-flip test, 200,000-draw
conversation bootstrap, `+0.02` practical bar and seeds remain unchanged. The
T1-A0 one-sided non-inferiority margin and bootstrap remain unchanged. Scale and
category descriptive guardrails and every disposition threshold remain
unchanged.

This is a confirmatory balanced-sample result, not a full BEAM census score.
The lower five-question within-conversation measurement density limits
precision for heterogeneous effects. Retaining all 90 independent units and
perfect overall category balance is the design's protection against replacing
power with a small conversation subset.

## 7. Revised gates

- **G-SAMPLE:** reproduce all 450 identities, per-conversation count, category
  balance, scale counts and zero pilot overlap from the committed mechanism
  surface.
- **G-TOKENS:** reproduce all counts and exact token totals in Section 4 before
  an API request.
- **G-FILE:** every uploaded file reaches `processed` before Batch creation;
  the former access-race fixture must fail before submission.
- **G-RETRY:** synthetic terminal jobs prove zero, one and exhausted retry
  paths; no key can create a third batch.
- **G-RUNTIME:** complete answers, judgments and seals within five hours or
  cancel and stop without a score.
- **G-ANSWERS:** exactly 1,350 optimized answers, with 450 per arm and three per
  selected question; reject all stopped-census ids.
- **G-JUDGES:** exactly 4,119 judgments over 1,373 criteria per arm after the
  complete optimized answer seal.
- **G-SCORE:** exactly 1,350 question-arm scores, 90 conversation units, 45
  questions per category and independent reproduction of every statistic.

PF1-PF10 from the live registration remain binding with the optimized counts.
PF4 must additionally demonstrate every disposition at five observations per
conversation and both sides of the runtime boundary. PF8 records that the
sample can test the registered overall paired effect but has less precision for
scale and category guardrails than the stopped census.

## 8. Unchanged claim boundary

All three arms, model snapshot, temperature, reader and repaired judge prompts,
output limits, blind ids, answer-before-judge ordering, criterion scoring,
statistics and package-adoption boundary are unchanged. Only the prospective
question population, runtime cap and defective Batch transport mechanics
change. No result from the stopped census is carried into the optimized score.

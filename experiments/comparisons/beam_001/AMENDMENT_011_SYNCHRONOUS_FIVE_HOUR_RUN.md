# BEAM-001 Amendment 011 - Synchronous five-hour run

**Status:** authorized prospective final runtime design; no optimized response
generated  
**Date:** 2026-08-28  
**Amends:** Amendments 008-010  
**Audit anchor:** `2f510af1`

## 1. Batch transport is closed

Four optimized Batch jobs were submitted only after their uploaded files
reported `processed`. All four still failed validation because the Batch service
organization could not access the project key's files. They completed zero
requests and used zero tokens. The detached process was stopped and no batch
remains active.

Batch transport is unavailable for this credential and is removed from the
optimized run. It is not retried, worked around with another organization or
mixed with synchronous output.

## 2. Measured synchronous limits

One non-study one-token call opened only response headers and fixed the current
project limits:

- `x-ratelimit-limit-tokens`: 200,000;
- `x-ratelimit-limit-requests`: 10,000;
- request reset: 8.64 seconds, or 6.944 requests/minute; and
- token reset reported continuously.

The optimized runner uses 195,000 charged tokens/minute and 6.8 requests/minute.
Both budgets are acquired before a call. A refused call remains charged. Eight
reader workers overlap latency; 32 judge workers overlap the smaller judge
calls. Worker count never bypasses either shared bucket.

Every successful response is appended, flushed and fsynced immediately by
stable id. One identical-body retry is allowed after a transport, refusal,
length, empty or parse failure. A second failure stops without scoring.

## 3. Final balanced population

Retain all 90 conversations and select four questions per conversation, for
360 questions. Amendment 009's scale ordering, category ordering and offsets
0/0/5 remain, but the cyclic category window is four rather than five. The
within-category domain becomes `beam001-optimized-4q-sample-v1`, followed by one
NUL byte and the question key.

The fixed population has:

- 80 questions from 100K and 140 each from 500K and 1M;
- 36 questions in every category;
- eight per category in 100K and 28 per category across 500K plus 1M;
- zero overlap with the excluded six-call pilot; and
- 1,080 reader calls, three arms for every selected question.

The exact reader schedule contains 43,077,320 input tokens and 45,289,160
charged tokens including the fixed output maxima. Median prompt length is
38,616 tokens and p95 is 49,572. At 195,000 charged tokens/minute, the reader
floor is 3.871 hours. No prompt byte, context, arm or output cap changes.

## 4. Bundled blind judge

The separate-criterion schedule cannot fit the measured request bucket after
the reader. Replace it with exactly one judge call per selected question: 360
calls. Each call evaluates all three generated answers against all official
criteria for that question.

The three answers receive slots `R0`, `R1`, `R2` in ascending SHA-256 order of
`"beam001-bundled-judge-slot-v1" || NUL || question_key || NUL || arm`. The
judge surface contains only question, ordered official criteria and slotted
answer text. Arm names, payloads, retrieval traces and mapping are absent. The
slot-to-arm mapping is sealed separately before calls and unopened until all
360 judgments seal.

The fixed judge prompt is:

```text
You are an expert evaluator. Independently score each RESPONSE against each
ordered RUBRIC CRITERION for the QUESTION.

QUESTION:
<question>

RUBRIC CRITERIA (zero-based JSON array):
<rubric_json>

RESPONSES (JSON object keyed by blind slot):
<responses_json>

For every response and criterion, first require that the response addresses the
QUESTION. A non-responsive answer scores 0.0. Judge semantic meaning rather
than exact wording. Accept equivalent paraphrases, numbers, currencies and
dates. Ignore style unless the criterion explicitly requires format. For a
positive criterion, score 1.0 when fully satisfied, 0.5 when partially
satisfied, and 0.0 when missing or incorrect. For a negative constraint, score
1.0 only when the response is responsive and the prohibited element is absent,
0.5 for a minor or edge violation, and 0.0 when the prohibited element is
present or the response is non-responsive. Evaluate each slot independently;
do not rank or compare responses.

Return only JSON with this shape:
{"evaluations":[{"slot":"R0","criteria":[{"rubric_index":0,"score":1.0,
"reason":"concise justification"}]}]}

Include every supplied slot and every rubric index exactly once. Scores must be
0.0, 0.5 or 1.0. Keep each reason concise.
```

Literal placeholders are replaced with the exact question and canonical JSON
using UTF-8, sorted object keys and preserved criterion order. Judge model is
the same dated GPT-4o mini snapshot at temperature zero,
`response_format={"type":"json_object"}`, and `max_tokens=4096`.

There are 1,061 official criteria across the 360 selected questions, producing
3,183 criterion-slot scores inside 360 responses. The parser requires every
registered slot/index pair exactly once, allowed scores and nonempty reasons.
Extra, missing or duplicate pairs are malformed. One identical retry is
allowed. No criterion score is inferred or repaired.

Bundling creates common judge-call dependence and permits implicit comparison
despite the independence instruction. Hash-randomized blind slots prevent a
systematic arm position advantage; the claim remains conditional on this one
bundled judge instrument. Bundling is a measurement change, not an official
BEAM benchmark score.

## 5. Runtime and counts

The final optimized schedule contains 1,080 reader calls plus 360 judge calls:
1,440 successful calls before retries. The 360-judge request floor at 6.8/minute
is 0.882 hours. Combined with the conservative charged reader floor, projected
API pacing is 4.753 hours.

The five-hour hard cap from Amendment 009 remains. It starts before the first
optimized reader request and covers readers, answer sealing, judge construction,
judging and result seals. At the cap, no new synchronous call is admitted;
incomplete rows are preserved and the study stops `RUNTIME_BUDGET_EXCEEDED`
without a score.

## 6. Endpoint and dispositions

Question score remains the arithmetic mean of all criterion scores for that
question-arm. Conversation score is now the mean of four selected question
scores. Equal four-per-conversation and 36-per-category balance preserve the
identity between overall question mean, category macro mean and conversation
mean.

The T1-C0 estimator, sign-flip test, cluster bootstrap, practical bar, T1-A0
non-inferiority guard, scale/category guardrails, seeds and dispositions remain
unchanged. This is a 360-question balanced-sample confirmatory result, not a
full BEAM census or official benchmark score.

## 7. Revised gates

- **G-SAMPLE:** exactly 360 identities, 90 conversations, four each, 36 per
  category, scale counts 80/140/140 and zero excluded-pilot overlap.
- **G-TOKENS:** exactly 1,080 readers, 43,077,320 input and 45,289,160 charged
  reader tokens.
- **G-SYNC:** one pre-result fixture reproduces both measured rate headers;
  token and request buckets charge before dispatch and never exceed targets.
- **G-CHECKPOINT:** interrupted synthetic and real-prefix runs adopt every
  fsynced stable id and resend no completed request.
- **G-ANSWERS:** exactly 1,080 valid answers, 360 per arm, sealed before outcome
  or judge-surface construction.
- **G-BLIND:** exactly 360 question judge surfaces and 3,183 unique blind
  slot-criterion pairs; mapping access fails before the judgment seal.
- **G-JUDGES:** exactly 360 valid JSON responses and all 3,183 scores.
- **G-RUNTIME:** all result seals within five hours or no score.
- **G-SCORE:** 1,080 question-arm scores, 90 conversation units, 36 per
  category and independent statistical reproduction.

PF4 must reach malformed, missing, duplicate and extra matrix cells, every
score value, both signs of all comparisons, every disposition and both sides of
the runtime boundary. PF9 records bundled-judge common-mode and comparison bias
as residual surrogate risks.

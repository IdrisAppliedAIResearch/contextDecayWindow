# BEAM-001 - Live reader pre-registration

**Type:** fixed-population, three-arm paired live reader study  
**Status:** pre-registered; no reader or judge call made  
**Date:** 2026-08-28  
**Authorization:** program owner directed end-to-end completion with the dated
GPT-4o mini model used by the HH studies

## 1. Question and claim boundary

On all 1,800 questions from the 90 normal-scale BEAM conversations, does the
parent-opportunity ASPECT selector improve answer correctness over global static
ASPECT while remaining non-inferior to the shipped CC80 selection architecture?

This is a paired reader validation of three already-sealed context payloads per
question. It changes no corpus row, episode, embedding, retrieval score,
selection identity, order, renderer, recency composition or context byte. It
tests the BEAM normal-scale population under one dated reader and one dated
judge. It cannot establish 10M behavior, real-user transfer, reader generality,
production latency, package-port fidelity or a new public default.

## 2. Frozen inputs and population

- Part 1 commit: `fc71e60c`.
- Live-design audit commit: `aacb8a6c`.
- Part 1 report SHA-256:
  `914f254db4419e21325e367eb8e39de034962a216ff66d4d2ce0a7829ac55d91`.
- Mechanism surface SHA-256:
  `0377df4ddafa6899f9b21c4f908a5061852b75580958dd480d31511b9261acec`.
- Sealed outcome surface SHA-256:
  `954bde7b7a5dba3d1656cb74d7c56b9bfec5acd272922957cf0c5f4aa3108943`.
- Sealed payload SHA-256:
  `59f12e55f7f851633b049fdb416d990eda32820ee83897cbd7b10a804f8124dd`.
- BEAM source commit: `3e12035532eb85768f1a7cd779832b650c4b2ef9`.
- Official prompt/scorer hashes are fixed in
  `artifacts/preflight/live_design_audit.json` at `aacb8a6c`.

The population is 90 conversations and 1,800 questions: 20 questions per
conversation, exactly two in each of ten official categories. The scale strata
are 20 100K, 35 500K and 35 1M conversations. There are 5,425 official rubric
criteria, from one to 13 per question. No row, category, criterion or arm is
sampled or excluded after this commit.

Stable comparison keys are the committed content-derived conversation and
question keys. API ids, timestamps, local paths, batch ids and response order
are forbidden as comparison keys.

## 3. Frozen arms

The live runner reads the exact payload string from the Part 1 seal.

- **A0 `A0_CC80_QWEN_GPU_COMMON`:** full-budget CC80 long-term selection plus
  additive latest-32 recency.
- **C0 `C0_STATIC_ASPECT_QWEN_GPU_COMMON`:** global static ASPECT protected
  selection with slack return plus the same recency.
- **T1 `T1_PARENT_OPPORTUNITY_ASPECT_QWEN_GPU_COMMON`:** one-child
  CC80-parent fan-out with opportunity admission and slack return plus the same
  recency.

The local Qwen embedder was a Part 1 precompute and is not loaded during the
live phase. No embedding, retrieval, parsing, packing or rendering is permitted
after this registration.

## 4. Reader prompt and runtime

Both reader and judge use `gpt-4o-mini-2024-07-18`, temperature `0.0`, through
`POST /v1/chat/completions`. The reader receives one user message whose content
is this official BEAM template after literal replacement of `<context>` and
`<question>`:

```text
You are an assistant that MUST answer questions using ONLY the information provided in the context below. 

STRICT INSTRUCTIONS:
1. Answer ONLY based on the provided context
2. Do NOT use your internal knowledge

CONTEXT:
<context>

QUESTION:
<question>

ANSWER REQUIREMENTS:
- Be direct and concise
- Only output the answer to the question without any explanation 

RESPONSE:
```

The exact leading and trailing newlines from the pinned Python string are
retained. Reader `max_tokens=2048`. A length-stopped, empty, refused or missing
answer is a validity failure. Content-filter and transport failures are
preserved. One resubmission of a failed request with an identical body is
allowed; a second failure makes the study `NOT_INTERPRETABLE`.

The token audit covers all 5,400 prompts under `o200k_base`: min 28,516,
median 38,614.5, p95 49,715 and max 64,740 input tokens including fixed chat
overhead. All are below the registered 125,952-token input ceiling after the
2,048-token output reserve. No truncation or context modification is allowed.

## 5. Schedule, pilot and durable transport

There is one reader response per question-arm: 5,400 total. Within every
question, arm order is ascending SHA-256 of
`"beam001-reader-order-v1" || question_key || arm`. Question processing order
is ascending question key. Batch completion order has no semantic meaning.

The pilot is the two lexicographically smallest question keys, all three arms,
for six reader requests. Its responses are retained as scheduled population
responses. The pilot passes only if all six responses are nonempty, naturally
stopped and bound to their request digests. Their official criteria are then
judged under Section 6; every judgment must parse and carry an allowed score.
The pilot opens no aggregate or arm comparison.

After the pilot, remaining work uses the OpenAI Batch API with durable JSONL
inputs, content-derived custom ids and an append/flush/fsync ledger. A request
body digest binds every result. Jobs target at most 400,000 estimated tokens
and 2,000 lines; aggregate submitted work respects the observed 2,000,000-token
queue ceiling with the carried 1,400,000-token target. Existing in-flight jobs
are adopted by digest on resume and never duplicated.

`OPENAI_API_KEY` is process-only. It is never written to a file, command line,
manifest, request artifact or log. Once the first jobs are accepted, a detached
driver advances from reader batches through answer sealing, blind judge
batches, scoring and reporting. Agent-side polling is not part of the method.

## 6. Blind official-rubric scoring

All 5,400 complete reader answers are sealed before any judge request is
created. Judge custom ids are SHA-256 blind ids under domain
`beam001-judge-v1`; they disclose neither arm nor mechanism. The mapping is
sealed separately and cannot be imported by request rendering.

For every answer and every corresponding official rubric criterion, the judge
receives one user message containing the official
`unified_llm_judge_base_prompt`. The implementation makes one registered repair:
it replaces `<question>` with the exact question, in addition to the official
replacements of `<rubric_item>` and `<llm_response>`. The pinned official code
otherwise leaves `<question>` literal even though its responsiveness rule
requires the real question. Leaving the placeholder unresolved could pass while
responsiveness is false, so the upstream behavior is not a valid instrument.

The judge uses `response_format={"type":"json_object"}` and
`max_tokens=512`. Exactly one judgment is made per criterion, for 16,275 judge
calls. Parsed JSON must contain only an allowed numeric score `0.0`, `0.5` or
`1.0` plus a nonempty reason. Markdown-fence removal and extraction of one JSON
object are allowed parse repairs; changing a score or asking another model to
repair content is forbidden. One identical-body resubmission is allowed after
a malformed or failed call; a second failure makes the study
`NOT_INTERPRETABLE`.

The separate official event-ordering alignment path is not used. It discards
its extracted facts, splits raw answers by newline, makes a variable number of
equivalence calls and reports normalized Kendall tau instead of the common
rubric endpoint. All ten categories therefore use the repaired official
criterion judge uniformly. This deviation is fixed before any live call.

Question score is the arithmetic mean of its criterion scores. Category score
is the arithmetic mean of its 180 question scores. Conversation score is the
arithmetic mean of its 20 question scores. Because each conversation contains
two questions from every category, the mean of 90 conversation scores equals
both the overall question mean and the macro mean of ten category scores.

## 7. Confirmatory comparisons and statistics

The independent analysis unit is conversation (`n=90`). Question-level tests
are forbidden because 20 questions share a conversation and context store.

### Primary: T1 versus C0

For each conversation, compute mean `T1 - C0` across its 20 paired question
scores. The estimand is the mean of the 90 conversation differences in score
units. Report the estimate in points, gains/losses/ties at question and
conversation level, and a two-sided paired sign-flip test of the mean with
1,000,000 Monte Carlo draws under NumPy `PCG64` seed `2026082801`:

`p = (1 + count(|permuted mean| >= |observed mean|)) / 1,000,001`.

Report a two-sided 95% percentile cluster-bootstrap interval from 200,000
conversation resamples under seed `2026082802`.

### Required A0 guardrail

Apply the same estimator to `T1 - A0`. Report a one-sided 95% percentile lower
bound from 200,000 conversation resamples under seed `2026082803`.
Non-inferiority margin is `-0.01` score units.

### Scale and category guardrails

Report paired mean differences for each of the three scale strata and ten
categories. These are descriptive guardrails, not additional significance
tests. T1-C0 must be at least `-0.01` in every scale and T1-A0 at least `-0.02`
in every scale for `WORKS`. No category may have T1-C0 below `-0.03` for
`WORKS`. No parameter, prompt, subset or threshold changes after inspection.

C0-A0, answer lengths, token use, latency, API finish reasons and criterion
score distributions are descriptive. No multiplicity-adjusted secondary winner
claim is made.

## 8. Dispositions

Apply the first matching rule after all validity gates pass:

1. **`WORKS`:** T1-C0 is at least `+0.02`, its sign-flip `p <= .05`, its
   two-sided bootstrap lower bound is above zero, the T1-A0 one-sided lower
   bound is above `-0.01`, and every scale/category guardrail passes.
2. **`GAIN_WITH_GUARDRAIL_FAILURE`:** T1-C0 is positive with `p <= .05` but
   one practical, A0, scale or category condition for `WORKS` fails.
3. **`REGRESSES`:** T1-C0 is at most `-0.02`, `p <= .05`, and the two-sided
   bootstrap upper bound is below zero; or T1-A0 is at most `-0.02` and its
   one-sided lower bound is at or below `-0.01`.
4. **`NO_DEMONSTRATED_GAIN`:** every other valid result.
5. **`NOT_INTERPRETABLE`:** any input, prompt, schedule, completion, blinding,
   parse, mapping, count or statistical reproduction gate fails.

Only `WORKS` makes T1 eligible for a separate package-port registration. It
does not itself authorize implementation in the public package. A primary gain
with an A0 or scale regression cannot be described as an improvement.

## 9. Preflight - binding before live calls

- **PF1 Inputs:** verify the hashes in Section 2, count 90 conversations,
  1,800 questions, 5,400 payloads and 5,425 nonempty rubric lists, and record
  the dated model and client version without credential material.
- **PF2 Mechanism identity:** reproduce each payload digest from the Part 1
  seal and state each arm's verified behavior. Reader input differs only by the
  sealed arm payload for a fixed question.
- **PF3 Gate ordering:** Part 1 and live-design audit commits precede this
  standalone registration; this registration commit precedes live
  implementation; all answers seal before judge construction; all judgments
  seal before blind mapping and scoring.
- **PF4 Reachability:** deterministic synthetic fixtures must reach every
  disposition, both signs of each comparison, equality at every threshold,
  the non-inferiority boundary, each scale/category guardrail, malformed JSON,
  duplicate/missing ids, length stop and retry exhaustion.
- **PF5 Stable keys:** rebuild and shuffled-order tests reproduce all request
  ids, body digests, joins and scores. Duplicate text occurrences remain
  distinct through committed question keys.
- **PF6 Reproduction:** render the official reader prompt byte-for-byte from
  the pinned constant; reproduce all 5,400 prompt token counts and payload
  hashes; prove the judge differs from upstream only by exact question
  insertion and request transport fields.
- **PF7 Feedback and termination:** requests are stateless, each scheduled key
  has one terminal result, retries are bounded at one, resumes adopt by digest,
  and no answer can alter a later prompt or schedule.
- **PF8 Adequacy:** 90 paired conversation units can identify an effect of the
  registered practical size under this reader. The 20-conversation 100K
  stratum has limited precision; scale checks are guardrails, not independent
  efficacy claims.
- **PF9 Surrogates:** criterion compliance can pass despite judge bias;
  temperature zero can remain nondeterministic; more retrieved facets can lower
  correctness; an average gain can hide a category loss. Blinding, paired
  scoring and registered regression guards reduce but do not remove these
  risks.
- **PF10 Live requirement:** this live run, not Part 1 overlap, payload size,
  token fit or a successful API call, decides the registered disposition.

Additional validity gates:

- **G-INPUT:** exact hashes and population counts match.
- **G-PROMPT:** every request body and token count reproduces before submission.
- **G-PILOT:** all pilot answers and judgments are valid and digest-bound.
- **G-ANSWERS:** exactly 5,400 naturally stopped, nonempty sealed answers.
- **G-BLIND:** exactly 16,275 arm-blind criterion requests with a one-to-one
  sealed mapping.
- **G-JUDGES:** exactly 16,275 valid parsed judgments and no unresolved prompt
  placeholder.
- **G-SCORE:** independent recomputation reproduces every question,
  conversation, category, scale and overall score plus all test statistics.

## 10. Fixed API count and stopping rule

The complete valid schedule contains 5,400 reader calls and 16,275 judge calls:
21,675 calls before retries. The pilot is part of these totals. Retries are
reported separately and never change the estimand.

Stop without a substantive verdict on hash drift, population drift, any
over-limit prompt, unresolved placeholder, answer or judgment exhaustion,
duplicate successful response, missing blind row, mapping exposure before the
judge seal, score outside the allowed set or failure to reproduce statistics.
Do not repair the corpus, trim context, drop questions, increase output limits,
change models, add replicates or rerun a valid result.

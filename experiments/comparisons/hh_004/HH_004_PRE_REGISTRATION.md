# HH-004 Pre-Registration - frozen DA-098 decoded arm

**Status:** `COMPLETE - CHARACTERIZED; decoded allocation did not beat episodic controls`
**Date:** September 1, 2026
**Predecessor:** HH-003 deployed episodic-chat benchmark

## 1. Question

What does DA-098's frozen strongest 32k protected allocation score when its
selected source members are decoded and inserted into the unchanged HH-003
LoCoMo answer and judge harness?

Only the new arm is generated and judged. All unchanged arms are reused by
stable item key; they are not submitted again.

## 2. Arm And Claim Boundary

The only paid arm is `A_DA098_ARCH32_DECODED`. Its source is committed DA-098
allocation SHA-256
`f5327a9b5946f217910f2de5df222da66bda59d5f7b18267f8154763f98d44f9`.
For each item, preserve `arch32.selected_members` exactly in stored order, map
each identity/member coordinate to its locked LoCoMo source turn, and render
the exact speaker and text in a deterministic member-delimited payload.

The model receives decoded source text. This tests whether the frozen
allocation and order support answers; it does **not** test model interpretation
of DA-034 sentinel-varint pointers. DA-098's role-pattern charge has no
canonical parseable prompt wire, so no result may call this a compact-wire
reader test or claim a 32k prompt. Blind preflight measured decoded payloads at
44,735.5 median and 46,352 maximum characters.

No evidence annotation, answer, category, rubric, score or prior model output
enters context construction.

## 3. Population

Use the exact intersection of:

- DA-098's 1,098 primary rows from holdout conversations `conv-26`, `conv-30`,
  `conv-43`, `conv-44`, `conv-49`, `conv-50`; and
- HH-003's 1,540 scored non-category-5 items.

The population is locked at 842 items: 151/81/177/123/153/157 by conversation
in the order above. Join on `(sample_id, source_index)` and verify question,
answer and stable item identity against the unchanged HH-003 context cache.
No missing or additional row is allowed.

## 4. Frozen Harness

- Corpus: `C:\Users\muzaf\Downloads\locomo10.json`, 2,805,274 bytes, SHA-256
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- Answerer and judge: `gpt-4o-mini-2024-07-18`, temperature 0.0.
- Answer and judge prompts, deterministic F1/exact match, item keys and parsing
  are unchanged from HH-003/HH-002.
- Transport: synchronous OpenAI calls with eight workers, answer pacing at 6.6
  requests/minute plus 170,000 estimated tokens/minute, and judge pacing at
  170,000 estimated tokens/minute as established by HH-003 Amendment 009.
- API key is read only from `OPENAI_API_KEY`, inherited by the supervisor, and
  never written to source, artifacts, logs, prompts or command-line arguments.

## 5. Reused Comparators

Subset prior sealed predictions and judgements by the 842 stable keys for
`A_EPISODIC`, `A_EPISODIC_ASPECT`, HH-002 `A_CDW`, `A_RAG`, and `A_FULL`.
Verify their committed file hashes and 842 exact joins before submission.
Comparisons are cross-date and descriptive.

Primary endpoint is mean binary `llm_score`. Also report deterministic F1,
exact match, category/conversation scores, prompt/completion tokens, context
characters, latency, malformed responses, failures, and two-sided exact paired
sign tests against every reused comparator. No directional quality bar or
automatic adoption decision is registered.

## 6. Gates And Run Order

1. `G0 INPUTS`: corpus, DA-098 allocation and reused HH files match committed
   hashes; population is exactly 842.
2. `G1 RENDERER`: every selected coordinate resolves once; decoded text and
   order replay exactly; no leakage field appears; max prompt estimate is below
   the model context limit.
3. `G2 CONTROLS`: all reused comparator rows join exactly by stable key and
   reproduce their subset summaries.
4. `G3 CONTEXTS`: all 842 contexts are deterministic, committed, nonempty and
   have exact source/order hashes. Paid execution requires clean tracked files
   and committed G0-G3 artifacts matching current runner hashes.
5. `G4 PILOT`: the first eight scored `conv-26` items are answered and judged
   to verify access, response shape, checkpoint resume and accounting. They are
   reused in the full arm.
6. `G5 ANSWERS`: seal all 842 answers before any non-pilot judgement.
7. `G6 JUDGING`: seal all 842 judgements, then open and report scores.

Completed stable keys are never regenerated. A resumed stage submits only
absent keys.

## 7. Supervision And Recovery

A committed supervisor runs `pilot -> answers -> judge`, writes atomic health
state at least every 30 seconds, records stage, child PID, completed/expected
counts, checkpoint age, restart count and last error, and captures stdout/stderr
without credentials. It restarts a nonzero-exit stage or a stage with no
checkpoint progress for 20 minutes, using stable-key resume, with five automatic
restart attempts and bounded backoff. It never restarts a completed stage or
deletes a checkpoint. Exhaustion writes terminal `NEEDS_ATTENTION` and exits.

A thread heartbeat independently checks the health file, process existence,
checkpoint counts and freshness every 15 minutes. It reports completion,
`NEEDS_ATTENTION`, a dead supervisor, count regression, or stale progress; it
does not hold or reproduce the API key and does not itself submit calls.

## 8. Limits

LoCoMo and the six-conversation allocation are spent. The 842-item population
is not the full 1,540-item HH leaderboard and must not be compared through raw
full-population means. Reused comparators are cross-date. The decoded context
tests selected evidence use but not compact pointer interpretation, fresh
transfer, interactive memory, or production concurrency.

## 9. Result

The new arm scored 606/842 (`.7197`), with mean F1 `.4079` and exact match
`.0190`. It trailed episodic by 49 net paired items (60 gains/109 losses,
p=`.000202`) and episodic-aspect by 64 (60/124, p=`2.74e-6`), beat RAG by 223
(270/47, p=`3.43e-39`), and trailed full context by 16 (85/101, p=`.271`).
No judgement was malformed and no item failed.

Decoded contexts were 52,798-58,091 characters (median 55,205), not 32k
prompts. The watchdog made one stale-progress restart and recovered by
stable-key resume. This characterizes allocation answer utility, not compact
code interpretation or production concurrency.

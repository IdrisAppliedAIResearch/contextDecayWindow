# BEAM-001 Amendment 008 - Transport smoke and queue utilization

**Status:** authorized prospective transport amendment; zero successful reader
or judge responses exist  
**Date:** 2026-08-28  
**Amends:** `BEAM_001_PRE_REGISTRATION.md` at `12f01fcc` and Amendment 006

## 1. Trigger

The owner directed the live phase to reuse the HH transport pattern: synchronous
calls for the first reader and judge smoke sets, then Batch API population work
packed close to the account's token ceiling. The first attempted pilot transport
failed authentication against a stale host environment key before producing a
model response. It created no answer, judgment or outcome observation.

## 2. Synchronous smoke calls

The fixed six-reader pilot from Amendment 006 uses synchronous
`POST /v1/chat/completions`, one request at a time. Bodies, ids, model,
temperature, output cap, validation and one-retry rule are identical to the
registered population requests. Valid pilot responses are sealed into and
reused by the 5,400-answer population.

After all 5,400 answers seal and the complete blind judge surface is constructed,
the two lexicographically smallest blind judge ids run synchronously, one at a
time. They validate transport and strict JSON parsing only. Their valid results
are sealed into and reused by the 16,275-judgment population. No score,
arm mapping or aggregate is opened at either smoke gate.

## 3. Batch utilization

All remaining reader and judge requests use the existing resumable Batch API
ledger with:

- exact registered input-token count plus the request's maximum output tokens
  as the queue charge;
- 600,000 charged tokens per job;
- at most 2,000 requests per job;
- 1,900,000 charged tokens as the aggregate in-flight target under the
  observed 2,000,000-token account ceiling; and
- queue refill immediately after a terminal job is durably collected.

The 100,000-token headroom covers endpoint bookkeeping without retaining the
older characters-per-four estimation margin. Reader and judge stages use the
same charged-token scheduler; smaller judge requests therefore admit many more
calls per job and complete in fewer refill cycles.

## 4. Credential correction

The stale inherited environment key is ignored. The owner-supplied temporary
credential is injected through hidden process input into the detached runner's
environment. It is not written to source, artifacts, logs, shell history or
command-line arguments. Authentication failures are transport failures and
never become answer rows.

## 5. Unchanged

The fixed population, schedule identities, request bodies, total successful
call count, retry cap, answer-before-judge gate, blind mapping, scoring,
statistics and dispositions are unchanged. Synchronous versus Batch execution
is transport only and cannot select or alter a request.

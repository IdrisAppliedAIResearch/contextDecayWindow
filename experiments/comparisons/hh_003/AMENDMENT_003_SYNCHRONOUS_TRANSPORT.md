# HH-003 Amendment 003 - synchronous API transport

**Date:** August 24, 2026
**Timing:** After pilot answers, before any pilot judgement and before any
full-run answer
**Authorization:** User requested synchronous calls rather than waiting for
Batch API jobs
**Pre-registration anchor:** `ea5cf2b6`

## State at amendment

Both pilot answer batches completed 8/8 with zero failures and were collected.
The two pilot judgement batches were `in_progress` at 0/8 completed, zero
failed, and had no output file. They will be cancelled before synchronous
judging. No completed judgement is replaced.

## Transport change

All remaining HH-003 answer and judgement requests use the synchronous
`/v1/chat/completions` endpoint with eight workers, carried from HH-002's
existing synchronous runner. Model, messages, prompts, response format,
temperature, stable item keys, sealing order, endpoints, and denominators are
unchanged. Completed records are adopted by stable key and never regenerated.

Batch is not a fallback. A synchronous rate-limit or access failure stops the
run and is reported rather than silently changing transport again. Per-call
latency and token usage are recorded. The cancelled batch IDs and final request
counts remain in the ledger.

Transport is operationally observable and may move vendor output despite an
identical request body. Results will carry this amendment and will not be
described as a byte replay of HH-002's Batch transport.

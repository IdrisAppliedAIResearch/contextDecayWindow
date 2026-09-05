# DA-046 Single Retained-Frame Contract

**Status:** `COMPLETE; ORACLE_SINGLE_REGISTER_SUFFICIENT`
**Date:** August 30, 2026
**Parent:** DA-045 result commit `64782f70`
**Standing:** blind architecture contract plus spent oracle sufficiency audit
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

If a reader recognizes the relevant DA-045 frame, is one bounded retained-frame
register mechanically sufficient to preserve and deliver every residual fact
without modifying the DA-038 prompt?

DA-045 exposes all 18 residuals but replaces each frame. This study tests the
retention primitive, not recognition or stopping.

## 2. Part 1: Blind Contract

Freeze DA-045's 465 streams byte-for-byte. Define a deterministic state machine
with:

- immutable DA-038 prompt;
- `current`, holding the exposed frame or empty;
- `retained`, holding at most one exact frame or empty;
- `NEXT`, replacing `current` with the next stream action;
- `KEEP`, atomically moving a valid current frame to `retained` and clearing
  `current`;
- `ANSWER`, exposing the immutable prompt plus retained frame.

`KEEP` is invalid on overflow/empty current. Registers may never truncate,
merge, summarize or modify a frame. Each register is capped at 2,048 chars;
general peak auxiliary capacity is 4,096 chars.

Commit transition ledgers, frame hashes, caps and immutable prompt hashes before
evidence. Require exact replay, all transition guards exercised, no prompt
mutation, no frame mutation, <=4,096 peak, zero calls. Stop unopened on failure.

## 3. Part 2: Oracle Sufficiency

After Part 1 is sealed, use DA-039's residual identities only to issue `NEXT`
through the required frame, `KEEP` that frame, then `ANSWER`. Stop immediately
after retention. This oracle action is evidence-aware and nondeployable.

Report exact evidence availability against DA-038, traversal depth, cumulative
chars, path peak, retained chars and one-hop ceiling.

Report `ORACLE_SINGLE_REGISTER_SUFFICIENT` only if all 18 residuals are retained,
delivery reaches 250/250, losses are zero, DA-038 is immutable, and oracle path
peak is <=2,048 chars. Otherwise report `ORACLE_SINGLE_REGISTER_INSUFFICIENT`.

## 4. Boundary

Passing proves only that recognition plus one exact retained frame would be
mechanically sufficient. It does not prove a reader recognizes relevance,
chooses `KEEP`, stops, answers correctly, or transfers. No model, embedding,
runtime or adoption claim follows.

# LV-003 — bounded-output live validation

**Status:** `STOPPED_AT_GENERATION; TWO_BALANCED_TRUNCATIONS`  
**Registration commit:** `4f91840d`  
**Preflight commit:** `0e0f4069`  
**Date:** 2026-08-26

LV-003 preserved all 170 scheduled responses with no missing, duplicate or
extra keys. Two responses reached the registered 512-token limit, so the
binding truncation gate stopped judging and no arm verdict exists.

Both truncations belong to the same offline opportunity-gain breadth question
(`conv-42`, source 79): full CC80 replicate 2 and opportunity replicate 3. Each
contains an answer before continuing to inspect the context, but content
adequacy is not an exception to the locked gate.

The preserved answer artifact SHA-256 is
`e7a9a2343182502d0be1675ba5b797a2115e49b873709cb3614e22a9bd55e784`.
No blind surface, judge call, unblinding or outcome score was produced.

Unlike LV-002, the persistence correction worked: the two incomplete responses
and all 168 naturally stopped responses remain auditable. A successor may make
only a mechanically identified completion repair, retain the originals, and
require deterministic prefix identity before scoring.

# BEAM-001 Amendment 007 - Exact reader prompt token counts

**Status:** prospective instrument correction; no reader or judge call made  
**Date:** 2026-08-28  
**Amends:** `BEAM_001_PRE_REGISTRATION.md` at `12f01fcc` and the descriptive
token fields in `artifacts/preflight/live_design_audit.json` at `aacb8a6c`

## 1. Finding

The pre-implementation design audit reconstructed the visible reader prompt
text but omitted the pinned Python string's one leading and one trailing newline
token. The registered live runner extracts the constant through Python AST from
the hash-pinned official `prompts.py`, preserving both newlines as Section 4
requires. Exact full-population preflight therefore gives min 28,518 and max
64,742 input tokens, not 28,516 and 64,740.

No API request had been made when this discrepancy was found. The payload,
question, prompt source, tokenizer, chat-overhead convention and every request
identity are unchanged.

## 2. Binding correction

Replace the reader token distribution in Section 4 with:

- min: 28,518;
- median: 38,616.5;
- p95: 49,717;
- p99: 58,650;
- max: 64,742; and
- over the 125,952-token input ceiling: 0 of 5,400.

Exact extraction from the pinned official constant is authoritative. Synthetic
reconstruction of visible prompt text is not an acceptable reproduction path.

## 3. Unchanged

The maximum remains 61,210 tokens below the registered input ceiling. No
truncation, model, output reserve, prompt, schedule, score, gate, disposition or
call count changes. This correction authorizes no API call by itself.

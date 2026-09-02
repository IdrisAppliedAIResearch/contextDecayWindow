# DA-015 Reversible Phrase-Dictionary Report

**Status:** `TRANSFERABLE_CAPACITY_SIGNAL`
**Date:** August 30, 2026
**Standing:** evidence-blind mechanical transfer on two spent corpora

## Mechanical Result

The identical frozen phrase codec exceeds its registered median 100-character
bar on both corpora while preserving every direct identity, order, member and
decoded character.

- NF-004 LoCoMo: median incremental savings **448.5** characters (p10 290.6,
  p90 624, max 804) across 1,104 contexts.
- DA-013 LongMemEval: median **863** (p10 562.2, p90 1,457, max 4,160) across
  465 contexts.
- Zero rows expand or use the no-dictionary fallback. Both full builds are
  byte-identical. There were zero embedding, model or cache calls.

This is a mechanical transfer signal: explicit repeated-phrase references create
substantially more protected capacity without pre-dropping direct evidence.

## DA-014 Capacity Check

After the blind codec artifact was committed, the registered oracle join found
that added slack clears the cheapest evidence-complete payload threshold for
**47/49** DA-014 `INITIAL_PAYLOAD_TOO_LARGE` misses. All knowledge-update,
multi-session, user and temporal-reasoning cases clear; the two assistant cases
do not.

This does not mean 47 items will be delivered. Actual traversal can consume
slack, select a different member, or require conjunctions. It establishes that
the previous modal blocker is largely removed before allocation.

## Boundary and Next Step

The codec is lossless but introduces explicit dictionary references. Exact
decoding by code is not evidence that a language model will interpret them.
The naive exhaustive implementation is also too slow for production and needs
an equivalence-preserving optimization.

A successor may freeze phrase-coded direct contexts and replay the existing
temporal pair-then-turn allocator to measure exact availability. Reader use,
fresh-corpus validation and adoption require separate authorization; no such
claim is made here.


# DA-077 Sequence-Prefix Witness Audit

**Status:** `POSTHOC_SEQUENCE_PREFIX_WITNESS_CHARACTERIZED`
**Date:** August 31, 2026
**Parent:** DA-076 result commit `73c7aa3f`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Scope

DA-076 shows that exact ordered episode-feature sequences distinguish all five
residual role-union collisions. This audit asks how much of each exact sequence
is required. It does not define a traversal, selector, or substitution policy.

## Fixed Analysis

Use the five sealed DA-076 targets and their sealed role-union groups. Preserve
the DA-074 per-episode augmented feature sets and every episode position,
including empty feature sets. For prefix lengths one through the target's full
sequence length, compare the target prefix with the same-length prefix of every
peer. The first prefix with group size one is the witness.

Report witness depth, characters in a canonical exact encoding of the witness,
the peer-group sizes by depth, and the full sequence length. Also report whether
episode count alone was unique in DA-076. Do not search suffixes, subsequences,
alignments, hashes, codecs, scores, or alternate feature families.

Byte-identical replay and zero model, embedding, and cache calls are required.
This is posthoc structural anatomy only; no address, reader, transfer, delivery,
or adoption claim follows.

## Result

All five targets become unique after one or two episodes: witness depth p50 is
1, p90/max 2, against full sequence length 5-6. Canonical exact witnesses cost
36-236 characters (p50 135), versus 437-1,289 for full sequences (p50 594).

The witness is compact enough to motivate a sequence-prefix branching probe.
It is metadata, not evidence, and cannot replace a protected payload. Replay is
byte-identical; model, embedding, and cache calls are zero.

Artifacts:

- `artifacts/analysis/result.json`
- `artifacts/analysis/target_sessions.jsonl.gz`

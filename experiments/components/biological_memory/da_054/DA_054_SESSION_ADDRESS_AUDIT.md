# DA-054 Session Addressability Audit

**Status:** `COMPLETE; UNSEEDED_SESSION_BLOCKER`
**Date:** August 31, 2026
**Parent:** DA-053 result commit `52aaefbe`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Are DA-053's absent evidence members merely farther away within sessions already
seeded by retrieval, or do they live in sessions with no frozen temporal entry?

## Audit

Reproduce DA-053's 102 residual questions and 134 absent members exactly. Use
the frozen DA-042 `direct_ids` order. Define top-16 seeds as `direct_ids[:16]`,
matching the carried temporal seed count. Assign every absent member's episode:

- `TOP16_SESSION`: its session contains at least one top-16 seed;
- `DIRECT_TAIL_SESSION`: absent from top-16 seed sessions but its session
  contains a later packed direct episode;
- `UNTOUCHED_SESSION`: its session contains no packed direct episode.

For seeded/tail sessions report minimum absolute episode distance to the nearest
respective direct episode. Report member and question combinations by type.

This is evidence-aware anatomy only. It changes no rank, seed, edge, stream,
capacity, codec, or outcome. Zero model, embedding, and cache calls.

## Result

Of 134 absent members, 133 are in sessions untouched by the complete packed
direct set. One is in a top-16 seed session at distance 3; none are tail-only.
At question level, 99 are untouched-session, 1 top-16-session, and 2 have no
absent member because they are overflow-only. Longer rays close. The next
representation is an out-of-band deterministic session directory.

# DA-055 Control-Plane Session Directory

**Status:** `COMPLETE; SESSION_DIRECTORY_ADDRESSABILITY_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-054 result commit `1975597d`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can the memory store represent every session as an independently addressable
dependency chain without consuming prompt capacity or changing retrieval order?

## Blind Representation

For each of the sealed 465 LongMem questions, enumerate source sessions in
corpus order. Create one typed directory root with an ordered sequence of
session heads. Each head names its first episode and episode count. Each episode
node stores exact session/episode coordinates, reciprocal previous/next episode
pointers, and two deterministic member coordinates (`user`, `assistant`).

The sidecar stores identities and coordinates only, not rendered payload text,
question text, answer flags, evidence labels, similarity, rank, score, feature,
or model output. Payload remains in the immutable source store and is resolved
only by exact coordinate. DA-038 and all prior streams remain byte-identical;
the directory has zero rendered characters.

## Gates

Require locked corpus and 465-question population; every session exactly once;
every accepted episode exactly once; reciprocal chains; no cross-session edge;
two members per episode; canonical source order; exact identity replay; zero
rendered-char delta; byte-identical artifact replay; and zero model, embedding,
or cache calls. Stop unopened on failure.

## Addressability Audit

After sealing, resolve DA-053's 134 absent members through root -> session head
-> episode -> member coordinate. Report resolution count, session ordinal,
episode depth, and pointer hops. `SESSION_DIRECTORY_ADDRESSABILITY_SIGNAL`
requires 134/134 exact resolutions, zero ambiguity, and zero payload mutation.

Addressability is not delivery. Session selection, materialization, recognition,
stopping, reader use, runtime, fresh transfer, and adoption remain untested.

## Result

The blind sidecar contains 22,182 sessions, 106,412 episodes, and 212,824 member
coordinates with zero rendered characters. It resolves all 134/134 absent
members with zero ambiguity. Target session ordinal is p50 27.5, but episode
order is p50 0/p90 2 and pointer hops p50 3/p90 5. Session choice, not local
depth, is the next boundary.

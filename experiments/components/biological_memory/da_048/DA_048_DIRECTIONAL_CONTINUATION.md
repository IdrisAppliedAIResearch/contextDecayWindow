# DA-048 Directional Dependency Continuation

**Status:** `COMPLETE; SECOND_HOP_CAPACITY_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-047 contract commit `ac86c504`
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Does the frozen temporal edge itself carry enough structure to reach useful
evidence beyond DA-046's one-hop ceiling without modifying or displacing the
strongest payload?

DA-042's control-plane frontier contains only members of the original one-hop
neighbors. DA-048 adds one structural continuation along each edge's already
recorded direction. It introduces no new score.

## 2. Frozen Inputs

Use the sealed 465-question DA-042 envelopes and locked LongMemEval corpus.
Preserve DA-038, DA-045 traversal, DA-046 retained state, baseline edge order,
edge direction, and all prior payload identities byte-for-byte.

## 3. Blind Continuation

For each baseline edge in frozen order, locate its `neighbor_id` within its
source session. Move exactly one episode farther in the edge's recorded
direction (`-1` or `+1`). Reject session-boundary and missing continuations.
Reject episodes already present in DA-038 or already represented by DA-042's
one-hop frontier. Deduplicate episodes by first frozen-edge occurrence.

Emit user then assistant members for each surviving episode. Take the first 32
members in that deterministic order. Render each with DA-044's exact node codec;
expose it only when the frame is at most 2,048 characters, otherwise emit an
overflow action. Frames replace only `current`; immutable and retained bytes do
not change.

No question text, answer, `has_answer`, evidence identity, outcome, similarity,
feature, fitted parameter, or model output enters construction.

## 4. Blind Gates

Require 465 exact joins; locked corpus and DA-042 hashes; directions in
`{-1,+1}`; no cross-session continuation; no one-hop/direct duplication;
deterministic first-occurrence order; canonical frame replay; at least one frame
and one boundary rejection; peak frame <=2,048; unchanged DA-038 bytes; and zero
model, embedding, or cache calls. Stop unopened on failure.

## 5. Outcome Audit

After the blind artifact is sealed, measure complete evidence availability from
DA-046's 250 oracle ceiling plus an evidence-aware oracle `KEEP` of one DA-048
frame. Report gains/losses, target distance, action depth, payload and cumulative
cost. The oracle is nondeployable and tests structural capacity only.

Report `SECOND_HOP_CAPACITY_SIGNAL` for at least 5 gains, zero losses, and every
question type nonnegative. Report `WEAK_SECOND_HOP_CAPACITY_SIGNAL` for 1-4 gains
under the same protection. Otherwise report `NO_SECOND_HOP_CAPACITY_SIGNAL`.

## 6. Boundary

Passing would show only that directional dependency continuation exposes new
evidence with bounded peak capacity. Recognition, stopping, reader use, fresh
transfer, runtime, and adoption remain untested.

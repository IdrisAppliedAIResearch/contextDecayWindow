# DA-052 Protected Retained Dependency Set

**Status:** `COMPLETE; RETAINED_SET_CAPACITY_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-051 result commit `52c961ae`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can a bounded retained set compose distributed evidence from the already-sealed
one-hop and distance-2-to-5 streams without changing the strongest payload?

## Blind Contract

Replay DA-045, DA-048, and DA-050 action order exactly, in that order. Maintain
one replaceable `current` frame and a retained set of at most five exact frames,
matching DA-051's observed maximum required episode count. `KEEP` atomically
moves a valid current frame into the first free retained slot. Duplicate frame
hashes are rejected. Retained frames cannot be replaced, reordered, truncated,
merged, or summarized. DA-038 and every prior action remain immutable.

Each frame is capped at 2,048 characters; retained peak is capped at 10,240 and
current-plus-retained peak at 12,288. Admission reads only frame validity, hash,
slot availability, and duplicate identity. It reads no question, evidence,
answer, score, similarity, feature, model output, or outcome.

## Gates And Oracle Audit

Seal transition semantics and combined stream hashes before evidence. Exercise
empty, overflow, duplicate, full-set, next-frame, and retained-survival guards;
require atomic rollback, exact replay, immutable payload, and zero calls.

After sealing, an evidence-aware oracle may retain the minimum exact frame set
needed by each DA-050 residual. Report recoverable complete evidence by retained
count, stream source, peak and cumulative traversal. `RETAINED_SET_CAPACITY_SIGNAL`
requires >=10 gains, zero losses, <=5 retained frames, and all types nonnegative.

The oracle does not establish recognition, stopping, reader use, runtime, fresh
transfer, or adoption.

## Result

The five-slot oracle raises complete availability 332->363: 31 gains, zero
losses, p=9.31e-10. Retained counts are k2=24, k3=4, k4=1, k5=2. Retained
payload p50 is 646 chars and peak auxiliary p50 2,223, but cumulative traversal
p50 is 27,333 chars. Composition works; recognition and stopping now dominate.

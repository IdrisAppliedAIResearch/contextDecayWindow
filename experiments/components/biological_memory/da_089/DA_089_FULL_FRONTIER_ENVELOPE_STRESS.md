# DA-089 Full-Frontier Envelope Stress Test

**Status:** `COMPLETE; PARTIAL_FRONTIER_ENVELOPE_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-088 result commit `04889229`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Does DA-088's protected dependency-envelope representation transfer blindly
from 13 known residuals to all 8,055 sealed DA-042 frontier targets?

## Frozen Population And Routes

Use all DA-042 targets and the complete sealed DA-078 prompt membership. For
each target, use the first frozen baseline edge whose neighbor is the target
episode. Determine the route mechanically:

- `PROMPT_MEMBER` with zero frames when the exact target member is in DA-078;
- `PROMPT_SIBLING_FRAME` when the target's other member is in DA-078;
- `PROMPT_LINKED_FRAME` when any member of the edge seed is in DA-078; otherwise
- `ANCHORED_EDGE_SLICES`.

No evidence outcome, answer marker, text score, threshold, or route tuning is
allowed.

## Frozen Rendering

Prompt sibling/linked routes use one DA-044 canonical full child frame.
Orphan routes use DA-087's exact fixed 1,200-character parent-assistant chunks,
repeating exact parent user and full child in every slice. Preserve edge,
direction, identity, role, and source text. Every frame replaces the previous
frame and must be <=2,048 characters. DA-078 remains byte-for-byte immutable.

Do not add a chunked-child fallback or repair any overflow. Classify each target
as complete, full-child overflow, or anchored-slice overflow.

`FULL_FRONTIER_ENVELOPE_SIGNAL` requires 8,055/8,055 targets already present or
covered by complete exact envelopes, zero DA-078 mutation, and every frame
within cap. Otherwise report
`PARTIAL_FRONTIER_ENVELOPE_SIGNAL` and characterize the failure population for
a successor.

Require sealed joins, canonical decode, byte-identical replay, and zero model,
embedding, and cache calls. This is blind structural exposure only; no reader,
retention, stopping, delivery, runtime, transfer-to-outcomes, or adoption claim.

**Pre-analysis clarification:** `PROMPT_MEMBER` is necessary because DA-078 is
stronger than DA-042's DA-038 control and may already contain frontier members.
It adds no payload, route choice, or outcome information.

## Result

Blind transfer completes 4,556/8,055 targets (56.56%) with zero DA-078
mutation. Routes are 618 prompt-member, 4,507 sibling, 1,296 linked, and 1,634
anchored. Failures are 2,701 full-child overflows and 798 anchored-slice
overflows. Replay is byte-identical; zero calls.

Assistant members account for 2,672/2,701 full-child and 732/798 anchored
failures. Full-child overflow deficit is p50 488 characters; anchored deficit is
p50 1,454 because the full child repeats around context chunks. The fixed
13-item renderer does not transfer broadly. The successor must packetize large
source components exactly rather than tune route scores.

Artifacts:

- `artifacts/analysis/result.json`
- `artifacts/analysis/targets.jsonl.gz`

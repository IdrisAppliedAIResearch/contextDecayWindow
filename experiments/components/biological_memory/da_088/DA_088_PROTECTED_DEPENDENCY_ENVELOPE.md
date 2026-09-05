# DA-088 Protected Dependency Envelope

**Status:** `COMPLETE; PROTECTED_DEPENDENCY_ENVELOPE_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-087 result commit `e16d07bb`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can the strongest prompt and structural routes compose into one deterministic
bounded dependency envelope for all 13 DA-079 residuals without displacement?

## Fixed Composition

Use DA-083's sealed state as the route key; do not choose or score a route.

- `ROOT_MEMBER`: expose the sealed required DA-045 child frame with a typed
  same-carrier sibling edge to the immutable prompt member.
- `LINKED_PATH`: expose the sealed required DA-045 child frame with the exact
  one-edge parent provenance from DA-083 to its immutable prompt root.
- `ORPHAN_PARENT`: use the sealed complete DA-087 anchored edge slices.

DA-078 remains byte-for-byte immutable. All metadata is typed and out of band;
all payload frames remain replaceable and <=2,048 characters. Preserve source
identity, role, text, edge direction, and route order exactly.

`PROTECTED_DEPENDENCY_ENVELOPE_SIGNAL` requires exact 13/13 coverage, zero
DA-078 mutation, complete canonical payload exposure, and every frame within
cap. Report route cells, frames, peak, and cumulative characters.

This is structural exposure only. Require byte-identical replay and zero model,
embedding, and cache calls. No reader, retention, stopping, transfer, delivery,
runtime, or adoption claim.

## Result

All 13/13 residuals receive an exact protected envelope with zero DA-078
mutation: seven `PROMPT_LINKED_FRAME`, one `PROMPT_SIBLING_FRAME`, and five
`ANCHORED_EDGE_SLICES`. Route selection is the sealed DA-083 structural state,
not a score.

Frames are p50 one and p90 2.8. Peak frame characters are p50 555 and p90
1,907.8; cumulative characters are p50 555 and p90 4,872.4. Every payload is a
previously sealed exact frame or slice and remains within 2,048 characters.

This closes the offline representation/capacity gap for the 13 reachable
residuals while preserving the strongest prompt. Whether a reader recognizes,
retains, stops on, and uses the envelope remains untested. Replay is
byte-identical; zero model, embedding, and cache calls.

Artifacts:

- `artifacts/analysis/result.json`
- `artifacts/analysis/envelopes.jsonl.gz`

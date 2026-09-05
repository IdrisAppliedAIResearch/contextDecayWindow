# DA-050 Directional Cursor Through Distance Five

**Status:** `COMPLETE; FAR_DIRECTIONAL_CAPACITY_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-049 result commit `7b3b5386`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can a bounded cursor over the same frozen temporal rays expose the 37 farther
directional residuals without adding resident payload or displacing evidence?

## Blind Stream

Use DA-042's frozen baseline edge order. For each edge, continue from `seed_id`
at exact temporal distances 3, 4, then 5 in the recorded direction. Stay within
the source session. Reject missing and boundary targets. Exclude direct episodes
and all DA-042 one-hop episodes. Deduplicate an episode by first occurrence in
`(edge order, distance)` order. Emit user then assistant members.

Render every member with DA-044's exact codec. Expose one replaceable `current`
frame at a time; frames over 2,048 characters become overflow actions. DA-038,
DA-046 retained state, and every prior stream remain immutable. Do not truncate
the cursor by total action count; report peak and cumulative exposure explicitly.

No question, answer, evidence marker, similarity, feature, score, model output,
or outcome enters construction.

## Gates And Audit

Seal the complete cursor before evidence. Require locked hashes, 465 joins,
exact distances 3-5, no cross-session target, canonical replay, deterministic
deduplication, positive frames and rejections, peak <=2,048, unchanged payload,
and zero calls.

After sealing, use an evidence-aware one-frame oracle over the DA-050 cursor on
top of DA-048=295. Report gains/losses, distance, ordinal, frame chars, and
cumulative chars. `FAR_DIRECTIONAL_CAPACITY_SIGNAL` requires >=10 gains, zero
losses, and every type nonnegative; 1-9 is `WEAK_FAR_DIRECTIONAL_CAPACITY_SIGNAL`.

This tests structural availability only. Recognition, stopping, reader use,
runtime, fresh transfer, and adoption remain untested.

## Result

The protected oracle raises complete availability 295->332: 37 gains, zero
losses, p=1.46e-11. Useful frames have ordinal p50 7, payload p50 285 chars,
and cumulative traversal p50 3,190/p90 9,909.6 chars. The cursor recovers every
DA-049 singleton directional residual while preserving fixed peak capacity.

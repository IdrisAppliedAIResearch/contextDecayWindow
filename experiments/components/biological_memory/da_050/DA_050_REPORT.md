# DA-050 Report

**Disposition:** `FAR_DIRECTIONAL_CAPACITY_SIGNAL`

The complete distance-3-to-5 directional cursor preserves DA-038 and all prior
retained state while exposing one replaceable frame at a time. Its blind stream
contains 6,231 episodes, 9,591 fitting frames, and 2,871 overflows; peak frame
capacity remains 2,048 characters.

The evidence-aware one-frame oracle raises complete availability from 295 to
332: 37 gains, zero losses, two-sided exact p=1.46e-11. It recovers every
singleton farther-ray residual identified by DA-049. Useful frames occur at
ordinal p50 7 and carry p50 285 chars. Cumulative traversal is p50 3,190 and p90
9,909.6 chars.

The gain is structural reach with fixed peak capacity, not simultaneous token
flooding. Recognition and stopping are still oracle operations. No reader,
runtime, fresh-transfer, or adoption claim follows; zero calls occurred.

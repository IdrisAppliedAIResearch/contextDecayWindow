# DA-052 Report

**Disposition:** `RETAINED_SET_CAPACITY_SIGNAL`

DA-052 composes the sealed one-hop, distance-2, and distance-3-to-5 streams with
five append-only retained slots. DA-038 remains immutable; duplicate, empty,
overflow, and full-set operations reject atomically.

The evidence-aware minimum-set oracle raises complete availability from 332 to
363: 31 gains, zero losses, two-sided exact p=9.31e-10. Twenty-four gains need
two retained frames, four need three, one needs four, and two need five. All
question types are nonnegative.

Retained payload remains compact: p50 646 chars, max 1,494. Peak current plus
retained capacity is p50 2,223 and max 3,272, far below the registered 12,288
cap. The expensive axis is sequential search: cumulative traversal p50 27,333,
p90 34,820, max 51,950 chars.

This confirms that distributed dependency evidence composes without
displacement. It does not supply recognition or stopping; those remain oracle
operations. No reader, runtime, transfer, or adoption claim follows. Zero model,
embedding, and cache calls occurred.

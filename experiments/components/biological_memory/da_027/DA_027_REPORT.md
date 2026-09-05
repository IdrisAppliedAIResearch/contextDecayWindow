# DA-027 Compact Relative Backreferences Report

**Status:** `STOPPED AT BLIND NO-EXPANSION GATE`
**Date:** August 30, 2026
**Protocol commit:** `f639ee1d`
**Standing:** unopened mechanical stop

The compact relative codec passed all nine unit gates: canonical base-36
boundaries, exact roundtrip, collision-safe prefixes, and rejection of zero,
forward, malformed and out-of-bounds references.

The full blind allocation then stopped before producing an allocation artifact
and before any evidence access. At least one LongMem immutable DA-023 pack was
larger under the forced compact codec, violating the registered question-wise
no-expansion gate.

This closes the universal-codec policy, not relative pointers. DA-023 already
uses a question-wise renderer decision: 449/465 LongMem rows use backreferences
and 16 retain the prior control renderer. Forcing the compact codec removes that
fallback and therefore cannot be guaranteed to dominate the frozen control.

The next mechanically valid design is evidence-blind shortest-exact-codec
selection: compare exact charges for the existing DA-023 renderer and compact
relative renderer, retain the existing bytes on ties or expansion, and use
compact pointers only when strictly shorter. Decoded identities/order remain
immutable; additions still consume recovered tail capacity only.

There were zero model, embedding and cache calls. Outcomes were not opened.


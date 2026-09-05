# DA-032 Varint Residual Dependency Audit Report

**Status:** `COMPLETE; CORPUS-SPECIFIC SUCCESSORS`
**Date:** August 30, 2026
**Protocol commit:** `70475b0f`
**Standing:** spent evidence-aware causal audit

## Residuals

| Blocker | NF-004 | LongMemEval |
|---|---:|---:|
| Wrong frozen member | 3 | 21 |
| Prior varint consumption | 0 | 12 |
| Multi-carrier conjunction | 0 | 5 |
| Initial varint size | 0 | 1 |

NF is cleanly concentrated: all three remaining reachable misses need the other
member of an exposed carrier. However, none fits after the complete protected
DA-031 pack. Median postpack slack is 9 characters and median required cost is
108. Atomic completion alone therefore cannot safely close NF's final gap.

LongMem remains mixed, but 17/39 required materializations fit after the full
pack. This is a mechanically valid protected-atomic successor. Wrong member is
the largest class at 21/39, below the registered 60% dominance threshold.

## Interpretation

Varint pointers solved NF's prior-consumption band but then saturated the newly
available capacity with frozen-order additions. The final three dependencies
are structurally identified yet still need roughly another hundred characters
of representation headroom. This is a codec/dependency-interface boundary,
not evidence for local substitution scoring.

LongMem can proceed directly to a varint-plus-atomic composition because its
postpack fit is positive. NF should instead explore a stronger exact pointer
representation, such as stateful/delta coordinates, before composition.

Classification SHA-256 is
`cf7764fa9e96f5621330510704d1deb976f9a623f45047010430b69b0f250cfe`.
Replay is byte-identical; there were zero model, embedding and cache calls.


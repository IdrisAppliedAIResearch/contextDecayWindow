# DA-079 Scratchpad

## 2026-08-31 - Diagnostic Lock

- Freeze DA-078 byte-for-byte; inspect its 13 unresolved DA-039 requirements.
- Measure exact required-member cost at initial, arrival, and final states.
- Fixed blockers: initial size, prior consumption, or postpack fit.
- No reordering, retry, selector, codec change, or allocation claim.
- Zero model/embedder/cache calls.

## 2026-08-31 - Result

- DA-078 resolves 5/18; all remaining 13 are mechanically accounted for.
- Prior optimal atomic consumption: 9; initial optimal atomic size: 4.
- Initial-size deficits: 23, 98, 143, 1,391 chars.
- Prior-consumption arrival deficits: 28-245 chars; all nine fit initially.
- Postpack fits: 0. Dominant boundary is scheduling/lazy materialization.
- Byte-identical replay; zero calls.

# DA-039 Scratchpad

## 2026-08-30 - Registration

- Audit the exact 18 reachable misses after DA-038.
- Freeze and replay the complete protected DA-038 sequence before evidence.
- Distinguish conjunction structure from initial size and prior append-only
  capacity consumption.
- Zero intervention, model, embedding and cache calls.

## 2026-08-30 - Result

- All 18 residuals classify with zero unaccounted cases and byte-identical
  replay.
- Prior sentinel atomic consumption dominates 17/18; only one member is too
  large at the initial recovered-capacity boundary.
- Initial slack p50 is 765 chars, but final slack is 41.5; missing-member cost
  is 239 chars. No residual fits after the complete DA-038 pack.
- The next structural signal is to separate compact dependency references from
  payload materialization while keeping all DA-038 payloads immutable.
